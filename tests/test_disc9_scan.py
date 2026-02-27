"""Integration tests for the disc9 fixture scan results.

Disc9 is a single-movie disc (vol 4 of a box set) with two playlist
variants sharing the same main clip (00006, ~90 min):
- 00002.mpls: full streams (10 tracks) + short outro clip 00007 (0.2 min)
- 00003.mpls: alt audio (pid 4356) + longer ending clip 00008 (2.0 min)

Primary-clip variant detection identifies these as duplicates, picking
00002.mpls (more streams) as the representative episode.  00003.mpls
becomes a special feature (alt-audio version).
"""

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc9Episodes:
    def test_episode_count(self, disc9_analysis: DiscAnalysis) -> None:
        """Disc9 should have exactly 1 episode (single movie)."""
        assert len(disc9_analysis.episodes) == 1

    def test_episode_playlist(self, disc9_analysis: DiscAnalysis) -> None:
        """The episode should use 00002.mpls (more streams)."""
        assert disc9_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_uses_main_clip(self, disc9_analysis: DiscAnalysis) -> None:
        """The episode should reference clip 00006 as primary content."""
        assert disc9_analysis.episodes[0].segments[0].clip_id == "00006"

    def test_episode_duration_reasonable(self, disc9_analysis: DiscAnalysis) -> None:
        """Episode should be ~88–95 min (movie length)."""
        dur_min = disc9_analysis.episodes[0].duration_ms / 60_000
        assert 88 < dur_min < 95, f"Episode duration {dur_min:.1f}min out of range"

    def test_episode_scene_count(self, disc9_analysis: DiscAnalysis) -> None:
        """Episode should have 4 scenes from chapter downsampling."""
        ep = disc9_analysis.episodes[0]
        assert len(ep.scenes) == 4, f"Expected 4 scenes, got {len(ep.scenes)}"


class TestDisc9Specials:
    def test_special_count(self, disc9_analysis: DiscAnalysis) -> None:
        """Disc9 should have 1 special (alt-audio variant 00003.mpls)."""
        assert len(disc9_analysis.special_features) == 1

    def test_special_is_variant(self, disc9_analysis: DiscAnalysis) -> None:
        """The special should be 00003.mpls (alt-audio version)."""
        assert disc9_analysis.special_features[0].playlist == "00003.mpls"


class TestDisc9Metadata:
    def test_disc_title(self, disc9_analysis: DiscAnalysis) -> None:
        """Disc title should be extracted from META/DL/bdmt_eng.xml."""
        assert disc9_analysis.disc_title == "TEST DISC 9"

    def test_variant_dedup_detected(self, disc9_analysis: DiscAnalysis) -> None:
        """Variant dedup should group 00002 and 00003 as duplicates."""
        dups = disc9_analysis.analysis.get("duplicate_groups", [])
        assert any("00002.mpls" in g and "00003.mpls" in g for g in dups)
