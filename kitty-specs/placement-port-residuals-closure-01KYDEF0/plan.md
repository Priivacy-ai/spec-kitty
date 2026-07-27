# Implementation Plan: Placement-Port Residuals Closure

**Branch**: `placement-port-residuals` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/placement-port-residuals-closure-01KYDEF0/spec.md`

## Summary

Close the placement-port residuals PR #2920 deferred (Parts A/B, issues #2923+#2924)
and green the six gate/contract reds the PR merged red into `upstream/main` (Part C,
incl. #2926). The work is a brownfield hardening pass over the birth-cutover / legacy
runtime cutover, the coordination write-target degrade idiom, a best-effort tracer read,
and four architectural/contract gates. Every fix is red-first through a pre-existing entry
point; A1/A3 are validated across the whole FR-007 dogfood corpus. The engineering approach
is fixed by the squad-hardened spec — no open design questions remain.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (runtime); `spec_kitty_events` / `spec_kitty_tracker` (external contract pkgs); `mission_runtime` placement port (in-repo)
**Storage**: Git-backed mission artifacts on disk (`kitty-specs/<mission>/`), append-only `status.events.jsonl`; `meta.json` metadata
**Testing**: pytest (`PWHEADLESS=1 pytest tests/`), parallel `-n auto --dist loadfile`; red-first per DIRECTIVE_041; `tests/architectural/` gate suite; mypy `--strict`; ruff (complexity ceiling 15)
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), Python 3.11+
**Project Type**: single (Python CLI package `specify_cli` + shared `mission_runtime`)
**Performance Goals**: N/A (correctness/gate mission, not a perf change)
**Constraints**: No new lint/type debt (ruff+mypy clean, complexity ≤15); no legacy terminology; canonical sources only; no version/patch number assigned (C-005); no direct push to origin/main (PR workflow)
**Scale/Scope**: 12 FRs / 4 NFRs / 7 constraints across ~8 product files + 5 test files; corpus-wide validation over the dogfood `kitty-specs/` missions

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter mode: compact (`software-dev-default`). Binding gates relevant here:

- **Red-first / ATDD-first** — each fix ships a failing test through the pre-existing entry point BEFORE the fix (NFR-001). Part C reds are already-red and satisfy this inherently; judged per the failing-test remediation framework (fix PRODUCT vs re-pin TEST), never retry-to-green.
- **Canonical sources** — use `mission_runtime` port surfaces + doctrine templates; no improvised path reconstruction (FR-001/FR-005 route through the port).
- **Terminology canon** — `Mission` not `feature`; PRIMARY-partition ≠ Primary-Branch (Domain Language table). Terminology guard run each spec commit (green).
- **Quality gates** — ruff + mypy `--strict` clean, complexity ≤15, no blanket suppressions (NFR-003).
- **Git workflow** — mission merges to local `placement-port-residuals`; PR to `main` separately; no `git push origin main`.
- **No version prescription** — C-005 (PO superimposes at release).

No charter violations anticipated. Complexity Tracking: N/A (no gate justifications required).

## Project Structure

### Documentation (this mission)

```
kitty-specs/placement-port-residuals-closure-01KYDEF0/
├── plan.md              # This file
├── research.md          # Phase 0 output — decisions already resolved by the post-spec squad
├── data-model.md        # Phase 1 output — partitions / gates / capabilities (no new persisted entities)
├── quickstart.md        # Phase 1 output — how to run each red-first repro
├── contracts/           # Phase 1 output — the invariant contracts each FR must satisfy
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/
│   ├── resolution.py           # resolve_artifact_surface / resolve_placement_only / placement_seam (FR-001, FR-005 home)
│   └── artifacts.py            # MissionArtifactKind (PRIMARY_METADATA / STATUS_STATE / TRACER_FILE partitions)
├── specify_cli/
│   ├── migration/
│   │   ├── runtime_state_cutover.py     # _flip_phase (FR-001), cutover_mission seed/verify (FR-002)
│   │   └── backfill_runtime_state.py    # read-dir vs write-dir decoupling + has_evictable_state (FR-002)
│   ├── merge/executor.py                # coord-seed safe_commit @1053-1060 (FR-008+FR-012), committed-set (FR-011)
│   ├── events/decision_log.py           # _mission_meta_exists clone + _resolve_commit_target (FR-005)
│   ├── git/bookkeeping_commit.py        # _mission_meta_exists clone + _resolve_bookkeeping_commit_target (FR-005)
│   ├── coordination/status_transition.py# _resolve_write_target divergent degrade (FR-005)
│   ├── retrospective/generator.py       # _load_traces best-effort read (FR-006)
│   └── cli/commands/agent/mission_repair.py  # raw KITTY_SPECS_DIR/mission path (FR-009)

