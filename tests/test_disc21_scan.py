"""Integration tests for the disc21 fixture — special disc with OVA + digital archive."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc21Episodes:
    def test_episode_count(self, disc21_analysis: DiscAnalysis) -> None:
        assert len(disc21_analysis.episodes) == 1

    def test_episode_playlist(self, disc21_analysis: DiscAnalysis) -> None:
        assert disc21_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration(self, disc21_analysis: DiscAnalysis) -> None:
        dur_min = disc21_analysis.episodes[0].duration_ms / 60000
        assert 44.0 < dur_min < 44.2, f"OVA duration {dur_min:.2f}min, expected ~44:03"


class TestDisc21Specials:
    def test_special_feature_count(self, disc21_analysis: DiscAnalysis) -> None:
        assert len(disc21_analysis.special_features) == 1

    def test_digital_archive(self, disc21_analysis: DiscAnalysis) -> None:
        sf = disc21_analysis.special_features[0]
        assert sf.category == "digital_archive"
        assert sf.playlist == "00003.mpls"

    def test_digital_archive_visible(self, disc21_analysis: DiscAnalysis) -> None:
        assert disc21_analysis.special_features[0].menu_visible


class TestDisc21Metadata:
    def test_disc_title(self, disc21_analysis: DiscAnalysis) -> None:
        assert disc21_analysis.disc_title == "TEST DISC 21"
