"""Integration tests for the disc26 fixture — 3-episode OVA disc with commentary + extras."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc26Episodes:
    def test_episode_count(self, disc26_analysis: DiscAnalysis) -> None:
        assert len(disc26_analysis.episodes) == 3

    def test_episodes_are_ordered(self, disc26_analysis: DiscAnalysis) -> None:
        assert [ep.episode for ep in disc26_analysis.episodes] == list(range(1, 4))

    def test_episode_playlists(self, disc26_analysis: DiscAnalysis) -> None:
        assert [ep.playlist for ep in disc26_analysis.episodes] == [
            "00002.mpls",
            "00003.mpls",
            "00004.mpls",
        ]

    def test_episode_durations(self, disc26_analysis: DiscAnalysis) -> None:
        for ep in disc26_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 25 < dur_min < 30, f"ep{ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc26Specials:
    def test_special_count(self, disc26_analysis: DiscAnalysis) -> None:
        assert len(disc26_analysis.special_features) == 12

    def test_no_commentary(self, disc26_analysis: DiscAnalysis) -> None:
        commentary = [sf for sf in disc26_analysis.special_features if sf.category == "commentary"]
        assert len(commentary) == 0

    def test_has_creditless_ed(self, disc26_analysis: DiscAnalysis) -> None:
        creditless = [
            sf for sf in disc26_analysis.special_features if sf.category == "creditless_ed"
        ]
        assert len(creditless) == 4


class TestDisc26Metadata:
    def test_disc_title(self, disc26_analysis: DiscAnalysis) -> None:
        assert disc26_analysis.disc_title == "TEST DISC 26"
