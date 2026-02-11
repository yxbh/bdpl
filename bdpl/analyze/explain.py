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
            pl = next((p for p in analysis.playlists if p.mpls == mpls), None)
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

    # Disc hints (navigation metadata)
    hints = analysis.analysis.get("disc_hints", {})
    if hints:
        lines.append("Disc hints:")
        idx = hints.get("index", {})
        if idx:
            titles = idx.get("titles", [])
            lines.append(f"  index.bdmv: {len(titles)} title(s)")
        mo = hints.get("movie_objects", {})
        if mo:
            obj_pl = mo.get("obj_playlists", {})
            lines.append(
                f"  MovieObject.bdmv: {mo.get('count', '?')} object(s), "
                f"{len(obj_pl)} with playlist refs"
            )
        tp = hints.get("title_playlists", {})
        if tp:
            mappings = ", ".join(
                f"T{t}->{','.join(f'{p:05d}.mpls' for p in pls)}" for t, pls in sorted(tp.items())
            )
            lines.append(f"  Title→playlist: {mappings}")
        ig = hints.get("ig_menu", {})
        if ig:
            marks = ig.get("chapter_marks", [])
            parts = [f"{ig.get('hint_count', 0)} button action(s)"]
            if marks:
                parts.append(f"chapter marks={marks}")
            if ig.get("has_direct_play"):
                parts.append("has direct PlayPL")
            lines.append(f"  IG menu: {', '.join(parts)}")
        lines.append("")

    return "\n".join(lines)
