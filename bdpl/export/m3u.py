"""M3U playlist generation for debugging."""

from __future__ import annotations

from pathlib import Path

from bdpl.model import DiscAnalysis


def export_m3u(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
) -> list[Path]:
    """Generate one .m3u file per episode.

    If stream_dir is None, derive it from analysis.path + /STREAM.
    Each m3u references the m2ts files with start/duration for each segment.
    Returns list of created file paths.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if stream_dir is None:
        stream = Path(analysis.path) / "STREAM"
    else:
        stream = Path(stream_dir)

    # Build a map of clip_id -> first in_time seen, so we can compute
    # the PTS base for each m2ts file and emit VLC-relative seek times.
    clip_pts_base: dict[str, float] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            ms = pi.in_time / 45.0  # raw 45 kHz ticks → ms
            if pi.clip_id not in clip_pts_base or ms < clip_pts_base[pi.clip_id]:
                clip_pts_base[pi.clip_id] = ms

    # Resolve to absolute so relative-path math is reliable.
    out = out.resolve()
    stream = stream.resolve()

    created: list[Path] = []
    for ep in analysis.episodes:
        filename = f"Episode_{ep.episode:02d}.m3u"
        filepath = out / filename
        lines = ["#EXTM3U"]
        for seg in ep.segments:
            dur_s = seg.duration_ms / 1000.0
            m2ts = stream / f"{seg.clip_id}.m2ts"
            # Path relative to the directory containing the .m3u file
            try:
                rel = m2ts.relative_to(out)
            except ValueError:
                # Not a sub-path — use os.path.relpath for arbitrary trees
                import os

                rel = Path(os.path.relpath(m2ts, out))
            # VLC normalises m2ts PTS to start at 0, so subtract the
            # clip's base PTS to get a VLC-relative seek position.
            base_ms = clip_pts_base.get(seg.clip_id, seg.in_ms)
            start_s = (seg.in_ms - base_ms) / 1000.0
            stop_s = start_s + dur_s
            lines.append(f"#EXTINF:{dur_s:.3f},{seg.clip_id} ({seg.label})")
            if start_s > 0.5:
                lines.append(f"#EXTVLCOPT:start-time={start_s:.3f}")
            if stop_s < dur_s * 2:
                lines.append(f"#EXTVLCOPT:stop-time={stop_s:.3f}")
            lines.append(str(rel))
        filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
        created.append(filepath)

    return created
