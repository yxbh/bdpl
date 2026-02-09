import os

import pytest
from pathlib import Path


@pytest.fixture
def bdmv_path():
    """Path to an example BDMV directory for integration tests.

    Set the BDPL_TEST_BDMV environment variable to point at a BDMV/
    directory (or its parent).  Skips if unset or missing.
    """
    env = os.environ.get("BDPL_TEST_BDMV")
    if not env:
        pytest.skip("BDPL_TEST_BDMV not set – skipping integration test")
    p = Path(env)
    # Accept a parent dir that contains BDMV/
    if (p / "BDMV" / "PLAYLIST").is_dir():
        p = p / "BDMV"
    if not (p / "PLAYLIST").is_dir():
        pytest.skip(f"No PLAYLIST/ found at {p}")
    return p
