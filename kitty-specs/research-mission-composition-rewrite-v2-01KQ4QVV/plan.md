# Implementation Plan: Research Mission Composition Rewrite v2

**Branch**: `main` (planning base = merge target)
**Date**: 2026-04-26
**Spec**: [`spec.md`](./spec.md)
**Mission ID**: `01KQ4QVVZ4DC6CXA1XCZZAQ8AG`
**Mission slug**: `research-mission-composition-rewrite-v2-01KQ4QVV`
**Prior attempt evidence**: git tag `attempt/research-composition-mission-100-broken` at `d10af600` (local-only)

## Branch Strategy

- Current branch at plan start: `main`
- Planning / base branch: `main`
- Final merge target: `main`
- Branch matches target: `true`

Lane-based execution worktrees are created at `spec-kitty implement` time. This mission plans, implements, and merges entirely against `main`.

## Summary

Audit-driven correction. Software-dev's composition runnability comes from `mission-runtime.yaml` — a sidecar file separate from the legacy `mission.yaml` state machine — which the runtime bridge explicitly prefers. Research has no such sidecar today, so `get_or_start_run('demo-research', repo, 'research')` raises `MissionRuntimeError`. The reroll authors `src/specify_cli/missions/research/mission-runtime.yaml` (and the doctrine sibling), hand-adds five `action:research/*` nodes plus their scope edges to the shipped `src/doctrine/graph.yaml`, extends `_check_composed_action_guard()` with five research branches that emit structured failures on missing artifacts (and a fail-closed default for unknown research actions), and replaces the bypass test with a real-runtime walk that exercises `get_or_start_run` end-to-end with no mocks of composition surfaces. The v1 step contracts, doctrine bundles, profile defaults, and dispatch entry are re-authored on top of this corrected substrate.

## Technical Context

**Language/Version**: Python 3.11+ (charter)
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic, pytest, mypy --strict (charter)
**Storage**: Filesystem only — YAML for mission-runtime, step contracts, action doctrine, DRG; markdown for guidelines and prompt templates; JSONL invocation trail under `~/.kittify/invocations/<id>/`.
**Testing**: pytest with 90%+ coverage on new code; mypy --strict; ruff check; **mandatory real-runtime walk** without mocks of composition surfaces (spec C-007).
**Target Platform**: macOS / Linux developer environments.
**Project Type**: Single Python package.
**Performance Goals**: Composition fast-path lookup remains O(1); `_check_composed_action_guard` adds five branches without changing the unrecognized-action fall-through hot path; DRG `resolve_context` for research actions returns within the same envelope as software-dev.
**Constraints**: spec C-001 (no host-LLM), C-002 (StepContractExecutor chokepoint), C-003 (no defaults wildcards), C-007 (no mocks of `_dispatch_via_composition`/`StepContractExecutor.execute`/`ProfileInvocationExecutor.invoke`/frozen-template loaders/`load_validated_graph`/`resolve_context` in real-runtime tests), C-008 (mission-review PASS requires dogfood smoke evidence).
**Scale/Scope**: 5 advancing research actions; 1 new mission-runtime YAML × 2 mirrors; 5 new graph nodes + ~10 edges; 5 new guard branches + a fail-closed default; 1 real-runtime walk test; ~25 files touched.

## Charter Check

| Gate | Source | Status | Evidence |
|---|---|---|---|
| `DIRECTIVE_003` Decision Documentation | charter | PASS | All 5 Open Questions resolved with file:line evidence below. |
| `DIRECTIVE_010` Specification Fidelity | charter | PASS | All 15 FRs map to concrete plan-time decisions. |
| Test coverage 90%+ on new code | charter | PLAN-PASS | Test plan covers contract loading, profile defaults, DRG node existence, doctrine bundle resolution, guard parity, real-runtime walk. |
| `mypy --strict` zero new errors | charter | PLAN-PASS | New YAMLs validate via existing Pydantic schemas; new test code is typed. |
| Shared package boundary preserved | architectural tests | PASS | No edits to `spec_kitty_events` / `spec_kitty_tracker`. |
| #797 fast-path invariant preserved | runtime_bridge.py:307-310 | PASS | New `_COMPOSED_ACTIONS_BY_MISSION` entry extends the same short-circuit. |
| #799 custom-loader semantics | runtime_bridge.py:328-329 | PASS | Custom-loader widening branch unchanged. |
| C-007 (no mocks of real-runtime surfaces) | spec | PLAN-PASS | Test plan explicitly excludes those targets; reviewer greps the test file. |
| C-008 (dogfood smoke as mission-review hard gate) | spec | PLAN-PASS | Quickstart authors a smoke sequence; mission-review WP makes it a hard gate. |

