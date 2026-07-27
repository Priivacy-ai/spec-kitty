# Implementation Plan: Autonomous Runtime Safety Follow-ups

**Branch**: `main` | **Date**: 2026-05-21 | **Spec**: `kitty-specs/autonomous-runtime-safety-followups-01KS52BD/spec.md`  
**Input**: Feature specification from `/private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260521-124440-zhQksA/spec-kitty/kitty-specs/autonomous-runtime-safety-followups-01KS52BD/spec.md`

Planning branch contract: current branch is `main`; planning/base branch is
`main`; merge target is `main`. Completed changes must merge into `main` unless
the human explicitly redirects the landing branch.

## Summary

Close six runtime-safety issues discovered by PR #1251 so autonomous Spec Kitty
missions can run from brief intake through retrospective without manual
workarounds. The plan keeps each issue independently shippable: retrospective
schema compatibility, decision closure, ownership validation, bulk-edit planning
pre-flight refinement, lane-collapse parallelism, and focused-PR documentation.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Typer CLI, Rich output, pydantic v2, ruamel.yaml, pytest, mypy strict  
**Storage**: Git-tracked mission artifacts under `kitty-specs/`; local runtime records under `.kittify/missions/`; YAML/JSON/JSONL files (`retrospective.yaml`, `meta.json`, task frontmatter, `lanes.json`, `status.events.jsonl`)  
**Testing**: Focused pytest packages per WP: `tests/cli/`, `tests/agent/`, `tests/tasks/`, `tests/runtime/`, `tests/architectural/`; mypy strict for touched modules  
**Target Platform**: Cross-platform Python CLI on Linux, macOS, and Windows 10+  
**Project Type**: Single Python CLI package with docs and mission artifacts  
**Performance Goals**: Lane computation and validation remain bounded by mission WP count; no new full-repo scans outside existing architectural/doc tests  
**Constraints**: No new pip dependencies; preserve public contracts called out in the spec; run SaaS/sync-specific commands with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this machine, but this mission's local planning commands are not SaaS/tracker/sync test flows  
**Scale/Scope**: Six WPs, six GitHub issues, one repo (`Priivacy-ai/spec-kitty`), no cross-repo code changes

## Charter Check

Status: PASS with one operational note.

- Stack alignment: changes stay within Typer, Rich, ruamel.yaml, pydantic,
  pytest, and mypy strict.
- Test expectation: each WP owns focused tests for its changed behavior and
  targets at least 90% coverage for new code.
- Typing expectation: touched typed modules must remain `mypy --strict` clean.
- Dependency expectation: no new pip dependencies.
- Operational note: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` was attempted for planning
  and correctly failed with `SAAS_SYNC_UNAUTHENTICATED` because the temp
  checkout is not authenticated. Since this mission does not test hosted auth,
  tracker, or sync behavior, local planning proceeds without the env var. Any
  later hosted/sync-specific test command must use the env var or authenticate
  first.

## Project Structure

### Documentation (this feature)

```
kitty-specs/autonomous-runtime-safety-followups-01KS52BD/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── runtime-safety-followups.md
├── spec.md
├── tasks.md
└── tasks/
```

### Source Code (repository root)

```
src/specify_cli/
├── retrospective/
│   ├── reader.py
│   ├── schema.py
│   └── writer.py
├── cli/commands/
│   ├── agent_retrospect.py
│   ├── decision.py
│   ├── implement.py
│   └── agent/
│       ├── mission.py
│       └── workflow.py
├── decisions/
│   ├── models.py
│   ├── service.py
│   └── verify.py
├── bulk_edit/
│   ├── gate.py
│   ├── inference.py
│   └── occurrence_map.py
├── lanes/
│   ├── compute.py
│   └── models.py
├── mission_metadata.py
└── acceptance/
    └── __init__.py

tests/
├── cli/
├── agent/
├── tasks/
├── runtime/
├── architectural/
└── docs/ or docs-facing tests as needed

