# Implementation Plan: Implement-Loop Coord-Authority Completion

**Branch**: `design/coord-authority-remediation-2160` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/implement-loop-coord-authority-completion-01KW2E7A/spec.md`

## Summary

Adopt the existing kind-aware read seam `resolve_planning_read_dir(kind=...)` at every
implement/review-loop read site that currently reads a PRIMARY-kind artifact
(`tasks/`, `WP*.md`, `lanes.json`, WP-frontmatter) off a coordination-aware resolver,
so a coordination-topology mission finalized after #2106 reads from the primary surface
instead of the empty `-coord` husk. Harden the dir-read ratchet (inline-call-shape aware,
whole-`src` scope, mandatory self-test) so the residual census is no longer vacuous, and
triage the full surfaced set — routing this mission's loop surface and pinning the
out-of-scope clusters (the `merge/`+`lanes/` `lanes.json` cluster → sibling mission; the
`meta.json` identity-read class → identity ticket) with tracking references. Close the
already-remediated #2140 with a negative-assertion regression pin, and fold #2183 (teach
the resolution-gate discriminator the second canonicalizer seam, recompute the floor).

Approach is squad-grounded (pre-spec + post-spec adversarial squads + a fan-out FR-008
sweep over all 111 coord-aware call sites — see `research.md`). The scope was corrected
~3× upward from the originally-named six residuals and then split on a path boundary.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `ast` (scanner), existing `resolve_planning_read_dir` seam (`src/specify_cli/missions/_read_path_resolver.py`), `MissionArtifactKind` partition (`src/specify_cli/mission_runtime/artifacts.py`); typer/rich (CLI surfaces). No new third-party dependencies.
**Storage**: Filesystem mission artifacts (kitty-specs/<mission>/), coordination worktree (STATUS-only), primary checkout (planning artifacts). No DB.
**Testing**: pytest (`tests/architectural/`, `tests/integration/`, `tests/git/`), the dir-read literal-ban + resolution-authority architectural gates, a new shared coord-topology fixture (un-stubbed). Parallel run `-n auto --dist loadfile`; real-port/daemon tests serial.
**Target Platform**: Linux/macOS/Windows dev environments running the spec-kitty CLI.
**Project Type**: single (Python CLI package `src/specify_cli/`).
**Performance Goals**: N/A (correctness/structural mission; no hot path). Scanner self-test must stay within the existing architectural-gate runtime budget (~tens of seconds).
**Constraints**: Behavior-neutral for flat/single-branch topologies (regression-guarded); STATUS-partition reads unchanged (C-001); gate floors shrink-only / raise-only-upward; no new `# noqa`/`# type: ignore`; complexity ≤ 15; gate hardening + floor raises validated by a merged-branch verbatim dry-run (NFR-005, gate-unmask-cannot-self-validate).
**Scale/Scope**: ~20 in-scope ROUTE functions across `cli/commands/agent/`, `workspace/`, `context/`, `task_utils/`, plus gate hardening + #2140 + #2183 + fixture + triage. 111 coord-aware call sites swept; this mission owns the loop-read subset.

## Charter Check

*GATE: software-dev-default charter (compact mode). Directives DIR-001..DIR-013 apply.*

- **Terminology Canon (Mission not Feature):** touched code uses legacy `feature_dir`
  variable names; this mission re-points resolvers but does not rename — no new
  `feature*` terms introduced in canonical/user-facing surfaces (variable-local names
  are pre-existing; rename is out of scope). PASS.
- **ATDD-first / red-first (C-011):** every routed site gets a RED-first per-site test
  through the pre-existing entry point against the un-stubbed coord-topology fixture
  (FR-014). PASS by design.
- **`__all__` convention (C-007 charter):** dead-symbol removal (FR-013) respects export
  hygiene. PASS.
- **Shared package boundary:** no change to `src/runtime/` or external contract packages.
  PASS.
