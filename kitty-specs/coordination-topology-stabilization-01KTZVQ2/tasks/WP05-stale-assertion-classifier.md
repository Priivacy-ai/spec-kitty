---
work_package_id: WP05
title: Stale-Assertion Message-Content Classifier
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "92989"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/stale_assertions.py
execution_mode: code_change
owned_files:
- src/specify_cli/stale_assertions.py
- tests/specify_cli/test_stale_assertions_message.py
priority: P2-High
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Suppress or demote stale-assertion false positives (FPs) where the removed literal is the right-hand operand of an `in`/`not in` operator whose left-hand operand is a message-capture expression (`str(exc)`, `.message`, `.stderr`, `.stdout`, capsys captures, etc.). Also fix the `changed_literals` last-wins dict bug and add confidence grouping.

---

## Context

### The Bug (Issue #1886)

`_literal_findings_for_assertion` in `stale_assertions.py:350` reports findings for ALL removed literals without checking whether the assertion tests message content. This causes FPs when a diagnostic message is intentionally changed: the assertion `assert "old error text" in str(exc)` becomes `assert "new error text" in str(exc)`, and the stale-assertion analyzer flags `"old error text"` as a stale literal even though the test is still correct — the developer deliberately updated the message.

### Message-Capture AST Pattern

A message-capture expression is the left-hand side of an `in` operator that is:
- `str(<expr>)` / `repr(<expr>)`
- `<expr>.message` / `<expr>.stderr` / `<expr>.stdout` / `<expr>.output`
- `<expr>.value` (for `excinfo.value.message`)
- A `capsys.readouterr().out` / `capsys.readouterr().err` call chain

When the right-hand side (the literal) has been removed from the codebase, and the left-hand side matches the message-capture pattern → emit at `info` grade with label `message-content-check` rather than as a stale-assertion finding.

### `changed_literals` Last-Wins Dict Bug

At `stale_assertions.py:~280`, `changed_literals` is built as a dict:
```python
changed_literals[old_literal] = new_literal
```
When the same literal is removed at multiple call sites (e.g., 3 test files all check `"bad request"`), only the last removal site is recorded. Fix: use `dict[str, list[str]]` or collect all removal sites.

---

## Subtasks

### T021 — Add message-capture expression classifier in `_literal_findings_for_assertion`

1. Read `src/specify_cli/stale_assertions.py` lines 340–420 in full.
2. Identify the point where findings are emitted for `in`-operator assertions.
3. Write a helper:
   ```python
   def _is_message_capture_expr(node: ast.expr) -> bool:
       """Return True if node is a message-capture expression."""
       # str(...) / repr(...)
       if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
           if node.func.id in ("str", "repr"):
               return True
       # .message / .stderr / .stdout / .output / .value
       if isinstance(node, ast.Attribute):
           if node.attr in ("message", "stderr", "stdout", "output", "value"):
               return True
       # capsys.readouterr().out / .err
       if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Call):
           if isinstance(node.value.func, ast.Attribute):
               if node.value.func.attr == "readouterr":
                   return True
       return False
   ```
4. In `_literal_findings_for_assertion`, before emitting a finding for an `in`-operator assertion:
   - Check if the left operand passes `_is_message_capture_expr`.
   - If yes: emit at `grade="info"` with `label="message-content-check"` instead of the default grade.
5. Do NOT suppress entirely — emit at info so operators can still audit them.

### T022 — Fix `changed_literals` last-wins dict

1. Read `src/specify_cli/stale_assertions.py` lines 270–300.
2. Change `changed_literals: dict[str, str]` to `changed_literals: dict[str, list[str]]`.
3. Update all call sites that build and read `changed_literals` to handle the list.
4. In merge summary output, report all removal sites, not just the last.

### T023 — Add confidence threshold/grouping in merge summary

1. Read `src/specify_cli/merge/executor.py` lines 2560–2580 (stale-assertion merge summary).
2. Add grouping by grade: `high`/`medium` findings first, then `low`, then `info` (message-content).
3. In the merge summary, add a note if any `info`-grade `message-content-check` findings exist:
   ```
   Note: N message-content assertions skipped (info grade) — review manually if diagnostic text changed.
   ```
4. This prevents CI noise while preserving auditability.

### T024 — Regression tests for message-content FP suppression

File: `tests/specify_cli/test_stale_assertions_message.py` (new)

Write pytest tests that:
1. Create a before/after AST fixture where `assert "old text" in str(exc)` is updated to `assert "new text" in str(exc)`.
2. Call `_literal_findings_for_assertion` (or the public surface) on the diff.
3. Assert no `high`/`medium` findings — only `info`-grade findings with `label="message-content-check"`.
4. Also test the negative: `assert "old text" in some_set` (NOT a message capture) → still emits at the original grade.
5. Test `changed_literals` multi-site: same literal removed in 3 files → all 3 sites reported.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP05 --agent <name>
```

---

## Definition of Done

- [ ] `_is_message_capture_expr` helper present and tested
- [ ] Message-capture `in`-operator findings emitted at `info` grade
- [ ] `changed_literals` is now `dict[str, list[str]]` — all sites reported
- [ ] Merge summary groups by grade and notes info-grade findings
- [ ] `test_stale_assertions_message.py` passes
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **AST node variants**: The `in` operator may appear in `ast.Compare` nodes with multiple comparators. Handle `ast.In` and `ast.NotIn` in `ast.Compare.ops`. Do not assume a simple binary expression.
- **Identifier channel**: `stale_assertions.py:440–479` (identifier channel) may have the same FP pattern at higher confidence — note this as a follow-up but do not fix in this WP (scope creep risk).
- **`changed_literals` type change**: Callers that expect `dict[str, str]` will need updating. Run `mypy` to find all affected call sites.

## Activity Log

- 2026-06-13T07:59:31Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Assigned agent via action command
- 2026-06-13T08:06:28Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Ready for review: stale-assertion classifier implemented
- 2026-06-13T08:07:25Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=92989 – Started review via action command
- 2026-06-13T08:14:23Z – user – shell_pid=92989 – Review passed: stale-assertion classifier correct, types consistent, all 51 tests pass, mypy --strict clean