**Charter check verdict**: PASS. No violations to track.

## Decisions (resolves Open Questions from spec.md)

Each decision below is grounded in code with file:line citations.

### D1 — Coexistence: mission-runtime.yaml sidecar coexists with legacy mission.yaml

**Decision**: Author a new `mission-runtime.yaml` sidecar at:

- `src/specify_cli/missions/research/mission-runtime.yaml` (new)
- `src/doctrine/missions/research/mission-runtime.yaml` (new mirror)

The legacy `src/specify_cli/missions/research/mission.yaml` and `src/doctrine/missions/research/mission.yaml` remain unchanged.

**Rationale (code evidence)**:

- `_candidate_templates_for_root()` at `runtime_bridge.py:905-933` looks for both `mission-runtime.yaml` and `mission.yaml` in each candidate root.
- `_resolve_runtime_template_in_root()` at `runtime_bridge.py:943-961` prefers the `mission-runtime.yaml` sidecar when both exist (line 950: `runtime_sidecar = candidate.with_name("mission-runtime.yaml")`; sidecar tried first at line 953).
- Software-dev follows this exact pattern. `src/specify_cli/missions/software-dev/mission-runtime.yaml` carries `mission.key: software-dev` plus a `steps` list with 7 PromptSteps. The legacy `src/specify_cli/missions/software-dev/mission.yaml` is a v1 state machine (verified via `head -50`) — both files exist, both load, runtime prefers the sidecar.
- The legacy `mission.yaml` for research is consumed only by `merge_package_assets()` (`src/specify_cli/runtime/merge.py:16`) and `MANAGED_MISSION_DIRS` (`src/specify_cli/runtime/doctor.py:25`), which check directory existence and not schema. Coexistence breaks no consumer.

**Alternatives rejected**:

- **Replace mission.yaml with the new MissionTemplate**: rejected. Software-dev does not do this; the legacy file is harmless and removing it requires touching merge/doctor paths.
- **Single hybrid YAML**: rejected. The Pydantic schemas don't combine well; sidecar pattern is what software-dev established.

### D2 — DRG authoring: hand-add `action:research/*` nodes to shipped `src/doctrine/graph.yaml`

**Decision**: Add 5 new `action:research/<action>` nodes to `src/doctrine/graph.yaml` plus per-action `scope` edges pointing at directives and tactics.

**Per-action edge map** (initial; reviewer verifies during implementation):

