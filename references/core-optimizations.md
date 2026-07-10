# Core Optimizations — O1-O8 and Scaling Axes

The core 10 principles (see core-workflow.md) cover the fundamental
architecture. The following 8 enhancements raise the pattern to production
level. They are **independent and additive** — pick and choose based on
concrete pain points. NOT sequential.

Decision rule per enhancement: "Do you have [problem X] right now? →
No → do not implement." (YAGNI)

## O1: Handle Lifecycle Interface

Optional `on_register`/`on_disable` hooks. Cleanup formalized, hot-reloads
become cleaner. Additive and non-breaking.

Controller calls hooks only if `hasattr(handle, method)` is True.
Exceptions in lifecycle methods are caught and logged, not propagated.

See `references/lifecycle-circuit-breaker.md` for implementation and tests.

## O2: Inter-Controller Communication via Event Bus

Trigger: 3+ controllers reference each other directly. Under 3
cross-references: direct access via composition root is acceptable.

EventBus decouples controllers. Controller A emits, Controller B
subscribes. A does not know B exists.

## O3: Capability Resolution Instead of ID Lookup

Trigger: 5+ hardcoded `get_handle(id)` calls OR handles with overlapping
capabilities. Under 5 unambiguous IDs: ID lookup suffices.

Handles declare what they can do, controllers search by capability.
Variant A: criteria match (`matches(**criteria)`).
Variant B: set-intersection match (`matches_types(found_types: set)`).

## O4: Circuit Breaker per Handle

3 failures in 30 seconds → handle skipped for 60 seconds. `get_primary()`
ignores tripped handles automatically. Additive, non-breaking.

See `references/lifecycle-circuit-breaker.md` for implementation and tests.

## O5: Inject Sub-Handle Dependencies via Composition Root

Composite handles should receive sub-handles via constructor injection
from the composition root, not create new instances or look them up.

Exception: if sub-handles are registered dynamically at runtime or
circular load order makes constructor injection impossible, a composite
handle MAY resolve from the controller at call time — this is the Service
Locator anti-pattern applied narrowly and must be documented.

Consistency rule: A skill that declares an anti-pattern as "Bad" must not
show the same pattern as "Good" elsewhere unless explicitly marked as an
exception. O5 originally showed registry lookup as "Good" while the skill
declares Service Locator as "Bad". Fix: Constructor Injection as default,
registry lookup as explicitly marked exception with justification. LLMs
cannot infer the difference from context — it must be stated explicitly.

## O6: Unified Reload

`Reloadable` interface with `reload()`. Registry calls `reload()` on all
controllers that implement it. One command reloads everything.

Critical: lazy imports in `reload()` to avoid circular imports. Creates
new handle instances. For multi-user: copy-on-write (S2).

## O7: Typed Handle IDs

Constants or enums instead of raw strings. Prevents typos. IDE
autocomplete works. Refactoring-safe. Near-zero cost.

## O8: Metrics / Observability

Counter per `handle_id.method_name` key. `call()` wraps method invocations
and tracks calls + errors. `get_metrics()` returns `{"calls": {...},
"errors": {...}}`.

Thread safety (concurrent shared state): counters are compound dict operations
(check-then-set) — NOT atomic even with GIL. Use thread-safe primitives
(Lock in Python, AtomicInteger in Java).

## Enhancement Prioritization

**Single execution context / local app:**

| # | Impact | Effort | Recommendation |
|---|--------|--------|---------------|
| O5 | High | Low | Yes |
| O7 | Medium | Low | Yes |
| O6 | Low | Low | YAGNI |
| O8 | Low | Low | YAGNI |
| O1 | Low | Medium | YAGNI |
| O4 | Low | Medium | YAGNI |
| O3 | Low | Medium | Only when needed |
| O2 | Low | High | Only when needed |

**Concurrent shared-state deployment:**

| # | Impact | Effort | Recommendation |
|---|--------|--------|---------------|
| O5 | High | Low | Yes |
| O7 | High | Low | Yes |
| O6 | High | Low | Yes |
| O8 | High | Low | Yes |
| O1 | High | Medium | Yes |
| O4 | High | Medium | Yes |
| O3 | Medium | Medium | When handle count grows |
| O2 | High | High | When inter-controller coupling appears |

## Scaling Axes

**Horizontal (more handles per controller):** 5 = no problem. 20+ =
startup time → lazy init essential. 100+ = memory → resource pooling.

**Vertical (more controllers/domains):** 3 = one method. 10+ = per domain
`_register_*()`. 20+ = own file. 30+ = sub-registries.

**Functional (concurrent access):** One execution context = YAGNI. Multiple
readers with immutable state = snapshots may suffice. Concurrent mutation =
locks/atomic operations; reload needs Copy-on-Write. High contention or heavy
resources = consider sharding or pooling.

IMPORTANT: Pattern is for vertical scaling (within a process). Horizontal
(multiple processes) → Service Registry + Discovery, different pattern.

**S1:** Lazy init as scaling tool.
**S2:** Copy-on-Write for reload.
**S3:** Resource pooling.
**S4:** Composition root modularization at 10+ controllers.

**S5: Scaling Decision Table**

```
Users         | Handle Map    | Circuit Breaker | Metrics | Pooling | Reload
1 (CLI)       | LinkedHashMap | YAGNI          | YAGNI   | YAGNI   | YAGNI
5 (Server)    | LinkedHashMap | Recommended    | Optional| YAGNI   | Optional
50 (Multi)    | COW on Reload | Essential      | Essential| Optional| Recommended
100+ (Heavy)  | COW + Lock    | Essential      | Essential| Recommended| Essential
```

**S6: Vertical vs. Horizontal Scaling Boundary**

The pattern is for vertical scaling (within a process). Horizontal
(multiple processes/servers) → Service Registry + Discovery, a different
pattern. Do not mix them.

## Auto-Registration (Optional — 10+ Handles per Domain)

Auto-registration (decorator in Python, annotation+scanning in Java) is
an optional extension that conflicts with the YAGNI guiding principle —
only justified at a concrete pain point.

| Handle Count (per Domain) | Recommendation |
|---------------------------|----------------|
| <10                       | Explicit registration — clearer, no side effects |
| 10+                       | Consider auto-registration — but weigh trade-offs |
| 20+                       | Auto-registration + modular init functions (S4) |

Approach: Decorator (`@register_handle("id", controller="x")`) in Python,
annotation + class-path scanning in Java. The decorator-registry is
transferred into real controllers in the composition root.

Trade-offs: Auto-registration makes dependencies less explicit and
complicates testing (side effects at import time). When using
auto-registration, tests must reset the registry (`registry.clear()` in
setUp/tearDown). On import failures, the registry may be left inconsistent.