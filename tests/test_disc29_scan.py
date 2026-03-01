"""Integration tests for the disc29 fixture — special disc with OVA + digital archives."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc29Episodes:
    def test_episode_count(self, disc29_analysis: DiscAnalysis) -> None:
        assert len(disc29_analysis.episodes) == 1

    def test_episode_playlist(self, disc29_analysis: DiscAnalysis) -> None:
        assert disc29_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration(self, disc29_analysis: DiscAnalysis) -> None:
        dur_min = disc29_analysis.episodes[0].duration_ms / 60000
        assert 43 < dur_min < 45, f"OVA duration {dur_min:.1f}min, expected ~44min"


class TestDisc29Specials:
    def test_special_feature_count(self, disc29_analysis: DiscAnalysis) -> None:
        assert len(disc29_analysis.special_features) == 3

    def test_all_digital_archives(self, disc29_analysis: DiscAnalysis) -> None:
        for sf in disc29_analysis.special_features:
            assert sf.category == "digital_archive"


class TestDisc29Metadata:
    def test_disc_title(self, disc29_analysis: DiscAnalysis) -> None:
        assert disc29_analysis.disc_title == "TEST DISC 29"
