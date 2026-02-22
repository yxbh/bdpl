"""Tests for MPLS parsing against the real BDMV."""

from pathlib import Path

import pytest

from bdpl.bdmv.mpls import parse_mpls, parse_mpls_dir
from bdpl.model import ChapterMark, Playlist, StreamInfo


class TestParseAllMpls:
    def test_parse_all_mpls(self, bdmv_path: Path) -> None:
        """Parse all 11 MPLS files without error."""
        playlist_dir = bdmv_path / "PLAYLIST"
        playlists: list[Playlist] = parse_mpls_dir(playlist_dir)
        assert len(playlists) == 11


class TestPlaylist00002:
    @pytest.fixture
    def pl00002(self, bdmv_path: Path) -> Playlist:
        return parse_mpls(bdmv_path / "PLAYLIST" / "00002.mpls")

    def test_playlist_00002_items(self, pl00002: Playlist) -> None:
        """Verify 00002.mpls has 4 play items with correct clip IDs."""
        assert len(pl00002.play_items) == 4
        clip_ids = [pi.clip_id for pi in pl00002.play_items]
        assert clip_ids == ["00007", "00008", "00009", "00010"]

    def test_playlist_00002_duration(self, pl00002: Playlist) -> None:
        """Verify 00002.mpls total duration is approximately 4866.5 seconds."""
        assert pl00002.duration_seconds == pytest.approx(4866.5, abs=1.0)


class TestPlaylist00003:
    def test_playlist_00003_single_item(self, bdmv_path: Path) -> None:
        """Verify 00003.mpls has 1 play item with clip 00011, ~66s."""
        pl: Playlist = parse_mpls(bdmv_path / "PLAYLIST" / "00003.mpls")
        assert len(pl.play_items) == 1
        assert pl.play_items[0].clip_id == "00011"
        assert pl.duration_seconds == pytest.approx(66, abs=1.0)


class TestStreamsDetected:
    def test_streams_detected(self, bdmv_path: Path) -> None:
        """Verify 00002.mpls first play item has H.264/AVC video and LPCM audio."""
        pl: Playlist = parse_mpls(bdmv_path / "PLAYLIST" / "00002.mpls")
        streams: list[StreamInfo] = pl.play_items[0].streams
        codecs: list[str] = [s.codec for s in streams]
        assert "H.264/AVC" in codecs
        assert "LPCM" in codecs


class TestChaptersParsed:
    def test_chapters_parsed(self, bdmv_path: Path) -> None:
        """Verify 00002.mpls has chapters (mark_type=1)."""
        pl: Playlist = parse_mpls(bdmv_path / "PLAYLIST" / "00002.mpls")
        assert len(pl.chapters) > 0
        entry_marks: list[ChapterMark] = [ch for ch in pl.chapters if ch.mark_type == 1]
        assert len(entry_marks) > 0


class TestLanguages:
    def test_languages(self, bdmv_path: Path) -> None:
        """Verify PGS subs include jpn, eng, zho languages."""
        pl: Playlist = parse_mpls(bdmv_path / "PLAYLIST" / "00002.mpls")
        pgs_langs: set[str] = set()
        for pi in pl.play_items:
            for s in pi.streams:
                if s.codec == "PGS" and s.lang:
                    pgs_langs.add(s.lang)
        assert "jpn" in pgs_langs
        assert "eng" in pgs_langs
        assert "zho" in pgs_langs
