from __future__ import annotations

from dataclasses import dataclass, field


def ticks_to_ms(ticks: int) -> float:
    """Convert 45 kHz ticks to milliseconds."""
    return ticks / 45.0


@dataclass(slots=True)
class StreamInfo:
    pid: int
    stream_type: int
    codec: str
    lang: str = ""
    extra: dict = field(default_factory=dict)


@dataclass(slots=True)
class PlayItem:
    clip_id: str
    m2ts: str
    in_time: int
    out_time: int
    connection_condition: int
    streams: list[StreamInfo]
    label: str = "UNKNOWN"

    @property
    def duration_ticks(self) -> int:
        return self.out_time - self.in_time

    @property
    def duration_ms(self) -> float:
        return ticks_to_ms(self.duration_ticks)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0

    def segment_key(self, quant_ms: float = 250) -> tuple:
        in_ms = ticks_to_ms(self.in_time)
        out_ms = ticks_to_ms(self.out_time)
        q_in = round(in_ms / quant_ms) * quant_ms
        q_out = round(out_ms / quant_ms) * quant_ms
        return (self.clip_id, q_in, q_out)


@dataclass(slots=True)
class ChapterMark:
    mark_id: int
    mark_type: int
    play_item_ref: int
    timestamp: int
    entry_es_pid: int = 0
    duration_ms: float = 0.0


@dataclass(slots=True)
class Playlist:
    mpls: str
    play_items: list[PlayItem]
    chapters: list[ChapterMark] = field(default_factory=list)
    is_multi_angle: bool = False

    @property
    def duration_ms(self) -> float:
        return sum(pi.duration_ms for pi in self.play_items)

    @property
    def duration_seconds(self) -> float:
        return self.duration_ms / 1000.0

    @property
    def clip_ids(self) -> list[str]:
        return [pi.clip_id for pi in self.play_items]

    def signature_exact(self) -> tuple:
        return tuple(pi.segment_key(quant_ms=0) for pi in self.play_items)

    def signature_loose(self, quant_ms: float = 250) -> tuple:
        return tuple(pi.segment_key(quant_ms=quant_ms) for pi in self.play_items)


@dataclass(slots=True)
class ClipInfo:
    clip_id: str
    streams: list[StreamInfo]
    duration_ticks: int = 0


@dataclass(slots=True)
class SegmentRef:
    key: tuple
    clip_id: str
    in_ms: float
    out_ms: float
    duration_ms: float
    label: str = "UNKNOWN"


@dataclass(slots=True)
class Episode:
    episode: int
    playlist: str
    duration_ms: float
    confidence: float
    segments: list[SegmentRef]
    alternates: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SpecialFeature:
    """A non-episode special feature detected from disc menu structure."""

    index: int  # 1-based display order
    playlist: str  # MPLS filename
    duration_ms: float
    category: str  # creditless_op, creditless_ed, extra, preview, etc.
    chapter_start: int | None = None  # chapter index if feature is part of a multi-feature playlist


@dataclass(slots=True)
class Warning:
    code: str
    message: str
    context: dict = field(default_factory=dict)


@dataclass(slots=True)
class DiscAnalysis:
    path: str
    playlists: list[Playlist]
    clips: dict[str, ClipInfo]
    episodes: list[Episode]
    warnings: list[Warning]
    special_features: list[SpecialFeature] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)
