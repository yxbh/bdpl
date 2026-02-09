"""Experimental parser for Blu-ray IG (Interactive Graphics) menu streams.

Parses the Interactive Composition Segment (ICS) from IG streams to extract
button navigation commands.  These can reveal episode → playlist / chapter
mappings embedded in the disc menu structure.

Status: **EXPERIMENTAL** — covers the common cases observed in anime Blu-ray
discs.  Edge cases (BD-J overlays, multi-segment ICS, etc.) are not handled.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path

from bdpl.bdmv.movieobject_bdmv import NavCommand, _decode_nav_command

log = logging.getLogger(__name__)

# IG stream PIDs: 0x1400-0x141F per BD-ROM spec
_IG_PID_MIN = 0x1400
_IG_PID_MAX = 0x141F

# Segment types within the IG PES stream
_SEG_ICS = 0x18  # Interactive Composition Segment

# M2TS packet geometry
_M2TS_PKT = 192
_TS_HDR = 4  # extra 4-byte timestamp prepended to each TS packet

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class IGButton:
    """A button in an IG menu page."""

    button_id: int
    x: int
    y: int
    auto_action: bool
    commands: list[NavCommand]


@dataclass(slots=True)
class IGPage:
    """One page of the interactive menu."""

    page_id: int
    default_button: int
    default_activated: int
    buttons: list[IGButton]


@dataclass(slots=True)
class InteractiveComposition:
    """Parsed Interactive Composition Segment (ICS)."""

    width: int
    height: int
    pages: list[IGPage]


@dataclass(slots=True)
class IGMenuHint:
    """An actionable hint extracted from one IG button."""

    page_id: int
    button_id: int
    playlist: int | None = None
    mark: int | None = None
    jump_title: int | None = None
    register_sets: dict[int, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# M2TS demuxing
# ---------------------------------------------------------------------------


def demux_ig_stream(
    m2ts_path: Path | str,
    ig_pid: int | None = None,
) -> bytes:
    """Extract IG PES payload data from an m2ts file.

    If *ig_pid* is ``None``, auto-detects the first PID in 0x1400–0x141F.
    Returns concatenated PES payload bytes (segment headers included).
    """
    data = Path(m2ts_path).read_bytes()
    pes_data = bytearray()
    pos = 0
    found_pid = ig_pid

    while pos + _M2TS_PKT <= len(data):
        ts = data[pos + _TS_HDR : pos + _M2TS_PKT]
        if ts[0] != 0x47:
            pos += 1
            continue

        pid = ((ts[1] & 0x1F) << 8) | ts[2]
        adapt = (ts[3] >> 4) & 3
        pusi = (ts[1] >> 6) & 1

        if found_pid is None and _IG_PID_MIN <= pid <= _IG_PID_MAX:
            found_pid = pid
            log.debug("Auto-detected IG PID: 0x%04X", found_pid)

        if pid == found_pid:
            offset = 4
            if adapt in (2, 3):
                offset = 5 + ts[4]
            if adapt in (1, 3):
                payload = ts[offset:]
                if pusi and len(payload) >= 9 and payload[:3] == b"\x00\x00\x01":
                    hdr_len = payload[8]
                    pes_data.extend(payload[9 + hdr_len :])
                else:
                    pes_data.extend(payload)

        pos += _M2TS_PKT

    return bytes(pes_data)


# ---------------------------------------------------------------------------
# Segment extraction
# ---------------------------------------------------------------------------


def _extract_ics_data(pes_data: bytes) -> bytes | None:
    """Return the body of the first ICS segment found in *pes_data*."""
    pos = 0
    while pos + 3 <= len(pes_data):
        seg_type = pes_data[pos]
        seg_len = (pes_data[pos + 1] << 8) | pes_data[pos + 2]
        if seg_type == _SEG_ICS:
            return pes_data[pos + 3 : pos + 3 + seg_len]
        if seg_len == 0:
            break
        pos += 3 + seg_len
    return None


# ---------------------------------------------------------------------------
# ICS parsing
# ---------------------------------------------------------------------------


def parse_ics(data: bytes) -> InteractiveComposition:
    """Parse an ICS body (bytes *after* the 3-byte segment header).

    Layout reference: libbluray ``ig_decode.c``.
    """
    p = 0

    # video_descriptor (5 bytes)
    width = struct.unpack_from(">H", data, p)[0]
    height = struct.unpack_from(">H", data, p + 2)[0]
    p += 5

    # composition_descriptor (3 bytes) + sequence_descriptor (1 byte)
    p += 4

    # interactive_composition_data_length (24 bits)
    p += 3

    # stream_model (1 bit) | ui_model (1 bit) | reserved (6 bits)
    stream_model = (data[p] >> 7) & 1
    p += 1

    if stream_model == 0:
        p += 10  # composition_timeout_PTS + selection_timeout_PTS

    # user_timeout_duration (24 bits)
    p += 3

    num_pages = data[p]
    p += 1

    pages: list[IGPage] = []
    for _ in range(num_pages):
        page_id = data[p]; p += 1
        p += 1  # page_version
        p += 8  # UO mask table

        # in_effects + out_effects
        for _ in range(2):
            num_windows = data[p]; p += 1
            p += num_windows * 9
            num_effects = data[p]; p += 1
            for _ in range(num_effects):
                p += 4  # duration(24) + palette_id_ref(8)
                num_co = data[p]; p += 1
                for _ in range(num_co):
                    p += 2  # object_id
                    p += 1  # window_id
                    crop_flag = (data[p] >> 7) & 1
                    p += 1  # flags
                    p += 4  # x, y
                    if crop_flag:
                        p += 8

        p += 1  # animation_frame_rate_code
        default_btn = struct.unpack_from(">H", data, p)[0]; p += 2
        default_act = struct.unpack_from(">H", data, p)[0]; p += 2
        p += 1  # palette_id_ref
        num_bogs = data[p]; p += 1

        page_buttons: list[IGButton] = []
        for _ in range(num_bogs):
            p += 2  # bog_default_button
            num_btns = data[p]; p += 1

            for _ in range(num_btns):
                btn_id = struct.unpack_from(">H", data, p)[0]; p += 2
                p += 2  # numeric_select_value
                auto_action = bool((data[p] >> 7) & 1); p += 1
                btn_x = struct.unpack_from(">H", data, p)[0]; p += 2
                btn_y = struct.unpack_from(">H", data, p)[0]; p += 2
                p += 8  # neighbor button IDs (up/down/left/right)

                # normal state: start(16)+end(16)+repeat_flag+skip(7) = 5 bytes
                p += 5
                # selected state: sound(8)+start(16)+end(16)+repeat_flag+skip(7) = 6 bytes
                p += 6
                # activated state: sound(8)+start(16)+end(16) = 5 bytes
                p += 5

                num_cmds = struct.unpack_from(">H", data, p)[0]; p += 2
                commands: list[NavCommand] = []
                for _ in range(num_cmds):
                    raw = data[p : p + 12]
                    try:
                        commands.append(_decode_nav_command(raw))
                    except Exception:
                        log.debug("Failed to decode IG nav command", exc_info=True)
                    p += 12

                page_buttons.append(
                    IGButton(
                        button_id=btn_id,
                        x=btn_x,
                        y=btn_y,
                        auto_action=auto_action,
                        commands=commands,
                    )
                )

        pages.append(
            IGPage(
                page_id=page_id,
                default_button=default_btn,
                default_activated=default_act,
                buttons=page_buttons,
            )
        )

    return InteractiveComposition(width=width, height=height, pages=pages)


# ---------------------------------------------------------------------------
# High-level hint extraction
# ---------------------------------------------------------------------------


def extract_menu_hints(ics: InteractiveComposition) -> list[IGMenuHint]:
    """Extract actionable hints from parsed IG menu buttons.

    Returns hints for buttons that directly play a playlist, jump to a
    title, or set GPR registers (often used for episode / chapter selection).
    """
    hints: list[IGMenuHint] = []

    for page in ics.pages:
        for btn in page.buttons:
            if not btn.commands:
                continue

            hint = IGMenuHint(page_id=page.page_id, button_id=btn.button_id)
            has_action = False

            for cmd in btn.commands:
                if cmd.is_play_playlist:
                    hint.playlist = cmd.operand1
                    if cmd.op_code == 2:  # PlayPL_PM
                        hint.mark = cmd.operand2
                    has_action = True
                elif cmd.is_jump_title:
                    hint.jump_title = cmd.operand1
                    has_action = True
                elif cmd.group == 2 and cmd.sub_group == 0:
                    # SET / MOV: reg = value
                    reg = cmd.operand1
                    val = cmd.operand2
                    if cmd.imm_op2 and reg < 0x1000:
                        hint.register_sets[reg] = val
                        has_action = True

            if has_action:
                hints.append(hint)

    return hints


def parse_ig_from_m2ts(
    m2ts_path: Path | str,
    ig_pid: int | None = None,
) -> InteractiveComposition | None:
    """Convenience: demux IG stream from *m2ts_path* and parse the ICS."""
    try:
        pes_data = demux_ig_stream(m2ts_path, ig_pid)
        if not pes_data:
            log.debug("No IG PES data found in %s", m2ts_path)
            return None
        ics_data = _extract_ics_data(pes_data)
        if ics_data is None:
            log.debug("No ICS segment found in IG stream of %s", m2ts_path)
            return None
        return parse_ics(ics_data)
    except Exception:
        log.warning("Failed to parse IG stream from %s", m2ts_path, exc_info=True)
        return None
