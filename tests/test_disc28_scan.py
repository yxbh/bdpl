"""Integration tests for the disc28 fixture — 3-episode OVA disc with creditless + extras."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc28Episodes:
    def test_episode_count(self, disc28_analysis: DiscAnalysis) -> None:
        assert len(disc28_analysis.episodes) == 3

    def test_episodes_are_ordered(self, disc28_analysis: DiscAnalysis) -> None:
        assert [ep.episode for ep in disc28_analysis.episodes] == list(range(1, 4))

    def test_episode_playlists(self, disc28_analysis: DiscAnalysis) -> None:
        assert [ep.playlist for ep in disc28_analysis.episodes] == [
            "00002.mpls",
            "00003.mpls",
            "00004.mpls",
        ]

    def test_episode_durations(self, disc28_analysis: DiscAnalysis) -> None:
        for ep in disc28_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 25 < dur_min < 33, f"ep{ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc28Specials:
    def test_special_count(self, disc28_analysis: DiscAnalysis) -> None:
        assert len(disc28_analysis.special_features) == 13

    def test_has_commentary(self, disc28_analysis: DiscAnalysis) -> None:
        commentary = [sf for sf in disc28_analysis.special_features if sf.category == "commentary"]
        assert len(commentary) == 2

    def test_has_creditless_ed(self, disc28_analysis: DiscAnalysis) -> None:
        creditless = [
            sf for sf in disc28_analysis.special_features if sf.category == "creditless_ed"
        ]
        assert len(creditless) == 7


class TestDisc28Metadata:
    def test_disc_title(self, disc28_analysis: DiscAnalysis) -> None:
        assert disc28_analysis.disc_title == "TEST DISC 28"
