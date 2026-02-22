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
from tests.builders import (
    build_disc_analysis,
    build_play_item,
    build_playlist,
    build_special_feature,
)


def test_digital_archive_playlist_detected_from_structure() -> None:
    """Many ultra-short unique items should be classified as digital archive shape."""
    items = [build_play_item(f"{i:05d}", 0.0, 0.04) for i in range(30)]
    pl = build_playlist("00003.mpls", items)
    assert is_digital_archive_playlist(pl)


def test_digital_archive_playlist_rejects_low_item_count() -> None:
    """Few short items should not trigger digital archive classification."""
    items = [build_play_item(f"{i:05d}", 0.0, 0.04) for i in range(10)]
    pl = build_playlist("00003.mpls", items)
    assert not is_digital_archive_playlist(pl)


def test_digital_archive_playlist_accepts_boundary_thresholds() -> None:
    """Boundary case: exactly minimum item count and unique ratio should pass."""
    # 20 items total, 16 unique -> unique ratio 0.8
    clip_ids = [f"{i:05d}" for i in range(16)] + [f"{i:05d}" for i in range(4)]
    items = [build_play_item(clip_id, 0.0, 0.04) for clip_id in clip_ids]
    pl = build_playlist("00003.mpls", items)
    assert is_digital_archive_playlist(pl)


def test_digital_archive_playlist_rejects_low_unique_ratio() -> None:
    """Boundary case: unique ratio below threshold should fail."""
    # 20 items total, 15 unique -> unique ratio 0.75
    clip_ids = [f"{i:05d}" for i in range(15)] + ["00000"] * 5
    items = [build_play_item(clip_id, 0.0, 0.04) for clip_id in clip_ids]
    pl = build_playlist("00003.mpls", items)
    assert not is_digital_archive_playlist(pl)


def test_classify_playlists_labels_digital_archive() -> None:
    """Playlist classifier should emit digital_archive category for matching shape."""
    archive_items = [build_play_item(f"{i:05d}", 0.0, 0.042) for i in range(24)]
    extra_items = [build_play_item("99999", 0.0, 90.0)]
    playlists = [
        build_playlist("00003.mpls", archive_items),
        build_playlist("00004.mpls", extra_items),
    ]

    classes = classify_playlists(playlists, play_all=[])
    assert classes["00003.mpls"] == "digital_archive"


def test_digital_archive_dry_run_generates_ffmpeg_commands() -> None:
    """Dry-run should return ffmpeg plans for each archive item."""
    archive_items = [build_play_item(f"{i:05d}", 0.0, 0.042) for i in range(3)]
    archive_pl = build_playlist("00003.mpls", archive_items)
    analysis = build_disc_analysis(
        path=Path("C:/disc/BDMV"),
        playlists=[archive_pl],
        classifications={"00003.mpls": "digital_archive"},
    )

    items = collect_archive_items(analysis)
    assert len(items) == 3

    plans = get_digital_archive_dry_run(analysis, out_dir="./DigitalArchive", image_format="png")
    assert len(plans) == 3
    assert plans[0]["command"][0] == "ffmpeg"
    assert plans[0]["command"][-1].endswith(".png")


def test_digital_archive_dry_run_blocks_output_path_traversal() -> None:
    """Malicious clip IDs must not be able to escape output directory."""
    archive_pl = build_playlist("00003.mpls", [build_play_item("/../../x", 0.0, 0.042)])
    analysis = build_disc_analysis(
        path=Path("C:/disc/BDMV"),
        playlists=[archive_pl],
        classifications={"00003.mpls": "digital_archive"},
    )

    with pytest.raises(ValueError, match="escapes target directory"):
        get_digital_archive_dry_run(analysis, out_dir="./DigitalArchive")


def test_digital_archive_export_collects_partial_failures(tmp_path: Path, monkeypatch) -> None:
    """Extraction should continue and report all failed items in one error."""
    stream = tmp_path / "STREAM"
    stream.mkdir(parents=True)
    (stream / "00001.m2ts").write_bytes(b"a")
    (stream / "00002.m2ts").write_bytes(b"b")

    archive_pl = build_playlist(
        "00003.mpls",
        [build_play_item("00001", 0.0, 0.042), build_play_item("00002", 0.0, 0.042)],
    )
    analysis = build_disc_analysis(
        path=tmp_path / "BDMV",
        playlists=[archive_pl],
        classifications={"00003.mpls": "digital_archive"},
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


def test_collect_archive_items_visible_only_filters_hidden() -> None:
    """Visible-only mode should keep only archive playlists marked menu-visible."""
    visible_pl = build_playlist("00003.mpls", [build_play_item("00001", 0.0, 0.042)])
    hidden_pl = build_playlist("00004.mpls", [build_play_item("00002", 0.0, 0.042)])
    analysis = build_disc_analysis(
        path=Path("C:/disc/BDMV"),
        playlists=[visible_pl, hidden_pl],
        classifications={
            "00003.mpls": "digital_archive",
            "00004.mpls": "digital_archive",
        },
        special_features=[
            build_special_feature(
                index=1,
                playlist="00003.mpls",
                duration_ms=42.0,
                category="digital_archive",
                menu_visible=True,
            ),
            build_special_feature(
                index=2,
                playlist="00004.mpls",
                duration_ms=42.0,
                category="digital_archive",
                menu_visible=False,
            ),
        ],
    )

    all_items = collect_archive_items(analysis)
    visible_items = collect_archive_items(analysis, visible_only=True)

    assert len(all_items) == 2
    assert len(visible_items) == 1
    assert visible_items[0].playlist == "00003.mpls"
