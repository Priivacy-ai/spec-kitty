---
work_package_id: WP01
title: Auto-Fix Ruff Violations
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: feat/079-ci-hardening-and-lint-cleanup
merge_target_branch: feat/079-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/079-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/079-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "opencode"
shell_pid: "40632"
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: src/charter/
execution_mode: code_change
owned_files:
- src/charter/catalog.py
- src/charter/resolver.py
- src/doctrine/missions/glossary_hook.py
- src/kernel/_safe_re.py
tags: []
---

# WP01 — Auto-Fix Ruff Violations

## Objective

Fix four isolated ruff violations across four independent files using ruff's own `--fix` mode
(per C-004). Each file has exactly one violation. No file overlap with any other WP.

After this WP, `ruff check src/charter/catalog.py src/charter/resolver.py src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py` must exit 0.

## Context

**Why this WP exists:** The ruff lint gate is currently advisory because pre-existing violations
cause CI to always report failures. FR-001 mandates that all violations on `main` are resolved
so the gate becomes authoritative. WP01 handles the four violations that are in non-acceptance
files with no cross-file dependencies.

**Doctrine:** DIRECTIVE_030 (Test and Typecheck Quality Gate) — ruff must pass before handoff.
C-004 — auto-fixable violations must be fixed using ruff's own fix mode, not manual edits.

**Relevant spec refs:** FR-001

**This WP is part of Batch 1 (parallel).** It can be implemented simultaneously with WP02–WP05.
No other WP touches these four files.

## Subtask Guidance

### T001 — Fix ARG001: unused `doctrine_root` arg in `charter/catalog.py:245`

**File:** `src/charter/catalog.py`, around line 245

**Violation:** ARG001 — a function parameter `doctrine_root` is accepted but never used inside
the function body. Ruff flags this to prevent silent parameter drift.

**Fix approach:**
```bash
ruff check --fix --select ARG001 src/charter/catalog.py
```

If ruff's auto-fix removes the parameter, verify the call sites still compile:
```bash
ruff check src/charter/catalog.py
mypy src/charter/catalog.py
```

If ruff cannot auto-fix (ARG001 is sometimes not auto-fixable), the manual fix is:
- If `doctrine_root` is genuinely unused: add a leading underscore (`_doctrine_root`) OR
  remove the parameter entirely. Check call sites first — if callers pass this argument,
  add `_` prefix; if no callers pass it, remove it.
- Do NOT simply suppress with `# noqa:` — that would re-introduce a violation.

**Validation:** `ruff check src/charter/catalog.py` exits 0 with no ARG001 errors.

---

### T002 — Fix SIM108: if/else → ternary in `charter/resolver.py:120`

**File:** `src/charter/resolver.py`, around line 120

**Violation:** SIM108 — an `if/else` block that assigns a single value can be collapsed into
a ternary expression for clarity.

**Fix approach:**
```bash
ruff check --fix --select SIM108 src/charter/resolver.py
```

SIM108 is auto-fixable. Ruff will rewrite the construct. Review the diff to confirm the
ternary is readable — if the condition is long (>80 chars), consider a manual split:
```python
# Acceptable if ternary fits on one line:
result = value_if_true if condition else value_if_false
```

**Validation:**
```bash
ruff check src/charter/resolver.py  # exits 0
mypy src/charter/resolver.py         # exits 0
```
Run the charter test suite: `pytest tests/charter/ -m fast -q`

---

### T003 — Fix B009: `getattr` with constant → direct attr in `glossary_hook.py:134`

**File:** `src/doctrine/missions/glossary_hook.py`, around line 134

**Violation:** B009 — `getattr(obj, "constant_string")` is equivalent to `obj.constant_string`
and should be written as a direct attribute access. The `getattr` form is only needed when the
attribute name is dynamic (a variable).

**Fix approach:**
```bash
ruff check --fix --select B009 src/doctrine/missions/glossary_hook.py
```

B009 is auto-fixable. The rewrite is: `getattr(module, "name")` → `module.name`.

**Edge case:** If the original code uses `getattr` with a default fallback
(`getattr(module, "name", None)`), that is a B009 non-fix scenario — the default makes it
semantically different from direct access. Check whether the actual usage has a default;
if so, leave it and suppress with an inline comment explaining why.

