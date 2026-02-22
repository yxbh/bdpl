from __future__ import annotations

from bdpl.model import Playlist

# Duration thresholds in seconds
_BUMPER_MAX = 10
_SHORT_MAX = 30
_OP_ED_MIN = 60
_OP_ED_MAX = 135
_EXTRA_MIN = 180
_EPISODE_MIN = 600  # 10 minutes
_PREVIEW_MAX = 60
_BODY_MIN_S = 300  # 5 minutes
_DIGITAL_ARCHIVE_MIN_ITEMS = 20
_DIGITAL_ARCHIVE_MAX_TOTAL_S = 300
_DIGITAL_ARCHIVE_MAX_AVG_ITEM_S = 0.5
_DIGITAL_ARCHIVE_MIN_UNIQUE_RATIO = 0.8


def is_digital_archive_playlist(pl: Playlist) -> bool:
    """Return True when playlist shape resembles an image archive.

    Heuristic targets menu-like playlists made of many ultra-short items
    (often one still image per clip) and avoids short video extras.
    """
    item_count = len(pl.play_items)
    if item_count < _DIGITAL_ARCHIVE_MIN_ITEMS:
        return False

    total_s = pl.duration_seconds
    if total_s > _DIGITAL_ARCHIVE_MAX_TOTAL_S:
        return False

    avg_item_s = total_s / item_count
    if avg_item_s > _DIGITAL_ARCHIVE_MAX_AVG_ITEM_S:
        return False

    unique_clip_count = len({pi.clip_id for pi in pl.play_items})
    unique_ratio = unique_clip_count / item_count
    return unique_ratio >= _DIGITAL_ARCHIVE_MIN_UNIQUE_RATIO


def label_segments(playlists: list[Playlist], segment_freq: dict[tuple, int]) -> None:
    """Mutate PlayItem.label in-place based on segment frequency and position.

    Rules applied in priority order:
    - duration < 30s and appears in many playlists → LEGAL
    - first segment in many episode-length playlists, 60-120s → OP
    - last/second-to-last segment in many episode-length playlists, 60-120s → ED
    - last segment, < 60s → PREVIEW
    - unique to one playlist and > 5min → BODY
    - else UNKNOWN
    """
    # Identify episode-length playlists (>10 min, for position analysis)
    ep_playlists = [pl for pl in playlists if pl.duration_seconds >= _EPISODE_MIN]

    # Count how often a segment appears as first item of ep playlists
    first_seg_count: dict[tuple, int] = {}
    last_seg_count: dict[tuple, int] = {}
    second_last_seg_count: dict[tuple, int] = {}
    for pl in ep_playlists:
        if pl.play_items:
            k = pl.play_items[0].segment_key()
            first_seg_count[k] = first_seg_count.get(k, 0) + 1
            k_last = pl.play_items[-1].segment_key()
            last_seg_count[k_last] = last_seg_count.get(k_last, 0) + 1
            if len(pl.play_items) >= 2:
                k_sl = pl.play_items[-2].segment_key()
                second_last_seg_count[k_sl] = second_last_seg_count.get(k_sl, 0) + 1

    # Assign labels
    for pl in playlists:
        for idx, pi in enumerate(pl.play_items):
            key = pi.segment_key()
            dur_s = pi.duration_seconds
            freq = segment_freq.get(key, 1)

            # Short + shared → LEGAL
            if dur_s < _SHORT_MAX and freq >= 2:
                pi.label = "LEGAL"
                continue

            # First in episode playlists, 60-120s → OP
            if _OP_ED_MIN <= dur_s <= _OP_ED_MAX and first_seg_count.get(key, 0) >= 2:
                pi.label = "OP"
                continue

            # Last or second-to-last in episode playlists, 60-120s → ED
            if _OP_ED_MIN <= dur_s <= _OP_ED_MAX and (
                last_seg_count.get(key, 0) >= 2 or second_last_seg_count.get(key, 0) >= 2
            ):
                pi.label = "ED"
                continue

            # Last segment and short → PREVIEW
            if idx == len(pl.play_items) - 1 and dur_s < _PREVIEW_MAX:
                pi.label = "PREVIEW"
                continue

            # Unique and long → BODY
            if freq == 1 and dur_s > _BODY_MIN_S:
                pi.label = "BODY"
                continue

            # Long segment (> 5 min) even if shared → BODY
            if dur_s > _BODY_MIN_S:
                pi.label = "BODY"
                continue

            pi.label = "UNKNOWN"


def classify_playlists(playlists: list[Playlist], play_all: list[Playlist]) -> dict[str, str]:
    """Return dict mpls_name -> category string.

    Categories: 'episode', 'play_all', 'menu', 'extra', 'bumper',
    'creditless_op', 'creditless_ed'.
    """
    play_all_names = {pl.mpls for pl in play_all}
    result: dict[str, str] = {}

    for pl in playlists:
        dur_s = pl.duration_seconds

        if pl.mpls in play_all_names:
            result[pl.mpls] = "play_all"
            continue

        if is_digital_archive_playlist(pl):
            result[pl.mpls] = "digital_archive"
            continue

        if dur_s < _BUMPER_MAX:
            result[pl.mpls] = "bumper"
            continue

        # Single-item playlists in the OP/ED duration range
        if len(pl.play_items) == 1 and _OP_ED_MIN <= dur_s <= _OP_ED_MAX:
            # Guess OP vs ED based on duration: shorter ones (~66s) lean OP
            if dur_s < 90:
                result[pl.mpls] = "creditless_op"
            else:
                result[pl.mpls] = "creditless_ed"
            continue

        if _BUMPER_MAX <= dur_s < _EXTRA_MIN:
            result[pl.mpls] = "extra"
            continue

        if dur_s >= _EPISODE_MIN:
            # Check if any play item has a BODY label
            has_body = any(pi.label == "BODY" for pi in pl.play_items)
            if has_body:
                result[pl.mpls] = "episode"
            else:
                result[pl.mpls] = "extra"
            continue

        # 180-600s range
        result[pl.mpls] = "extra"

    return result
