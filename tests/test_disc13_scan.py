"""Integration tests for the disc13 fixture scan results.

Disc13 is a six-episode bonus disc with the most complex special features
page in the box set (9 specials):
- Play_all (00002.mpls, 7 clips, 38 chapters) decomposes into 6 episodes
  at IG chapter marks [0, 6, 13, 19, 25, 31].  Five ~24 min, one ~23.6 min.
- Two individual playlists (00003-00004) are commentary / alt-audio tracks
  for episodes.  Both detected as commentary specials.
- Five creditless OP/ED playlists (00005-00008, 00011) each ~1.5-2 min.
- Two extra / promotional playlists (00009, 00010) — 3.3 min and 8.8 min.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc13Episodes:
    def test_finds_six_episodes(self, disc13_analysis: DiscAnalysis) -> None:
        """Disc13 should infer exactly six episodes from play_all."""
        assert len(disc13_analysis.episodes) == 6

    def test_episodes_are_ordered(self, disc13_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1..6]."""
        assert [ep.episode for ep in disc13_analysis.episodes] == [1, 2, 3, 4, 5, 6]

    def test_all_episodes_from_play_all(self, disc13_analysis: DiscAnalysis) -> None:
        """All episodes should come from the play_all playlist."""
        for ep in disc13_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_durations_reasonable(self, disc13_analysis: DiscAnalysis) -> None:
        """Each episode should be ~20–28 min."""
        for ep in disc13_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 20 < dur_min < 28, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc13Specials:
    def test_special_count(self, disc13_analysis: DiscAnalysis) -> None:
        """Disc13 should have 9 specials total."""
        assert len(disc13_analysis.special_features) == 9

    def test_commentary_count(self, disc13_analysis: DiscAnalysis) -> None:
        """Two specials should be commentary / alt-audio tracks."""
        commentaries = [
            sf for sf in disc13_analysis.special_features if sf.category == "commentary"
        ]
        assert len(commentaries) == 2

    def test_commentary_playlists(self, disc13_analysis: DiscAnalysis) -> None:
        """Commentary tracks should reference individual episode playlists."""
        playlists = {
            sf.playlist for sf in disc13_analysis.special_features if sf.category == "commentary"
        }
        assert playlists == {"00003.mpls", "00004.mpls"}

    def test_creditless_count(self, disc13_analysis: DiscAnalysis) -> None:
        """Five specials should be creditless OP/ED tracks."""
        creditless = [
            sf for sf in disc13_analysis.special_features if sf.category == "creditless_ed"
        ]
        assert len(creditless) == 5

    def test_extra_count(self, disc13_analysis: DiscAnalysis) -> None:
        """Two specials should be extras (promotional content)."""
        extras = [sf for sf in disc13_analysis.special_features if sf.category == "extra"]
        assert len(extras) == 2


class TestDisc13Metadata:
    def test_disc_title(self, disc13_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc13_analysis.disc_title == "TEST DISC 13"

    def test_play_all_detected(self, disc13_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc13_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"

    def test_ig_chapter_marks(self, disc13_analysis: DiscAnalysis) -> None:
        """IG hints should report 6 chapter marks for episode starts."""
        ig = disc13_analysis.analysis.get("disc_hints", {}).get("ig_menu", {})
        marks = ig.get("chapter_marks", [])
        assert marks == [0, 6, 13, 19, 25, 31]
