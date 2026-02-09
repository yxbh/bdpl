"""Analysis and episode inference modules."""

from __future__ import annotations

import logging
from pathlib import Path

from bdpl.model import ClipInfo, DiscAnalysis, Playlist, Warning

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


def _parse_disc_hints(bdmv_path: Path) -> dict:
    """Parse index.bdmv and MovieObject.bdmv for navigation hints.

    Returns a dict with 'title_playlists' (title# → playlist#) mapping
    and raw parsed objects, or empty dict on failure.
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

    return hints


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
    hints = _parse_disc_hints(bdmv)
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

    return DiscAnalysis(
        path=str(bdmv_path),
        playlists=playlists,
        clips=clips,
        episodes=episodes,
        warnings=warnings,
        analysis=analysis,
    )
