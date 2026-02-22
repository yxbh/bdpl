"""Analysis and episode inference modules."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from bdpl.analyze.classify import classify_playlists, label_segments
from bdpl.analyze.clustering import cluster_by_duration, pick_representative
from bdpl.analyze.explain import explain_disc
from bdpl.analyze.ordering import order_episodes
from bdpl.analyze.segment_graph import (
    build_segment_frequency,
    detect_play_all,
    find_shared_segments,
)
from bdpl.analyze.signatures import compute_signatures, find_duplicates
from bdpl.model import (
    ClipInfo,
    DiscAnalysis,
    Episode,
    Playlist,
    SegmentRef,
    SpecialFeature,
    Warning,
    ticks_to_ms,
)

log = logging.getLogger(__name__)

__all__ = [
    "compute_signatures",
    "find_duplicates",
    "cluster_by_duration",
    "pick_representative",
    "build_segment_frequency",
    "find_shared_segments",
    "detect_play_all",
    "label_segments",
    "classify_playlists",
    "order_episodes",
    "explain_disc",
    "scan_disc",
]


def _parse_disc_hints(bdmv_path: Path, clips: dict[str, ClipInfo] | None = None) -> dict:
    """Parse index.bdmv, MovieObject.bdmv, and IG menu streams for hints.

    Returns a dict with 'title_playlists' (title# → playlist#) mapping,
    IG menu hints, and raw parsed objects, or empty dict on failure.
    """
    hints: dict = {}

    # --- index.bdmv ---
    index_file = bdmv_path / "index.bdmv"
    if index_file.is_file():
        try:
            from bdpl.bdmv.index_bdmv import parse_index_bdmv

            idx = parse_index_bdmv(index_file)
            hints["index"] = {
                "first_playback_obj": idx.first_playback_obj,
                "top_menu_obj": idx.top_menu_obj,
                "titles": [
                    {"title": t.title_num, "movie_object": t.movie_object_id} for t in idx.titles
                ],
            }
        except Exception:
            log.debug("Failed to parse index.bdmv", exc_info=True)

    # --- MovieObject.bdmv ---
    mobj_file = bdmv_path / "MovieObject.bdmv"
    if mobj_file.is_file():
        try:
            from bdpl.bdmv.movieobject_bdmv import parse_movieobject_bdmv

            mo = parse_movieobject_bdmv(mobj_file)
            # Build title → playlist mapping via index titles → movie objects
            obj_playlists: dict[int, list[int]] = {}
            obj_play_marks: dict[int, list[tuple[int, int]]] = {}
            for obj in mo.objects:
                if obj.referenced_playlists:
                    obj_playlists[obj.object_id] = obj.referenced_playlists
                marks = [
                    (cmd.operand1, cmd.operand2)
                    for cmd in obj.commands
                    if cmd.group == 0 and cmd.sub_group == 2 and cmd.op_code == 2
                ]
                if marks:
                    obj_play_marks[obj.object_id] = marks
            hints["movie_objects"] = {
                "count": len(mo.objects),
                "obj_playlists": obj_playlists,
                "obj_play_marks": obj_play_marks,
            }
        except Exception:
            log.debug("Failed to parse MovieObject.bdmv", exc_info=True)

    # Combine: resolve title → playlist via title → obj → playlist
    if "index" in hints and "movie_objects" in hints:
        obj_pl = hints["movie_objects"]["obj_playlists"]
        title_playlists: dict[int, list[int]] = {}
        for t in hints["index"]["titles"]:
            obj_id = t["movie_object"]
            if obj_id in obj_pl:
                title_playlists[t["title"]] = obj_pl[obj_id]
        hints["title_playlists"] = title_playlists

    # --- IG stream (experimental) ---
    if clips:
        try:
            _parse_ig_hints(bdmv_path, clips, hints)
        except Exception:
            log.debug("Failed to parse IG menu hints", exc_info=True)

    return hints


def _parse_ig_hints(bdmv_path: Path, clips: dict[str, ClipInfo], hints: dict) -> None:
    """Try to parse IG menu streams and add hints in-place."""
    from bdpl.bdmv.ig_stream import extract_menu_hints, parse_ig_from_m2ts

    stream_dir = bdmv_path / "STREAM"
    if not stream_dir.is_dir():
        return

    # Find clips with IG streams (stream_type 0x91)
    ig_clips = [
        clip_id
        for clip_id, clip in clips.items()
        if any(s.stream_type == 0x91 for s in clip.streams)
    ]
    if not ig_clips:
        return

    all_ig_hints = []
    for clip_id in ig_clips:
        m2ts = stream_dir / f"{clip_id}.m2ts"
        if not m2ts.is_file():
            continue
        ics = parse_ig_from_m2ts(m2ts)
        if ics is None:
            continue
        page_hints = extract_menu_hints(ics)
        if page_hints:
            all_ig_hints.extend(page_hints)
            log.debug(
                "IG clip %s: %d pages, %d actionable buttons",
                clip_id,
                len(ics.pages),
                len(page_hints),
            )

    if all_ig_hints:
        hints["ig_menu"] = {
            "hint_count": len(all_ig_hints),
            "chapter_marks": sorted(
                set(h.register_sets.get(2) for h in all_ig_hints if 2 in h.register_sets)
            ),
            "has_direct_play": any(h.playlist is not None for h in all_ig_hints),
        }
        hints["ig_hints_raw"] = all_ig_hints


def _detect_special_features(
    hints: dict,
    classifications: dict[str, str],
    playlists: list[Playlist],
    episodes: list,
) -> list[SpecialFeature]:
    """Detect special features using IG menu JumpTitle buttons + title hints.

    Looks for IG buttons that JumpTitle to non-episode playlists. When a button
    also sets reg2 (chapter index), it indicates multiple features within one
    playlist — each gets its own SpecialFeature entry.
    """
    ig_hints_raw = hints.get("ig_hints_raw", [])
    title_pl = hints.get("title_playlists", {})

    if not ig_hints_raw or not title_pl:
        # Fall back to classification-only detection (no IG data)
        return _special_features_from_classifications(
            classifications,
            playlists,
            episodes,
            hints,
        )

    # Build set of episode playlists to exclude
    ep_playlists = {ep.playlist for ep in episodes} if episodes else set()
    # Also exclude play_all playlists
    play_all_set = set()
    for mpls, cat in classifications.items():
        if cat == "play_all":
            play_all_set.add(mpls)

    # Build title → playlist name mapping (0-based title index)
    title_to_mpls: dict[int, str] = {}
    for title_num, pl_nums in title_pl.items():
        if pl_nums:
            title_to_mpls[title_num] = f"{pl_nums[0]:05d}.mpls"

    # Build playlist lookup
    pl_by_name = {pl.mpls: pl for pl in playlists}

    # Find IG buttons with JumpTitle to non-episode titles.
    # JumpTitle operand is 1-based; index titles are 0-based.
    seen: set[tuple[str, int | None]] = set()
    features: list[SpecialFeature] = []
    idx = 1

    # Sort by page then button_id for stable menu-order output
    sorted_hints = sorted(ig_hints_raw, key=lambda h: (h.page_id, h.button_id))

    for h in sorted_hints:
        if h.jump_title is None:
            continue
        # Convert 1-based JumpTitle to 0-based index title
        title_idx = h.jump_title - 1
        mpls = title_to_mpls.get(title_idx)
        if mpls is None:
            continue
        if mpls in ep_playlists or mpls in play_all_set:
            continue

        ch_start = h.register_sets.get(2)
        key = (mpls, ch_start)
        if key in seen:
            continue
        seen.add(key)

        pl = pl_by_name.get(mpls)
        if pl is None:
            continue

        category = classifications.get(mpls, "extra")

        # Calculate duration for chapter-split features
        dur_ms = pl.duration_ms
        if ch_start is not None and pl.chapters and len(pl.chapters) > 1:
            ch_times = [ticks_to_ms(ch.timestamp) for ch in pl.chapters]
            end_ms = ticks_to_ms(pl.play_items[-1].out_time)
            if ch_start < len(ch_times):
                start_ms = ch_times[ch_start]
                # Find next chapter-start for this same playlist
                next_start = None
                for h2 in sorted_hints:
                    if h2.jump_title != h.jump_title:
                        continue
                    r2 = h2.register_sets.get(2)
                    if r2 is not None and r2 > ch_start and r2 < len(ch_times):
                        if next_start is None or ch_times[r2] < next_start:
                            next_start = ch_times[r2]
                if next_start is not None:
                    dur_ms = next_start - start_ms
                else:
                    dur_ms = end_ms - start_ms

        features.append(
            SpecialFeature(
                index=idx,
                playlist=mpls,
                duration_ms=dur_ms,
                category=category,
                chapter_start=ch_start,
                menu_visible=True,
            )
        )
        idx += 1

    # Supplement direct IG-derived features with title-hint specials when
    # menus jump via intermediate logic and only expose a subset of targets.
    title_hint_entries = _title_hint_non_episode_entries(hints, classifications, episodes)
    existing_keys = {(feature.playlist, feature.chapter_start) for feature in features}
    pl_by_name = {pl.mpls: pl for pl in playlists}
    for mpls, chapter_starts in title_hint_entries:
        pl = pl_by_name.get(mpls)
        if pl is None:
            continue
        category = classifications.get(mpls, "extra")
        if category in {"episode", "play_all"}:
            continue

        if chapter_starts and pl.chapters:
            for chapter_idx, chapter_start in enumerate(chapter_starts):
                key = (mpls, chapter_start)
                if key in existing_keys:
                    continue
                chapter_end = (
                    chapter_starts[chapter_idx + 1]
                    if chapter_idx + 1 < len(chapter_starts)
                    else None
                )
                features.append(
                    SpecialFeature(
                        index=idx,
                        playlist=mpls,
                        duration_ms=_duration_from_chapter_window(pl, chapter_start, chapter_end),
                        category=category,
                        chapter_start=chapter_start,
                        menu_visible=True,
                    )
                )
                existing_keys.add(key)
                idx += 1
            continue

        key = (mpls, None)
        if key in existing_keys:
            continue
        features.append(
            SpecialFeature(
                index=idx,
                playlist=mpls,
                duration_ms=pl.duration_ms,
                category=category,
                menu_visible=True,
            )
        )
        existing_keys.add(key)
        idx += 1

    return features


def _title_hint_non_episode_entries(
    hints: dict,
    classifications: dict[str, str],
    episodes: list,
) -> list[tuple[str, list[int]]]:
    """Return ordered non-episode title-hint playlists and optional chapter starts."""
    title_pl = hints.get("title_playlists", {})
    if not title_pl:
        return []

    title_to_object = {
        entry["title"]: entry["movie_object"] for entry in hints.get("index", {}).get("titles", [])
    }
    obj_play_marks = hints.get("movie_objects", {}).get("obj_play_marks", {})

    ep_playlists = {ep.playlist for ep in episodes} if episodes else set()
    play_all_set = {mpls for mpls, cat in classifications.items() if cat == "play_all"}

    ordered: list[tuple[str, list[int]]] = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for title_num, pl_nums in sorted(title_pl.items()):
        if not pl_nums:
            continue
        playlist_num = pl_nums[0]
        mpls = f"{playlist_num:05d}.mpls"
        if mpls in ep_playlists or mpls in play_all_set:
            continue

        chapter_starts: list[int] = []
        object_id = title_to_object.get(title_num)
        if object_id is not None:
            starts = {
                mark
                for pl_num, mark in obj_play_marks.get(object_id, [])
                if pl_num == playlist_num and mark >= 0
            }
            if starts:
                starts = starts | {0}
                chapter_starts = sorted(starts)

        key = (mpls, tuple(chapter_starts))
        if key in seen:
            continue

        ordered.append((mpls, chapter_starts))
        seen.add(key)
    return ordered


def _duration_from_chapter_window(
    playlist: Playlist,
    chapter_start: int,
    chapter_end: int | None,
) -> float:
    """Return duration in ms for a chapter window within a playlist."""
    if not playlist.chapters:
        return playlist.duration_ms

    chapter_times = [ticks_to_ms(chapter.timestamp) for chapter in playlist.chapters]
    if chapter_start < 0 or chapter_start >= len(chapter_times):
        return playlist.duration_ms

    start_ms = chapter_times[chapter_start]
    if chapter_end is not None and 0 <= chapter_end < len(chapter_times):
        end_ms = chapter_times[chapter_end]
    else:
        end_ms = ticks_to_ms(playlist.play_items[-1].out_time)

    duration_ms = end_ms - start_ms
    return duration_ms if duration_ms > 0 else playlist.duration_ms


def _infer_visible_button_count_from_ig(hints: dict) -> int:
    """Infer visible content-button count from IG button hints.

    Chapter menus typically set register 2 before JumpTitle. Buttons that
    JumpTitle without setting register 2 are treated as visible content items.
    """
    ig_hints_raw = hints.get("ig_hints_raw", [])
    if not ig_hints_raw:
        return 0

    visible_buttons: set[tuple[int, int]] = set()
    for hint in ig_hints_raw:
        if hint.jump_title is None:
            continue
        if 2 in hint.register_sets:
            continue
        if hint.button_id <= 0:
            continue
        visible_buttons.add((hint.page_id, hint.button_id))
    return len(visible_buttons)


def _special_visibility_score(feature: SpecialFeature) -> tuple[int, int, float]:
    """Return ranking key for likely menu-visible special features."""
    try:
        playlist_num = int(feature.playlist.split(".")[0])
    except (ValueError, IndexError):
        playlist_num = 99999

    score = 0
    if playlist_num < 1000:
        score += 2
    if feature.duration_ms >= 15_000:
        score += 1
    return (score, -playlist_num, feature.duration_ms)


def _is_likely_menu_visible_special(feature: SpecialFeature) -> bool:
    """Fallback visibility heuristic when no IG button evidence exists."""
    try:
        playlist_num = int(feature.playlist.split(".")[0])
    except (ValueError, IndexError):
        return False
    if playlist_num >= 1000:
        return False
    return feature.duration_ms >= 15_000


def _apply_menu_visibility_from_hints(features: list[SpecialFeature], hints: dict) -> None:
    """Mark each SpecialFeature as menu-visible or not, in-place."""
    if not features:
        return

    visible_count = _infer_visible_button_count_from_ig(hints)
    if visible_count <= 0:
        for feature in features:
            feature.menu_visible = _is_likely_menu_visible_special(feature)
        return

    # Best effort: IG-derived count approximates number of visible content
    # entries, then ranking chooses the most likely visible features.
    ranked = sorted(features, key=_special_visibility_score, reverse=True)
    visible_keys = {
        (feature.playlist, feature.chapter_start, feature.index)
        for feature in ranked[:visible_count]
    }
    for feature in features:
        feature.menu_visible = (
            feature.playlist,
            feature.chapter_start,
            feature.index,
        ) in visible_keys


def _special_features_from_classifications(
    classifications: dict[str, str],
    playlists: list[Playlist],
    episodes: list,
    hints: dict | None = None,
) -> list[SpecialFeature]:
    """Fallback: build special features list from playlist classifications."""
    ep_playlists = {ep.playlist for ep in episodes} if episodes else set()
    pl_by_name = {pl.mpls: pl for pl in playlists}
    features: list[SpecialFeature] = []
    idx = 1

    title_hint_entries = _title_hint_non_episode_entries(hints or {}, classifications, episodes)
    if title_hint_entries:
        for mpls, chapter_starts in title_hint_entries:
            pl = pl_by_name.get(mpls)
            if pl is None:
                continue
            category = classifications.get(mpls, "extra")
            if category in {"episode", "play_all"}:
                category = "extra"

            if chapter_starts and pl.chapters:
                for chapter_idx, chapter_start in enumerate(chapter_starts):
                    chapter_end = (
                        chapter_starts[chapter_idx + 1]
                        if chapter_idx + 1 < len(chapter_starts)
                        else None
                    )
                    features.append(
                        SpecialFeature(
                            index=idx,
                            playlist=mpls,
                            duration_ms=_duration_from_chapter_window(
                                pl,
                                chapter_start,
                                chapter_end,
                            ),
                            category=category,
                            chapter_start=chapter_start,
                            menu_visible=True,
                        )
                    )
                    idx += 1
                continue

            features.append(
                SpecialFeature(
                    index=idx,
                    playlist=mpls,
                    duration_ms=pl.duration_ms,
                    category=category,
                    menu_visible=True,
                )
            )
            idx += 1

        _apply_menu_visibility_from_hints(features, hints or {})
        return features

    non_episode_cats = {"creditless_op", "creditless_ed", "extra", "digital_archive"}
    for mpls, cat in sorted(classifications.items()):
        if cat not in non_episode_cats or mpls in ep_playlists:
            continue
        pl = pl_by_name.get(mpls)
        if pl is None:
            continue
        features.append(
            SpecialFeature(
                index=idx,
                playlist=mpls,
                duration_ms=pl.duration_ms,
                category=cat,
                menu_visible=True,
            )
        )
        idx += 1

    _apply_menu_visibility_from_hints(features, hints or {})

    return features


def _downsample_scene_starts(starts_ms: list[float], target_count: int = 4) -> list[float]:
    """Downsample sorted scene starts to at most ``target_count`` anchors."""
    if len(starts_ms) <= target_count:
        return starts_ms
    if target_count <= 1:
        return [starts_ms[0]]

    last = len(starts_ms) - 1
    indices = {round(i * last / (target_count - 1)) for i in range(target_count)}
    return [starts_ms[i] for i in sorted(indices)]


def _sanitize_scene_starts(
    starts_ms: list[float],
    duration_ms: float,
    *,
    target_count: int = 4,
    min_tail_ms: float = 120_000,
) -> list[float]:
    """Normalize raw scene start anchors and avoid terminal end-mark artifacts."""
    starts = sorted({start for start in starts_ms if 0 <= start < duration_ms})
    if not starts:
        return []

    # Some playlists contain a final chapter marker ~end_of_episode; keep it
    # out of scene starts when enough earlier anchors are available.
    trimmed = [start for start in starts if start <= duration_ms - min_tail_ms]
    if len(trimmed) >= target_count:
        return trimmed

    return starts


def _scene_mark_indices_from_ig(hints: dict) -> dict[str, list[int]]:
    """Collect chapter-mark indices from IG button hints by target playlist."""
    ig_hints_raw = hints.get("ig_hints_raw", [])
    title_pl = hints.get("title_playlists", {})
    if not ig_hints_raw or not title_pl:
        return {}

    title_to_mpls: dict[int, str] = {}
    for title_num, pl_nums in title_pl.items():
        if pl_nums:
            title_to_mpls[title_num] = f"{pl_nums[0]:05d}.mpls"

    result: dict[str, list[int]] = defaultdict(list)
    for hint in ig_hints_raw:
        if hint.jump_title is None or 2 not in hint.register_sets:
            continue
        title_idx = hint.jump_title - 1
        mpls = title_to_mpls.get(title_idx)
        if mpls is None:
            continue
        mark_idx = hint.register_sets[2]
        if mark_idx >= 0:
            result[mpls].append(mark_idx)

    return {mpls: sorted(set(indices)) for mpls, indices in result.items() if indices}


def _build_episode_scenes(episodes: list[Episode], playlists: list[Playlist], hints: dict) -> None:
    """Populate ``Episode.scenes`` from menu chapter marks and chapter metadata.

    Primary source is IG chapter-button marks (register 2 values). When unavailable,
    fallback is playlist chapter anchors, downsampled to four scene entries.
    """
    if not episodes:
        return

    pl_by_name = {playlist.mpls: playlist for playlist in playlists}
    mark_map = _scene_mark_indices_from_ig(hints)

    episode_by_playlist = {episode.playlist: episode for episode in episodes}
    episode_by_clip: dict[str, Episode] = {}
    for episode in episodes:
        if episode.segments:
            episode_by_clip[episode.segments[0].clip_id] = episode

    starts_by_episode: dict[str, list[float]] = defaultdict(list)

    # Direct episode-targeted IG marks
    for mpls, indices in mark_map.items():
        episode = episode_by_playlist.get(mpls)
        playlist = pl_by_name.get(mpls)
        if episode is None or playlist is None or not playlist.chapters or not playlist.play_items:
            continue
        base_in = playlist.play_items[0].in_time
        for index in indices:
            if index < 0 or index >= len(playlist.chapters):
                continue
            chapter = playlist.chapters[index]
            local_ms = ticks_to_ms(chapter.timestamp - base_in)
            if 0 <= local_ms < episode.duration_ms:
                starts_by_episode[episode.playlist].append(local_ms)

    # Play-all-targeted IG marks mapped to episodes by chapter play_item_ref clip
    for mpls, indices in mark_map.items():
        play_all = pl_by_name.get(mpls)
        if play_all is None or not play_all.chapters or not play_all.play_items:
            continue
        for index in indices:
            if index < 0 or index >= len(play_all.chapters):
                continue
            chapter = play_all.chapters[index]
            if chapter.play_item_ref < 0 or chapter.play_item_ref >= len(play_all.play_items):
                continue
            play_item = play_all.play_items[chapter.play_item_ref]
            episode = episode_by_clip.get(play_item.clip_id)
            if episode is None:
                continue

            ep_playlist = pl_by_name.get(episode.playlist)
            if ep_playlist is None or not ep_playlist.play_items:
                continue
            ep_base_in = ep_playlist.play_items[0].in_time
            local_ms = ticks_to_ms(chapter.timestamp - ep_base_in)
            if 0 <= local_ms < episode.duration_ms:
                starts_by_episode[episode.playlist].append(local_ms)

    for episode in episodes:
        playlist = pl_by_name.get(episode.playlist)
        if playlist is None or not playlist.play_items:
            continue

        starts = sorted(set(starts_by_episode.get(episode.playlist, [])))
        if not starts:
            base_in = playlist.play_items[0].in_time
            starts = [
                ticks_to_ms(chapter.timestamp - base_in)
                for chapter in playlist.chapters
                if 0 <= ticks_to_ms(chapter.timestamp - base_in) < episode.duration_ms
            ]
            starts = sorted(set(starts))

        starts = _sanitize_scene_starts(starts, episode.duration_ms, target_count=4)
        starts = _downsample_scene_starts(starts, target_count=4)

        if not starts:
            starts = [0.0]

        # Ensure first scene starts at episode start.
        if starts[0] > 250.0:
            starts = [0.0, *starts]
            starts = _downsample_scene_starts(sorted(set(starts)), target_count=4)

        clip_id = (
            episode.segments[0].clip_id if episode.segments else playlist.play_items[0].clip_id
        )
        scene_segments: list[SegmentRef] = []
        for idx, start_ms in enumerate(starts):
            end_ms = starts[idx + 1] if idx + 1 < len(starts) else episode.duration_ms
            if end_ms <= start_ms:
                continue
            scene_segments.append(
                SegmentRef(
                    key=("SCENE", episode.playlist, idx + 1),
                    clip_id=clip_id,
                    in_ms=start_ms,
                    out_ms=end_ms,
                    duration_ms=end_ms - start_ms,
                    label="SCENE",
                )
            )

        episode.scenes = scene_segments


def _maybe_keep_single_title_episode(
    episodes: list[Episode],
    playlists: list[Playlist],
    hints: dict,
    classifications: dict[str, str],
) -> list[Episode]:
    """Collapse chapter-split output back to one episode when hints warrant it.

    This addresses discs where one long main feature is chapter-split by
    heuristics, while disc navigation clearly presents a separate title for
    digital archive content.
    """
    if len(episodes) < 2:
        return episodes

    episode_playlists = {ep.playlist for ep in episodes}
    if len(episode_playlists) != 1:
        return episodes
    playlist_name = next(iter(episode_playlists))

    try:
        playlist_num = int(playlist_name.split(".")[0])
    except (ValueError, IndexError):
        return episodes

    title_pl = hints.get("title_playlists", {})
    if not title_pl:
        return episodes

    titles_for_main = [title for title, pl_nums in title_pl.items() if playlist_num in pl_nums]
    if len(titles_for_main) != 1:
        return episodes

    referenced_playlist_nums = {p for pl_nums in title_pl.values() for p in pl_nums}
    has_archive_title = any(
        classifications.get(f"{pl_num:05d}.mpls") == "digital_archive"
        for pl_num in referenced_playlist_nums
        if pl_num != playlist_num
    )
    if not has_archive_title:
        return episodes

    playlist = next((pl for pl in playlists if pl.mpls == playlist_name), None)
    if playlist is None:
        return episodes

    segments = [
        SegmentRef(
            key=pi.segment_key(),
            clip_id=pi.clip_id,
            in_ms=ticks_to_ms(pi.in_time),
            out_ms=ticks_to_ms(pi.out_time),
            duration_ms=pi.duration_ms,
            label=pi.label,
        )
        for pi in playlist.play_items
    ]

    log.debug(
        "Collapsing %d inferred episodes into one for %s based on title/archive hints",
        len(episodes),
        playlist.mpls,
    )

    return [
        Episode(
            episode=1,
            playlist=playlist.mpls,
            duration_ms=playlist.duration_ms,
            # Higher than chapter-split base (0.6) because title hints
            # confirm one main feature with a separate archive title.
            confidence=0.85,
            segments=segments,
        )
    ]


def scan_disc(
    bdmv_path: str | Path,
    playlists: list[Playlist],
    clips: dict[str, ClipInfo],
) -> DiscAnalysis:
    """Run the full analysis pipeline and return a DiscAnalysis."""
    warnings: list[Warning] = []
    analysis: dict = {}
    bdmv = Path(bdmv_path)

    # 0. Parse navigation hints (index.bdmv + MovieObject.bdmv)
    hints = _parse_disc_hints(bdmv, clips)
    if hints:
        analysis["disc_hints"] = hints

    # 1. Deduplicate playlists
    dup_groups = find_duplicates(playlists)
    analysis["duplicate_groups"] = [[pl.mpls for pl in group] for group in dup_groups]

    # Pick representatives — deduplicated working set
    seen_sigs: set[tuple] = set()
    unique_playlists: list[Playlist] = []
    for pl in playlists:
        sig = pl.signature_loose()
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            unique_playlists.append(pl)
        else:
            # Find the cluster this playlist belongs to, pick representative
            for group in dup_groups:
                if pl in group:
                    rep = pick_representative(group, clips)
                    if rep not in unique_playlists:
                        unique_playlists.append(rep)
                    break

    if dup_groups:
        warnings.append(
            Warning(
                code="DUPLICATES",
                message=f"Found {len(dup_groups)} group(s) of duplicate playlists",
                context={"groups": analysis["duplicate_groups"]},
            )
        )

    # 2. Build segment frequency map
    segment_freq = build_segment_frequency(unique_playlists)
    analysis["segment_freq_keys"] = len(segment_freq)

    # 3. Detect play-all playlists
    play_all = detect_play_all(unique_playlists)
    analysis["play_all"] = [pl.mpls for pl in play_all]

    # 4. Label segments
    label_segments(unique_playlists, segment_freq)

    # 5. Classify playlists
    classifications = classify_playlists(unique_playlists, play_all)
    analysis["classifications"] = classifications

    # 6. Order episodes
    episodes = order_episodes(unique_playlists, play_all, classifications)

    episodes = _maybe_keep_single_title_episode(
        episodes,
        unique_playlists,
        hints,
        classifications,
    )

    # If episodes came from Play All decomposition, reclassify playlists
    # that were marked 'episode' but whose segments aren't in the episode
    # list as 'extra' instead.
    if episodes and all(ep.playlist in {p.mpls for p in play_all} for ep in episodes):
        ep_clip_ids = {seg.clip_id for ep in episodes for seg in ep.segments}
        for mpls, cat in list(classifications.items()):
            if cat == "episode":
                pl = next((p for p in unique_playlists if p.mpls == mpls), None)
                if pl and not any(pi.clip_id in ep_clip_ids for pi in pl.play_items):
                    classifications[mpls] = "extra"

    # 6b. Boost confidence when navigation hints confirm episode playlists
    title_pl = hints.get("title_playlists", {})
    if title_pl and episodes:
        # Build set of playlist numbers referenced by titles
        hint_playlist_nums: set[int] = set()
        for pls in title_pl.values():
            hint_playlist_nums.update(pls)

        for ep in episodes:
            # Extract playlist number from name like "00002.mpls" → 2
            try:
                pl_num = int(ep.playlist.split(".")[0])
            except (ValueError, IndexError):
                continue
            if pl_num in hint_playlist_nums:
                ep.confidence = min(1.0, ep.confidence + 0.1)

    # 6c. Boost confidence when IG chapter marks confirm episode boundaries
    ig_menu = hints.get("ig_menu", {})
    ig_marks = ig_menu.get("chapter_marks")
    if ig_marks and episodes and len(ig_marks) >= 2:
        # Build list of chapter-start indices for each episode
        # (episode starts at the chapter whose timestamp matches ep.segments[0].in_ms)
        ep_playlist = episodes[0].playlist
        match_pl = next((p for p in unique_playlists if p.mpls == ep_playlist), None)
        if match_pl and match_pl.chapters:
            ch_times = [ticks_to_ms(ch.timestamp) for ch in match_pl.chapters]
            ep_start_indices: list[int] = []
            for ep in episodes:
                seg_in = ep.segments[0].in_ms
                # Find the chapter index closest to this episode start
                best_idx = min(
                    range(len(ch_times)),
                    key=lambda j: abs(ch_times[j] - seg_in),
                )
                if abs(ch_times[best_idx] - seg_in) < 500:  # within 500ms
                    ep_start_indices.append(best_idx)

            if sorted(ep_start_indices) == sorted(ig_marks[: len(ep_start_indices)]):
                for ep in episodes:
                    ep.confidence = min(1.0, ep.confidence + 0.1)

    if not episodes:
        warnings.append(
            Warning(
                code="NO_EPISODES",
                message="Could not identify any episodes on this disc",
            )
        )

    # 7. Extra warnings
    if play_all and episodes and all(ep.playlist in {p.mpls for p in play_all} for ep in episodes):
        warnings.append(
            Warning(
                code="PLAY_ALL_ONLY",
                message=(
                    "Episodes were inferred by decomposing Play All "
                    "playlist — no individual episode playlists found"
                ),
                context={"play_all": analysis["play_all"]},
            )
        )

    # 8. Detect special features from IG menu + title hints
    special_features = _detect_special_features(
        hints,
        classifications,
        playlists,
        episodes,
    )

    # 9. Build scene-level episode segments from menu/chapter markers.
    _build_episode_scenes(episodes, unique_playlists, hints)

    return DiscAnalysis(
        path=str(bdmv_path),
        playlists=playlists,
        clips=clips,
        episodes=episodes,
        warnings=warnings,
        special_features=special_features,
        analysis=analysis,
    )
