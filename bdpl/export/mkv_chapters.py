"""Ordered-chapters MKV generation for debug playback.

Creates a tiny MKV per episode that references external m2ts segments
via Matroska chapter linking — no media data is copied.  VLC / mpv will
play these with chapters, track names, and (mostly) seamless joins.

Requires ``mkvmerge`` (MKVToolNix) on PATH or specified explicitly.
"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from bdpl.model import DiscAnalysis, Playlist, SpecialFeature, ticks_to_ms

# ── helpers ──────────────────────────────────────────────────────────


def _find_mkvmerge() -> str | None:
    """Return path to mkvmerge if found, else None."""
    found = shutil.which("mkvmerge")
    if found:
        return found
    # Common Windows install locations
    for candidate in (
        Path(r"C:\Program Files\MKVToolNix\mkvmerge.exe"),
        Path(r"C:\Program Files (x86)\MKVToolNix\mkvmerge.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _ns(ms: float) -> int:
    """Milliseconds → Matroska ChapterTimeStart nanoseconds."""
    return max(0, int(ms * 1_000_000))


def _fmt_time(ms: float) -> str:
    """Format ms as HH:MM:SS.nnnnnnnnn for Matroska XML chapters."""
    total_s = max(0.0, ms / 1000.0)
    h = int(total_s // 3600)
    m = int((total_s % 3600) // 60)
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:012.9f}"


def _chapters_for_episode(
    analysis: DiscAnalysis,
    ep_idx: int,
) -> list[tuple[float, str]]:
    """Return [(relative_ms, label), ...] chapter points for one episode.

    Computes chapter timestamps relative to the start of the episode's
    first segment by matching MPLS chapter marks to play-item boundaries.
    """
    ep = analysis.episodes[ep_idx]
    chapters: list[tuple[float, str]] = []

    # Find the playlist that owns this episode
    pl: Playlist | None = None
    for p in analysis.playlists:
        if p.mpls == ep.playlist:
            pl = p
            break
    if pl is None or not pl.chapters:
        # Fallback: single chapter at 0
        return [(0.0, f"Episode {ep.episode}")]

    # Determine if this is a chapter-split episode (sub-range of a play item)
    # by checking if the episode is significantly shorter than its play item
    is_chapter_split = False
    if len(ep.segments) == 1:
        seg = ep.segments[0]
        for pi in pl.play_items:
            if pi.clip_id == seg.clip_id:
                if ep.duration_ms < pi.duration_ms * 0.95:
                    is_chapter_split = True
                break

    if is_chapter_split:
        # Chapter-split: filter MPLS chapters that fall within this
        # episode's time range (using absolute PTS timestamps)
        seg = ep.segments[0]
        for ch in pl.chapters:
            ch_ms = ticks_to_ms(ch.timestamp)
            if ch_ms >= seg.in_ms - 100 and ch_ms < seg.out_ms - 100:
                rel_ms = max(0.0, ch_ms - seg.in_ms)
                chapters.append((rel_ms, f"Chapter {len(chapters) + 1}"))
    else:
        # Standard path: match chapters to play items by index
        # Build a set of clip_ids for this episode's segments
        [seg.clip_id for seg in ep.segments]

        # Map play-item index → clip_id for matching chapters
        {i: pi.clip_id for i, pi in enumerate(pl.play_items)}

        # Accumulate offset as we walk through episode segments in order.
        seg_offset_ms = 0.0
        for seg in ep.segments:
            for pi_idx, pi in enumerate(pl.play_items):
                if pi.clip_id != seg.clip_id:
                    continue
                pi_in_ms = ticks_to_ms(pi.in_time)
                if abs(pi_in_ms - seg.in_ms) > 1000:
                    continue
                for ch in pl.chapters:
                    if ch.play_item_ref != pi_idx:
                        continue
                    ch_ms = ticks_to_ms(ch.timestamp)
                    rel_ms = seg_offset_ms + (ch_ms - pi_in_ms)
                    if rel_ms < -500:
                        continue
                    rel_ms = max(0.0, rel_ms)
                    chapters.append((rel_ms, f"Chapter {len(chapters) + 1}"))
                break
            seg_offset_ms += seg.duration_ms

    if not chapters:
        chapters.append((0.0, f"Episode {ep.episode}"))

    # Deduplicate and sort
    seen: set[int] = set()
    unique: list[tuple[float, str]] = []
    for ms, label in sorted(chapters):
        rounded = round(ms)
        if rounded not in seen:
            seen.add(rounded)
            unique.append((ms, label))
    return unique


# ── XML chapter file generation ──────────────────────────────────────


def _build_chapter_xml(chapters: list[tuple[float, str]]) -> str:
    """Build a Matroska XML chapters string."""
    root = ET.Element("Chapters")
    edition = ET.SubElement(root, "EditionEntry")
    ET.SubElement(edition, "EditionFlagDefault").text = "1"
    ET.SubElement(edition, "EditionFlagOrdered").text = "0"

    for ms, label in chapters:
        atom = ET.SubElement(edition, "ChapterAtom")
        ET.SubElement(atom, "ChapterTimeStart").text = _fmt_time(ms)
        disp = ET.SubElement(atom, "ChapterDisplay")
        ET.SubElement(disp, "ChapterString").text = label
        ET.SubElement(disp, "ChapterLanguage").text = "und"

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


# ── public API ───────────────────────────────────────────────────────


def export_chapter_mkv(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    mkvmerge_path: str | None = None,
    dry_run: bool = False,
    on_progress: Callable[[int, int, str], None] | None = None,
    pattern: str = "{name} - S01E{ep:02d}.mkv",
) -> list[Path]:
    """Generate one lightweight MKV per episode with chapters and track names.

    Each MKV directly muxes the source m2ts (no transcoding) and embeds
    chapter marks from the MPLS data.

    *on_progress(current, total, message)* is called before each episode
    to allow callers to update a progress bar / spinner.

    Returns list of created MKV paths (empty list on dry-run).
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    mkvmerge = mkvmerge_path or _find_mkvmerge()
    if mkvmerge is None and not dry_run:
        raise RuntimeError(
            "mkvmerge not found. Install MKVToolNix or pass --mkvmerge-path.\n"
            "  https://mkvtoolnix.download/"
        )

    # Build clip PTS base map (same logic as m3u export)
    clip_pts_base: dict[str, float] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            ms = ticks_to_ms(pi.in_time)
            if pi.clip_id not in clip_pts_base or ms < clip_pts_base[pi.clip_id]:
                clip_pts_base[pi.clip_id] = ms

    # Collect stream metadata for track naming
    clip_streams: dict[str, list] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            if pi.clip_id not in clip_streams and pi.streams:
                clip_streams[pi.clip_id] = pi.streams

    name = _disc_name(analysis)
    created: list[Path] = []
    commands: list[list[str]] = []
    total = len(analysis.episodes)

    for ep_idx, ep in enumerate(analysis.episodes):
        mkv_name = pattern.format(ep=ep.episode, name=name)
        mkv_path = out / mkv_name

        if on_progress is not None:
            on_progress(ep_idx + 1, total, mkv_name)

        # Build chapters
        chapters = _chapters_for_episode(analysis, ep_idx)
        chapter_xml = _build_chapter_xml(chapters)
        chapter_file = out / f".ep{ep.episode:02d}_chapters.xml"

        # Collect m2ts source files for this episode
        m2ts_files = [stream / f"{seg.clip_id}.m2ts" for seg in ep.segments]

        # Determine if we need time-based splitting (chapter-based episodes
        # reference a sub-range of a large m2ts file)
        needs_split = (
            len(ep.segments) == 1
            and ep.segments[0].clip_id in clip_pts_base
            and ep.duration_ms
            < 0.95
            * sum(
                pi.duration_ms
                for pl in analysis.playlists
                for pi in pl.play_items
                if pi.clip_id == ep.segments[0].clip_id
            )
        )

        # Build mkvmerge command
        cmd: list[str] = [mkvmerge or "mkvmerge", "-o", str(mkv_path)]

        # If episode is a sub-range of a single m2ts, use --split parts:
        if needs_split:
            seg = ep.segments[0]
            base_ms = clip_pts_base[seg.clip_id]
            start_ms = seg.in_ms - base_ms
            end_ms = seg.out_ms - base_ms
            start_ts = _fmt_time(start_ms)
            end_ts = _fmt_time(end_ms)
            cmd.extend(["--split", f"parts:{start_ts}-{end_ts}"])

        # Add chapters
        cmd.extend(["--chapters", str(chapter_file)])

        # Title
        cmd.extend(["--title", f"Episode {ep.episode}"])

        # Add track names from stream metadata
        for i, m2ts in enumerate(m2ts_files):
            seg = ep.segments[i]
            streams = clip_streams.get(seg.clip_id, [])

            # Track-name options for this input
            track_opts: list[str] = []
            for s in streams:
                if s.lang:
                    track_opts.extend(["--language", f"{s.pid}:{s.lang}"])
                name = ""
                if s.codec and s.lang:
                    name = f"{s.lang.upper()} {s.codec}"
                elif s.codec:
                    name = s.codec
                if name:
                    track_opts.extend(["--track-name", f"{s.pid}:{name}"])

            cmd.extend(track_opts)

            if i > 0:
                cmd.append("+")  # append/concatenate
            cmd.append(str(m2ts))

        commands.append(cmd)

        if dry_run:
            continue

        # Write chapter file
        chapter_file.write_text(chapter_xml, encoding="utf-8")

        # Run mkvmerge
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        # mkvmerge returns 0 (success) or 1 (warnings) or 2 (error)
        if result.returncode > 1:
            raise RuntimeError(f"mkvmerge failed for episode {ep.episode}:\n{result.stderr}")

        # Clean up chapter file
        chapter_file.unlink(missing_ok=True)
        created.append(mkv_path)

    return created


