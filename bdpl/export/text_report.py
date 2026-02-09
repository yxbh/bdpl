"""Text/rich report for terminal display."""
from __future__ import annotations

from bdpl.model import DiscAnalysis


def format_duration(ms: float) -> str:
    """Format milliseconds as HH:MM:SS or MM:SS."""
    total_seconds = int(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def text_report(analysis: DiscAnalysis) -> str:
    """Generate a plain text summary report."""
    lines: list[str] = []

    # Disc Summary
    clip_ids = set()
    for pl in analysis.playlists:
        for pi in pl.play_items:
            clip_ids.add(pi.clip_id)

    lines.append("=" * 60)
    lines.append("Disc Summary")
    lines.append("=" * 60)
    lines.append(f"  Path:       {analysis.path}")
    lines.append(f"  Playlists:  {len(analysis.playlists)}")
    lines.append(f"  Clips:      {len(clip_ids)}")
    lines.append("")

    # Playlists table
    classifications = analysis.analysis.get("classifications", {})
    lines.append("-" * 60)
    lines.append("Playlists")
    lines.append("-" * 60)
    lines.append(f"  {'Name':<16} {'Duration':>10} {'Items':>6}  {'Class'}")
    lines.append(f"  {'----':<16} {'--------':>10} {'-----':>6}  {'-----'}")
    for pl in analysis.playlists:
        cls = classifications.get(pl.mpls, "")
        lines.append(
            f"  {pl.mpls:<16} {format_duration(pl.duration_ms):>10} "
            f"{len(pl.play_items):>6}  {cls}"
        )
    lines.append("")

    # Episodes
    if analysis.episodes:
        lines.append("-" * 60)
        lines.append("Episodes")
        lines.append("-" * 60)
        for ep in analysis.episodes:
            clips = ", ".join(seg.clip_id for seg in ep.segments)
            lines.append(
                f"  Ep {ep.episode:>2}  {format_duration(ep.duration_ms):>10}  "
                f"conf={ep.confidence:.2f}  clips=[{clips}]"
            )
        lines.append("")

    # Warnings
    if analysis.warnings:
        lines.append("-" * 60)
        lines.append("Warnings")
        lines.append("-" * 60)
        for w in analysis.warnings:
            lines.append(f"  [{w.code}] {w.message}")
        lines.append("")

    return "\n".join(lines)
