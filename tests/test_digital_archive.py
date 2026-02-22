"""Tests for digital archive classification and extraction planning."""

from pathlib import Path

from bdpl.analyze.classify import classify_playlists, is_digital_archive_playlist
from bdpl.export.digital_archive import collect_archive_items, get_digital_archive_dry_run
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
    items = [
        _mk_item(f"{i:05d}", 0.0, 40.0)
        for i in range(30)
    ]
    pl = Playlist(mpls="00003.mpls", play_items=items)
    assert is_digital_archive_playlist(pl)


def test_digital_archive_playlist_rejects_low_item_count() -> None:
    """Few short items should not trigger digital archive classification."""
    items = [
        _mk_item(f"{i:05d}", 0.0, 40.0)
        for i in range(10)
    ]
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
