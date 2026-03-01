"""Integration tests for the disc24 fixture — 3-episode compilation + commentary + extras."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc24Episodes:
    def test_episode_count(self, disc24_analysis: DiscAnalysis) -> None:
        assert len(disc24_analysis.episodes) == 3

    def test_episodes_are_ordered(self, disc24_analysis: DiscAnalysis) -> None:
        assert [ep.episode for ep in disc24_analysis.episodes] == [1, 2, 3]

    def test_all_from_same_playlist(self, disc24_analysis: DiscAnalysis) -> None:
        assert all(ep.playlist == "00002.mpls" for ep in disc24_analysis.episodes)

    def test_episode_durations(self, disc24_analysis: DiscAnalysis) -> None:
        for ep in disc24_analysis.episodes:
            dur_min = ep.duration_ms / 60000
            assert 25 < dur_min < 33, f"ep{ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc24Specials:
    def test_special_count(self, disc24_analysis: DiscAnalysis) -> None:
        assert len(disc24_analysis.special_features) == 8

    def test_extra_count(self, disc24_analysis: DiscAnalysis) -> None:
        extras = [sf for sf in disc24_analysis.special_features if sf.category == "extra"]
        assert len(extras) == 1

    def test_commentary_count(self, disc24_analysis: DiscAnalysis) -> None:
        commentaries = [
            sf for sf in disc24_analysis.special_features if sf.category == "commentary"
        ]
        assert len(commentaries) == 3

    def test_creditless_ed_count(self, disc24_analysis: DiscAnalysis) -> None:
        creds = [sf for sf in disc24_analysis.special_features if sf.category == "creditless_ed"]
        assert len(creds) == 4


class TestDisc24Metadata:
    def test_disc_title(self, disc24_analysis: DiscAnalysis) -> None:
        assert disc24_analysis.disc_title == "TEST DISC 24"
