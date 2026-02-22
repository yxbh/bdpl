"""Tests for the BinaryReader class."""

import struct

import pytest

from bdpl.bdmv.reader import BinaryReader


class TestPrimitiveReads:
    """Test u8, u16, u32, u64 big-endian reads."""

    def test_u8(self) -> None:
        r = BinaryReader(b"\xab")
        assert r.u8() == 0xAB

    def test_u16(self) -> None:
        r = BinaryReader(struct.pack(">H", 0xBEEF))
        assert r.u16() == 0xBEEF

    def test_u32(self) -> None:
        r = BinaryReader(struct.pack(">I", 0xDEADBEEF))
        assert r.u32() == 0xDEADBEEF

    def test_u64(self) -> None:
        r = BinaryReader(struct.pack(">Q", 0x0102030405060708))
        assert r.u64() == 0x0102030405060708


class TestReadBytesAndString:
    """Test read_bytes and read_string."""

    def test_read_bytes(self) -> None:
        r = BinaryReader(b"\x01\x02\x03\x04")
        assert r.read_bytes(3) == b"\x01\x02\x03"
        assert r.read_bytes(1) == b"\x04"

    def test_read_string(self) -> None:
        r = BinaryReader(b"MPLS\x00")
        assert r.read_string(4) == "MPLS"

    def test_read_string_strips_nulls(self) -> None:
        r = BinaryReader(b"AB\x00\x00\x00")
        assert r.read_string(5) == "AB"


class TestCursor:
    """Test seek, tell, skip."""

    def test_tell_starts_at_zero(self) -> None:
        r = BinaryReader(b"\x00" * 10)
        assert r.tell() == 0

    def test_tell_advances_after_read(self) -> None:
        r = BinaryReader(b"\x00" * 10)
        r.u8()
        assert r.tell() == 1
        r.u16()
        assert r.tell() == 3

    def test_seek(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03")
        r.seek(2)
        assert r.tell() == 2
        assert r.u8() == 0x02

    def test_skip(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03")
        r.skip(3)
        assert r.tell() == 3
        assert r.u8() == 0x03

    def test_seek_out_of_range_raises(self) -> None:
        r = BinaryReader(b"\x00\x01")
        with pytest.raises(ValueError):
            r.seek(10)


class TestSlice:
    """Test slice creates a sub-reader."""

    def test_slice_basic(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03\x04\x05")
        child: BinaryReader = r.slice(2, 3)
        assert child.remaining == 3
        assert child.tell() == 0
        assert child.u8() == 0x02
        assert child.u8() == 0x03
        assert child.u8() == 0x04

    def test_slice_independent_of_parent(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03\x04\x05")
        child: BinaryReader = r.slice(1, 2)
        child.u8()
        # Parent position unchanged
        assert r.tell() == 0


class TestGuards:
    """Test require and require_at."""

    def test_require_raises_when_not_enough_bytes(self) -> None:
        r = BinaryReader(b"\x00\x01")
        with pytest.raises(ValueError, match="need 5 bytes"):
            r.require(5)

    def test_require_ok_when_enough_bytes(self) -> None:
        r = BinaryReader(b"\x00\x01\x02")
        r.require(3)  # Should not raise

    def test_require_at_raises_for_out_of_bounds(self) -> None:
        r = BinaryReader(b"\x00\x01\x02")
        with pytest.raises(ValueError):
            r.require_at(2, 5)

    def test_require_at_ok_within_bounds(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03")
        r.require_at(1, 2)  # Should not raise


class TestRemaining:
    """Test remaining property."""

    def test_remaining_full(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03")
        assert r.remaining == 4

    def test_remaining_after_reads(self) -> None:
        r = BinaryReader(b"\x00\x01\x02\x03")
        r.u8()
        assert r.remaining == 3
        r.u16()
        assert r.remaining == 1

    def test_remaining_at_end(self) -> None:
        r = BinaryReader(b"\x00")
        r.u8()
        assert r.remaining == 0
