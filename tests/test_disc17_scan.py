"""Tests for disc17 fixture — single OVA episode with digital archive."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc17Episodes:
    def test_episode_count(self, disc17_analysis: DiscAnalysis) -> None:
        assert len(disc17_analysis.episodes) == 1

    def test_episode_playlist(self, disc17_analysis: DiscAnalysis) -> None:
        assert disc17_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration_reasonable(self, disc17_analysis: DiscAnalysis) -> None:
        dur_min = disc17_analysis.episodes[0].duration_ms / 60000
        assert 30 < dur_min < 60, f"Episode duration {dur_min:.1f}min out of range"


class TestDisc17Specials:
    def test_special_feature_count(self, disc17_analysis: DiscAnalysis) -> None:
        assert len(disc17_analysis.special_features) == 1

    def test_digital_archive_detected(self, disc17_analysis: DiscAnalysis) -> None:
        sf = disc17_analysis.special_features[0]
        assert sf.category == "digital_archive"
        assert sf.playlist == "00003.mpls"

    def test_digital_archive_visible(self, disc17_analysis: DiscAnalysis) -> None:
        assert disc17_analysis.special_features[0].menu_visible


class TestDisc17Metadata:
    def test_disc_title(self, disc17_analysis: DiscAnalysis) -> None:
        assert disc17_analysis.disc_title == "TEST DISC 17"
