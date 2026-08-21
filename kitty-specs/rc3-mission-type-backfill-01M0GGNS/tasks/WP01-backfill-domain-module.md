---
work_package_id: WP01
title: Backfill domain module (backfill_mission_type.py)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
planning_base_branch: pr/rc3-mission-type-backfill
merge_target_branch: pr/rc3-mission-type-backfill
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-mission-type-backfill. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-mission-type-backfill unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-mission-type-backfill-01M0GGNS
base_commit: 43ed5e55c906dad75d0be378ae36b40bbc14786a
created_at: '2026-08-21T06:33:58.356898+00:00'
subtasks:
- T001
- T002
- T003
- T004
history: []
authoritative_surface: src/specify_cli/migration/backfill_mission_type.py
create_intent:
- src/specify_cli/migration/backfill_mission_type.py
- tests/specify_cli/migration/test_backfill_mission_type.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/backfill_mission_type.py
- tests/specify_cli/migration/test_backfill_mission_type.py
tags: []
tracker_refs: []
wp_code: WP01
---

# Work Package WP01 — Backfill domain module

## Objective

Create `src/specify_cli/migration/backfill_mission_type.py`: an idempotent, single-field
`meta.json` backfill that writes `mission_type` for legacy `mission`-only missions **whose value
resolves to a governance profile at any layer**. Structure it after the single-field sibling
`src/specify_cli/migration/backfill_topology.py` (NOT the two-dimension `backfill_identity.py`).

## Context & anchors (canonical sources — do not improvise)

- Canonicalizer: `charter.mission_type_key.canonical_mission_type_key` (strip-only; `None` for
  blank/absent; does `raw.strip()` → **requires** an `isinstance(raw, str)` guard upstream).
- Tolerance authority (operator decision B): `charter.mission_type_profile_repository
  .MissionTypeProfileRepository.for_project(repo_root).get(key)` — non-`None` iff a per-type
  `governance-profile.yaml` (id-matched) resolves at builtin/org/project layer. **Activation-
  independent** — this is why built-in types resolve on an unprovisioned repo.
- Reader: `load_meta_fail_closed` / `MissionMetaReadError` from `specify_cli.core.paths`.
- Dossier rehash: `specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled`
  (never raises; short-circuits when no project UUID). Lift the rehash pass from
  `backfill_identity._rehash_modified_missions` — `backfill_topology` has none.
- Do NOT copy topology's `routes_through_coordination`/`_coord_branch_exists` git probe.
- Do NOT import the CLI classifier (`_mission_type_audit`) — layer smell.

## Subtasks

### T001 — Skeleton
- Module docstring (single-field backfill; profile-resolution predicate; cites M3 §B authority).
- Constants: `MISSION_TYPE_KEY = "mission_type"`, `LEGACY_MISSION_KEY = "mission"`, reason strings
  (hoist any reason used ≥3× — Sonar S1192).
- `MissionTypeBackfillAction = Literal["wrote","skip","needs_manual_resolution","error"]`.
- `@dataclass MissionTypeBackfillResult`: `feature_dir, slug, action, mission_type=None,
  legacy_value=None, reason=None, dossier_warning=None`.

### T002 — Per-mission decision
- `_profile_resolves(repo, key) -> bool`: `repo.get(key) is not None`.
- `backfill_mission_mission_type(feature_dir, *, repo, dry_run=False)` under one broad
  `try/except Exception → error(str(exc))` (FR-005 — one bad mission never aborts the walk):
  1. no `meta.json` → `skip("meta.json not found")`
  2. `load_meta_fail_closed`; `MissionMetaReadError` → `error("corrupt json: …")`
  3. `MISSION_TYPE_KEY in meta` → `skip("mission_type already present")` (no write — AC-2a byte-identical)
  4. `raw = meta.get(LEGACY_MISSION_KEY)`; `not isinstance(raw, str)` or
     `canonical_mission_type_key(raw) is None` → `skip("no legacy mission value")` (AC-6 typeless-equiv)
  5. `key = canonical_mission_type_key(raw)`; `not _profile_resolves(repo, key)` →
     `needs_manual_resolution("no governance profile resolves for '<key>' at any layer")` (AC-4/R-4)
  6. resolves → if not dry_run: `meta[MISSION_TYPE_KEY] = key`; write canonical
     `json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"`. → `wrote` (AC-2b)

