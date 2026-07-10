---
name: controller-handle-architecture
category: software-development
description: |
  Use when refactoring or generating code with multiple runtime-selectable
  providers, modes, engines, backends, handlers, listeners, commands, or
  feature implementations. Especially useful when code currently contains
  if/else dispatch trees, god managers, duplicated managers, hard-coded
  provider selection, or plugin-like extensibility requirements. Do not use
  for 1-2 static implementations.
---

# Controller-Handle-Interface Architecture (Register)

This skill is a register/router. It contains core guardrails inline and
directs to detailed execution in reference files. Load only the references
your case requires — not all at once.

## When to Apply This Skill

- New project or refactoring where at least one domain has 3+ runtime-
  selectable implementations (e.g. 3 search engines, 3 render modes,
  3 storage backends). NOT: 3+ domains with 1 implementation each.
- Grown codebase with if/else dispatch trees, duplicated manager classes,
  or hard-to-test logic
- Project must scale: new features without modifying existing classes
- Listeners, event handlers, or commands should be decoupled from
  business logic

## When NOT to Apply — Decision Matrix

Applying the pattern to simple projects is over-engineering.
Rule of Three: 3+ handle implementations per domain, not 3+ domains.

```
Question                                        Answer   Recommendation
──────────────────────────────────────────────────────────────────────────
Does at least one domain have 3+ runtime-       No       No pattern needed
selectable implementations?                     Yes      continue

Are the implementations genuinely different?    No       A dispatcher suffices
                                                Yes      continue

Must new implementations be addable without             No       Enum + switch suffices
modifying existing controller or dispatch logic?        Yes      continue

Do you need more than ID lookup                          No       Strategy pattern suffices
(fallback, capabilities, etc.)?                          Yes      Controller+Handle

Can shared controller state be accessed         No       Core-10 suffices
concurrently (threads/tasks/workers/requests)?   Yes      Core-10 + Thread-Safety
```

| Situation | Use Instead |
|-----------|-------------|
| 1 implementation | Direct service class, no abstraction |
| 2 static implementations | Interface + factory method |
| Fixed set, never changes | Enum + switch/map |
| All similar handlers (5 listeners) | Single dispatcher |
| Config choice (dark mode, locale) | Config file or boolean, not a handle |

When in doubt, start simpler. Refactor toward Controller+Handle when the
third implementation arrives.

## Core Digest — always active

These 10 guardrails apply ALWAYS, even without a loaded reference:

1. Rule of Three first — fewer than 3 genuinely different code-extensible
   implementations per domain = no pattern.
2. One controller per domain, not per feature.
3. Handles implement behavior; controllers only register/resolve/orchestrate.
4. Composition Root is the sole wiring point — handles receive deps via
   constructor, not via lookup.
5. Wrap existing services, don't delete them.
6. Fail loudly on unknown or duplicate handle IDs — no silent null.
7. Insertion-ordered map for deterministic fallback chains.
8. Tests are part of the output — registration, lookup, ordering, unknown,
   reset, idempotent init.
9. If the pattern is not justified, recommend the simpler design explicitly.
10. Context management: write handoff before context runs low, resume from
    handoff in next session.

For detailed execution of these principles (with code examples, Bad/Good
transformations, anti-patterns, testing guidance):
Load `references/core-workflow.md` BEFORE generating code. MANDATORY.

## Routing Table

Load the references your situation requires. Not all at once.

| Situation | Load | Skip |
|-----------|------|------|
| New small implementation (1-3 qualifying domains) | core-workflow + 1 template | everything else |
| Migrating grown codebase | core-workflow + migration-workflow + handle-wrapping-patterns | O1-O8, scaling |
| 3+ controllers in project | + composition-root-patterns | — |
| Concurrent shared state (threads/tasks/workers/request handlers) | + core-optimizations + concurrency-testing template | — |
| Feature toggle system | + feature-toggle-pattern | — |
| Multi-phase migration (context full) | migration-workflow (handoff section) | — |

Templates (choose your language):
- `templates/python_template.py` — Controller, Protocol, Registry, init
- `templates/java_template.java` — Controller, Handle, Composition Root
- `templates/typescript_template.ts` — Tauri/frontend
- `templates/python_optimizations.py` — O1-O8 Python-idiomatic
- `templates/java_optimizations.java` — O1-O8 Java
- `templates/concurrency-testing.md` — Race-condition tests for shared concurrent state

## Context Management

For multi-phase migrations, the context window of a session can fill up.

Rule: When context is at <20% free window, write a handoff BEFORE loading
more references. Continue only if the next step is small and correctness
does not require more context. If a reference is needed to produce correct
code, load it — but write the handoff first.

Handoff template and resume workflow: see `references/migration-workflow.md`
section "Multi-Phase Migration Handoff".

## Feature-Toggle Pattern

Controller-Handle applied at the feature module level. Each feature
independently switchable. See `references/feature-toggle-pattern.md`.

## Reference Index

| File | Content | When to load |
|------|---------|--------------|
| core-workflow.md | Principles detail, Bad/Good, anti-patterns, tests, min output, runtime terminology | ALWAYS before code generation |
| migration-workflow.md | Agent workflow, verification phase, subagent parallelization, multi-phase handoff | When migrating a grown codebase |
| core-optimizations.md | O1-O8 + scaling axes S1-S6 + auto-registration + prioritization tables | When multi-user/server or optimization needed |
| composition-root-patterns.md | Multi-controller orchestration, test reset, init ordering | When 3+ controllers |
| handle-wrapping-patterns.md | Factory closures, enum-to-handle mapping, inline classes | When migrating |
| feature-toggle-pattern.md | Feature protocol, toggle controller, YAML config | When building feature toggles |
| lifecycle-circuit-breaker.md | O1/O4 implementation, test patterns, race condition pitfalls | When implementing O1 or O4 |
| verification-phase-pattern.md | Verification checklist for migrations | At migration completion |
| external-codebase-analysis.md | Workflow for external repo analysis | When analyzing a foreign codebase |
| multi-instance-session-routing.md | Multi-tenant session mapping | When building multi-instance server |