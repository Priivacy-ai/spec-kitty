# Tasks: Runtime-State Corpus Cutover

**Mission**: `runtime-state-corpus-cutover-01KXZ0AX` · **Branch**: `feat/runtime-state-corpus-cutover`
**Input**: [spec.md](./spec.md) (16 FR / 6 NFR / 11 C / US1–US6 / SC-001–011), [plan.md](./plan.md) (IC-01…IC-10 + IC-08a),
[research.md](./research.md) (D-01…D-14), [data-model.md](./data-model.md) (INV-1…INV-8),
[contracts/cutover-cli.md](./contracts/cutover-cli.md), [contracts/resolved-binding.md](./contracts/resolved-binding.md).

> **Concerns are not work packages.** This file translates the plan's 11 implementation concerns into 13 WPs.
> The **contract order (C-001)** is the hard spine — never delete a fallback before backfill is wired+verified.
> Two **merge-unit atomicity** constraints are baked into the dependency edges (see Dependency Graph):
> `WP03(IC-01b) → WP04(IC-03) → WP05(IC-04)` land as one unit; `WP10(IC-08 re-seed) → WP11(IC-07)` land as one unit.

## Execution & test discipline (binding — from HANDOVER + research D)

- Tests: `uv run --extra test python -m pytest -p no:cacheprovider <FILE>` — bare `python` resolves a sibling
  checkout → false greens. **Never** run the whole `tests/architectural/` directory (it hangs) — per-file + timeout.
- No suppression to pass gates (NFR-004): no new blanket `# noqa` / `# type: ignore` / per-file ignores; `ruff` + `mypy`
  clean; complexity ≤15. Every new branch/helper gets a focused test in the same WP (ATDD, C-011).
