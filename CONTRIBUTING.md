# Contributing to bdpl

Thanks for contributing to **bdpl**.

## Scope and Principles

- Keep changes focused and minimal.
- Prefer fixes at the root cause over surface workarounds.
- Preserve existing behavior unless the change intentionally updates behavior.
- Do not add copyrighted media content to this repository.

## Development Setup

1. Use Python 3.10+ (3.12 recommended).
2. Create/activate a virtual environment.
3. Install project + dev dependencies:

```bash
pip install -e ".[dev]"
```

## Local Validation

Run these before opening a PR:

```bash
ruff check .
ruff format .
pytest -q
```

If your change is localized, run targeted tests first, then the full suite.

## Code Style

- Follow PEP 8 and existing repository style.
- Add type hints for new/changed Python functions.
- Add/adjust tests for behavioral changes.
- Keep public CLI behavior documented in README when changed.

## Fixtures and Copyright Safety

This project accepts **metadata-only** Blu-ray fixtures.

Allowed fixture files (small binary metadata):
- `BDMV/index.bdmv`
- `BDMV/MovieObject.bdmv`
- `BDMV/PLAYLIST/*.mpls`
- `BDMV/CLIPINF/*.clpi`
- optional tiny IG/ICS metadata artifacts used by tests

Do **not** commit:
- `BDMV/STREAM/*.m2ts` (audio/video payload)
- full disc images/ISOs
- cover art, subtitle dumps, or other copyrighted content
- large backups of disc folders

Fixture guidance:
- Use generic fixture names such as `disc1`, `disc2`, etc.
- Keep fixture payloads as small as possible.
- Add tests that assert behavior using those fixtures.

## Test Organization

- Place tests under `tests/`.
- Prefer disc-specific integration tests for fixture-backed behavior (for example, `test_disc4_scan.py`).
- Keep test names descriptive and deterministic.

## Commit and Pull Request Guidance

- Create a feature branch from `main`.
- Use clear commit messages describing behavior-level intent.
- In PR descriptions, include:
  - what changed
  - why it changed
  - validation performed (`ruff`, `pytest`, manual checks)
  - any fixture additions/updates

## Security and Safety Expectations

- Never hardcode secrets.
- Avoid unsafe shell invocation patterns in new code.
- Validate and sanitize user-provided paths/inputs.

## Questions

If requirements are unclear, open a draft PR with assumptions and ask for guidance early.
