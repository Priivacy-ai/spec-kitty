# Contract — Gate & contract reconciliation (FR-003, FR-004, FR-008, FR-009, FR-010, FR-011, FR-012)

## C-GATE-1 — Coord-seed commit allow-listed on both gates (FR-008 + FR-012)

**Given** the coord-seed `safe_commit(target=CommitTarget(ref=coord_ref), …, capability=MERGE_BOOKKEEPING)` at `merge/executor.py:1053-1060`,
**Then** `test_no_write_side_rederivation` is green because `merge/executor.py` carries a tracked, dated allow-list entry,
**And** `test_guard_capability_call_sites[MERGE_BOOKKEEPING]` is green because `merge/executor.py` is in `_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]` with a rationale naming the merge coord-seed flow.
**Rationale (single, shared)**: best-effort coord-seed write of `status.events.jsonl` (STATUS_STATE → COORD) to the captured `pre_target_coord_ref`; must not abort the merge; STANDARD would refuse the protected coord destination; seam-routing would couple to merge-window resolvability. **Red-first**: the two tests are already red at `executor.py`.

## C-GATE-2 — `migration/` whole-tree carve-out narrowed (FR-003, FR-004)

**Then** `src/specify_cli/migration/` is removed from `BOUNDARY_SANCTIONED_PREFIXES` and every genuinely-sanctioned migration module (if any) is a per-file `BOUNDARY_SANCTIONED_MODULES` entry with an individual rationale; non-primitive modules fall back into scope,
**And** `src/mission_runtime/` and `src/specify_cli/upgrade/migrations/` prefixes are retained (C-002),
**And** SC-002/NFR-001 wording reads "any module in the `migration/` subtree" (not un-qualified); the merged deferral note (cited by anchor) reads "closed for `migration/`; `upgrade/migrations/` retained".
**Red-first**: a synthetic `CommitTarget`/`safe_commit` bypass added to a previously-carved-out `migration/` module reds the gate after narrowing.

## C-GATE-3 — Merge durably commits the status event log (FR-011)

**Given** a planning-artifact or mark-done merge,
**Then** the committed file-set includes `status.events.jsonl` alongside `meta.json`/`status.json` — greening `test_safe_commit_is_called_with_correct_files` and `test_planning_artifact_only_merge_does_not_require_mission_branch`.
**Judgment**: the tests encode the real FR-019/FR-020 durability invariant → fix the PRODUCT (the committed-set), not the test.

## C-CLI-1 — Raw mission-spec path routed/allow-listed (FR-009)

**Then** `mission_repair.py:65`'s `repo_root / KITTY_SPECS_DIR / mission` is either routed through the canonical mission-dir constructor OR `mission_repair.py` is a rationale-bearing entry in the `test_no_raw_mission_spec_paths` constructor allow-list — the gate is green.

## C-CLI-2 — Mission-CLI golden contract includes `repair` (FR-010)

**Then** `_EXPECTED_COMMANDS` includes `repair` (9), `_EXPECTED_FLAGS["repair"]` (and any `_EXPECTED_POSITIONALS["repair"]`) pin repair's flag/positional surface, the `test_app_exposes_exactly_eight_frozen_commands` test + docstring are renamed to the new count, and `cli-surface-contract.md` gains the `repair` row.
**Anti-fakeable**: adding `repair` to `_EXPECTED_COMMANDS` alone (greening the count while leaving the flag surface unverified) does NOT satisfy this contract.
