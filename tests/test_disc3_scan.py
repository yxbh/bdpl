"""Integration tests for the disc3 fixture scan results."""

from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.model import DiscAnalysis

_DISC3 = Path(__file__).parent / "fixtures" / "disc3"


@pytest.fixture
def disc3_path() -> Path:
    """Return path to bundled disc3 fixture if available."""
    if not (_DISC3 / "PLAYLIST").is_dir():
        pytest.skip("disc3 fixture not available")
    return _DISC3


def test_disc3_finds_four_episodes(disc3_path: Path) -> None:
    """Scan disc3 and verify four episodes are inferred."""
    playlists = parse_mpls_dir(disc3_path / "PLAYLIST")
    clips = parse_clpi_dir(disc3_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc3_path, playlists, clips)

    assert len(analysis.episodes) == 4


def test_disc3_episode_numbers_are_ordered(disc3_path: Path) -> None:
    """Verify inferred episode sequence is 1..4 for disc3."""
    playlists = parse_mpls_dir(disc3_path / "PLAYLIST")
    clips = parse_clpi_dir(disc3_path / "CLIPINF")
    analysis: DiscAnalysis = scan_disc(disc3_path, playlists, clips)

    assert [episode.episode for episode in analysis.episodes] == [1, 2, 3, 4]
