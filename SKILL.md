---
name: controller-handle-architecture
category: software-development
description: |
  Scalable architecture following the Controller-Handle-Interface pattern.
  Language-agnostic architecture pattern. Designed to avoid
  over-engineering while remaining adaptive and maintaining clear structure
  across any program.
---

# Controller-Handle-Interface Architecture

A language-agnostic architectural pattern for building extensible systems
that scale gracefully. One controller per domain, handles registered
dynamically, zero if/else dispatch trees.

## When to Apply This Skill

- New project with 3+ distinct functional domains
- Refactoring a grown codebase with if/else dispatch trees, duplicated
  manager classes, or hard-to-test logic
- Project must scale: new features without modifying existing classes
- Listeners, event handlers, or commands should be decoupled from
  business logic

## When NOT to Apply This Skill

Use this decision matrix first. Applying the pattern to simple projects
is over-engineering.

```
Question                                     Answer   Recommendation
──────────────────────────────────────────────────────────────────────
Does the project have 3+ functional domains?  No      No pattern needed
                                               Yes     continue

Are the domains genuinely different?           No      A dispatcher suffices
                                               Yes     continue

Must they be extensible at runtime?            No      Enum + switch suffices
                                               Yes     continue

Do you need more than ID lookup                No      Strategy pattern suffices
(fallback, capabilities, etc.)?                Yes     Controller+Handle

Is the project multi-threaded/server?          No      Core-10 suffices
                                               Yes     Core-10 + Thread-Safety
```

### Rule of Three for Entry

- **1-2 domains?** You don't need a controller. A simple interface
  implementation or factory suffices.
- **3+ domains, but all similar (e.g., 5 listeners)?** You don't need a
  controller per domain. A single dispatcher suffices.
- **3+ domains, different, but static (never change)?** You don't need
  dynamic registration. An enum + switch suffices.
- **3+ domains, different, AND runtime-extensible (without code changes)?**
  THEN use Controller+Handle.

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

## Rule 0: Minimum Viable Architecture (MVA)

Before anything else: **start with the minimum, add only what solves a
concrete pain point.** This is the guiding principle of the entire skill.

- **Core (Level 0):** Controller + Handle Interface + Registry. Nothing
  more. This covers 80% of projects.
- **Enhancements (O1-O8):** Each solves a specific problem. Add only
  when you have that problem NOW — not "just in case."
- **Decision rule per enhancement:** "Do you have [problem X] right now?
  → If no, do not implement."

YAGNI is not "never add abstraction." It is "only add abstraction when
you are solving a specific problem that requires it."

## Core Design Principles (1-10)

1. **One Controller per Domain** — Each functional area gets exactly one
   controller. All controllers look the same: a registry of handles with
   register/get/has methods plus domain-specific convenience methods.

2. **Handle as Interface/Protocol** — Defines the domain-specific API.
   Every handle MUST implement `get_id()`. Optionally `get_display_name()`
   for UI/logs.

3. **Dynamic Registration** — New functionality = `controller.register(new
   Handle())`. No if/else, no modification of existing classes.
   Open/Closed Principle.

4. **Insertion-Ordered Map** — Use whatever your language provides to
   preserve insertion order (ordered dict, linked map, etc.). Critical
   for fallback chains (first available handle = primary) and
   deterministic iteration.

5. **Service Wrapping, not Service Deletion** — Existing service/manager
   classes are not deleted. Handles wrap them. Backward compatibility is
   preserved; the new API sits on top. Example: a handle wraps an existing
   database client, exposing it through the handle interface without
   rewriting the client.

6. **Lazy Imports/Initialization** — Heavy dependencies are loaded lazily
   (in the method body, not at module level). Prevents import chains and
   reduces startup time/memory. See Scaling (S1) for why this matters
   beyond import cycle prevention.

7. **Fail-Fast on Unknown Handles** — `getHandle("unknown")` throws an
   exception. No silent null return. Callers must provide valid IDs.