def get_dry_run_commands(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    pattern: str = "{name} - S01E{ep:02d}.mkv",
) -> list[dict]:
    """Return the mkvmerge commands that would be run, without executing.

    Returns list of dicts with 'episode', 'output', 'command', 'chapters_xml'.
    """
    out = Path(out_dir).resolve()
    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    # Build clip PTS base map for split calculations
    clip_pts_base: dict[str, float] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            ms = ticks_to_ms(pi.in_time)
            if pi.clip_id not in clip_pts_base or ms < clip_pts_base[pi.clip_id]:
                clip_pts_base[pi.clip_id] = ms

    name = _disc_name(analysis)
    result = []
    for ep_idx, ep in enumerate(analysis.episodes):
        chapters = _chapters_for_episode(analysis, ep_idx)
        chapter_xml = _build_chapter_xml(chapters)
        mkv_path = out / pattern.format(ep=ep.episode, name=name)

        m2ts_files = [stream / f"{seg.clip_id}.m2ts" for seg in ep.segments]

        # Check if this episode needs time-based splitting
        needs_split = (
            len(ep.segments) == 1
            and ep.segments[0].clip_id in clip_pts_base
            and ep.duration_ms
            < 0.95
            * sum(
                pi.duration_ms
                for pl in analysis.playlists
                for pi in pl.play_items
                if pi.clip_id == ep.segments[0].clip_id
            )
        )

        cmd_parts = ["mkvmerge", "-o", str(mkv_path)]
        if needs_split:
            seg = ep.segments[0]
            base_ms = clip_pts_base[seg.clip_id]
            start_ts = _fmt_time(seg.in_ms - base_ms)
            end_ts = _fmt_time(seg.out_ms - base_ms)
            cmd_parts.extend(["--split", f"parts:{start_ts}-{end_ts}"])
        cmd_parts.extend(["--title", f"Episode {ep.episode}"])
        for i, m2ts in enumerate(m2ts_files):
            if i > 0:
                cmd_parts.append("+")
            cmd_parts.append(str(m2ts))

        result.append(
            {
                "episode": ep.episode,
                "output": str(mkv_path),
                "command": cmd_parts,
                "chapters_xml": chapter_xml,
            }
        )

    return result


