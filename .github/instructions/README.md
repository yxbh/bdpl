# Agent Instructions & Skills Manifest

Provenance tracking for all Copilot instruction files and agent skills.

## Instructions

| File | Source | Notes |
|------|--------|-------|
| `python.instructions.md` | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md) → **customized** | Originally copied from awesome-copilot; updated to match bdpl conventions (100-char lines, modern type syntax, ruff, dataclasses, struct parsing) |
| `pytest.instructions.md` | **Project-specific** | Written for bdpl's fixture patterns, matrix tests, and disc analysis conventions. Nothing equivalent in awesome-copilot. |
| `code-review-generic.instructions.md` | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/code-review-generic.instructions.md) | Identical to upstream |
| `security-and-owasp.instructions.md` | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/security-and-owasp.instructions.md) | Identical to upstream |
| `agent-skills.instructions.md` | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/agent-skills.instructions.md) | Identical to upstream |
| `instructions.instructions.md` | [awesome-copilot](https://github.com/github/awesome-copilot/blob/main/instructions/instructions.instructions.md) | Identical to upstream |

## Skills

| Skill | Source | Notes |
|-------|--------|-------|
| `add-disc-fixture` | **Project-specific** | 10-step disc fixture workflow + analysis debugging guide |
| `gh-cli` | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/gh-cli) | GitHub CLI reference |
| `gh-commit` | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/gh-commit) | Conventional commit generation |
| `make-repo-contribution` | [awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/make-repo-contribution) | Contribution workflow |

## Upstream Sync

When updating from awesome-copilot, check the "Notes" column:
- **Identical to upstream** — safe to overwrite with newer version
- **Customized** — merge manually; review diffs to preserve project-specific changes
- **Project-specific** — no upstream equivalent; maintained independently