8. **Decouple Listeners/Event Handlers** — Listeners query only the
   controller, never concrete implementations. Example:
   `controller.isAllowed(player, Rule.ALLOW_DAMAGE)` instead of
   `isInSpecificMode()`.

9. **Config from YAML/JSON** — Modes, categories, rules are defined in
   config files. Controller loads them at startup. Default values are
   created when the file is missing.

10. **Idempotent Initialization** — `init_controllers()` can be called
    multiple times. An `_initialized` flag prevents double-registration.
    Important for tests and reloads.

## Composition Root vs. Service Locator — The Critical Boundary

The pattern uses a Composition Root (good). The line to Service Locator
(often criticized) is thin. Observe these rules:

- **Composition Root (good):** Exactly ONE place (app entry point, plugin
  enable, `__init__.py`) instantiates everything and wires it together.
  Controllers and handles receive dependencies via constructor injection.
  Nobody else fetches dependencies from the registry.
- **Service Locator (bad):** When listeners, handles, or other classes
  call `getControllerRegistry().getController(...)` to fetch their own
  dependencies. This creates hidden coupling.
- **The rule:** Controllers may know other controllers (via the
  composition root). Handles must NOT know controllers. Handles receive
  dependencies via constructor, not via lookup.
- **Exception:** Composite handles (O5) depend on the controller — this
  is a known compromise. Alternative: pass sub-handles to the composite
  handle via constructor instead of having it look them up.

## Pattern Relationships

### Strategy + Registry

This pattern combines two classic patterns:
- **Strategy Pattern:** Handles are strategies — interchangeable
  implementations behind a common interface.
- **Registry Pattern:** Controllers are registries — lookup tables for
  ID → implementation.

You need BOTH aspects to justify this pattern:
- Need only Strategy (fixed set of strategies, runtime selection)?
  A simple `Map<Enum, Strategy>` in the context suffices. No controller.
- Need only Registry (dynamic discoverability, no common interface)?
  A service locator suffices. No handle hierarchy.
- Need both (dynamic discoverability + common interface + runtime
  extensibility)? Controller+Handle.

### Hexagonal Architecture Mapping

If you know Hexagonal Architecture (Ports & Adapters), the mapping is:

```
Hexagonal                →  Controller+Handle
Port (Interface)          →  Handle Interface / Protocol
Adapter (Implementation)  →  Concrete Handle
Application Core          →  Controller + Composition Root
Driving Adapter            →  Listener/Command that calls the controller
Driven Adapter              →  Concrete Handle (DB, API, external service)
```

This is for orientation only — do not add hexagonal architecture as an
additional abstraction layer on top.

## Templates

This skill contains copy-paste templates for three languages:
- `templates/java_template.java` — Controller, Handle Interface, ConcreteHandle, Composition Root
- `templates/python_template.py` — Controller Base, HandleBase Protocol, Domain Controller, ConcreteHandle, ControllerRegistry, init_controllers
- `templates/typescript_template.ts` — same structure for Tauri/frontend
- `templates/java_optimizations.java` — Lifecycle, EventBus, CircuitBreaker, Reloadable, HandleIds, ControllerMetrics, EnhancedController
- `templates/python_optimizations.py` — same optimizations, Python-idiomatic

## Step-by-Step: Setting Up a New Project

1. **Identify domains** — What functional areas exist? (e.g., Search,
   Storage, Rendering, Sync)

2. **Per domain: define Handle protocol** — What methods does the domain
   need? Only `get_id()` is mandatory; the rest is domain-specific.

3. **Write Controller** — Copy the template once, add domain-specific
   convenience methods.

4. **Implement Concrete Handles** — Wrap existing services/classes. Use
   lazy imports for heavy dependencies.

5. **Write Composition Root** — Instantiate all controllers, register all
   handles. Make it idempotent.

6. **Wire Event Handlers/Listeners/Commands to Controllers** — Instead
   of `if (isInX())` → `if (controller.isAllowed(...))`.

7. **Create Config Files** — Outsource rules, categories, modes to
   YAML/JSON. Generate defaults when files are missing.

8. **Write Tests** — Reset controller registry, register handles, test
   the API. See Testing Guidance below.

