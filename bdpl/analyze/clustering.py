from __future__ import annotations

from bdpl.model import ClipInfo, Playlist


def cluster_by_duration(
    playlists: list[Playlist], tolerance_ratio: float = 0.15
) -> list[list[Playlist]]:
    """Cluster playlists by similar duration.

    Two playlists are in the same cluster if their durations differ by less
    than *tolerance_ratio* of the shorter one.  Returns clusters sorted by
    cluster size (largest first).
    """
    if not playlists:
        return []

    sorted_pls = sorted(playlists, key=lambda p: p.duration_ms)
    clusters: list[list[Playlist]] = []
    current: list[Playlist] = [sorted_pls[0]]

    for pl in sorted_pls[1:]:
        ref_dur = current[0].duration_ms
        if ref_dur == 0:
            # Avoid division by zero; group zero-length together
            if pl.duration_ms == 0:
                current.append(pl)
            else:
                clusters.append(current)
                current = [pl]
        elif abs(pl.duration_ms - ref_dur) / ref_dur <= tolerance_ratio:
            current.append(pl)
        else:
            clusters.append(current)
            current = [pl]

    clusters.append(current)
    clusters.sort(key=len, reverse=True)
    return clusters


def pick_representative(cluster: list[Playlist], clips: dict[str, ClipInfo]) -> Playlist:
    """Pick best representative from a cluster.

    Prefers the playlist with: more streams on first clip, then more chapters,
    then shortest mpls name (likely lower-numbered / canonical).
    """

    def _score(pl: Playlist) -> tuple:
        stream_count = 0
        if pl.play_items:
            cid = pl.play_items[0].clip_id
            if cid in clips:
                stream_count = len(clips[cid].streams)
            if not stream_count:
                stream_count = len(pl.play_items[0].streams)
        chapter_count = len(pl.chapters)
        return (stream_count, chapter_count, -len(pl.mpls))

    return max(cluster, key=_score)
