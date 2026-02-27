"""Integration tests for the disc12 fixture scan results.

Disc12 is a five-episode bonus disc with commentary specials (same
structure as disc10):
- Play_all (00002.mpls, 6 clips, 31 chapters) decomposes into 5 episodes
  at IG chapter marks [0, 6, 12, 18, 24].  Each episode ~24 min.
- Three individual playlists (00003-00005) duplicate episodes 2-4 with
  commentary audio; detected as commentary specials via IG menu.
- Episodes 1 and 5 are play_all-only.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc12Episodes:
    def test_finds_five_episodes(self, disc12_analysis: DiscAnalysis) -> None:
        """Disc12 should infer exactly five episodes from play_all."""
        assert len(disc12_analysis.episodes) == 5

    def test_episodes_are_ordered(self, disc12_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1..5]."""
        assert [ep.episode for ep in disc12_analysis.episodes] == [1, 2, 3, 4, 5]

    def test_all_episodes_from_play_all(self, disc12_analysis: DiscAnalysis) -> None:
        """All episodes should come from the play_all playlist."""
        for ep in disc12_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_durations_reasonable(self, disc12_analysis: DiscAnalysis) -> None:
        """Each episode should be ~20–28 min."""
        for ep in disc12_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 20 < dur_min < 28, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc12Specials:
    def test_special_count(self, disc12_analysis: DiscAnalysis) -> None:
        """Disc12 should have 3 commentary specials."""
        assert len(disc12_analysis.special_features) == 3

    def test_all_commentaries(self, disc12_analysis: DiscAnalysis) -> None:
        """All specials should be commentary tracks."""
        for sf in disc12_analysis.special_features:
            assert sf.category == "commentary"

    def test_commentary_playlists(self, disc12_analysis: DiscAnalysis) -> None:
        """Commentary tracks should reference individual episode playlists."""
        playlists = {sf.playlist for sf in disc12_analysis.special_features}
        assert playlists == {"00003.mpls", "00004.mpls", "00005.mpls"}


class TestDisc12Metadata:
    def test_disc_title(self, disc12_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc12_analysis.disc_title == "TEST DISC 12"

    def test_play_all_detected(self, disc12_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc12_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"

    def test_ig_chapter_marks(self, disc12_analysis: DiscAnalysis) -> None:
        """IG hints should report 5 chapter marks for episode starts."""
        ig = disc12_analysis.analysis.get("disc_hints", {}).get("ig_menu", {})
        marks = ig.get("chapter_marks", [])
        assert marks == [0, 6, 12, 18, 24]