| Action | scope edges (directive URNs) | scope edges (tactic URNs) |
|---|---|---|
| `scoping` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement` | `tactic:requirements-validation-workflow`, `tactic:premortem-risk-identification` |
| `methodology` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement` | `tactic:adr-drafting-workflow`, `tactic:requirements-validation-workflow` |
| `gathering` | `directive:003-decision-documentation-requirement`, `directive:037-living-documentation-sync` | `tactic:requirements-validation-workflow` |
| `synthesis` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement` | `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow` |
| `output` | `directive:010-specification-fidelity-requirement`, `directive:037-living-documentation-sync` | `tactic:requirements-validation-workflow` |

**Rationale (code evidence)**:

- `load_validated_graph()` at `src/charter/_drg_helpers.py:19-39` loads `<doctrine_root>/graph.yaml` and validates via `assert_valid()`. No extractor builds this file from action bundles; it is hand-authored.
- The five existing software-dev action nodes at `src/doctrine/graph.yaml:5-18` use exactly this `urn` / `kind` / `label` shape. Edges use `relation: scope` pointing at directive and tactic URNs.
- `resolve_context()` at `src/specify_cli/next/_internal_runtime/engine.py:962-1019` walks the graph from the action URN to populate `artifact_urns`. With no node, `artifact_urns` is empty (this is the v1 P1 finding).
- Directives `003-decision-documentation-requirement`, `010-specification-fidelity-requirement`, `037-living-documentation-sync` and tactics `adr-drafting-workflow`, `premortem-risk-identification`, `requirements-validation-workflow` are confirmed shipped (resolved cleanly during the v1 attempt's WP02 audit; preserved here).

**Alternatives rejected**:

- **Project overlay only at `.kittify/doctrine/graph.yaml`**: rejected. The shipped graph is what fresh installs use; overlay-only would leave research action nodes empty for end users.
- **Calibration step that builds nodes from action bundles**: rejected. Software-dev does not do this; introducing it is scope creep.

### D3 — Guard semantics: re-implement against feature_dir contents, mirroring software-dev

**Decision**: Extend `_check_composed_action_guard()` at `src/specify_cli/next/runtime_bridge.py:444-528` with five research branches checking `feature_dir` directly. Add a fail-closed default when `mission == "research"` and `action` is not in the known set.

**Per-action guard logic**:

| Action | Check | Failure message |
|---|---|---|
| `scoping` | `feature_dir / "spec.md"` exists | "Required artifact missing: spec.md" |
| `methodology` | `feature_dir / "plan.md"` exists | "Required artifact missing: plan.md" |
| `gathering` | `feature_dir / "source-register.csv"` exists AND status events log includes ≥3 `source_documented` events | "Required artifact missing: source-register.csv" / "Insufficient sources documented (need ≥3)" |
| `synthesis` | `feature_dir / "findings.md"` exists | "Required artifact missing: findings.md" |
| `output` | `feature_dir / "report.md"` exists AND status events log includes a `publication_approved` gate event | "Required artifact missing: report.md" / "Publication approval gate not passed" |
| Unknown research action | n/a | "No guard registered for research action: <action>" (fail-closed) |

**Rationale (code evidence)**:

- Software-dev's guards check `feature_dir / <artifact>` directly (`runtime_bridge.py:477-509`). They do NOT evaluate `mission.yaml`'s declarative `artifact_exists(...)` predicates.
- `_dispatch_via_composition()` at `runtime_bridge.py:531` calls `_check_composed_action_guard` after composition (line 634-638) and propagates a non-empty failure list as a structured error with no run-state advancement (line 642 prevents legacy DAG fallback).
- `_should_advance_wp_step()` (used by software-dev's implement/review branches) reads status events directly. Research's `gathering` (event_count) and `output` (gate_passed) checks use the same pattern.
- The unrecognized-action fall-through at line 528 currently returns an empty failures list (silent pass) — that is the v1 P1 finding. The fail-closed default for research closes that gap for our mission while leaving software-dev's behavior untouched.

**Alternatives rejected**:

- **Delegate to mission.yaml predicate evaluator**: rejected. No such evaluator is wired into the composition path; introducing one expands scope.
- **Generic "any artifact named in expected-artifacts.yaml"**: rejected. Software-dev hardcodes; mirroring gives operators precise error messages.

### D4 — PromptStep shape per action: mirror software-dev's mission-runtime.yaml

**Decision**: The new `mission-runtime.yaml` carries 6 `PromptStep` entries (5 advancing actions + `accept`), mirroring the structure of `src/specify_cli/missions/software-dev/mission-runtime.yaml`.

```yaml
mission:
  key: research
  name: Deep Research Kitty
  version: "2.0.0"

steps:
  - id: scoping
    title: Research Scoping
    agent-profile: researcher-robbie
    prompt_template: scoping.md
    description: Define the research question, scope boundaries, and stakeholder context.
  - id: methodology
    title: Methodology Design
    depends_on: [scoping]
    agent-profile: researcher-robbie
    prompt_template: methodology.md
    description: Document the research methodology, frameworks, and reproducibility plan.
  - id: gathering
    title: Source Gathering
    depends_on: [methodology]
    agent-profile: researcher-robbie
    prompt_template: gathering.md
    description: Register sources with citations and emit source_documented events.
  - id: synthesis
    title: Findings Synthesis
    depends_on: [gathering]
    agent-profile: researcher-robbie
    prompt_template: synthesis.md
    description: Synthesize evidence into findings, tracing each conclusion to documented sources.
  - id: output
    title: Publication Output
    depends_on: [synthesis]
    agent-profile: reviewer-renata
    prompt_template: output.md
    description: Prepare findings for publication; verify citation completeness and methodology clarity.
  - id: accept
    title: Acceptance
    depends_on: [output]
    prompt_template: accept.md
    description: Validate research completeness and readiness.
