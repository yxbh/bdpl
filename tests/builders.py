"""Shared test-data builders for bdpl tests."""

from __future__ import annotations

from pathlib import Path

from bdpl.model import DiscAnalysis, PlayItem, Playlist, SpecialFeature


def ticks_from_seconds(seconds: float) -> int:
    """Convert seconds to 45 kHz ticks."""
    return int(seconds * 45_000)


def build_play_item(
    clip_id: str,
    start_s: float,
    end_s: float,
    *,
    label: str = "UNKNOWN",
) -> PlayItem:
    """Build a minimal PlayItem for tests."""
    return PlayItem(
        clip_id=clip_id,
        m2ts=f"{clip_id}.m2ts",
        in_time=ticks_from_seconds(start_s),
        out_time=ticks_from_seconds(end_s),
        connection_condition=0,
        streams=[],
        label=label,
    )


def build_playlist(mpls: str, items: list[PlayItem]) -> Playlist:
    """Build a playlist from play items."""
    return Playlist(mpls=mpls, play_items=items)


def build_special_feature(
    *,
    index: int,
    playlist: str,
    duration_ms: float,
    category: str = "extra",
    menu_visible: bool = True,
) -> SpecialFeature:
    """Build a SpecialFeature for tests."""
    return SpecialFeature(
        index=index,
        playlist=playlist,
        duration_ms=duration_ms,
        category=category,
        menu_visible=menu_visible,
    )


def build_disc_analysis(
    *,
    playlists: list[Playlist] | None = None,
    path: str | Path = "C:/disc/BDMV",
    classifications: dict[str, str] | None = None,
    special_features: list[SpecialFeature] | None = None,
) -> DiscAnalysis:
    """Build a minimal DiscAnalysis for tests."""
    return DiscAnalysis(
        path=str(path),
        playlists=playlists or [],
        clips={},
        episodes=[],
        warnings=[],
        special_features=special_features or [],
        analysis={"classifications": classifications or {}},
    )
