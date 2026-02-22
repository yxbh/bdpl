"""Integration tests for the disc4 fixture scan results."""

from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.model import DiscAnalysis

_DISC4 = Path(__file__).parent / "fixtures" / "disc4"


@pytest.fixture
def disc4_path() -> Path:
    """Return path to bundled disc4 fixture if available."""
    if not (_DISC4 / "PLAYLIST").is_dir():
        pytest.skip("disc4 fixture not available")
    return _DISC4


def test_disc4_finds_one_episode(disc4_path: Path) -> None:
    """Scan disc4 and verify one main episode is inferred."""
    playlists = parse_mpls_dir(disc4_path / "PLAYLIST")
    clips = parse_clpi_dir(disc4_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc4_path, playlists, clips)

    assert len(analysis.episodes) == 1


def test_disc4_episode_numbers_are_ordered(disc4_path: Path) -> None:
    """Verify inferred episode sequence is [1] for disc4."""
    playlists = parse_mpls_dir(disc4_path / "PLAYLIST")
    clips = parse_clpi_dir(disc4_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc4_path, playlists, clips)

    assert [episode.episode for episode in analysis.episodes] == [1]


def test_disc4_detects_digital_archive_playlist(disc4_path: Path) -> None:
    """Verify digital archive playlist classification is present."""
    playlists = parse_mpls_dir(disc4_path / "PLAYLIST")
    clips = parse_clpi_dir(disc4_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc4_path, playlists, clips)

    classes = analysis.analysis.get("classifications", {})
    assert classes.get("00003.mpls") == "digital_archive"


def test_disc4_keeps_single_main_title_when_archive_title_exists(disc4_path: Path) -> None:
    """Guard against chapter-splitting when hints show one main + archive title."""
    playlists = parse_mpls_dir(disc4_path / "PLAYLIST")
    clips = parse_clpi_dir(disc4_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc4_path, playlists, clips)

    hints = analysis.analysis.get("disc_hints", {})
    title_playlists = hints.get("title_playlists", {})
    classes = analysis.analysis.get("classifications", {})

    assert title_playlists.get(0) == [2]
    assert title_playlists.get(1) == [3]
    assert classes.get("00003.mpls") == "digital_archive"

    assert len(analysis.episodes) == 1
    assert analysis.episodes[0].playlist == "00002.mpls"

    main = next(pl for pl in playlists if pl.mpls == "00002.mpls")
    assert abs(analysis.episodes[0].duration_ms - main.duration_ms) < 1.0