```

**Rationale (code evidence)**:

- `PromptStep` schema at `schema.py:401-434` accepts `agent_profile` (alias `agent-profile` in YAML at line 415) and `contract_ref` (line 421).
- `_is_composed_step()` at `contract_synthesis.py:62-73` returns True when `contract_ref` is unset, triggering in-memory contract synthesis with ID `f"custom:{template.mission.key}:{step.id}"` (line 28). Our shipped contracts at `src/doctrine/mission_step_contracts/shipped/research-*.step-contract.yaml` are still consulted via the resolver chain.
- Software-dev's `mission-runtime.yaml` uses `agent-profile: <profile-id>` for routing without `contract_ref`; mirroring that for research keeps the shipped step contracts authoritative.
- The `prompt_template:` filenames resolve under `src/specify_cli/missions/research/templates/`. We add 6 new templates (one per step) since the existing legacy templates support the v1 state machine flow.

**Alternatives rejected**:

- **Use `contract_ref` instead of `agent-profile`**: rejected. Synthesis is the established path.

### D5 — v1 preservation: re-author from scratch on the corrected substrate

**Decision**: The v1 attempt (preserved at tag `attempt/research-composition-mission-100-broken`) authored 5 step contract YAMLs, 10 doctrine bundle files, 5 `_ACTION_PROFILE_DEFAULTS` entries, and 1 `_COMPOSED_ACTIONS_BY_MISSION` entry. These were correct in shape and content. Re-author them on the corrected substrate (do not merge from the v1 tag; copy verbatim where appropriate).

**Re-authoring scope**:

- Copy verbatim (referencing v1 tag artifacts as a source): 5 step contract YAMLs, 5 action doctrine `index.yaml` files, 5 action doctrine `guidelines.md` files (specifically `output/guidelines.md` already includes the cycle-2 fix with literal `gate_passed("publication_approved")` token).
- Re-add: 5 entries to `_ACTION_PROFILE_DEFAULTS`, 1 entry to `_COMPOSED_ACTIONS_BY_MISSION`.
- Author new (not in v1): `mission-runtime.yaml` × 2 mirrors, 6 markdown templates (one per step), 5 graph node entries + edges, 5 guard branches + fail-closed default, real-runtime integration walk.

**Rationale**: clean history, correct shape preservation, no merge dependency on the broken local commit.

## Project Structure

```
kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/
├── plan.md                      # This file
├── research.md                  # Phase 0 — pre-spec audit + plan-phase deeper audit
├── data-model.md                # Phase 1 — entities and relations
├── quickstart.md                # Phase 1 — operator dogfood smoke sequence
├── contracts/                   # Phase 1
│   ├── mission-runtime.md       # mission-runtime.yaml shape contract
│   ├── drg-nodes.md             # action:research/* node + edge contract
│   ├── guards.md                # _check_composed_action_guard research-branch contract
│   └── real-runtime-walk.md     # integration walk contract (no-mock list)
├── checklists/
│   └── requirements.md          # spec quality checklist (already created)
├── meta.json
├── spec.md
└── tasks/                       # filled by /spec-kitty.tasks
```

### Source code paths

```
NEW:
  src/specify_cli/missions/research/mission-runtime.yaml
  src/doctrine/missions/research/mission-runtime.yaml
  src/specify_cli/missions/research/templates/{scoping,methodology,gathering,synthesis,output,accept}.md
  src/doctrine/mission_step_contracts/shipped/research-{scoping,methodology,gathering,synthesis,output}.step-contract.yaml
  src/doctrine/missions/research/actions/{scoping,methodology,gathering,synthesis,output}/{index.yaml,guidelines.md}
  tests/specify_cli/mission_step_contracts/test_research_composition.py
  tests/specify_cli/next/test_runtime_bridge_research_composition.py
  tests/integration/test_research_runtime_walk.py

MODIFIED (additive only):
  src/doctrine/graph.yaml                                                 (5 new nodes + ~10 new edges)
  src/specify_cli/mission_step_contracts/executor.py                      (5 entries in _ACTION_PROFILE_DEFAULTS)
  src/specify_cli/next/runtime_bridge.py                                  (1 entry in _COMPOSED_ACTIONS_BY_MISSION + 5 branches in _check_composed_action_guard + fail-closed default)

