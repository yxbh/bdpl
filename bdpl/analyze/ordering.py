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


def _episodes_from_chapters(
    playlist: Playlist,
) -> list[Episode]:
    """Split a single long playlist into episodes using chapter marks.

    Used when a playlist contains one (or few) very long play item(s) with
    multiple episodes encoded back-to-back, distinguishable only by chapters.

    Heuristic: group consecutive chapters into blocks whose total duration
    falls within episode range (10–45 min). When a running block exceeds the
    expected episode length, start a new episode at the chapter boundary.
    """
    if not playlist.chapters or len(playlist.chapters) < 4:
        return []

    # Only consider chapters on the main play item (item_ref=0 typically)
    # Build list of (chapter_index, start_time_ms)
    main_item = playlist.play_items[0]
    ticks_to_ms(main_item.in_time)

    ch_times: list[float] = []
    for ch in playlist.chapters:
        ch_ms = ticks_to_ms(ch.timestamp)
        ch_times.append(ch_ms)

    # Compute total playlist duration
    total_dur_ms = playlist.duration_ms
    # Estimate episode count from total duration
    # Typical anime episode: 22–26 min; try to find the best fit
    est_ep_dur_ms = 25 * 60 * 1000  # 25 minutes as starting estimate
    est_count = max(1, round(total_dur_ms / est_ep_dur_ms))

    if est_count <= 1:
        return []  # Not worth splitting

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
) -> list[Episode]:
    """Infer ordered episode list.

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
            ch_episodes = _episodes_from_chapters(best_pa)
            if len(ch_episodes) > len(pa_episodes):
                pa_episodes = ch_episodes

    # Strategy 1: use individual episode playlists — but only if they
    # look like real episodes and not just long extras.
    # Prefer Play All decomposition when it yields more (or equal) episodes
    # that are individually longer than the individual candidates.
    if individual_eps and pa_episodes:
        avg_indiv = sum(p.duration_ms for p in individual_eps) / len(individual_eps)
        avg_pa = sum(e.duration_ms for e in pa_episodes) / len(pa_episodes) if pa_episodes else 0
        # If Play All yields more episodes whose average duration is much
        # longer, the individual playlists are probably extras, not episodes.
        if len(pa_episodes) > len(individual_eps) and avg_pa > avg_indiv * 1.5:
            return pa_episodes
        return _episodes_from_individual(individual_eps)

    if individual_eps:
        # Strategy 3: if only one "episode" but it's very long with chapters,
        # it likely contains multiple episodes in a single m2ts
        if len(individual_eps) == 1:
            candidate = individual_eps[0]
            ch_episodes = _episodes_from_chapters(candidate)
            if len(ch_episodes) >= 2:
                return ch_episodes
        return _episodes_from_individual(individual_eps)

    if pa_episodes:
        return pa_episodes

    # No episodes found
    return []
