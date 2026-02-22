"""Unit tests for episode ordering safeguards."""

from __future__ import annotations

from bdpl.analyze.ordering import order_episodes
from bdpl.model import PlayItem, Playlist


def _ticks(seconds: float) -> int:
    """Convert seconds to 45 kHz ticks for test fixtures."""
    return int(seconds * 45_000)


def _pi(clip_id: str, start_s: float, end_s: float, label: str = "BODY") -> PlayItem:
    """Build a play item for ordering tests."""
    return PlayItem(
        clip_id=clip_id,
        m2ts=f"{clip_id}.m2ts",
        in_time=_ticks(start_s),
        out_time=_ticks(end_s),
        connection_condition=0,
        streams=[],
        label=label,
    )


def test_order_episodes_uses_classified_episode_only() -> None:
    """Exclude long extras when explicit playlist classifications are available."""
    episode_pl = Playlist(
        mpls="00001.mpls",
        play_items=[_pi("00010", 0.0, 700.0, label="BODY")],
    )
    long_extra_pl = Playlist(
        mpls="00002.mpls",
        play_items=[_pi("00020", 0.0, 650.0, label="UNKNOWN")],
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
    with_preview = Playlist(
        mpls="00001.mpls",
        play_items=[
            _pi("00010", 10.0, 710.0, label="BODY"),
            _pi("00011", 0.0, 12.0, label="PREVIEW"),
        ],
    )
    body_only = Playlist(
        mpls="00012.mpls",
        play_items=[_pi("00010", 10.0, 709.5, label="BODY")],
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
