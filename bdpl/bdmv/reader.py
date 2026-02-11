"""Big-endian binary reader for parsing Blu-ray BDMV structures."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Union


class BinaryReader:
    """Reads big-endian binary data with cursor tracking and helpful errors."""

    __slots__ = ("_data", "_pos", "_start", "_end", "_path")

    def __init__(self, source: Union[bytes, memoryview, str, Path]) -> None:
        if isinstance(source, (str, Path)):
            path = Path(source)
            self._data = memoryview(path.read_bytes())
            self._path: str | None = str(path)
        else:
            self._data = memoryview(source) if not isinstance(source, memoryview) else source
            self._path = None
        self._pos: int = 0
        self._start: int = 0
        self._end: int = len(self._data)

    # -- context manager --

    def __enter__(self) -> BinaryReader:
        return self

    def __exit__(self, *_: object) -> None:
        self._data.release()

    # -- cursor --

    def tell(self) -> int:
        """Return the current read position relative to the slice start."""
        return self._pos - self._start

    def seek(self, offset: int) -> None:
        """Set the read position relative to the slice start."""
        absolute = self._start + offset
        if absolute < self._start or absolute > self._end:
            raise ValueError(f"seek to offset {offset} out of range [0, {self._end - self._start}]")
        self._pos = absolute

    def skip(self, n: int) -> None:
        """Advance the read position by *n* bytes."""
        self.require(n)
        self._pos += n

    @property
    def remaining(self) -> int:
        """Number of unread bytes from the current position."""
        return self._end - self._pos

    # -- guards --

    def require(self, n: int) -> None:
        """Raise if fewer than *n* bytes remain at the current position."""
        if self._end - self._pos < n:
            raise ValueError(
                f"need {n} bytes at offset {self.tell()}, but only {self._end - self._pos} remain"
            )

    def require_at(self, offset: int, n: int) -> None:
        """Raise if fewer than *n* bytes available starting at *offset*."""
        absolute = self._start + offset
        if absolute < self._start or absolute + n > self._end:
            raise ValueError(
                f"need {n} bytes at offset {offset}, but range is [0, {self._end - self._start}]"
            )

    # -- slicing --

    def slice(self, offset: int, length: int) -> BinaryReader:
        """Return a new reader over a sub-range without copying."""
        self.require_at(offset, length)
        absolute = self._start + offset
        child = object.__new__(BinaryReader)
        child._data = self._data
        child._start = absolute
        child._end = absolute + length
        child._pos = absolute
        child._path = self._path
        return child

    # -- primitive reads (big-endian) --

    def read_bytes(self, n: int) -> bytes:
        """Read *n* raw bytes and advance the cursor."""
        self.require(n)
        result = bytes(self._data[self._pos : self._pos + n])
        self._pos += n
        return result

    def _read_fmt(self, fmt: str, size: int) -> int:
        self.require(size)
        (value,) = struct.unpack_from(fmt, self._data, self._pos)
        self._pos += size
        return value

    def u8(self) -> int:
        """Read an unsigned 8-bit integer."""
        return self._read_fmt(">B", 1)

    def u16(self) -> int:
        """Read a big-endian unsigned 16-bit integer."""
        return self._read_fmt(">H", 2)

    def u32(self) -> int:
        """Read a big-endian unsigned 32-bit integer."""
        return self._read_fmt(">I", 4)

    def u64(self) -> int:
        """Read a big-endian unsigned 64-bit integer."""
        return self._read_fmt(">Q", 8)

    # -- string reads --

    def read_string(self, n: int) -> str:
        """Read *n* bytes and decode as ASCII, stripping null bytes."""
        return self.read_bytes(n).replace(b"\x00", b"").decode("ascii")

    # -- repr --

    def __repr__(self) -> str:
        src = self._path or "bytes"
        return f"BinaryReader({src}, pos={self.tell()}, remaining={self.remaining})"
