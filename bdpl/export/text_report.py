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
            f"  {pl.mpls:<16} {format_duration(pl.duration_ms):>10} {len(pl.play_items):>6}  {cls}"
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

    # Special Features
    if analysis.special_features:
        visible_count = sum(1 for sf in analysis.special_features if sf.menu_visible)
        lines.append("-" * 60)
        lines.append(
            f"Special Features ({len(analysis.special_features)} total, {visible_count} visible)"
        )
        lines.append("-" * 60)
        for sf in analysis.special_features:
            ch_str = f"  ch.{sf.chapter_start}" if sf.chapter_start is not None else ""
            vis_str = "visible" if sf.menu_visible else "hidden"
            lines.append(
                f"  {sf.index:>2}. {sf.playlist}{ch_str}"
                f"  {format_duration(sf.duration_ms):>10}  {sf.category}  [{vis_str}]"
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

    # Disc hints
    hints = analysis.analysis.get("disc_hints", {})
    if hints:
        lines.append("-" * 60)
        lines.append("Disc Hints")
        lines.append("-" * 60)
        idx = hints.get("index", {})
        if idx:
            titles = idx.get("titles", [])
            lines.append(f"  index.bdmv:       {len(titles)} title(s)")
        mo = hints.get("movie_objects", {})
        if mo:
            obj_pl = mo.get("obj_playlists", {})
            lines.append(
                f"  MovieObject.bdmv: {mo.get('count', '?')} object(s), "
                f"{len(obj_pl)} with playlist refs"
            )
        tp = hints.get("title_playlists", {})
        if tp:
            for t, pls in sorted(tp.items()):
                pl_str = ", ".join(f"{p:05d}.mpls" for p in pls)
                lines.append(f"    Title {t} -> {pl_str}")
        ig = hints.get("ig_menu", {})
        if ig:
            marks = ig.get("chapter_marks", [])
            parts = [f"{ig.get('hint_count', 0)} button action(s)"]
            if marks:
                parts.append(f"chapter marks={marks}")
            if ig.get("has_direct_play"):
                parts.append("direct PlayPL")
            lines.append(f"  IG menu:          {', '.join(parts)}")
        lines.append("")

    return "\n".join(lines)
