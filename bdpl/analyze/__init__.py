"""Analysis and episode inference modules."""

from __future__ import annotations

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


def scan_disc(
    bdmv_path: str | Path,
    playlists: list[Playlist],
    clips: dict[str, ClipInfo],
) -> DiscAnalysis:
    """Run the full analysis pipeline and return a DiscAnalysis."""
    warnings: list[Warning] = []
    analysis: dict = {}

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
