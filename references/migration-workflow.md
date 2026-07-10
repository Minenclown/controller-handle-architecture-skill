# Migration Workflow — Migrating a Grown Codebase to Controller+Handle

Load this file when migrating an existing project with if/else dispatch
trees, duplicated manager classes, or hard-coded provider selection. For
greenfield projects: not needed, core-workflow.md suffices.

## Agent Workflow (Migration)

1. **Inspect existing code** — Read the codebase before generating
   abstractions. Identify what exists: services, managers, dispatch logic,
   config structures. For external repos: shallow clone, then class-count
   + dispatch-pattern scan. See `references/external-codebase-analysis.md`.

2. **Identify candidate domains** — List functional areas with 3+
   runtime-selectable implementations or modes. If none: stop.

3. **Apply the Rule of Three** — Count genuinely different, runtime-
   extensible implementations per domain. Under 3: use simpler design.

4. **If pattern not justified, say so** — Explicitly state why a simpler
   design suffices. Do not implement "just in case."

5. **For each justified domain, generate:**
   - Handle interface/protocol
   - Controller (registry + convenience methods)
   - Concrete handles (wrapping existing services)
   - Composition root (idempotent init)

6. **Preserve existing services** — Wrap, don't delete.

7. **Wire listeners to controllers** — Replace `if (mode == X)` with
   `controller.is_allowed(...)`.

8. **Write tests** — See core-workflow.md Minimum Code Output.

9. **Verification phase** — MUST be planned as final phase. See below.

## Handle Wrapping for Migrations

Three proven patterns for wrapping existing code:

1. Factory-Handle Closure — 5+ similar classes. See
   `references/handle-wrapping-patterns.md` Pattern 1.
2. Enum-to-Handle Mapping — Bridge from existing Enum+Switch. See
   `references/handle-wrapping-patterns.md` Pattern 2.
3. Inline Handle Classes — Under 5 handles. See
   `references/handle-wrapping-patterns.md` Pattern 3.

## Verification Phase (Mandatory for Migrations)

When migrating an existing codebase, the plan MUST include a final phase
that verifies ALL untouched modules still work. Skipping this leads to
discovering breakage late.

See `references/verification-phase-pattern.md` for the complete checklist:
import integrity, API stability, CLI smoke, REST endpoints, existing test
suite, real smoke test, AST analysis, final gate. Also includes patterns
for pre-existing bugs (skip, don't fix) and test contamination.

## Subagent Parallelization for Migrations

Controller+Handle migrations with many independent domains can be
parallelized efficiently via `delegate_task`:

- One subagent per domain pair
- Each creates handle implementations + tests + fills its stub in
  composition root
- Pitfall: composition root file edited by multiple subagents → merge
  conflicts. Solution: each uses `patch` to fill only its own stub.
- Pitfall: fake modules contaminate subsequent tests. Solution: cleanup
  functions or isolated test files.

## Multi-Instance Session Routing

When a controller-based web server serves multiple user instances on a
single port (multi-tenant), the web server layer needs session-to-instance
mapping. Controllers are instance-neutral — handles accept instance
context as kwargs.

See `references/multi-instance-session-routing.md` for the full pattern.

## Multi-Phase Migration Handoff

When a migration fills the context window of a session, the current state
must be written as a handoff file. The next session loads the skill register
+ the handoff and knows where the migration stands.

### When to Write a Handoff

- Context at <20% free window: write handoff, recommend new session.
- Before loading another reference: update handoff.
- At the end of each domain phase: update handoff.
- When the user takes a break or ends the session.

RULE: Not "do not load more references", but "write handoff BEFORE loading
more references". If a reference is needed to produce correct code, load it
— but write the handoff first.

### Handoff File Template

File: `<project>-info/HANDOFF.md`

```markdown
# Controller+Handle Migration Handoff — <Project>

> Date: <YYYY-MM-DD>
> Skill version: controller-handle-architecture v2 (Register)

## Identified Domains
- [ ] Domain A — <name> — <status: pending/in_progress/done>

## Accepted Domains (pattern justified)
- Domain A: <how many implementations, why justified>

## Rejected Domains (pattern not justified)
- Domain X: <reason: only 2 implementations, static, etc.>

## Controllers Created
| Controller | Domain | Handles | File |

## Handles Created
| Handle ID | Controller | Wraps | File |

## Composition Root
- File: <path> | Init function: <name> | Singletons: <how to reset>

## Existing Services (wrapped, not deleted)
- <service> → wrapped by <handle-id>

## Tests
| Test file | Tests | Status |

## Selected Optimizations
- [ ] O1/O4/O6/O8/None — <reason>

## Next Step
<What to do next? Which domain is missing? Which reference to load?>

## Known Risks
- <risk 1>

## References Loaded in This Session
- <files>
```

### Resume Workflow

1. New session starts.
2. Load skill register (SKILL.md).
3. Read handoff file.
4. Based on handoff: load only references needed for the next step.
5. Continue working.
6. At end: update handoff.