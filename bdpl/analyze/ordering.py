from __future__ import annotations

from collections.abc import Iterable

from bdpl.model import Episode, Playlist, SegmentRef, ticks_to_ms

# Minimum duration (seconds) for an item to be considered an episode
_EPISODE_MIN_S = 600  # 10 minutes
_EPISODE_ITEM_MIN_S = 300  # 5 minutes for play-all decomposition


def _make_segment_ref(pi) -> SegmentRef:
    """Build a SegmentRef from a PlayItem."""
    return SegmentRef(
        key=pi.segment_key(),
        clip_id=pi.clip_id,
        in_ms=ticks_to_ms(pi.in_time),
        out_ms=ticks_to_ms(pi.out_time),
        duration_ms=pi.duration_ms,
        label=pi.label,
    )


def _episodes_from_individual(
    episode_playlists: list[Playlist],
) -> list[Episode]:
    """Build episodes from individual episode-length playlists.

    Sort by the body segment's clip_id (clip IDs increase with episode order).
    """

    episode_playlists = _collapse_body_equivalent_variants(episode_playlists)

    # Sort by first BODY clip_id, falling back to first clip_id
    def _sort_key(pl: Playlist) -> str:
        for pi in pl.play_items:
            if pi.label == "BODY":
                return pi.clip_id
        return pl.play_items[0].clip_id if pl.play_items else ""

    sorted_pls = sorted(episode_playlists, key=_sort_key)

    episodes: list[Episode] = []
    for idx, pl in enumerate(sorted_pls, start=1):
        segments = [_make_segment_ref(pi) for pi in pl.play_items]
        episodes.append(
            Episode(
                episode=idx,
                playlist=pl.mpls,
                duration_ms=pl.duration_ms,
                confidence=0.9,
                segments=segments,
            )
        )
    return episodes


def _body_signature(playlist: Playlist) -> tuple:
    """Return a normalized signature of BODY segments for one playlist."""
    body_segments = [
        pi.segment_key(quant_ms=5000) for pi in playlist.play_items if pi.label == "BODY"
    ]
    if body_segments:
        return tuple(body_segments)
    return playlist.signature_loose()


def _collapse_body_equivalent_variants(playlists: Iterable[Playlist]) -> list[Playlist]:
    """Collapse episode variants that share the same BODY segment signature."""
    by_sig: dict[tuple, Playlist] = {}
    for playlist in playlists:
        sig = _body_signature(playlist)
        current = by_sig.get(sig)
        if current is None or playlist.duration_ms > current.duration_ms:
            by_sig[sig] = playlist
    return list(by_sig.values())


def _episodes_from_play_all(
    play_all: Playlist,
) -> list[Episode]:
    """Decompose a Play All playlist into episodes.

    Each play item that is episode-length (>5 min) becomes an episode.
    Short items at the end are ignored (extras/outros).
    """
    episodes: list[Episode] = []
    ep_num = 0

    for pi in play_all.play_items:
        seg = _make_segment_ref(pi)
        if pi.duration_seconds >= _EPISODE_ITEM_MIN_S:
            ep_num += 1
            episodes.append(
                Episode(
                    episode=ep_num,
                    playlist=play_all.mpls,
                    duration_ms=pi.duration_ms,
                    confidence=0.7,
                    segments=[seg],
                )
            )

    return episodes


def _chapter_durations_s(playlist: Playlist) -> list[float]:
    """Return chapter durations in seconds for a playlist."""
    ch_times = [ticks_to_ms(ch.timestamp) for ch in playlist.chapters]
    total_ms = playlist.duration_ms
    durs: list[float] = []
    for i in range(len(ch_times)):
        end = ch_times[i + 1] if i + 1 < len(ch_times) else total_ms
        durs.append((end - ch_times[i]) / 1000)
    return durs


# Anime episode chapter structure ranges (in seconds)
_OP_MIN_S, _OP_MAX_S = 45, 160  # opening theme
_BODY_MIN_S_CH = 180  # body segment (scene)
_ED_MIN_S, _ED_MAX_S = 45, 160  # ending theme


