"""Integration tests for disc5 fixture scan behavior."""

from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.model import DiscAnalysis

_DISC5 = Path(__file__).parent / "fixtures" / "disc5"


@pytest.fixture
def disc5_path() -> Path:
    """Return path to bundled disc5 fixture if available."""
    if not (_DISC5 / "PLAYLIST").is_dir():
        pytest.skip("disc5 fixture not available")
    return _DISC5


@pytest.fixture
def analysis(disc5_path: Path) -> DiscAnalysis:
    """Run full scan pipeline on the disc5 fixture."""
    playlists = parse_mpls_dir(disc5_path / "PLAYLIST")
    clips = parse_clpi_dir(disc5_path / "CLIPINF")
    return scan_disc(disc5_path, playlists, clips)


def test_disc5_finds_single_main_episode(analysis: DiscAnalysis) -> None:
    """Disc5 should infer one main title, not chapter buttons as episodes."""
    assert len(analysis.episodes) == 1
    assert analysis.episodes[0].playlist == "00001.mpls"


def test_disc5_keeps_long_special_playlist_as_extra(analysis: DiscAnalysis) -> None:
    """Long specials playlist should remain extra, not become an episode."""
    classes = analysis.analysis.get("classifications", {})
    assert classes.get("01001.mpls") == "extra"


def test_disc5_has_no_digital_archive_playlist(analysis: DiscAnalysis) -> None:
    """Disc5 does not contain an image archive playlist in this fixture."""
    classes = analysis.analysis.get("classifications", {})
    assert "digital_archive" not in classes.values()


def test_disc5_special_features_detected(analysis: DiscAnalysis) -> None:
    """Metadata-only disc5 fixture exposes 14 playlist-level specials."""
    assert len(analysis.special_features) == 14


def test_disc5_menu_visible_specials_count_is_11(analysis: DiscAnalysis) -> None:
    """Disc5 SPECIAL menu should have exactly 11 visible entries."""
    visible = [sf for sf in analysis.special_features if sf.menu_visible]
    assert len(visible) == 11


def test_disc5_non_visible_specials_count_is_3(analysis: DiscAnalysis) -> None:
    """Disc5 should have three hidden/non-visible utility specials."""
    hidden = [sf for sf in analysis.special_features if not sf.menu_visible]
    assert len(hidden) == 3