## When to Add a New Handle vs. a New Method

- **New Handle** when: a new external provider (new search engine, new
  database, new mode set). The implementation lives in a separate class,
  has its own state, its own config.
- **New method on existing handle** when: same implementation, new
  operation (e.g., `search()` + `search_async()`). That is an interface
  extension, not a new handle.
- **Refactor signal:** When a handle exceeds ~200 lines or ~7 methods,
  consider splitting it into two handles.
- **Guideline:** 3-7 handles per controller is a healthy range. Too many
  handles with 1 method each is also over-engineering.

## Anti-Patterns (Avoid)

- **God Controller** — One controller for everything. One controller per
  domain, no more.
- **Handle without Interface** — If handles don't share a common
  interface, the pattern is meaningless.
- **Silent null on getHandle** — Always throw. Callers must provide
  valid IDs.
- **Import chains at module level** — Lazy imports in handles, not in
  the controller layer.
- **Delete services instead of wrapping** — Backward compatibility is
  lost. Wrap and layer the new API on top.
- **Hardcoded handle IDs in listeners** — Listeners should query the
  controller, not know concrete handle IDs.
- **Unordered map instead of insertion-ordered map** — Insertion order is
  lost, fallback chains become non-deterministic. Use an insertion-ordered
  data structure (most modern languages provide one by default).
- **TypeVar bound to Protocol (language-specific)** — In languages with
  structural typing (e.g., Python Protocols), binding a generic type
  variable directly to a Protocol may raise a TypeError. Fix: omit the
  bound. Type-safety is not lost due to structural typing. If your
  language has no structural typing, this pitfall does not apply.
- **Composite handle creates new instances** — A handle that delegates
  to other handles should obtain registered instances from the
  controller, not call `new SubHandle()`. See O5.
- **Controller Inflation** — Too many controllers for too few domains.
  One controller per domain, not per feature. "Storage" is a domain;
  "PostgreSQL" is a feature within it — not its own controller.
- **Handle Hopping** — Handles that know other controllers. If handle A
  needs something from controller B, the composition root should wire it
  — not the handle itself.
- **God Handle** — A handle with 15 methods and multiple responsibilities.
  Split criterion: >7 methods or >200 lines → split.
- **Registry as Configuration** — Not every config detail needs a handle.
  "Dark Mode" is config, not a handle. "Render Engine: Skia vs. Canvas"
  is a handle. Ask: "Could this be a boolean in a config file?" → If yes,
  no handle.
- **Over-Abstracted Protocol Tower** — Protocols inheriting protocols
  inheriting protocols. Maximum 2 levels: HandleBase → DomainHandle.
  Concrete handles implement DomainHandle directly. No further
  intermediate protocols.

## Testing Guidance

- **Controller isolation:** Each test creates a fresh controller or
  resets the registry singleton. Do not share controller state between
  tests.
- **Fake handles:** Simple test handles with predefined return values.
  No real services/engines.
- **Fake module contamination:** If your test framework allows injecting
  fake modules into the module system, these can contaminate subsequent
  tests that import real modules. Solution: clean up fake modules in
  setup/teardown hooks or isolate test files that use fakes from those
  that import real modules.
- **What to test:** `register()` adds, `get_handle()` returns correctly,
  `get_handle("unknown")` throws, insertion order is preserved,
  `unregister()` removes cleanly.
- **What NOT to test:** The concrete handle implementation (that has its
  own tests). The controller tests only registry logic.
- **Integration vs. unit:** Controller tests are unit tests (fake handles).
  Handle tests are unit tests (fake services). Composition root tests are
  integration (real handles, real services).

## Progressive Enhancements (O1-O8)

The core 10 principles cover the fundamental architecture. The following
8 enhancements raise the pattern to production level. They are optional
when starting a new project, but recommended as the project grows.

Each enhancement is **independent and additive** — pick and choose based
on concrete pain points. They are NOT sequential phases.

### O1: Handle Lifecycle Interface