- All event writes resolve via `canonicalize_feature_dir` — no repo-root `status.events.jsonl` (INV-5 / #2815 / C-003).
- Pre-existing reds are NOT ours: the phantom `SYNC_DISABLE_ENV_VARS` `arch-adversarial` red + the ADR-2026-07-17-1
  known-P0s (#2736/#2772/#1834). Confirm on the merge-base before attributing any red to this diff.
- **Extreme campsite-cleaning (D-14, binding):** two forced tidy-firsts (`reducer._apply_annotation_delta`,
  `scanner._process_wp_file`); god-modules surgical-ONLY; hoist repeated literals (S1192); delete orphan flag-wrappers.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `migration/runtime_state_cutover.py` (`cutover_mission`: seed→verify→atomic flip, cx≤15, `CutoverResult`) | WP01 | | [D] | [D] | [D] |
| T002 | Add `migrate backfill-runtime-state` CLI (`--dry-run`/`--mission`/corpus default; per-mission best-effort exit) | WP01 | | [D] |
| T003 | Sole `status_phase` writer; refuse-to-flip on non-ok verify; write target via `canonicalize_feature_dir` | WP01 | | [D] |
| T004 | Remove 15-symbol `_CATEGORY_C_DEFERRED_RUNTIME_STATE_BACKFILL_CUTOVER` frozenset (first caller wired, C-006) | WP01 | | [D] |
| T005 | Tests: helper phases, fault-injection abort/refuse-to-flip, dry-run counts, idempotent, INV-5 guard, US1 | WP01 | | [D] |
| T006 | Create auto-discovered `upgrade/migrations/m_<version>_runtime_state_backfill.py` (reuses helper) | WP02 | [D] |
| T007 | Fail-closed abort on any mission verify failure (NFR-005); no-op fresh install; idempotent | WP02 | [D] |
| T008 | Tests: legacy migrate+verify+flip; fresh no-op; verify-fail aborts+actionable+no partial flip; US3 | WP02 | [D] |
| T009 | Dry-run backfill over this repo's `kitty-specs/`; capture per-mission would-seed counts | WP03 | [D] |
| T010 | Real run: seed events + flip `status_phase` for every passing mission; corpus-wide verify `ok` | WP03 | [D] |
| T011 | Commit seed-event deltas (`kitty-specs/**/status.events.jsonl`) + `status_phase` flips (`**/meta.json`) | WP03 | [D] |
| T012 | Acceptance: `wp_snapshot_state` non-empty per runtime-carrying mission; sample done-mission proof; idempotent | WP03 | [D] |
| T013 | Delete `_phase1_snapshot_authority_active` + facade alias/`__all__`; KEEP `_legacy_lane_mirror_enabled` (C-004) | WP04 | | [D] |
| T014 | Collapse flag-OFF branch at 12 call sites / 11 files (heterogeneous; drop paired imports + orphan wrappers) | WP04 | | [D] |
| T015 | Writer cutover (NFR-003): stop `write_shell_pid_claim` + template emitters writing runtime to `tasks/WP##.md` | WP04 | | [D] |
| T016 | Lane-mirror regression: `status_phase 0→1` activates mirror — assert lane behaviour unchanged (C-004) | WP04 | | [D] |
| T017 | Tests: byte-stability (0 bytes on transition), predicate-gone grep (SC-002), 12-site behavior, lane mirror | WP04 | | [D] |
| T018 | Build event-sourced done-evidence read from snapshot `review` slot (`done_bookkeeping`) BEFORE deleting synth | WP05 | | [D] |
| T019 | `workflow_cores.resolve_review_feedback_context`: delete verdict/review fallback + route bypass (ONE block); narrow `except` | WP05 | | [D] |
| T020 | Delete `done_bookkeeping._extract_done_evidence` frontmatter synth + dead `frontmatter-migration:` branch | WP05 | | [D] |
| T021 | Route `tasks_move_task` ownership read onto snapshot accessor (extract, `_mt_emit_runtime_state` at cx15) | WP05 | | [D] |
| T022 | Route `dashboard/scanner._process_wp_file` runtime reads onto snapshot; surface-sweep stale_detection/ownership/resolver | WP05 | | [D] |
| T023 | Tests: event-only mission → correct DoneEvidence via merge path; bypass readers snapshot-sourced | WP05 | | [D] |
| T024 | `test_2093`: `_SANCTIONED_READER_MODULES`→`frozenset()`; rewrite vacuous gate-identity arm | WP06 | | [D] |
| T025 | EXTEND detector to attribute-access reads; prove it flags dashboard scanner RED pre-reroute (SC-009, non-vacuous) | WP06 | | [D] |
| T026 | Reconcile ~33-file flag-ON/flag-OFF split suite (delete `_flag_off` twins, unconditional assertions, compat surface) | WP06 | | [D] |
| T027 | Regenerate baselines (`fast-tests-core-misc-nodeids.txt` + gate-coverage) via `--update-baseline`/`--freeze-baselines` | WP06 | | [D] |
| T028 | Add NFR-003 byte-stability regression + #2815 repo-root-write guard (if not already in WP01/02) | WP06 | | [D] |
| T029 | Remove inert `wp_metadata` runtime fields + cosmetic `WP_FIELD_ORDER` slots; keep `status_phase` OUT of bounds | WP07 | | [D] |
| T030 | `assert_zero_readers` proof before removal; full suite green | WP07 | | [D] |
| T031 | Author field-authority ADR (addendum to `2026-07-19-1` B4): resolved role/profile/model→dynamic; authored→static (C-009) | WP08 | | [D] |
| T032 | Add `authored intent`/`resolved binding` to `docs/context/identity.md`; run terminology guard + docs-freshness | WP08 | | [D] |
| T033 | Data-drive `WPInnerStateDelta` (collapse `is_empty`/`to_dict`/`from_dict` triple-enum) then add resolved slots | WP09 | | [D] |
| T034 | Tidy-first: extract `reducer._apply_annotation_delta` if-chain → data-driven replace-slot table (cx13→≤15) | WP09 | | [D] |
| T035 | Add resolved slots to `_RUNTIME_SLOTS` + `_apply_annotation_delta` (latest-wins) | WP09 | | [D] |
| T036 | Tests: reducer folds resolved slots latest-wins; delta round-trip; is_empty | WP09 | | [D] |
| T037 | Thread resolved model+profile(+invocation_id) into implement/review commands from `invocation/executor` (C-007) | WP10 | | [D] |
| T038 | Consume at claim seams (implement+review claim) + `tasks_move_task` reassign; explicitly-absent when unavailable (SC-011) | WP10 | | [D] |
| T039 | Emit binding as `InnerStateChanged` annotation (latest-wins both claims) + enrich `actor` via helper (no NOSONAR inflate) | WP10 | | [D] |
| T040 | Enforce ADR provenance: historical backfill never copies authored recommendations into resolved actuals (C-011) | WP10 | | [D] |
| T041 | Scrub deterministic authored-derived binding seeds by exact ID; preserve live annotations and stale snapshot bytes | WP10 | | [D] |
| T042 | Tests: resolved from resolver not frontmatter (INV-6); latest-wins implement→review; explicitly-absent path | WP10 | | [D] |
| T043 | Create `status/wp_view.py::reconstruct_wp_view` — resolved (snapshot) + authored (frontmatter, distinct); tolerate-absent | WP11 | [D] |
| T044 | Tidy-first: extract `scanner._process_wp_file` runtime-view helper backed by the reader (cx13→≤15); identity/runtime only | WP11 | [D] |
| T045 | Reroute all 4 gates onto the reader (scanner, `tasks_status_cmd` board, `WorkPackage`); subtasks from snapshot slot | WP11 | [D] |
| T046 | Tests: 3 consumers agree (SC-007); implement→review shows current actual (SC-008); never-reclaimed → resolved empty | WP11 | [D] |
| T047 | Widen `actor` to `str\|dict` (`StatusEvent`, `build_status_event`, `emit_status_transition`); guard `from_dict` coercions | WP12 | [D] |
| T048 | Enrich `actor` `{role,profile,tool,model}` on claim/review `StatusEvent` + `_saas_fan_out`; feature-detect dict | WP12 | [D] |
| T049 | Version-gated `WPResolvedBindingChanged` fallback scaffold (`hasattr` gate, genesis-lane pattern); local-first | WP12 | [D] |
| T050 | Tests: dict actor round-trips JSONL; fan-out carries resolved binding; older pkg → skip+log, local unaffected | WP12 | [D] |
| T051 | Reroute lane-transition guard (`core/subtask_rows.py`) + dashboard checkbox count onto snapshot `subtasks` slot | WP13 | | [D] |
| T052 | Remove `- [ ] T###` checkboxes from templates + this tasks.md (AFTER seed, C-010); update SOURCE doctrine templates → `mark-status` | WP13 | | [D] |
| T053 | Run terminology guard + docs-freshness after prose edits | WP13 | | [D] |
| T054 | Tests: guard blocks/unblocks off snapshot; dashboard reads snapshot subtasks; no checkbox remains (SC-010) | WP13 | | [D] |

---

## Phase 1 — Fail-closed cutover (US1–US5)

### WP01 — Cutover orchestration helper + operator CLI (IC-01)

- **Goal**: An invocable, fail-closed cutover entry point — seed → verify(count+value) → flip `status_phase` **only** on pass.
- **Priority**: P1 (spine first step; the load-bearing safety mechanism). **Dependencies**: none.
- **Independent test**: dry-run reports would-seed counts & writes nothing; real run seeds+verifies+flips only passers;
  fault-injected corrupt seed aborts before any flip; re-run idempotent. No `status.events.jsonl` at repo root.
- **Subtasks**: [ ] T001 [ ] T002 [ ] T003 [ ] T004 [ ] T005
- **Prompt**: [tasks/WP01-cutover-helper-cli.md](./tasks/WP01-cutover-helper-cli.md) · ~320 lines · FR-001/2/3, C-003/006, NFR-001/2/6

### WP02 — Upgrade-path migration (IC-02)

- **Goal**: Existing deployments migrate their corpus on `spec-kitty upgrade` (auto-discovered, fail-closed, idempotent).
- **Priority**: P2. **Dependencies**: WP01 (reuses the shared `cutover_mission` helper — do NOT fork verify-then-flip).
- **Independent test**: legacy corpus migrates+verifies+flips; fresh install no-ops; verify-fail aborts the step with an
  actionable message and no partial flip.
- **Subtasks**: [ ] T006 [ ] T007 [ ] T008
- **Prompt**: [tasks/WP02-upgrade-migration.md](./tasks/WP02-upgrade-migration.md) · ~230 lines · FR-010, NFR-005, C-003

### WP03 — Execute dogfood corpus backfill + commit seeds (IC-01b, BLOCKER-fix)

- **Goal**: RUN the backfill over **this repo's** `kitty-specs/` and **commit** the seeds+flips so IC-03's unconditional
  readers see a populated snapshot (else every dogfood mission reads empty → red). Owns the contract's *execution* step.
- **Priority**: P1 (BLOCKER). **Dependencies**: WP01. **Merge unit** with WP04/WP05.
- **Independent test**: post-run `wp_snapshot_state` non-empty for every runtime-carrying mission; corpus-wide verify `ok`;
  a sampled done-mission's `_infer_subtasks_complete` correct with the predicate deleted (local IC-03 dry-run); idempotent.
- **Subtasks**: [ ] T009 [ ] T010 [ ] T011 [ ] T012
- **Prompt**: [tasks/WP03-dogfood-corpus-backfill.md](./tasks/WP03-dogfood-corpus-backfill.md) · ~200 lines · FR-001/2/3, C-001, NFR-001

### WP04 — Unconditional reader/writer cutover (IC-03)

- **Goal**: Delete the phase-1 predicate, collapse the flag-OFF branch at all 12 sites / 11 files, cut over the runtime
  **writer** for byte-stability. `_legacy_lane_mirror_enabled` is KEPT (C-004) and still reads `status_phase` — the flip
  now activates the lane mirror, so carry a regression proving lane behaviour is unchanged.
- **Priority**: P1. **Dependencies**: WP03 (C-001: corpus backfilled+committed before readers go unconditional).
- **Independent test**: `_phase1_snapshot_authority_active` grep = 0 (SC-002); a runtime transition writes 0 bytes to
  `tasks/WP##.md` (SC-004); lane behaviour unchanged by mirror activation.
- **Subtasks**: [ ] T013 [ ] T014 [ ] T015 [ ] T016 [ ] T017
- **Prompt**: [tasks/WP04-unconditional-cutover.md](./tasks/WP04-unconditional-cutover.md) · ~380 lines · FR-004/5, NFR-003, C-002/004

### WP05 — Snapshot done-evidence + delete fallbacks + route bypass readers (IC-04)

- **Goal**: BUILD the event-sourced done-evidence read (snapshot `review` slot) first, THEN delete the T037 frontmatter
  fallbacks; route the four bypass readers (workflow_cores verdict+review = one block, done_bookkeeping, tasks_move_task
  ownership, dashboard scanner runtime reads) onto the snapshot seam.
- **Priority**: P1. **Dependencies**: WP04 (fallbacks safe to delete only after the flip; C-001).
- **Independent test**: an event-only mission with NO frontmatter review produces correct `DoneEvidence` through the merge
  path; the bypass readers resolve the snapshot, not `extract_scalar(front, …)`.
- **Subtasks**: [ ] T018 [ ] T019 [ ] T020 [ ] T021 [ ] T022 [ ] T023
- **Prompt**: [tasks/WP05-done-evidence-bypass-readers.md](./tasks/WP05-done-evidence-bypass-readers.md) · ~420 lines · FR-006/7

### WP06 — #2093 invariant hardening + test-suite reconciliation (IC-05)

- **Goal**: Empty the tolerated set, EXTEND the detector to attribute-access reads (else false green), reconcile the
  ~33-file flag-ON/flag-OFF split suite, regenerate baselines.
- **Priority**: P2. **Dependencies**: WP04, WP05 (invariant/tests reflect the end-state).
- **Independent test**: `test_2093_authority_invariant.py` passes with an empty tolerated set and fails on a reintroduced
  frontmatter authority read; the extended detector flags the pre-reroute dashboard scanner red (SC-009).
- **Subtasks**: [ ] T024 [ ] T025 [ ] T026 [ ] T027 [ ] T028
- **Prompt**: [tasks/WP06-invariant-test-reconciliation.md](./tasks/WP06-invariant-test-reconciliation.md) · ~360 lines · FR-008/9, C-006

### WP07 — Inert-field reduction (IC-06, optional tail)

- **Goal**: Remove the now-inert `wp_metadata` runtime fields + cosmetic `WP_FIELD_ORDER` slots — pure hygiene, safe only
  post-cutover. **`status_phase` is OUT of bounds** (kept lane mirror reads it — C-004).
- **Priority**: P3 (optional/deferrable; DoD rests on US1–US4+US6). **Dependencies**: WP06. **Folded in-mission (no follow-up issue).**
- **Independent test**: inert fields gone, no live reader references them (`assert_zero_readers`), full suite green.
- **Subtasks**: [ ] T029 [ ] T030
- **Prompt**: [tasks/WP07-inert-field-reduction.md](./tasks/WP07-inert-field-reduction.md) · ~180 lines · FR-011

---

## Phase 2 — Resolved-binding record + reconstruct (US6)

### WP08 — Field-authority ADR + identity vocabulary (IC-08a)

- **Goal**: Ratify the per-field authority (resolved role/agent_profile/model → dynamic/event; authored → static/frontmatter)
  as an ADR **before** the IC-08 vocabulary lands (C-009); add the two terms to `docs/context/identity.md`.
- **Priority**: P2 (gates IC-08). **Dependencies**: WP07 (chains Phase 2 after Phase 1).
- **Independent test**: ADR exists as an addendum to `2026-07-19-1` (B4); terminology guard + docs-freshness pass.
- **Subtasks**: [ ] T031 [ ] T032
- **Prompt**: [tasks/WP08-field-authority-adr.md](./tasks/WP08-field-authority-adr.md) · ~170 lines · FR-013 (ADR gate), C-009

### WP09 — Resolved-binding vocabulary + reducer (IC-08 vocabulary)

- **Goal**: Data-drive `WPInnerStateDelta` (tidy-first, collapse the triple-enumeration), add resolved slots, and extract
  `reducer._apply_annotation_delta` into a data-driven replace-slot table (tidy-first, cx13→≤15) before adding the slots.
- **Priority**: P2. **Dependencies**: WP08 (ADR precedes vocabulary).
- **Independent test**: reducer folds resolved slots latest-wins; delta round-trips; `is_empty` correct with the new fields.
- **Subtasks**: [ ] T033 [ ] T034 [ ] T035 [ ] T036
- **Prompt**: [tasks/WP09-resolved-binding-vocabulary.md](./tasks/WP09-resolved-binding-vocabulary.md) · ~300 lines · FR-013, C-009

### WP10 — Dispatch→claim linkage + historical provenance correction (IC-08 linkage)

- **Goal**: Thread the genuine dispatch-resolved model+profile into the claim seams (C-007, never frontmatter), emit the
  binding as an annotation (latest-wins at both claim points) + enrich `actor`, prohibit authored-to-resolved
  historical backfill (C-011), and remove the earlier deterministic fabricated corpus rows.
- **Priority**: P2 (largest scope-growth: invocation + command surface + claim seams). **Dependencies**: WP09, WP03.
- **Independent test**: recorded resolved comes from `resolve_profile`/`resolved_agent()` not frontmatter (INV-6); latest-wins
  across implement→review claim; authored-only legacy binding remains unresolved; explicitly-absent model path recorded honestly.
- **Subtasks**: [ ] T037 [ ] T038 [ ] T039 [ ] T040 [ ] T041 [ ] T042
- **Prompt**: [tasks/WP10-dispatch-claim-linkage.md](./tasks/WP10-dispatch-claim-linkage.md) · ~460 lines · FR-013/14, C-007/011, SC-011

### WP11 — Canonical WP-view reconstruction reader (IC-07)

- **Goal**: One `reconstruct_wp_view(feature_dir, wp_id)` replacing the four hand-rolled gates; resolved (snapshot) vs
  authored (frontmatter) surfaced distinctly (C-008); tidy-first extract `scanner._process_wp_file`; tolerate-absent (INV-7).
- **Priority**: P2. **Dependencies**: WP10 (needs resolved slots + the re-seed; merge unit).
- **Independent test**: dashboard, `agent tasks status` board, `WorkPackage` agree (SC-007); implement→review shows current
  actual (SC-008); never-reclaimed WP → authored populated / resolved empty.
- **Subtasks**: [ ] T043 [ ] T044 [ ] T045 [ ] T046
- **Prompt**: [tasks/WP11-reconstruction-reader.md](./tasks/WP11-reconstruction-reader.md) · ~340 lines · FR-012, C-008, SC-007/8

### WP12 — SaaS fan-out of the resolved binding (IC-09)

- **Goal**: Widen the local `actor` type-surface to `str | dict`, guard the round-trip coercions, enrich the structured
  actor on claim/review (zero shared-package change), and scaffold the version-gated fallback event.
- **Priority**: P3. **Dependencies**: WP10 (resolved actuals must exist to fan out). Parallel with WP11.
- **Independent test**: a dict actor round-trips JSONL uncorrupted; a claim fan-out payload carries the resolved
  `{role,profile,tool,model}`; with an older `spec_kitty_events` the new-event fan-out is skipped (logged), local unaffected.
- **Subtasks**: [ ] T047 [ ] T048 [ ] T049 [ ] T050
- **Prompt**: [tasks/WP12-saas-fanout.md](./tasks/WP12-saas-fanout.md) · ~300 lines · FR-015

### WP13 — Subtask completion event-sourced; checkboxes removed (IC-10)

- **Goal**: Make the snapshot `subtasks` slot the sole authority — reroute the lane-transition guard + dashboard off
  checkbox counting, remove the `- [ ] T###` checkboxes (AFTER the seed, C-010), and update the SOURCE doctrine templates
  to direct `mark-status`.
- **Priority**: P2. **Dependencies**: WP11 (reader reads the slot), WP03 (seed precedes removal).
- **Independent test**: the guard blocks/unblocks correctly off the snapshot; the dashboard reads snapshot subtasks; no
  `- [ ] T###` checkbox remains in templates/tasks.md; historical completion was seeded before removal (SC-010).
- **Subtasks**: [ ] T051 [ ] T052 [ ] T053 [ ] T054
- **Prompt**: [tasks/WP13-subtasks-event-sourced.md](./tasks/WP13-subtasks-event-sourced.md) · ~340 lines · FR-016, C-010, NFR-003

---

## Dependency Graph

```
WP01 ─┬─ WP02 (upgrade migration)                                   [WP02 ∥ WP03]
      └─ WP03 ── WP04 ── WP05 ── WP06 ── WP07 ── WP08 ── WP09 ── WP10 ─┬─ WP11 ─┐
                 └──────────────── merge unit ─────────┘               ├─ WP12  │  [WP11 ∥ WP12]
                                                       (re-seed unit) └─────────┴─ WP13
                                                                                    ▲
                                        WP03 (seed) ────────────────────────────────┘
```

- **Merge-unit atomicity #1 (C-001 / D-07):** `WP03 → WP04 → WP05` — seeds committed to local main **before** readers go
  unconditional. Merge WPs in dependency order; each WP's worktree branches from the prior WP's merged state.
- **Merge-unit atomicity #2 (C-011 / IC-08→IC-07):** `WP10 → WP11` — provenance-safe resolved-binding
  writes land before the reader exposes actuals; legacy authored-only bindings intentionally stay empty.
- **Parallel forks:** WP02 ∥ WP03 (both on WP01, disjoint owned_files); WP11 ∥ WP12 (both on WP10, disjoint owned_files).

## Sizing

13 WPs, 54 subtasks. Per-WP subtask counts: WP01=5, WP02=3, WP03=4, WP04=5, WP05=6, WP06=5, WP07=2, WP08=2, WP09=4,
WP10=6, WP11=4, WP12=4, WP13=4 — all ≤7 (ideal band). Estimated prompt sizes 170–460 lines (all ≤700). WP07/WP08 are
intentionally small (optional tail; ADR).

## MVP / merge order

MVP = **Phase 1 cutover** (WP01→WP07): the fail-closed corpus cutover is the mission's headline outcome (US1–US4) and a
coherent shippable unit. Phase 2 (WP08→WP13, US6) is the resolved-binding record+reconstruct slice built on top. All 13
land in one PR (`Closes #2816` iff FR-001–016 land; `Closes #2093` iff FR-012–014+FR-008 land and the lane-mirror
follow-up is filed).

## Next command

`spec-kitty agent mission finalize-tasks --validate-only --mission runtime-state-corpus-cutover-01KXZ0AX --json` → then
`/spec-kitty-implement-review`.
