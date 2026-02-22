"""Digital archive image extraction helpers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bdpl.model import DiscAnalysis, PlayItem, Playlist


@dataclass(slots=True)
class ArchiveItem:
    """One image-like entry from a digital archive playlist."""

    playlist: str
    index: int
    clip_id: str
    in_ms: float
    duration_ms: float


def _find_ffmpeg() -> str | None:
    """Return path to ffmpeg executable, or None if unavailable."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in (
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _digital_archive_playlists(analysis: DiscAnalysis) -> list[Playlist]:
    """Return playlists classified as digital archives, preserving stable order."""
    pl_by_name = {pl.mpls: pl for pl in analysis.playlists}
    names: list[str] = []

    for sf in analysis.special_features:
        if sf.category == "digital_archive":
            names.append(sf.playlist)

    classifications = analysis.analysis.get("classifications", {})
    for name, category in sorted(classifications.items()):
        if category == "digital_archive":
            names.append(name)

    seen: set[str] = set()
    result: list[Playlist] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        pl = pl_by_name.get(name)
        if pl is not None:
            result.append(pl)
    return result


def collect_archive_items(analysis: DiscAnalysis) -> list[ArchiveItem]:
    """Collect extractable archive items from digital archive playlists."""
    items: list[ArchiveItem] = []
    for pl in _digital_archive_playlists(analysis):
        for idx, pi in enumerate(pl.play_items, start=1):
            items.append(_to_archive_item(pl, pi, idx))
    return items


def _to_archive_item(pl: Playlist, pi: PlayItem, idx: int) -> ArchiveItem:
    """Build an archive item descriptor for one playlist entry."""
    return ArchiveItem(
        playlist=pl.mpls,
        index=idx,
        clip_id=pi.clip_id,
        in_ms=pi.in_time / 45.0,
        duration_ms=pi.duration_ms,
    )


def _validate_image_format(image_format: str) -> str:
    """Normalize and validate desired image extension."""
    fmt = image_format.lower()
    if fmt in {"jpg", "jpeg"}:
        return "jpg"
    if fmt == "png":
        return "png"
    raise ValueError("image_format must be one of: jpg, jpeg, png")


def _output_name(item: ArchiveItem, image_format: str) -> str:
    """Build deterministic output filename for one archive image."""
    stem = item.playlist.rsplit(".", 1)[0]
    return f"{stem}-{item.index:03d}-{item.clip_id}.{image_format}"


def _resolve_output_path(out: Path, item: ArchiveItem, image_format: str) -> Path:
    """Resolve output path and block path traversal outside out directory."""
    output = (out / _output_name(item, image_format)).resolve()
    if not output.is_relative_to(out):
        raise ValueError(f"Output path escapes target directory: {output}")
    return output


def _build_ffmpeg_cmd(
    ffmpeg: str,
    stream_file: Path,
    out_file: Path,
    in_ms: float,
    image_format: str,
) -> list[str]:
    """Build ffmpeg command to capture one frame at a timestamp."""
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{max(0.0, in_ms) / 1000.0:.3f}",
        "-i",
        str(stream_file),
        "-frames:v",
        "1",
    ]

    if image_format == "jpg":
        cmd.extend(["-q:v", "2"])

    cmd.append(str(out_file))
    return cmd


def get_digital_archive_dry_run(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    ffmpeg_path: str | None = None,
    image_format: str = "jpg",
) -> list[dict]:
    """Return the ffmpeg commands that would be run for archive extraction."""
    fmt = _validate_image_format(image_format)
    out = Path(out_dir).resolve()
    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    ffmpeg = ffmpeg_path or "ffmpeg"
    result: list[dict] = []
    for item in collect_archive_items(analysis):
        source = stream / f"{item.clip_id}.m2ts"
        output = _resolve_output_path(out, item, fmt)
        cmd = _build_ffmpeg_cmd(ffmpeg, source, output, item.in_ms, fmt)
        result.append(
            {
                "playlist": item.playlist,
                "index": item.index,
                "clip_id": item.clip_id,
                "output": str(output),
                "command": cmd,
            }
        )
    return result


def export_digital_archive_images(
    analysis: DiscAnalysis,
    out_dir: str | Path,
    stream_dir: str | Path | None = None,
    ffmpeg_path: str | None = None,
    image_format: str = "jpg",
) -> list[Path]:
    """Extract one still image for each digital archive entry.

    Uses ffmpeg to grab one frame at each play item in-time.
    """
    fmt = _validate_image_format(image_format)
    items = collect_archive_items(analysis)
    if not items:
        return []

    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if stream_dir is None:
        stream = Path(analysis.path).resolve() / "STREAM"
    else:
        stream = Path(stream_dir).resolve()

    ffmpeg = ffmpeg_path or _find_ffmpeg()
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found. Install ffmpeg or pass --ffmpeg-path.")

    created: list[Path] = []
    errors: list[str] = []
    for item in items:
        source = stream / f"{item.clip_id}.m2ts"
        output = _resolve_output_path(out, item, fmt)

        if not source.is_file():
            errors.append(f"{item.playlist} item {item.index} ({item.clip_id}): source not found")
            continue

        cmd = _build_ffmpeg_cmd(ffmpeg, source, output, item.in_ms, fmt)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except OSError as exc:
            errors.append(f"{item.playlist} item {item.index} ({item.clip_id}): {exc}")
            continue
        if result.returncode != 0:
            errors.append(
                f"{item.playlist} item {item.index} ({item.clip_id}): {result.stderr.strip()}"
            )
            continue
        created.append(output)

    if errors:
        raise RuntimeError(f"ffmpeg failed for {len(errors)} items:\n" + "\n".join(errors))

    return created
