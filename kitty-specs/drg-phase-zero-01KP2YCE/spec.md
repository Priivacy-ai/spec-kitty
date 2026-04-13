# DRG Phase Zero --- Graph Model, Context Parity, and Surface Calibration

**Mission ID**: `01KP2YCESBSG61KQH5PQZ9662H`
**Mission type**: software-dev
**Parent epic**: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461) --- Charter as Synthesis & Doctrine Reference Graph
**Phase**: 0 (DRG prototype + invariant test)
**Scoped issues**: #462, #470, #471, #472, #473, #474

## Problem Statement

Spec Kitty's governance context assembly depends on implicit inline references scattered across doctrine artifact YAML files (`tactic_refs`, `directive_refs`, `references`, `opposed_by`) and action index files (`directives`, `tactics`, `styleguides`, `toolguides`, `procedures`). These references are not queryable as a graph, not independently testable, and not calibrated per action. Adding, removing, or reweighting doctrine artifacts requires editing multiple YAML files with no automated consistency check.

Phase 0 introduces the Doctrine Reference Graph (DRG) as an explicit, validated, queryable graph model that replaces the implicit reference web. It ships alongside the existing inline references --- Phase 1 deletes the inline references after Phase 0 proves parity.

## Motivation

- **Governance context is assembled ad hoc.** `build_charter_context()` loads action indices, intersects with project selections, and renders inline. There is no centralized model of what references what, so changes to doctrine artifacts can silently alter governance context.
- **Action surfaces are uncalibrated.** The `specify` action may receive the same governance surface as `implement`, violating the minimum-effective-dose principle. There is no automated way to measure or enforce surface size inequalities across actions.
- **Phase 1 excision has no safety net.** Deleting inline references and the curation pipeline requires proving the DRG path produces identical or intentionally-improved output. Without an invariant test, excision is a blind deletion.

## Actors

- **Agent operator**: Runs `spec-kitty` commands; receives governance context in prompts. Primary beneficiary of right-sized action surfaces.
- **Doctrine maintainer**: Edits doctrine artifacts and action indices. Benefits from a single graph model instead of scattered inline references.
- **CI pipeline**: Runs invariant and calibration tests on every PR that touches doctrine artifacts or context assembly code.

## User Scenarios & Testing

### Scenario 1: Migration produces a valid DRG from existing artifacts

A doctrine maintainer runs the migration extractor against the current shipped artifacts. The extractor walks all directive, tactic, paradigm, and action index YAML files, extracts every inline reference, and emits a `graph.yaml` file with typed edges. The resulting graph validates against the DRG Pydantic model: no dangling references, no unknown relation types, no malformed URNs.

**Verification**: Load `graph.yaml` via the Pydantic model; assert zero validation errors. Assert edge count >= the sum of all inline reference fields across all shipped artifacts.

### Scenario 2: DRG-driven context matches legacy context

For every supported `(profile, action, depth)` combination, `build_context_v2()` resolves the same set of governance artifacts (by URN) as the currently shipped `src/charter/context.py` path. Reachability differences are either exact matches or itemized intentional improvements (e.g., legacy path was wrong-sized). Rendered-text differences (formatting, section ordering) are out of scope for Phase 0.

**Verification**: Run invariant test matrix; assert artifact-set identity or accepted difference with explicit justification per entry.

### Scenario 3: Action surfaces respect calibration inequalities

The surface size (measured as artifact count or token estimate) for each action respects the minimum-effective-dose ordering:

```
|context(specify)| < |context(plan)| < |context(implement)|
|context(tasks)|   < |context(implement)|
|context(review)|  ~= |context(implement)|
```

**Verification**: Calibration test asserts these inequalities. When violated, the fix is adjusting the migration calibrator inputs or the action index files and regenerating `graph.yaml`, never adding filtering logic in the context builder. Post-Phase-0, `graph.yaml` becomes the authoritative source and can be edited directly.

### Scenario 4: CI catches governance artifact reachability regressions

A contributor modifies a directive YAML file and opens a PR. The invariant test detects that the DRG path and the canonical `build_charter_context()` path now resolve different artifact sets for one `(profile, action)` pair. The PR is blocked until the contributor either regenerates `graph.yaml` to reflect the change or updates the expected-differences manifest.

