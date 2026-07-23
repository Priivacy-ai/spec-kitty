# Implementation Plan: ScopeSource gate follow-up — cleanup & correctness

**Branch**: `fix/scopesource-gate-followup` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/scopesource-gate-followup-01KY6S9P/spec.md`

## Summary

Close the four #2873 follow-ups to the doctrine-controlled transition gates (half A, #2871), in three work packages sequenced **A→C (hard) with B parallel**:

- **WP-A cleanup** — retire the production-dead census-derivation tier + the dead `_mt_pre_review_gate_verdict`; hoist the shared `ScopeSource` factory.
- **WP-B contract** — decouple the `ScopeBreakdownSource` port (two independent predicates + a `file_to_scope` projection mixin).
- **WP-C correctness** — close the baseline↔head command-authority split (incl. the parse-after-teardown asymmetry, B1); add a warn-shaped `GateOutcome.SOURCE_MISMATCH`; **add config-driven `ScopeSource` selection (FR-014) so SC-001 is real for non-pytest consumer repos**.

Design is fully grounded in the merged base `eb06ca176` (PRs #2874 coord-commit-integrity + #2820 dossier-parity landed). Six locked decisions in [research.md](./research.md); entities/fields/outcomes in [data-model.md](./data-model.md); surface contracts in [contracts/](./contracts/). Hardened by three adversarial squads ([post-spec](./reviews/post-spec-squad.md), [fold/boyscout](./reviews/fold-boyscout-squad.md), [post-plan](./reviews/post-plan-squad.md)).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing spec-kitty surfaces only — `specify_cli.review` (`pre_review_gate`, `scope_source`, `baseline`, `gate_registry`, `verdict_aggregation`), `specify_cli.cli.commands.agent` (`tasks_move_task`, `workflow_executor`, `workflow`), `charter`/`mission_runtime` for the `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam (#2874 C-008). No new third-party dependency.
**Storage**: `tasks/<wp>/baseline-tests.json` (`BaselineTestResult`, gains a `source_identity` field); no DB.
**Testing**: pytest (`PYTHONPATH=$(pwd)/src`); ATDD red-first (C-006); behavior-preservation goldens captured from the pre-mission commit against BOTH the registry hook (NFR-001) and the override tier (NFR-006), non-circular.
**Target Platform**: Linux/macOS dev + CI (the spec-kitty CLI runtime).
**Project Type**: single project (CLI/library).
**Performance Goals**: N/A (correctness + cleanup mission; no perf target).
**Constraints**: complexity ≤15/function; `mypy --strict` + `ruff` zero-issue/zero-warning, no new suppressions; ≥90% new-code coverage; behavior-preserving deletions (byte-identical live-path verdicts); half B (#2599) OUT.
**Scale/Scope**: ~450 LoC of dead duplicate removed; 14 FR / 7 NFR across 3 WPs / 15 ICs (IC-00..IC-14); single subsystem (`review/` + the gate hook).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (charter context: compact)

- **Single canonical authority** — WP-A collapses the duplicated census logic to the single live `scope_source.py` authority; WP-C unifies baseline+head onto one `ScopeSource` command authority. ✅ advances the principle.
- **DDD + tiered rigour / ATDD-first** — every IC is red-first (C-006) with a named failing artifact; the correctness ICs carry non-circular goldens. ✅
- **Architectural gate discipline** — the mission IS the pre-review gate; NFR-004 keeps the dead-symbol / compat-surface / census-parity / ratchet gates green (or retired with their target); #2825 baseline-red-gotcha check before attributing. ✅
- **Canonical sources, no improvisation** — FR-009 consumes #2874's existing `_resolve_workflow_read_dir` seam rather than reconstructing `feature_dir`. ✅
- **Terminology canon** — Mission not Feature; no forbidden terms (verified on spec + records). ✅
- No violations → Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/scopesource-gate-followup-01KY6S9P/
├── plan.md              # This file
├── research.md          # 6 locked decisions (D-1..D-6)
├── data-model.md        # source_identity field, SOURCE_MISMATCH, factory/seam homes, predicates+mixin
├── contracts/           # scope-source-contract.md, gate-outcome-contract.md, baseline-identity-contract.md
├── reviews/             # post-spec-squad.md, fold-boyscout-squad.md
└── tasks.md             # (created later by /spec-kitty.tasks — NOT here)
```

### Source Code (repository root)

```
src/specify_cli/review/
├── pre_review_gate.py        # WP-A: delete census tier; WP-B: two predicates (:881,:1013); WP-C: SOURCE_MISMATCH
├── scope_source.py           # WP-A: factory home (resolve_scope_source); WP-B: ScopeBreakdownMixin mixin + predicates
├── baseline.py               # WP-C: artifact-before-teardown, source_identity field, from_dict default; WP-A(tail): unused-import + ruff fold
├── gate_registry.py          # WP-C: TransitionGateContext (unchanged shape)
└── verdict_aggregation.py    # WP-C: SOURCE_MISMATCH is WARN_PROCEED by allowlist (assert, no filter edit)

src/specify_cli/cli/commands/agent/
├── tasks_move_task.py        # WP-A: delete _mt_pre_review_gate_verdict, hoist _mt_resolve_scope_source, keep seams; WP-C: console-ladder branch (_mt_pre_review_gate_console_warning), consume #2874 kind-aware read seam
├── tasks.py                  # WP-A: compat re-export edit (golden 157→156)
└── workflow_executor.py      # WP-C: implement_capture_baseline injects the shared factory

tests/review/ + tests/specify_cli/cli/commands/agent/  # migrate 8 verdict-diff tests; parity/golden/guard tests
ruff.toml                     # WP-A(tail): tighten baseline.py legacy-debt entry
```

**Structure Decision**: single-project edit confined to the `review/` subsystem + its gate hook; no new packages. The one config touch (`ruff.toml`) is a one-line narrowing coupled to `baseline.py`.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` maps these to WPs. WP grouping (A cleanup / B contract / C correctness) and the A→C-hard, B-parallel sequencing are shown for context; the single hard cross-WP edge is IC-04 (factory hoist) → IC-09 (WP-C).

### IC-00 — Behavior-preservation golden capture (canonical harness)

- **Purpose**: Adopt the EXISTING canonical parity harness (`tests/review/fixtures/parity/_capture.py` + `tests/review/test_transition_gate_parity.py`) to capture the NFR-001 (registry hook) AND NFR-006 (override tier, **non-empty scope**) verdict/metadata tuples against the pinned base `eb06ca176` — asserting `HEAD==base` at capture, machine-emitting `base_commit` provenance — and commit them BEFORE any deletion. Prevents the circular-oracle trap; no improvised snapshot, no hand-typed SHA.
- **Relevant requirements**: NFR-001, NFR-006, NFR-007
- **Affected surfaces**: `tests/review/fixtures/parity/_capture.py` (extend), `tests/review/test_transition_gate_parity.py` (replay carrier), committed fixtures
- **Sequencing/depends-on**: none — **WP-A entry, strictly before IC-02**
- **Risks**: capturing after the deletion (circular oracle) — the harness's `HEAD==base` assertion forbids it; the override golden must drive a non-empty scope or NFR-006 passes vacuously (`run_scoped_tests_at_head` never runs).

### IC-01 — Pre-deletion sole-caller characterization (precondition)

- **Purpose**: Characterize (green-on-base) that the census branch is the *only* live caller reaching `evaluate_pre_review_gate` with `scope_source=None` — the load-bearing precondition that makes "no coverage lost" falsifiable.
- **Relevant requirements**: FR-002 (audit half)
- **Affected surfaces**: `pre_review_gate.py` (`evaluate_pre_review_gate`), a characterization test
- **Sequencing/depends-on**: IC-00 (WP-A entry)
- **Risks**: this is a **characterization precondition, not an ATDD red-first artifact** (it asserts a property already true on base); if a non-census `scope_source=None` caller exists, the whole WP-A premise changes — the audit must be exhaustive.

### IC-02 — Delete dead census tier + verdict helper + atomic compat edit

- **Purpose**: Remove `derive_test_scope` + census helpers/constants from `pre_review_gate.py` (live `scope_source.py` copy untouched) and the dead `_mt_pre_review_gate_verdict`, dropping the `filter_groups`/`composite_routing`/`scope_source=None` signature — in one atomic commit with the compat golden **157→156**.
- **Relevant requirements**: FR-001, FR-002 (deletion half), C-004; guards NFR-001, NFR-006, NFR-004
- **Affected surfaces**: `pre_review_gate.py`, `tasks_move_task.py` (`_mt_pre_review_gate_verdict`), `tasks.py:442` re-export, `test_tasks_compat_surface.py` (tuple + golden 157→156)
- **Sequencing/depends-on**: IC-01
- **Risks**: an accidental import break if the re-export/tuple/golden aren't edited atomically (C-004); KEEP-live set (`_CompositeRoute`, `evaluate_with_scope`, `run_scoped_tests_at_head`, `ScopeResult`, `_mt_pre_review_gate_with_override_scope`, `_mt_empty_scope_verdict`) must survive — guarded by the NFR-006 override-tier golden.

### IC-03 — Migrate/retire affected tests + coverage-parity inventory

- **Purpose**: Retire census-only tests, repoint the 2 `derive_test_scope`-oracle tests, and **migrate the 8 verdict-diff tests** (`test_pre_review_gate_engine.py:827,843,868,897,918,936,961,996`) from dropped-param to `scope_source=` injection — with an inventory mapping each retirement to a surviving equivalent.
- **Relevant requirements**: FR-004; guards NFR-003, NFR-004
- **Affected surfaces**: `test_census_parity.py`, `test_pre_review_scope_singlesource.py`, `test_pre_review_gate_engine.py`, `test_scope_source.py`
- **Sequencing/depends-on**: IC-02 (the param drop turns the 8 tests red → migrate to green)
- **Risks**: losing the unique verdict-diff coverage (NO_COVERAGE warn, terminal-interruption, sentinel/None-baseline degradation, NEW_FAILURES) if the 8 are retired instead of migrated — they MUST be migrated.

### IC-04 — Hoist the shared `ScopeSource` factory + seams

- **Purpose**: Extract `_mt_resolve_scope_source` to `scope_source.py` (already imported by both `baseline.py` and `pre_review_gate.py` → no new edge) importable by the head hook and the implement-time baseline path; keep the monkeypatched override seams in `tasks_move_task.py` and pass them as parameters (no `baseline.py→tasks_move_task.py` cycle). **The single artifact WP-C depends on.**
- **Relevant requirements**: FR-003; defines NFR-005
- **Affected surfaces**: `scope_source.py` (new `resolve_scope_source`), `tasks_move_task.py` (seams stay, factory call-site updated), `workflow_executor.py` (baseline call-site)
- **Sequencing/depends-on**: IC-02, IC-03 (natural WP-A order)
- **Risks**: an import cycle if the factory is placed wrong — the chosen `scope_source.py` home + parameterized seams avoid it; NFR-005 equivalence test pins identical `test_command()` + parse-mode at both call sites.

### IC-05 — Docs/comment hygiene + `baseline.py` boyscout fold

- **Purpose**: Scrub stale docstrings/CHANGELOG/plan-doc references to deleted symbols + dropped params; delete `baseline.py:25`'s unused `timezone` import and tighten its `ruff.toml` entry `["ARG001","F401","S314","S602"]` → `["ARG001","S314"]`.
- **Relevant requirements**: FR-013; guarded by NFR-002 + docs-freshness gate
- **Affected surfaces**: docstrings across the deleted surface, `CHANGELOG.md`/plan docs, `baseline.py:25`, `ruff.toml`
- **Sequencing/depends-on**: docs half after IC-02/IC-03; the `baseline.py` half lands as the **trailing** commit *after* WP-C rewrites `baseline.py` (cosmetic soft-edge onto IC-09, not a functional dependency)
- **Risks**: doing the `baseline.py` ruff-entry tighten before WP-C rewrites the file → premature; sequence it last.

### IC-06 — Split the welded `isinstance` into two independent predicates

- **Purpose**: Replace `isinstance(scope_source, ScopeBreakdownSource)` with `exposes_scope_breakdown` (capability, backed by the `isinstance`) and `empty_scope_is_coverage_gap` (policy, backed by a **distinct** `treats_empty_scope_as_coverage_gap` ClassVar marker) — different backing signals so the weld is provably gone, not renamed.
- **Relevant requirements**: FR-005
- **Affected surfaces**: `scope_source.py` (predicates + marker), `pre_review_gate.py:881,:1013` (call sites)
- **Sequencing/depends-on**: none (WP-B, parallel to A/C)
- **Risks**: making both predicates read the same signal (the carla-2 trap) — the ClassVar marker is what keeps them independent; a synthetic-source test must prove one-without-the-other.

### IC-07 — `file_to_scope` default projection (ABC/mixin)

- **Purpose**: Provide a `ScopeBreakdownMixin` ABC/mixin (NOT a Protocol default — won't reach structural implementers) giving `file_to_scope` as a projection over `scope_breakdown`, so `GateCoverageScopeSource` implements only `scope_breakdown`.
- **Relevant requirements**: FR-006
- **Affected surfaces**: `scope_source.py` (mixin + `GateCoverageScopeSource` inheritance)
- **Sequencing/depends-on**: none (independent of IC-06)
- **Risks**: `DeclaredCommandScopeSource` must remain a structural implementer with NO `scope_breakdown` (its absence is the "empty ≠ gap" signal) — the mixin must not force it to inherit.

### IC-08 — Migrate the intent-encoding test

- **Purpose**: Repoint the test pinning "membership ⇒ empty-is-gap" off the raw `isinstance` onto the two independent predicates, including a synthetic source satisfying one but not the other (US3 AS3).
- **Relevant requirements**: FR-007
- **Affected surfaces**: `test_scope_source.py:121-128`
- **Sequencing/depends-on**: IC-06
- **Risks**: the migrated test must fail against the old `isinstance`-only path and pass only post-IC-06 — proves decoupling.

### IC-09 — Artifact-parse-before-teardown + shared-factory injection (the B1 fix)

- **Purpose**: Inject the shared factory into `implement_capture_baseline` (activating `_capture_baseline_via_scope_source`) so baseline+head share one authority, AND read/relocate the baseline artifact to a stable out-of-worktree path *before* worktree teardown — closing the parse-after-teardown asymmetry that reintroduces the bug for `DeclaredCommandScopeSource` with a worktree-relative `--junitxml`.
- **Relevant requirements**: FR-008; enforces C-001/C-005
- **Affected surfaces**: `baseline.py` (`_capture_baseline_via_scope_source`, `capture_baseline`), `workflow_executor.py` (`implement_capture_baseline`)
- **Sequencing/depends-on**: **IC-04 (hard — the only cross-WP edge)**
- **Red-first carrier (post-plan squad)**: a **direct** `capture_baseline`/`_capture_baseline_via_scope_source` unit test with `DeclaredCommandScopeSource` + a **worktree-relative** `--junitxml`, asserted red on base *before* the relocate fix (the workflow-routed path is dormant on base). Split: factory-injection lands with the red observed, then relocate greens it. The relative `--junitxml` resolves against `cwd=tmp_worktree`, not process cwd.
- **Risks**: the B1 bug itself — a worktree-relative artifact deleted on teardown → text/synthetic identities → disjoint namespace.

### IC-10 — Record + assert source/parse-mode identity (kind-aware seam)

- **Purpose**: Add a `source_identity` (source class + parse-mode/artifact-presence — enough to catch B1's same-class-different-parse-mode) to `BaselineTestResult`; compute it via one helper used at both capture and diff; compare **only in `_evaluate_via_scope_source`** (never the override tier); read the baseline through #2874's `_resolve_workflow_read_dir(kind=WORK_PACKAGE_TASK)` seam; `from_dict` defaults a missing field to `UNVERIFIED_BASELINE`, not a spurious `SOURCE_MISMATCH`.
- **Relevant requirements**: FR-009
- **Affected surfaces**: `baseline.py` (`BaselineTestResult`, `from_dict`, `diff_baseline`), `pre_review_gate.py` (`_evaluate_via_scope_source`), `tasks_move_task.py` (identity read via the kind-aware seam)
- **Sequencing/depends-on**: IC-09
- **Risks**: firing the compare on the shared override tier (which has no injected source) → spurious mismatch; the "unknown → UNVERIFIED_BASELINE" default protects straddling-upgrade + sentinel artifacts.

### IC-11 — `GateOutcome.SOURCE_MISMATCH` + console-ladder exhaustiveness

- **Purpose**: Add a dedicated warn-shaped, fail-open `SOURCE_MISMATCH` (not `NO_COVERAGE`, not a block); add an explicit branch to `_mt_pre_review_gate_console_warning` and convert its trailing `return "…no new failures"` into an explicit `NO_NEW_FAILURES` branch + defensive `else` rendering `outcome.value` — closing the latent silent-clean-pass class for any future member.
- **Relevant requirements**: FR-011
- **Affected surfaces**: `pre_review_gate.py` (`GateOutcome`), `tasks_move_task.py:1156` (console ladder), `verdict_aggregation.py` (assert-only: SOURCE_MISMATCH absent from `_TERMINAL_OUTCOMES` + the NEW_FAILURES block → WARN_PROCEED by construction)
- **Sequencing/depends-on**: IC-10
- **Risks**: editing the allowlist filters instead of asserting them (they're member-explicit → fail-open by construction); missing the console fall-through (the exhaustiveness gap alphonso/#2874-lens flagged).

### IC-12 — Dual-impl/dual-parse-mode baseline↔head parity test

- **Purpose**: Prove baseline+head land in one failure-identity namespace under `GateCoverageScopeSource` AND `DeclaredCommandScopeSource`, for both a worktree-relative-JUnit case and a FAIL-text case (the B1 cases) — the SC-001/US1 proof; a deliberately mismatched pair raises `SOURCE_MISMATCH`.
- **Relevant requirements**: FR-010
- **Affected surfaces**: `tests/review/` (new parity test, 2 sources × 2 parse modes)
- **Sequencing/depends-on**: IC-09, IC-11
- **Risks**: a happy-path absolute-artifact case passing while the worktree-relative case (the real bug) is untested — all four combinations required.

### IC-13 — Anti-narrowing guard

- **Purpose**: Assert the baseline runs the WHOLE command, without head's per-file `scope.test_targets` appended, so a future refactor can't silently narrow baseline and break the broad-baseline/narrow-head invariant (C-005).
- **Relevant requirements**: FR-012
- **Affected surfaces**: `tests/review/` (guard test), `baseline.py` (the invariant it guards)
- **Sequencing/depends-on**: IC-09
- **Risks**: low — a targeted assertion; its value is preventing a future regression.

### IC-14 — Config-driven ScopeSource selection (delivers SC-001)

- **Purpose**: Make `resolve_scope_source` SELECT the source from config — `DeclaredCommandScopeSource` when `review.test_command` is present (non-pytest), else `GateCoverageScopeSource` — so a real non-pytest consumer repo runs baseline + head through one authority and **SC-001 is achievable against an actual repository** (not only IC-12's synthetic injection). Keeps `_capture_baseline_via_config`'s behavior alive via the portable source; fixes the stale `scope_source.py:51-55` "lands with #2873" comment + `docs/development/review-gates.md:174`.
- **Relevant requirements**: FR-014; makes SC-001 real; extends the FR-003/FR-008/NFR-005/FR-010 matrix to the selected `DeclaredCommandScopeSource` path
- **Affected surfaces**: `scope_source.py` (`resolve_scope_source` selection branch), `docs/development/review-gates.md`, the stale comment
- **Sequencing/depends-on**: IC-04 (the factory it makes selective); feeds IC-09/IC-10/IC-12 (the selected portable path is what makes the correctness proof real, not synthetic)
- **Risks**: the selection policy (presence of `review.test_command` ⇒ portable) must not accidentally route spec-kitty itself (which has no `review.test_command`) away from `GateCoverageScopeSource`; a wrong policy silently changes every consumer's gate. Test both branches.

---

### WP grouping, sequencing & coverage (context for /spec-kitty.tasks)

- **WP-A cleanup**: IC-01 → IC-02 → IC-03 → IC-04 (⇢ IC-05 docs; IC-05 baseline-tail lands last). **WP-B contract**: IC-06 → IC-08, IC-07 (parallel, no cross-WP edges). **WP-C correctness**: IC-09 → IC-10 → IC-11 → IC-12, IC-13 (IC-09 depends only on IC-04).
- **Hard cross-WP edges**: IC-04 → IC-09 (factory) and IC-04 → IC-14 (selection); IC-14 feeds IC-09/IC-10/IC-12 (the selected portable path makes the correctness proof real). Everything else within-WP. **Note (carla m2):** IC-02 (~450 LoC delete) and IC-06/IC-07 (edits at `pre_review_gate.py:881,:1013`) touch the same file — tasks must not schedule them as truly-simultaneous same-hunk edits.
- **FR coverage (no orphans)**: FR-001→IC-02, FR-002→IC-01+IC-02, FR-003→IC-04, FR-004→IC-03, FR-005→IC-06, FR-006→IC-07, FR-007→IC-08, FR-008→IC-09, FR-009→IC-10, FR-010→IC-12, FR-011→IC-11, FR-012→IC-13, FR-013→IC-05, **FR-014→IC-14**. NFR-001→IC-00(capture)+IC-02(replay), NFR-002→cross-cutting (carrier IC-05), NFR-003→cross-cutting (each IC's test), NFR-004→IC-02+IC-03, NFR-005→IC-04(defines)+IC-10/IC-14(consumes), NFR-006→IC-00+IC-02, **NFR-007→IC-00**. **Constraints: C-001→IC-09/IC-14, C-002→IC-02(keep-live golden), C-003→this WP graph, C-004→IC-02, C-005→IC-09/IC-13, C-006→every IC's red-first test.**
- **MVP / first-landable slice**: WP-A (IC-01→IC-04) + WP-C (IC-09→IC-13) — closes the P1 correctness bug (US1/SC-001/SC-004) and retires the dead duplicate WP-C's factory depends on. WP-B (IC-06/07/08) + IC-05 are zero-behavior-change hygiene, a fully-parallel fast-follow.
- **#2825 baseline-red-gotcha**: before attributing any `test_no_dead_symbols` / `test_golden_count_ban` failure (IC-02/03/11 touch that gate family) to this diff, confirm it's pre-existing red on `eb06ca176` via `PYTHONPATH=<worktree>/src` against `upstream/main` — do not green-wash a category-1 pre-existing red.
