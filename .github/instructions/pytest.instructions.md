---
description: 'Pytest conventions and testing patterns for the bdpl project'
applyTo: 'tests/**/*.py'
---

# Pytest Conventions

## Project Test Structure

```
tests/
├── conftest.py              # Shared fixtures (_fixture_path, _analyze_fixture, disc fixtures)
├── test_disc_matrix.py      # Cross-disc parametrized tests (6 parametrizations)
├── test_disc{N}_scan.py     # Per-disc integration tests
├── test_fixture_integrity.py # Fixture file validation
├── test_reader.py           # BinaryReader unit tests
├── test_mpls_parse.py       # MPLS parser tests
├── test_clpi_parse.py       # CLPI parser tests
├── test_index_bdmv.py       # index.bdmv parser tests
├── test_movieobject_bdmv.py # MovieObject parser tests
├── test_ig_stream.py        # IG stream parser tests
├── test_cli.py              # CLI subprocess tests
└── fixtures/disc{N}/        # Bundled BDMV metadata fixtures
```

## Fixture Patterns

### Disc Analysis Fixtures (conftest.py)

- Use `@pytest.fixture(scope="session")` for disc analysis — parsing is expensive.
- Helper `_fixture_path(name)` resolves fixture directories and validates structure.
- Helper `_analyze_fixture(path)` runs `scan_disc()` and returns `DiscAnalysis`.
- Each disc gets a fixture like `disc3(request)` that calls `_analyze_fixture`.

```python
@pytest.fixture(scope="session")
def disc7(request):
    """Disc with commentary audio and creditless extras."""
    path = _fixture_path("disc7")
    if path is None:
        pytest.skip("disc7 fixture not available")
    return _analyze_fixture(path)
```

### Adding a New Disc Fixture

1. Create `tests/fixtures/disc{N}/` with PLAYLIST/, CLIPINF/, index.bdmv, MovieObject.bdmv.
2. Files go directly under `disc{N}/` — NOT under `disc{N}/BDMV/`.
3. Add the fixture to `conftest.py` with a descriptive docstring.
4. Add to ALL 6 parametrizations in `test_disc_matrix.py`.
5. Create `test_disc{N}_scan.py` with per-disc assertions.

## Test Patterns

### Per-Disc Integration Tests

Each disc test file follows a consistent structure:

```python
def test_episode_count(disc7):
    assert len(disc7.episodes) == 6

def test_special_features(disc7):
    cats = Counter(sf.category for sf in disc7.special_features)
    assert cats["commentary"] == 2
    assert cats["creditless_op"] == 1
```

### Matrix Tests (test_disc_matrix.py)

Cross-disc parametrized tests validate invariants across all fixtures:

```python
@pytest.mark.parametrize("fixture_name,expected", [
    ("disc1", 6),
    ("disc3", 5),
    # ... all discs
])
def test_episode_count(fixture_name, expected, request):
    da = request.getfixturevalue(fixture_name)
    assert len(da.episodes) == expected
```

When adding a disc, update ALL parametrizations:
- `test_episode_count`
- `test_special_feature_count`
- `test_episode_numbering`
- `test_no_warnings` (or expected warnings)
- `test_playlist_classification_coverage`
- `test_episode_confidence`

### Unit Tests

Use small, focused tests with inline binary data or minimal fixtures:

```python
def test_read_u32(self):
    r = BinaryReader(b"\x00\x01\x00\x02")
    assert r.read_u32() == 0x00010002
```

## Running Tests

```bash
pytest tests/ -v                     # All tests
pytest tests/test_disc7_scan.py -v   # Single disc
pytest tests/ -k "matrix" -v        # Matrix tests only
pytest tests/ -x                     # Stop on first failure
```

## Conventions

- Use `assert` statements directly — no `self.assertEqual`.
- Group related assertions in a single test when they share expensive setup.
- Use `Counter` from `collections` for category breakdowns.
- Test names follow `test_{what}` pattern (e.g., `test_episode_count`, `test_special_features`).
- Skip tests gracefully when fixtures are unavailable (`pytest.skip`).
- Never commit copyrighted media (m2ts streams) — fixtures contain only structural metadata.
