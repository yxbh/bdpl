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
