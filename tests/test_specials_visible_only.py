"""Tests for specials visible-only filtering in remux dry-run plans."""

from pathlib import Path

import pytest

from bdpl.analyze import scan_disc
from bdpl.bdmv.clpi import parse_clpi_dir
from bdpl.bdmv.mpls import parse_mpls_dir
from bdpl.export.mkv_chapters import get_specials_dry_run

_DISC5 = Path(__file__).parent / "fixtures" / "disc5"


@pytest.fixture
def disc5_analysis():
    """Return analyzed disc5 fixture for specials filtering tests."""
    if not (_DISC5 / "PLAYLIST").is_dir():
        pytest.skip("disc5 fixture not available")

    playlists = parse_mpls_dir(_DISC5 / "PLAYLIST")
    clips = parse_clpi_dir(_DISC5 / "CLIPINF")
    return scan_disc(_DISC5, playlists, clips)


def test_specials_dry_run_visible_only_filters_hidden(disc5_analysis) -> None:
    """Visible-only mode should keep only menu-visible specials."""
    all_plans = get_specials_dry_run(disc5_analysis, out_dir="./Episodes")
    visible_plans = get_specials_dry_run(
        disc5_analysis,
        out_dir="./Episodes",
        visible_only=True,
    )

    assert len(all_plans) == 14
    assert len(visible_plans) == 11


def test_specials_dry_run_visible_only_excludes_hidden_playlists(disc5_analysis) -> None:
    """Hidden utility playlists should be excluded in visible-only mode."""
    visible_plans = get_specials_dry_run(
        disc5_analysis,
        out_dir="./Episodes",
        visible_only=True,
    )
    playlists = {Path(plan["output"]).name for plan in visible_plans}

    assert not any("01000" in name for name in playlists)
    assert not any("01001" in name for name in playlists)
    assert not any("00100" in name for name in playlists)