**Verification**: CI runs both test harnesses on every PR touching `src/doctrine/`, `src/charter/`, or `graph.yaml`.

## Baseline (already shipped or landing with PR #608)

The following are NOT greenfield --- they exist on `main` and must be preserved:

| Surface | Location | Status |
|---------|----------|--------|
| Action-scoped `build_charter_context()` with depth parameter | `src/charter/context.py` | Canonical baseline; parity oracle |
| Legacy `build_charter_context()` without depth | `src/specify_cli/charter/context.py` | Compatibility surface; 2 callers remain |
| Action index files per mission/action | `src/doctrine/missions/software-dev/actions/*/index.yaml` | Input to migration extractor |
| `DoctrineService` with 8 lazy-loaded repositories | `src/doctrine/service.py` | Preserved; DRG does not replace it |
| Glossary scope/store/middleware/CLI | `src/specify_cli/glossary/` | Untouched by this mission |
| Typed `WPMetadata`, 9-lane `Lane`, `InReviewState` | Various | Untouched by this mission |
| `mission_id` mandatory, drift fallback removed | PR #608 (sync/emitter, status/models) | Landing; treated as baseline |
| Schema version gating on artifacts (`1.0`) | `src/doctrine/shared/schema_utils.py` | Preserved |
| Charter bundle layout | `.kittify/charter/` | Preserved |
| Prompt builder governance integration | `src/specify_cli/next/prompt_builder.py` | Call-site reroute needed (see FR-001) |

### Call-Site Audit Finding

Two callers still import from the OLD `src/specify_cli/charter/context.py`:
- `src/specify_cli/next/prompt_builder.py:13`
- `src/specify_cli/cli/commands/agent/workflow.py:20`

One caller uses the canonical NEW path:
- `src/specify_cli/cli/commands/charter.py:13`

