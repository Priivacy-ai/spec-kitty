# Implementation Plan: Implement Review Retrospect Reliability
*Path: kitty-specs/implement-review-retrospect-reliability-01KQQSCW/plan.md*

**Branch**: `main` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)  
**Input**: Mission specification from `kitty-specs/implement-review-retrospect-reliability-01KQQSCW/spec.md`  
**Mission ID**: `01KQQSCWP7HAJRR93F98AESKH4`  
**Mission Type**: `software-dev`

## Summary

Implement a narrow shared review-cycle domain boundary that owns rejected review-cycle validity before status/state pointers change. The boundary will cover review artifact creation, required YAML frontmatter validation, canonical `review-cycle://...` pointer generation and resolution, legacy `feedback://` normalization, and rejected `ReviewResult` derivation for outbound `in_review` transitions. Existing CLI paths will call that boundary instead of each re-encoding the invariant. Separate focused changes will make `spec-kitty next` prefer finalized task/WP state over stale early mission phase state and add a first-class completed-mission retrospective initialization or synthesis path.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer, Rich, ruamel.yaml, pytest, pydantic, ulid  
**Storage**: Local mission files under `kitty-specs/<mission>/`, canonical status events in `status.events.jsonl`, review-cycle markdown artifacts under `kitty-specs/<mission>/tasks/<WP-slug>/`, retrospective records under `.kittify/missions/<mission_id>/retrospective.yaml`  
**Testing**: Focused pytest unit tests for the shared review-cycle boundary, CLI integration tests with `CliRunner`, status transition tests, next-routing regression fixtures, and retrospective command JSON tests  
**Target Platform**: Cross-platform Spec Kitty CLI on Linux, macOS, and Windows 10+  
**Project Type**: Single Python CLI/library package  
**Performance Goals**: Typical affected CLI paths remain under the charter target of 2 seconds for normal projects; pointer resolution and artifact validation perform bounded filesystem reads for one WP review cycle  
**Constraints**: Do not redesign the review runtime; do not replace the event log; do not duplicate merged PR #959 scope unless a relevant fix is still absent; local-only fixture commands may use `SPEC_KITTY_ENABLE_SAAS_SYNC=0` only when they do not touch hosted auth, tracker, SaaS sync, or sync finalization; any hosted/sync path on this computer must use `SPEC_KITTY_ENABLE_SAAS_SYNC=1`  
**Scale/Scope**: One narrow domain boundary plus adapters in existing review/status/workflow/next/retrospective surfaces; regression coverage for #960, #962, #963, #961, and #965; #967, #966, #964, and #968 deferred unless naturally adjacent

## Engineering Alignment

The shared boundary is intentionally small and boring. It is not a new review runtime, not a new state machine, and not a replacement for `emit_status_transition`. It is a pre-mutation invariant boundary used by CLI callers before they write review artifacts, review pointers, or outbound `in_review` events. The acceptance rule is: a rejected review cycle is valid, canonical, and resolvable before any status/state pointer changes.

The main adapter sequence for #960/#962/#963 is:

1. `agent tasks move-task ... --to planned --review-feedback-file <path>` resolves the WP slug and source feedback file.
2. The shared review-cycle boundary builds and validates a rejected artifact, writes it atomically or fail-closed, returns a canonical pointer, and derives a `ReviewResult(verdict="changes_requested", reference=<canonical-pointer>)`.
3. The move-task path calls `emit_status_transition` with both `review_ref` and `review_result` for outbound `in_review -> planned` or `in_review -> in_progress` rejection transitions.
4. Fix-mode prompt loading resolves that same canonical pointer through the shared resolver and renders the focused rejection context.

The next-routing fix for #961 should stay in the existing `next/runtime_bridge.py` and `next/decision.py` layer. The rule is that finalized tasks and canonical WP lanes override stale runtime/phase discovery state for implement-review routing.

