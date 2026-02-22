"""Integration tests for the disc4 fixture scan results."""

from bdpl.analyze.__init__ import _maybe_keep_single_title_episode
from bdpl.model import DiscAnalysis, Episode, SegmentRef


def test_disc4_finds_one_episode(disc4_analysis: DiscAnalysis) -> None:
    """Scan disc4 and verify one main episode is inferred."""
    assert len(disc4_analysis.episodes) == 1


def test_disc4_episode_numbers_are_ordered(disc4_analysis: DiscAnalysis) -> None:
    """Verify inferred episode sequence is [1] for disc4."""
    assert [episode.episode for episode in disc4_analysis.episodes] == [1]


def test_disc4_detects_digital_archive_playlist(disc4_analysis: DiscAnalysis) -> None:
    """Verify digital archive playlist classification is present."""
    classes = disc4_analysis.analysis.get("classifications", {})
    assert classes.get("00003.mpls") == "digital_archive"


def test_disc4_keeps_single_main_title_when_archive_title_exists(
    disc4_analysis: DiscAnalysis,
) -> None:
    """Guard against chapter-splitting when hints show one main + archive title."""
    hints = disc4_analysis.analysis.get("disc_hints", {})
    title_playlists = hints.get("title_playlists", {})
    classes = disc4_analysis.analysis.get("classifications", {})

    assert title_playlists.get(0) == [2]
    assert title_playlists.get(1) == [3]
    assert classes.get("00003.mpls") == "digital_archive"

    assert len(disc4_analysis.episodes) == 1
    assert disc4_analysis.episodes[0].playlist == "00002.mpls"

    main = next(pl for pl in disc4_analysis.playlists if pl.mpls == "00002.mpls")
    assert abs(disc4_analysis.episodes[0].duration_ms - main.duration_ms) < 1.0


def test_single_title_collapse_handles_three_or_more_inferred_episodes(
    disc4_analysis: DiscAnalysis,
) -> None:
    """Collapse helper should merge any 2+ chapter-split episodes when guarded hints match."""
    fake_eps = [
        Episode(
            episode=1,
            playlist="00002.mpls",
            duration_ms=1_000.0,
            confidence=0.6,
            segments=[
                SegmentRef(
                    key=("00005", 0, 1_000),
                    clip_id="00005",
                    in_ms=0.0,
                    out_ms=1_000.0,
                    duration_ms=1_000.0,
                    label="BODY",
                )
            ],
        ),
        Episode(
            episode=2,
            playlist="00002.mpls",
            duration_ms=1_000.0,
            confidence=0.6,
            segments=[
                SegmentRef(
                    key=("00005", 1_000, 2_000),
                    clip_id="00005",
                    in_ms=1_000.0,
                    out_ms=2_000.0,
                    duration_ms=1_000.0,
                    label="BODY",
                )
            ],
        ),
        Episode(
            episode=3,
            playlist="00002.mpls",
            duration_ms=1_000.0,
            confidence=0.6,
            segments=[
                SegmentRef(
                    key=("00005", 2_000, 3_000),
                    clip_id="00005",
                    in_ms=2_000.0,
                    out_ms=3_000.0,
                    duration_ms=1_000.0,
                    label="BODY",
                )
            ],
        ),
    ]

    collapsed = _maybe_keep_single_title_episode(
        fake_eps,
        disc4_analysis.playlists,
        disc4_analysis.analysis.get("disc_hints", {}),
        disc4_analysis.analysis.get("classifications", {}),
    )

    assert len(collapsed) == 1
    assert collapsed[0].playlist == "00002.mpls"