Phase 0 does NOT reroute these callers. The behavioral delta between the two implementations (canonical has depth/action-doctrine/guidelines; legacy does not) means rerouting is a user-visible behavior change, not a transparent import swap. The reroute is Phase 1 scope. The invariant test (FR-007) calls the canonical path directly as the parity oracle without changing any production call sites.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Audit all `build_charter_context()` call sites, document the behavioral delta between the canonical `src/charter/context.py` and the legacy `src/specify_cli/charter/context.py`, and confirm the canonical path is the correct parity oracle for FR-007. The actual reroute of callers is Phase 1 scope (after parity is confirmed). | Proposed |
| FR-002 | Define a DRG schema as a single YAML file (`graph.yaml`) with node URN format (`kind:id`), typed edges (v1 relation types: `requires`, `suggests`, `applies`, `scope`, `vocabulary`, `instantiates`, `replaces`, `delegates_to`), and a Pydantic model that validates the graph. | Proposed |
| FR-003 | The Pydantic model rejects malformed graphs: dangling references (edge target not a known node), unknown relation types, malformed URNs, and cycles in `requires` edges. | Proposed |
| FR-004 | Provide a migration extractor that walks all shipped doctrine artifacts (directives, tactics, paradigms) and action index files, extracts every inline reference field, and emits equivalent typed edges into `graph.yaml`. | Proposed |
| FR-005 | The migration extractor applies per-action surface calibration: each action (`specify`, `plan`, `tasks`, `implement`, `review`) receives `scope` edges that respect the minimum-effective-dose principle. | Proposed |
| FR-006 | Implement `build_context_v2(profile, action, depth)` that queries the merged DRG (shipped + project-local layers), walks `scope` edges from the action node to depth 1, walks `requires` transitively, walks `suggests` to user-configured depth, includes `vocabulary` edges as glossary scope, materializes each resolved artifact, and returns a structured prompt block. (`applies` is defined in the v1 schema but not populated by the Phase 0 migration; it is reserved for Phase 2+ when artifacts self-declare applicability.) | Proposed |
| FR-007 | Provide an invariant regression test that compares the **artifact reachability** of `build_context_v2(profile, action, depth)` against the canonical `src/charter/context.py` `build_charter_context()` for every shipped profile x action x depth combination. Parity means: the same set of artifact URNs is resolved by both paths. Rendered-text parity (guidelines, reference filtering, section formatting) is a Phase 1 concern when callers are switched to `build_context_v2`. Intentional reachability differences must be itemized in an accepted-differences manifest. | Proposed |
| FR-008 | Provide an action surface calibration test that asserts the minimum-effective-dose inequalities for every shipped action. Violations are fixed by adjusting `scope` edges in `graph.yaml`, never by adding filtering logic in the context builder. | Proposed |
| FR-009 | The DRG is the only knob for calibrating action surfaces. No per-action filtering logic exists in `build_context_v2` or the prompt builder. Context size is determined entirely by graph topology. | Proposed |
| FR-010 | Both the invariant test and the calibration test run in CI on every PR that touches `src/doctrine/`, `src/charter/`, or `graph.yaml`. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `graph.yaml` loads and validates in under 500ms for a graph with up to 500 nodes and 2000 edges. | < 500ms cold load | Proposed |
| NFR-002 | `build_context_v2()` resolves a single `(profile, action)` query in under 200ms including artifact materialization. | < 200ms per query | Proposed |
| NFR-003 | The full invariant test matrix (all profile x action x depth combinations) completes in under 60 seconds. | < 60s CI wall time | Proposed |
| NFR-004 | New code ships with 90%+ test coverage (project standard). | >= 90% line coverage | Proposed |
| NFR-005 | All new code passes `mypy --strict` with zero type errors. | 0 type errors | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Inline references in doctrine YAML files must remain in place. Phase 0 ships the DRG alongside them. Phase 1 deletes them after both test harnesses pass. | Active |
| C-002 | The `DoctrineService` and its 8 repositories are preserved. The DRG is an additional index, not a replacement for the service layer. | Active |
| C-003 | The curation pipeline (`_proposed/` directories, `doctrine curate/promote/reset/status` commands, `src/doctrine/curation/` package) is untouched. Phase 1 excises it. | Active |
| C-004 | No cross-repo changes. `spec-kitty-events`, `spec-kitty-saas`, `spec-kitty-tracker`, and `spec-kitty-runtime` are out of scope unless a hard contract dependency is proven. | Active |
| C-005 | The glossary module (`src/specify_cli/glossary/`) is not modified. `vocabulary` edges in the DRG reference glossary scopes but do not alter glossary internals. | Active |
| C-006 | Mission identity surfaces (`mission_id`, sync emission) are not reopened. PR #608 is the final word. | Active |
| C-007 | `graph.yaml` uses YAML format consistent with existing doctrine YAML conventions (`schema_version: "1.0"`, sorted keys, human-readable). | Active |

## Success Criteria

1. The invariant regression test passes for 100% of shipped profile x action x depth combinations (artifact reachability parity), with any accepted differences explicitly itemized and reviewed.
2. The calibration test confirms all minimum-effective-dose inequalities hold for every shipped action.
3. Both test harnesses run green in CI before Phase 1 work begins.
4. The behavioral delta between `src/charter/context.py` and `src/specify_cli/charter/context.py` is documented, and the canonical path is confirmed as the correct parity oracle.
5. `graph.yaml` validates with zero errors against the DRG Pydantic model.
6. The migration extractor accounts for every inline reference field across all shipped artifacts (zero missed references).

## Scope Boundary: What Phase 1 Will Delete

Once Phase 0's test harnesses pass, Phase 1 (#463) will delete the following. Phase 0 must NOT delete any of these:

| Surface | Location | Phase 1 action |
|---------|----------|----------------|
| `_proposed/` directories | `src/doctrine/*/_ proposed/` | Delete entirely |
| Curation package | `src/doctrine/curation/` | Delete entirely |
| Curation CLI commands | `doctrine curate/promote/reset/status` | Remove from CLI |
| Inline `tactic_refs` fields | Directive and paradigm YAMLs | Remove field |
| Inline `directive_refs` fields | Paradigm YAMLs | Remove field |
| Inline `references` arrays | Directive and tactic YAMLs | Remove field |
| Inline `opposed_by` arrays | Paradigm YAMLs | Remove field |
| Action index inline lists | `actions/*/index.yaml` `directives`, `tactics`, etc. | Replace with DRG edge queries |
| Call-site reroute (prompt_builder, workflow) | `src/specify_cli/next/prompt_builder.py`, `src/specify_cli/cli/commands/agent/workflow.py` | Switch imports to `charter.context` + test rendered-text parity |
| Legacy context compatibility surface | `src/specify_cli/charter/context.py` | Delete after reroute confirmed |
| Validators for inline refs | Schema validation for above fields | Remove validators |
| `build_charter_context()` in `src/charter/context.py` | `src/charter/context.py` | Replace with `build_context_v2` |

