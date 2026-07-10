# Handle Wrapping Patterns (Integrating Existing Code as Handles)

When introducing Controller+Handle into an existing project, existing
classes must be wrapped as handles. Three patterns proven in practice.

## Pattern 1: Factory-Handle Closure (Wrapping Many Similar Classes)

When 5+ similar existing classes need to be registered as handles, writing
a separate handle class for each becomes repetitive. A factory function
that produces a closure:

```python
def make_handle(klass, display_name: str):
    class ProviderHandle:
        def __init__(self):
            self._klass = klass
            self._name = display_name

        def get_id(self) -> str:
            return klass.__name__

        def get_display_name(self) -> str:
            return self._name

        def process(self, query: str) -> dict:
            instance = self._klass()
            return instance.process(query)

        def is_available(self) -> bool:
            return True

    return ProviderHandle()

# Instead of 7 separate classes:
providers = [(ProviderA, "Provider A"), (ProviderB, "Provider B"), ...]
for klass, name in providers:
    ctrl.register(make_handle(klass, name))
```

When to apply: 5+ similar classes with the same interface shape that all
need wrapping. Under 5: explicit handle classes are clearer.

PITFALL: Closure-handles cannot hold state beyond the klass parameter. If
handles need individual state (circuit breaker, config, per-request
instances), write explicit classes.

## Pattern 2: Enum-to-Handle Mapping (Migration Bridge)

When an existing project uses Enum+Switch for dispatch, you cannot switch
everything to Controller+Handle at once. A lookup table in the controller
bridges the transition:

```python
def find_handle_for_enum(self, enum_value) -> Optional[DomainHandle]:
    type_map = {
        "TYPE_A": "handle_a",
        "TYPE_B": "handle_b",
        "TYPE_C": "handle_c",
    }
    name = enum_value.name if hasattr(enum_value, 'name') else str(enum_value)
    handle_id = type_map.get(name)
    if handle_id and self.has_handle(handle_id):
        return self.get_handle(handle_id)
    return None
```

Caller code can be migrated incrementally:
- Phase 1: Introduce controller with enum-to-handle mapping. Existing code
  calls `find_handle_for_enum()` instead of the old switch.
- Phase 2: New handles register directly via `get_handle("new_type")` —
  without extending the enum.
- Phase 3: When all callers use `get_handle()` directly, the enum mapping
  can be removed.

When to apply: Migration of a grown codebase with existing enum-based
dispatch. For greenfield projects: not needed, use `get_handle(id)` directly.

PITFALL: The enum mapping is temporary migration code. If it stays
permanently, you have two dispatch mechanisms (Enum+Map and Handle-Registry)
which causes confusion. The mapping table should carry a comment:
"MIGRATION: remove when all callers use get_handle() directly."

## Pattern 3: Inline Handle Classes in init() (Stylistic Choice)

Handle classes can be defined INSIDE the `init_xxx_controller()` function
rather than at module level:

```python
def init_domain_a_controller():
    ctrl = get_domain_a_controller()

    class PrimaryHandle:
        def get_id(self): return "primary"
        def process(self, data): return self._service.process(data)

    ctrl.register(PrimaryHandle())
```

Advantages:
- Namespace stays clean — handle classes are only visible inside init.
- Handle classes are co-located with their registration.

Disadvantages:
- Handle classes cannot be imported by other modules (e.g., for tests
  that use concrete handles instead of fakes).
- With 10+ handles, the init function becomes very long.

Recommendation: Under 5 handles that are only used in init(): inline is
fine. With 5+ handles or when tests need to import concrete handles:
module-level classes.

## When These Patterns Are Relevant

| Trigger | Pattern | Reference |
|---------|---------|-----------|
| 5+ similar classes to wrap | Factory-Handle Closure | Pattern 1 |
| Migrating from Enum+Switch | Enum-to-Handle Mapping | Pattern 2 |
| <5 handles, co-location desired | Inline Handle Classes | Pattern 3 |