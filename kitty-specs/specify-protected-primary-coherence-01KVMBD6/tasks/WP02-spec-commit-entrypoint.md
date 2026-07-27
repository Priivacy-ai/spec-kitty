---
work_package_id: WP02
title: Extract planning-commit pipeline + spec-commit entrypoint + record-analysis
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-007
- FR-009
- NFR-001
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T027
- T028
- T014
- T017
phase: Phase 2 - P0 Fix
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3069227"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/coordination/
create_intent:
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- tests/coordination/test_commit_router.py
- tests/specify_cli/cli/commands/test_spec_commit_cmd.py
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/__init__.py
- tests/coordination/test_commit_router.py
- tests/specify_cli/cli/commands/test_spec_commit_cmd.py
- tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py
role: implementer
tags: []
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Close the #1619 P0 deadlock at the specify boundary via a **new mission-aware spec-commit entrypoint** that
materializes the coordination worktree on demand on a protected primary. To do that without a parallel
materializer (C-001), **extract** the canonical planning-commit pipeline out of `mission.py` into a reusable
`coordination/commit_router.py` helper, then build the entrypoint on top of it. This WP owns **all
`mission.py` edits** (extraction + caller repoint + record-analysis) so ownership stays disjoint from WP04.

Design basis: `plan.md` (IC-02), `research.md` (D2), ADR `2026-06-21-1`. NOTE: the plan/IC-02 prose names the
`safe_commit_cmd.py` boundary, but the operator decision (and this WP) use a **new** entrypoint; the generic
`safe-commit` stays unchanged (recorded as an analyze-class erratum).

## Context & Constraints

