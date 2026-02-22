"""Tests for specials visible-only filtering in remux dry-run plans."""

from bdpl.export.mkv_chapters import get_specials_dry_run
from bdpl.model import DiscAnalysis


def test_specials_dry_run_visible_only_filters_hidden(disc5_analysis: DiscAnalysis) -> None:
    """Visible-only mode should keep only menu-visible specials."""
    all_plans = get_specials_dry_run(disc5_analysis, out_dir="./Episodes")
    visible_plans = get_specials_dry_run(
        disc5_analysis,
        out_dir="./Episodes",
        visible_only=True,
    )

    assert len(all_plans) == 14
    assert len(visible_plans) == 11


def test_specials_dry_run_visible_only_excludes_hidden_playlists(
    disc5_analysis: DiscAnalysis,
) -> None:
    """Hidden utility playlists should be excluded in visible-only mode."""
    visible_plans = get_specials_dry_run(
        disc5_analysis,
        out_dir="./Episodes",
        visible_only=True,
    )
    playlists = {plan["playlist"] for plan in visible_plans}

    assert "01000.mpls" not in playlists
    assert "01001.mpls" not in playlists
    assert "00100.mpls" not in playlists
