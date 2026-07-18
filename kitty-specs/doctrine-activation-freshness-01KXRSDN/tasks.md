# Tasks — Doctrine-activation freshness integrity

Mission: `doctrine-activation-freshness-01KXRSDN` | Branch: `feat/doctrine-activation-freshness` (coord topology)
Plan: [plan.md](./plan.md) — 5-concern ICM. DAG: `WP01 ∥ (WP02 → WP03 → {WP04, WP05})`.

> **Tasks-time scope refinement (verified live 2026-07-17):** `spec-kitty doctrine regenerate-graph --check`
> is **fresh** and the 4 #2770 tests **pass** on this branch — S-C's landing fold already regenerated the
> graph + wired the citation + set the baseline `289/765/11`. So **WP01 is the durable un-pin only**
> (remove the 4 #2770-tied `@regression` markers, re-arm the gate), not a regeneration.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Remove the 2 #2770 `@regression` markers + stale comments in `test_extractor_projection.py` (TestDRGZeroDelta); confirm baseline 289/765/11 still matches a fresh regen | WP01 | | [D] |
| T002 | Remove the #2770 `@regression` marker + comment in `test_doctrine_regenerate_graph.py::test_check_reports_committed_graph_fresh` | WP01 | [D] |
| T003 | Remove the #2770 `@regression` marker + comment in `test_charter_references_resolve.py::test_no_new_charter_reference_danglers` | WP01 | [D] |
| T004 | Verify: `regenerate-graph --check` green + the 4 tests pass as ordinary tests + the regression-visibility gate is clean (no other issue's markers touched) | WP01 | | [D] |
| T005 | Red-first: repro a synced-but-not-generated project (references.yaml absent) → permanent-stale dead-end `None` through the freshness/synthesize path | WP02 | | [D] |
| T006 | Add the fail-closed preflight: on missing `references.yaml`, surface one actionable "run `charter generate` first" (hoisted message constant) — KEEP the 4-file hash (no narrowing) | WP02 | | [D] |
| T007 | Tests: missing-references fail-closed message; a COMPLETE bundle's `compute_bundle_content_hash` is byte-unchanged (NFR-002) | WP02 | | [D] |
| T008 | Gate WP02: `tests/charter/` green; ruff + mypy --strict clean; complexity ≤15 | WP02 | | [D] |
| T009 | Red-first: on a fresh project, `charter activate <kind> <id>` → `_compute_synthesized_drg` reports STALE (currently fresh) — SC-002 e2e | WP03 | | [D] |
| T010 | Campsite: pre-extract `consistency_check.py:_check_reference_id_parity` sub-checks (complexity 12) + extract `computer.py:_compute_synthesized_drg` built_in_only branch + hash-compare tail (stay ≤15/≤6 returns) | WP03 | | [D] |
| T011 | Wire `run_consistency_check` into `_compute_synthesized_drg` (read-path parity; writer-agnostic; compose with content-identity; PRESERVE fresh-seed early-exit) | WP03 | | [D] |
| T012 | Tests: SC-002 activate→stale→reconcile→fresh; `merge_defaults`-seeded visibility; deactivate symmetric; NFR-002 unchanged-bundle→unchanged-hash preserve | WP03 | | [D] |
| T013 | Gate WP03: `tests/specify_cli/charter_runtime/` + `tests/charter/` green; ruff + mypy --strict clean; complexity ≤15; `commit_plan` untouched (C-001) | WP03 | | [D] |
| T014 | Red-first: multiple charter-owed prerequisites stale → implement preflight raises on the FIRST (repro the one-at-a-time bounce) | WP04 | |
| T015 | Extend `_attempt_auto_refresh` to compute + report the full charter-owed owed-set in ONE pass (additive; per-prerequisite verdicts UNCHANGED); campsite: hoist the `["spec-kitty","charter",…]` prefix (×3) | WP04 | |
| T016 | Tests: one-pass report; verdicts unchanged; C-004 fence (`analysis_report` untouched); ruff + mypy --strict clean | WP04 | |
| T017 | Red-first: NFR-001 subprocess/call-count spy — assert default `charter activate` performs NO synthesis/regenerate (the target behavior) | WP05 | |
| T018 | Add `--resynthesize` to `charter activate` + `deactivate` (eager synthesize orchestration in the specify_cli CLI; `commit_plan` untouched — C-001) | WP05 | |
| T019 | Tests: `--resynthesize`→FRESH immediately; default→STALE + ZERO synthesis subprocess (NFR-001 spy); NFR-003 migration + `org_charter` `promote_activations` no-synthesis | WP05 | |
| T020 | Gate WP05: `tests/specify_cli/cli/commands/charter/` green; ruff + mypy --strict clean; complexity ≤15 | WP05 | |

## Work Packages

### WP01 — #2770 durable un-pin (EARLY / STANDALONE, release-sensitive)
- **Goal**: Re-arm the gate — remove the 4 #2770-tied `@regression` markers so the (already-fresh) DRG-staleness tests pass as ordinary, blocking tests. FR-004, SC-001, NFR-004.
- **Priority**: P1 (release-sensitive; lands first, independent of the seam).
- **Independent test**: `regenerate-graph --check` green + the 4 tests pass with no `@regression` marker; no other issue's markers changed.
- **Dependencies**: none.
- **Subtasks**: T001, T002, T003, T004. **Est. ~180 lines.**

### WP02 — #2758 references.yaml fail-closed preflight
- **Goal**: Kill the permanent-stale `None`; missing `references.yaml` → actionable "run `charter generate`". FR-005, SC-003. Q1 = fail-closed (keep 4-file hash).
- **Priority**: P2. **Dependencies**: none (parallel WP01; before WP03).
- **Independent test**: synced-but-not-generated project fails closed with the actionable message; complete-bundle hash byte-unchanged.
- **Subtasks**: T005, T006, T007, T008. **Est. ~260 lines.**

### WP03 — #2759 seam core: parity into the freshness read-path
- **Goal**: Make config-activation visible — wire `run_consistency_check` into `_compute_synthesized_drg` so a config↔derived mismatch reports STALE by construction (writer-agnostic). FR-001/002/003, SC-002, NFR-002.
- **Priority**: P1 (seam core). **Dependencies**: WP02.
- **Independent test**: fresh project, `charter activate` → signal STALE; reconcile → FRESH; `merge_defaults`-seeded activation also visible; unchanged bundle → unchanged hash.
- **Subtasks**: T009, T010, T011, T012, T013. **Est. ~340 lines.**

### WP04 — #2157a one-pass prerequisite gate
- **Goal**: Report all charter-owed prerequisites in one pass, not raise-on-first. FR-006, SC-004.
- **Priority**: P2. **Dependencies**: WP03.
- **Independent test**: multiple stale prerequisites → single-pass report; per-verdict values unchanged; `analysis_report` (2157b) untouched.
- **Subtasks**: T014, T015, T016. **Est. ~200 lines.**

### WP05 — `--resynthesize` opt-in + hot-path guards
- **Goal**: Eager-refresh escape hatch; prove the default path stays cheap. FR-007, NFR-001, NFR-003.
- **Priority**: P3. **Dependencies**: WP03.
- **Independent test**: `--resynthesize`→FRESH now; default→STALE + zero synthesis subprocess (spy); migration path no-synthesis.
- **Subtasks**: T017, T018, T019, T020. **Est. ~250 lines.**

## Dependencies

```
WP01 (none, early standalone)
WP02 (none) → WP03 (WP02) → WP04 (WP03)
                          → WP05 (WP03)
```

## Follow-ups (file at close)
- #2760 (upgrade⇒overlay-revalidation → #2721); #2157b (analyzer-freshness); #2773 coordination (references.yaml deprecation — WP02 deliberately avoids a stopgap); broader #2519 authoring/init; step-model Family 2.
