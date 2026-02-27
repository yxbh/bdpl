# Agent Instructions & Skills Manifest

Provenance tracking for all Copilot instruction files and agent skills.

Legend: **upstream** = copied from awesome-copilot as-is · **customized** = forked
from awesome-copilot with local changes · **project-specific** = written for bdpl,
no upstream equivalent.

## Instructions

| File | Status | Source |
|------|--------|--------|
| `python.instructions.md` | **customized** | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md) |
| `pytest.instructions.md` | **project-specific** | — |
| `code-review-generic.instructions.md` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/code-review-generic.instructions.md) |
| `security-and-owasp.instructions.md` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/security-and-owasp.instructions.md) |
| `agent-skills.instructions.md` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md) |
| `instructions.instructions.md` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/instructions.instructions.md) |

## Skills

| Skill | Status | Source |
|-------|--------|--------|
| `add-disc-fixture` | **project-specific** | — |
| `gh-cli` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/gh-cli) |
| `gh-commit` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/gh-commit) |
| `make-repo-contribution` | **upstream** | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/make-repo-contribution) |

## Local Modifications

Changes made to files forked from awesome-copilot. Keep this up to date when
making further edits so upstream syncs can be done safely.

### `python.instructions.md`

Upstream version is a generic PEP 8 guide. Customized to match bdpl's actual
tooling and conventions:

- **Line length**: 79 → 100 (matches `line-length = 100` in `pyproject.toml`)
- **Type hints**: Replaced `typing.List[str]` / `typing.Dict` / `typing.Optional`
  guidance with modern syntax (`list[str]`, `dict[str, int]`, `X | None`)
- **Added project conventions section**: `from __future__ import annotations`,
  `dataclasses` with `slots=True`, `struct` for binary parsing, `typer`/`rich`
- **String style**: Added double-quote preference (ruff format default)
- **Import sorting**: Added isort-style via ruff `I` rule
- **Tooling**: Added `ruff check .` and `ruff format .` as pre-commit steps
- **Comments**: Changed "write clear and concise comments for each function" to
  "only comment code that needs clarification" (matches AGENTS.md style guide)
- **Docstring example**: Modernized to single-line summary style per PEP 257
- **Removed**: Over-commenting guidance, `typing` module recommendation,
  mention of external dependency comments

## Upstream Sync Guide

When pulling updates from awesome-copilot:

- **upstream** — safe to overwrite with newer version
- **customized** — merge manually; check "Local Modifications" above for what to preserve
- **project-specific** — no upstream equivalent; maintained independently
