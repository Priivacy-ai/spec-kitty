---
work_package_id: WP04
title: 'Remove Stale type: ignore Comments'
dependencies: []
requirement_refs:
- FR-002
planning_base_branch: feat/080-ci-hardening-and-lint-cleanup
merge_target_branch: feat/080-ci-hardening-and-lint-cleanup
branch_strategy: Planning artifacts for this feature were generated on feat/080-ci-hardening-and-lint-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/080-ci-hardening-and-lint-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
history:
- date: '2026-04-09'
  action: created
  actor: claude-sonnet-4-6
authoritative_surface: src/specify_cli/post_merge/
execution_mode: code_change
owned_files:
- src/specify_cli/post_merge/stale_assertions.py
- src/specify_cli/merge/config.py
- src/specify_cli/migration/rebuild_state.py
- src/specify_cli/migration/backfill_identity.py
- src/specify_cli/policy/audit.py
tags: []
---

# WP04 — Remove Stale `# type: ignore` Comments

## Objective

Remove 8 stale `# type: ignore` suppressions across 5 files. Two of the removals also require
fixing the underlying violation that the ignore was (incorrectly) masking. After this WP, mypy
reports zero `unused-ignore` errors for all 5 files.

## Context

**Why this WP exists:** Over time, some `# type: ignore` comments became stale — the
underlying type error was fixed elsewhere, but the suppression comment remained. Mypy now
reports `[unused-ignore]` for each one, adding noise that masks genuine type errors.

**Constraint (C-005):** Each removal must be verified: remove the comment, run mypy on the
file, and confirm no error reappears. If an error reappears, the original suppression was
still valid — restore it and document the remaining error in a comment.

**File ownership note:** `backfill_identity.py` appears in both WP04 and WP05 in the plan
documentation, but this is consolidated here: WP04 owns `backfill_identity.py` for the
`unused-ignore` removal at line 36 plus the `no-any-return` fix. WP05 does NOT touch this
file.

**Doctrine:** DIRECTIVE_030 (type quality gate).

**This WP is part of Batch 1 (parallel).** T014–T018 each touch a different file; safe to
apply all simultaneously.

## Subtask Guidance

### T014 — Remove 4 stale ignores from `post_merge/stale_assertions.py` (lines 317, 319, 322, 324)

**File:** `src/specify_cli/post_merge/stale_assertions.py`

Read lines 310–330 to understand the context. There are 4 consecutive `# type: ignore`
comments. These typically cluster around AST node processing where mypy's type narrowing
was once insufficient but now works correctly.

**Process:**
1. Remove all 4 `# type: ignore` comments (keep the code lines, just remove the comment suffix)
2. Run: `mypy src/specify_cli/post_merge/stale_assertions.py`
3. If no errors → stale confirms, proceed
4. If errors reappear on any of the 4 lines → restore that specific comment and add:
   `# type: ignore[<error_code>]  # TODO: genuine error, tracked in mission 079`

**Validation:**
```bash
mypy src/specify_cli/post_merge/stale_assertions.py
```
Zero `unused-ignore` errors on lines 317, 319, 322, 324.

---

### T015 — Remove stale ignore from `merge/config.py:57`

**File:** `src/specify_cli/merge/config.py`

Read around line 57. There is a single `# type: ignore` on a config attribute assignment.
This likely became stale after a dataclass or TypedDict update that made the type correct.

**Process:** Remove the comment suffix from line 57. Run mypy. If clean, done.

```bash
mypy src/specify_cli/merge/config.py
```

---

### T016 — Remove stale ignore from `migration/rebuild_state.py:38`

**File:** `src/specify_cli/migration/rebuild_state.py`

Read around line 38. Single stale `# type: ignore`.

**Process:** Remove the comment. Run mypy. Verify clean.

```bash
mypy src/specify_cli/migration/rebuild_state.py
```

---

### T017 — Fix `migration/backfill_identity.py:36`: fix no-any-return + remove stale ignore

**File:** `src/specify_cli/migration/backfill_identity.py`

This file has a stale `# type: ignore` at line 36, but the underlying situation is more
involved: the function at line 36 (or surrounding it) has a `no-any-return` violation
(returns `Any` where a specific type is declared).

