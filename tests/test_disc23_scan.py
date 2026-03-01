"""Integration tests for the disc23 fixture — 5-episode chapter-split compilation."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc23Episodes:
    def test_episode_count(self, disc23_analysis: DiscAnalysis) -> None:
        assert len(disc23_analysis.episodes) == 5

    def test_episodes_are_ordered(self, disc23_analysis: DiscAnalysis) -> None:
        assert [ep.episode for ep in disc23_analysis.episodes] == list(range(1, 6))

    def test_all_from_same_playlist(self, disc23_analysis: DiscAnalysis) -> None:
        assert all(ep.playlist == "00002.mpls" for ep in disc23_analysis.episodes)

    def test_episode_durations(self, disc23_analysis: DiscAnalysis) -> None:
        for ep in disc23_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 24 < dur_min < 32, f"ep{ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc23Specials:
    def test_no_specials(self, disc23_analysis: DiscAnalysis) -> None:
        assert len(disc23_analysis.special_features) == 0


class TestDisc23Metadata:
    def test_disc_title(self, disc23_analysis: DiscAnalysis) -> None:
        assert disc23_analysis.disc_title == "TEST DISC 23"
