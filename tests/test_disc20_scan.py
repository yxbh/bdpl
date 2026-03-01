"""Tests for disc20 fixture — single compilation movie with scene chapters."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc20Episodes:
    def test_episode_count(self, disc20_analysis: DiscAnalysis) -> None:
        assert len(disc20_analysis.episodes) == 1

    def test_episode_playlist(self, disc20_analysis: DiscAnalysis) -> None:
        assert disc20_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration_is_movie_length(self, disc20_analysis: DiscAnalysis) -> None:
        dur_min = disc20_analysis.episodes[0].duration_ms / 60000
        assert 100 < dur_min < 140, f"Movie duration {dur_min:.1f}min out of range"

    def test_not_chapter_split(self, disc20_analysis: DiscAnalysis) -> None:
        """Movie with 41 scene chapters must NOT be split into episodes."""
        assert len(disc20_analysis.episodes) == 1
        assert disc20_analysis.episodes[0].confidence == 1.0


class TestDisc20Specials:
    def test_special_feature_count(self, disc20_analysis: DiscAnalysis) -> None:
        assert len(disc20_analysis.special_features) == 1

    def test_special_category(self, disc20_analysis: DiscAnalysis) -> None:
        sf = disc20_analysis.special_features[0]
        assert sf.category == "extra"
        assert sf.playlist == "00003.mpls"

    def test_special_visible(self, disc20_analysis: DiscAnalysis) -> None:
        assert disc20_analysis.special_features[0].menu_visible


class TestDisc20Metadata:
    def test_disc_title(self, disc20_analysis: DiscAnalysis) -> None:
        assert disc20_analysis.disc_title == "TEST DISC 20"
