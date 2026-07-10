# Controller-Handle-Interface Architecture

A language-agnostic architectural pattern for building extensible systems
that scale gracefully. One controller per domain, handles registered
dynamically, zero if/else dispatch trees.

## What This Is

A proven architecture pattern — not a framework, not a library. You copy
the templates into your project and adapt them. No dependencies, no
runtime, no build step.

**Battle-tested in production:**
- A multi-user server system (Python, 8 controllers, 14+ handles, 355+ tests)
- A game plugin (Java, 8 controllers, 18 listeners migrated)
- A wallet modernization (Python, 5 controllers, feature-toggle system, 177 tests)

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

New feature? `controller.register(new Handle())`. No changes to existing
controller or dispatch logic; only the composition root is extended.
Open/Closed Principle enforced by structure, not discipline.

## When to Use It

- At least one domain has 3+ runtime-selectable implementations
  (e.g. 3 search engines, 3 render modes, 3 storage backends)
- Refactoring a grown codebase with if/else dispatch trees or
  duplicated manager classes
- New implementations should be addable without modifying existing
  controller or dispatch logic. The composition root MAY be extended.
  Hot-plugging (runtime registration without code changes) is NOT a
  prerequisite — it requires O6 Reload or dynamic plugin registration.

## When NOT to Use It

- 1-2 implementations in a domain → a simple interface suffices
- Static implementations that never change → an enum + switch suffices
- All implementations are similar (5 listeners doing the same thing) → a
  single dispatcher suffices

**Rule of Three:** 3+ handle implementations per domain, genuinely
different, AND code-extensible (new implementation addable without
modifying existing controller/dispatch logic) → THEN use this pattern.
Not 3+ domains with 1 implementation each. Otherwise it's over-engineering.

## What's Included

```
controller-handle-architecture/
├── SKILL.md                          ← Register/router with core guardrails
├── README.md                         ← This file
├── CONTRIBUTING.md                   ← Skill authoring lessons (for maintainers)
├── templates/
│   ├── java_template.java            ← Controller, Handle, ConcreteHandle, Composition Root
│   ├── python_template.py            ← Same structure, Python-idiomatic
│   ├── typescript_template.ts        ← Same structure for Tauri/frontend
│   ├── java_optimizations.java       ← Lifecycle, EventBus, CircuitBreaker, Reloadable, Metrics (snippets)
│   ├── python_optimizations.py       ← Same optimizations, Python-idiomatic
│   └── concurrency-testing.md        ← Race-condition tests for shared concurrent state
└── references/
    ├── core-workflow.md              ← Principles detail, Bad/Good, anti-patterns, tests
    ├── migration-workflow.md         ← Agent workflow, verification, handoff, subagent parallelization
    ├── core-optimizations.md         ← O1-O8 enhancements + scaling S1-S6 + auto-registration
    ├── composition-root-patterns.md  ← Multi-controller orchestration, test reset, init ordering
    ├── handle-wrapping-patterns.md   ← Factory closures, enum-to-handle mapping, inline classes
    ├── feature-toggle-pattern.md     ← Feature protocol, toggle controller, YAML config
    ├── lifecycle-circuit-breaker.md  ← O1 + O4 implementation notes
    ├── verification-phase-pattern.md ← Migration verification checklist
    ├── multi-instance-session-routing.md ← Multi-tenant session mapping
    └── external-codebase-analysis.md ← Workflow for analyzing external repos
```

## Architecture: Register + Progressive Disclosure

SKILL.md is a **register/router** — a thin file (~140 lines) with core
guardrails inline and a routing table that directs to detailed reference
files. Load only what your case requires.

The skill applies its own principle: Progressive Disclosure.

- **SKILL.md** = Controller (register, route, guardrail)
- **references/** = Handles (detailed execution, loaded on demand)
- **Routing Table** = Dispatch (which references for which situation)
- **Handoff** = Resume state for multi-phase migrations (in migration-workflow.md)

## Core Digest (always active)

1. Rule of Three first — <3 implementations per domain = no pattern
2. One controller per domain, not per feature
3. Handles implement behavior; controllers only register/resolve/orchestrate
4. Composition Root is the sole wiring point — constructor injection, not lookup
5. Wrap existing services, don't delete them
6. Fail loudly on unknown or duplicate handle IDs — no silent null
7. Insertion-ordered map for deterministic fallback chains
8. Tests are part of the output
9. If the pattern is not justified, recommend the simpler design explicitly
10. Context management: write handoff before context runs low

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
- **Functional** (concurrent shared state): copy-on-write, thread safety, pooling

See `references/core-optimizations.md` for the full scaling decision table
(S1-S6) and prioritization by deployment context.

## Languages

Templates included for **Java**, **Python**, and **TypeScript**. The
core principles are language-agnostic — translate the concepts to any
language:

- **Rust:** `trait` for handles, `HashMap` with `entry()` API
- **Go:** implicit interface satisfaction, `map[string]Handle`
- **Kotlin:** `interface` for handles, `object` for singleton registry

## Getting Started

1. Read `SKILL.md` — the register with core guardrails and routing table
2. Load `references/core-workflow.md` — mandatory before generating code
3. Pick the template for your language from `templates/`
4. Copy it into your project and adapt domain names
5. Start with the core (Controller + Handle + Registry). Add
   enhancements only when you hit the problem they solve

## Philosophy

**Rule 0: Minimum Viable Architecture.** Start with the minimum. Add
abstraction only when solving a concrete pain point — not "just in case."

YAGNI is not "never add abstraction." It is "only add abstraction when
you are solving a specific problem that requires it."

## License

Use freely. Attribution appreciated but not required.