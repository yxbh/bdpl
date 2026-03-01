"""Matrix-style integration checks across bundled disc fixtures."""

from __future__ import annotations

import pytest

from bdpl.model import DiscAnalysis

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("analysis_fixture", "expected_episode_count", "expected_episode_playlists"),
    [
        ("disc1_analysis", 3, ["00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc14_analysis", 4, ["00002.mpls", "00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc3_analysis", 4, ["00002.mpls", "00002.mpls", "00002.mpls", "00002.mpls"]),
        ("disc4_analysis", 1, ["00002.mpls"]),
        ("disc5_analysis", 1, ["00001.mpls"]),
        ("disc6_analysis", 2, ["00003.mpls", "00005.mpls"]),
        ("disc7_analysis", 2, ["00003.mpls", "00004.mpls"]),
        ("disc8_analysis", 2, ["00003.mpls", "00004.mpls"]),
        ("disc9_analysis", 1, ["00002.mpls"]),
        ("disc10_analysis", 5, ["00002.mpls"] * 5),
        ("disc11_analysis", 6, ["00002.mpls"] * 6),
        ("disc12_analysis", 5, ["00002.mpls"] * 5),
        ("disc13_analysis", 6, ["00002.mpls"] * 6),
        ("disc15_analysis", 4, ["00002.mpls"] * 4),
        ("disc16_analysis", 4, ["00002.mpls"] * 4),
        ("disc17_analysis", 1, ["00002.mpls"]),
        ("disc18_analysis", 1, ["00002.mpls"]),
        ("disc19_analysis", 1, ["00002.mpls"]),
        ("disc20_analysis", 1, ["00002.mpls"]),
        ("disc21_analysis", 1, ["00002.mpls"]),
        ("disc22_analysis", 5, ["00002.mpls"] * 5),
        ("disc23_analysis", 5, ["00002.mpls"] * 5),
        ("disc24_analysis", 3, ["00002.mpls"] * 3),
        ("disc25_analysis", 1, ["00002.mpls"]),
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
        ("disc14_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc3_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc5_analysis", 14, 11),  # 14 IG-derived, 11 visible content buttons
        ("disc6_analysis", 3, 3),  # 3 title-hint specials
        ("disc7_analysis", 2, 2),  # 2 title-hint specials (stream variants)
        ("disc8_analysis", 3, 3),  # 2 commentaries + 1 lyrics ending
        ("disc9_analysis", 1, 1),  # alt-audio variant detected as special
        ("disc10_analysis", 3, 3),  # 3 commentaries (play_all-only episodes)
        ("disc11_analysis", 1, 1),  # 1 short extra
        ("disc12_analysis", 3, 3),  # 3 commentaries (play_all-only episodes)
        ("disc13_analysis", 9, 9),  # 2 commentary + 5 creditless + 2 extra
        ("disc15_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc16_analysis", 4, 4),  # 2 extras + 2 creditless EDs
        ("disc17_analysis", 1, 1),  # 1 digital archive
        ("disc18_analysis", 2, 2),  # 1 extra + 1 creditless ED
        ("disc19_analysis", 1, 1),  # 1 digital archive (hint-backed)
        ("disc20_analysis", 1, 1),  # 1 extra (trailer)
        ("disc21_analysis", 1, 1),  # 1 digital archive
        ("disc22_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc23_analysis", 0, 0),  # chapter-split disc with no extras
        ("disc24_analysis", 8, 8),  # 1 extra + 3 commentary + 4 creditless ED
        ("disc25_analysis", 1, 1),  # 1 digital archive
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
        "disc14_analysis",
        "disc3_analysis",
        "disc4_analysis",
        "disc5_analysis",
        "disc6_analysis",
        "disc7_analysis",
        "disc8_analysis",
        "disc9_analysis",
        "disc10_analysis",
        "disc11_analysis",
        "disc12_analysis",
        "disc13_analysis",
        "disc15_analysis",
        "disc16_analysis",
        "disc17_analysis",
        "disc18_analysis",
        "disc19_analysis",
        "disc20_analysis",
        "disc21_analysis",
        "disc22_analysis",
        "disc23_analysis",
        "disc24_analysis",
        "disc25_analysis",
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
        "disc14_analysis",
        "disc3_analysis",
        "disc4_analysis",
        "disc5_analysis",
        "disc6_analysis",
        "disc7_analysis",
        "disc8_analysis",
        "disc9_analysis",
        "disc10_analysis",
        "disc11_analysis",
        "disc12_analysis",
        "disc13_analysis",
        "disc15_analysis",
        "disc16_analysis",
        "disc17_analysis",
        "disc18_analysis",
        "disc19_analysis",
        "disc20_analysis",
        "disc21_analysis",
        "disc22_analysis",
        "disc23_analysis",
        "disc24_analysis",
        "disc25_analysis",
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
        ("disc14_analysis", 0),
        ("disc3_analysis", 0),
        ("disc4_analysis", 0),
        ("disc5_analysis", 0),
        ("disc6_analysis", 0),
        ("disc7_analysis", 0),
        ("disc8_analysis", 0),
        ("disc9_analysis", 0),
        ("disc10_analysis", 0),
        ("disc11_analysis", 0),
        ("disc12_analysis", 0),
        ("disc13_analysis", 0),
        ("disc15_analysis", 0),
        ("disc16_analysis", 0),
        ("disc17_analysis", 0),
        ("disc18_analysis", 0),
        ("disc19_analysis", 0),
        ("disc20_analysis", 0),
        ("disc21_analysis", 0),
        ("disc22_analysis", 0),
        ("disc23_analysis", 0),
        ("disc24_analysis", 0),
        ("disc25_analysis", 0),
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
        ("disc14_analysis", "TEST DISC 14"),
        ("disc6_analysis", "TEST DISC 6"),
        ("disc7_analysis", "TEST DISC 7 VOL 2"),
        ("disc8_analysis", "TEST DISC 8"),
        ("disc9_analysis", "TEST DISC 9"),
        ("disc10_analysis", "TEST DISC 10"),
        ("disc11_analysis", "TEST DISC 11"),
        ("disc12_analysis", "TEST DISC 12"),
        ("disc13_analysis", "TEST DISC 13"),
        ("disc15_analysis", "TEST DISC 15"),
        ("disc16_analysis", "TEST DISC 16"),
        ("disc17_analysis", "TEST DISC 17"),
        ("disc18_analysis", "TEST DISC 18"),
        ("disc19_analysis", "TEST DISC 19"),
        ("disc20_analysis", "TEST DISC 20"),
        ("disc21_analysis", "TEST DISC 21"),
        ("disc22_analysis", "TEST DISC 22"),
        ("disc23_analysis", "TEST DISC 23"),
        ("disc24_analysis", "TEST DISC 24"),
        ("disc25_analysis", "TEST DISC 25"),
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
