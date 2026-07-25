# Implementation Plan: Coord Write-Placement Closure & Birth-Cutover

**Branch**: `feat/coord-write-placement-closure` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/coord-write-placement-closure-01KYCF83/spec.md`

## Summary

Close the coord/primary write-placement residual left after #2874 so the split-brain is unrepresentable across **all** of `src/` (not a 17-module allowlist) and symmetric on the read side, add a cure for pre-existing drift (`agent mission repair`), and make new missions **born runtime-reconciled** (the #2917 birth-cutover) so the dogfood corpus never re-drifts. Approach: extend the existing placement port (do not re-architect it), replace the allowlist ratchet with a whole-tree AST gate, route the remaining writers/readers through the port, reuse `cutover_mission` (the sole `status_phase` writer) at the merge bake hook, and event-source exactly the two authoring paths (#2684) that make a birth-stamp valid. Sequence A→B; front-load the 12 drifted missions first to clear CI.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, jsonschema; `ast`/pytestarch for architectural gates; subprocess-based git (no gitpython)
**Storage**: git branches (coord/primary partitions), append-only `status.events.jsonl`, `meta.json`, `tasks.md`
**Testing**: pytest (ATDD, red-first per DIRECTIVE_041); ruff + mypy zero-warning; architectural gates in `tests/architectural/`; the durable dogfood lock `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py`
**Target Platform**: Linux / macOS / Windows CLI
**Project Type**: single (CLI framework — `src/specify_cli` + `src/mission_runtime`)
**Performance Goals**: the whole-tree AST enforcement gate completes within the existing `tests/architectural/` time budget (seconds, not minutes); zero runtime-path performance regression
**Constraints**: no green-wash of the lock (preserve `verify_backfill` parity); whole-tree coverage with individually-justified sanctioned-primitive exclusions only; fail-loud on partition mismatch; idempotent cutover (deterministic seed ids); reuse `cutover_mission` as the sole `status_phase` writer; no `MissionArtifactHome`/topology re-architecture; no `doctor coordination --fix` growth
**Scale/Scope**: ~9 implementation concerns across `src/mission_runtime/{artifacts,resolution}.py`, `src/specify_cli/{coordination,status,migration,merge,mission_metadata}`, `src/specify_cli/cli/commands/agent/`, and `tests/architectural/`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Charter present (`compact` mode; `software-dev-default`). Relevant governing principles and their fit:

- **Single canonical authority** — reinforced, not violated: the mission consolidates writers onto the one placement port and keeps `cutover_mission` the sole `status_phase` writer (C-004). No rival authority is introduced.
- **Architectural alignment** — the fix extends the existing port kind-mapping (FR-002) rather than re-architecting `MissionArtifactHome` (explicitly OUT, C-002).
- **DDD + tiered rigour** — core seams (placement routing, cutover) get full rigour + red-first ATDD; the front-load (IC-01) is a mechanical, deterministic corpus write.
- **ATDD-first / red-first** — every FR ships a red-first test through the real entry point (DIRECTIVE_041); the birth-write repro drives create→implement→merge, not a fixture.
- **Canonical sources** — no improvised substitutes; reuse `cutover_mission`, the placement port, and the existing `doctor coordination --fix` (kept minimized) rather than growing them.

No charter violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coord-write-placement-closure-01KYCF83/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/mission_runtime/
├── artifacts.py            # kind→partition maps; PRIMARY_METADATA commit_target (FR-002); decisions/traces classification (FR-003/006)
└── resolution.py           # placement_seam / resolve_placement_only / read_dir — read-surface authority (FR-004)

src/specify_cli/
├── coordination/
│   ├── commit_router.py    # partition-split write chokepoint (route remaining writers here)
│   └── status_transition.py# close the HEAD-derived fallback #1716 (FR-003)
├── status/
│   ├── emit.py             # status write surface; status_phase's only reader (lane mirror)
│   └── bookkeeping…        # decision_log.py / bookkeeping_commit.py routing (FR-003)
├── migration/
│   └── runtime_state_cutover.py  # sole status_phase writer — reused at birth (FR-009, C-004)
├── merge/
│   ├── ordering.py         # _bake_mission_number_into_mission_branch — birth-cutover hook (FR-009)
│   ├── executor.py         # _phase_bake_and_pre_target_done — invocation point
│   └── bookkeeping_projection.py # coord→target projection writer (route via port) (FR-003)
├── mission_metadata.py     # write_meta — partition-aware target (FR-002)
└── cli/commands/agent/     # new `mission repair` command (FR-005)

tests/architectural/
├── test_no_write_side_rederivation.py   # replace 17-module allowlist → whole-tree (FR-001)
├── test_safe_commit_import_boundary.py  # extend to check target= seam-derivation (FR-001)
└── test_read_surface_placement_guard.py # NEW read-side enforcement gate (FR-004)
```

