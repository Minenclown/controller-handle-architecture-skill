# Handle Lifecycle (O1) + Circuit Breaker (O4) — Implementation Notes

Both optimizations are additive — no breaking changes, all existing
controller tests remain green.

## O1: Handle Lifecycle Interface

### Files (typical layout)

- `controllers/lifecycle.py` — `HandleLifecycle` protocol
  (`@runtime_checkable`, `on_register()` / `on_disable()`)
- `controllers/base.py` — `register()` / `unregister()` call hooks
- `controllers/handles/*_handle.py` — `__init__` with
  `self._engine = None`, `on_register` no-op, `on_disable` sets
  `_engine = None`
- `tests/test_controllers/test_lifecycle.py`

### Pattern

- `hasattr(handle, "on_register")` checks if the hook exists — handles
  without hooks work unchanged (non-breaking).
- Exceptions in lifecycle methods are caught and logged as warnings, not
  propagated. A faulty `on_register()` must not crash `register()`.
- `on_disable()` is called BEFORE the `del`, `on_register()` AFTER adding
  to the dict. Order matters for hot-reload scenarios.
- Resource-holding handles: `on_register` = no-op (lazy init),
  `on_disable` sets the resource reference to None — the underlying
  singleton/service remains unaffected, only the handle's reference is
  released.

### Test Patterns

- Protocol existence and `runtime_checkable` behavior
- Register/unregister hook invocation with a handle that records calls
  (`registered_called` / `disable_called` flags)
- "Does not crash without hook" test with a plain handle that only has
  `get_id()` — important for backward compatibility
- Resource handle tests: `on_disable` sets `_engine = None` — set
  `_engine` to a sentinel object, call `on_disable()`, assert None

## O4: Circuit Breaker

### Files (typical layout)

- `controllers/circuit_breaker.py` — `CircuitBreaker` class
- `controllers/base.py` — `_breakers` dict, `is_handle_available()`,
  `get_breaker()`, breaker cleanup in `unregister()`
- `controllers/domain_controller.py` — `get_primary()` and
  `get_available_handles()` skip tripped handles with logging
- `tests/test_controllers/test_circuit_breaker.py`

### Pattern

- `_breakers: Dict[str, CircuitBreaker]` is initialized in
  `Controller.__init__` — one breaker per handle, created in
  `register()`.
- `is_handle_available(handle_id)` is the central query — returns False
  if the breaker is tripped, True otherwise. If the handle doesn't
  exist, returns False (safe default).
- `get_breaker(handle_id)` allows direct access for
  `record_failure()` / `record_success()` calls from the call layer.
- `unregister()` does `_breakers.pop(handle_id, None)` — no leak.
- `get_primary()` uses `is_handle_available()` BEFORE calling
  `h.is_available()` — tripped handles are skipped before the expensive
  availability check (which might make an HTTP call).
- Logging: `logger.info` in `get_primary()` (user-relevant),
  `logger.debug` in `get_available_handles()` (frequent, less important).

### Test Patterns

- CircuitBreaker unit tests: threshold, window-expiry (with
  `time.sleep` and very short `window_sec=0.05`), cooldown-expiry,
  `record_success` resets
- Controller integration: `is_handle_available` False when tripped,
  `get_breaker` None for unknown handles, breaker removal on unregister
- Domain controller integration: `get_primary` skips tripped and
  unavailable handles, returns None when all are tripped, test stub
  with controllable `is_available()`

### IMPORTANT: Non-disruptive by Default

The circuit breaker is purely additive. `record_failure()` /
`record_success()` are never called automatically — the call layer
must do this explicitly. Until that happens, all breakers remain in
the not-tripped state and `is_handle_available()` always returns True.
This is intentional — O4 must not disrupt existing functionality.

## Pitfall P9: Parallel-Edit Race Condition on Shared Files

**Symptom:** While editing `domain_controller.py` with `patch`, a
parallel subagent modified the same file. The patch produced a
**duplicate file header**: two docstrings and two `from __future__`
imports back to back. The linter reported `Imports from __future__ must
be at the beginning of the file`.

**Cause:** `patch` (find-replace) searches for `old_string` and
replaces it. If a parallel subagent changed the file between the
`read_file` and `patch`, the fuzzy matcher can find the old content and
prepend the new content instead of replacing it.

**Fix:**
1. After every `write_file`/`patch` on shared files, re-read the file and
   check for duplication.
2. On header duplication, rewrite the file completely with
   `write_file`, preserving all legitimate changes from both subagents.
3. `git diff` at the end of all changes reveals duplications immediately.

**Prevention:** In parallel subagent sessions, each subagent should only
use `patch` (never `write_file` on shared files) and re-read the file
after each change. The orchestrator should serialize shared files (like
`base.py`, `domain_controller.py`) — only domain-specific files (one
handle per subagent) are safe to parallelize.
