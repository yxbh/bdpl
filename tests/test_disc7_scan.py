"""Integration tests for the disc7 fixture scan results.

Disc7 is a two-episode disc (vol 2 of a box set) where each episode is a
single long clip (~59–60 min) with chapter marks dividing it into scenes:
- Episode 1 (00003.mpls, clip 00006): 3 scenes
- Episode 2 (00004.mpls, clip 00007): 4 scenes

Two specials are detected (00005.mpls + 00006.mpls) — stream variants of
the same clip (00009, ~3.5 min) with TrueHD vs AC-3 audio.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc7Episodes:
    def test_finds_two_episodes(self, disc7_analysis: DiscAnalysis) -> None:
        """Disc7 should infer exactly two episodes."""
        assert len(disc7_analysis.episodes) == 2

    def test_episodes_are_ordered(self, disc7_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1, 2]."""
        assert [ep.episode for ep in disc7_analysis.episodes] == [1, 2]

    def test_episode1_has_four_scenes(self, disc7_analysis: DiscAnalysis) -> None:
        """Episode 1 should have 4 scenes (3 content + credits tail)."""
        ep1 = disc7_analysis.episodes[0]
        assert len(ep1.scenes) == 4, (
            f"Episode 1 expected 4 scenes, got {len(ep1.scenes)}"
        )

    def test_episode2_has_four_scenes(self, disc7_analysis: DiscAnalysis) -> None:
        """Episode 2 should have 4 scenes per disc menu structure."""
        ep2 = disc7_analysis.episodes[1]
        assert len(ep2.scenes) == 4, (
            f"Episode 2 expected 4 scenes, got {len(ep2.scenes)}"
        )

    def test_episode_durations_reasonable(self, disc7_analysis: DiscAnalysis) -> None:
        """Both episodes should be ~55–65 min (OVA length)."""
        for ep in disc7_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 55 < dur_min < 65, (
                f"Ep {ep.episode} duration {dur_min:.1f}min out of range"
            )


class TestDisc7Specials:
    def test_special_count(self, disc7_analysis: DiscAnalysis) -> None:
        """Disc7 should have 2 specials (stream variants of same clip)."""
        assert len(disc7_analysis.special_features) == 2

    def test_specials_are_short(self, disc7_analysis: DiscAnalysis) -> None:
        """Both specials should be ~3–4 min."""
        for sf in disc7_analysis.special_features:
            dur_min = sf.duration_ms / 60_000
            assert 3 < dur_min < 5, (
                f"Special {sf.playlist} duration {dur_min:.1f}min out of range"
            )


class TestDisc7Metadata:
    def test_disc_title(self, disc7_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc7_analysis.disc_title == "TEST DISC 7 VOL 2"

    def test_play_all_detected(self, disc7_analysis: DiscAnalysis) -> None:
        """00002.mpls should be classified as play_all."""
        classes = disc7_analysis.analysis.get("classifications", {})
        assert classes.get("00002.mpls") == "play_all"
