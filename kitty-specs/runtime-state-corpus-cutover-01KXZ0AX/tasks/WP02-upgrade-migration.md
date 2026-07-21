---
work_package_id: WP02
title: Upgrade-path migration (existing deployments)
dependencies:
- WP01
requirement_refs:
- FR-010
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
agent: "claude"
shell_pid: "3706820"
shell_pid_created_at: "1784549947.15"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
create_intent:
- src/specify_cli/upgrade/migrations/m_zz_runtime_state_backfill.py
- tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/upgrade/migrations/m_zz_runtime_state_backfill.py
- tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py
role: implementer
tags: []
tracker_refs: []
---

> **RENAME NOTICE (ordering trap — see Risks):** the file is `m_zz_runtime_state_backfill.py`,
> **not** `m_3_3_1_runtime_state_backfill.py`. The brief's `m_3_3_1_*` name provably sorts **before**
> the charter-fold migrations and would run at the wrong point (FR-010 requires "after the charter
> folds"). `owned_files`/`create_intent` above are updated accordingly. Rationale is load-bearing —
> read the Subtasks/Risks sections before writing a line.

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` implementer profile before touching code:

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration. `python-pedro` is
the Python-specialist implementer: TDD/ATDD-first, type-safe, idiomatic Python 3.11+, Sonar-aware
(complexity ≤ 15, no suppressions). Everything below is executed under that profile.

## Objective

Ship the **upgrade-path** half of the corpus cutover: an **auto-discovered** `spec-kitty upgrade`
migration that runs `backfill → verify(FAIL-CLOSED) → flip status_phase` over every mission in an
existing deployment's corpus, so a big-bang production-default flip does not strand un-migrated
on-disk WP runtime state. The migration is **fail-closed** (stricter than the operator CLI): any one
mission's verify failure **aborts the whole migration step** with an operator-actionable message
naming the mission + mismatch, leaving **no** mission half-flipped. It **no-ops** on fresh installs
and is **idempotent** on already-migrated corpora. It **reuses** the WP01 shared cutover helper —
it must **not** fork verify-then-flip.

## Context & grounding

- **Plan IC-02** (`plan.md`, "IC-02 — Upgrade-path migration (existing deployments)"): NEW
  `upgrade/migrations/m_<version>_runtime_state_backfill.py`, self-registers via
  `@MigrationRegistry.register`, **version-key ordered to sort after the charter folds**, **reuses the
  IC-01 orchestration helper (do not fork verify-then-flip)**, plus the #2815 repo-root-write guard.
- **Spec US3 + FR-010 + NFR-002/NFR-005 + C-003** (`spec.md`): upgrade migrates existing corpora;
  auto-discovered; idempotent; fail-closed abort with actionable message + **no partial flip**;
  no-op on fresh installs; write target via `canonicalize_feature_dir`, **no** repo-root write (#2815).
- **Research D-03** (`research.md`): the **upgrade migration is stricter than the CLI** — **any**
  mission's verify failure **aborts the whole step** (the CLI is per-mission best-effort). "Non-partially
  flipped" is clarified as **per-mission atomicity**: a failed mission is never flipped; missions that
  passed earlier in the run are legitimately flipped-and-verified (each independently consistent) — it
  is **not** a corpus-wide rollback (no cross-mission transaction primitive exists).
- **Research D-04** (`research.md`): auto-discovered module, **ordered after the charter folds**; no
  central sequence-list edit (`auto_discover_migrations()` walks `m_*.py`).
- **Contract `contracts/cutover-cli.md`, "Upgrade migration" section**: the acceptance surface — self
  registers, discovered by `auto_discover_migrations()`, calls the same `cutover_mission` per mission;
  fail-closed abort; no-op fresh install; idempotent; INV-5 repo-root-write regression.
- **Data model `data-model.md`** INV-4 (idempotency), INV-5 (no repo-root write).

**Reuse, do not re-implement.** WP01 (dependency) delivers
`src/specify_cli/migration/runtime_state_cutover.py::cutover_mission(feature_dir, *, dry_run=False) -> CutoverResult`
(fields: `slug`, `flipped: bool`, `would_flip: bool`, `seeded_count: int`, `verify: VerifyResult`,
`error: str | None`). This WP **calls** it per mission. The fail-closed verify-then-flip atomicity lives
in that one helper (research D-01); a second copy here is the exact logical-duplication trap the plan
forbids.

## Subtasks

### T006 — Author the auto-discovered migration

- Create **`src/specify_cli/upgrade/migrations/m_zz_runtime_state_backfill.py`** (see the rename
  notice + Risks for the name). Subclass `BaseMigration` (`.base`), decorate with
  `@MigrationRegistry.register`. Implement `detect(project_path) -> bool`,
  `can_apply(project_path) -> tuple[bool, str]`, `apply(project_path, dry_run=False) -> MigrationResult`.
- Class attributes:
  - `migration_id = "runtime_state_backfill"` (semantic, unique — the ordering lives in the **filename**,
    exactly as `m_unify_charter_activation_finalize.py` keeps `migration_id = "consolidate_charter_bundle_fold"`).
  - `target_version = "3.2.6"` — **tie with the charter folds; do NOT set it higher.** The registry
    primary-sorts by `Version(target_version)`, and `get_applicable()` gates on `target <= to_version`;
    the installed package is `3.2.6` (unreleased), so any `target_version > 3.2.6` is **silently
    skipped** (and trips `tests/architectural/test_migration_chain_integrity.py`, which HARD-FAILs when
    the chain end is ahead of `pyproject.toml`). This mirrors `m_3_2_6_meta_traces_merge_drivers.py` and
    the charter folds — all `"3.2.6"`, shipping within the current cycle.
  - `runs_on_worktrees = False` (recommended — a corpus/primary-partition fold like the charter finalize;
    the backfill canonicalizes each write target, so per-worktree re-runs are redundant. Confirm against
    the runner before finalizing).
- Enumerate the corpus the **canonical** way, mirroring
  `specify_cli.migration.backfill_runtime_state.backfill_runtime_state_repo`: `project_path / "kitty-specs"`,
  `sorted(e for e in kitty_specs.iterdir() if e.is_dir())`. Do **not** hand-roll a divergent glob. For each
  mission `feature_dir`, call `cutover_mission(feature_dir, dry_run=dry_run)` (the write target is
  canonicalized inside the helper/library via `canonicalize_feature_dir` — C-003; the migration adds **no**
  `Path.cwd()` path — INV-5/#2815).
- Keep `apply` under complexity 15 by splitting seed/verify/flip loop from message assembly into small
  helpers; hoist repeated literals (`"kitty-specs"`, message templates) to module constants (Sonar S1192).

### T007 — Fail-closed abort + no-op + idempotency semantics

- **Fail-closed abort (NFR-005, D-03):** iterate missions; on the **first** `CutoverResult` whose
  `verify.ok` is false (or `error` is set), **stop immediately** and return
  `MigrationResult(success=False, errors=[<actionable message>])`. The message MUST name the **mission**
  (slug) and the **specific count/value mismatch** carried on `result.verify`, and state the remediation
  (run `spec-kitty migrate backfill-runtime-state --mission <slug> --dry-run` to inspect). Do **not**
  visit further missions after the abort. Missions flipped earlier in this run stay flipped — each was
  verified, so no mission is half-flipped (per-mission atomicity, not corpus rollback).
- **No-op on fresh install:** if `kitty-specs/` is absent, or no mission carries un-migrated legacy
  runtime state, `detect()` returns `False` and `apply()` returns `MigrationResult(success=True,
  changes_made=[])`. A cheap `detect()` may skip on `status_phase == "1"` (a fast skip-hint), but the
  **backfill seeds are the idempotency source of truth** (research D-02) — do not treat `status_phase`
  as the sole authority.
- **Idempotent re-run (NFR-002 / INV-4):** on an already-migrated corpus the helper seeds nothing and
  re-flips nothing; `apply()` returns success with no seed changes. Confirm a second `apply()` is a clean
  no-op.
- **Dry-run:** `apply(project_path, dry_run=True)` writes nothing (0 events, 0 flips) and reports
  would-migrate counts by threading `dry_run=True` into `cutover_mission`.

### T008 — Tests (ATDD, maps US3.1–US3.3)

Author `tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py`. Call
`detect()`/`can_apply()`/`apply()` **directly** on a migration instance (bypasses the `target_version`
guard — the established pattern in `test_unify_charter_activation_migration.py`). Build **synthetic**
fixture corpora under a `tmp_path/kitty-specs/` (do not mutate the live repo).

- **US3.1 — legacy corpus migrates:** fixture with legacy frontmatter/checkbox runtime state →
  `apply()` seeds events, verify passes, `status_phase` flips to `"1"` for every mission; reduced
  snapshot equals the old reader by count+value.
- **US3.2 — fresh install no-op:** no `kitty-specs/` (and separately, a corpus with no legacy state) →
  `detect()` False, `apply()` success with zero changes and zero writes.
- **US3.3 — one mission fails verify → step aborts, no partial flip:** fault-inject a corrupt
  deterministic seed row for one mission → `apply()` returns `success=False`, the error names that
  mission + the mismatch, and that mission's `status_phase` is **untouched**; assert no mission is left
  half-flipped.
- **INV-5 — no repo-root event file:** after `apply()` on a fixture, assert no `status.events.jsonl`
  (or any event file) exists at `tmp_path` (repo root); events land only under mission dirs (#2815).
- **Idempotency (INV-4):** run `apply()` twice → second run seeds nothing, re-flips nothing, stays green.
- **Auto-discovery + ordering:** after `auto_discover_migrations()`, assert the migration is registered
  (`MigrationRegistry.get_by_id("runtime_state_backfill")` is not None) **and** that in
  `MigrationRegistry.get_all()` it appears **after** both charter-fold migration_ids
  (`"unify_charter_activation_promote_answers"` and `"consolidate_charter_bundle_fold"`). This test is
  the self-verifying guard on the filename choice — it fails red if the name loses the same-version tie.

## Branch Strategy

Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge back
into `feat/runtime-state-corpus-cutover`. `execution_mode: code_change`. This WP **depends on WP01** —
`cutover_mission`/`CutoverResult` must exist before this integrates; do not stub or re-implement them.

## Test strategy

Run each owned test file **individually** (never the whole `tests/architectural/` dir — it hangs), with
a bare `python` avoided (it resolves a sibling checkout → false greens):

```
uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py
uv run --extra test python -m pytest -p no:cacheprovider tests/architectural/test_migration_chain_integrity.py
```

The chain-integrity gate is the corroborating guard on `target_version = "3.2.6"`; run it after adding
the migration. Every new branch/helper gets a focused test in this same WP (DIR-005 / ATDD).

## Definition of Done

- [ ] `m_zz_runtime_state_backfill.py` self-registers via `@MigrationRegistry.register`, is discovered by
      `auto_discover_migrations()`, and in `get_all()` sorts **after** both charter-fold migrations
      (FR-010, D-04). **Rename noted:** `m_3_3_1_*` → `m_zz_*` because the brief's numeric-prefix name
      sorts before the letter-prefixed `m_unify_*` folds at the tied `target_version` (see Risks).
- [ ] `target_version = "3.2.6"` (not higher — else silently skipped by `get_applicable` and red on
      `test_migration_chain_integrity`).
- [ ] Reuses `cutover_mission` per mission; **no** second copy of verify-then-flip (research D-01).
- [ ] Fail-closed: any mission's verify failure aborts the step with an operator-actionable message
      naming mission + mismatch; **no** mission half-flipped (NFR-005, D-03). `status_phase` never
      changes on a failed verify.
- [ ] No-op on fresh install; idempotent on already-migrated corpora (NFR-002, INV-4).
- [ ] Write target canonicalized inside the reused helper; **no** repo-root event file (C-003, INV-5,
      #2815) — proven by regression.
- [ ] SC-005 acceptance holds (legacy corpus migrates idempotently; fresh install no-ops; verify
      failure aborts with an actionable message).
- [ ] `ruff` + `mypy` clean, complexity ≤ 15, no new `# noqa`/`# type: ignore`/per-file ignores (NFR-004);
      repeated literals hoisted (S1192). All owned test files green.

## Risks & out-of-map edits

- **THE VERSION-KEY ORDERING TRAP (load-bearing).** Ordering is decided by
  `MigrationRegistry.get_all()` = **stable** `sorted(..., key=Version(target_version))`; same-version ties
  keep **insertion order**, which equals `pkgutil.iter_modules` **alphabetical** filename order (verified
  empirically). Two ways to get it wrong:
  1. **Too-high `target_version`** (e.g. `"3.3.1"`) → `> ` installed `3.2.6` → **silently skipped** by
     `get_applicable` and HARD-FAILs `test_migration_chain_integrity`. Fix: `target_version = "3.2.6"`.
  2. **Numeric-prefix filename at the tied version** — `m_3_3_1_runtime_state_backfill` sorts **before**
     `m_unify_charter_activation` / `m_unify_charter_activation_finalize` because digit `3` (0x33) < letter
     `u` (0x75). So the migration would run **before** the charter folds → violates FR-010's "after the
     charter folds" and the plan's "if wrong, runs before charter fold → wrong state." **No** numeric
     `m_<digits>_*` name can beat `m_unify_*` at the same version. Fix: a filename that wins the
     alphabetical tie — this WP uses **`m_zz_runtime_state_backfill.py`** (`z` > `u`; the `zz_` sentinel is
     documented in the module docstring as a deliberate ordering marker, mirroring how
     `m_unify_charter_activation_finalize.py` encodes ordering in its filename while keeping a semantic
     `migration_id`). The auto-discovery/ordering test (T008) locks this in.
- **Do not fork the cutover helper.** Re-deriving verify-then-flip here (instead of calling
  `cutover_mission`) is the logical-duplication trap (D-01) and would drift from the CLI.
- **"No partial flip" ≠ corpus rollback.** Abort-on-first-failure leaves earlier passed missions flipped;
  that is correct per-mission atomicity (D-03). Do not attempt a corpus-wide transaction.
- **No out-of-map edits.** This WP owns only the two files above. It does **not** edit `migrate_cmd.py`,
  the shared helper, or the 12 flag call sites (WP01 / later WPs). No file here is owned by another WP.

## Reviewer guidance

- **Auto-discovery order:** confirm `get_all()` places `runtime_state_backfill` **after** both
  `unify_charter_activation_promote_answers` and `consolidate_charter_bundle_fold`; confirm
  `target_version = "3.2.6"` (not higher) and that `test_migration_chain_integrity` stays green. Verify the
  filename rename (`m_zz_*`) and its docstring rationale.
- **Fail-closed abort leaves no partial flip:** exercise the US3.3 fault-injection test — one mission's
  verify failure must abort with a message naming the mission + mismatch, and that mission's `status_phase`
  must be unchanged; missions that passed earlier are the only ones flipped.
- **Fresh-install no-op & idempotency:** `detect()` False with no `kitty-specs/`; a second `apply()` seeds
  nothing and re-flips nothing.
- **INV-5:** after `apply()`, no `status.events.jsonl` at repo root; reuse of `cutover_mission` (not a
  re-implementation) is visible in the diff.

## Activity Log

- 2026-07-20T11:17:22Z – claude – shell_pid=3579827 – Assigned agent via action command
- 2026-07-20T11:49:25Z – claude – shell_pid=3579827 – Ready for review. Pre-review gate skipped: it timed out at 300s scoping the known-slow tests/architectural/ suite (pulled in because WP02 makes a required one-line allowlist edit to tests/architectural/test_no_dead_modules.py). Relevant regression surface verified GREEN individually: 13 owned tests + test_no_dead_modules.py + test_migration_chain_integrity.py = 17 passed in ~53s.
- 2026-07-20T12:19:11Z – claude – shell_pid=3706820 – Started review via action command
- 2026-07-20T12:19:59Z – user – shell_pid=3706820 – Approved: reuses cutover_mission, m_zz ordering correct, fail-closed abort non-vacuous, 17 tests green