**Validation:**
```bash
ruff check src/doctrine/missions/glossary_hook.py  # exits 0
mypy src/doctrine/missions/glossary_hook.py         # exits 0
```

---

### T004 — Fix SIM105: try/except/pass → `contextlib.suppress` in `_safe_re.py:185`

**File:** `src/kernel/_safe_re.py`, around line 185

**Violation:** SIM105 — a `try/except SomeException: pass` block (which silently swallows an
exception) should be replaced with `contextlib.suppress(SomeException)` for clarity.

**Fix approach:**
```bash
ruff check --fix --select SIM105 src/kernel/_safe_re.py
```

SIM105 is auto-fixable. The rewrite is:
```python
# Before:
try:
    some_operation()
except SomeException:
    pass

# After:
import contextlib
with contextlib.suppress(SomeException):
    some_operation()
```

Ruff will add the `contextlib` import if it is not already present. Confirm the import is
added to the correct import block (after stdlib imports, not mixed into third-party).

**Validation:**
```bash
ruff check src/kernel/_safe_re.py  # exits 0
mypy src/kernel/_safe_re.py         # exits 0
```
Run the kernel tests: `pytest tests/kernel/ -m fast -q`

---

### T005 — Verify all WP01 files pass ruff check and mypy; run affected tests

**Final verification gate** (DIRECTIVE_030 compliance):

```bash
# 1. All four files clean
ruff check src/charter/catalog.py src/charter/resolver.py \
           src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py

# 2. Mypy passes for each file
mypy src/charter/catalog.py src/charter/resolver.py \
     src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py

# 3. Affected test suites pass
pytest tests/charter/ tests/kernel/ -m fast -q
```

If any command fails:
- `ruff check` failure: re-examine the fix applied; check if ruff introduced a new issue
- `mypy` failure: the auto-fix may have changed a type — review the diff and fix manually
- Test failure: inspect the diff — only structural changes (parameter removal) can cause test
  failures; data-flow changes by ruff should not affect test outcomes

**Commit the changes** to the feature branch once all gates pass.

## Definition of Done

- [ ] `ruff check src/charter/catalog.py src/charter/resolver.py src/doctrine/missions/glossary_hook.py src/kernel/_safe_re.py` exits 0
- [ ] `mypy` exits 0 for all four files
- [ ] Affected test suites pass (`tests/charter/`, `tests/kernel/`)
- [ ] No new ruff or mypy violations introduced in any of the four files
- [ ] Changes committed to `feat/079-ci-hardening-and-lint-cleanup`

## Risks

- **ARG001 not auto-fixable:** If ruff cannot auto-fix ARG001, determine whether to prefix
  the parameter with `_` or remove it. Removing it requires checking call sites first.
- **SIM105 import injection:** Ruff adds `import contextlib` — verify it lands in the correct
  import group (stdlib, not third-party).
- **mypy regression from ternary (T002):** Ternary rewrites are type-preserving, but confirm
  with `mypy` after the fix.

## Reviewer Guidance

Review the diff for each file independently. Each change is one lint rule. The diff should be
minimal: 1–5 lines per file. Any change larger than that warrants investigation.

## Activity Log

- 2026-04-09T14:38:47Z – codex:gpt-5:python-implementer:implementer – shell_pid=43579 – Started implementation via action command
- 2026-04-09T14:42:44Z – codex:gpt-5:python-implementer:implementer – shell_pid=43579 – Moved to planned
- 2026-04-09T14:44:36Z – codex:gpt-5:python-implementer:implementer – shell_pid=43579 – Started implementation via action command
- 2026-04-09T14:47:34Z – codex:gpt-5:python-implementer:implementer – shell_pid=43579 – Blocked: WP01 fixes committed in 1a211d566; ruff and fast charter/kernel tests pass, but mypy still fails in external file src/doctrine/missions/repository.py when checking src/doctrine/missions/glossary_hook.py.
- 2026-04-09T14:53:23Z – codex:gpt-5:python-implementer:implementer – shell_pid=43579 – Ready for review: fixed targeted Ruff violations and strict-typing spillover needed for scoped mypy pass; forced past unrelated WP02 task artifact
- 2026-04-09T14:57:45Z – opencode – shell_pid=40632 – Started review via action command
- 2026-04-09T15:01:19Z – opencode – shell_pid=40632 – Moved to planned
- 2026-04-09T15:03:06Z – opencode – shell_pid=40632 – Started implementation via action command