UNCHANGED (must remain so):
  src/specify_cli/missions/research/mission.yaml                          (legacy state machine)
  src/doctrine/missions/research/mission.yaml                             (legacy state machine)
  src/specify_cli/validators/research.py                                  (post-action artifact validation)
  src/specify_cli/missions/research/expected-artifacts.yaml
  src/doctrine/missions/software-dev/**                                   (no software-dev edits)
  src/specify_cli/missions/software-dev/**
  src/specify_cli/next/_internal_runtime/**                               (engine internals)
  src/specify_cli/mission_step_contracts/repository.py
  spec_kitty_events / spec_kitty_tracker package surfaces
```

## Test Plan

| Test file | Purpose | C-007 status |
|---|---|---|
| `tests/specify_cli/mission_step_contracts/test_research_composition.py` | Unit: 5 contracts load; 5 profile defaults resolve; 5 doctrine bundles reachable via `MissionTemplateRepository`; sentinel for software-dev no-regression. | Mocks at config layer only. |
| `tests/specify_cli/next/test_runtime_bridge_research_composition.py` | Unit-level bridge: dispatch fires for known research actions; rejects unknown; fast-path invariant; action_hint==step.id; no fall-through. Includes 5 guard-failure cases (one per action) on empty feature_dir asserting structured failures. Includes the unknown-research-action fail-closed test. | Mocks bridge internals only. |
| **`tests/integration/test_research_runtime_walk.py`** | **Real-runtime walk: `get_or_start_run('demo-research', repo, 'research')` succeeds; advances at least one composed step; trail records show paired lifecycle and research-native action names; missing-artifact scenarios produce structured guard failures; DRG resolves non-empty `artifact_urns` for each of the 5 actions.** | **MUST NOT mock `_dispatch_via_composition`, `StepContractExecutor.execute`, `ProfileInvocationExecutor.invoke`, frozen-template loaders, `load_validated_graph`, or `resolve_context`.** Reviewer will `grep` the file. |

Regression sweep stays the same as v1: `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/test_runtime_bridge_composition.py`, `tests/integration/test_custom_mission_runtime_walk.py`, `tests/integration/test_mission_run_command.py` all stay green.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `mission-runtime.yaml` schema requirements I missed (e.g. RACI, significance blocks). | Implementer mirrors software-dev's shape line-for-line; mypy --strict validates load via existing Pydantic schema. |
| New graph nodes break `assert_valid()` (cycles, missing referenced nodes). | Implementer runs `load_validated_graph(repo)` after each edit; the validator emits structured errors. Each referenced directive/tactic URN is verified to exist before adding the edge. |
| `_check_composed_action_guard` branches add to a hot path. | Branches use simple `feature_dir / X` checks (file syscalls); software-dev branches do the same with no measurable overhead. |
| Real-runtime test introduces flakiness (file IO, tmp dirs). | Use `tmp_path` and isolated `~/.kittify/invocations/` via env var; pattern follows `test_custom_mission_runtime_walk.py`. |
| Profile names (`researcher-robbie`, `reviewer-renata`) drift before this mission lands. | First implementation WP runs `rg -n "researcher-robbie\|reviewer-renata" src/`; both confirmed to exist at `src/doctrine/agent_profiles/shipped/` during audit. |
| Status-events log path differs between live runtime and tests. | Use the same status events module the runtime uses; do not mock it. |
| Templates referenced by `prompt_template:` don't exist. | The implementation WP creates the 6 markdown templates explicitly. |
| The legacy `mission.yaml` and new `mission-runtime.yaml` get out of sync. | Spec C-006 acknowledges coexistence; the legacy file is unchanged in this mission, so no sync path is required. |

## Acceptance Mapping

| Spec FR | Discharged by |
|---|---|
| FR-001 (runnability) | D1 (mission-runtime.yaml); real-runtime walk asserts no `MissionRuntimeError`. |
| FR-002 (advancement via composition) | New `_COMPOSED_ACTIONS_BY_MISSION` entry; real-runtime walk asserts at least one advancement. |
| FR-003 (MissionTemplate shape) | D1 + D4. |
| FR-004 (DRG node existence) | D2 (5 new nodes in shipped graph.yaml). |
| FR-005 (resolve_context non-empty) | D2 (edges per action). |
| FR-006 (doctrine bundle reachable via composition resolver) | D2 + per-action edges pointing at directive/tactic nodes that resolve to the doctrine bundle content. |
| FR-007 (guard parity) | D3 (5 new branches + fail-closed default in `_check_composed_action_guard`). |
| FR-008 (structured failure on missing) | D3 (each branch returns named failures). |
| FR-009 (no-fallthrough on guard failure) | Inherited PR #797 invariant; new branches preserve it. |
| FR-010 (loader path parity) | D1 (mission-runtime.yaml resolved by existing `_resolve_runtime_template_in_root`). |
| FR-011 (action_hint correctness) | Inherited from `executor.py:173`; preserved. |
| FR-012 (paired lifecycle) | Inherited from `ProfileInvocationExecutor`; preserved. |
| FR-013 (no mocks of real-runtime surfaces) | Test plan + reviewer `grep` checklist. |
| FR-014 (no regression) | Regression sweep. |
| FR-015 (preserved-but-re-authored artifacts) | D5. |

## Final Branch Statement

- Current branch at plan completion: `main`.
- Planning base / merge target: `main`.
- Branch matches target: `true`.
- Next command: `/spec-kitty.tasks`.
