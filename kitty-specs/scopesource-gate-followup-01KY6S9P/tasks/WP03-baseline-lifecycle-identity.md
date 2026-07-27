---
work_package_id: WP03
title: baseline lifecycle + source identity (the B1 fix)
dependencies:
- WP01
- WP02
requirement_refs:
- FR-008
- FR-009
- FR-012
- FR-013
- NFR-002
- NFR-005
planning_base_branch: fix/scopesource-gate-followup
merge_target_branch: fix/scopesource-gate-followup
branch_strategy: Planning artifacts for this mission were generated on fix/scopesource-gate-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/scopesource-gate-followup unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 3 - baseline correctness
history:
- at: '2026-07-23T10:19:53Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- tests/review/test_baseline_lifecycle.py
- tests/review/test_baseline_anti_narrowing.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/baseline.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- ruff.toml
- tests/review/test_baseline_lifecycle.py
- tests/review/test_baseline_anti_narrowing.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2873'
---

# Work Package Prompt: WP03 – baseline lifecycle + source identity (the B1 fix)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter and behave per its guidance.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` before starting; address all feedback.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in fenced code blocks.

---

## Objectives & Success Criteria

Close the **parse-after-teardown asymmetry (B1)** that would reintroduce the bug for artifact-based
declared commands, unify baseline capture onto the shared factory, and record the source identity the head
diff (WP04) asserts against. This WP owns `baseline.py` + `workflow_executor.py` + `ruff.toml`.

Complete when:

- **`BaselineTestResult.source_identity: str = "unknown"`** exists (FR-009), serialized by `to_dict`,
  defaulted by `from_dict` to `"unknown"` for straddling-upgrade artifacts (no `KeyError`).
- **`_capture_baseline_via_scope_source` parses/relocates the artifact BEFORE worktree teardown** (FR-008
  / B1) and records `source_identity = scope_source_identity(scope_source, raw)` at the same point.
- **Implement-time capture injects the shared factory** (`workflow_executor.py` `capture_baseline(...)`
  call gains `scope_source=resolve_scope_source(main_repo_root)`), activating
  `_capture_baseline_via_scope_source`.
- **A direct B1 red-first test** is red on base before T014 and green after.
- **An anti-narrowing guard** proves the baseline runs the WHOLE command (FR-012 / C-005).
- **Boyscout**: the unused `timezone` import is gone and the `ruff.toml` `baseline.py` entry is tightened
  (FR-013).

Requirements covered: **FR-008, FR-009 (field half), FR-012, FR-013 (baseline half)**; NFR-005 (consumes).
Carrier for IC-09, IC-10 (field), IC-13, IC-05 (baseline half).

## Context & Constraints

- **Design authorities**: [data-model.md §1 (field), §5 (lifecycle)](../data-model.md);
  [contracts/baseline-identity-contract.md](../contracts/baseline-identity-contract.md);
  [plan.md IC-09/IC-10/IC-13/IC-05](../plan.md); [post-plan-squad.md M-B1 (direct red-first), M-nfr5r](../reviews/post-plan-squad.md).
- **Consumes from WP02** (already landed): `resolve_scope_source(repo_root, ...)` and
  `scope_source_identity(scope_source, raw)` — import them from `specify_cli.review.scope_source`. Do NOT
  redefine either.
- **The B1 lifecycle fix** (data-model §5, `baseline.py:491-536`): today `raw =
  _run_command_for_baseline(...)` runs inside `with _baseline_worktree(...)` (`:517-520`) but
  `failures = scope_source.parse_results(raw)` runs AFTER the `with` (`:522`, post-teardown). Move the
  parse (or relocate the artifact to a stable out-of-worktree path, then parse the relocated copy) INSIDE
  the `with`, before teardown; record `source_identity` there. `GateCoverageScopeSource` (absolute
  tempfile JUnit) is unaffected either way; `DeclaredCommandScopeSource` with a worktree-relative
  `--junitxml` is the bug surface.
- **`from_dict` default** (data-model §1, US1 AS4): `source_identity=data.get("source_identity",
  "unknown")`. `"unknown"` at diff time ⇒ the head path (WP04) emits `UNVERIFIED_BASELINE`, never a
  spurious `SOURCE_MISMATCH`.
- **Broad-baseline invariant** (C-005): the baseline runs the whole command; head narrows via
  `scope.test_targets`. Command AUTHORITY is unified; scope legitimately differs. The guard (T017) asserts
  baseline does NOT get head's per-file targets appended.
- **Boyscout** (data-model §5): `baseline.py:25` is `from datetime import datetime, timezone, UTC` — only
  `datetime`/`UTC` are used; delete `timezone`. Tighten the `ruff.toml` `baseline.py` entry from
  `["ARG001","F401","S314","S602"]` to `["ARG001","S314"]` (F401 clears once the import is gone; S602 is
  already stale — no `shell=True`; ARG001 stays for the dead `mission_slug` param at `baseline.py:267`,
  explicitly OUT of scope). Do this as the TRAILING edit after T014 rewrites the file.
- **Do NOT edit** `pre_review_gate.py` (WP04 reads `source_identity` + constructs `SOURCE_MISMATCH`),
  `scope_source.py` (WP02), or `tasks_move_task.py` (WP04). This WP provides the field + the factory
  injection; the diff-time compare is WP04's.
- **Quality bars (NFR-002)**: `mypy --strict` + `ruff` zero issues, complexity ≤15, ≥90% new coverage.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership)
- **Planning base branch**: `fix/scopesource-gate-followup`
- **Merge target branch**: `fix/scopesource-gate-followup`

## Subtasks & Detailed Guidance

### Subtask T013 – `source_identity` field on `BaselineTestResult`