docs/
├── how-to/
└── reference/tutorial/explanation pages as discovered for the focused-PR path
```

**Structure Decision**: This is a single-repo CLI/runtime mission. Each WP owns a
small, explicit runtime surface and its nearest tests. The docs WP owns only
workflow/how-to documentation and does not touch runtime code.

## Phase 0: Research Findings

See `research.md` for issue-by-issue evidence and source mapping. Key outcomes:

- #1255 is localized to retrospective reader/writer/schema compatibility and
  synthesize command tests.
- #1256 is localized to decision state transitions, verifier rules, and
  acceptance marker handling.
- #1235 and #1257 overlap at WP ownership metadata, but one is finalization
  validation and the other is implementation pre-flight classification.
- #1236 is localized to `src/specify_cli/lanes/compute.py`; merge already
  consumes multi-lane manifests.
- #1258 is docs-only, with `TARGET_BRANCH_NOT_SYNCHRONIZED` as the trigger.

## Phase 1: Design

### WP01: Retrospect Schema Reconciliation (#1255)

Preferred implementation: make the synthesize reader accept the complete record
shape written by `retrospect create`. If the existing create-side model is the
most complete source of truth, refactor shared fields into a common pydantic
model. If that expands blast radius too much, set the synthesize reader model to
ignore informational extras and add regression tests around the exact
create-written fields from the issue.

Tests:

- Add or extend `tests/cli/test_agent_retrospect_synthesize.py` with a
  create-shaped record fixture.
- Cover default dry-run and `--apply`.
- Preserve missing/malformed/I/O error tests.

### WP02: Decision Deferred Closure (#1256)

Preferred implementation: allow `deferred -> resolved` in
`src/specify_cli/decisions/service.py` when `resolve_decision` receives a final
answer. Keep `open`, `defer`, and `cancel` contracts unchanged. Update
`src/specify_cli/decisions/verify.py` so absence of a marker is not drift when
the decision status is resolved. Update acceptance marker handling where it
classifies outstanding `needs_clarification` items.

Tests:

- CLI/service test for open -> defer -> resolve.
- Verifier test for removed marker after closure.
- Acceptance test for no outstanding clarification when the decision is closed.

### WP03: `kitty-specs/` Owned-Files Validation (#1235)

Preferred implementation: validate WP frontmatter during `finalize-tasks` and
reject any `owned_files` value that starts with `kitty-specs/`. Return a
structured error in JSON mode containing at least `wp_id`, `path`, and a stable
error code such as `OWNED_FILES_KITTY_SPECS_PATH`. Apply the same validation in
`--validate-only` and real finalization.

Tests:

- Unit/CLI test in `tests/tasks/` or `tests/agent/` for validate-only and full
  finalization failures.
- Architectural test in `tests/architectural/` scanning WP frontmatter for
  `kitty-specs/` owned-file entries.

### WP04: Bulk-Edit Planning Pre-flight (#1257)

Preferred implementation: in implementation pre-flight, inspect the claimed
WP's frontmatter. If it owns `occurrence_map.yaml` or a path under the mission
artifact directory, classify the warning as bulk-edit planning and do not block
that WP on `--acknowledge-not-bulk-edit`. Preserve the blocking gate for active
rewrite WPs and for missions explicitly marked `change_mode: bulk_edit` without
valid occurrence-map coverage.

Tests:

- Implement command test for inferred bulk-edit text plus occurrence-map-owned
  WP passing without acknowledgement.
- Negative test proving active rewrite WP still blocks when classification is
  missing or occurrence map is invalid.

### WP05: Lane-Collapse Algorithm Refinement (#1236)

Preferred implementation: change collapse decisions in
`src/specify_cli/lanes/compute.py` from dependency-only to
dependency-plus-overlap for code-change WPs. Direct dependencies with overlapping
`owned_files` collapse. Direct dependencies with disjoint ownership may stay in
separate lanes if lane dependency ordering can express the relationship.
Transitive-only relationships through a fan-in WP must not collapse disjoint
upstreams; the fan-in lane depends on upstream lanes.

Tests:

- Fixture with six disjoint workstreams plus fan-in WP produces six upstream
  lanes and a synchronized fan-in lane/dependency shape.
- Regression fixture for overlapping owned files still collapses.
- Verify `collapse_report` records overlap/dependency evidence clearly.

### WP06: Focused-PR Workflow Documentation (#1258)

Preferred implementation: update the standing mission workflow doc if present,
and update/create `docs/how-to/run-an-autonomous-mission.md` or the closest
existing autonomous-run how-to. Cite `TARGET_BRANCH_NOT_SYNCHRONIZED`, include
the focused branch commands, note that PR #1251 succeeded with direct PR from
`kitty/mission-<slug>` into `main`, and recommend squash-merge.

Tests:

- Docs-only lint/check if existing docs tests cover toc or generated references.
- Manual review of command snippets.

## Data Model

See `data-model.md`. No new persistent storage system is introduced. The design
changes interpretation and validation of existing models:

- Retrospective record schema.
- Decision status transition and verifier state.
- WP ownership metadata.
- Bulk-edit planning classification.
- Lane manifest collapse/dependency metadata.

## Contracts

See `contracts/runtime-safety-followups.md` for command-level contracts and
expected JSON/error behavior.

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Retrospective model refactor broadens schema behavior too much | Prefer shared model only if local tests stay tight; otherwise ignore informational extras only in reader |
| Decision closure hides genuinely unresolved questions | Require explicit resolve/final answer or explicit new close-with-default action; do not treat deferred as resolved automatically |
| `kitty-specs/` rejection blocks valid planning-artifact WPs | Pair #1235 with #1257 and document the mission-branch/planning-artifact route clearly |
| Bulk-edit planning bypass weakens active bulk-edit safety | Add negative tests for active rewrite WPs and `change_mode: bulk_edit` gates |
| Lane parallelism creates merge conflicts | Keep owned-file overlap collapse and lane dependency ordering; add fan-in fixture coverage |
| Docs target path is ambiguous | Prefer existing workflow docs and create `docs/how-to/run-an-autonomous-mission.md` if no exact page exists |

## Complexity Tracking

No charter violations. The mission touches multiple runtime areas because the
six filed issues are independent surfaces, but each WP remains scoped and
independently reviewable.

## Re-check Charter After Design

Status: PASS.

- No new dependencies.
- Tests are assigned per behavior surface.
- Public contracts are preserved except the explicitly requested closure path for
  deferred decisions.
- All material decisions are captured in this plan and the contract artifact.

Planning branch contract repeated: current branch is `main`; planning/base branch
is `main`; merge target is `main`.
