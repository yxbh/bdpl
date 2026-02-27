from __future__ import annotations

from collections import defaultdict

from bdpl.model import Playlist


def compute_signatures(playlists: list[Playlist]) -> dict[str, tuple]:
    """Return dict mapping mpls name -> loose signature tuple."""
    return {pl.mpls: pl.signature_loose() for pl in playlists}


def find_duplicates(playlists: list[Playlist], quant_ms: float = 250) -> list[list[Playlist]]:
    """Group playlists with identical loose signatures.

    Returns list of clusters where each cluster has 2+ playlists sharing
    the same signature.
    """
    sig_groups: dict[tuple, list[Playlist]] = defaultdict(list)
    for pl in playlists:
        sig = pl.signature_loose(quant_ms=quant_ms)
        sig_groups[sig].append(pl)
    return [group for group in sig_groups.values() if len(group) >= 2]


def find_primary_clip_variants(
    playlists: list[Playlist],
    min_primary_ratio: float = 0.85,
    duration_tolerance_ms: float = 5000,
) -> list[list[Playlist]]:
    """Group playlists that share the same dominant primary clip.

    Detects stream-variant playlists where the primary clip (first play
    item) is identical and accounts for the vast majority of the total
    duration, but secondary clips differ (e.g. different outro or audio
    commentary version).

    Only groups playlists that were NOT already caught by exact signature
    dedup (i.e. their full signatures differ).

    Parameters
    ----------
    playlists:
        Candidate playlists to check.
    min_primary_ratio:
        Minimum fraction of total duration the first play item must
        represent for a playlist to be considered primary-clip-dominated.
    duration_tolerance_ms:
        Maximum difference in primary clip duration (ms) to still be
        considered the same clip.

    Returns
    -------
    List of variant groups (each with 2+ playlists sharing the same
    primary clip).
    """
    # Only consider playlists dominated by their first play item
    candidates: list[tuple[str, float, float, Playlist]] = []
    for pl in playlists:
        if not pl.play_items:
            continue
        first = pl.play_items[0]
        total_dur = pl.duration_ms
        if total_dur <= 0:
            continue
        if first.duration_ms / total_dur < min_primary_ratio:
            continue
        in_ms = round(first.in_time * 1000 / 45000)
        candidates.append((first.clip_id, in_ms, first.duration_ms, pl))

    # Group by clip_id, then merge candidates with similar in_time
    # and duration within tolerance
    by_clip: dict[str, list[tuple[float, float, Playlist]]] = defaultdict(list)
    for clip_id, in_ms, dur_ms, pl in candidates:
        by_clip[clip_id].append((in_ms, dur_ms, pl))

    variant_groups: list[list[Playlist]] = []
    for entries in by_clip.values():
        if len(entries) < 2:
            continue
        # Cluster entries with similar in_time and duration
        groups: list[list[Playlist]] = []
        used: set[int] = set()
        for i, (in_i, dur_i, pl_i) in enumerate(entries):
            if i in used:
                continue
            group = [pl_i]
            used.add(i)
            for j, (in_j, dur_j, pl_j) in enumerate(entries):
                if j in used:
                    continue
                if (
                    abs(in_i - in_j) < duration_tolerance_ms
                    and abs(dur_i - dur_j) < duration_tolerance_ms
                ):
                    group.append(pl_j)
                    used.add(j)
            if len(group) >= 2:
                # Only include if full signatures differ (not exact dups)
                sigs = {pl.signature_loose() for pl in group}
                if len(sigs) > 1:
                    groups.append(group)
        variant_groups.extend(groups)
    return variant_groups
