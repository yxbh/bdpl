"""Tests for CLPI parsing."""

import pytest

from bdpl.bdmv.clpi import parse_clpi, parse_clpi_dir


class TestParseAllClpi:
    def test_parse_all_clpi(self, bdmv_path):
        """Parse all 19 CLPI files without error."""
        clipinf_dir = bdmv_path / "CLIPINF"
        clips = parse_clpi_dir(clipinf_dir)
        assert len(clips) == 19


class TestClip00007:
    @pytest.fixture
    def clip(self, bdmv_path):
        return parse_clpi(bdmv_path / "CLIPINF" / "00007.clpi")

    def test_clip_00007_streams(self, clip):
        """Verify clip 00007 has H.264 video and LPCM audio with jpn."""
        codecs = [s.codec for s in clip.streams]
        assert "H.264" in codecs
        assert "LPCM" in codecs
        lpcm_streams = [s for s in clip.streams if s.codec == "LPCM"]
        assert any(s.lang == "jpn" for s in lpcm_streams)

    def test_clip_00007_subtitles(self, clip):
        """Verify clip 00007 has PGS subtitles."""
        pgs_streams = [s for s in clip.streams if s.codec == "PGS"]
        assert len(pgs_streams) > 0


class TestClipLanguages:
    def test_clip_languages(self, bdmv_path):
        """Verify stream languages are correctly parsed."""
        clips = parse_clpi_dir(bdmv_path / "CLIPINF")
        clip = clips["00007"]
        langs = {s.lang for s in clip.streams if s.lang}
        assert len(langs) > 0
        # Should have at least Japanese
        assert "jpn" in langs
