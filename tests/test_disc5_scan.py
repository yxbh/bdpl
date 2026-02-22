"""Integration tests for disc5 fixture scan behavior."""

from bdpl.model import DiscAnalysis


def test_disc5_finds_single_main_episode(disc5_analysis: DiscAnalysis) -> None:
    """Disc5 should infer one main title, not chapter buttons as episodes."""
    assert len(disc5_analysis.episodes) == 1
    assert disc5_analysis.episodes[0].playlist == "00001.mpls"


def test_disc5_keeps_long_special_playlist_as_extra(disc5_analysis: DiscAnalysis) -> None:
    """Long specials playlist should remain extra, not become an episode."""
    classes = disc5_analysis.analysis.get("classifications", {})
    assert classes.get("01001.mpls") == "extra"


def test_disc5_has_no_digital_archive_playlist(disc5_analysis: DiscAnalysis) -> None:
    """Disc5 does not contain an image archive playlist in this fixture."""
    classes = disc5_analysis.analysis.get("classifications", {})
    assert "digital_archive" not in classes.values()


def test_disc5_special_features_detected(disc5_analysis: DiscAnalysis) -> None:
    """Metadata-only disc5 fixture exposes 14 playlist-level specials."""
    assert len(disc5_analysis.special_features) == 14


def test_disc5_menu_visible_specials_count_is_11(disc5_analysis: DiscAnalysis) -> None:
    """Disc5 SPECIAL menu should have exactly 11 visible entries."""
    visible = [sf for sf in disc5_analysis.special_features if sf.menu_visible]
    assert len(visible) == 11


def test_disc5_non_visible_specials_count_is_3(disc5_analysis: DiscAnalysis) -> None:
    """Disc5 should have three hidden/non-visible utility specials."""
    hidden = [sf for sf in disc5_analysis.special_features if not sf.menu_visible]
    assert len(hidden) == 3
