---
work_package_id: WP12
title: ADR + Docs + Upstream Events Tracking
dependencies:
- WP05
- WP07
requirement_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T062
- T063
- T064
- T065
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: docs/
execution_mode: planning_artifact
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- architecture/2.x/adr/2026-04-27-1-retrospective-gate-shared-module.md
- docs/retrospective-learning-loop.md
- docs/migration/retrospective-events-upstream.md
priority: P3
status: planned
tags: []
---

# WP12 — ADR + Docs + Upstream Events Tracking

## Objective

Document the AD-001 gate-shared-module decision in an ADR; ship an operator overview doc and an upstream-events cutover runbook; open the upstream `spec_kitty_events` issue and record its link in the local events module.

## Spec coverage

- Charter **DIRECTIVE_003** (Decision Documentation Requirement) — material technical decisions captured.
- Charter **DIRECTIVE_010** (Specification Fidelity Requirement) — supports.

## Context

- AD-001 is the architectural decision to put the gate in a single shared module rather than burying it in WP-level status code or in `next/` internals. The ADR justifies this against the alternatives.
- The operator doc is a polished version of [`../quickstart.md`](../quickstart.md) suitable for `docs/`.
- The cutover runbook documents the mechanical swap from local `specify_cli.retrospective.events` to upstream `spec_kitty_events.retrospective.*` once the upstream PR ships.
- The upstream issue tracks the eight retrospective event names + payload contracts for inclusion in the next `spec_kitty_events` release. Open the issue against the `spec_kitty_events` repo and record its URL in the local module's docstring (replacing the `<TODO: WP12>` marker added in WP03 / WP14 of the boundary test).

## Subtasks

### T062 — ADR for AD-001

Path: `architecture/2.x/adr/2026-04-27-1-retrospective-gate-shared-module.md`.

Use the project's existing ADR template (see neighboring ADRs in `architecture/2.x/adr/`). Sections:

- **Status**: Accepted.
- **Context**: lifecycle gate must be consulted from `specify_cli.next` (canonical control loop) and from any future status-transition surface that needs mission-level mode policy. WP-level transitions are governed by per-WP transition matrix and are the wrong layer for mission-mode policy.
- **Decision**: place the gate in `specify_cli.retrospective.gate` as a single source of truth. Both callers stay thin.
- **Consequences**: callers do not duplicate gate logic; gate is unit-testable in isolation; `next` and status-transition surfaces both depend on the retrospective package.
- **Alternatives considered**: (A) gate in `status.transitions` (rejected: wrong layer); (B) gate buried in `next` (rejected: requires status callers to reach into runtime internals).
- **References**: link to `kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/plan.md` AD-001 and the `gate_api.md` contract.

### T063 — Operator overview doc

Path: `docs/retrospective-learning-loop.md`.

Audience: spec-kitty operators (humans running missions). Content: the seven scenarios from `quickstart.md`, polished and de-duplicated, with absolute paths and CLI examples kept current. Cross-link to the relevant FR/NFR ids in `spec.md`.

If the project uses `mkdocs` or similar, register the new page in the docs nav (one-line edit; declare scope and request reviewer confirmation).

### T064 — Cutover runbook

Path: `docs/migration/retrospective-events-upstream.md`.

Content: the cutover steps from `contracts/retrospective_events_v1.md` "Cutover note" — verify upstream shapes, bump version pin, swap imports, delete local module, unskip the boundary test. Include a verification checklist:

- [ ] `pip install spec_kitty_events>=<X>` resolves.
- [ ] `python -c "from spec_kitty_events import retrospective"` succeeds.
- [ ] All eight names import: Requested, Started, Completed, Skipped, Failed, ProposalGenerated, ProposalApplied, ProposalRejected.
- [ ] Existing tests still pass after import swap.
- [ ] The boundary test in `tests/architectural/test_retrospective_events_boundary.py` is unskipped and passes.
- [ ] No `class *Event` Pydantic definitions remain under `src/specify_cli/retrospective/`.

### T065 — Open upstream issue + record link

1. Open an issue against the `spec_kitty_events` repo (assume it lives under the same org as this project; see `pyproject.toml` for the canonical name). Title: "Add retrospective lifecycle events (8) to public surface."
2. Body: link to this mission's plan + contracts; paste the eight event names and their payload contract field minimums.
3. Take the issue URL.
4. Edit `src/specify_cli/retrospective/events.py` (file owned by WP03 — coordinate or pass the URL to WP03's owner via a small follow-up patch) to replace the `<TODO: WP12>` marker with the real URL.
5. Edit `tests/architectural/test_retrospective_events_boundary.py` (file owned by WP03) similarly.

If WP03 has already merged: this WP issues a small `events.py` and `test_retrospective_events_boundary.py` edit-only patch and explicitly notes the cross-WP dependency in the PR description; the architectural overlap is a one-line edit and acceptable. If WP03 has not yet merged, coordinate so WP03 absorbs the URL before merging.

## Definition of Done

- [ ] ADR file exists, follows project template, references AD-001.
- [ ] Operator doc renders cleanly (no broken links).
- [ ] Cutover runbook is actionable from start to finish.
- [ ] Upstream issue is opened; URL is recorded in the local events module and boundary test.
- [ ] No changes outside `owned_files` except the documented one-line edits in `events.py` / boundary test (with justification and reviewer ack).

## Risks

- **Cross-WP file edit**: the URL needs to land in `events.py` which is owned by WP03. Document the coordination explicitly; reviewer accepts the small overlap as a one-line patch.

## Reviewer guidance

- Read the ADR end-to-end for clarity.
- Walk the cutover runbook checklist; ensure each step has a concrete command.
- Confirm the upstream issue URL is real (resolves on github.com).

## Implementation command

```bash
spec-kitty agent action implement WP12 --agent <name>
```
