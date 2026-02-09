"""Parser for Blu-ray MovieObject.bdmv files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from bdpl.bdmv.reader import BinaryReader

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Navigation command bit layout (12 bytes per command)
#
#   byte 0:  [op_cnt(3)][grp(2)][sub_grp(3)]
#   byte 1:  [imm_op1(1)][imm_op2(1)][reserved(2)][op_code(4)]
#   bytes 2-3:  reserved / additional flags
#   bytes 4-7:  operand1  (big-endian u32)
#   bytes 8-11: operand2  (big-endian u32)
#
# Branch group (grp=0):
#   sub_grp=0  Goto:  0=nop, 1=goto, 2=break
#   sub_grp=1  Jump:  0=jump_object, 1=jump_title, 2=call_object,
#                      3=call_title, 4=resume
#   sub_grp=2  Play:  0=play_pl, 1=play_pl_pi, 2=play_pl_pm,
#                      3=play_pl_rnd, 5=play_pl_still,
#                      6=link_pi, 7=link_mk
# ---------------------------------------------------------------------------

_NAV_CMD_SIZE = 12


@dataclass(slots=True)
class NavCommand:
    """A single HDMV navigation command (12 bytes)."""

    raw: bytes
    group: int       # 0=branch, 1=compare, 2=set
    sub_group: int
    op_code: int
    imm_op1: bool
    imm_op2: bool
    operand1: int    # 32-bit value
    operand2: int    # 32-bit value

    # -- branch / jump helpers --

    @property
    def is_play_playlist(self) -> bool:
        """True for PlayPL, PlayPL_PI, or PlayPL_PM commands."""
        return self.group == 0 and self.sub_group == 2 and self.op_code in (0, 1, 2)

    @property
    def is_jump_title(self) -> bool:
        return self.group == 0 and self.sub_group == 1 and self.op_code == 1

    @property
    def is_jump_object(self) -> bool:
        return self.group == 0 and self.sub_group == 1 and self.op_code == 0

    @property
    def is_call_object(self) -> bool:
        return self.group == 0 and self.sub_group == 1 and self.op_code == 2

    @property
    def playlist_number(self) -> int | None:
        """Playlist number referenced by a play command, or *None*."""
        if self.is_play_playlist:
            return self.operand1
        return None


@dataclass(slots=True)
class MovieObject:
    """One movie object containing a sequence of navigation commands."""

    object_id: int
    resume_intention: bool
    menu_call_mask: bool
    title_search_mask: bool
    commands: list[NavCommand]

    @property
    def referenced_playlists(self) -> list[int]:
        """Playlist numbers referenced by play commands."""
        return [c.operand1 for c in self.commands if c.is_play_playlist]

    @property
    def referenced_titles(self) -> list[int]:
        """Title numbers referenced by JumpTitle commands."""
        return [c.operand1 for c in self.commands if c.is_jump_title]


@dataclass(slots=True)
class MovieObjectBDMV:
    """Parsed contents of a ``MovieObject.bdmv`` file."""

    version: str
    objects: list[MovieObject]

    def playlist_to_objects(self) -> dict[int, list[int]]:
        """Map *playlist_number* → list of movie object ids that play it."""
        result: dict[int, list[int]] = {}
        for obj in self.objects:
            for pl in obj.referenced_playlists:
                result.setdefault(pl, []).append(obj.object_id)
        return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _decode_nav_command(raw: bytes) -> NavCommand:
    """Decode a 12-byte navigation command."""
    b0, b1 = raw[0], raw[1]
    group = (b0 >> 3) & 0x03
    sub_group = b0 & 0x07
    imm_op1 = bool((b1 >> 7) & 1)
    imm_op2 = bool((b1 >> 6) & 1)
    op_code = b1 & 0x0F
    operand1 = int.from_bytes(raw[4:8], "big")
    operand2 = int.from_bytes(raw[8:12], "big")
    return NavCommand(
        raw=raw,
        group=group,
        sub_group=sub_group,
        op_code=op_code,
        imm_op1=imm_op1,
        imm_op2=imm_op2,
        operand1=operand1,
        operand2=operand2,
    )


def _parse_reader(r: BinaryReader) -> MovieObjectBDMV:
    """Parse from an already-opened :class:`BinaryReader`."""
    magic = r.read_string(4)
    if magic != "MOBJ":
        raise ValueError(f"Not a MovieObject.bdmv file (magic={magic!r})")
    version = r.read_string(4)

    # Skip the rest of the 40-byte header (extension_data_start + padding).
    r.seek(40)

    # Movie-objects section
    _section_length = r.u32()
    r.skip(4)  # reserved
    num_objects = r.u16()

    objects: list[MovieObject] = []
    for idx in range(num_objects):
        flags = r.u8()
        resume_intention = bool((flags >> 7) & 1)
        menu_call_mask = bool((flags >> 6) & 1)
        title_search_mask = bool((flags >> 5) & 1)
        r.skip(1)  # reserved
        num_commands = r.u16()

        commands: list[NavCommand] = []
        for _ in range(num_commands):
            raw = r.read_bytes(_NAV_CMD_SIZE)
            try:
                commands.append(_decode_nav_command(raw))
            except Exception:
                log.warning(
                    "Failed to decode nav command in object %d", idx, exc_info=True
                )

        objects.append(
            MovieObject(
                object_id=idx,
                resume_intention=resume_intention,
                menu_call_mask=menu_call_mask,
                title_search_mask=title_search_mask,
                commands=commands,
            )
        )

    return MovieObjectBDMV(version=version, objects=objects)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_movieobject_bdmv(
    source: Union[BinaryReader, str, Path],
) -> MovieObjectBDMV:
    """Parse a ``MovieObject.bdmv`` file.

    *source* may be a file path (str / Path) or an existing
    :class:`BinaryReader`.
    """
    if isinstance(source, BinaryReader):
        return _parse_reader(source)
    path = Path(source)
    with BinaryReader(path) as r:
        return _parse_reader(r)
