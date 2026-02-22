"""Matrix-style integration checks across bundled disc fixtures."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("analysis_fixture", "expected_episode_count", "expected_episode_playlists"),
    [
        ("disc1_analysis", 3, ["00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc2_analysis", 4, ["00002.mpls", "00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc3_analysis", 4, ["00002.mpls", "00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc4_analysis", 1, ["00002.mpls"]),
        ("disc5_analysis", 1, ["00001.mpls"]),
    ],
)
def test_disc_episode_expectation_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
    expected_episode_count: int,
    expected_episode_playlists: list[str],
) -> None:
    """Validate core episode-count and playlist expectations for each fixture."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)

    assert len(analysis.episodes) == expected_episode_count
    assert [episode.playlist for episode in analysis.episodes] == expected_episode_playlists


@pytest.mark.parametrize(
    ("analysis_fixture", "expected_total", "expected_visible"),
    [
        ("disc5_analysis", 14, 11),
    ],
)
def test_disc_special_visibility_expectation_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
    expected_total: int,
    expected_visible: int,
) -> None:
    """Validate total and menu-visible special feature counts for target fixtures."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)

    total = len(analysis.special_features)
    visible = sum(1 for feature in analysis.special_features if feature.menu_visible)

    assert total == expected_total
    assert visible == expected_visible
