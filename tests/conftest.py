import os
from pathlib import Path

import pytest

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "disc1"


@pytest.fixture
def bdmv_path():
    """Path to a BDMV directory for integration tests.

    Uses BDPL_TEST_BDMV env var if set, otherwise falls back to the
    bundled fixtures (stripped metadata-only copies of real disc files).
    """
    env = os.environ.get("BDPL_TEST_BDMV")
    if env:
        p = Path(env)
        # Accept a parent dir that contains BDMV/
        if (p / "BDMV" / "PLAYLIST").is_dir():
            p = p / "BDMV"
        if not (p / "PLAYLIST").is_dir():
            pytest.skip(f"No PLAYLIST/ found at {p}")
        return p

    # Fall back to bundled fixtures
    if (_FIXTURE_DIR / "PLAYLIST").is_dir():
        return _FIXTURE_DIR
    pytest.skip("No BDMV fixtures available")
