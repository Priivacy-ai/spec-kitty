# Implementation Plan: Review Verdict Write Integrity

**Branch**: `research/3044-review-artifact-topology-seam` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/review-verdict-write-integrity-01KZ1CGF/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow.

## Summary

Approving a previously-rejected work package (WP) does not persist any artifact today — the stale `rejected` verdict remains authoritative for every terminal gate, forcing an operator override on the ordinary path. This mission generalizes the existing rejected-verdict writer (`create_rejected_review_cycle`) into a single verdict-aware writer that also handles `approved`, adds a feedback-source provenance guard that closes both the fabrication (#2996(b)) and content-wrapping (#990) defects in that same function, and — a post-plan adversarial squad's live-reproduction finding, folded in after this section's first draft — adds a commit step to that same writer, since it was found to never git-commit its output under any topology (closing #2697 as the same gap). #2646 is verified against the shipped writer rather than fixed by a separately-designed coord-authority read-router: a post-plan squad found that design type-shape broken and found live evidence the issue may already be closed by the writer existing at all.

## Technical Context

**Language/Version**: Python 3.11+ (repository standard; no new language/runtime requirement)
**Primary Dependencies**: None new. Uses existing internals: `mission_runtime.placement_seam`/`MissionArtifactKind`, `specify_cli.review.cycle`, `specify_cli.review.artifacts`, `specify_cli.status` (`ReviewResult`).
**Storage**: Filesystem — git-tracked Markdown artifacts (`review-cycle-N.md` with YAML frontmatter). No database involved.
**Testing**: pytest, targeted packages (`tests/review/`, `tests/post_merge/`, `tests/agent/`, `tests/regression/`) per this repo's scoped-change testing convention — not the full suite, per Testing Requirements.
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows via WSL) — unchanged from the project as a whole.
**Project Type**: Single project (this mission modifies the `spec-kitty` CLI package itself).
**Performance Goals**: No new performance target beyond NFR-003 (≤5% wall-clock regression on `move-task --to approved` / `spec-kitty merge --dry-run` versus pre-mission baseline).
**Constraints**: NFR-001 (zero regression in `tests/review/`, `tests/post_merge/`); C-001–C-004 from spec.md (no topology-seam re-architecture beyond FR-003's narrow scope, no verdict-vocabulary/cycle-numbering change, no coord/primary partition relitigation).
**Scale/Scope**: Touches 3–4 production modules (`review/cycle.py`, `review/artifacts.py`, `cli/commands/agent/tasks_move_task.py`, `agent_utils/status.py`) plus their test siblings. No new modules.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Assessed against `.kittify/charter/charter.md`'s Code Quality / Quality Gates sections:

- **Required pytest surface**: `tests/review/`, `tests/post_merge/`, `tests/agent/`, `tests/regression/` (scoped — not the full suite, per this repo's own scoped-change testing convention).
- **Type checking**: `mypy --strict` must pass on every touched module (`review/cycle.py`, `review/artifacts.py`, `tasks_move_task.py`; `agent_utils/status.py` only if FR-003's verification fails and a fix is built there).
- **Docstrings**: the generalized writer's new `verdict` parameter and any new public/module-level function need docstrings per the Code Review Checklist.
- **No regressions**: NFR-001 restates this explicitly as a spec-level requirement, not just a charter formality.
- **CHANGELOG**: this is a bug fix to internal review-cycle behavior, not a breaking public-API/CLI-surface change (existing callers of `create_rejected_review_cycle` keep working via a `verdict="rejected"` default) — a CHANGELOG entry is still warranted (user-visible behavior change: approvals now persist; `--skip-review-artifact-check` no longer needed on the ordinary path) even though it isn't a breaking change requiring a migration note.
- **PR requirements** (linear history, independent review): applies at merge time, not plan time — noted here so `/spec-kitty.tasks` and the eventual PR reflect it; an adversarial squad (as already run post-spec) is this mission's sanctioned independent-review mechanism.

No charter violations identified. Complexity Tracking table below is empty — no exceptions to justify.

## Project Structure

### Documentation (this mission)

```
kitty-specs/review-verdict-write-integrity-01KZ1CGF/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command) — not applicable, no new external contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/specify_cli/review/
├── cycle.py              # create_rejected_review_cycle generalized to a verdict-aware writer (FR-001);
│                          # feedback-source provenance guard added here (FR-002, closes #2996(b) + #990)
└── artifacts.py           # validate_review_artifact's hardcoded rejected-only check loosened to accept
                            # "approved" (C-002)

src/specify_cli/cli/commands/agent/
└── tasks_move_task.py      # _mt_finalize_plan / _mt_plan_review_result wired to call the generalized
                             # writer on the approve/done transition when the latest artifact is rejected (FR-001)

src/specify_cli/agent_utils/
└── status.py               # UNCHANGED unless FR-003's verification fails — see IC-02. Do not
                             # modify preemptively.

tests/
├── review/test_cycle.py                    # FR-001/FR-002 unit coverage; turns the two pre-existing
│                                            # red tests green (test_self_referential_feedback_source_is_rejected,
│                                            # test_new_cycle_body_never_duplicates_a_prior_cycle_file);
│                                            # plus new coverage asserting the write is git-committed
├── post_merge/                              # FR-001 merge-gate integration coverage (review_artifact_consistency)
└── regression/                              # new coord-topology regression verifying #2646 closes via
                                              # FR-001 alone (FR-003) — mirroring
                                              # test_2684_review_override_recognition.py's shape; only
                                              # gains an agent_utils/status.py-touching test if that
                                              # verification fails
```

**Structure Decision**: Single project (Option 1). This mission is entirely internal to the existing `spec-kitty` CLI package — no new top-level directories, no frontend/backend split, no new service boundary.

## Complexity Tracking

*No Charter Check violations identified — table intentionally empty.*

## Implementation Concern Map

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP.

### IC-01 — Approved-verdict writer, validator loosening, provenance guard, and commit step (merged; was IC-01+IC-02)

- **Purpose**: Generalize `create_rejected_review_cycle` into a single verdict-aware writer (operator-confirmed shape: generalize, not a new sibling function); loosen `validate_review_artifact`'s hardcoded rejected-only check to accept `approved`; wire `move-task --to approved`/`--to done` to call the writer whenever the WP's latest artifact is `rejected`; add the feedback-source provenance guard (path + content identity) that closes #2996(b) and #990 in the same function; and add a commit step (via the existing `commit_artifact` port capability) so every write — both verdicts — is actually committed, not left untracked. **Merged from the original separate IC-01/IC-02 split**: a post-plan squad (planner-priti lens) found the writer-generalization, provenance-guard, and commit-step subtasks (T001/T003/T004) all edit the same ~55-line `create_rejected_review_cycle` function with a stated sequential dependency. The validator-loosening subtask (T002) touches a distinct, separately-defined function (`validate_review_artifact`) in the same file — a post-tasks squad flagged that this narrower "adjacent function, small diff" framing is the accurate justification for including it here, not "same function." Either way, splitting any of these four into a separate WP bought no independent-reviewability (a reviewer of one piece would still need to read the others' diff to the same file to make sense of it) while doubling review overhead.
- **Relevant requirements**: FR-001, FR-002, C-001, C-002, C-003, NFR-001, NFR-002, NFR-003
- **Affected surfaces**: `src/specify_cli/review/cycle.py`, `src/specify_cli/review/artifacts.py`, `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- **Sequencing/depends-on**: none — foundational and self-contained. A post-plan squad (architect-alphonso, debugger-debbie lenses, live reproduction) confirmed the commit-target/branch-checkout path (`_ensure_target_branch_checked_out`) needs no hardening beyond adding the missing commit call itself — this concern does not depend on or share risk with IC-02 below.
- **Risks**: Existing callers of `create_rejected_review_cycle` must keep working unchanged — a `verdict="rejected"` default parameter preserves current call sites. The commit step must use the already-existing, already-tested `commit_artifact` port capability (do not hand-roll a new commit path) — confirmed available but currently unused for this write (`tasks_mark_status.py`/`tasks_map_requirements.py` are its only current callers). Content-based (not just path-based) duplicate detection for the provenance guard must not false-positive on legitimately similar feedback text between independent reviews.

### IC-02 — Verify #2646 against the shipped writer; fix only if verification fails (was IC-03; redesigned)

- **Purpose**: **This is not a design-and-build concern; it is a verify-first concern.** After IC-01 lands, drive a `lanes_with_coord` mission's WP through reject→approve using only the shipped writer and confirm via a checked-in regression test that `agent tasks status`'s stale-verdict scan (`_get_wp_review_verdict`, `agent_utils/status.py`) reports correctly — with zero changes to that module. A post-plan squad found live evidence that #2646's originally-reported coord/primary read-authority split already appears closed by an earlier, separately-merged mission, and that #2646 reproduces today only because IC-01's writer doesn't exist yet. The squad also found this concern's originally-planned mechanism (routing `_get_wp_review_verdict` through `resolve_snapshot_review`/`latest_review_artifact_verdict`) was type-shape broken — `ReviewOverride` carries no `verdict` field, so that reuse does not actually work as described. That design is dropped. #2697 is closed by IC-01's commit step, not by this concern.
- **Relevant requirements**: FR-003, NFR-001
- **Affected surfaces**: none, if verification passes (which is the expected, evidence-favored outcome). `src/specify_cli/agent_utils/status.py` plus a new `tests/regression/` fixture, only if verification fails.
- **Sequencing/depends-on**: none — independent of IC-01's files (`agent_utils/status.py` has no call-site overlap with `review/cycle.py`/`tasks_move_task.py`), safe to implement in a parallel lane, though its regression fixture logically runs *after* IC-01's writer exists to have something real to verify against.
- **Risks**: Low — this concern's main risk is skipping the verification step and building a fix anyway (the exact fakeable-DoD shape a post-plan squad flagged). The acceptance criterion must be a checked-in, executed regression test result, not a prose assertion that the issue "must be" fixed.