# ── Special features export ──────────────────────────────────────────


def _disc_name(analysis: DiscAnalysis) -> str:
    """Derive a disc name from the BDMV parent folder."""
    bdmv = Path(analysis.path).resolve()
    # BDMV/ is typically inside a disc folder like UCG_0080_D1/BDMV
    parent = bdmv.parent
    if parent.name and parent.name != bdmv.anchor:
        return parent.name
    return bdmv.name


def _specials_filename(sf: SpecialFeature, pattern: str, name: str = "") -> str:
    """Generate output filename for a special feature."""
    return pattern.format(
        idx=sf.index,
        category=sf.category,
        name=name,
    )


def _build_specials_cmd(
    sf: SpecialFeature,
    mkv_path: Path,
    stream: Path,
    pl: Playlist,
    clip_pts_base: dict[str, float],
    mkvmerge: str,
) -> list[str]:
    """Build the mkvmerge command for one special feature."""
    m2ts = stream / f"{pl.play_items[0].clip_id}.m2ts"
    cmd: list[str] = [mkvmerge, "-o", str(mkv_path)]

    # Chapter-split: use --split parts: for sub-range of playlist
    if sf.chapter_start is not None and pl.chapters and len(pl.chapters) > 1:
        ch_times = [ticks_to_ms(ch.timestamp) for ch in pl.chapters]
        clip_id = pl.play_items[0].clip_id
        base_ms = clip_pts_base.get(clip_id, 0.0)

        if sf.chapter_start < len(ch_times):
            start_ms = ch_times[sf.chapter_start] - base_ms
            end_ms = start_ms + sf.duration_ms
            cmd.extend(["--split", f"parts:{_fmt_time(start_ms)}-{_fmt_time(end_ms)}"])

    cmd.extend(["--title", f"{sf.category} {sf.index}"])
    cmd.append(str(m2ts))
    return cmd


