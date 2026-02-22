"""Unit tests for episode ordering safeguards."""

from __future__ import annotations

from bdpl.analyze.ordering import order_episodes
from tests.builders import build_play_item, build_playlist


def test_order_episodes_uses_classified_episode_only() -> None:
    """Exclude long extras when explicit playlist classifications are available."""
    episode_pl = build_playlist(
        mpls="00001.mpls",
        items=[build_play_item("00010", 0.0, 700.0, label="BODY")],
    )
    long_extra_pl = build_playlist(
        mpls="00002.mpls",
        items=[build_play_item("00020", 0.0, 650.0, label="UNKNOWN")],
    )

    episodes = order_episodes(
        [episode_pl, long_extra_pl],
        play_all_playlists=[],
        classifications={
            "00001.mpls": "episode",
            "00002.mpls": "extra",
        },
    )

    assert len(episodes) == 1
    assert episodes[0].playlist == "00001.mpls"


def test_order_episodes_collapses_body_equivalent_variants() -> None:
    """Treat playlists with identical BODY content as one episode variant."""
    with_preview = build_playlist(
        mpls="00001.mpls",
        items=[
            build_play_item("00010", 10.0, 710.0, label="BODY"),
            build_play_item("00011", 0.0, 12.0, label="PREVIEW"),
        ],
    )
    body_only = build_playlist(
        mpls="00012.mpls",
        items=[build_play_item("00010", 10.0, 709.5, label="BODY")],
    )

    episodes = order_episodes(
        [with_preview, body_only],
        play_all_playlists=[],
        classifications={
            "00001.mpls": "episode",
            "00012.mpls": "episode",
        },
    )

    assert len(episodes) == 1
    assert episodes[0].playlist == "00001.mpls"