The retrospective fix for #965 should stay in the `agent retrospect` command family and `retrospective` package. It should add an explicit missing-record path: either `capture`/`init` plus a structured synthesize diagnostic, or synthesize auto-initialization from completed mission artifacts. The plan prefers explicit `capture`/`init` if available mission artifacts are insufficient, but allows auto-initialization when the completed mission record can be generated deterministically.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter Area | Result | Plan Response |
| --- | --- | --- |
| Python 3.11+ CLI/library code | Pass | All work remains in `src/specify_cli/` Python modules. |
| Typer/Rich/ruamel.yaml/pytest/mypy stack | Pass | Reuse existing CLI, frontmatter, status, and test stack. |
| 90%+ coverage for new code | Pass with implementation obligation | New domain boundary requires focused unit coverage plus CLI integration regressions. |
| Integration tests for CLI commands | Pass with implementation obligation | `move-task`, fix-mode, `next`, and `agent retrospect` paths each get targeted command-level tests. |
| CLI operations under 2 seconds for typical projects | Pass | Boundary work is bounded to one WP artifact directory and one status transition. |
| Cross-platform behavior | Pass | Use `pathlib`, existing atomic file helpers where appropriate, and avoid shell-specific test assumptions. |
| Branch terminology | Pass | Current branch, planning/base branch, and merge target are all `main` from deterministic setup-plan JSON. |
| Mission terminology canon | Pass with vigilance | New user-facing text must use Mission/Missions and `--mission`; no new active `feature*` aliases. |
| External package boundaries | Pass | No change to `spec-kitty-events`, `spec-kitty-tracker`, or standalone runtime dependency boundaries. |
| SaaS contract | Pass | This mission targets local CLI state. Hosted SaaS contract changes are out of scope unless implementation discovers sync payload changes. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/implement-review-retrospect-reliability-01KQQSCW/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── review-cycle-domain.md
│   ├── next-routing.md
│   └── retrospective-cli.md
└── tasks.md             # Created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── review/
│   ├── artifacts.py                 # Existing artifact dataclasses/readers
│   └── cycle.py                     # New narrow review-cycle boundary
├── cli/commands/
│   ├── agent/tasks.py               # move-task adapter for rejection transitions
│   ├── agent/workflow.py            # fix-mode/review prompt adapter for pointer resolution
│   └── agent_retrospect.py          # completed-mission retrospective path
├── status/
│   ├── models.py                    # Existing ReviewResult contract
│   ├── transitions.py               # Existing review_result guard
│   └── emit.py                      # Existing validated transition pipeline
├── next/
│   ├── decision.py                  # Existing Decision contract and WP helpers
│   └── runtime_bridge.py            # finalized WP state routing override
└── retrospective/
    ├── reader.py
    ├── writer.py
    └── schema.py

tests/
├── review/
│   └── test_cycle.py                # New shared-boundary unit coverage
├── integration/review/
│   └── test_reject_from_in_review.py
├── agent/
│   └── test_workflow_review_cycle_pointer.py
├── next/
│   └── test_finalized_task_routing.py
└── cli/
    └── test_agent_retrospect_missing_record.py
```

**Structure Decision**: Keep the reusable invariant in `src/specify_cli/review/cycle.py` and adapt existing callers. This keeps review-cycle concerns local to the existing `review` package, while leaving status validation, next routing, and retrospective behavior in their current packages.

## Complexity Tracking

No charter violations are planned. The only new abstraction is justified because at least three current paths encode related pieces of the same invariant: `agent/tasks.py` writes rejected artifacts and pointers, `agent/workflow.py` resolves pointers and feeds fix-mode, and `status/transitions.py` requires structured `review_result` for outbound `in_review` transitions. Consolidating only artifact/pointer/result validity reduces duplication without changing the broader review runtime.

## Phase 0: Research Findings

See [research.md](research.md). Key decisions:

- Use `src/specify_cli/review/cycle.py` as the shared invariant boundary.
- Extend or wrap `ReviewCycleArtifact` validation rather than replace it.
- Preserve `emit_status_transition` as the only status mutation gateway.
- Add next-routing override in the existing runtime bridge layer.
- Add a structured missing-record path for `agent retrospect synthesize`, with an optional explicit capture/init command if auto-initialization cannot be deterministic.

## Phase 1: Design Artifacts

See:

- [data-model.md](data-model.md)
- [contracts/review-cycle-domain.md](contracts/review-cycle-domain.md)
- [contracts/next-routing.md](contracts/next-routing.md)
- [contracts/retrospective-cli.md](contracts/retrospective-cli.md)
- [quickstart.md](quickstart.md)

## Post-Design Charter Check

| Charter Area | Result | Notes |
| --- | --- | --- |
| Specification fidelity | Pass | Each design artifact maps back to FR-001 through FR-011. |
| Decision documentation | Pass | Material boundary decisions are recorded in `research.md` and this plan. |
| Locality of change | Pass | Changes stay in existing packages with one narrow shared module. |
| Mission terminology | Pass | Contracts use `--mission` and active Mission wording. |
| Testing expectations | Pass | Quickstart and contracts identify focused unit, integration, and smoke verification. |

## Historical Stop Point

This was the `/spec-kitty.plan` stop point before `/spec-kitty.tasks` ran. It is now historical: `tasks.md` and flat WP prompt files have been generated and finalized for this mission.