Handles have optional `on_register`/`on_disable` hooks. Cleanup is
formalized, hot-reloads become cleaner. **Additive and non-breaking:**
handles without lifecycle methods work unchanged.

```python
@runtime_checkable
class HandleLifecycle(Protocol):
    def on_register(self) -> None: ...
    def on_disable(self) -> None: ...
```

Controller calls `on_register()` after adding to the dict and
`on_disable()` before removing — both only if `hasattr(handle, method)`
is True. Exceptions in lifecycle methods are caught and logged, not
propagated (a faulty `on_register()` must not crash `register()`).

**When:** Handles hold resources (DB connections, model sessions) that
need explicit setup/cleanup. Stateless handles: YAGNI.

### O2: Inter-Controller Communication via Event Bus

When controllers need to communicate, direct access (`plugin.getXController()`)
couples them. An event bus decouples this.

```python
class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, channel: str, handler: Callable):
        self._listeners[channel].append(handler)

    def emit(self, channel: str, *args, **kwargs):
        for handler in self._listeners.get(channel, []):
            handler(*args, **kwargs)
```

Controller A emits `("domain_a.event", payload)`. Controller B subscribes.
Controller A does not know controller B exists. New controllers can react
to existing events without modifying the emitter.

**When:** Inter-controller coupling becomes painful (3+ controllers
reference each other). Single domain or 2 controllers: YAGNI.

### O3: Capability Resolution Instead of ID Lookup

Instead of `get_handle("pdf")`, handles declare what they can do and
controllers search by capability:

```python
def find_handle(self, **criteria) -> Optional[H]:
    for h in self.get_handles():
        if hasattr(h, "matches") and h.matches(**criteria):
            return h
    return None
```

Makes handles interchangeable. "Give me an available engine handle"
instead of "Give me the ollama handle."

**When:** Growing handle count, multiple handles can satisfy the same
request. Fixed IDs with no ambiguity: YAGNI.

### O4: Circuit Breaker per Handle

When a handle crashes at runtime (external service dies mid-request),
there is no protection. A circuit breaker per handle:

```
3 failures in 30 seconds → handle is skipped for 60 seconds
get_primary() automatically ignores tripped handles
```

```python
class CircuitBreaker:
    def __init__(self, threshold=3, window_sec=30, cooldown_sec=60):
        self._threshold = threshold
        self._window_sec = window_sec
        self._cooldown_sec = cooldown_sec
        self._errors: deque = deque()
        self._tripped_until: float = 0.0

    def record_failure(self):
        now = time.time()
        self._errors.append(now)
        while self._errors and now - self._errors[0] > self._window_sec:
            self._errors.popleft()
        if len(self._errors) >= self._threshold:
            self._tripped_until = now + self._cooldown_sec

    def record_success(self):
        self._errors.clear()
        self._tripped_until = 0.0

    def is_tripped(self) -> bool:
        return time.time() < self._tripped_until
```

Controller integration (additive, non-breaking):
- `_breakers: Dict[str, CircuitBreaker]` in `Controller.__init__`
- `register()` creates a breaker per handle
- `unregister()` removes the breaker
- `is_handle_available(handle_id)` returns False if breaker is tripped
- Fallback chains (`get_primary()`) skip tripped handles with logging

**When:** Multi-user server where one handle failure shouldn't block all
users. Single-user CLI: YAGNI — `is_available()` suffices.

### O5: Resolve Handle Dependencies via Controller

A composite handle that delegates to other handles should obtain them
from the controller, not create new instances:

```python
# Bad — creates new instances, state is inconsistent
sub_handle = SubHandle()

# Good — obtains the registered instance
from app.controllers.registry import get_controller_registry
ctrl = get_controller_registry().get_controller("domain_a")
sub_handle = ctrl.get_handle("sub_handle_id")
```

**When:** Composite handles exist. No composite handles: YAGNI.

### O6: Unified Reload

A `Reloadable` interface with `reload()`. The controller registry calls
`reload()` on all controllers that implement it. One command reloads
everything.

