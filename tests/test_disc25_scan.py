"""Integration tests for the disc25 fixture — special disc with OVA + digital archive."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc25Episodes:
    def test_episode_count(self, disc25_analysis: DiscAnalysis) -> None:
        assert len(disc25_analysis.episodes) == 1

    def test_episode_playlist(self, disc25_analysis: DiscAnalysis) -> None:
        assert disc25_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration(self, disc25_analysis: DiscAnalysis) -> None:
        dur_min = disc25_analysis.episodes[0].duration_ms / 60000
        assert 43 < dur_min < 45, f"OVA duration {dur_min:.1f}min, expected ~44min"


class TestDisc25Specials:
    def test_special_feature_count(self, disc25_analysis: DiscAnalysis) -> None:
        assert len(disc25_analysis.special_features) == 1

    def test_digital_archive(self, disc25_analysis: DiscAnalysis) -> None:
        sf = disc25_analysis.special_features[0]
        assert sf.category == "digital_archive"
        assert sf.playlist == "00003.mpls"


class TestDisc25Metadata:
    def test_disc_title(self, disc25_analysis: DiscAnalysis) -> None:
        assert disc25_analysis.disc_title == "TEST DISC 25"
