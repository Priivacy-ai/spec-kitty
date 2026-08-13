---
work_package_id: WP03
title: '#3334 — failed upgrade recoverability via ProjectMetadata schema_version round-trip'
dependencies: []
requirement_refs:
- FR-005
- FR-006
planning_base_branch: fix/mission-a-p0-consistency
merge_target_branch: fix/mission-a-p0-consistency
branch_strategy: Planning artifacts for this mission were generated on fix/mission-a-p0-consistency. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-a-p0-consistency unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-a-p0-consistency-01KZWHY1
base_commit: bdc442171205cd4cedf3bf675aa4aedf9fd40501
created_at: '2026-08-13T04:31:46.072369+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
history:
- Created by /spec-kitty.tasks for mission-a-p0-consistency-01KZWHY1
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/
create_intent:
- tests/upgrade/test_metadata_schema_roundtrip.py
- tests/upgrade/test_failed_upgrade_recoverable.py
execution_mode: code_change
owned_files:
- src/specify_cli/upgrade/metadata.py
- src/specify_cli/upgrade/runner.py
- tests/upgrade/test_metadata_schema_roundtrip.py
- tests/upgrade/test_failed_upgrade_recoverable.py
- tests/regression/test_issue_3334_failed_upgrade_wedges_repair.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile: `/ad-hoc-profile-load python-pedro` and apply it. You are an **implementer**.

## Objective

A failed `spec-kitty upgrade` strips `schema_version` from `.kittify/metadata.yaml`,
wedging the project into `LEGACY` classification (exit 4) with no forward path. Fix
the **root cause**: make `ProjectMetadata` round-trip `schema_version` through
load→save so **no `save()` caller** can strip it. This closes the wedge at its source
and **subsumes** the earlier minimal runner restore-on-failure idea.

## Context (root cause — traced live)

- `ProjectMetadata.save()` (`metadata.py:188-210`) rebuilds YAML from a model with **no** `schema_version` field; `load()` (`:126`) ignores it. It survives only via a separate `_stamp_schema_version`.
- Failure path: `_apply_migration` records the migration `"failed"` → `metadata.save()` (`runner.py:487-489`/`288`) → strips `schema_version` (the failed record changes `migrations.applied` so the masked compare-before-write, `:227`, fires a real write). The restoring re-stamp (`runner.py:189-190`) is gated behind `if not dry_run and result.success:` (`:181`) → skipped.
- Re-run: `has_migration()` ignores `failed` records (`:242`) → the migration re-fails → restore never reached: self-perpetuating.
- Exit-4 surfaces via startup gate (`migration/gate.py:146-154`, wired `__init__.py:140`) and via `upgrade --json --project` (`upgrade.py:688`,`1136-1163`).

## Constraints

- **C-008 (root fix, in scope)**: `ProjectMetadata` round-trips `spec_kitty.schema_version` (load reads into a model field; save writes it back); drop the `schema_version` entry from `_mask_volatile_metadata` (`:23-47`) so a legitimate stamp change is not masked away.
- **C-004**: do NOT touch `compat/planner.py` or `safety.py` (the classifier is a faithful reader). Keep UNSAFE mutating commands blocked on a genuinely schema-less project.
- Keep the success-path advance to `REQUIRED_SCHEMA_VERSION` (`runner.py:189-190`) and `dry_run`-writes-nothing. Keep the second schema writer `migration/runner.py:193` `_update_schema_version` (ruamel in-place, already non-stripping) consistent — verify, edit only if needed for consistency (record a one-line rationale if you edit outside `owned_files`).

## Subtasks

### T009 — ProjectMetadata round-trips schema_version

Add a `schema_version: int | None` field to `ProjectMetadata`; populate it in `load()`
(`:120-134`) from `spec_kitty.get("schema_version")`; write it back in `save()` (`:188-210`)
into the `spec_kitty` block when not `None`. Remove the `schema_version` special-case
from `_mask_volatile_metadata` (`:23-47`). Ensure `None` (genuine pre-3.x) writes no
`schema_version` key (stays `None` → `LEGACY`).

### T010 — Preserve success-path + dry_run semantics