### T003 — Repo walk
- `backfill_mission_type_repo(repo_root, *, dry_run=False, mission_slug=None) -> list[...]`:
  build `MissionTypeProfileRepository.for_project(repo_root)` ONCE; sorted `kitty-specs/` walk;
  `mission_slug` given but no matching dir → **raise a structured error** (reuse
  `specify_cli.mission.MissionNotFoundError` or a small module-local error) — NOT
  `logger.warning(...); return []` (AC-9). After the walk, rehash `action=="wrote" and not dry_run`
  via `trigger_feature_dossier_sync_if_enabled`, capturing failures into `result.dossier_warning`.
- `__all__` per C-007.

### T004 — Red-first unit tests
`tests/specify_cli/migration/test_backfill_mission_type.py`, `pytestmark = [pytest.mark.unit, pytest.mark.fast]`.
Author each **red first** (assert it fails before the implementing subtask lands), realistic data
(real built-in types `software-dev`/`research`; a real typo `sofware-dev`):
- `test_resolving_candidates_all_written` (AC-1)
- `test_already_typed_mission_untouched_byte_identical` (AC-2a — compare bytes)
- `test_written_mission_gains_key_fields_preserved` (AC-2b — JSON-semantic equality)
- `test_idempotent_second_run_wrote_zero` (AC-3)
- `test_nonresolving_value_needs_manual_not_written` (AC-4)
- `test_non_string_legacy_value_not_candidate_no_crash` (AC-6 — `{"mission":123}`)
- `test_mixed_repo_partition` (AC-10 — ≥4 missions)
- `test_write_decision_matches_profile_repository` (R-4)

## Definition of Done

- All WP01 tests green, each demonstrably red before its subtask.
- `ruff check` + `mypy` clean (no new suppressions).
- Complexity ≤15 on every function.

## Terminal state

`done` when the above hold.

## Campsite / born-clean constraints (squad #3 Sonar census)

- **M3/m4 — topology one-return-per-outcome shape.** Follow `backfill_topology.py`'s straight-line
  `skip/error/needs_manual/wrote` early-returns; NEVER the `backfill_identity.py:190-195` reassigned-
  `action` ternary tangle (S3776). Drop topology's `routes_through_coordination`/`_coord_branch_exists`
  coord-probe block entirely (irrelevant to mission_type; keeps the per-mission fn ~CC 6-8).
- **m6 — canonical write parity.** Copy `_write_meta_canonical` byte-for-byte from `backfill_topology.py`
  (`json.dumps(..., indent=2, ensure_ascii=False, sort_keys=True) + "\n"`). Hoist `MISSION_TYPE_KEY`
  ("mission_type", ≥3 refs). Per-branch reason strings occur once each → leave inline (below S1192).
- **m5 REJECTED (rationale).** Do NOT add a `_VALID_MISSION_TYPES`-membership skip guard. M0's
  skip-if-already-typed is intentionally keyed on **`MISSION_TYPE_KEY in meta` (key presence)**, matching
  the audit's `legacy-key-only` boundary. A present-but-blank `mission_type` is the deferred/out-of-scope
  `typeless` case (spec Out of scope) — M0 must LEAVE it, not write over it. Value-validity is judged only
  for the LEGACY value, via the profile-resolution predicate.
- **m7 — no silent excepts.** The broad per-mission `except Exception → error(...)` is meaningful recovery
  (log + typed error result), mirroring the audit's `classify_mission_type`. Keep it; no bare/empty except.

## Added test coverage (squad #3 anti-laziness — B1/M1/M2/m1)

Add these named tests to T004 (each red-first):
- `test_corrupt_meta_classifies_error_walk_continues` (**B1/FR-005**): a repo with a corrupt
  `meta.json` **between** two resolving candidates → the corrupt one is `error`, BOTH neighbours are
  still processed (proves the broad-`except` doesn't abort the walk).
- `test_dossier_rehash_fires_on_wrote_not_dryrun_and_captures_warning` (**M1/R-1**): monkeypatch
  `trigger_feature_dossier_sync_if_enabled` (raising + non-raising) → assert it fires on
  `wrote ∧ ¬dry_run`, does NOT fire on `--dry-run`, and a raise is captured into `dossier_warning`
  without aborting.
- **M2**: `test_already_typed_..._byte_identical` MUST author its already-typed fixture in
  **non-canonical** form (unsorted keys / compact separators) so an accidental full rewrite would
  break the byte-compare (a canonical-form fixture makes the test vacuous).
- **m1**: `test_write_decision_matches_profile_repository` (R-4) fixture uses an
  **unactivated-but-resolving built-in** (bare temp repo → empty activation roster) so the
  profile-resolution-vs-`registered∧roster` distinction is proven WITHIN WP01, not only via WP03/AC-5.
