# Skill-Authoring Lessons (Session 2026-07-09)

Lessons learned from external review of the controller-handle-architecture
skill. These are generalizable principles for any skill that prescribes
architecture patterns or progressive enhancement layers.

## Lesson 1: MVA vs. Skill Size — Practice What You Preach

A skill that preaches YAGNI / Minimum Viable Architecture on 1000+ lines
creates an inherent tension. An agent loading the entire file gets massive
context for simple cases, contradicting the "start small" message.

Fix: Add a "Fast Path" section near the top that tells the agent which
sections are sufficient for simple cases. This is Progressive Disclosure
for the skill itself — core principles first, enhancements only when the
corresponding pain point exists.

Fast Path format:
```
## Fast Path — What You Need for Simple Cases

When the pattern is justified because at least one domain has 3+ genuinely
different implementations, reading the following
sections is sufficient:
- Core Design Principles 1-10
- One language template (not both)
- Bad → Good Transformations
- Anti-Patterns
- Minimum Code Output
- Testing Guidance

Enhancement layers (O1-O8), scaling, and references are progressive
enhancement — load only when the corresponding pain point exists.
```

This does NOT reduce the skill's length. It INSTRUCTS the agent on what
to skip, which is the next best thing when the runtime loads the whole
file regardless.

## Lesson 2: Quantified Triggers for Enhancement Layers

Enhancements labeled "when needed" or "when X becomes a problem" are
vague. Agents cannot evaluate "when needed" from code inspection alone.

Fix: Replace vague triggers with explicit, countable thresholds:
- Instead of "when controllers need to communicate" → "3+ controllers
  reference each other directly"
- Instead of "when handle count grows" → "5+ hardcoded get_handle(id)
  calls OR handles have overlapping capabilities"

Quantified triggers let an agent grep/count in the codebase and make a
concrete yes/no decision. Vague triggers leave the decision to "judgment"
which agents handle poorly.

This applies to any skill with progressive enhancement or optimization
layers: each layer should have a clear, testable activation condition.

## Lesson 3: Every Hard Rule Needs a "When NOT" Clause

Principle 7 ("Fail-Fast on Unknown Handles — always throw, never null")
was the ONLY principle without an exception clause. Every other principle
in the skill had one. The exception is real: plugin systems with optional
extensions where a missing handle is a normal state, not an error.

Fix: For every hard rule in a skill, ask: "Is there a legitimate context
where this rule is wrong?" If yes, write the exception explicitly. Do NOT
assume the reader will infer the exception from context.

Format:
```
**Rule:** Always X. [explanation]

Exception: When [specific context], Y is allowed because [reason].
Example: [concrete example].

Principle: When ALL cases are X → X is default. When SOME cases are Y →
Y is explicitly allowed with [condition]. Never [opposite of X] without
[explicit check].
```

The "Principle" line makes the boundary testable: "ALL mandatory →
fail-fast. SOME optional → has_handle() + fallback."

## Lesson 4: Architecture Testing Must Cover Concurrency

Thread-safety was treated architecturally (Circuit Breaker, Metrics,
Copy-on-Write) but the Testing Guidance section had zero concurrency
tests. Architecture claims without test patterns are unverified claims.

Fix: For any architecture pattern that claims thread-safety, the skill
MUST include or reference concurrency test patterns. The test patterns
should live in templates/ (not the main SKILL.md) to avoid bloating
the core document — a single reference line plus a template file.

This generalizes: any architectural claim in a skill (performance,
safety, idempotency, thread-safety) needs corresponding test patterns
in templates/ or references/.

## Lesson 5: Skill Content Should Live Where It's Loaded On-Demand

The concurrency-testing template is ~200 lines of code. Putting that
in SKILL.md would add ~200 lines to every skill load. Putting it in
templates/concurrency-testing.md means it's only loaded when the agent
calls skill_view(file_path='templates/concurrency-testing.md').

Rule of thumb: if content is conditional (only needed for concurrent
shared-state deployments, only needed for Java, only needed when O4 is implemented), it
belongs in references/ or templates/, not in SKILL.md. SKILL.md gets
a one-line pointer.

## Lesson 6: Multi-Language Sync — Never Blindly Copy References Between Versions

When a skill has multiple versions (e.g., a German working copy and an
English publish copy), each version may have its OWN reference files with
different names, different languages, and different structures. The
publish version had `references/lifecycle-circuit-breaker.md` (EN, 5069
bytes) while the working copy historically used a differently named `o1-o4-implementation.md`
(DE, 6298 bytes) covering the same topic but in a different language and
with project-specific examples.

