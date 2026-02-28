"""Tests for disc18 fixture — single movie with 2 specials."""

from __future__ import annotations

from collections import Counter

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc18Episodes:
    def test_episode_count(self, disc18_analysis: DiscAnalysis) -> None:
        """Single movie should not be chapter-split."""
        assert len(disc18_analysis.episodes) == 1

    def test_episode_playlist(self, disc18_analysis: DiscAnalysis) -> None:
        assert disc18_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration_reasonable(self, disc18_analysis: DiscAnalysis) -> None:
        dur_min = disc18_analysis.episodes[0].duration_ms / 60000
        assert 40 < dur_min < 65, f"Movie duration {dur_min:.1f}min out of range"


class TestDisc18Specials:
    def test_special_feature_count(self, disc18_analysis: DiscAnalysis) -> None:
        assert len(disc18_analysis.special_features) == 2

    def test_special_categories(self, disc18_analysis: DiscAnalysis) -> None:
        cats = Counter(sf.category for sf in disc18_analysis.special_features)
        assert cats["extra"] == 1
        assert cats["creditless_ed"] == 1

    def test_all_specials_visible(self, disc18_analysis: DiscAnalysis) -> None:
        for sf in disc18_analysis.special_features:
            assert sf.menu_visible


class TestDisc18Metadata:
    def test_disc_title(self, disc18_analysis: DiscAnalysis) -> None:
        assert disc18_analysis.disc_title == "TEST DISC 18"
