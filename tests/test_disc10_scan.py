"""Integration tests for the disc10 fixture scan results.

Disc10 is a five-episode bonus disc with commentary specials:
- Play_all (00002.mpls, 6 clips, 31 chapters) decomposes into 5 episodes
  at IG chapter marks [0, 6, 12, 18, 24].  Each episode ~24 min.
- Three individual playlists (00003-00005) duplicate episodes 1-3 with
  commentary audio; detected as commentary specials via IG page 4 buttons.
- Only episodes 1-3 have individual playlists; episodes 4-5 are
  play_all-only, driving the play_all-subset ordering heuristic.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc10Episodes:
    def test_finds_five_episodes(self, disc10_analysis: DiscAnalysis) -> None:
        """Disc10 should infer exactly five episodes from play_all."""
        assert len(disc10_analysis.episodes) == 5

    def test_episodes_are_ordered(self, disc10_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1, 2, 3, 4, 5]."""
        assert [ep.episode for ep in disc10_analysis.episodes] == [1, 2, 3, 4, 5]

    def test_all_episodes_from_play_all(self, disc10_analysis: DiscAnalysis) -> None:
        """All episodes should come from the play_all playlist."""
        for ep in disc10_analysis.episodes:
            assert ep.playlist == "00002.mpls"

    def test_episode_durations_reasonable(self, disc10_analysis: DiscAnalysis) -> None:
        """Each episode should be ~20–28 min."""
        for ep in disc10_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 20 < dur_min < 28, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_episodes_have_scenes(self, disc10_analysis: DiscAnalysis) -> None:
        """Each episode should have at least 1 scene."""
        for ep in disc10_analysis.episodes:
            assert len(ep.scenes) >= 1, f"Ep {ep.episode} has no scenes"


class TestDisc10Specials:
    def test_special_count(self, disc10_analysis: DiscAnalysis) -> None:
        """Disc10 should have 3 specials (commentaries for episodes 1-3)."""
        assert len(disc10_analysis.special_features) == 3

    def test_all_commentaries(self, disc10_analysis: DiscAnalysis) -> None:
        """All specials should be commentary tracks."""
        for sf in disc10_analysis.special_features:
            assert sf.category == "commentary", (
                f"Special {sf.playlist} has category '{sf.category}', expected 'commentary'"
            )

    def test_commentary_playlists(self, disc10_analysis: DiscAnalysis) -> None:
        """Commentary tracks should reference individual episode playlists."""
        playlists = {sf.playlist for sf in disc10_analysis.special_features}
        assert playlists == {"00003.mpls", "00004.mpls", "00005.mpls"}


class TestDisc10Metadata:
    def test_disc_title(self, disc10_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc10_analysis.disc_title == "TEST DISC 10"

    def test_play_all_detected(self, disc10_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc10_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"

    def test_ig_chapter_marks(self, disc10_analysis: DiscAnalysis) -> None:
        """IG hints should report 5 chapter marks for episode starts."""
        ig = disc10_analysis.analysis.get("disc_hints", {}).get("ig_menu", {})
        marks = ig.get("chapter_marks", [])
        assert marks == [0, 6, 12, 18, 24]