- **The "mirror `_planning_commit_worktree`" framing is wrong — it is a 5-function pipeline** (Alphonso B-1).
  The real canonical routine is the composition of (all in `cli/commands/agent/mission.py`):
  `_resolve_planning_placement` (`:732`), `_planning_commit_worktree` (`:748`),
  `_stage_finalize_artifacts_in_coord_worktree` (`:120` — the artifact copy-across, incl.
  `COORD_OWNED_STATUS_FILES` skip #1589 + #1814 primary-residue cleanup), `_safe_load_meta` (`:802`, mid8),
  `_artifact_absent_at_placement` (`:1035`), plus the `safe_commit(...)` call + the benign "nothing to
  commit" handling (`:1239-1260`). These have NO hidden command/typer state — they import cleanly
  (`COORD_OWNED_STATUS_FILES` from `specify_cli.status`, `CoordinationWorkspace` from `coordination.workspace`,
  `resolve_mid8` from `lanes.branch_naming`, `resolve_placement_only` from `mission_runtime`, `safe_commit`
  from `specify_cli.git`). So extraction is clean.
- **Reuse only (C-001)**: extract, leave thin re-export shims in `mission.py`, repoint mission.py's own
  callers — do NOT leave two live copies.
- Preserve the #1718 create-window contract: materialize at the COMMIT boundary, not at read time (the
  materializer is process-stateless, so a standalone-process entrypoint is fine — confirm by test, don't worry).

## Subtasks & Detailed Guidance

### Subtask T006 — Extract the pipeline into `coordination/commit_router.py`
- Move the 5 helpers above + the safe_commit/benign-no-op wrapper into `src/specify_cli/coordination/commit_router.py`
  as a canonical `commit_for_mission(repo_root, mission_slug, files, message, policy) -> CommitResult`:
  resolve placement via `resolve_placement_only`; if `policy.is_protected(target_ref)` AND placement is
  COORDINATION → materialize via `CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)` (NOTE: param
  is `mission_slug`), copy artifacts across, commit on the coord branch; else commit directly (FR-005);
  idempotent.
- **Files**: `src/specify_cli/coordination/commit_router.py` (new).

### Subtask T027 — Collapse the THREE inline commit tails into `commit_for_mission` (de-god fold, #2056)
- The pipeline is open-coded **three more times inline**, bypassing the wrapper — each hand-rolls
  `_resolve_planning_placement` + `_planning_commit_worktree` + `safe_commit(...)` + `_try_advance_primary_ref`:
  `mission.py:2443-2468` (gap-analysis commit), `:2500-2510` (generator-config commit), `:3937-3961`
  (tasks commit in `finalize_tasks`). **Collapse all three TAILS into single `commit_for_mission(...)` calls**
  — not merely repoint the low-level `_planning_commit_worktree` helper. If only the helper is repointed and
  the `safe_commit + _try_advance_primary_ref` tails stay duplicated, the split-brain class is **relocated, not
  closed** (Paula's load-bearing finding from the #2056 research squad). Leave thin re-export shims for any
  symbol still imported elsewhere.
- **Success criterion (reviewer gate)**: after this WP, `grep -c 'safe_commit(' src/specify_cli/cli/commands/agent/mission.py`
  drops to ~0 (only a re-export shim, no parallel pipeline) — the C-001 "no leftover duplicate" evidence.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`.
- **Scope note**: this is the ONLY `agent/mission.py` de-god slice folded into this P0 mission (it completes
  the WP02 extraction). The remaining decomposition (`finalize_tasks` phase-split, `_parse_*_md` parsers,
  branch-context/identity, emit helpers) is deferred to #2056.

### Subtask T007 — New mission-aware spec-commit entrypoint
- New `src/specify_cli/cli/commands/spec_commit_cmd.py`. Derive `mission_slug` from a `kitty-specs/<slug>/`
  path arg via `Path(arg).name`, or `--mission` (pass-through to `resolve_placement_only`'s built-in handle
  canonicalization — do NOT build a new reverse-resolver, C-001). Resolve `ProtectionPolicy.resolve(repo_root)`,
  call `commit_for_mission(...)`.
- **Files**: `src/specify_cli/cli/commands/spec_commit_cmd.py` (new).

### Subtask T028 — Register the command (CORRECTED target)
- Register in **`src/specify_cli/cli/commands/__init__.py::register_commands`**, mirroring the `safe-commit`
  precedent at `:226` (`app.command(name="…")(spec_commit_module.<fn>)`). This is the REAL registration site —
  NOT `src/specify_cli/__init__.py` (which only calls `register_commands`; `__version__` is dynamic, so no
  forced version bump). A `CHANGELOG.md` entry for the new user-facing command is reasonable but optional.
- **Files**: `src/specify_cli/cli/commands/__init__.py`.

### Subtask T008 — Actionable refusal error (FR-003)
- If the commit cannot proceed, materialize-then-retry or emit the EXACT sanctioned command; never point at a
  worktree nothing materializes.

### Subtask T014 — record-analysis materialize-then-retry (moved here; owns mission.py)
- `record-analysis` (`mission.py:898` `assert_not_protected_branch`) currently raises/exits on a protected
  primary and writes the report to the primary checkout. Route its report commit through `commit_for_mission`
  (materialize-then-retry); fix the actionable-error-points-at-unmaterialized-path defect. Its protection
  provenance comes from WP01's demotion of `assert_not_protected_branch` (`commit_helpers.py:527`) — do not
  re-read directly.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`.

### Subtask T017 — REWRITE landmine L1 (moved here)
- `tests/specify_cli/cli/commands/agent/test_record_analysis_coord_worktree.py` — the `PROTECTED_BRANCH_REFUSED`
  assertion is at **:292-294** (the `:225` def). Rewrite to assert materialize-then-retry (report on coord
  branch; worktree materialized by the command; no refusal).
- **Files**: that test.

### Subtask T009 — Helper + entrypoint tests (narrow; full e2e in WP07)
- `commit_router` (protected → materializes + lands on coord branch; unprotected → direct; idempotent) and
  the entrypoint wiring. Reuse `ProtectedTargetRepo`. Assert #1718 preserved (no materialization at read time).
  Include a negative variant (stub the materializer ⇒ test FAILS).
- **Files**: `tests/coordination/test_commit_router.py`, `tests/specify_cli/cli/commands/test_spec_commit_cmd.py`.

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- Pipeline extracted to `commit_router.py`; the **three inline commit tails collapsed** into `commit_for_mission`
  (T027); new entrypoint registered in `cli/commands/__init__.py`; record-analysis materializes-then-retries;
  L1 rewritten.
- **De-god evidence (#2056)**: `grep -c 'safe_commit(' src/specify_cli/cli/commands/agent/mission.py` ≈ 0
  (only a re-export shim) — proves the duplication was removed, not relocated. Record the count in the handoff
  note + PR body.
- Protected → spec/report land on coord branch; unprotected → direct; idempotent; #1718 preserved.
- ruff + mypy clean; complexity ≤ 15.

## Risks & Reviewer Guidance
- **C-001 (both directions)**: no new materializer AND no leftover duplicate — confirm the three inline tails
  (`:2443`/`:2500`/`:3937`) now call `commit_for_mission`, evidenced by the `safe_commit(` occurrence count.
- **B-1**: confirm the entrypoint derives `mission_slug` + resolves COORDINATION placement + copies artifacts
  (a "worktree was created" test is insufficient — WP07's negative variant is the gate).
- Confirm registration is in `cli/commands/__init__.py` (not `specify_cli/__init__.py`).

## Activity Log

- 2026-06-21T08:23:52Z – claude:sonnet:python-pedro:implementer – shell_pid=3005066 – Assigned agent via action command
- 2026-06-21T09:13:46Z – claude:sonnet:python-pedro:implementer – shell_pid=3005066 – WP02 (lane-b): extract commit_for_mission + new spec-commit entrypoint + 3-tail collapse (safe_commit(=0) + record-analysis materialize-then-retry + L1 rewrite; 312 passed
- 2026-06-21T09:13:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=3069227 – Started review via action command
- 2026-06-21T09:37:25Z – user – shell_pid=3069227 – Review passed cycle-2 (reviewer-renata): findings resolved + mutation-verified, 312 green
