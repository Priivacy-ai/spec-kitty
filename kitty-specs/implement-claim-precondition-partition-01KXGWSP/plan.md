# Implementation Plan: Partition-Aware Implement-Claim Precondition

**Branch**: `mission/2533-pr-bound-coord-claim-precondition` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/implement-claim-precondition-partition-01KXGWSP/spec.md`
**Tracker**: fixes [#2533](https://github.com/Priivacy-ai/spec-kitty/issues/2533) · parent [#2624](https://github.com/Priivacy-ai/spec-kitty/issues/2624) · cross-linked [#2160](https://github.com/Priivacy-ai/spec-kitty/issues/2160)

## Summary

The implement-claim precondition wrongly compares PRIMARY planning artifacts
(`spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`, `lanes.json`) against a single
collapsed *coordination* ref. On a solo PR-bound `coord`-topology mission whose
planning artifacts are committed on the feature branch (and absent on the empty
coord branch), every artifact reads as "changed" → the claim aborts with
"Planning artifacts not committed." This mission makes the precondition
**partition-aware**: each candidate artifact is compared against the ref where its
kind actually lives (PRIMARY → target/feature branch, COORD → coord ref), reusing
the existing per-kind authority in `mission_runtime/artifacts.py`. It is the
write/claim-side twin of the already-shipped read-side fix (WP08, `52211737b`).

**Technical approach (squad-validated):** the three precondition helpers currently
resolve "compare against which ref" inconsistently — `_files_changed_vs_ref`
short-circuits on a `None` ref (treats all files as changed) while
`_committed_meta_mapping` and `_drop_runtime_frontmatter_only_wp` fall back to
`HEAD`. Collapse that decision into one pure resolver,
`resolve_precondition_ref(coord_branch_for_filter) -> str | None`, that returns the
correct comparison ref per partition. This *is* the fix and simultaneously folds
the duplicated `ref or "HEAD"` idiom (a SAFE campsite item). The pure function is
trivially unit-testable (no subprocess / real repo), giving Sonar new-code
coverage on the new branch.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer, ruamel.yaml, GitPython-free `git` shell wrapper (`core/vcs`), internal `mission_runtime` shared package
**Storage**: Git refs (feature/target branch vs coordination branch); no database
**Testing**: `pytest` — pure unit tests on the ref resolver/classifier + real-`tmp_path`-git integration tests through the pre-existing `agent action implement` claim gate (harness template `test_implement.py::test_committing_content_already_on_coord_is_noop`); parallel-safe (`-n auto --dist loadfile`)
**Target Platform**: Spec Kitty CLI (Linux/macOS dev environments)
**Project Type**: single (Python CLI monorepo — `src/specify_cli/` + `src/mission_runtime/`)
**Performance Goals**: N/A (correctness fix; the precondition adds no new git calls beyond the ref-scoped diff already performed)
**Constraints**: `ruff` + `mypy --strict` zero new issues; per-function complexity ≤ 15; no new artifact-kind→partition mapping outside `mission_runtime/artifacts.py`; topology derivation unchanged; `mission_runtime/*` read-only
**Scale/Scope**: ~1 new pure helper + 3 consumer-helper edits + 2 call-site updates + 1 write-side ref block; 2 WPs; ~6 files of source, ~3 test files, 2 docs

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present; `charter context --action plan` returned **compact** mode (no
action-scoped directives/tactics beyond the standing orders). Relevant standing
governance for this mission:

- **Single canonical authority** — the fix consumes `mission_runtime/artifacts.py`
  (per-kind partition) rather than introducing a parallel classification. ✅ by design (NFR-004).
- **ATDD / red-first (DIRECTIVE_041)** — WP02 reproduces the defect through the
  pre-existing claim gate before the WP01 fix is asserted green. ✅
- **Campsite discipline (#1931)** — one SAFE fold (`ref or "HEAD"` → resolver) +
  one doc-sync; no unrelated refactor. ✅
- **Canonical sources / no legacy resolver paths** — no "if ref is None: fallback"
  scattered per-helper; the resolver is the single seam. ✅
- **Boundary guards** — `mission_runtime/*` and status-event placement untouched (C-001/C-002). ✅
- **DIR-013** — if any pre-existing test failure is encountered during implement,
  open a GitHub issue before treating it as baseline.

No Charter Check violations → **Complexity Tracking not required.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/implement-claim-precondition-partition-01KXGWSP/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (ref-resolution decision table)
├── quickstart.md        # Phase 1 output (repro walkthrough)
├── contracts/           # Phase 1 output (resolver signature contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/cli/commands/
├── implement_cores.py          # SEAM: add resolve_precondition_ref(); update
│                               #   _files_changed_vs_ref:406, _committed_meta_mapping:249,
│                               #   _drop_runtime_frontmatter_only_wp:387; keep
│                               #   _placement_coord_filter:562 return type stable
├── implement.py                # call site :542; write-side twin ref block ~632-642
└── agent/tasks_move_task.py    # call site :1400 via _mt_untracked_planning_artifact_paths:1364

src/mission_runtime/
└── artifacts.py                # READ-ONLY authority: kind_for_mission_file /
                                #   is_primary_artifact_kind / _PRIMARY_ARTIFACT_KINDS

tests/specify_cli/cli/commands/
├── test_implement_cores.py     # NEW pure unit tests for resolver; RE-PIN :287,:290
├── test_implement.py           # NEW red-first integration repro (claim succeeds)
└── test_wp06_sc2_paused_mission_blockers.py  # survives if _placement_coord_filter type stable

docs/architecture/
├── branch-target-routing.md    # campsite: correct :42-44 to kind-based partition
└── execution-lanes.md          # campsite: correct :78-82 See-Also blurb
```

**Structure Decision**: Single project. The change is localized to the
`specify_cli/cli/commands` implement-claim surface plus its docs; `mission_runtime`
is consumed read-only as the partition authority.

## Complexity Tracking

*Not applicable — no Charter Check violations.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Partition-aware precondition ref resolution (the seam)

- **Purpose**: Replace the inconsistent per-helper single-ref logic with one pure
  resolver so PRIMARY planning artifacts are compared against the ref where they
  live, eliminating the false "not committed" abort.
- **Relevant requirements**: FR-001, FR-002, FR-003, NFR-003, NFR-004; guards C-001, C-002.
- **Affected surfaces**: `implement_cores.py` (`resolve_precondition_ref` NEW,
  `_files_changed_vs_ref:406`, `_committed_meta_mapping:249`,
  `_drop_runtime_frontmatter_only_wp:387`, `resolve_planning_artifact_staging:454`);
  `implement.py` (call site `:542`, write-side twin `~632-642`);
  `tasks_move_task.py` (call site `:1400`). `mission_runtime/artifacts.py` READ-ONLY.
- **Sequencing/depends-on**: none (first).
- **Risks**: **Two-consumer lockstep** — `resolve_planning_artifact_staging` is
  called from both `implement.py:542` and `tasks_move_task.py:1400`; a signature
  change must move both in the same WP, and move-task swallows errors
  (`except: return ()`) so a break degrades silently → guard with a regression.
  **Brittle unit pins** — `test_implement_cores.py:287,290` encode the current
  `None → return all files` contract that changes; re-pin (not delete) in the same
  WP per the failing-test-remediation framework. Keep `_placement_coord_filter`
  return type stable so `test_wp06_sc2_...` survives.

### IC-02 — Red-first reproduction, move-task regression, and docs campsite

- **Purpose**: Prove the defect and the fix end-to-end through the real claim gate,
  guard the silent move-task consumer, and correct the stale single-ref docs.
- **Relevant requirements**: FR-004, FR-005, FR-006, NFR-001, NFR-002; SC-001..SC-004.
- **Affected surfaces**: `tests/.../test_implement.py` (NEW integration repro via
  `_ensure_planning_artifacts_committed_git:494` / `agent action implement`);
  `tests/.../test_implement_cores.py` or a move-task test (partition regression);
  `docs/architecture/branch-target-routing.md:42-44`, `execution-lanes.md:78-82`.
- **Sequencing/depends-on**: IC-01 (the fix must exist for the repro to go green;
  the RED assertion is authored first against unfixed code).
- **Risks**: **Sequencing gate** — open PR #2639 (observability-only, MERGEABLE)
  line-shifts `tasks_move_task.py:1364`; the WP touching that file rebases onto
  `upstream/main` after #2639 merges (line reconciliation only, no logic
  contention). #2570 WP01 (`e7cab2693`) is already in base — `implement_cores.py`
  churn absorbed, no signature reconciliation needed there.

## Work-Package Shape (advisory input to /spec-kitty.tasks)

- **WP01 (lane-a)** — IC-01: `resolve_precondition_ref` + 3 consumer helpers + both
  call sites in lockstep + write-side twin routing + pure unit tests + re-pin
  `test_implement_cores.py:287,290`.
- **WP02 (lane-b, depends WP01)** — IC-02: red-first integration repro + move-task
  partition regression + docs campsite.

LANES topology. **Revised to 3 WPs after the post-tasks anti-laziness squad** (see
below): WP01 read/compare seam; WP02 write-side partition commit; WP03 move-task
regression + docs. WP02 ⊥ WP03 (both depend only on WP01) → genuine parallel lanes b/c.

## Post-tasks Anti-Laziness Squad Revision (reviewer-renata + python-pedro, 2026-07-14)

The squad traced the design against live code and found the original contract
unbuildable. Corrections applied to the contract, spec, data-model, and WPs:

- **Resolver signature (BLOCKER-1):** must be per-path —
  `resolve_precondition_ref(repo_rel_path, coord_branch_for_filter) -> str`. The
  single-arg form returned one ref for all files and was a no-op.
- **`meta.json` routing (BLOCKER-2):** `kind_for_mission_file("…meta.json")` is `None`
  (self-bookkeeping allowlist, not the kind map), so `is_primary_artifact_kind(None)`
  is a mypy-strict error and misroutes it to coord. Use the None-safe
  `is_coordination_artifact_residue_path` and default to `"HEAD"`.
- **Public signature stable:** resolving per-path *inside* `resolve_planning_artifact_staging`
  means its public signature is unchanged → call sites (`implement.py:542`,
  `tasks_move_task.py:1400`) are not edited → **no `tasks_move_task.py` source edit →
  the PR #2639 rebase gate is dropped.**
- **Write-side sized in (operator decision):** FR-003 is a real two-transaction
  partition split (not a ref-line tweak) and is not exercised by the read-side repro →
  its own WP (WP02) with its own red test (dirty PRIMARY on coord → primary ref).
- **Test cites:** only `test_implement_cores.py:287` re-pins; `:290` is a still-valid
  missing-source test (untouched); the abort message is at `implement.py:319`.

## Scope Fences

- **OUT** — `pr_bound ⇒ coord` topology derivation (`mission_create.py:216-217`) → #2602.
- **DEFERRED (file a follow-up, do not implement)** — retire the bespoke
  `resolve_planning_artifact_staging` path into `commit_router.commit_for_mission`
  and correct the false `C-PLACE-1` docstring → #2160 placement-seam SSOT cluster.
- **Adjacent siblings (coordinate, do not fold)** — #2570 (allocator self-dirty,
  same seam, different root cause), #2549 (move-task COORD-leak, opposite direction).

## Pre-tasks Squad Verdict (planner-priti + paula-patterns, 2026-07-14)

- **Fold set:** `Closes #2533` ONLY. No open issue is genuinely closed by this diff
  besides #2533 (its read-side twin already shipped as WP08). #2570 / #2549A / #2646
  / #2334 / #2482 are adjacent but different consumers or root causes — folding any
  would over-claim (FR-005/C-001 mean the diff does not resolve them).
- **PR body cross-refs (do not close):** `Related: #2160, #2570, #2549, #2646, #2334`.
- **PR overlap:** no open PR implements `resolve_precondition_ref` (mission not
  redundant). Sequence AFTER PR #2639 (line-drift only — its hunks are all in the
  pre-review-gate cluster, none touch `tasks_move_task.py:1364/1400`). #2612 is
  unrelated source (review auto-commit); rebase-awareness only.
- **Degod position: ALIGNED-DOWNPAYMENT.** `implement_cores.py` is the *destination*
  of the already-landed Wave-2 coord-authority trio-degod (#2464/#2465/#2508,
  `ed336e034` in base), not a god-module to decompose. `resolve_precondition_ref`
  extends that canonical seam. **Guardrail:** keep the change additive inside
  `implement_cores.py`; do NOT drift into splitting `implement.py` /
  `tasks_move_task.py` (owned by still-open #2465 / the #2160 family). Stay surgical.
