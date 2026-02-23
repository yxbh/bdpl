"""Integration tests for disc1 fixture scan behavior."""

import json

import pytest

from bdpl.export import export_json
from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestScanFindsEpisodes:
    def test_scan_finds_episodes(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify scan finds 3 episodes."""
        assert len(disc1_analysis.episodes) == 3


class TestEpisodeDurations:
    def test_episode_durations(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify each episode is approximately 26-27 minutes."""
        for ep in disc1_analysis.episodes:
            duration_min = ep.duration_ms / 1000.0 / 60.0
            assert 26 <= duration_min <= 28, (
                f"Episode {ep.episode} duration {duration_min:.1f} min not in 26-28 range"
            )


class TestEpisodeClipIds:
    def test_episode_clip_ids(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify episodes reference clips 00007, 00008, 00009."""
        ep_clip_ids: set[str] = set()
        for ep in disc1_analysis.episodes:
            for seg in ep.segments:
                ep_clip_ids.add(seg.clip_id)
        assert "00007" in ep_clip_ids
        assert "00008" in ep_clip_ids
        assert "00009" in ep_clip_ids


class TestPlayAllDetected:
    def test_play_all_detected(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify 00002.mpls classified as play_all."""
        classifications = disc1_analysis.analysis.get("classifications", {})
        assert classifications.get("00002.mpls") == "play_all"


class TestWarningsEmitted:
    def test_warnings_emitted(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify PLAY_ALL_ONLY warning is present."""
        codes = [w.code for w in disc1_analysis.warnings]
        assert "PLAY_ALL_ONLY" in codes


class TestSpecialFeatures:
    def test_special_feature_count(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify disc1 exposes 9 special features."""
        assert len(disc1_analysis.special_features) == 9

    def test_playlist_00008_has_two_chapter_split_specials(
        self, disc1_analysis: DiscAnalysis
    ) -> None:
        """Verify playlist 00008.mpls is exposed as two chapter-targeted specials."""
        chapter_starts = sorted(
            sf.chapter_start
            for sf in disc1_analysis.special_features
            if sf.playlist == "00008.mpls" and sf.chapter_start is not None
        )
        assert chapter_starts == [0, 3]

    def test_playlist_00008_split_duration_boundary_fallback(
        self, disc1_analysis: DiscAnalysis
    ) -> None:
        """Verify out-of-range chapter marks fall back to full playlist duration."""
        specials = sorted(
            (
                sf
                for sf in disc1_analysis.special_features
                if sf.playlist == "00008.mpls" and sf.chapter_start is not None
            ),
            key=lambda sf: sf.chapter_start,
        )
        assert [sf.chapter_start for sf in specials] == [0, 3]
        assert all(sf.duration_ms > 0 for sf in specials)

        source = next(pl for pl in disc1_analysis.playlists if pl.mpls == "00008.mpls")
        assert source.chapters
        max_valid_chapter = len(source.chapters) - 1
        assert specials[-1].chapter_start is not None
        assert specials[-1].chapter_start > max_valid_chapter

        assert abs(specials[0].duration_ms - source.duration_ms) < 1.0
        assert abs(specials[1].duration_ms - source.duration_ms) < 1.0


class TestJsonExport:
    def test_json_export_valid(self, disc1_analysis: DiscAnalysis) -> None:
        """Verify JSON export is valid JSON and has required keys."""
        json_str = export_json(disc1_analysis)
        data = json.loads(json_str)
        assert "schema_version" in data
        assert "disc" in data
        assert "playlists" in data
        assert "episodes" in data
        assert "warnings" in data
        assert "analysis" in data
