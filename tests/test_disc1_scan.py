"""Integration tests for disc1 fixture scan behavior."""

import json
from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.export import export_json
from bdpl.model import DiscAnalysis

_DISC1 = Path(__file__).parent / "fixtures" / "disc1"


@pytest.fixture
def disc1_path() -> Path:
    """Return path to bundled disc1 fixture if available."""
    if not (_DISC1 / "PLAYLIST").is_dir():
        pytest.skip("disc1 fixture not available")
    return _DISC1


@pytest.fixture
def analysis(disc1_path: Path) -> DiscAnalysis:
    """Run the full scan pipeline on the disc1 fixture BDMV."""
    playlists = parse_mpls_dir(disc1_path / "PLAYLIST")
    clips = parse_clpi_dir(disc1_path / "CLIPINF")
    return scan_disc(disc1_path, playlists, clips)


class TestScanFindsEpisodes:
    def test_scan_finds_episodes(self, analysis: DiscAnalysis) -> None:
        """Verify scan finds 3 episodes."""
        assert len(analysis.episodes) == 3


class TestEpisodeDurations:
    def test_episode_durations(self, analysis: DiscAnalysis) -> None:
        """Verify each episode is approximately 26-27 minutes."""
        for ep in analysis.episodes:
            duration_min = ep.duration_ms / 1000.0 / 60.0
            assert 26 <= duration_min <= 28, (
                f"Episode {ep.episode} duration {duration_min:.1f} min not in 26-28 range"
            )


class TestEpisodeClipIds:
    def test_episode_clip_ids(self, analysis: DiscAnalysis) -> None:
        """Verify episodes reference clips 00007, 00008, 00009."""
        ep_clip_ids: set[str] = set()
        for ep in analysis.episodes:
            for seg in ep.segments:
                ep_clip_ids.add(seg.clip_id)
        assert "00007" in ep_clip_ids
        assert "00008" in ep_clip_ids
        assert "00009" in ep_clip_ids


class TestPlayAllDetected:
    def test_play_all_detected(self, analysis: DiscAnalysis) -> None:
        """Verify 00002.mpls classified as play_all."""
        classifications = analysis.analysis.get("classifications", {})
        assert classifications.get("00002.mpls") == "play_all"


class TestWarningsEmitted:
    def test_warnings_emitted(self, analysis: DiscAnalysis) -> None:
        """Verify PLAY_ALL_ONLY warning is present."""
        codes = [w.code for w in analysis.warnings]
        assert "PLAY_ALL_ONLY" in codes


class TestJsonExport:
    def test_json_export_valid(self, analysis: DiscAnalysis) -> None:
        """Verify JSON export is valid JSON and has required keys."""
        json_str = export_json(analysis)
        data = json.loads(json_str)
        assert "schema_version" in data
        assert "disc" in data
        assert "playlists" in data
        assert "episodes" in data
        assert "warnings" in data
        assert "analysis" in data