def _detect_episode_periodicity(
    ch_durs_s: list[float],
) -> tuple[int, int, float] | None:
    """Detect repeating episode structure in chapter durations.

    Anime episode compilations embed a fixed structure per episode:
    OP (~90 s) → Body segments → ED (~90 s) [→ Preview (~30 s)].  This
    creates a periodic pattern visible in the chapter durations.

    Tries periods 4–7 (chapters per episode).  For each candidate period,
    partitions chapters into groups and checks whether each group matches
    the expected structure (OP-length first chapter, at least one long body
    chapter, ED-length chapter near the end).

    Returns ``(period, n_episodes, confidence)`` for the best match, where
    *confidence* is the fraction of groups that match.  Returns ``None``
    when no period achieves ≥ 75 % match with ≥ 2 groups.
    """
    n = len(ch_durs_s)
    best: tuple[int, int, float] | None = None

    for period in range(4, 8):
        # Allow total chapters to be within ±1 of period × n_groups
        for n_groups in range(2, n // period + 2):
            total_expected = n_groups * period
            if abs(total_expected - n) > 1:
                continue

            groups_matched = 0
            for g in range(n_groups):
                start = g * period
                end = min(start + period, n)
                group = ch_durs_s[start:end]
                if len(group) < 3:
                    continue

                # OP: first chapter, or second if first is a short preamble
                op_ok = _OP_MIN_S <= group[0] <= _OP_MAX_S
                if not op_ok and len(group) >= 4 and group[0] < _OP_MIN_S:
                    op_ok = _OP_MIN_S <= group[1] <= _OP_MAX_S
                body_ok = any(d > _BODY_MIN_S_CH for d in group[1:-1])
                # ED: within last 3 positions (covers trailing preview/transition)
                ed_ok = any(
                    _ED_MIN_S <= group[-(i + 1)] <= _ED_MAX_S for i in range(min(3, len(group) - 1))
                )

                if op_ok and body_ok and ed_ok:
                    groups_matched += 1

            if n_groups >= 2 and groups_matched >= 2:
                score = groups_matched / n_groups
                # Majority rule: more groups match than don't.  A simple
                # majority is structural evidence rather than a magic
                # threshold.  Series finales often drop OP/ED, making one
                # group fail without invalidating the overall pattern.
                if groups_matched * 2 > n_groups:
                    if best is None or score > best[2] or (score == best[2] and n_groups > best[1]):
                        best = (period, n_groups, score)

    return best


def _episodes_from_chapters(
    playlist: Playlist,
    ig_chapter_marks: list[int] | None = None,
) -> list[Episode]:
    """Split a single long playlist into episodes using chapter marks.

    Used when a playlist contains one (or few) very long play item(s) with
    multiple episodes encoded back-to-back, distinguishable only by chapters.

    **Decision to split** requires positive structural evidence from at least
    one of two signals:

    1. **IG chapter marks** — buttons in the disc menu directly encode episode
       start chapters (e.g. reg2 = [0, 5, 10, 15]).  Definitive.
    2. **Chapter periodicity** — chapter durations show a repeating
       OP / body / ED cycle characteristic of anime episode compilations.

    Without either signal the playlist is assumed to be a single movie or OVA
    and is *not* split, regardless of total duration.

    Splitting uses a greedy algorithm that groups consecutive chapters into
    blocks whose total duration approaches the target episode length.
    """
    if not playlist.chapters or len(playlist.chapters) < 4:
        return []

    main_item = playlist.play_items[0]

    ch_times: list[float] = []
    for ch in playlist.chapters:
        ch_times.append(ticks_to_ms(ch.timestamp))

    total_dur_ms = playlist.duration_ms
    est_ep_dur_ms = 25 * 60 * 1000  # 25 minutes as starting estimate
    est_count = max(1, round(total_dur_ms / est_ep_dur_ms))

    if est_count <= 1:
        return []  # Not worth splitting

    # --- Require positive structural evidence before splitting ---
    has_ig_confirmation = ig_chapter_marks is not None and len(ig_chapter_marks) >= 2
    if not has_ig_confirmation:
        ch_durs = _chapter_durations_s(playlist)
        periodicity = _detect_episode_periodicity(ch_durs)
        if periodicity is None:
            return []  # No structural evidence of episodes
        # Use the detected episode count from periodicity when it differs
        # from the duration-based estimate.
        _, periodic_count, _ = periodicity
        if abs(periodic_count - est_count) <= 1:
            est_count = periodic_count

    # Target duration per episode
    target_dur_ms = total_dur_ms / est_count
    # Tolerance: 60% to 140% of target
    min_ep_ms = target_dur_ms * 0.60
    max_ep_ms = target_dur_ms * 1.40

    # Greedily group chapters into episodes.
    # At each candidate split point, compare "split here" vs "include next
    # chapter" and pick whichever is closer to the target duration.
    episodes: list[Episode] = []
    ep_start_ms = ch_times[0]
    ep_start_idx = 0

    for i in range(1, len(ch_times)):
        block_dur = ch_times[i] - ep_start_ms

        if block_dur >= min_ep_ms:
            # How far is current block from target?
            undershoot = abs(block_dur - target_dur_ms)
            # How far would we be if we include the next chapter?
            if i + 1 < len(ch_times):
                next_dur = ch_times[i + 1] - ep_start_ms
                overshoot = abs(next_dur - target_dur_ms)
            else:
                overshoot = float("inf")

            # Split here if this is closer to target than including
            # the next chapter, or if next chapter would exceed max
            if undershoot <= overshoot or block_dur > max_ep_ms:
                ep_num = len(episodes) + 1
                seg = SegmentRef(
                    key=(main_item.clip_id, round(ep_start_ms), round(ch_times[i])),
                    clip_id=main_item.clip_id,
                    in_ms=ep_start_ms,
                    out_ms=ch_times[i],
                    duration_ms=block_dur,
                    label="BODY",
                )
                episodes.append(
                    Episode(
                        episode=ep_num,
                        playlist=playlist.mpls,
                        duration_ms=block_dur,
                        confidence=0.6,
                        segments=[seg],
                    )
                )
                ep_start_ms = ch_times[i]
                ep_start_idx = i

    # Handle remaining chapters as final episode (if substantial)
    remaining_ms = ticks_to_ms(main_item.out_time) - ep_start_ms
    if remaining_ms >= min_ep_ms and ep_start_idx < len(ch_times) - 1:
        ep_num = len(episodes) + 1
        out_ms = ticks_to_ms(main_item.out_time)
        seg = SegmentRef(
            key=(main_item.clip_id, round(ep_start_ms), round(out_ms)),
            clip_id=main_item.clip_id,
            in_ms=ep_start_ms,
            out_ms=out_ms,
            duration_ms=remaining_ms,
            label="BODY",
        )
        episodes.append(
            Episode(
                episode=ep_num,
                playlist=playlist.mpls,
                duration_ms=remaining_ms,
                confidence=0.6,
                segments=[seg],
            )
        )

    # Only accept if we got the expected number of episodes (±1)
    if abs(len(episodes) - est_count) <= 1 and len(episodes) >= 2:
        return episodes
    return []


def order_episodes(
    playlists: list[Playlist],
    play_all_playlists: list[Playlist],
    classifications: dict[str, str] | None = None,
    ig_chapter_marks: list[int] | None = None,
) -> list[Episode]:
    """Infer ordered episode list.

    Parameters:
        ig_chapter_marks: Chapter indices from IG menu buttons that confirm
            episode boundaries.  Passed through to chapter-splitting logic.

    Strategy:
    1. If there are individual episode-length playlists (>10 min, not in
       play_all list) with unique body segments, use those.
    2. If no individual episode playlists exist but there is a Play All,
       decompose it: each play item >5 min becomes an episode.
    3. Assign confidence based on method used.
    """
    play_all_names = {pl.mpls for pl in play_all_playlists}

    # Find individual episode playlists (not play-all, >10 min)
    if classifications and any(cat == "episode" for cat in classifications.values()):
        individual_eps = [
            pl
            for pl in playlists
            if pl.mpls not in play_all_names and classifications.get(pl.mpls) == "episode"
        ]
    else:
        individual_eps = [
            pl
            for pl in playlists
            if pl.mpls not in play_all_names and pl.duration_seconds >= _EPISODE_MIN_S
        ]

    # Strategy 2: decompose the longest Play All
    pa_episodes: list[Episode] = []
    if play_all_playlists:
        best_pa = max(play_all_playlists, key=lambda p: p.duration_ms)
        pa_episodes = _episodes_from_play_all(best_pa)
        # If play-all decomposition yields only 1 episode, try chapter-based
        if len(pa_episodes) <= 1 and best_pa.chapters:
            ch_episodes = _episodes_from_chapters(best_pa, ig_chapter_marks)
            if len(ch_episodes) > len(pa_episodes):
                pa_episodes = ch_episodes

    # Strategy 1: use individual episode playlists — but only if they
    # look like real episodes and not just long extras.
    # Prefer Play All decomposition when it yields more (or equal) episodes
    # that are individually longer than the individual candidates.
    if individual_eps and pa_episodes:
        avg_indiv = sum(p.duration_ms for p in individual_eps) / len(individual_eps)
        avg_pa = sum(e.duration_ms for e in pa_episodes) / len(pa_episodes) if pa_episodes else 0
        if len(pa_episodes) > len(individual_eps):
            # If individual episode clips are a strict subset of the
            # play_all clips, the individual playlists only cover some
            # episodes (the rest are play_all-only).  Use play_all.
            indiv_clips = {pi.clip_id for p in individual_eps for pi in p.play_items}
            pa_clips = {seg.clip_id for ep in pa_episodes for seg in ep.segments}
            if indiv_clips <= pa_clips:
                return pa_episodes
            # If Play All episodes are much longer on average, the
            # individual playlists are probably extras, not episodes.
            if avg_pa > avg_indiv * 1.5:
                return pa_episodes
        return _episodes_from_individual(individual_eps)

    if individual_eps:
        # Try chapter-splitting the longest playlist.  If structural
        # evidence (IG marks or periodicity) confirms it's a compilation,
        # its split episodes are better than one massive "episode" entry.
        longest = max(individual_eps, key=lambda p: p.duration_ms)
        ch_episodes = _episodes_from_chapters(longest, ig_chapter_marks)
        if len(ch_episodes) >= 2:
            return ch_episodes
        return _episodes_from_individual(individual_eps)

    if pa_episodes:
        return pa_episodes

    # No episodes found
    return []
