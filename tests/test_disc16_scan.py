"""Tests for disc16 fixture — chapter-split disc with 4 episodes and 4 specials."""

from __future__ import annotations

from collections import Counter

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc16Episodes:
    def test_episode_count(self, disc16_analysis: DiscAnalysis) -> None:
        assert len(disc16_analysis.episodes) == 4

    def test_episodes_are_ordered(self, disc16_analysis: DiscAnalysis) -> None:
        nums = [ep.episode for ep in disc16_analysis.episodes]
        assert nums == [1, 2, 3, 4]

    def test_episode_durations_reasonable(self, disc16_analysis: DiscAnalysis) -> None:
        for ep in disc16_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 15 < dur_min < 35, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_all_episodes_from_same_playlist(self, disc16_analysis: DiscAnalysis) -> None:
        for ep in disc16_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_segments_dont_overlap(self, disc16_analysis: DiscAnalysis) -> None:
        for i in range(len(disc16_analysis.episodes) - 1):
            seg_a = disc16_analysis.episodes[i].segments[0]
            seg_b = disc16_analysis.episodes[i + 1].segments[0]
            assert seg_a.out_ms <= seg_b.in_ms, (
                f"Ep {i + 1} end {seg_a.out_ms} overlaps Ep {i + 2} start {seg_b.in_ms}"
            )


class TestDisc16Specials:
    def test_special_feature_count(self, disc16_analysis: DiscAnalysis) -> None:
        assert len(disc16_analysis.special_features) == 4

    def test_special_categories(self, disc16_analysis: DiscAnalysis) -> None:
        cats = Counter(sf.category for sf in disc16_analysis.special_features)
        assert cats["extra"] == 2
        assert cats["creditless_ed"] == 2

    def test_all_specials_visible(self, disc16_analysis: DiscAnalysis) -> None:
        for sf in disc16_analysis.special_features:
            assert sf.menu_visible


class TestDisc16Metadata:
    def test_disc_title(self, disc16_analysis: DiscAnalysis) -> None:
        assert disc16_analysis.disc_title == "TEST DISC 16"