- No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/implement-loop-coord-authority-completion-01KW2E7A/
├── plan.md              # This file
├── research.md          # FR-008 fan-out sweep + adjudication (Phase 0)
├── data-model.md        # Artifact-kind partition + residual taxonomy (Phase 1)
├── quickstart.md        # Dev verification flow (Phase 1)
├── contracts/           # Seam + gate behavioral contracts (Phase 1)
├── traces/              # tooling-friction / approach / design tracer files
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── missions/
│   ├── _read_path_resolver.py     # the seam (resolve_planning_read_dir); dead-symbol removal (FR-013)
│   └── _substantive.py            # is_committed docstring + #2140 (FR-010)
├── cli/commands/agent/
│   ├── tasks.py                   # status/list_tasks/finalize/map-reqs routing + mixed-read splits (FR-001/003/004)
│   ├── workflow.py                # implement/review/_resolve_review_context/_preview/_find_first_for_review_wp (FR-002)
│   ├── tasks_dependency_graph.py  # build_dependency_graph read (FR-004)
│   └── tasks_parsing_validation.py# research-artifact read (FR-004)
├── workspace/context.py           # build_normalized_wp_index/resolve_workspace_for_wp (FR-005)
├── context/resolver.py            # MissionContext WP-frontmatter (FR-004)
├── task_utils/support.py          # locate_work_package (FR-005)
└── cli/commands/validate_tasks.py # WP-frontmatter leg (FR-004)

tests/architectural/
├── test_gate_read_literal_ban.py  # scanner: inline-shape + whole-src + self-test + pin triage (FR-007/008/009)
├── test_resolution_authority_gates.py # is_def_use_canonical fold (FR-011) + floor recompute (FR-012)
└── resolution_gate_allowlist.yaml # allowlist shrink 7→3 (FR-011)

