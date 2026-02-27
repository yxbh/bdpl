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
        ("disc6_analysis", 2, ["00003.mpls", "00005.mpls"]),
        ("disc7_analysis", 2, ["00003.mpls", "00004.mpls"]),
        ("disc8_analysis", 2, ["00003.mpls", "00004.mpls"]),
        ("disc9_analysis", 2, ["00002.mpls", "00003.mpls"]),
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
    [  # (analysis_fixture, expected_total, expected_visible)
        ("disc1_analysis", 9, 9),  # 7 title-hint + 2 chapter-split
        ("disc2_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc3_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc5_analysis", 14, 11),  # 14 IG-derived, 11 visible content buttons
        ("disc6_analysis", 3, 3),  # 3 title-hint specials
        ("disc7_analysis", 2, 2),  # 2 title-hint specials (stream variants)
        ("disc8_analysis", 2, 2),  # 2 title-hint specials (stream variants)
        ("disc9_analysis", 0, 0),  # stream-variant playlists not deduped
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


@pytest.mark.parametrize(
    "analysis_fixture",
    [
        "disc1_analysis",
        "disc2_analysis",
        "disc3_analysis",
        "disc4_analysis",
        "disc5_analysis",
        "disc6_analysis",
        "disc7_analysis",
        "disc8_analysis",
        "disc9_analysis",
    ],
)
def test_disc_episode_segment_boundaries_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
) -> None:
    """Validate episode segment start/end boundaries and duration consistency."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)

    for episode in analysis.episodes:
        assert episode.segments

        total_segment_duration = 0.0
        for segment in episode.segments:
            assert segment.in_ms >= 0
            assert segment.out_ms > segment.in_ms
            assert segment.duration_ms > 0
            total_segment_duration += segment.duration_ms

        assert abs(total_segment_duration - episode.duration_ms) < 1.0


@pytest.mark.parametrize(
    "analysis_fixture",
    [
        "disc1_analysis",
        "disc2_analysis",
        "disc3_analysis",
        "disc4_analysis",
        "disc5_analysis",
        "disc6_analysis",
        "disc7_analysis",
        "disc8_analysis",
        "disc9_analysis",
    ],
)
def test_disc_special_boundary_semantics_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
) -> None:
    """Validate chapter-targeted special boundaries against source playlist chapters."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)
    playlists_by_name = {playlist.mpls: playlist for playlist in analysis.playlists}

    for feature in analysis.special_features:
        assert feature.duration_ms > 0
        if feature.chapter_start is None:
            continue

        playlist = playlists_by_name.get(feature.playlist)
        assert playlist is not None

        # Valid chapter index: feature should be bounded by chapter windows and
        # never exceed source playlist duration.
        if 0 <= feature.chapter_start < len(playlist.chapters):
            assert feature.duration_ms <= playlist.duration_ms
            continue

        # Out-of-range chapter index: analyzer intentionally falls back to full
        # playlist duration for robust metadata-only behavior.
        assert abs(feature.duration_ms - playlist.duration_ms) < 1.0


@pytest.mark.parametrize(
    ("analysis_fixture", "expected_chapter_split_specials"),
    [  # (analysis_fixture, expected_chapter_split_specials)
        ("disc1_analysis", 2),  # PlayPL_PM marks → 2 chapter-split entries
        ("disc2_analysis", 0),
        ("disc3_analysis", 0),
        ("disc4_analysis", 0),
        ("disc5_analysis", 0),
        ("disc6_analysis", 0),
        ("disc7_analysis", 0),
        ("disc8_analysis", 0),
        ("disc9_analysis", 0),
    ],
)
def test_disc_special_chapter_split_expectation_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
    expected_chapter_split_specials: int,
) -> None:
    """Validate chapter-targeted special feature counts across key fixtures."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)

    chapter_split = sum(
        1 for feature in analysis.special_features if feature.chapter_start is not None
    )
    assert chapter_split == expected_chapter_split_specials


@pytest.mark.parametrize(
    ("analysis_fixture", "expected_title"),
    [
        ("disc2_analysis", "TEST DISC 2"),
        ("disc6_analysis", "TEST DISC 6"),
        ("disc7_analysis", "TEST DISC 7 VOL 2"),
        ("disc8_analysis", "TEST DISC 8"),
        ("disc9_analysis", "TEST DISC 9"),
    ],
)
def test_disc_title_extraction_matrix(
    request: pytest.FixtureRequest,
    analysis_fixture: str,
    expected_title: str,
) -> None:
    """Validate disc title extraction from META/DL/bdmt_eng.xml."""
    analysis: DiscAnalysis = request.getfixturevalue(analysis_fixture)
    assert analysis.disc_title == expected_title
