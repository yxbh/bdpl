"""Analysis and episode inference modules."""

from __future__ import annotations

import logging
from pathlib import Path

from bdpl.model import ClipInfo, DiscAnalysis, Playlist, SpecialFeature, Warning, ticks_to_ms

from bdpl.analyze.signatures import compute_signatures, find_duplicates
from bdpl.analyze.clustering import cluster_by_duration, pick_representative
from bdpl.analyze.segment_graph import (
    build_segment_frequency,
    find_shared_segments,
    detect_play_all,
)
from bdpl.analyze.classify import label_segments, classify_playlists
from bdpl.analyze.ordering import order_episodes
from bdpl.analyze.explain import explain_disc

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
                    {"title": t.title_num, "movie_object": t.movie_object_id}
                    for t in idx.titles
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
            for obj in mo.objects:
                if obj.referenced_playlists:
                    obj_playlists[obj.object_id] = obj.referenced_playlists
            hints["movie_objects"] = {
                "count": len(mo.objects),
                "obj_playlists": obj_playlists,
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


def _parse_ig_hints(
    bdmv_path: Path, clips: dict[str, ClipInfo], hints: dict
) -> None:
    """Try to parse IG menu streams and add hints in-place."""
    from bdpl.bdmv.ig_stream import parse_ig_from_m2ts, extract_menu_hints

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
                clip_id, len(ics.pages), len(page_hints),
            )

    if all_ig_hints:
        hints["ig_menu"] = {
            "hint_count": len(all_ig_hints),
            "chapter_marks": sorted(set(
                h.register_sets.get(2)
                for h in all_ig_hints
                if 2 in h.register_sets
            )),
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
            classifications, playlists, episodes,
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

        features.append(SpecialFeature(
            index=idx,
            playlist=mpls,
            duration_ms=dur_ms,
            category=category,
            chapter_start=ch_start,
        ))
        idx += 1

    return features


def _special_features_from_classifications(
    classifications: dict[str, str],
    playlists: list[Playlist],
    episodes: list,
) -> list[SpecialFeature]:
    """Fallback: build special features list from playlist classifications."""
    ep_playlists = {ep.playlist for ep in episodes} if episodes else set()
    pl_by_name = {pl.mpls: pl for pl in playlists}
    features: list[SpecialFeature] = []
    idx = 1

    non_episode_cats = {"creditless_op", "creditless_ed", "extra"}
    for mpls, cat in sorted(classifications.items()):
        if cat not in non_episode_cats or mpls in ep_playlists:
            continue
        pl = pl_by_name.get(mpls)
        if pl is None:
            continue
        features.append(SpecialFeature(
            index=idx,
            playlist=mpls,
            duration_ms=pl.duration_ms,
            category=cat,
        ))
        idx += 1

    return features


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
    analysis["duplicate_groups"] = [
        [pl.mpls for pl in group] for group in dup_groups
    ]

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
    episodes = order_episodes(unique_playlists, play_all)

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
        match_pl = next(
            (p for p in unique_playlists if p.mpls == ep_playlist), None
        )
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
    if play_all and episodes and all(
        ep.playlist in {p.mpls for p in play_all} for ep in episodes
    ):
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
        hints, classifications, playlists, episodes,
    )

    return DiscAnalysis(
        path=str(bdmv_path),
        playlists=playlists,
        clips=clips,
        episodes=episodes,
        warnings=warnings,
        special_features=special_features,
        analysis=analysis,
    )
