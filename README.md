# Controller-Handle-Interface Architecture

A language-agnostic architectural pattern for building extensible systems
that scale gracefully. One controller per domain, handles registered
dynamically, zero if/else dispatch trees.

## What This Is

A proven architecture pattern — not a framework, not a library. You copy
the templates into your project and adapt them. No dependencies, no
runtime, no build step.

**Battle-tested in two production projects:**
- A multi-user knowledge-base server (Python, 6 controllers, 14 handles, 355 tests)
- A Minecraft game plugin (Java, 8 controllers, 8MB JAR)

## The Problem It Solves

Most codebases grow into one of these:

- **God classes** — one manager knows everything, every new feature adds
  another `if/else` branch
- **Duplicated managers** — five variations of the same pattern, each
  slightly different, none testable in isolation
- **Hard-coded dispatch** — `if (mode == X)` scattered across listeners,
  impossible to add a new mode without touching every file

This pattern replaces all of that with: **one controller per domain,
handles registered dynamically, zero if/else dispatch.**

## The Pattern in 30 Seconds

```
Composition Root  →  instantiates controllers, registers handles
       ↓
   Controller     →  Map<String, Handle> — one per domain
       ↓
   Handle         →  Interface/Protocol — the contract
       ↓
ConcreteHandle    →  wraps an existing service or stands alone
```

New feature? `controller.register(new Handle())`. No existing code
changes. Open/Closed Principle enforced by structure, not discipline.

## When to Use It

- New project with 3+ distinct functional domains
- Refactoring a grown codebase with if/else dispatch trees or
  duplicated manager classes
- Features must be extensible at runtime without code changes

## When NOT to Use It

- 1-2 domains → a simple interface suffices
- Static domains that never change → an enum + switch suffices
- All domains are similar (5 listeners doing the same thing) → a single
  dispatcher suffices

**Rule of Three:** 3+ domains, genuinely different, AND
runtime-extensible → THEN use this pattern. Otherwise it's
over-engineering.

## What's Included

```
controller-handle-architecture/
├── SKILL.md                          ← Full pattern documentation
├── README.md                         ← This file
├── templates/
│   ├── java_template.java            ← Controller, Handle, ConcreteHandle, Composition Root
│   ├── python_template.py            ← Same structure, Python-idiomatic
│   ├── typescript_template.ts        ← Same structure for Tauri/frontend
│   ├── java_optimizations.java       ← Lifecycle, EventBus, CircuitBreaker, Reloadable, Metrics
│   └── python_optimizations.py       ← Same optimizations, Python-idiomatic
└── references/
    ├── lifecycle-circuit-breaker.md          ← O1 + O4 implementation notes
    ├── multi-instance-session-routing.md     ← Multi-tenant session mapping
    └── verification-phase-pattern.md         ← Migration verification checklist
```

## Core Principles (1-10)

1. One controller per domain
2. Handle as interface/protocol — every handle implements `get_id()`
3. Dynamic registration — no if/else, no modifying existing classes
4. Insertion-ordered map — deterministic fallback chains
5. Wrap existing services, don't delete them
6. Lazy imports/initialization — heavy deps load on first use
7. Fail-fast on unknown handles — throw, never return null
8. Decouple listeners — query the controller, not concrete implementations
9. Config from YAML/JSON — modes and rules externalized
10. Idempotent initialization — safe to call multiple times

## Progressive Enhancements (O1-O8)

The core 10 principles cover 80% of projects. Enhancements are
**independent and additive** — add only when you have the specific
problem they solve:

| # | Enhancement | Solves |
|---|-------------|--------|
| O1 | Handle Lifecycle | Resources needing setup/cleanup |
| O2 | Event Bus | Inter-controller coupling |
| O3 | Capability Resolution | Multiple handles satisfying the same request |
| O4 | Circuit Breaker | One handle crash shouldn't block all users |
| O5 | Constructor Injection | Composite handle dependencies |
| O6 | Unified Reload | Config changes without restart |
| O7 | Typed Handle IDs | Prevent string-typo bugs |
| O8 | Metrics / Observability | Admin diagnostics for multi-user servers |

## Scaling (S1-S6)

Three axes with different failure modes:

- **Horizontal** (more handles): lazy init, auto-registration
- **Vertical** (more controllers): modular composition root
- **Functional** (more users): copy-on-write, thread safety, pooling

See the Scaling Decision Table in SKILL.md for concrete recommendations
by user count.

## Languages

Templates included for **Java**, **Python**, and **TypeScript**. The
core principles are language-agnostic — translate the concepts to any
language:

- **Rust:** `trait` for handles, `HashMap` with `entry()` API
- **Go:** implicit interface satisfaction, `map[string]Handle`
- **Kotlin:** `interface` for handles, `object` for singleton registry

## Getting Started

1. Read `SKILL.md` — the full pattern with decision matrices,
   anti-patterns, and step-by-step setup guide
2. Pick the template for your language from `templates/`
3. Copy it into your project and adapt domain names
4. Start with the core (Controller + Handle + Registry). Add
   enhancements only when you hit the problem they solve

## Philosophy

**Rule 0: Minimum Viable Architecture.** Start with the minimum. Add
abstraction only when solving a concrete pain point — not "just in case."

YAGNI is not "never add abstraction." It is "only add abstraction when
you are solving a specific problem that requires it."

## License

Use freely. Attribution appreciated but not required.