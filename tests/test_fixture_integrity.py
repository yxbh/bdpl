"""Safety checks for bundled metadata-only fixture content."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

FORBIDDEN_DIRS = {"STREAM", "AUXDATA", "JAR", "BACKUP"}
MAX_FIXTURE_FILE_BYTES = 100_000


def _fixture_roots() -> list[Path]:
    """Return all top-level disc fixture directories."""
    fixtures_root = Path(__file__).parent / "fixtures"
    return [path for path in fixtures_root.iterdir() if path.is_dir()]


def test_fixtures_do_not_include_media_payload_dirs() -> None:
    """Fixtures should not contain stream/media payload directories."""
    fixture_roots = _fixture_roots()
    assert fixture_roots, "Expected at least one fixture directory"

    for fixture_root in fixture_roots:
        children = {path.name for path in fixture_root.iterdir() if path.is_dir()}
        forbidden = sorted(children & FORBIDDEN_DIRS)
        assert not forbidden, f"{fixture_root.name} contains forbidden dirs: {forbidden}"


def test_fixture_files_remain_small_metadata_only_assets() -> None:
    """Fixture files should remain small metadata-only assets."""
    fixture_roots = _fixture_roots()
    assert fixture_roots, "Expected at least one fixture directory"

    for fixture_root in fixture_roots:
        for file_path in fixture_root.rglob("*"):
            if not file_path.is_file():
                continue
            size = file_path.stat().st_size
            assert size <= MAX_FIXTURE_FILE_BYTES, (
                f"{file_path.relative_to(fixture_root.parent)} is {size} bytes "
                f"(limit {MAX_FIXTURE_FILE_BYTES})"
            )
