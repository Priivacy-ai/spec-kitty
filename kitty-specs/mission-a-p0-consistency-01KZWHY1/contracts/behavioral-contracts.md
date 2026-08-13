# Behavioral Contracts — Mission A

Four observable contracts. Each is pinned by a red-first reproduction (existing or
replaced) plus the mandatory green-wash guard tests. These are behavior contracts,
not HTTP APIs — the mission adds no endpoints.

**Regression-exit (NFR-005/SC-006), applies to all four:** when a reproduction
turns green, its WP relocates it to the functional-slice home named below (or, for
#3334, lands the replacement there), drops `@pytest.mark.regression`, adds the
canonical `unit`/`integration` marks + a guard docstring, so that at mission
completion `pytest tests/ -m regression` shows **none** of the four green.

## C#3320 — Retrospect `--update` agrees with disk

- **Given** an on-disk retrospective record `has_findings` with 1 gap, **when**
  `retrospect create --update --json` runs with a generator yielding
  `ran_no_findings`, **then** reported `findings_status == "has_findings"` and
  `counts.gaps == 1`, **and** the emitted `RetrospectiveCaptured` event carries
  the same merged record.
- **Invariant**: report ≡ event ≡ persisted file, for `--update`. `--overwrite`/
  `error`/backfill unchanged. `write_gen_record` return type unchanged.
- **Tests**: `tests/regression/test_issue_3320_*` (JSON) → on green, relocate to
  `tests/cli/commands/`; **+ new**: patch `emit_captured` with a **spy** and
  assert the captured event's `findings_status`/gap-count equal the values **read
  back from `record_path` on disk** (not the reported JSON — both could be
  wrong-and-equal; not the repro's `emit_captured→None` patch).

## C#3231 — A scaffold placeholder cannot flip acceptance

- **Given** a matrix whose real criteria are all `pass` plus the empty `AC-001`
  placeholder (`description == SCAFFOLD_TODO_MARKER`), **when** `overall_verdict`
  is computed, **then** it is not `pending`.
- **Given** a matrix with a seeded FR row still `pending` (marker in `notes`,
  real `description`), **or** an all-scaffold matrix, **then** `overall_verdict`
  is `pending`.
- **Invariant**: only the contentless empty placeholder is verdict-exempt; a
  seeded-but-unauthored requirement always blocks; an un-authored matrix never
  reads `pass`.
- **Tests**: `tests/regression/test_issue_3231_*` (empty-placeholder+all-pass) →
  on green relocate to `tests/acceptance/`; **+ new (non-fakeable)**:
  partial-authoring (9/10 FR `pending`)→pending; single-row empty-`AC-001`-only
  →pending (the "no non-scaffold criterion" branch); **single REAL `AC-001` (real
  `description`, `pending`, no marker)→pending** (defeats a `criterion_id=="AC-001"`
  shortcut, pins the `description` discriminator).

## C#3334 — A failed upgrade leaves a recoverable project

- **Given** a healthy schema-3 project (`schema_version: 3`, version behind, 3.x
  `success` history), **when** `MigrationRunner.upgrade(target)` hits a failing
  migration, **then** `get_project_schema_version() == 3` afterward (not `None`),
  **and** the real startup gate `check_schema_version(project_root, "plan")` does
  not raise `SystemExit`.
- **Given** a genuinely pre-3.x project (`schema_version` absent, no 3.x `success`
  history), **when** the gate runs for an unsafe command, **then** it classifies
  `LEGACY` and raises `SystemExit(4)`.
- **Invariant**: `ProjectMetadata` round-trips `schema_version` (root fix,
  C-008) so no `save()` caller strips it; a failed upgrade is non-destructive to
  the stamp; the genuine-pre-3.x `LEGACY` guard is unchanged; the classifier
  (`planner.py`, `safety.py`) is untouched.
- **Tests (non-fakeable — renata)**: **replace** `tests/regression/test_issue_3334_*`
  (same PR as the fix; it perma-reds NFR-001 otherwise) — drive real
  `MigrationRunner.upgrade()` (stub failing migration via `MigrationRegistry`),
  fixture `schema_version` **present** + version behind + 3.x `success` history.
  Assert: (1) post-failure `schema_version == the captured pre_schema`, using a
  **non-`REQUIRED` (STALE, `< min_supported`)** fixture value — `== 3` alone is
  faked by always-stamp-`REQUIRED`; (2) real gate no `SystemExit`; (3)
  `upgrade(dry_run=True)` against the failing migration leaves `metadata.yaml`
  **byte-identical**; (4) genuine pre-3.x still `LEGACY` + `SystemExit(4)`.
  **+ direct unit test**: `ProjectMetadata` round-trips `schema_version` through
  load→save (the root-fix guard — a `save()` after load preserves the on-disk
  value; the `_mask_volatile_metadata` change does not re-mask a real change).

## C#3311 — Re-finalize after execution preserves provenance

- **Given** a mission with materialized lanes, a recorded `planning_commit_sha`,
  and ≥1 WP past `planned` in the status event log, **when** `finalize-tasks`
  re-runs after an ownership-only `owned_files` amendment, **then**
  `planning_commit_sha` is preserved (or the run refuses before writing) — even
  when the current branch tip differs (non-`None`).
- **Given** a mission with all WPs at `planned` (no execution begun), **when**
  `finalize-tasks` re-runs, **then** lanes regenerate and the run does not refuse.
- **Invariant**: preserve/refuse triggers on execution-state via the resolved
  coord-aware surface (`resolve_status_surface_with_anchor().read_dir` →
  `has_event_log` guard → `get_all_wp_lanes`; never `reducer.materialize()`),
  never on `lanes.json`/`planning_commit_sha` presence; single-write provenance
  freeze (ADR 2026-07-29-1/FR-009) preserved.
- **Tests (non-fakeable — renata)**: `tests/regression/test_issue_3311_*`
  (None-tip) → on green relocate to `tests/specify_cli/cli/commands/agent/`;
  **+ new**: (a) non-`None`-tip preservation (branch-tip differs, SHA still
  preserved); (b) **benign pre-execution re-finalize must assert regeneration
  actually ran** — make the `owned_files` amendment observable and assert the
  regenerated `lanes.json` reflects it (two lanes union into one) or
  `planning_commit_sha` re-captured to the new tip; "did not refuse" alone is
  faked by an always-preserve impl.