**Pitfall:** Blindly copying reference files from the working copy into
the publish version creates German files inside an English skill, and
breaks the SKILL.md references section which now points to files with
German content and German filenames.

**Fix:** Before syncing, verify:
1. Each version's references section lists ONLY files that actually exist
   in its own `references/` directory.
2. Each reference file matches the SKILL.md's language.
3. Never assume "same topic = same file" across versions — the publish
   version may have merged, restructured, or translated content
   differently.

**Check command:** `grep -oP 'references/[\w-]+\.md' SKILL.md | sort -u`
must match exactly the files in `references/`. Any mismatch = broken
references or orphaned files.

## Lesson 7: "Good"-Beispiel nutzt "Bad"-deklarierten Pattern

Ein Skill der einen Anti-Pattern als "Bad" deklariert darf denselben
Pattern nirgendwo als "Good" zeigen — es sei denn die Ausnahme ist
explizit als AUSNAHME markiert. LLMs können den Unterschied nicht aus
Kontext ableiten.

Konkretes Beispiel: Service Locator wurde als "Bad" deklariert, aber O5
zeigte Registry-Lookup als "Good". Fix: Constructor Injection als Default,
Registry-Lookup als markierte Ausnahme mit Begründung.

Siehe O5 Abschnitt in `references/core-optimizations.md` für die vollständige Analyse.

## Lesson 8: Sprachneutralität in abstrakten Skills

Wenn ein Skill als "sprachunabhängig" deklariert ist, dürfen die
Prinzipien-Prosa KEINE sprachspezifischen Klassen/Methoden nennen
(`LinkedHashMap`, `ConcurrentHashMap`, `threading.Lock`, `sys.modules`,
`GIL`, `volatile`, `AtomicReference`). Diese gehören in die Templates,
nicht in die Architektur-Prinzipien. Die Prosa sollte sagen "insertion-
ordered map" statt "LinkedHashMap", "thread-safe map" statt
"ConcurrentHashMap". Code-Beispiele als Illustration sind okay, aber die
Prosa muss neutral sein.

## Lesson 9: Hermes Preset Skills bei Reviews

Hermes-seitig ausgelieferte Skills referenzieren oft Sub-Skills die nicht
installiert sind. Das ist BY DESIGN — sie dienen als Roadmap-Blueprint.
Bei Skill-Reviews nicht als 'broken' oder 'critical' flaggen. Nur falsche
Tool-Referenzen (Tools die der Agent aufrufen soll die aber nicht
existieren) sind echte Criticals.

## Lesson 10: Register Pattern — Skill als Router für kleine Kontextfenster

Ein Skill der YAGNI predigt kollidiert mit seinem eigenen Umfang.
Lösung: SKILL.md wird zum Register/Router (~150 Zeilen), Details werden
zu References die nur bei Bedarf geladen werden.

### Register-Design (bewährt 2026-07-10, externe Review validiert)

SKILL.md enthält inline:
1. Trigger + Decision Matrix — Entry-Point
2. Core Digest: 10 Leitplanken als kompakte Sätze — Safety-Guardrails
   die gelten auch ohne geladene Referenz
3. Routing-Tabelle: welche Referenzen für welchen Fall (paketbasiert)
4. Context Management: wann Handoff schreiben, wie resumen
5. Reference-Index: alle Dateien mit 1-Zeiler + "wann laden"

Ausgelagert: core-workflow.md (MANDATORY), migration-workflow.md,
handoff-protocol.md, core-optimizations.md, etc.

### Hybrid-Design (ChatGPT-Review)

NICHT nur Routing (gefährlich). SONDERN Routing + kompakter Core Digest
+ harte Stop-Regeln. 10 Zeilen Digest ist wenig genug für kleinen
Register aber genug für Guardrails ohne geladene Referenz.

### Context-Regel (abgeschwächt)

NICHT "keine weiteren Referenzen laden". SONDERN "Handoff schreiben BEVOR
weitere Referenzen geladen werden. Weiter wenn Schritt klein und
Korrektheit es zulässt."

### Archiv-Pitfall

Archiv-Verzeichnis mit SKILL.md gleichem Frontmatter-Namen → Hermes
erkennt zwei Skills → skill_view weigert sich. Lösung: SKILL.md im
Archiv umbenennen zu SKILL.md.archived.