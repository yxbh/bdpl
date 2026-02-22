"""Tests for CLPI parsing."""

from pathlib import Path

import pytest

from bdpl.bdmv.clpi import parse_clpi, parse_clpi_dir
from bdpl.model import ClipInfo


class TestParseAllClpi:
    def test_parse_all_clpi(self, bdmv_path: Path) -> None:
        """Parse all 19 CLPI files without error."""
        clipinf_dir = bdmv_path / "CLIPINF"
        clips: dict[str, ClipInfo] = parse_clpi_dir(clipinf_dir)
        assert len(clips) == 19


class TestClip00007:
    @pytest.fixture
    def clip(self, bdmv_path: Path) -> ClipInfo:
        return parse_clpi(bdmv_path / "CLIPINF" / "00007.clpi")

    def test_clip_00007_streams(self, clip: ClipInfo) -> None:
        """Verify clip 00007 has H.264 video and LPCM audio with jpn."""
        codecs = [s.codec for s in clip.streams]
        assert "H.264" in codecs
        assert "LPCM" in codecs
        lpcm_streams = [s for s in clip.streams if s.codec == "LPCM"]
        assert any(s.lang == "jpn" for s in lpcm_streams)

    def test_clip_00007_subtitles(self, clip: ClipInfo) -> None:
        """Verify clip 00007 has PGS subtitles."""
        pgs_streams = [s for s in clip.streams if s.codec == "PGS"]
        assert len(pgs_streams) > 0


class TestClipLanguages:
    def test_clip_languages(self, bdmv_path: Path) -> None:
        """Verify stream languages are correctly parsed."""
        clips: dict[str, ClipInfo] = parse_clpi_dir(bdmv_path / "CLIPINF")
        clip: ClipInfo = clips["00007"]
        langs: set[str] = {s.lang for s in clip.streams if s.lang}
        assert len(langs) > 0
        # Should have at least Japanese
        assert "jpn" in langs