Verify `MigrationRunner.upgrade()` still advances the stamp to `REQUIRED_SCHEMA_VERSION`
on success (via the existing `_stamp_schema_version`, kept consistent with the model),
and that `dry_run` writes nothing (`_stamp_schema_version` at `runner.py:493` writes raw
YAML — confirm it is not reached in dry_run). Verify `migration/runner.py:193`
`_update_schema_version` stays consistent with the new round-trip semantics. **Pin the
success path** (renata): add or name a test asserting a *successful* upgrade advances
`schema_version` to `REQUIRED_SCHEMA_VERSION` (the mask-entry drop + `save()` change could
regress it — do not leave the success-path bump self-certified by "suite green" alone).

### T011 — Round-trip unit test [P]

`tests/upgrade/test_metadata_schema_roundtrip.py`: load a `metadata.yaml` with
`schema_version: N`, call `save()` after a material change (e.g. append a migration
record), assert the on-disk `schema_version` is still `N` (not dropped). Assert the
`_mask_volatile_metadata` change does not re-mask a legitimate schema change.

### T012 — REPLACE the #3334 repro (non-fakeable)

Delete/replace `tests/regression/test_issue_3334_failed_upgrade_wedges_repair.py`
(it pins the wrong classifier contract → perma-red under this fix) with
`tests/upgrade/test_failed_upgrade_recoverable.py` (canonical marks, guard docstring).
Drive the **real** `MigrationRunner(project_path).upgrade(target)` (or `upgrade` via
`CliRunner`) with a stub failing migration injected into `MigrationRegistry`.
**Injection mechanism (feasibility — copy the sibling)**: follow
`tests/upgrade/test_upgrade_worktree_commit.py:198-229` — `MigrationRegistry.clear()`
then `@MigrationRegistry.register` on a `class _StubMigration(BaseMigration)` declaring
the REQUIRED_FIELDS (`migration_id`, `description`, `target_version` — `registry.py:19`)
with `apply(self, project_path, dry_run=False) -> MigrationResult` returning
`MigrationResult(success=False, ...)` (`migrations/base.py`). Global `_migrations` state
is saved/restored by the autouse fixture `tests/upgrade/conftest.py:29-36` — no manual
teardown. **Version-window (the real trap)**: `MigrationRegistry.get_applicable` selects
a migration only when `from_v < Version(target_version) <= to_v`, so wire the fixture's
behind-`version` and the stub's `target_version` so the stub is actually selected — else
the failing migration never runs and the repro is vacuous.
Fixture starts with `schema_version` **present at a STALE value (`< min_supported`, non-`REQUIRED`)**
+ version behind + 3.x `success` history. Assert:
1. post-failure `get_project_schema_version() == the STALE pre-value` (a hardcoded `==3`/`==REQUIRED` is fakeable — this pins "preserve", not "constant");
2. real gate `check_schema_version(project_root, "plan")` does **not** raise `SystemExit`;
3. `upgrade(dry_run=True)` against the failing migration leaves `metadata.yaml` **byte-identical**;
4. negative guard — genuine pre-3.x (no `schema_version`, no 3.x history) still `LEGACY` + `SystemExit(4)`.

### T013 — Gates

`ruff`/`mypy` clean. `PWHEADLESS=1 .venv/bin/python -m pytest tests/upgrade/ -q` +
the compat gate suite. No green `regression`-marked #3334 test remains (the repro is replaced).

## Branch Strategy

Planning base + merge target: `fix/mission-a-p0-consistency`. Worktree is per-lane from
`lanes.json`. Implement via `spec-kitty agent action implement WP03 --agent claude`.

## Definition of Done

- [ ] `ProjectMetadata` round-trips `schema_version`; `_mask_volatile_metadata` entry dropped.
- [ ] Success-path bump + `dry_run`-writes-nothing preserved; second writer consistent.
- [ ] Round-trip unit test (T011) + replacement recoverability repro with all 4 post-conditions (T012).
- [ ] `compat/planner.py`/`safety.py` untouched; genuine pre-3.x stays blocked.
- [ ] `ruff`/`mypy` clean; upgrade suite green; no green `regression`-marked #3334 test.

## Risks / Reviewer guidance

- Reviewer: confirm assertion (1) uses a **STALE** fixture value, not `REQUIRED`/3 — the load-bearing non-fakeable check.
- Confirm the masked-compare change doesn't reintroduce churn or skip a legitimate write.
- This WP partially closes **Epic #3347** (see its comment `5275734966`); the broader atomicity work stays in #3347.
