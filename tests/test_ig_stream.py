"""Tests for the experimental IG stream parser."""

from pathlib import Path

import pytest

from bdpl.bdmv.ig_stream import (
    IGMenuHint,
    InteractiveComposition,
    _extract_ics_data,
    extract_menu_hints,
    parse_ics,
)

_FIXTURE_DIR: Path = Path(__file__).parent / "fixtures" / "disc2"
_ICS_FILE: Path = _FIXTURE_DIR / "ics_menu.bin"


@pytest.fixture()
def ics() -> InteractiveComposition:
    """Parse the disc2 ICS fixture."""
    data: bytes = _ICS_FILE.read_bytes()
    return parse_ics(data)


# ---------------------------------------------------------------------------
# ICS parsing
# ---------------------------------------------------------------------------


def test_ics_dimensions(ics: InteractiveComposition) -> None:
    """ICS should report the correct video dimensions."""
    assert ics.width == 1920
    assert ics.height == 1080


def test_ics_page_count(ics: InteractiveComposition) -> None:
    """Disc2 menu has 4 pages."""
    assert len(ics.pages) == 4


def test_ics_pages_have_buttons(ics: InteractiveComposition) -> None:
    """Every page should have at least one button."""
    for page in ics.pages:
        assert len(page.buttons) > 0, f"Page {page.page_id} has no buttons"


def test_ics_buttons_have_positions(ics: InteractiveComposition) -> None:
    """All buttons should have non-negative coordinates."""
    for page in ics.pages:
        for btn in page.buttons:
            assert btn.x >= 0 and btn.y >= 0


# ---------------------------------------------------------------------------
# Hint extraction
# ---------------------------------------------------------------------------


def test_extract_hints_returns_actions(ics: InteractiveComposition) -> None:
    """extract_menu_hints should find actionable button commands."""
    hints: list[IGMenuHint] = extract_menu_hints(ics)
    assert len(hints) > 0


def test_hints_contain_register_sets(ics: InteractiveComposition) -> None:
    """Disc2 episode buttons should SET GPR registers."""
    hints: list[IGMenuHint] = extract_menu_hints(ics)
    reg_hints: list[IGMenuHint] = [h for h in hints if h.register_sets]
    assert len(reg_hints) > 0, "Expected some register-setting buttons"


def test_hints_episode_register_pattern(ics: InteractiveComposition) -> None:
    """Disc2 episode selection buttons SET reg6 to episode indices 0-5."""
    hints: list[IGMenuHint] = extract_menu_hints(ics)
    reg6_values: list[int] = sorted(set(h.register_sets[6] for h in hints if 6 in h.register_sets))
    # reg6 values 0-5 map to episode/segment selection
    assert 0 in reg6_values
    assert len(reg6_values) >= 4


def test_episode_chapter_pattern(ics: InteractiveComposition) -> None:
    """Disc2 has buttons that SET reg2 to chapter-mark multiples of 5.

    This confirms the 5-chapters-per-episode pattern (marks 0, 5, 10, 15).
    """
    hints: list[IGMenuHint] = extract_menu_hints(ics)
    # Find hints where register 2 is set (chapter mark index)
    reg2_values: list[int] = sorted(h.register_sets[2] for h in hints if 2 in h.register_sets)
    # Should contain at least {0, 5, 10, 15}
    expected: set[int] = {0, 5, 10, 15}
    assert expected.issubset(set(reg2_values)), (
        f"Expected reg2 values to include {expected}, got {reg2_values}"
    )


# ---------------------------------------------------------------------------
# Segment extraction
# ---------------------------------------------------------------------------


def test_extract_ics_from_padded_stream() -> None:
    """_extract_ics_data should skip non-ICS segments."""
    # Build a tiny fake PES stream: one PDS segment + one ICS segment
    pds_body: bytes = b"\x00" * 4
    pds: bytes = bytes([0x16]) + len(pds_body).to_bytes(2, "big") + pds_body
    ics_body = b"\xde\xad"
    ics_seg: bytes = bytes([0x18]) + len(ics_body).to_bytes(2, "big") + ics_body
    pes: bytes = pds + ics_seg

    result: bytes | None = _extract_ics_data(pes)
    assert result == ics_body


def test_extract_ics_returns_none_on_empty() -> None:
    """_extract_ics_data returns None when no ICS segment is present."""
    assert _extract_ics_data(b"") is None
    # Stream with only a PDS segment
    pds = bytes([0x16, 0x00, 0x02, 0x00, 0x00])
    assert _extract_ics_data(pds) is None
