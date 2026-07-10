# Composition Root Patterns (Multi-Controller Orchestration)

When a project has more than 2-3 controllers, practical questions arise
that go beyond "idempotent init()": How do you orchestrate multiple
singleton controllers? How do you reset them for tests? In what order
should they be initialized?

## Pattern 1: Singleton-per-Controller + Central Composition Root

Each controller has its own singleton + getter. The composition root is
a SEPARATE module that orchestrates all singletons.

```python
# Per-controller singleton (each controller module has its own)
_domain_a_controller: Optional[DomainAController] = None

def get_domain_a_controller() -> DomainAController:
    global _domain_a_controller
    if _domain_a_controller is None:
        _domain_a_controller = DomainAController()
    return _domain_a_controller
```

```python
# composition_root.py — the ONLY place that knows all controllers
_initialized = False
_controllers: Dict[str, object] = {}

def init_all_controllers() -> Dict[str, object]:
    global _initialized, _controllers
    if _initialized:
        return _controllers

    _controllers["domain_a"] = init_domain_a_controller()
    _controllers["domain_b"] = init_domain_b_controller()
    _controllers["domain_c"] = init_domain_c_controller()

    _initialized = True
    return _controllers

def get_controller(name: str):
    if name not in _controllers:
        raise KeyError(f"Controller '{name}' not initialized.")
    return _controllers[name]
```

Why both — singleton-per-controller AND central dict?
- Individual modules get their controller directly:
  `get_domain_a_controller()` — without importing the composition root.
- The composition root offers name-based lookup:
  `get_controller("domain_a")` — useful for generic code (REST API,
  tests, reload logic).

These getters are allowed ONLY at bootstrap, framework integration
boundaries, legacy adapters, and tests. Domain services, handles,
listeners, and ordinary business objects receive typed dependencies
through constructors.

IMPORTANT: The composition root is the ONLY place that knows init order.
Individual `init_xxx_controller()` functions know nothing about each other.

## Pattern 2: reset_controllers() for Test Isolation

With multiple singleton controllers, `registry.clear()` is not enough —
each singleton must be reset. A central reset function:

```python
def reset_controllers() -> None:
    """Reset all controllers. For testing only."""
    global _initialized, _controllers
    _initialized = False
    _controllers = {}

    # Reset each singleton
    import app.domain_a_controller as da
    da._domain_a_controller = None

    import app.domain_b_controller as db
    db._domain_b_controller = None

    import app.domain_c_controller as dc
    dc._domain_c_controller = None
```

Every test using controllers should call reset in setUp:

```python
class TestCompositionRoot:
    def setUp(self):
        reset_controllers()

    def test_init_all(self):
        controllers = init_all_controllers()
        assert len(controllers) == 3
```

PITFALL: If reset_controllers() forgets a singleton, tests inherit
controller instances from other tests — hidden test dependencies that
cause flaky tests. Solution: reset_controllers() must know all singletons.
When adding a new controller: update the reset function. A
forget-resistance test (assert all singletons are None after reset) helps.

## Pattern 3: Init Ordering (Dependency-Ordered)

Controllers may depend on each other. The composition root must know the
order and document it explicitly:

```python
def init_all_controllers():
    # 1. Domain A — no deps on other controllers
    _controllers["domain_a"] = init_domain_a_controller()

    # 2. Domain B — depends on domain A's registered handles
    _controllers["domain_b"] = init_domain_b_controller()

    # 3. Domain C — may reference domain A and B handles
    _controllers["domain_c"] = init_domain_c_controller()
```

Rule: Controllers with no controller-dependencies first. Controllers that
know other controllers (via composition root injection) after.

PITFALL: If controller A's init() expects handles registered by B, but B
is not yet initialized → KeyError at startup. Solution: comment init order
explicitly. For circular dependencies: lazy resolution — handle fetches
dependency at method-call time, not in constructor. See O5 exception.

## When These Patterns Are Relevant

| Trigger | Pattern | Reference |
|---------|---------|-----------|
| 3+ controllers in project | Composition Root dict | Pattern 1 |
| Tests share controller state | reset_controllers() | Pattern 2 |
| Controllers depend on each other | Init ordering | Pattern 3 |

For 1-2 controllers: YAGNI — direct singleton access suffices, no central
composition root needed.