```python
@runtime_checkable
class Reloadable(Protocol):
    def reload(self) -> None: ...

def reload_all():
    for ctrl in get_controller_registry()._controllers.values():
        if hasattr(ctrl, "reload"):
            ctrl.reload()
```

Critical implementation details:
1. **Lazy imports in reload()** to avoid circular imports — the
   `_register_*_handles` functions live in the composition root which
   imports all controller modules. Import within the `reload()` method.
2. **reload() creates new handle instances** — `_handles.clear()` +
   re-register. This is intentional: handles may have state that should
   reset.
3. **Copy-on-Write for thread safety** — see Scaling (S2).

```python
class DomainController(Controller[DomainHandle]):
    def reload(self) -> None:
        new_handles = {}
        # ... register new handles into new_handles ...
        self._handles = new_handles  # atomic reference swap
```

**When:** Config changes require reload without app restart (server,
multi-user). Desktop app where restart is fast: YAGNI.

### O7: Typed Handle IDs

Handle IDs are raw strings: `getHandle("primary")`. Typos are runtime
errors. Constants or enums prevent this:

```java
public final class HandleIds {
    public static final String DOMAIN_A_PRIMARY = "primary";
    public static final String DOMAIN_A_SECONDARY = "secondary";
    public static final String DOMAIN_B_ALPHA = "alpha";
    private HandleIds() {}
}
```

```python
class HandleIds:
    DOMAIN_A_PRIMARY = "primary"
    DOMAIN_A_SECONDARY = "secondary"
    DOMAIN_B_ALPHA = "alpha"
```

Prevents `getHandle("Primary")` vs `getHandle("primary")` bugs. IDE
autocomplete works. Refactoring-safe.

**When:** Any project with more than 3-4 handle IDs. The cost is near
zero; the benefit is immediate.

### O8: Metrics / Observability

Track which handle is called how often and how often it fails. A counter
per `handle_id.method_name` key:

```python
class Controller(Generic[H]):
    def __init__(self, name: str = ""):
        # ... existing ...
        self._call_counts: Dict[str, int] = {}
        self._error_counts: Dict[str, int] = {}

    def call(self, handle_id: str, method_name: str, *args, **kwargs):
        key = f"{handle_id}.{method_name}"
        self._call_counts[key] = self._call_counts.get(key, 0) + 1
        handle = self.get_handle(handle_id)
        try:
            return getattr(handle, method_name)(*args, **kwargs)
        except Exception:
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            raise

    def get_metrics(self) -> Dict[str, Dict[str, int]]:
        return {
            "calls": dict(self._call_counts),
            "errors": dict(self._error_counts),
        }
```

**When:** Multi-user server needing admin diagnostics. Single-user CLI:
YAGNI — `print()` / `journalctl` suffices.

## Enhancement Prioritization

Prioritization depends on deployment context. A single-user desktop app
has different requirements than a multi-user server.

**Single-User Desktop:**

| # | Enhancement | Impact | Effort | Recommendation |
|---|------------|--------|--------|---------------|
| O5 | Handle dependencies via controller | High | Low | Yes — quick fix |
| O7 | Typed handle IDs | Medium | Low | Yes — quick fix |
| O6 | Unified reload | Low | Low | YAGNI — app restart suffices |
| O8 | Metrics / observability | Low | Low | YAGNI — print/journalctl suffices |
| O1 | Handle lifecycle | Low | Medium | YAGNI — handles are stateless |
| O4 | Circuit breaker | Low | Medium | YAGNI — is_available() suffices |
| O3 | Capability resolution | Low | Medium | Only when needed |
| O2 | Event bus | Low | High | Only when needed |

**Multi-User Server:**

| # | Enhancement | Impact | Effort | Recommendation |
|---|------------|--------|--------|---------------|
| O5 | Handle dependencies via controller | High | Low | Yes — quick fix |
| O7 | Typed handle IDs | High | Low | Yes — prevents typos |
| O6 | Unified reload | High | Low | Yes — no restart on config change |
| O8 | Metrics / observability | High | Low | Yes — admin diagnostics |
| O1 | Handle lifecycle | High | Medium | Yes — DB connections/models per instance |
| O4 | Circuit breaker | High | Medium | Yes — one handle crash shouldn't block all users |
| O3 | Capability resolution | Medium | Medium | When handle count grows |
| O2 | Event bus | High | High | When inter-controller coupling appears |

