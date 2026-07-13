# Verification Phase Pattern

## Lesson

When migrating an existing codebase to Controller+Handle architecture,
the plan MUST include a final verification phase that systematically
checks all UNTOUCHED modules. Skipping this leads to a retroactive
phase added after the original plan was thought complete.

## Verification Matrix

Before starting implementation, list EVERY module that will NOT be
modified. For each, note WHY it's untouched and WHAT RISK the migration
poses to it (e.g. "Handle wraps it — API must remain stable").

Example: list every module across `your_module/core/`, `your_module/cli/`,
`your_module/api/`, `your_module/commands/`, `your_module/frontend/` —
note for each whether it depends on anything the migration changes.

## Required Verification Tests

1. **Import integrity** — parametrized test importing all untouched modules
2. **API stability** — Mock-based tests that new Handles call correct internal functions
3. **CLI smoke** — subprocess `python -m your_app --help` without ImportError
4. **REST endpoints** — TestClient for every endpoint (status codes + response shape)
5. **Existing test suite** — subprocess run, diff against baseline (no NEW failures)
6. **Real smoke test** — start server on a port, make HTTP request, verify response
7. **AST dependency analysis** — parse new files with `ast.parse`, verify no forbidden top-level imports
8. **Final gate** — all controllers initialized, all handles registered, Protocol-compliant, no circular imports

## Pre-existing Bugs (do not fix, do not ignore)

Document pre-existing issues (import hangers, SyntaxErrors) BEFORE the
migration. Mark affected tests with `pytest.skip()`. Do NOT fix
pre-existing bugs during the migration — that's scope creep.

IMPORTANT: A test that hits a pre-existing import hang and does not skip
will block the ENTIRE suite (pytest stops after timeout). Solution:
`pytest.skip()` with a descriptive message instead of a real import:

```python
def test_module_import_skipped_due_to_preexisting_bug():
    pytest.skip(
        "Pre-existing bug: your_module/__init__.py imports Engine eagerly "
        "which hangs. Fix: make __init__.py use lazy imports."
    )
```

Examples of pre-existing issues to document and skip:
- `your_module/__init__.py` imports an engine eagerly → hangs (not caused by migration)
- `your_module/commands/engine.py` hangs on import (pulls in the eagerly-imported engine)
- `tests/test_engine/test_source.py` has a SyntaxError
All pre-existing, all documented, all skipped in verification tests.

Additionally: maintain a known-issues file (e.g. `pre-existing-issues.md`)
in the project documentation directory recording all pre-existing problems
with file, line, workaround, and status. This helps future sessions.

## Test Contamination

Mock-based tests that inject fake modules into `sys.modules` contaminate
subsequent tests that import real modules. This causes errors like
`ImportError: cannot import name 'Config' from 'your_module.config'`
in import tests because earlier handle tests had faked `your_module.config`.

Solutions:
- Cleanup function that removes fake modules from `sys.modules` between tests
- Isolate test files using fake modules from test files importing real modules
- Or: exclude modules known to be contaminated from the parametrized import test

## Subagent Merge Conflicts

When parallelizing migration phases with subagent delegation, multiple
subagents may modify the same file (e.g. `setup.py` or `pyproject.toml`).
This produces git merge conflicts with `<<<<<<< Updated upstream` /
`=======` / `>>>>>>> Stashed changes` markers that cause
`SyntaxError: invalid syntax`.

Solutions:
- Each subagent uses `patch` mode='replace' on only their specific stub
- Parent agent resolves merge conflicts manually after subagents finish
- Or: serialize the shared-file modifications (parent does all stub-filling)