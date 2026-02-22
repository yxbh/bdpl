"""Tests for digital archive classification and extraction planning."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from bdpl.analyze.classify import classify_playlists, is_digital_archive_playlist
from bdpl.export.digital_archive import (
    collect_archive_items,
    export_digital_archive_images,
    get_digital_archive_dry_run,
)
from bdpl.model import DiscAnalysis, PlayItem, Playlist


def _mk_item(clip_id: str, in_ms: float, out_ms: float) -> PlayItem:
    """Build a PlayItem with minimal fields for classification tests."""
    return PlayItem(
        clip_id=clip_id,
        m2ts=f"{clip_id}.m2ts",
        in_time=int(in_ms * 45),
        out_time=int(out_ms * 45),
        connection_condition=0,
        streams=[],
    )


def test_digital_archive_playlist_detected_from_structure() -> None:
    """Many ultra-short unique items should be classified as digital archive shape."""
    items = [_mk_item(f"{i:05d}", 0.0, 40.0) for i in range(30)]
    pl = Playlist(mpls="00003.mpls", play_items=items)
    assert is_digital_archive_playlist(pl)


def test_digital_archive_playlist_rejects_low_item_count() -> None:
    """Few short items should not trigger digital archive classification."""
    items = [_mk_item(f"{i:05d}", 0.0, 40.0) for i in range(10)]
    pl = Playlist(mpls="00003.mpls", play_items=items)
    assert not is_digital_archive_playlist(pl)


def test_digital_archive_playlist_accepts_boundary_thresholds() -> None:
    """Boundary case: exactly minimum item count and unique ratio should pass."""
    # 20 items total, 16 unique -> unique ratio 0.8
    clip_ids = [f"{i:05d}" for i in range(16)] + [f"{i:05d}" for i in range(4)]
    items = [_mk_item(clip_id, 0.0, 40.0) for clip_id in clip_ids]
    pl = Playlist(mpls="00003.mpls", play_items=items)
    assert is_digital_archive_playlist(pl)


def test_digital_archive_playlist_rejects_low_unique_ratio() -> None:
    """Boundary case: unique ratio below threshold should fail."""
    # 20 items total, 15 unique -> unique ratio 0.75
    clip_ids = [f"{i:05d}" for i in range(15)] + ["00000"] * 5
    items = [_mk_item(clip_id, 0.0, 40.0) for clip_id in clip_ids]
    pl = Playlist(mpls="00003.mpls", play_items=items)
    assert not is_digital_archive_playlist(pl)


def test_classify_playlists_labels_digital_archive() -> None:
    """Playlist classifier should emit digital_archive category for matching shape."""
    archive_items = [_mk_item(f"{i:05d}", 0.0, 42.0) for i in range(24)]
    extra_items = [_mk_item("99999", 0.0, 90_000.0)]
    playlists = [
        Playlist(mpls="00003.mpls", play_items=archive_items),
        Playlist(mpls="00004.mpls", play_items=extra_items),
    ]

    classes = classify_playlists(playlists, play_all=[])
    assert classes["00003.mpls"] == "digital_archive"


def test_digital_archive_dry_run_generates_ffmpeg_commands() -> None:
    """Dry-run should return ffmpeg plans for each archive item."""
    archive_items = [_mk_item(f"{i:05d}", 0.0, 42.0) for i in range(3)]
    archive_pl = Playlist(mpls="00003.mpls", play_items=archive_items)
    analysis = DiscAnalysis(
        path=str(Path("C:/disc/BDMV")),
        playlists=[archive_pl],
        clips={},
        episodes=[],
        warnings=[],
        analysis={"classifications": {"00003.mpls": "digital_archive"}},
    )

    items = collect_archive_items(analysis)
    assert len(items) == 3

    plans = get_digital_archive_dry_run(analysis, out_dir="./DigitalArchive", image_format="png")
    assert len(plans) == 3
    assert plans[0]["command"][0] == "ffmpeg"
    assert plans[0]["command"][-1].endswith(".png")


def test_digital_archive_dry_run_blocks_output_path_traversal() -> None:
    """Malicious clip IDs must not be able to escape output directory."""
    archive_pl = Playlist(mpls="00003.mpls", play_items=[_mk_item("/../../x", 0.0, 42.0)])
    analysis = DiscAnalysis(
        path=str(Path("C:/disc/BDMV")),
        playlists=[archive_pl],
        clips={},
        episodes=[],
        warnings=[],
        analysis={"classifications": {"00003.mpls": "digital_archive"}},
    )

    with pytest.raises(ValueError, match="escapes target directory"):
        get_digital_archive_dry_run(analysis, out_dir="./DigitalArchive")


def test_digital_archive_export_collects_partial_failures(tmp_path: Path, monkeypatch) -> None:
    """Extraction should continue and report all failed items in one error."""
    stream = tmp_path / "STREAM"
    stream.mkdir(parents=True)
    (stream / "00001.m2ts").write_bytes(b"a")
    (stream / "00002.m2ts").write_bytes(b"b")

    archive_pl = Playlist(
        mpls="00003.mpls",
        play_items=[_mk_item("00001", 0.0, 42.0), _mk_item("00002", 0.0, 42.0)],
    )
    analysis = DiscAnalysis(
        path=str(tmp_path / "BDMV"),
        playlists=[archive_pl],
        clips={},
        episodes=[],
        warnings=[],
        analysis={"classifications": {"00003.mpls": "digital_archive"}},
    )

    def _fake_run(cmd, capture_output, text):
        if any("00002.m2ts" in str(part) for part in cmd):
            return SimpleNamespace(returncode=1, stderr="boom")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("bdpl.export.digital_archive.subprocess.run", _fake_run)

    with pytest.raises(RuntimeError, match="failed for 1 items"):
        export_digital_archive_images(
            analysis,
            out_dir=tmp_path / "out",
            stream_dir=stream,
            ffmpeg_path="ffmpeg",
        )
