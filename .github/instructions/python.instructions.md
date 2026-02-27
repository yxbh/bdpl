---
description: 'Python coding conventions and guidelines for the bdpl project'
applyTo: '**/*.py'
---

# Python Coding Conventions

## Project-Specific Conventions

- Python 3.10+ required; use `from __future__ import annotations` in all modules.
- Use `dataclasses` with `slots=True` for data models.
- Use the `struct` module for binary parsing — no external binary-parsing deps.
- Use `typer` for CLI commands and `rich` for terminal output.
- Line length limit is **100 characters** (configured in `pyproject.toml` via ruff).
- Use double quotes for strings (configured via ruff format).
- Import sorting follows isort-style rules (ruff `I` rule).

## Python Instructions

- Ensure functions have descriptive names and include type hints.
- Provide docstrings following PEP 257 conventions for public functions.
- Use modern Python type syntax (`list[str]`, `dict[str, int]`, `X | None`) — no `typing.List`/`typing.Dict`/`typing.Optional`.
- Break down complex functions into smaller, more manageable functions.
- Only comment code that needs clarification; avoid obvious comments.

## General Instructions

- Always prioritize readability and clarity.
- For algorithm-related code, include explanations of the approach used.
- Handle edge cases and write clear exception handling.
- Parsers should be robust — never crash on malformed binary data.
- Use consistent naming conventions and follow language-specific best practices.
- Write concise, efficient, and idiomatic code that is also easily understandable.

## Code Style and Formatting

- Follow **PEP 8** with the project's 100-character line limit.
- Maintain proper indentation (4 spaces).
- Place function and class docstrings immediately after the `def` or `class` keyword.
- Use blank lines to separate functions, classes, and code blocks where appropriate.
- Run `ruff check .` and `ruff format .` before committing.

## Edge Cases and Testing

- Always include test cases for critical paths of the application.
- Account for common edge cases like empty inputs, invalid data types, and large datasets.
- Write unit tests for functions and document them with docstrings explaining the test cases.
- See `pytest.instructions.md` for project-specific testing patterns.

## Example of Proper Documentation

```python
def calculate_area(radius: float) -> float:
    """Calculate the area of a circle given the radius.

    Parameters:
        radius: The radius of the circle.

    Returns:
        The area of the circle, calculated as π * radius².
    """
    import math
    return math.pi * radius ** 2
```
