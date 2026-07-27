---
work_package_id: WP06
title: '#1888 existence-check fix + #1971-tail verify'
dependencies: []
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: feat/naming-rider-3-2-1
merge_target_branch: feat/naming-rider-3-2-1
branch_strategy: Planning artifacts for this mission were generated on feat/naming-rider-3-2-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/naming-rider-3-2-1 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1909318"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/ownership/
create_intent:
- tests/specify_cli/ownership/test_validation_existence.py
- tests/specify_cli/core/test_locate_project_root_convergence.py
execution_mode: code_change
owned_files:
- src/specify_cli/ownership/validation.py
- tests/specify_cli/ownership/test_validation_existence.py
- tests/specify_cli/core/test_locate_project_root_convergence.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read `spec.md` (FR-006/FR-007), `plan.md` (IC-04), and `scope-review/priti-ticket-focus.md` (#1888 is
a real bug, not verify-close).

## Objective

(a) Fix the **#1888** phantom-path validation bug (real, TDD-first); (b) add the **#1971-tail** regression
test that *disproves the `SPECIFY_REPO_ROOT`/worktree split-brain* across the three `locate_project_root`
entries. Independent WP (no seam interaction).

## Subtasks

### T022 — (#1888) Failing repro FIRST (TDD)
Create `tests/specify_cli/ownership/test_validation_existence.py` with a failing test: ownership
validation **passes a phantom / non-existent owned path silently** (the bug Robert hit). Pin the exact
current (wrong) behavior so the fix flips it.

### T023 — (#1888) Add the existence check
In `src/specify_cli/ownership/validation.py`, add the missing existence check so validation no longer
silently passes non-existent declared owned paths. **Scope it carefully:** only reject declared owned
paths that must exist *at validation time*; do NOT reject legitimate future files that belong in
`create_intent` (zero-match `**` globs still warn, not fail — see #2007 bug #10 semantics). Make the
failure typed and actionable.

### T024 — (#1971-tail) Convergence regression test
Create `tests/specify_cli/core/test_locate_project_root_convergence.py` that **disproves the split-brain
the ticket asserts** — not merely "the 3 entries exist." Assert that `__init__.py`, `core/project_resolver.py`,
and `core/paths.py` all converge on the `core/paths.py` authority under the conditions that matter:
`SPECIFY_REPO_ROOT` set, worktree `.git`-file pointer, and `.kittify` walk. Pin the benign `__init__.py`
no-arg signature divergence. **Do NOT touch the intentional deferred-import shims** — reverting them is the
documented #1971 regression.

## ⚠️ Post-tasks remediation (binding — see tasks-review/POST-TASKS-SYNTHESIS.md)

- **#1888 — TDD-VERIFY, do not assume.** An existence check (`validate_glob_matches`, literal-zero-match
  hard error) **already landed** at `ownership/validation.py:319/375` (commit `991162c0a`, the
  topology-stabilization mission — *after* our scope review). So a "write a failing repro" framing can't
  fail. Instead: **write the #1888 repro test FIRST** (the exact phantom-path case the ticket describes).
  - If it **PASSES on HEAD** → the fix covers #1888: **verify-and-close** with that test as the evidence;
    do **NOT** fabricate a code change.
  - If it **FAILS** → there's a real gap: add the missing check (scoped per the create_intent/future-file
    rule below).
  Per the standing rule, a bug is not "fixed" because the code looks fixed — let the test decide. Record
  which path occurred.
- **#1971-tail — reject the tautology.** The regression test must assert **equal resolved `Path` values
  under each of the three named conditions** (`SPECIFY_REPO_ROOT` set, worktree `.git`-file pointer,
  `.kittify` walk) using a **divergent input** that would expose drift. A test that merely asserts "the 3
  entries exist / return the same type" must be REJECTED.

## Branch Strategy
Base/merge target: `feat/naming-rider-3-2-1`. Worktree from `lanes.json`.

## Definition of Done
- [ ] #1888 repro fails before the fix, passes after; phantom paths now rejected; future `create_intent`
      files NOT rejected; zero-match `**` globs still warn-not-fail.
- [ ] #1971-tail test proves the 3 entries converge under env-var/worktree/`.kittify` conditions; shims
      untouched.
- [ ] `ruff`/`mypy` clean on diff; complexity ≤ 15; no suppressions.

## Risks / reviewer guidance
- **Reviewer:** confirm the #1888 existence check does not over-reject (the create_intent / future-file
  case is the trap — verify a future literal path declared in owned_files + create_intent still validates).
- **Note (not in scope):** the deeper #2007 read-path bugs (#6 second root authority at `core/paths.py:284-288`,
  #7 coord-only `is_committed`) are the read-path follow-on focus — this WP only adds the #1971-tail
  *convergence test* and the #1888 *existence check*, nothing in the resolver itself.

## Activity Log

- 2026-06-16T12:22:36Z – claude:sonnet:python-pedro:implementer – shell_pid=1879752 – Assigned agent via action command
- 2026-06-16T12:29:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1879752 – #1888: PASSES-ON-HEAD = verify-and-close with test as evidence; #1971-tail divergent-input convergence test green (3 conditions x 3 entries = equal resolved Paths); shims untouched; ruff+mypy clean.
- 2026-06-16T12:30:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=1909318 – Started review via action command
- 2026-06-16T12:32:30Z – user – shell_pid=1909318 – Review passed: #1888 verify-and-close (validation.py unchanged; 5 real phantom-path tests pass on HEAD incl. create_intent-suppressed + zero-match-glob-warns over-rejection guards); #1971-tail 6 divergent-input convergence tests (non-tautological: env-var-override/worktree-pointer/.kittify-walk each assert equal resolved Paths AND correct value across all 3 entries, plus shim-integrity pins); shims untouched; ruff+mypy clean; no suppressions. issue-matrix #1888 set verified-already-fixed.