IMPORTANT: Check the deployment context before recommending enhancements.
A multi-tenant server system needs circuit breakers, metrics, and reload.
A desktop app does not.

## Scaling (S1-S6)

The pattern scales along three axes. Each axis has different failure
modes and solutions.

### Axis 1: Horizontal — More Handles per Controller

- **5 handles:** No problems. Insertion-ordered map, O(1) lookup.
- **20 handles:** Lookup still O(1), but startup time becomes noticeable
  if each handle initializes heavy dependencies in its constructor.
- **50+ handles:** Composition root gets unwieldy. Auto-registration (see
  below) becomes relevant. Lazy initialization becomes essential.
- **100+ handles:** Lookup still O(1), but memory footprint matters.
  Handles holding expensive resources (DB connections, ML models) need
  lazy init or resource pooling.
- **Limit:** No hard limit on lookup performance (HashMap is O(1)). The
  real limit is startup time and memory. "100 handles each loading 50MB
  models = 5GB at startup." Lazy init solves this.

### Axis 2: Vertical — More Controllers / More Domains

- **3 controllers:** Composition root is one method, 10 lines. Clear.
- **10 controllers:** Composition root grows to 50+ lines. Needs
  structuring — one `_register_*` function per controller.
- **20+ controllers:** Composition root becomes its own class/file.
  Grouping/namespace structure becomes relevant:
  `controllers.search.*`, `controllers.engine.*`, etc.
- **30+ controllers:** The flat `ControllerRegistry` (one dict with
  name → controller) gets unwieldy. Options:
  - **Controller groups:** Registry has sub-registries per domain group.
    Second hierarchy level.
  - **Modular composition root:** Instead of one big `init_controllers()`,
    each module exports its own `init()` that registers only its controllers.
- **Important:** This is NOT a call to introduce sub-controllers or
  controller hierarchies. A flat registry is better as long as it remains
  readable. Group only at pain point.

### Axis 3: Functional — More Users / Threads / Requests (Concurrency)

- **1 user (CLI, desktop):** Single-threaded. No synchronization needed.
  YAGNI for thread safety.
- **5 users (small server):** Threads exist, but handle map doesn't change
  after startup (handles registered once, then read-only). Read-only map
  access is thread-safe in most languages (no concurrent writes).
- **50 users (multi-user server):**
  - Handle map is effectively immutable after init → reads OK without lock.
  - Circuit breaker (O4) per handle MUST be thread-safe (written at
    runtime — record_failure/record_success).
  - Metrics (O8) counters must be thread-safe (increment).
  - Reload (O6) rewrites the map → needs lock or copy-on-write.
- **100+ users:** Connection pooling for handles holding DB/network
  resources. Circuit breaker is essential. Metrics is essential.
- **Rule:** The handle map itself needs locks only when `register()`/
  `unregister()` is called at runtime (hot-reload, dynamic plugins).
  For init-once + read-only: copy-on-write at reload suffices.

### Scaling Rules

**S1: Lazy Initialization as a Scaling Tool**

Lazy init is not just for avoiding import cycles. It is the most
important scaling tool: handles holding expensive resources (ML models,
DB connections, large caches) should load them LAZY — on first method
call, not in the constructor.

```python
class ProviderHandle:
    def __init__(self):
        self._engine = None  # lazy — loaded on first use

    def process(self, query):
        if self._engine is None:
            from app.engines.provider import ProviderEngine
            self._engine = ProviderEngine.get_instance()
        return self._engine.process(query)
```

"100 handles each loading 50MB models = 5GB at startup. Lazy init = 0MB
until a handle is used."

**S2: Copy-on-Write for Handle Map at Reload**

Instead of locking `register()`/`unregister()` at runtime, on reload:
build a new map, atomically swap the reference. Read operations need no
lock — they see either the old or the new map, never a half-updated one.