## Key Entities

### DRG Node

A doctrine artifact addressable by URN (`kind:id`).

- **URN format**: `{kind}:{id}` (e.g., `directive:DIRECTIVE_001`, `tactic:tdd-red-green-refactor`, `paradigm:domain-driven-design`, `action:software-dev/specify`)
- **Kind**: One of `directive`, `tactic`, `paradigm`, `styleguide`, `toolguide`, `procedure`, `agent_profile`, `action`, `glossary_scope`
- **ID**: Artifact's canonical identifier as defined in its YAML `id` field

### DRG Edge

A typed relationship between two nodes.

- **Relation types (v1)**: `requires`, `suggests`, `applies`, `scope`, `vocabulary`, `instantiates`, `replaces`, `delegates_to`
- **Source/target**: Node URNs
- **Metadata**: Optional `when` (applicability context), `reason` (for opposition/conflict edges)

### Accepted-Differences Manifest

A structured file listing intentional divergences between legacy and DRG context output.

- **Per entry**: `(profile, action, depth)` tuple, legacy artifact set, DRG artifact set, reason for divergence, reviewer who accepted it

## Assumptions

1. The set of shipped doctrine artifacts on `main` at mission start is the canonical input for the migration extractor. No new artifacts will be added during this mission.
2. The `software-dev` mission is the primary mission type for calibration testing. `research` and `documentation` missions are included if they have action indices; otherwise they are documented as future scope.
3. The "profile" dimension in the invariant test matrix uses shipped agent profiles from `src/doctrine/agent_profiles/shipped/`. If no profiles meaningfully alter context assembly today, the test degenerates to action-only and that is acceptable.
4. `graph.yaml` lives at `src/doctrine/graph.yaml` alongside the artifacts it indexes.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Inline reference extraction misses edge cases (e.g., directive ID format mismatch between `DIRECTIVE_NNN` and `NNN-slug` in action indices) | Medium | High | Migration extractor normalizes both ID formats; validation step counts extracted edges vs source field counts |
| Call-site reroute to `src/charter/context.py` introduces subtle behavior change | Low | Medium | Reroute is a separate, independently testable WP with before/after output comparison |
| Invariant test produces too many accepted differences, reducing Phase 1 confidence | Low | High | Differences must be individually reviewed and justified; a threshold (e.g., >10% divergence) triggers mission pause |
| `graph.yaml` becomes a merge-conflict hotspot | Medium | Low | Graph is generated by migration script, not hand-edited. Regeneration is idempotent. |

## Rollback Criteria

Phase 0 can be rolled back cleanly because:
1. Inline references remain in place (C-001). Deleting `graph.yaml` and `build_context_v2` restores the prior state.
2. No production call sites are changed. Phase 0 adds new code and tests; it does not modify any existing import paths or prompt behavior.
3. No existing tests are modified. New tests are additive.

**Rollback trigger**: If the invariant test reveals that the DRG resolves a fundamentally different artifact set than the canonical path and the root cause is unclear, pause the mission and escalate. Do not paper over divergence with a large accepted-differences manifest.

## Non-Goals (Explicit)

- Deleting `_proposed/` directories (Phase 1)
- Removing `doctrine curate/promote/reset/status` commands (Phase 1)
- Charter Synthesizer pipeline (Phase 3)
- `spec-kitty do/ask/advise` (Phase 4)
- `ProfileInvocationExecutor` (Phase 4)
- `StepContractExecutor` (Phase 6)
- Retrospective contract (Phase 6)
- Mission identity cleanup (PR #608)
- Cross-repo changes to `spec-kitty-events`, `spec-kitty-saas`, `spec-kitty-tracker`, `spec-kitty-runtime`
- Doctrine-specific compatibility registry in `src/doctrine/versioning.py` (Phase 7)
