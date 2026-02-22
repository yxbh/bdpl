"""Unit tests for special-feature visibility fallback heuristics."""

from bdpl.analyze.__init__ import _is_likely_menu_visible_special
from bdpl.model import SpecialFeature


def _feature(playlist: str, duration_ms: float) -> SpecialFeature:
    """Build a minimal SpecialFeature for heuristic tests."""
    return SpecialFeature(
        index=1,
        playlist=playlist,
        duration_ms=duration_ms,
        category="extra",
    )


def test_fallback_visibility_accepts_regular_playlist_over_15s() -> None:
    """Regular-numbered playlists >=15s should be treated as visible."""
    assert _is_likely_menu_visible_special(_feature("00010.mpls", 15_000.0))


def test_fallback_visibility_rejects_short_duration() -> None:
    """Very short helper playlists should be treated as hidden."""
    assert not _is_likely_menu_visible_special(_feature("00010.mpls", 14_999.0))


def test_fallback_visibility_rejects_high_numbered_utility_playlist() -> None:
    """High-numbered utility playlists should be treated as hidden."""
    assert not _is_likely_menu_visible_special(_feature("01000.mpls", 33_000.0))