- **File**: `src/specify_cli/review/baseline.py` (`BaselineTestResult` `:63-124`).
- **Steps**: Add `source_identity: str = "unknown"` to the frozen dataclass. `to_dict` (`:77`) adds
  `"source_identity": self.source_identity`; `from_dict` (`:92`) sets `source_identity=data.get(
  "source_identity", "unknown")`.
- **Red-first**: a test round-tripping a result WITH the field and a legacy dict WITHOUT it (→ `"unknown"`,
  no `KeyError`).

### Subtask T014 – Parse-before-teardown lifecycle fix + record identity (B1)

- **File**: `baseline.py` (`_capture_baseline_via_scope_source` `:491-536`).
- **Steps**: Restructure so `scope_source.parse_results(raw)` (or an artifact relocation to a stable
  out-of-worktree path followed by parsing the relocated copy) happens INSIDE `with _baseline_worktree(...)`,
  before teardown. Set `source_identity = scope_source_identity(scope_source, raw)` at that point and thread
  it into the returned `BaselineTestResult`.
- **Notes**: keep `GateCoverageScopeSource` byte-identical (its absolute JUnit already survives). The
  relative `--junitxml` in the declared-command case resolves against `cwd=tmp_worktree`.

### Subtask T015 – Inject the shared factory into implement-time capture

- **File**: `src/specify_cli/cli/commands/agent/workflow_executor.py` (`capture_baseline(...)` call
  `:1153-1160`, per data-model §3).
- **Steps**: Pass `scope_source=resolve_scope_source(main_repo_root)` into the `capture_baseline(...)`
  call so the implement-time path activates `_capture_baseline_via_scope_source` (and thus honors FR-014's
  selected source). Use the SAME `main_repo_root` the baseline placement already resolves
  (`_resolve_workflow_placement(kind=WORK_PACKAGE_TASK)` `:1176-1180`) — do NOT reconstruct a root.
- **Notes**: this is the write-side; the diff-time READ seam (`_resolve_workflow_read_dir`) is WP04's.
  `workflow_executor.py` does not currently import `scope_source` — this adds a NEW (cycle-free, verified
  by post-plan squad paula) import edge on the write side; that is fine, just be aware it is a new edge
  (data-model §3's "both consumers already import → no new edge" is scoped to the factory's two readers).

### Subtask T016 – B1 red-first DIRECT capture unit test

- **File (create)**: `tests/review/test_baseline_lifecycle.py` (owned, `create_intent`).
- **Steps**: A **direct** `capture_baseline` / `_capture_baseline_via_scope_source` unit test using
  `DeclaredCommandScopeSource` whose command writes a **worktree-relative** `--junitxml` artifact. Assert
  the parsed baseline failure identities match those the head run would derive (shared namespace). This
  test is **RED on the base** (the workflow-routed path is dormant on base; the direct call exposes the
  post-teardown parse) BEFORE T014, and GREEN after. Split: land the factory-injection with the red
  observed, then T014's relocate greens it.
- **Notes**: the relative `--junitxml` resolves against `cwd=tmp_worktree`, not the process cwd — set up
  the fixture accordingly. Record in the Activity Log that this red is a genuine bug repro, not migration-red.

### Subtask T017 – Anti-narrowing guard test (C-005 / FR-012)

- **File (create)**: `tests/review/test_baseline_anti_narrowing.py` (owned, `create_intent`).
- **Steps**: Assert the baseline command is run WITHOUT head's per-file `scope.test_targets` appended, so
  a future refactor cannot silently narrow the baseline. `[P]` — independent of T013-T016.

### Subtask T018 – `baseline.py` boyscout (FR-013)

- **Files**: `baseline.py:25`, `ruff.toml`.
- **Steps**: Delete `timezone` from the `from datetime import datetime, timezone, UTC` line (keep
  `datetime`, `UTC`). Tighten the `ruff.toml` `baseline.py` entry to `["ARG001","S314"]`. Do this LAST,
  after T014's rewrite. `[P]` w.r.t. T017.
- **Notes**: confirm `ruff check src/specify_cli/review/baseline.py` stays zero-issue with the tightened
  entry (F401/S602 must be genuinely clear).

## Test Strategy

- **Order**: T013 → T016 (observe red) → T014/T015 (green it) → T017, T018.
- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_baseline_lifecycle.py tests/review/test_baseline_anti_narrowing.py -q
  ```
- **Quality**: `ruff check src/specify_cli/review/baseline.py src/specify_cli/cli/commands/agent/workflow_executor.py`;
  `mypy --strict src/specify_cli/review/baseline.py`; ≥90% new coverage.
- **Regression**: `pytest tests/review/test_transition_gate_parity.py -q` stays green (baseline changes
  must not shift the registry-path golden).

## Risks & Mitigations

- **B1 itself**: worktree-relative artifact deleted on teardown → parse inside the `with`. The T016 red
  is the proof; do not green it by any means other than T014's relocate.
- **Spurious mismatch on legacy artifacts**: `from_dict` defaults `"unknown"` → head degrades to
  `UNVERIFIED_BASELINE` (WP04), never a mismatch.
- **Premature ruff tighten**: sequence T018 last, after the file is rewritten.

## Review Guidance

- Parse happens before teardown; `source_identity` recorded via `scope_source_identity` (not a local
  re-derivation).
- Factory injected at the implement-time call using the existing `main_repo_root`.
- T016 red is a real bug repro (labeled) and green only after the relocate.
- `from_dict` legacy-safe; anti-narrowing guard present; boyscout clean; zero suppressions.

## Activity Log

> **CRITICAL**: chronological order, append at the END.

- 2026-07-23T10:19:53Z – system – Prompt created.

### Updating Status

`spec-kitty agent tasks move-task WP03 --to <status>`.
