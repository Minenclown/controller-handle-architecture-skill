# Core Workflow — Basis Generation

This file MUST be loaded before generating code. It contains the detailed
execution of the 10 design principles, Bad/Good transformations,
anti-patterns, testing guidance, and minimum code output.

The Core Digest in SKILL.md is the compressed guardrail. This file is the
full execution with examples.

## The 10 Design Principles (Detail)

1. **One Controller per Domain** — Each functional area gets exactly one
   controller. All controllers look the same: registry with register/get/
   has plus domain-specific convenience methods.

2. **Handle as Interface/Protocol** — Defines the domain-specific API.
   Every handle MUST implement `get_id()`. Optionally `get_display_name()`
   for UI/logs.

3. **Dynamic Registration** — New functionality =
   `controller.register(new Handle())`. No if/else, no changes to
   existing controller or dispatch logic; the composition root MAY be
   extended. Open/Closed Principle.

4. **Insertion-Ordered Map** — Use whatever your language provides to
   preserve insertion order. Critical for fallback chains (first available
   handle = primary) and deterministic iteration.

5. **Service Wrapping, not Service Deletion** — Existing service/manager
   classes are not deleted. Handles wrap them. Backward compatibility is
   preserved; the new API sits on top.

6. **Lazy Imports/Initialization** — For heavy, optional, circular, or
   slow dependencies: load lazily (in the method body, not at module
   level). Do not add lazy loading for simple in-process dependencies.

7. **Fail-Fast on Unknown Handles** — `getHandle("unknown")` throws an
   exception. No silent null return.
   Exception: Plugin systems with optional extensions. Callers MUST check
   `has_handle()` before calling `get_handle()`. Rule: ALL handles
   mandatory → fail-fast. Some optional → `has_handle()` + fallback.
   Never silent null.

8. **Decouple Listeners/Event Handlers** — Listeners query only the
   controller, never concrete implementations.

9. **Config from YAML/JSON** — When modes, rules, or handles are
   user-configurable: define in config files. Do not add config files
   for static code-only selection.

10. **Idempotent Initialization** — `init_controllers()` can be called
    multiple times. An `_initialized` flag prevents double-registration.

## Runtime Terminology

These terms are used throughout the skill documentation and must be
clearly distinguished:

- **Runtime-selectable:** An existing implementation is chosen at runtime
  by ID, config, or capability.
- **Code-extensible:** A new implementation can be added without modifying
  existing controller or dispatch logic. The composition root MAY be
  extended.
- **Hot-pluggable:** Implementations can be registered or removed during
  the running process.

Controller+Handle requires runtime-selectable + code-extensible.
Hot-plugging is NOT a prerequisite — it requires O6 Reload or dynamic
plugin registration.

## The Pattern in 3 Layers

```
┌─────────────────────────────────────────┐
│  Composition Root                       │  ← App/Plugin/Registry
│  - instantiates all controllers         │
│  - registers handles                    │
│  - provides getters for all controllers │
└──────────────┬──────────────────────────┘
               │
   ┌───────────┴───────────┐
   │   Controller          │   ← Registry per domain
   │   - Map<String, Handle> │
   │   - register/get/has   │
   │   - domain-specific    │
   │     convenience methods│
   └───────────┬───────────┘
               │
   ┌───────────┴───────────┐
   │   Handle (Interface)  │   ← Protocol/Interface per domain
   │   - get_id() → str    │
   │   - domain methods    │
   └───────────┬───────────┘
               │
   ┌───────────┴───────────┐
   │   ConcreteHandle      │   ← Implementation
   │   - wraps a service   │
   │   - or standalone     │
   └───────────────────────┘
```

## Bad → Good Transformations

**if/else provider dispatch:**
```
Bad:   if provider == "alpha": return alpha.search(q)
       elif provider == "beta": return beta.search(q)

Good:  search_ctrl.get_handle(provider).search(q)
```

**God Manager:**
```
Bad:   class MegaManager:
           def search(self, q): ...
           def store(self, data): ...
           def render(self, view): ...

Good:  search_ctrl.get_handle(id).search(q)
       store_ctrl.get_handle(id).store(data)
```