def export_specials_mkv(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    mkvmerge_path: str | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
    pattern: str = "{name} - S00E{idx:02d} - {category}.mkv",
) -> list[Path]:
    """Generate one MKV per special feature.

    Returns list of created MKV paths.
    """
    if not analysis.special_features:
        return []

    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    mkvmerge = mkvmerge_path or _find_mkvmerge()
    if mkvmerge is None:
        raise RuntimeError("mkvmerge not found. Install MKVToolNix or pass --mkvmerge-path.")

    # Build clip PTS base map
    clip_pts_base: dict[str, float] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            ms = ticks_to_ms(pi.in_time)
            if pi.clip_id not in clip_pts_base or ms < clip_pts_base[pi.clip_id]:
                clip_pts_base[pi.clip_id] = ms

    name = _disc_name(analysis)
    pl_by_name = {pl.mpls: pl for pl in analysis.playlists}
    created: list[Path] = []
    total = len(analysis.special_features)

    for sf in analysis.special_features:
        pl = pl_by_name.get(sf.playlist)
        if pl is None:
            continue

        mkv_name = _specials_filename(sf, pattern, name)
        mkv_path = out / mkv_name

        if on_progress is not None:
            on_progress(sf.index, total, mkv_name)

        cmd = _build_specials_cmd(sf, mkv_path, stream, pl, clip_pts_base, mkvmerge)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode > 1:
            raise RuntimeError(f"mkvmerge failed for special {sf.index}:\n{result.stderr}")
        created.append(mkv_path)

    return created


def get_specials_dry_run(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    pattern: str = "{name} - S00E{idx:02d} - {category}.mkv",
) -> list[dict]:
    """Return the mkvmerge commands for special features without executing."""
    if not analysis.special_features:
        return []

    out = Path(out_dir).resolve()
    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    clip_pts_base: dict[str, float] = {}
    for pl in analysis.playlists:
        for pi in pl.play_items:
            ms = ticks_to_ms(pi.in_time)
            if pi.clip_id not in clip_pts_base or ms < clip_pts_base[pi.clip_id]:
                clip_pts_base[pi.clip_id] = ms

    name = _disc_name(analysis)
    pl_by_name = {pl.mpls: pl for pl in analysis.playlists}
    result = []

    for sf in analysis.special_features:
        pl = pl_by_name.get(sf.playlist)
        if pl is None:
            continue

        mkv_name = _specials_filename(sf, pattern, name)
        mkv_path = out / mkv_name
        cmd = _build_specials_cmd(sf, mkv_path, stream, pl, clip_pts_base, "mkvmerge")

        result.append(
            {
                "index": sf.index,
                "category": sf.category,
                "output": str(mkv_path),
                "command": cmd,
            }
        )

    return result
