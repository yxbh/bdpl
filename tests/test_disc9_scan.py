"""Integration tests for the disc9 fixture scan results.

Disc9 is a single-movie disc (vol 4 of a box set) with two playlist
variants sharing the same main clip (00006, ~90 min):
- 00002.mpls: full streams (10 tracks) + short outro clip 00007 (0.2 min)
- 00003.mpls: alt audio (pid 4356) + longer ending clip 00008 (2.0 min)

Current analysis detects both as separate episodes because the playlists
have different secondary clips and stream layouts, so they are not
deduplicated.  The user expects 1 episode (7 parts) + 1 special.

NOTE: The analysis produces 2 episodes and 0 specials — this reflects a
known limitation where stream-variant playlists with different secondary
clips are not detected as duplicates.
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc9Episodes:
    def test_episode_count(self, disc9_analysis: DiscAnalysis) -> None:
        """Analysis currently finds 2 episodes (stream variants)."""
        assert len(disc9_analysis.episodes) == 2

    def test_episodes_are_ordered(self, disc9_analysis: DiscAnalysis) -> None:
        """Verify inferred episode sequence is [1, 2]."""
        assert [ep.episode for ep in disc9_analysis.episodes] == [1, 2]

    def test_episodes_share_main_clip(self, disc9_analysis: DiscAnalysis) -> None:
        """Both episodes reference clip 00006 as their primary content."""
        for ep in disc9_analysis.episodes:
            assert ep.segments[0].clip_id == "00006"

    def test_episode_durations_reasonable(self, disc9_analysis: DiscAnalysis) -> None:
        """Both episodes should be ~88–95 min (movie length)."""
        for ep in disc9_analysis.episodes:
            dur_min = ep.duration_ms / 60_000
            assert 88 < dur_min < 95, f"Ep {ep.episode} duration {dur_min:.1f}min out of range"

    def test_episode_scene_counts(self, disc9_analysis: DiscAnalysis) -> None:
        """Both episodes should have 4 scenes from chapter downsampling."""
        for ep in disc9_analysis.episodes:
            assert len(ep.scenes) == 4, f"Ep {ep.episode} expected 4 scenes, got {len(ep.scenes)}"


class TestDisc9Specials:
    def test_no_specials_detected(self, disc9_analysis: DiscAnalysis) -> None:
        """No specials currently detected (stream variants not deduped)."""
        assert len(disc9_analysis.special_features) == 0


class TestDisc9Metadata:
    def test_disc_title(self, disc9_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc9_analysis.disc_title == "TEST DISC 9"