```python
def reload(self):
    new_handles = {}
    # ... register new handles into new_handles ...
    self._handles = new_handles  # atomic reference swap
```

Use your language's mechanism for atomic reference swaps (volatile
references, atomic variables, etc.). Works only if old handle instances
are not used after reload (which is the case — callers fetch fresh from
the controller).

**S3: Resource Pooling for Expensive Handles**

When a handle holds a limited resource (DB connection, model session)
and multiple users access it simultaneously: pool instead of singleton.

```python
class ProviderHandle:
    _pool = None  # lazy init

    def process(self, query):
        conn = self._get_pool().acquire()
        try:
            return conn.process(query)
        finally:
            self._get_pool().release(conn)
```

Only for real bottlenecks. Under 10 concurrent users: YAGNI, singleton
suffices.

**S4: Composition Root Modularization at 10+ Controllers**

Instead of a monolithic `init_controllers()`:

```python
def init_controllers():
    _init_domain_a_controllers(reg)
    _init_domain_b_controllers(reg)
    _init_domain_c_controllers(reg)

def _init_domain_a_controllers(reg):
    ctrl = DomainAController()
    ctrl.register(PrimaryDomainAHandle())
    ctrl.register(SecondaryDomainAHandle())
    reg.register_controller("domain_a", ctrl)
```

Per domain: its own init function. At 20+ controllers: each domain gets
its own module/package that exports its own `init()`.

**S5: Scaling Decision Table**

```
Users       | Handle Map      | Circuit Breaker | Metrics   | Pooling   | Reload
──────────────────────────────────────────────────────────────────────────────────
1 (CLI)     | Ordered map     | YAGNI           | YAGNI     | YAGNI     | YAGNI
5 (Server)  | Ordered map     | Recommended     | Optional  | YAGNI     | Optional
50 (Multi)  | COW at reload   | Essential       | Essential | Optional  | Recommended
100+ (Heavy)| COW + Lock      | Essential       | Essential | Recommended| Essential
```

COW = Copy-on-Write. "Optional" = "makes sense if there's pain."
"Recommended" = "should be implemented." "Essential" = "without this,
the system breaks under load."

**S6: Vertical vs. Horizontal Scaling Boundary**

This pattern is primarily for **vertical scaling within a single
process** — more handles, more controllers, more users on the same
process. It is NOT a pattern for **horizontal scaling** (multiple
processes/servers). For distributed systems, you need service discovery,
load balancing, remote handles — that is a completely different topic
and should not be mixed into this skill.

"Skalierung über Prozess-Grenzen → Service Registry + Discovery (separate
architecture, not Controller+Handle)."

### Scaling Quick Reference

| Pain | Solution | Reference |
|------|----------|-----------|
| Startup too slow | Lazy init (S1) | Principle 6 + S1 |
| Memory grows at startup | Lazy init (S1) | S1 |
| Composition root unwieldy | Modularization (S4) | S4 |
| Handle crashes under load | Circuit breaker (O4) | O4 + S5 |
| Bottleneck not findable | Metrics (O8) | O8 + S5 |
| Reload blocks users | Copy-on-Write (S2) | S2 |
| DB connections exhausted | Pooling (S3) | S3 |
| Multiple processes needed | Service discovery (S6) | Not this skill |

## Auto-Registration (Optional)

When handle count grows (10+ in one domain), explicit registration
becomes repetitive. Auto-registration via decorator/annotation is an
option — with clear trade-offs:

```python
@register_handle("primary", controller="domain_a")
class PrimaryDomainAHandle: ...
```

- **Advantage:** New handle class → just write the class, no
  `register()` call to forget.
- **Disadvantage:** "Global registration makes dependency relationships
  less explicit in large applications. It makes it difficult to locate
  a component's implementation." (Vue.js community consensus)
- **Recommendation:** Under 10 handles: explicit. 10+ handles in the
  same domain: consider auto-registration. Under 10: YAGNI.
