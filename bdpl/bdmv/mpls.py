"""Parser for Blu-ray MPLS (Movie PlayList) files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from bdpl.bdmv.reader import BinaryReader
from bdpl.model import ChapterMark, PlayItem, Playlist, StreamInfo

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Codec look-ups
# ---------------------------------------------------------------------------

_CODING_TYPE: dict[int, str] = {
    0x01: "MPEG-1 Video",
    0x02: "MPEG-2 Video",
    0x1B: "H.264/AVC",
    0x24: "HEVC",
    0x03: "MPEG-1 Audio",
    0x04: "MPEG-2 Audio",
    0x80: "LPCM",
    0x81: "AC-3",
    0x82: "DTS",
    0x83: "TrueHD",
    0x84: "AC-3+",
    0x85: "DTS-HD HR",
    0x86: "DTS-HD MA",
    0xA1: "DD+ secondary",
    0xA2: "DTS-HD secondary",
    0x90: "PGS",
    0x91: "IG",
    0x92: "Text subtitle",
}

_VIDEO_CODECS = {0x01, 0x02, 0x1B, 0x24}
_AUDIO_CODECS = {0x03, 0x04, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0xA1, 0xA2}
_PG_IG_CODECS = {0x90, 0x91, 0x92}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_stream_entry(r: BinaryReader) -> tuple[int, int]:
    """Parse a stream entry and return *(stream_type, pid)*."""
    entry_len = r.u8()
    entry_start = r.tell()
    stream_type = r.u8()
    pid = 0
    if stream_type == 0x01:
        pid = r.u16()
    elif stream_type == 0x02:
        pid = r.u16()
        r.skip(2)  # sub_path_id, sub_clip_entry_id
    elif stream_type in (0x03, 0x04):
        r.skip(1)  # sub_path_id
        pid = r.u16()
    r.seek(entry_start + entry_len)
    return stream_type, pid


def _parse_stream_attrs(r: BinaryReader) -> tuple[str, str, dict]:
    """Parse stream attributes and return *(codec, lang, extra)*."""
    attr_len = r.u8()
    attr_start = r.tell()
    coding_type = r.u8()
    codec = _CODING_TYPE.get(coding_type, f"0x{coding_type:02X}")
    lang = ""
    extra: dict = {}

    if coding_type in _VIDEO_CODECS:
        packed = r.u8()
        extra["video_format"] = (packed >> 4) & 0x0F
        extra["frame_rate"] = packed & 0x0F
    elif coding_type in _AUDIO_CODECS:
        packed = r.u8()
        extra["audio_format"] = (packed >> 4) & 0x0F
        extra["sample_rate"] = packed & 0x0F
        lang = r.read_string(3)
    elif coding_type in _PG_IG_CODECS:
        lang = r.read_string(3)

    r.seek(attr_start + attr_len)
    return codec, lang, extra


def _parse_stn_table(r: BinaryReader) -> list[StreamInfo]:
    """Parse the STN_table and return a list of :class:`StreamInfo`."""
    stn_len = r.u16()
    if stn_len == 0:
        return []
    stn_start = r.tell()
    r.skip(2)  # reserved

    num_video = r.u8()
    num_audio = r.u8()
    num_pg = r.u8()
    num_ig = r.u8()
    num_secondary_audio = r.u8()
    num_secondary_video = r.u8()
    num_pip_pg = r.u8()
    r.skip(5)  # reserved

    streams: list[StreamInfo] = []
    total = (
        num_video
        + num_audio
        + num_pg
        + num_ig
        + num_secondary_audio
        + num_secondary_video
        + num_pip_pg
    )
    for _ in range(total):
        stream_type, pid = _parse_stream_entry(r)
        codec, lang, extra = _parse_stream_attrs(r)
        extra["stream_type"] = stream_type
        streams.append(
            StreamInfo(pid=pid, stream_type=stream_type, codec=codec, lang=lang, extra=extra)
        )

    r.seek(stn_start + stn_len)
    return streams


def _parse_play_item(r: BinaryReader) -> PlayItem:
    """Parse a single PlayItem."""
    pi_len = r.u16()
    pi_start = r.tell()

    clip_name = r.read_string(5)
    r.read_string(4)

    flags = r.u16()
    is_multi_angle = bool((flags >> 4) & 1)
    connection_condition = flags & 0x0F

    r.skip(1)  # ref_to_STC_id
    in_time = r.u32()
    out_time = r.u32()
    r.skip(8)  # UO_mask_table
    r.skip(1)  # PlayItem_random_access_flag + reserved
    still_mode = r.u8()
    if still_mode == 0x01:
        r.skip(2)  # still_time
    else:
        r.skip(2)  # reserved

    if is_multi_angle:
        angle_count = r.u8()
        r.skip(1)  # flags byte
        for _ in range(angle_count - 1):
            r.skip(10)  # clip_name(5) + codec_id(4) + STC_id(1)

    # STN_table
    try:
        streams = _parse_stn_table(r)
    except Exception:
        log.warning("Failed to parse STN_table for clip %s", clip_name, exc_info=True)
        streams = []

    r.seek(pi_start + pi_len)

    return PlayItem(
        clip_id=clip_name,
        m2ts=f"{clip_name}.m2ts",
        in_time=in_time,
        out_time=out_time,
        connection_condition=connection_condition,
        streams=streams,
    )


def _parse_play_list(r: BinaryReader) -> tuple[list[PlayItem], bool]:
    """Parse the PlayList section and return *(play_items, is_multi_angle)*."""
    r.skip(4)  # section length
    r.skip(2)  # reserved
    num_items = r.u16()
    r.skip(2)  # num_sub_paths (not needed for play items)

    is_multi_angle = False
    items: list[PlayItem] = []
    for idx in range(num_items):
        try:
            item = _parse_play_item(r)
            items.append(item)
        except Exception:
            log.warning("Failed to parse PlayItem %d", idx, exc_info=True)
    return items, is_multi_angle


def _parse_marks(r: BinaryReader) -> list[ChapterMark]:
    """Parse the PlayListMark section."""
    r.skip(4)  # section length
    num_marks = r.u16()
    marks: list[ChapterMark] = []
    for i in range(num_marks):
        r.skip(1)  # reserved
        mark_type = r.u8()
        ref_item = r.u16()
        timestamp = r.u32()
        entry_es_pid = r.u16()
        duration = r.u32()
        marks.append(
            ChapterMark(
                mark_id=i,
                mark_type=mark_type,
                play_item_ref=ref_item,
                timestamp=timestamp,
                entry_es_pid=entry_es_pid,
                duration_ms=duration / 45.0,
            )
        )
    return marks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_mpls(source: Union[BinaryReader, str, Path]) -> Playlist:
    """Parse an MPLS file and return a :class:`Playlist` object."""
    if isinstance(source, BinaryReader):
        return _parse_mpls_reader(source, "")
    path = Path(source)
    with BinaryReader(path) as r:
        return _parse_mpls_reader(r, path.name)


def _parse_mpls_reader(r: BinaryReader, name: str) -> Playlist:
    magic = r.read_string(4)
    if magic != "MPLS":
        raise ValueError(f"Not an MPLS file (magic={magic!r})")
    _version = r.read_string(4)

    playlist_start = r.u32()
    mark_start = r.u32()
    _ext_start = r.u32()

    # PlayList section
    r.seek(playlist_start)
    items, is_multi_angle = _parse_play_list(r)

    # PlayListMark section
    chapters: list[ChapterMark] = []
    try:
        r.seek(mark_start)
        chapters = _parse_marks(r)
    except Exception:
        log.warning("Failed to parse PlayListMark section for %s", name, exc_info=True)

    return Playlist(
        mpls=name,
        play_items=items,
        chapters=chapters,
        is_multi_angle=is_multi_angle,
    )


def parse_mpls_dir(playlist_dir: Union[str, Path]) -> list[Playlist]:
    """Parse all ``*.mpls`` files in *playlist_dir*, sorted by filename."""
    d = Path(playlist_dir)
    results: list[Playlist] = []
    for p in sorted(d.glob("*.mpls")):
        try:
            results.append(parse_mpls(p))
        except Exception:
            log.warning("Skipping unparseable MPLS %s", p.name, exc_info=True)
    return results
