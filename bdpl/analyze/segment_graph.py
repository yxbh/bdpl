from __future__ import annotations

from collections import defaultdict

from bdpl.model import Playlist


def build_segment_frequency(playlists: list[Playlist]) -> dict[tuple, int]:
    """Count how often each segment key appears across all playlists."""
    freq: dict[tuple, int] = defaultdict(int)
    for pl in playlists:
        for pi in pl.play_items:
            freq[pi.segment_key()] += 1
    return dict(freq)


def find_shared_segments(playlists: list[Playlist]) -> dict[tuple, list[str]]:
    """Map segment_key -> list of mpls names that use it."""
    mapping: dict[tuple, list[str]] = defaultdict(list)
    for pl in playlists:
        for pi in pl.play_items:
            key = pi.segment_key()
            if pl.mpls not in mapping[key]:
                mapping[key].append(pl.mpls)
    return dict(mapping)


def detect_play_all(playlists: list[Playlist]) -> list[Playlist]:
    """Identify playlists whose segments are a superset/concatenation of
    other playlists' segments — i.e. "Play All" playlists.

    A playlist is considered a Play All if:
    - It has multiple play items
    - Its total duration is significantly longer than any other playlist
    - Its segment keys are a superset of at least one other playlist's
      full segment set, OR it concatenates segments that individually
      appear as standalone playlists
    """
    if len(playlists) < 2:
        return []

    # Build set of segment keys per playlist
    pl_segments: dict[str, list[tuple]] = {}
    for pl in playlists:
        pl_segments[pl.mpls] = [pi.segment_key() for pi in pl.play_items]

    # For each single-item playlist, note its segment key
    single_segments: set[tuple] = set()
    for pl in playlists:
        if len(pl.play_items) == 1:
            single_segments.add(pl.play_items[0].segment_key())

    # Also collect all segment keys from all playlists (not self)
    all_segment_sets: dict[str, set[tuple]] = {
        pl.mpls: set(pl_segments[pl.mpls]) for pl in playlists
    }

    play_all: list[Playlist] = []
    for pl in playlists:
        if len(pl.play_items) < 2:
            continue

        my_keys = set(pl_segments[pl.mpls])

        # Check if this playlist's segments are a superset of any other
        # playlist's segments
        is_superset = False
        for other in playlists:
            if other.mpls == pl.mpls:
                continue
            if len(other.play_items) == 0:
                continue
            other_keys = all_segment_sets[other.mpls]
            if other_keys and other_keys.issubset(my_keys):
                is_superset = True
                break

        # Also check: does this playlist contain multiple segments that
        # each appear in standalone (single-item) playlists?
        contained_singles = sum(1 for k in pl_segments[pl.mpls] if k in single_segments)

        # Or: is this playlist much longer than most others and has
        # multiple long items?
        long_items = sum(1 for pi in pl.play_items if pi.duration_seconds > 600)

        if is_superset or contained_singles >= 2 or long_items >= 2:
            play_all.append(pl)

    return play_all
