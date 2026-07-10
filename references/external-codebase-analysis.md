# Analyzing External Codebases for Controller-Handle Candidates

Proven workflow for analyzing an external codebase to determine whether
Controller-Handle refactoring is justified.

## Step-by-Step

1. **Shallow clone** the repo to /tmp — no need for full history
   ```
   git clone --depth 1 https://github.com/org/repo.git /tmp/repo
   ```

2. **Count classes per file** — files with 5+ classes are candidates
   ```python
   import os
   for root, dirs, files in os.walk(base):
       for f in files:
           if f.endswith('.py'):
               content = open(os.path.join(root, f)).read()
               if content.count('class ') >= 5:
                   print(f"{f}: {content.count('class ')} classes, {len(content)} chars")
   ```

3. **Search for dispatch patterns** — these signal if/elif dispatch trees:
   ```python
   import re
   # if/elif with string comparisons = type dispatch
   if_count = len(re.findall(r'\bif\b.*==.*[\'"]', content))
   elif_count = len(re.findall(r'\belif\b.*==.*[\'"]', content))
   isinstance_count = len(re.findall(r'isinstance\(', content))
   type_count = len(re.findall(r'type\([a-z_]+\)\s*==', content))
   ```

4. **Check runtime extensibility** — are new types added by:
   - Code modification (adding another if/elif branch) → Controller candidate
   - Registration (factory, plugin system) → already has a form of registry

5. **Apply Rule of Three** — count genuinely different, code-extensible
   implementations per domain:
   - <3: recommend simpler alternative (Enum+Switch, interface+factory)
   - 3-7: Controller+Handle justified
   - 7+: Controller+Handle with optimization layers

6. **Distinguish migration code from dispatch code**:
   - if/elif chains that convert old wallet formats → NOT dispatch, leave alone
   - if/elif chains that select between active implementations → dispatch candidate

7. **Distinguish data structures from providers**:
   - 31 SQLite table/row classes with no dispatch logic → NOT handle candidates
   - 7 exchange rate classes selected at runtime → handle candidates

## What to Report

For each candidate domain, report:
- File name and size
- Number of classes/ implementations
- Type of dispatch (if/elif, isinstance, type())
- Runtime extensible? (yes/no)
- Controller+Handle justified? (yes/no, with reasoning)

For each rejected domain, state WHY (static, migration code, too few, data structures).

## Example Results (reference)

| Domain | Impls | Dispatch Type | Runtime Extensible | Verdict |
|--------|-------|--------------|---------------------|---------|
| Keystore | 5 | if/elif (2 chains) | Yes | JUSTIFIED |
| Account/Wallet | 6+ | isinstance (11) | Yes | JUSTIFIED |
| Exchange Rates | 7 | introspection | Yes | PARTIAL (works, not clean) |
| Networks | 4 (static) | minimal | No | REJECT: Enum+Switch |
| Storage type | if/elif strings | No | No | REJECT: migration code |
| Extensions | 2 | none | No | REJECT: too few |
| DB Tables | 31 | none | No | REJECT: data structures |