from __future__ import annotations

from bdpl.model import DiscAnalysis


def _fmt_duration(ms: float) -> str:
    """Format milliseconds as H:MM:SS or M:SS."""
    total_s = ms / 1000.0
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = total_s % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:04.1f}"
    return f"{m}:{s:04.1f}"


def explain_disc(analysis: DiscAnalysis) -> str:
    """Generate a multi-line text explanation of the disc analysis."""
    lines: list[str] = []
    lines.append(f"Disc: {analysis.path}")
    lines.append(f"Playlists: {len(analysis.playlists)}")
    lines.append("")

    # Classification summary
    classifications = analysis.analysis.get("classifications", {})
    if classifications:
        lines.append("Playlist classification:")
        for mpls, cat in sorted(classifications.items()):
            pl = next(
                (p for p in analysis.playlists if p.mpls == mpls), None
            )
            dur_str = _fmt_duration(pl.duration_ms) if pl else "?"
            lines.append(f"  {mpls}: {cat} ({dur_str})")
        lines.append("")

    # Episodes
    if analysis.episodes:
        lines.append(f"Episodes found: {len(analysis.episodes)}")
        for ep in analysis.episodes:
            dur_str = _fmt_duration(ep.duration_ms)
            seg_labels = ", ".join(s.label for s in ep.segments)
            lines.append(
                f"  Episode {ep.episode}: {dur_str} "
                f"(playlist={ep.playlist}, confidence={ep.confidence:.0%}, "
                f"segments=[{seg_labels}])"
            )
        lines.append("")

    # Duplicates
    dup_groups = analysis.analysis.get("duplicate_groups", [])
    if dup_groups:
        lines.append("Duplicate playlist groups:")
        for group in dup_groups:
            lines.append(f"  {', '.join(group)}")
        lines.append("")

    # Play-all
    play_all_names = analysis.analysis.get("play_all", [])
    if play_all_names:
        lines.append(f"Play All playlists: {', '.join(play_all_names)}")
        lines.append("")

    # Warnings
    if analysis.warnings:
        lines.append("Warnings:")
        for w in analysis.warnings:
            lines.append(f"  [{w.code}] {w.message}")
        lines.append("")

    return "\n".join(lines)
