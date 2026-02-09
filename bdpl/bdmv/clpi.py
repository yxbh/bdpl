"""Parser for Blu-ray CLPI (CLip Information) files."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from bdpl.bdmv.reader import BinaryReader
from bdpl.model import ClipInfo, StreamInfo

# ── codec lookup ─────────────────────────────────────────────────────

_VIDEO_TYPES = {0x01, 0x02, 0x1B, 0x24, 0xEA}
_AUDIO_TYPES = {0x03, 0x04, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0xA1, 0xA2}
_PG_TYPES = {0x90}
_IG_TYPES = {0x91}
_TEXT_TYPES = {0x92}

_CODEC_NAME: dict[int, str] = {
    0x01: "MPEG-1",
    0x02: "MPEG-2",
    0x1B: "H.264",
    0x24: "HEVC",
    0xEA: "VC-1",
    0x03: "MPEG-1 Audio",
    0x04: "MPEG-2 Audio",
    0x80: "LPCM",
    0x81: "AC-3",
    0x82: "DTS",
    0x83: "TrueHD",
    0x84: "E-AC-3",
    0x85: "DTS-HD HR",
    0x86: "DTS-HD MA",
    0xA1: "DD+ Secondary",
    0xA2: "DTS-HD Secondary",
    0x90: "PGS",
    0x91: "IG",
    0x92: "Text Subtitle",
}

# ── stream attribute parsing ─────────────────────────────────────────


def _parse_stream_attrs(
    r: BinaryReader, coding_type: int, attr_len: int,
) -> tuple[str, dict]:
    """Return (lang, extra) for a stream based on its coding_type."""
    lang = ""
    extra: dict = {}
    try:
        if coding_type in _VIDEO_TYPES:
            packed = r.u8()
            extra["video_format"] = packed >> 4
            extra["frame_rate"] = packed & 0x0F
        elif coding_type in _AUDIO_TYPES:
            packed = r.u8()
            extra["channel_layout"] = packed >> 4
            extra["sample_rate"] = packed & 0x0F
            lang = r.read_string(3)
        elif coding_type in _PG_TYPES:
            lang = r.read_string(3)
        elif coding_type in _IG_TYPES:
            lang = r.read_string(3)
        elif coding_type in _TEXT_TYPES:
            extra["char_code"] = r.u8()
            lang = r.read_string(3)
    except Exception:
        pass  # skip unparseable attributes gracefully
    return lang, extra


# ── section parsers ──────────────────────────────────────────────────


def _parse_program_info(r: BinaryReader) -> list[StreamInfo]:
    """Parse ProgramInfo section and return a flat list of StreamInfo."""
    streams: list[StreamInfo] = []
    _length = r.u32()
    if _length == 0:
        return streams
    r.skip(1)  # reserved
    num_programs = r.u8()
    for _ in range(num_programs):
        r.skip(4)  # SPN_program_sequence_start
        r.skip(2)  # program_map_PID
        num_streams = r.u8()
        r.skip(1)  # num_groups
        for _ in range(num_streams):
            stream_pid = r.u16()
            attr_len = r.u8()
            attr_start = r.tell()
            try:
                coding_type = r.u8()
                codec = _CODEC_NAME.get(coding_type, f"0x{coding_type:02X}")
                lang, extra = _parse_stream_attrs(r, coding_type, attr_len)
                streams.append(
                    StreamInfo(
                        pid=stream_pid,
                        stream_type=coding_type,
                        codec=codec,
                        lang=lang,
                        extra=extra,
                    )
                )
            except Exception:
                pass  # skip malformed stream entry
            # always advance to the end of the attribute block
            r.seek(attr_start + attr_len)
    return streams


# ── public API ───────────────────────────────────────────────────────


def parse_clpi(source: Union[BinaryReader, str, Path]) -> ClipInfo:
    """Parse a CLPI file and return a ClipInfo object."""
    if isinstance(source, BinaryReader):
        return _parse_clpi_reader(source)
    path = Path(source)
    clip_id = path.stem
    with BinaryReader(path) as r:
        return _parse_clpi_reader(r, clip_id=clip_id)


def _parse_clpi_reader(r: BinaryReader, *, clip_id: str = "") -> ClipInfo:
    """Internal: parse from an already-open BinaryReader."""
    # ── header ──
    magic = r.read_string(4)
    if magic != "HDMV":
        raise ValueError(f"Not a CLPI file: bad magic {magic!r}")
    _version = r.read_string(4)  # "0100" or "0200"
    _seq_info_start = r.u32()
    program_info_start = r.u32()
    _cpi_start = r.u32()
    _clip_mark_start = r.u32()
    _ext_data_start = r.u32()

    # ── ClipInfo section (at offset 40) ──
    r.seek(40)
    _ci_length = r.u32()
    r.skip(2)  # reserved
    _clip_stream_type = r.u8()
    _application_type = r.u8()
    r.skip(4)  # reserved / flags
    _ts_recording_rate = r.u32()
    _num_source_packets = r.u32()

    # ── ProgramInfo section ──
    r.seek(program_info_start)
    streams = _parse_program_info(r)

    return ClipInfo(clip_id=clip_id, streams=streams)


def parse_clpi_dir(clipinf_dir: Union[str, Path]) -> dict[str, ClipInfo]:
    """Parse all *.clpi files in a directory. Returns dict keyed by clip_id (e.g. '00007')."""
    result: dict[str, ClipInfo] = {}
    clipinf = Path(clipinf_dir)
    for path in sorted(clipinf.glob("*.clpi")):
        try:
            clip = parse_clpi(path)
            result[clip.clip_id] = clip
        except Exception:
            continue  # skip unparseable files
    return result
