"""Tests for disc15 fixture — chapter-split disc with 4 episodes, no specials."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc15Episodes:
    def test_episode_count(self, disc15_analysis: DiscAnalysis) -> None:
        assert len(disc15_analysis.episodes) == 4

    def test_episodes_are_ordered(self, disc15_analysis: DiscAnalysis) -> None:
        nums = [ep.episode for ep in disc15_analysis.episodes]
        assert nums == [1, 2, 3, 4]

    def test_episode_durations_reasonable(self, disc15_analysis: DiscAnalysis) -> None:
        for ep in disc15_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 15 < dur_min < 35, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_all_episodes_from_same_playlist(self, disc15_analysis: DiscAnalysis) -> None:
        for ep in disc15_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_segments_dont_overlap(self, disc15_analysis: DiscAnalysis) -> None:
        for i in range(len(disc15_analysis.episodes) - 1):
            seg_a = disc15_analysis.episodes[i].segments[0]
            seg_b = disc15_analysis.episodes[i + 1].segments[0]
            assert seg_a.out_ms <= seg_b.in_ms, (
                f"Ep {i + 1} end {seg_a.out_ms} overlaps Ep {i + 2} start {seg_b.in_ms}"
            )


class TestDisc15Specials:
    def test_no_special_features(self, disc15_analysis: DiscAnalysis) -> None:
        assert len(disc15_analysis.special_features) == 0


class TestDisc15Metadata:
    def test_disc_title(self, disc15_analysis: DiscAnalysis) -> None:
        assert disc15_analysis.disc_title == "TEST DISC 15"
