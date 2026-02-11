"""Parser for Blu-ray index.bdmv files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from bdpl.bdmv.reader import BinaryReader

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class IndexTitle:
    """A single title entry from the Indexes section."""

    title_num: int
    object_type: str  # "hdmv" or "bdj"
    movie_object_id: int  # MovieObject index (HDMV) or 0 (BD-J)
    access_type: int


@dataclass(slots=True)
class IndexBDMV:
    """Parsed contents of an ``index.bdmv`` file."""

    first_playback_obj: int | None
    top_menu_obj: int | None
    titles: list[IndexTitle]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_OBJ_HDMV = 0x01
_OBJ_BDJ = 0x02


def _parse_index_entry(r: BinaryReader) -> tuple[str | None, int, int]:
    """Parse a 12-byte index entry.

    Returns ``(object_type, movie_object_id, access_type)``.
    *object_type* is ``None`` when no object is present.
    """
    flags = r.u8()
    object_type_bits = (flags >> 6) & 0x03
    access_type = (flags >> 2) & 0x0F
    r.skip(3)  # remaining flag / reserved bytes

    if object_type_bits == _OBJ_HDMV:
        r.skip(2)  # hdmv_playback_type
        movie_object_id = r.u16()
        r.skip(4)  # reserved
        return ("hdmv", movie_object_id, access_type)

    if object_type_bits == _OBJ_BDJ:
        r.read_string(5)
        r.skip(3)  # padding
        return ("bdj", 0, access_type)

    # No object present — skip remaining 8 bytes of the entry.
    r.skip(8)
    return (None, 0, 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_index_bdmv(source: Union[BinaryReader, str, Path]) -> IndexBDMV:
    """Parse an ``index.bdmv`` file and return an :class:`IndexBDMV`."""
    if isinstance(source, BinaryReader):
        return _parse_index_reader(source)
    path = Path(source)
    with BinaryReader(path) as r:
        return _parse_index_reader(r)


def _parse_index_reader(r: BinaryReader) -> IndexBDMV:
    magic = r.read_string(4)
    if magic != "INDX":
        raise ValueError(f"Not an index.bdmv file (magic={magic!r})")
    version = r.read_string(4)
    if version not in ("0100", "0200"):
        raise ValueError(f"Unsupported index.bdmv version {version!r}")

    indexes_start = r.u32()
    _ext_data_start = r.u32()

    # ── Indexes section ───────────────────────────────────────────────
    r.seek(indexes_start)
    _section_length = r.u32()

    # First Playback object (12 bytes)
    fp_type, fp_id, _ = _parse_index_entry(r)
    first_playback_obj = fp_id if fp_type is not None else None

    # Top Menu object (12 bytes)
    tm_type, tm_id, _ = _parse_index_entry(r)
    top_menu_obj = tm_id if tm_type is not None else None

    # Title entries
    num_titles = r.u16()
    titles: list[IndexTitle] = []
    for i in range(num_titles):
        try:
            obj_type, movie_obj_id, access_type = _parse_index_entry(r)
            if obj_type is not None:
                titles.append(
                    IndexTitle(
                        title_num=i,
                        object_type=obj_type,
                        movie_object_id=movie_obj_id,
                        access_type=access_type,
                    )
                )
        except Exception:
            log.warning("Failed to parse title entry %d", i, exc_info=True)

    return IndexBDMV(
        first_playback_obj=first_playback_obj,
        top_menu_obj=top_menu_obj,
        titles=titles,
    )