**Listener knows concrete implementation:**
```
Bad:   if current_mode == "advanced":
           advanced_engine.process(data)
       else:
           basic_engine.process(data)

Good:  engine_ctrl.get_primary().process(data)
```

## Minimum Code Output

When applying this pattern to a domain, you MUST generate at minimum:

- Handle interface/protocol — with `get_id()` and domain methods
- Controller — registry with `register`, `get_handle`, `has_handle`, and
  domain-specific convenience methods
- At least one concrete handle (template demonstration — in real code,
  generate ALL implementations identified during analysis. Do not
  introduce the pattern for a domain unless 3+ genuinely different
  implementations justify it.) — wrapping an existing service if one
  exists, standalone otherwise
- Composition root — `init_controllers()` that is idempotent
- Tests for: register adds, get_handle returns, unknown throws, insertion
  order preserved, unregister removes, init idempotent

All five elements are required. Do not generate partial implementations.

## Testing Guidance

- **Controller isolation:** Fresh controller per test. Reset singleton.
- **Fake handles:** Simple test handles with predefined returns.
- **Fake module contamination:** Clean up in setup/teardown hooks.
- **What to test:** register, get_handle, unknown→Exception, order,
  unregister.
- **What NOT to test:** Concrete handle implementation (has own tests).
- **Integration vs. unit:** Controller = unit (fakes). Handle = unit
  (fake services). Composition root = integration.
- **Concurrency tests:** Required whenever shared controller state can be accessed from multiple threads, tasks, workers, or request handlers. See `templates/concurrency-testing.md`.

## Anti-Patterns (Avoid)

- God Controller — one per domain, not one for everything.
- Handle without Interface — pattern is meaningless without common interface.
- Silent null on getHandle — always throw.
- Import chains at module level — lazy imports in handles.
- Delete services instead of wrapping — backward compat is lost.
- Hardcoded handle IDs in listeners — query the controller.
- Unordered map — use insertion-ordered data structure.
- TypeVar bound to Protocol (language-specific) — omit bound in structural
  typing languages.
- Composite handle creates new instances — use constructor injection.
- Controller Inflation — one per domain, not per feature.
- Handle Hopping — handles must not know other controllers.
- God Handle — >7 methods or >200 lines → split.
- Registry as Configuration — config values are not handles.
- Over-Abstracted Protocol Tower — max 2 levels: HandleBase → DomainHandle.

## Review Checklist

Reject or revise if:
- [ ] Handle fetches dependencies from global registry instead of constructor
- [ ] Listener references concrete handle IDs instead of querying controller
- [ ] Existing services deleted instead of wrapped
- [ ] Unknown handle returns null (except optional plugin handles with has_handle check)
- [ ] Duplicate registration silently overwrites
- [ ] Controller contains business logic instead of delegating
- [ ] Composition root spread across unrelated files
- [ ] Tests share global state without reset
- [ ] Handle IDs duplicated as ad-hoc string literals across consumers.
      A handle declaring its own stable ID once is fine. Use typed
      constants (O7) when IDs are referenced from multiple locations.
- [ ] get_handles() returns internal dict reference

## When to Add a New Handle vs. a New Method

- New Handle: new external provider, own state, own config.
- New method: same implementation, new operation.
- Refactor signal: >200 lines or >7 methods → split.
- Guideline: 3-7 handles per controller.

## Pattern Relationships

### Strategy + Registry
Controller+Handle = Registry (lookup) + Strategy (interface). Need both?
- Need only Strategy (fixed set, runtime selection)? A simple
  `Map<Enum, Strategy>` in the context suffices. No controller.
- Need only Registry (dynamic discoverability, no common interface)?
  Use a small explicit factory or map at the composition boundary.
  Do NOT introduce a Service Locator into business logic.
- Need both (dynamic + interface + code-extensible)?
  → Controller+Handle.
### Hexagonal Architecture Mapping
Port → Handle Interface, Adapter → Concrete Handle, Core → Controller +
Composition Root. Orientation only, not a new abstraction layer.

## Composition Root vs. Service Locator

- Composition Root (good): ONE place wires everything. Constructor injection.
- Service Locator (bad): classes fetch their own deps via lookup. Hidden coupling.
- Rule: Handles must NOT know controllers. Deps via constructor, not lookup.
- Exception: Composite handles (O5) — see core-optimizations.md.