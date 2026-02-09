"""Tests for chapter-based episode splitting (disc2 fixture)."""
from pathlib import Path

import pytest

from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.analyze import scan_disc

_DISC2 = Path(__file__).parent / "fixtures" / "disc2"


@pytest.fixture
def disc2_path():
    if not (_DISC2 / "PLAYLIST").is_dir():
        pytest.skip("disc2 fixture not available")
    return _DISC2


class TestChapterSplitting:
    def test_finds_four_episodes(self, disc2_path):
        pls = parse_mpls_dir(disc2_path / "PLAYLIST")
        clips = parse_clpi_dir(disc2_path / "CLIPINF")
        da = scan_disc(disc2_path, pls, clips)
        assert len(da.episodes) == 4

    def test_episode_durations_reasonable(self, disc2_path):
        pls = parse_mpls_dir(disc2_path / "PLAYLIST")
        clips = parse_clpi_dir(disc2_path / "CLIPINF")
        da = scan_disc(disc2_path, pls, clips)
        for ep in da.episodes:
            dur_min = ep.duration_ms / 60000
            assert 15 < dur_min < 35, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_episodes_are_ordered(self, disc2_path):
        pls = parse_mpls_dir(disc2_path / "PLAYLIST")
        clips = parse_clpi_dir(disc2_path / "CLIPINF")
        da = scan_disc(disc2_path, pls, clips)
        nums = [ep.episode for ep in da.episodes]
        assert nums == [1, 2, 3, 4]

    def test_episode_segments_dont_overlap(self, disc2_path):
        pls = parse_mpls_dir(disc2_path / "PLAYLIST")
        clips = parse_clpi_dir(disc2_path / "CLIPINF")
        da = scan_disc(disc2_path, pls, clips)
        for i in range(len(da.episodes) - 1):
            seg_a = da.episodes[i].segments[0]
            seg_b = da.episodes[i + 1].segments[0]
            assert seg_a.out_ms <= seg_b.in_ms, (
                f"Ep {i+1} end {seg_a.out_ms} overlaps Ep {i+2} start {seg_b.in_ms}"
            )
