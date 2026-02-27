"""Integration tests for the disc11 fixture scan results.

Disc11 is a six-episode bonus disc with one short special:
- Play_all (00002.mpls, 7 clips, 37 chapters) decomposes into 6 episodes
  at IG chapter marks [0, 6, 12, 18, 24, 30].  Each episode ~24 min.
- One special feature (00003.mpls, clip 00013, ~3.5 min) classified as
  extra, detected via title hint (title 1 → playlist 3).
- No individual episode playlists — all episodes come from play_all.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc11Episodes:
    def test_finds_six_episodes(self, disc11_analysis: DiscAnalysis) -> None:
        """Disc11 should infer exactly six episodes from play_all."""
        assert len(disc11_analysis.episodes) == 6

    def test_episodes_are_ordered(self, disc11_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1..6]."""
        assert [ep.episode for ep in disc11_analysis.episodes] == [1, 2, 3, 4, 5, 6]

    def test_all_episodes_from_play_all(self, disc11_analysis: DiscAnalysis) -> None:
        """All episodes should come from the play_all playlist."""
        for ep in disc11_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_durations_reasonable(self, disc11_analysis: DiscAnalysis) -> None:
        """Each episode should be ~20–28 min."""
        for ep in disc11_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 20 < dur_min < 28, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc11Specials:
    def test_special_count(self, disc11_analysis: DiscAnalysis) -> None:
        """Disc11 should have 1 special feature."""
        assert len(disc11_analysis.special_features) == 1

    def test_special_is_short(self, disc11_analysis: DiscAnalysis) -> None:
        """The special should be ~3–5 min."""
        sf = disc11_analysis.special_features[0]
        dur_min = sf.duration_ms / 60_000
        assert 2 < dur_min < 5, f"Special {sf.playlist} duration {dur_min:.1f}min out of range"

    def test_special_playlist(self, disc11_analysis: DiscAnalysis) -> None:
        """Special should be on 00003.mpls."""
        assert disc11_analysis.special_features[0].playlist == "00003.mpls"


class TestDisc11Metadata:
    def test_disc_title(self, disc11_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc11_analysis.disc_title == "TEST DISC 11"

    def test_play_all_detected(self, disc11_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc11_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"

    def test_ig_chapter_marks(self, disc11_analysis: DiscAnalysis) -> None:
        """IG hints should report 6 chapter marks for episode starts."""
        ig = disc11_analysis.analysis.get("disc_hints", {}).get("ig_menu", {})
        marks = ig.get("chapter_marks", [])
        assert marks == [0, 6, 12, 18, 24, 30]