**Process:**
1. Read the function containing line 36. Note the declared return type annotation.
2. Identify what the function actually returns (likely a dict, list, or optional).
3. Fix the return type: either tighten the annotation to `Any` (if the function is truly
   dynamic) OR narrow the actual return expression to match the declared type.
   - Preferred: narrow the return expression (cast if necessary):
     ```python
     from typing import cast
     return cast(ExpectedType, some_dict)
     ```
   - Fallback: if narrowing is impractical, change the return annotation to `dict[str, Any]`
     (explicit `Any` is better than implicit `Any`)
4. After fixing `no-any-return`, remove the `# type: ignore` comment.
5. Run mypy and confirm both the `no-any-return` and `unused-ignore` errors are gone.

```bash
mypy src/specify_cli/migration/backfill_identity.py
```

---

### T018 — Fix `policy/audit.py:27`: fix no-any-return + remove stale ignore

**File:** `src/specify_cli/policy/audit.py`

Same pattern as T017 — a `no-any-return` violation with a stale `# type: ignore` at line 27.

**Process:**
1. Read the function around line 27. Note the return type annotation.
2. The function likely returns a parsed value from a dict or YAML — something like
   `return config.get("key")` where the annotation says `str`.
3. Fix the return expression:
   ```python
   # Option A: assert/cast to narrow
   value = config.get("key")
   assert isinstance(value, str)
   return value
   
   # Option B: provide a typed default
   return str(config.get("key", ""))
   
   # Option C: widen the annotation to match reality
   def my_func(config: dict[str, Any]) -> str | None:
       return config.get("key")  # type is str | None
   ```
   Choose the option that preserves existing test behavior.
4. Remove the `# type: ignore` comment.
5. Run mypy and confirm clean.

```bash
mypy src/specify_cli/policy/audit.py
```

---

### T019 — Verify mypy passes for all 5 WP04 files; run affected tests; no regressions

**Full verification gate:**

```bash
# 1. Mypy clean for all 5 files
mypy \
  src/specify_cli/post_merge/stale_assertions.py \
  src/specify_cli/merge/config.py \
  src/specify_cli/migration/rebuild_state.py \
  src/specify_cli/migration/backfill_identity.py \
  src/specify_cli/policy/audit.py

# 2. Run affected test suites
pytest tests/post_merge/ tests/merge/ tests/migration/ tests/policy/ \
  -m "fast or git_repo" -q 2>&1 | tail -5
```

If mypy reports errors:
- `unused-ignore`: a comment was not removed correctly (check the exact line)
- A new error on a previously-suppressed line: C-005 applies — the suppression was valid;
  restore it with a typed code: `# type: ignore[<code>]`

If tests fail:
- For T017/T018 (no-any-return fixes), a test failure indicates the return type change
  affected downstream behavior — inspect the diff and narrow the fix

**Commit** once all gates pass.

## Definition of Done

- [ ] `mypy` exits 0 for all 5 files (no `unused-ignore` errors)
- [ ] No new mypy errors introduced by removing the comments
- [ ] `no-any-return` violations in `backfill_identity.py` and `policy/audit.py` are fixed
- [ ] All tests in affected modules pass
- [ ] Any comment that turned out to be a valid suppression is restored with `# type: ignore[<code>]` and a `# TODO` comment
- [ ] Changes committed to `feat/080-ci-hardening-and-lint-cleanup`

## Risks

- **Stale ignore is actually valid (medium risk):** About 20% of "stale" ignores turn out to
  still be masking a real error that was just suppressed at the wrong code version. C-005
  handles this — always verify with mypy before declaring it stale.
- **no-any-return fix breaks a test (low risk):** If a test asserts on the exact value returned
  by the fixed function and the type narrowing changes the value, the test will fail. Read
  the test before narrowing.
- **Cascade errors after removal:** Removing a `# type: ignore` on line X may expose a type
  error on line X+1 that was hidden by the propagation of the suppressed `Any`. Run mypy on
  the full file, not just the edited line.

## Reviewer Guidance

Each subtask's diff should be extremely small: one line changed per `# type: ignore` removal.
For T017 and T018, the diff will be slightly larger (a return expression or annotation change
plus the comment removal). Reject any diff that modifies logic beyond what is needed for type
correctness.