**Structure Decision**: single-project CLI framework; changes are surgical extensions of existing seams under `src/mission_runtime` and `src/specify_cli`, plus architectural gates under `tests/architectural/`. No new top-level packages.

## Post-Plan Squad Review (folded 2026-07-25)

A 3-lens squad (risk `debugger-debbie`, arch-alignment `architect-alphonso`, SSOT `paula-patterns`) reviewed this plan. Verdicts: arch = ALIGNED-with-caveats; SSOT = DUPLICATION-RISK (moderate); risk = 3 under-addressed criticals. All findings folded into the ICs below. The load-bearing corrections:

- **IC-08 (crux):** the `_bake_mission_number` hook is **pre-target** (not post-target-durable — corrected in the contract/research); and `cutover_mission(feature_dir)` is **single-partition by signature**, so the two-partition birth-write is an open design point (two-target spine form vs delegate the COORD seed write to the coord projection) with a two-write atomicity window to close.
- **IC-09 green-wash (highest silent-failure stakes):** the lock's eligibility keys on `has_evictable_state()` (the frontmatter IC-07 retires); re-keying to `status_phase` is circular. Must key on **independent event-log evidence**.
- **IC-07 reader coupling:** `stale_detection.py` / `task_metadata_validation.py` read `shell_pid` from frontmatter and were missing from IC-07's scope.
- **Convergence-not-duplication:** IC-05 must pull #2906's accept-time read guards *into* the read authority; IC-06 must reconcile against the third repair surface (`doctor mission-state --fix repair_repo`) and reuse `_is_ff_candidate`; IC-02 must reuse `_BOUNDARY_SANCTIONED_MODULES` (no new dir-prefix exclusions).
- **Layering:** `mission_runtime` already imports `specify_cli` (top-level + ~40 late) — IC-03/IC-05 must add **no new top-level** `specify_cli` imports.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Front-load the drifted corpus (unblock CI)

- **Purpose**: run the one-time backfill over the 12 drifted missions and commit the flips so `test_dogfood_corpus_backfilled` passes and 3.2.6 is unblocked.
- **Relevant requirements**: FR-007; SC-001 (initial green).
- **Affected surfaces**: `kitty-specs/**` (committed corpus); `migrate backfill-runtime-state` (`migrate_cmd.py`).
- **Sequencing/depends-on**: none — independent, lands first.
- **Risks**: must exclude the self-mission; deterministic byte-stable seeds; run against the branch that becomes the corpus.

### IC-02 — Whole-tree write-placement enforcement

- **Purpose**: replace the 17-module `_CHECKOUT_GRAMMAR_MODULES` allowlist with a whole-tree AST gate; extend `test_safe_commit_import_boundary` to assert `target=CommitTarget(...)` is seam-derived — so a bypass anywhere in `src/` reds.
- **Relevant requirements**: FR-001; NFR-001; NFR-004; SC-002.
- **Affected surfaces**: `tests/architectural/test_no_write_side_rederivation.py` (`_CHECKOUT_GRAMMAR_MODULES:471-476`, reuse the **existing** `_BOUNDARY_SANCTIONED_MODULES:486` — do NOT add a new collection; the meta-test `:746` extends to require an inline rationale per entry), `test_safe_commit_import_boundary.py`. A **shared whole-tree scan helper** (module walker + sanctioned set) consumed by both this gate and IC-05's read gate.
- **Sequencing/depends-on**: informs IC-03/IC-04/IC-08 (their writes must satisfy the widened gate). Shares the scan helper with IC-05.
- **Risks**: (a) **exclusion list balloons into an inverted allowlist** — keep it **per-file**, forbid new dir-prefix exclusions (`_BOUNDARY_SANCTIONED_PREFIXES` is how an allowlist creeps back). (b) ~15 modules newly enter scope (incl. the **definition sites** `commit_helpers.safe_commit`, `mission_metadata.write_meta`, plus `merge/baseline.py`, `acceptance/__init__.py`, `doc_state.py`, …) — the gate must discriminate **def vs call** or false-red them; tasks budget each as route (IC-04) vs sanctioned. (c) the gate proves **syntactic** provenance (arg is a `resolve_placement_only`/`placement_seam.write_target` call), not value-flow — state the proxy, don't over-promise.

### IC-03 — Partition-aware meta.json routing

