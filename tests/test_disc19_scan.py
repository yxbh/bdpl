"""Tests for disc19 fixture — single OVA episode with digital archive (hint-backed)."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


class TestDisc19Episodes:
    def test_episode_count(self, disc19_analysis: DiscAnalysis) -> None:
        assert len(disc19_analysis.episodes) == 1

    def test_episode_playlist(self, disc19_analysis: DiscAnalysis) -> None:
        assert disc19_analysis.episodes[0].playlist == "00002.mpls"

    def test_episode_duration_reasonable(self, disc19_analysis: DiscAnalysis) -> None:
        dur_min = disc19_analysis.episodes[0].duration_ms / 60000
        assert 30 < dur_min < 60, f"Episode duration {dur_min:.1f}min out of range"


class TestDisc19Specials:
    def test_special_feature_count(self, disc19_analysis: DiscAnalysis) -> None:
        assert len(disc19_analysis.special_features) == 1

    def test_digital_archive_detected(self, disc19_analysis: DiscAnalysis) -> None:
        sf = disc19_analysis.special_features[0]
        assert sf.category == "digital_archive"
        assert sf.playlist == "00003.mpls"

    def test_digital_archive_visible(self, disc19_analysis: DiscAnalysis) -> None:
        assert disc19_analysis.special_features[0].menu_visible

    def test_digital_archive_hint_backed(self, disc19_analysis: DiscAnalysis) -> None:
        """Disc19 has only 17 archive items — below strict 20-item threshold.

        Detection succeeds via two structural signals: title hints from
        disc navigation and the absence of audio streams in play items.
        """
        from pathlib import Path

        from bdpl.analyze.classify import is_digital_archive_playlist
        from bdpl.bdmv.mpls import parse_mpls_dir

        pl_dir = Path(__file__).parent / "fixtures" / "disc19" / "PLAYLIST"
        playlists = parse_mpls_dir(pl_dir)
        archive_pl = next(p for p in playlists if p.mpls == "00003.mpls")
        assert len(archive_pl.play_items) < 20, "Below strict item threshold"
        # Title hint alone is sufficient
        assert is_digital_archive_playlist(archive_pl, has_title_hint=True)
        # No-audio signal alone is also sufficient (items have no audio streams)
        assert is_digital_archive_playlist(archive_pl, has_title_hint=False)


class TestDisc19Metadata:
    def test_disc_title(self, disc19_analysis: DiscAnalysis) -> None:
        assert disc19_analysis.disc_title == "TEST DISC 19"
