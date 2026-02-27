"""Tests for chapter-based episode splitting (disc2 fixture)."""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestChapterSplitting:
    def test_finds_four_episodes(self, disc2_analysis: DiscAnalysis) -> None:
        da = disc2_analysis
        assert len(da.episodes) == 4

    def test_episode_durations_reasonable(self, disc2_analysis: DiscAnalysis) -> None:
        da = disc2_analysis
        for ep in da.episodes:
            dur_min = ep.duration_ms / 60000
            assert 15 < dur_min < 35, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_episodes_are_ordered(self, disc2_analysis: DiscAnalysis) -> None:
        da = disc2_analysis
        nums = [ep.episode for ep in da.episodes]
        assert nums == [1, 2, 3, 4]

    def test_episode_segments_dont_overlap(self, disc2_analysis: DiscAnalysis) -> None:
        da = disc2_analysis
        for i in range(len(da.episodes) - 1):
            seg_a = da.episodes[i].segments[0]
            seg_b = da.episodes[i + 1].segments[0]
            assert seg_a.out_ms <= seg_b.in_ms, (
                f"Ep {i + 1} end {seg_a.out_ms} overlaps Ep {i + 2} start {seg_b.in_ms}"
            )

    def test_no_special_features(self, disc2_analysis: DiscAnalysis) -> None:
        """Disc2 is a chapter-split disc with no extras."""
        assert len(disc2_analysis.special_features) == 0

    def test_disc_title(self, disc2_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc2_analysis.disc_title == "TEST DISC 2"
