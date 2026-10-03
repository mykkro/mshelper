# Python

## Language block (paste after the session primer)

Adjust the versions and tools to your project, then delete the lines that don't apply.

```text
PYTHON CONVENTIONS for this conversation:
- Python {{3.11}}. Use modern syntax: type hints everywhere (built-in generics like list[str],
  X | None), f-strings, pathlib (not os.path), dataclasses or {{pydantic v2}} for data containers,
  match statements where they make the code clearer.
- Follow PEP 8. Code must pass {{ruff}} and {{mypy --strict / pyright}} without new warnings.
- Docstrings: {{Google}} style for public functions and classes.
- Errors: raise specific exceptions (built-in or custom subclasses), never a bare `except:`, and don't
  swallow exceptions silently. Use `raise ... from err` when re-raising.
- Resources: always use context managers (`with`) for files, locks, connections.
- Logging: use the `logging` module (module-level `logger = logging.getLogger(__name__)`), not print.
- Testing: pytest with plain asserts, fixtures, and @pytest.mark.parametrize for tables of cases;
  use tmp_path and monkeypatch instead of real files or env.
- Dependencies: standard library first. Packaging/tooling: {{uv / poetry / pip + requirements.txt}}.
- No mutable default arguments. No wildcard imports. Keep functions small and pure where possible.
```

---

## Python prompts

### Add type hints

```text
Add complete, precise type hints to this module so that it passes `mypy --strict`.
Use Protocol / TypeVar / generics / TypedDict / Literal where they fit better than Any. Don't change
the runtime behavior. List any places where the hints exposed a real bug or an inconsistency.
{{code}}
```

### Make a script into a proper CLI

```text
Turn this script into a clean CLI tool:
- Use {{argparse / typer / click}}, with --help text for every option.
- A `main()` entry point plus `if __name__ == "__main__":`.
- Exit codes: 0 on success, non-zero on errors, with errors printed to stderr.
- Logging with a --verbose flag.
- Split the logic into testable functions that are separate from the I/O.
- Give a [project.scripts] entry for pyproject.toml.
{{script}}
```

### Write pytest tests

```text
Write pytest tests for the module below.
- Use parametrize for the input/output tables, fixtures for shared setup, and tmp_path for files.
- Mock external calls with monkeypatch or unittest.mock ({{requests/httpx/DB/time}}). Don't mock
  internal helpers.
- Test the exceptions with pytest.raises(..., match=...).
- Target: every branch covered. Tell me which branches you couldn't cover and why.
{{code}}
```

### Pythonic refactor

```text
Refactor this to idiomatic modern Python without changing the behavior:
comprehensions where they're clearer, enumerate/zip instead of index loops, dataclasses instead of
dict-soup, pathlib, context managers, early returns instead of deep nesting, and itertools/collections
where they fit. Don't golf it. Readability wins.
{{code}}
```

### Async conversion

```text
Convert this code to asyncio using {{httpx.AsyncClient / aiofiles / asyncpg}}.
- Run independent I/O concurrently (asyncio.gather or TaskGroup), with a concurrency limit of {{N}}
  through a Semaphore.
- Handle timeouts and cancellation correctly.
- Keep a sync wrapper for existing callers if needed: {{yes/no}}.
Explain where concurrency actually helps here and where it doesn't.
{{code}}
```

### Pandas / data processing

```text
Here is a {{pandas / polars}} transformation. The sample input is below (df.head(10).to_string() plus df.dtypes).
Goal: {{describe the output}}
- Vectorize it: no row-wise apply/iterrows unless there's no alternative.
- Be explicit about dtypes and NaN handling.
- Keep it as a sequence of named, testable steps.
Sample:
{{paste}}
Current code:
{{paste}}
```

### Packaging setup

```text
Create a minimal modern pyproject.toml for this project:
name {{name}}, Python {{>=3.11}}, src layout, dependencies {{list}}, dev dependencies
{{pytest, ruff, mypy}}, console script {{name = "pkg.cli:main"}}, and ruff + mypy + pytest config
sections. Build backend: {{hatchling}}. Explain any choices that aren't obvious.
```

### Debug a traceback

````text
Python traceback:
```
{{full traceback}}
```
Python {{version}}, key packages: {{pip freeze | grep relevant}}.
Code at the frames in MY code (not library frames):
{{snippets}}
Find the root cause. Note: the line in the last frame is often NOT where the bug is, so trace where the
bad value came from.
````

### Performance profiling help

```text
Here's output from `python -m cProfile -s cumtime {{script}}` (top 30 lines):
{{paste}}
And the hot functions:
{{code}}
Interpret the profile, identify the real bottleneck (cumulative vs own time), and suggest fixes
ranked by impact.
```