tests/<integration|git>/           # coord-topology fixture + per-site RED-first coverage (FR-014)
```

**Structure Decision**: Single Python package. Changes are surgical resolver re-points
at call sites plus test-surface (gate + fixture) work; no new modules or packages. The
seam, the artifact-kind partition, and the gate already exist — this mission consumes and
hardens them.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs. One concern may become several WPs; small ones may merge.

### IC-01 — Gate hardening (scanner + floor)

- **Purpose**: Teach the dir-read ratchet the inline-call shape and widen its scope to all
  of `src/specify_cli/`, with a mandatory self-test; recompute the routed-canonicalizer
  floor strictly below the post-fix live census. Makes the residual census non-vacuous.
- **Relevant requirements**: FR-007, FR-009, FR-012, NFR-001.
- **Affected surfaces**: `tests/architectural/test_gate_read_literal_ban.py`,
  `test_resolution_authority_gates.py`, `resolution_gate_allowlist.yaml`.
- **Sequencing/depends-on**: none (foundational; enables IC-07 triage). Note: the
  scope/floor changes only bite post-merge (NFR-005).
- **Risks**: gate-unmask-cannot-self-validate — pair with the merged-branch dry-run;
  widening the scan surfaces pre-existing residuals that MUST be triaged (IC-07), not
  silently skipped.

### IC-02 — Implement/review-loop CLI reads (`cli/commands/agent`)

- **Purpose**: Route the `tasks/` and WP-frontmatter reads in `tasks.py` and `workflow.py`
  onto the seam; split the mixed-read sites per-leg (PRIMARY→seam, STATUS→coord-aware).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-006; C-001, C-008.
- **Affected surfaces**: `cli/commands/agent/tasks.py` (status/list_tasks/finalize/
  _map_requirements), `workflow.py` (implement/review/_resolve_review_context/
  _preview_claimable_wp_for_mission/_find_first_for_review_wp).
- **Sequencing/depends-on**: IC-06 (fixture) for tests.
- **Risks**: mixed-read sites need per-leg splits; `_preview_claimable_wp_for_mission`/
  `discovery.py` needs a signature change (not a one-liner); review-cycle sub-artifacts
  stay coord (C-008); inline-shape reads must be caught individually.

### IC-03 — Workspace / context / dependency-graph readers

- **Purpose**: Route the PRIMARY-kind reads in the workspace and context-resolution layer
  (`tasks/`, `lanes.json`, WP-frontmatter) onto the seam; split mixed reads.
- **Relevant requirements**: FR-004, FR-005, FR-006; C-001, C-007.
- **Affected surfaces**: `workspace/context.py`, `context/resolver.py`,
  `task_utils/support.py`, `cli/commands/agent/tasks_dependency_graph.py`,
  `tasks_parsing_validation.py`, `cli/commands/validate_tasks.py` (frontmatter leg).
- **Sequencing/depends-on**: IC-06 (fixture).
- **Risks**: `validate_encoding`/`validate_tasks` whole-dir scans need both surfaces; do
  not consolidate the coord-aware twin resolver (C-007).

### IC-04 — #2140 close (`is_committed`)

- **Purpose**: Refresh the stale coord-worktree docstring and add a negative-assertion
  caller-contract regression pin; close #2140 (verified already-remediated by #2106).
- **Relevant requirements**: FR-010; C-004.
- **Affected surfaces**: `missions/_substantive.py`, a regression test.
- **Sequencing/depends-on**: none.
- **Risks**: pin must assert the negative (False on husk path w/o spec.md), not a
  tautology; must not introduce a multi-leg OR.

### IC-05 — #2183 discriminator fold

- **Purpose**: Teach `is_def_use_canonical` the `_canonicalize_bare_modern_handle` fold
  seam so the 4 hand-sanctioned entries auto-route; shrink permanent allowlist 7→3.
- **Relevant requirements**: FR-011; C-005.
- **Affected surfaces**: `test_resolution_authority_gates.py`, `resolution_gate_allowlist.yaml`.
- **Sequencing/depends-on**: coordinate floor recompute with IC-01 (same files).
- **Risks**: the other 3 permanent sanctions are raw-param (not self-fold) — must stay;
  behavior-preserving.

### IC-06 — Shared coord-topology test fixture

- **Purpose**: One un-stubbed fixture (real `meta.json` coord topology + status-only husk
  + `tasks/WP*.md` on primary) backing RED-first per-site coverage that asserts both legs.
- **Relevant requirements**: FR-014; NFR-003.
- **Affected surfaces**: `tests/integration/` or `tests/git/` fixtures + per-site tests.
- **Sequencing/depends-on**: none (enables IC-02/IC-03 tests).
- **Risks**: must NOT patch the topology-resolution stack (the `test_done_bookkeeping_seam.py:353`
  anti-pattern); must synthesize the post-#2106 coord shape (latent on existing repo).

### IC-07 — Residual triage + ticket filing

- **Purpose**: For every site the hardened scanner surfaces that is out of this mission's
  loop scope, pin it in `_DIR_READ_KNOWN_RESIDUALS` with a tracking-issue reference; file
  the sibling mission (merge/lanes `lanes.json` cluster) and the identity-read ticket.
- **Relevant requirements**: FR-008, FR-015; C-009.
- **Affected surfaces**: `_DIR_READ_KNOWN_RESIDUALS` pins; tracker (GitHub issues under #2160).
- **Sequencing/depends-on**: IC-01 (scan must be widened to surface the set).
- **Risks**: no silent skip — every surfaced out-of-scope site is pinned-and-ticketed;
  must not edit `merge/`/`lanes/`/`core/worktree_topology` source (C-009).

### IC-08 — Dead-symbol removal

- **Purpose**: Remove `FEATURE_CONTEXT_UNRESOLVED_CODE` (`_read_path_resolver.py`)
  behavior-preservingly.
- **Relevant requirements**: FR-013; C-005.
- **Affected surfaces**: `missions/_read_path_resolver.py`.
- **Sequencing/depends-on**: none.
- **Risks**: confirm zero source imports (only string-literal test refs) before removal.