- **Purpose**: give `PRIMARY_METADATA` a partition-aware write target (a **one-field flip**: `commit_target=None` → `commit_target=placement_ref` at `artifacts.py:218-224`, i.e. delete the special-case arm so it matches the generic primary arm) so `write_meta` / `_flip_phase` / `_bake_mission_number` route meta writes through the port.
- **Relevant requirements**: FR-002; SC-005 (enabling).
- **Affected surfaces**: `mission_runtime/artifacts.py:218-238` (the `PRIMARY_METADATA` arm), `resolution.py:949` (the sole `commit_target` consumer); `mission_metadata.py::write_meta`.
- **Sequencing/depends-on**: prerequisite for IC-08 (birth-write). **Before IC-04** (both edit `artifacts.py`; do the port kind-mapping first).
- **Risks**: (a) audit that **no consumer reads `commit_target is None` as "skip commit"** before flipping the sentinel (grep says inert today — confirm). (b) genuinely **extends** the kind-mapping — NOT a `MissionArtifactHome`/topology re-architecture (C-002). (c) **add no new top-level `specify_cli` import** to `mission_runtime` (the module is already inversion-coupled).

### IC-04 — Close the emit fork + unscanned writers + classify decisions/traces

- **Purpose**: close the `_current_branch` HEAD-derived fallback (#1716); route `bookkeeping_projection` / `bookkeeping_commit` / `decision_log` through the port; classify `decisions.events.jsonl` and `traces/` in the **one** partition SSOT.
- **Relevant requirements**: FR-003; FR-006; SC-006.
- **Affected surfaces**: `coordination/status_transition.py:685` (the fallback), `merge/bookkeeping_projection.py:247`, `git/bookkeeping_commit.py`, `events/decision_log.py:209`; classification goes **only** into `mission_runtime/artifacts.py::_MISSION_FILE_KIND_BY_BASENAME:181` + `_COORD_RESIDUE_DIRS:207` (the single `kind_for_mission_file` classifier) — writers call the classifier, they do **not** classify inline.
- **Sequencing/depends-on**: **after IC-03** (both edit `artifacts.py`). Its `status_transition.py` claim-region edit **co-lands with IC-07** (same region) — sequence as one pass. Satisfies IC-02's widened gate.
- **Risks**: the emit fallback is reached in the pre-`meta.json` create window — the replacement must not deadlock; `traces/` reclassification (PRIMARY→COORD) may move existing writes; classify in the two dicts only (SSOT), never at the writer sites.

### IC-05 — Read-side placement enforcement

- **Purpose**: the fail-loud arch gate + typed mismatch on reads (routing-by-kind via `artifact_home_for(kind).read_surface` already exists since #2090 — the **delta is enforcement**, not new routing). Generalize #2906's accept-time read guards **into** this authority.
- **Relevant requirements**: FR-004; NFR-002; SC-003.
- **Affected surfaces**: `mission_runtime/resolution.py:1403` (`read_dir` authority); **the #2906 guards to fold in** — `acceptance/execution_context.py:203-223`, `acceptance/gates_core.py:436` (refactor their substitution refusal to delegate to the new authority, not sit beside it); a NEW `tests/architectural/test_read_surface_placement_guard.py` reusing IC-02's shared scan helper.
- **Sequencing/depends-on**: pairs with IC-02 (shared scanner). No hard order vs IC-03/04.
- **Risks**: **the highest blast-radius** — ~68 read sites. Fail-loud must NOT break sanctioned degrades: enumerate every current lenient read — `StatusReadPathNotFound` (`resolution.py:365/841/886`), the **coord-worktree-absent degrade** (flatten-when-coord-gone), the #2906 lenient diagnose path — and prove each is either a true mismatch that *should* now fail or an explicitly whitelisted degrade (red-first test both stay lenient). **Add no new top-level `specify_cli` import** to `mission_runtime`.

### IC-06 — `agent mission repair` (Gap-2 cure)

- **Purpose**: a new command that detects a pre-existing content split-brain and forward-only repairs it (fail-loud with a diff otherwise) — distinct from BOTH existing repair surfaces.
- **Relevant requirements**: FR-005; NFR-005; SC-004.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_*.py` (new subcommand); **reuse** `_coordination_doctor._is_ff_candidate:341` / `_fast_forward_finding:362` (do NOT reimplement the FF/ancestor machinery).
- **Sequencing/depends-on**: none.
- **Risks**: (a) a **third** repair surface already exists — `doctor mission-state --fix` → `repair_repo` (`_mission_state_doctor.py:213`, `migration/mission_state.py:518`); the tasks must **explicitly adjudicate** why cross-partition content cure is a distinct Gap-2 concern and not an extension of `repair_repo`. (b) never force-overwrite divergence; keep `doctor coordination --fix` minimized (C-002/C-003).

### IC-07 — Event-source the two authoring paths

- **Purpose**: event-source exactly the claim fields (`shell_pid`/`agent`) and subtask-completion (`tasks.md` checkboxes) so nothing un-seeded accrues to frontmatter/`tasks.md` (extends #2684).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `coordination/status_transition.py` (claim — **co-lands with IC-04**'s fallback removal in the same region), `core/subtask_rows.py` / `tasks_*` (subtask completion), `frontmatter.py`; **plus the frontmatter READERS** `core/stale_detection.py:230` (`_is_claiming_process_alive` reads `shell_pid` from frontmatter) and `task_metadata_validation.py`.
- **Sequencing/depends-on**: prerequisite for IC-08 and IC-09; scope strictly the two paths (C-002).
- **Risks**: **retiring the `shell_pid` frontmatter write breaks claim-liveness / stale-sweep unless the readers first consume the reduced snapshot** — confirm `stale_detection.py`/`task_metadata_validation.py` read from the snapshot (or migrate them) with a red-first stale-sweep test *before* removing the write. Do NOT broaden into the #1619 dual-write program.

### IC-08 — Birth-time runtime cutover

- **Purpose**: stamp `status_phase` and reconcile residual runtime at land via `cutover_mission`, routed through IC-03's port — so missions are born reconciled.
- **Relevant requirements**: FR-009; NFR-003; C-004.
- **Affected surfaces**: `merge/ordering.py:485` (mission_number bake, structural twin), `merge/executor.py:1316-1328` (phase order), `runtime_state_cutover.py:107-180` (`cutover_mission` reuse), `merge/bookkeeping_projection.py` (coord projection, candidate owner of the COORD seed-event split).
- **Sequencing/depends-on**: **after IC-03 and IC-07** (C-001). **Add IC-08 → IC-02**: the birth-write must satisfy the whole-tree gate.
- **Risks (the plan's weakest seam — must be resolved in tasks)**:
  1. **Timing corrected**: `_bake_mission_number` is **pre-target** (`executor.py:1319` before `_phase_mission_to_target:1320`). The PRIMARY meta flip **rides the mission→target merge atomically** (abort ⇒ never reaches target ⇒ consistent). Tasks decide: (a) keep the bake hook and rely on merge-atomicity for the PRIMARY leg, or (b) relocate to a post-`_phase_commit_and_assert` phase. The earlier "after target durable" claim was **inaccurate** for this hook.
  2. **Single-`feature_dir` signature**: `cutover_mission(feature_dir)` writes seed events + `status_phase` relative to ONE dir — it **cannot** natively split meta→PRIMARY (mission branch) / seed events→COORD (coord branch). Resolve ownership: a **two-target spine form** OR delegate the COORD seed write to `_phase_record_done_and_project`. Either extends the spine, not forks it (C-004).
  3. **Two-write atomicity**: a crash between the COORD seed commit and the PRIMARY flip must not half-birth a mission — transactional envelope or resume-heal (`_heal_pending_coord_reconcile`).
  4. Idempotent with the one-time migration (deterministic seeds).

### IC-09 — Re-key the acceptance lock + migration coexistence

- **Purpose**: re-key `test_dogfood_corpus_backfilled` to an event-log birth invariant (every mission whose event log carries runtime, excluding the self-mission, is `status_phase>=1` + non-empty snapshot); add a regression that the one-time migration still cuts over a legacy corpus.
- **Relevant requirements**: FR-010; NFR-006; C-003; SC-001 (durable green).
- **Affected surfaces**: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` (`_eligible_runtime_missions:120-133`, `_backfilled_missions:110-115`); a migration-coexistence test.
- **Sequencing/depends-on**: **after IC-07** (C-001 — authoring retirement empties `has_evictable_state()`); preserve the `verify_backfill` parity assertion (no green-wash).
- **Risks (highest silent-failure stakes)**: the current eligibility keys on `has_evictable_state()` — **exactly the frontmatter IC-07 retires** → post-IC-07 born-reconciled missions become invisible and SC-001 passes **vacuously**. Re-keying to `status_phase>=1` is **circular** (only checks already-flipped). Tasks must **hard-forbid keying on `has_evictable_state()` OR `status_phase`** and key on **independent event-log evidence** (the mission's event log carries seed/runtime events), preserving the `verify_backfill` parity.
