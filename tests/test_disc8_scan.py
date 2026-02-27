"""Integration tests for the disc8 fixture scan results.

Disc8 is a two-episode disc (vol 3 of a box set) with similar structure
to disc7:
- Episode 1 (00003.mpls, clip 00006): ~54 min, 4 scenes
- Episode 2 (00004.mpls, clips 00007+00010): ~60 min, 4 scenes

Two specials are detected (00005.mpls + 00006.mpls) — stream variants of
the same clip (00009, ~5.2 min) with different audio tracks.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc8Episodes:
    def test_finds_two_episodes(self, disc8_analysis: DiscAnalysis) -> None:
        """Disc8 should infer exactly two episodes."""
        assert len(disc8_analysis.episodes) == 2

    def test_episodes_are_ordered(self, disc8_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1, 2]."""
        assert [ep.episode for ep in disc8_analysis.episodes] == [1, 2]

    def test_episode1_has_four_scenes(self, disc8_analysis: DiscAnalysis) -> None:
        """Episode 1 should have 4 scenes."""
        ep1 = disc8_analysis.episodes[0]
        assert len(ep1.scenes) == 4, f"Episode 1 expected 4 scenes, got {len(ep1.scenes)}"

    def test_episode2_has_four_scenes(self, disc8_analysis: DiscAnalysis) -> None:
        """Episode 2 should have 4 scenes."""
        ep2 = disc8_analysis.episodes[1]
        assert len(ep2.scenes) == 4, f"Episode 2 expected 4 scenes, got {len(ep2.scenes)}"

    def test_episode_durations_reasonable(self, disc8_analysis: DiscAnalysis) -> None:
        """Both episodes should be ~50–65 min (OVA length)."""
        for ep in disc8_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 50 < dur_min < 65, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"


class TestDisc8Specials:
    def test_special_count(self, disc8_analysis: DiscAnalysis) -> None:
        """Disc8 should have 2 specials (stream variants of same clip)."""
        assert len(disc8_analysis.special_features) == 2

    def test_specials_are_short(self, disc8_analysis: DiscAnalysis) -> None:
        """Both specials should be ~4–6 min."""
        for sf in disc8_analysis.special_features:
            dur_min = sf.duration_ms / 60_000
            assert 4 < dur_min < 7, f"Special {sf.playlist} duration {dur_min:.1f}min out of range"


class TestDisc8Metadata:
    def test_disc_title(self, disc8_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc8_analysis.disc_title == "TEST DISC 8"

    def test_play_all_detected(self, disc8_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc8_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"