tests/
├── architectural/
│   ├── test_no_write_side_rederivation.py   # FR-008 allow-list (+ context for FR-003)
│   ├── _placement_whole_tree_scan.py        # BOUNDARY_SANCTIONED_PREFIXES→MODULES (FR-003)
│   ├── test_no_raw_mission_spec_paths.py     # FR-009 constructor allow-list
│   └── test_guard_capability_call_sites.py   # FR-012 MERGE_BOOKKEEPING allow-list (#2926)
├── specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py  # FR-010 _EXPECTED_COMMANDS/_FLAGS
├── cli/commands/test_merge_status_commit.py             # FR-011
└── integration/test_merge_lane_planning_data_loss.py    # FR-011
```

**Structure Decision**: Single Python package; brownfield edits confined to the surfaces above. No new packages, no new top-level directories. New helper for FR-005 lands under `src/mission_runtime/` (the placement-port package that owns `resolve_placement_only`).

## Complexity Tracking

N/A — no Charter Check violations to justify.

## Implementation Concern Map

> Concerns are architectural areas, NOT work packages. `/spec-kitty.tasks` translates
> these into executable WPs (one IC may become several WPs; small ICs may merge).
> Lane hints below reflect **C-007** (shared-file cohesion), not final sequencing.

### IC-01 — Sole `status_phase` writer routed through the port (fail-closed)

- **Purpose**: Make `_flip_phase`'s PRIMARY-correctness enforced by a runtime home-equality assert through the placement port, not by caller discipline.
- **Relevant requirements**: FR-001; NFR-001, NFR-002.
- **Affected surfaces**: `migration/runtime_state_cutover.py` (`_flip_phase`), `mission_runtime/resolution.py` (`resolve_artifact_surface`).
- **Sequencing/depends-on**: none (first in Lane A).
- **Risks**: `repo_root` must be the CWD-invariant main-repo root derived from `feature_dir` (never `Path.cwd()`); a resolver **raise** on a well-formed legacy corpus mission must NOT abort the flip — only an equality **mismatch** fail-closes; `write_meta` is invisible to the write-side gate so this is runtime-enforced (see [[reference-write-side-rederivation-gate-grammar]]); corpus regression risk.

### IC-02 — Cutover read/write partition decoupling (no silent PRIMARY-runtime loss)

- **Purpose**: Read the legacy `tasks/` frontmatter from the PRIMARY leg so a pre-IC-07 cold-upgrade coord mission is not silently evicted, while the seed-event write stays on its canonical COORD leg.
- **Relevant requirements**: FR-002; NFR-002.
- **Affected surfaces**: `migration/runtime_state_cutover.py` (`cutover_mission` line 202, `_seed_phase`:205, `_verify_phase`:214 — split read-leg=PRIMARY `feature_dir` from write-leg=COORD `status_dir` **internally**). **Public signature of `cutover_mission` stays stable** — the split is internal.
- **No-change verification anchors** (post-squad): the only COORD-reader is the two-leg `executor.py:996` birth-cutover caller. The three single-leg callers (`m_zz_runtime_state_backfill.py:204`, `cli/commands/migrate_cmd.py:868`, `cutover_repo:281`) already read PRIMARY and MUST be byte-unchanged — do NOT spawn a caller-fanout WP. NFR-002's corpus run asserts they are unchanged.
- **Sequencing/depends-on**: IC-01 (same file; sequence after).
- **Risks**: NOT a leg swap — the event log (STATUS_STATE) must still land on COORD; the read/write split is internal to `cutover_mission`+`_seed_phase`/`_verify_phase` (signature stable); red-first test drives the **two-leg** shape (evictable PRIMARY `tasks/` + stale/absent COORD `tasks/`) and asserts both `seeded_count > 0` AND events on the COORD leg.

### IC-03 — Birth-cutover coord-seed commit: reconcile both arch gates at one call site

- **Purpose**: Green `test_no_write_side_rederivation` (FR-008) and `test_guard_capability_call_sites[MERGE_BOOKKEEPING]` (FR-012, #2926) — both flag the SAME `safe_commit` at `executor.py:1053-1060`.
- **Relevant requirements**: FR-008, FR-012; NFR-004, SC-008.
- **Affected surfaces**: `merge/executor.py` (coord-seed call site), `tests/architectural/test_no_write_side_rederivation.py` (allow-list), `tests/architectural/test_guard_capability_call_sites.py` (`_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]`).
- **Sequencing/depends-on**: none (Lane A; shares `executor.py` with IC-04).
- **Risks**: resolve BOTH gates with one coherent dated rationale (best-effort coord-seed writes `status.events.jsonl` to the protected coord ref during merge); do NOT downgrade to STANDARD (would refuse the protected destination) and do NOT seam-route (adds merge-window resolvability coupling).

### IC-04 — Merge status-event durability

- **Purpose**: Ensure merges durably commit `status.events.jsonl` alongside `meta.json`/`status.json` (product regression, not a stale test).
- **Relevant requirements**: FR-011; NFR-004, SC-008.
- **Affected surfaces**: `merge/executor.py` (committed-file set), `tests/cli/commands/test_merge_status_commit.py`, `tests/integration/test_merge_lane_planning_data_loss.py`.
- **Sequencing/depends-on**: none (Lane A; shares `executor.py` with IC-03).
- **Risks**: the tests encode the real FR-019/FR-020 durability invariant → fix the PRODUCT; verify across planning-only and mark-done merge paths.

### IC-05 — Whole-tree gate carve-out narrowing + guarantee wording

- **Purpose**: Convert the `src/specify_cli/migration/` whole-subtree prefix to per-file `BOUNDARY_SANCTIONED_MODULES` entries with individual rationales, and reconcile SC-002/NFR-001 wording precisely (migration/-subtree-scoped, not falsely un-qualified).
- **Relevant requirements**: FR-003, FR-004; SC-002.
- **Affected surfaces**: `tests/architectural/_placement_whole_tree_scan.py` (`BOUNDARY_SANCTIONED_PREFIXES`) **AND `tests/architectural/test_no_write_side_rederivation.py` (`_PINNED_BOUNDARY_SANCTIONED_PREFIXES`:511 — LOCKSTEP edit; the meta-test at :916 hard-asserts equality, so both must change together or it reds)**; the merged `coord-write-placement-closure-01KYCF83/spec.md` deferral note (by anchor).
- **Sequencing/depends-on**: `{IC-03 for suite-green verification, IC-01 defensive}`. Corrected C-001 (adjudicated from source): dropping the prefix reds nothing on `_flip_phase` (the write-side gate scans only `CommitTarget`/`safe_commit`; `migration/` has none) — so no *mechanical* IC-01 dependency; keep IC-01 ordering as defensive insurance. Last in Lane A.
- **Verification (3 shared-scan consumers)**: `BOUNDARY_SANCTIONED_PREFIXES` is imported by `test_no_write_side_rederivation`, `test_safe_commit_import_boundary`, and `test_read_surface_placement_guard` — verify all three green after the widen. **C-003 refutation (recorded):** the read-surface guard has no whole-scope offender scan and the AST consumers flag only `CommitTarget`/`safe_commit` (absent from `migration/`), so widening `scan_scope()` over `migration/` provably engages NO read-side offender grammar — no #2922 collision.
- **Empirical red-first (closes C-001)**: with the prefix dropped and IC-01 NOT yet applied, observe whether the gate reds on `_flip_phase` — empirically confirms the mechanism either way.
- **Risks**: keep `mission_runtime/` (port can't scan itself) AND `upgrade/migrations/` (C-002); every retained per-file entry needs a rationale; do not overclaim closure for `upgrade/migrations/`; the C-004 `_MIGRATION_WALKER_DIR_PREFIXES` blanket in `test_mission_resolver_walker_gate.py` is a SEPARATE, intentional, permanent carve-out — out of scope, do NOT convert (SC-002 is scoped to the placement-enforcement scan only).

### IC-06 — Write-target degrade unification (kind-parameterized) — SPLIT into 6a/6b

- **Purpose**: One shared `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)` in `mission_runtime` unifying **port-resolution + the `_mission_meta_exists` pre-gate** — NOT the degrade *policy*. The three sites keep three legitimately-distinct null-`degrade_ref` policies (decision_log = fail-open `return ref`; bookkeeping = fail-closed `raise ActionContextError`; status_transition = secondary-resolver `get_feature_target_branch`), so `degrade_ref` is **caller-computed**. SC-004 "exactly 1 implementation" = one resolution+pre-gate helper, not one degrade action.
- **Relevant requirements**: FR-005; NFR-003, SC-004.
- **IC-06a (mechanical, low-risk)**: extract the helper; migrate the **two verbatim clones** (`events/decision_log.py`, `git/bookkeeping_commit.py`) through it with caller-computed `degrade_ref`, each keeping its fail-open/fail-closed contract. Satisfies SC-004 "0 verbatim clones."
- **IC-06b (behavior change, C-004, dedicated tests)**: adopt `coordination/status_transition.py::_resolve_write_target` onto the helper — this ADDS the `_mission_meta_exists` pre-gate it lacks today (real behavior change) while preserving the `get_feature_target_branch` degrade. Separable so 6a lands even if 6b iterates.
- **Affected surfaces**: new helper in `src/mission_runtime/`; `events/decision_log.py` + `git/bookkeeping_commit.py` (6a); `coordination/status_transition.py` (6b).
- **Sequencing/depends-on**: none (Lane B); 6b after 6a.
- **Risks**: kind-parameterized — `STATUS_STATE`/coord kinds degrade to the COORD ref, never PRIMARY (C-004); do NOT flatten the three degrade policies into the helper.

### IC-07 — Best-effort tracer read guard

- **Purpose**: Wrap `_load_traces`' `read_dir(TRACER_FILE)` so a deleted coordination branch degrades to `[]` instead of crashing.
- **Relevant requirements**: FR-006; SC-005.
- **Affected surfaces**: `retrospective/generator.py` (`_load_traces`).
- **Sequencing/depends-on**: none (Lane C — split-candidate).
- **Risks**: `except (CoordinationBranchDeleted, StatusReadPathNotFound)` only — do NOT widen to bare `Exception`; single call site (C-003), do not touch #2922's read-side set.

### IC-08 — CLI path + golden-contract hygiene

- **Purpose**: Green `test_no_raw_mission_spec_paths` (FR-009) and reconcile the mission-CLI golden contract for the sanctioned `repair` command (FR-010).
- **Relevant requirements**: FR-009, FR-010; SC-008.
- **Affected surfaces**: `cli/commands/agent/mission_repair.py`, `tests/architectural/test_no_raw_mission_spec_paths.py`, `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py` (`_EXPECTED_COMMANDS`/`_EXPECTED_FLAGS`/`_EXPECTED_POSITIONALS`), `cli-surface-contract.md`.
- **Sequencing/depends-on**: none (Lane C — split-candidate).
- **Risks**: FR-010 must pin repair's flag/positional surface (not just the name) and rename the "exactly_eight" test/docstring 8→9 — else it green-washes the count while leaving the flag surface unverified.

### IC-09 — Tracker / issue-matrix shape

- **Purpose**: Parent the orphaned issues and give the Part C reds a tracked home with a 1:1 issue-matrix.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: GitHub issues + the mission issue-matrix. Terminal check = **per-FR → exactly one issue** (12 FR rows across 4 child issues under a new parent epic):
  - **#2923** → FR-001, FR-002, FR-003, FR-004 (IC-01, IC-02, IC-05)
  - **#2924** → FR-005, FR-006 (IC-06, IC-07)
  - **#2926** → **FR-008 + FR-012** (same `executor.py:1053-1060` call site; IC-03) — FR-008 rides under #2926, do NOT mint a separate FR-008 issue
  - **new Part-C issue** → FR-009, FR-010, FR-011 (IC-04, IC-08)
  - FR-007 maps to IC-09 itself.
- **Sequencing/depends-on**: none (planning-time; seeds the terminal matrix).
- **Risks**: #2923/#2924/#2926 are all `parent: null` today → native-link all four children under the new epic; do not ride the FR-009/010/011 reds under #2923 (whose body covers A1/A2/A3 only).

**Lane grouping (input to /tasks, per C-007):**
- **Lane A (serial):** IC-01 → IC-02 (runtime_state_cutover.py) and IC-03 + IC-04 (executor.py, same file) and IC-05 last (gate; depends-on `{IC-03 suite-green, IC-01 defensive}`) — one lane for file-ownership safety.
- **Lane B (parallel):** IC-06a → IC-06b.
- **Lane C (parallel, split-candidate for a fast PR if Lane A slips):** IC-07, IC-08.
- **Planning:** IC-09.

**Post-plan squad note:** paula-patterns + architect-alphonso + planner-priti (profile-loaded, read-only) hardened this IC-map. Key adjudications folded above: C-003 collision REFUTED (widening `scan_scope()` over `migration/` engages no read-side offender grammar); IC-05 acquires a lockstep pinned-tuple edit + 3-consumer verification, not an IC-01 correctness dep; paula's IC-02 premise was INVERTED (corpus callers already read PRIMARY; only the two-leg `executor.py:996` reads COORD — fix is internal, signature stable); IC-06 split 6a/6b to avoid over-folding three distinct degrade policies; SC-002 scoped to the placement-enforcement scan (the C-004 walker-gate blanket is a separate permanent carve-out).
