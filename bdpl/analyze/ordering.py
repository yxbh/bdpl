from __future__ import annotations

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


def order_episodes(
    playlists: list[Playlist],
    play_all_playlists: list[Playlist],
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
        return _episodes_from_individual(individual_eps)

    if pa_episodes:
        return pa_episodes

    # No episodes found
    return []