- **Caveat:** Decorator/annotation-based registration triggers at import
  time (side effects). Tests need `registry.clear()` in setup hooks.

## Thread Safety

The skill is silent on thread safety by default because the core pattern
is single-threaded (CLI, desktop, main thread in plugin systems).

When multi-threaded:
- **Concurrent map:** Use your language's thread-safe map implementation.
  Note that some concurrent maps lose insertion order — if fallback chains
  are needed, maintain a separate ordered list alongside.
- **Locks:** Protect `register()`/`unregister()`/`get_handle()` with a
  read-write lock or mutex. Even in languages with GIL or equivalent,
  compound operations (check-then-set) are not atomic.
- **Copy-on-Write:** Build a new map on `register()`, replace the old
  reference. Read operations need no lock. Good for "frequent reads,
  rare writes" (which is the case for handles).
- **When relevant:** Only for multi-threaded (server, web server,
  event-driven). Single-thread (CLI, plugin main thread): YAGNI.
- **Circuit breaker and metrics:** If implemented, these are written at
  runtime and MUST be thread-safe regardless of the handle map.

## Multi-Instance Session Routing

When a controller-based web server serves multiple user instances on a
single port (multi-tenant), the web server layer needs a
session-to-instance mapping. The controllers themselves are
instance-neutral — handles accept `db_path` (or equivalent) as a kwarg.
Only the web server resolves the correct path per session.

See `references/multi-instance-session-routing.md` for the full pattern
with login/logout, session-aware path resolution, thread safety, and
fallback for single-user mode.

## Verification Phase (Mandatory for Migrations)

When migrating an existing codebase to Controller+Handle, the plan MUST
include a final phase that verifies ALL untouched modules still work.
Skipping this leads to discovering breakage late.

See `references/verification-phase-pattern.md` for the complete checklist:
import integrity, API stability, CLI smoke, REST endpoints, existing
test suite, real smoke test, AST analysis, final gate. Also includes
patterns for pre-existing bugs (skip, don't fix) and test contamination
through fake modules.

## Subagent Parallelization for Migrations

Controller+Handle migrations with many independent domains can be
parallelized efficiently:

- One subagent per domain pair (e.g., Phase 1+2 = Domain A + Domain B,
  Phase 3 = Domain C)
- Each subagent creates handle implementations + tests + fills its stub
  in the composition root
- **Pitfall:** The composition root file is edited by multiple subagents
  → merge conflicts. Solution: each subagent uses `patch` (find-replace)
  to fill only its own stub, never rewrites the whole file.
- **Pitfall:** Fake modules injected into the module system (for mock
  tests) contaminate subsequent tests that import real modules. Solution:
  dedicated cleanup functions or isolated test files.

## References

- `references/lifecycle-circuit-breaker.md` — Implementation notes for O1
  (lifecycle hooks) and O4 (circuit breaker), including test patterns and
  parallel-edit race condition pitfalls.
- `references/multi-instance-session-routing.md` — Session-to-instance
  mapping for multi-tenant servers with thread safety.
- `references/verification-phase-pattern.md` — Verification checklist for
  migrations, including pre-existing bugs and test contamination.

## Language-Specific Templates

The 10 core principles and 8 enhancements are language-agnostic concepts.
Copy-paste templates are provided for common languages:

- `templates/java_template.java` — Controller, Handle, ConcreteHandle, Composition Root
- `templates/python_template.py` — Controller Base, Protocol, Domain Controller, Registry
- `templates/typescript_template.ts` — same structure for frontend/Tauri
- `templates/java_optimizations.java` — Lifecycle, EventBus, CircuitBreaker, Reloadable, Metrics
- `templates/python_optimizations.py` — same optimizations, Python-idiomatic

Templates for additional languages (Rust, Go, Kotlin, etc.) follow the
same principles. Translate the concepts, not the syntax:
- Use your language's interface/trait/protocol equivalent for handles.
- Use your language's insertion-ordered map (or maintain order separately).
- Use your language's concurrency primitives for thread safety.
- New languages = new template file, no SKILL.md change needed.