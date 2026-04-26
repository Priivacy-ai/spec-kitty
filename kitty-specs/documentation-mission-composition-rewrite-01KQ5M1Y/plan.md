# Implementation Plan: Documentation Mission Composition Rewrite

**Branch**: `main` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification at `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/spec.md`

## Summary

Move the built-in documentation mission onto the StepContractExecutor composition substrate, mirroring the landed research composition rewrite (#504). The work is wholly internal: a runtime sidecar template, six shipped step contracts, six action doctrine bundles, six DRG action nodes (with edges), runtime-bridge dispatch wiring, fail-closed guard branches, and a real-runtime integration walk plus a hard-gated dogfood smoke. The substrate (StepContractExecutor #501, single-dispatch composition #786/#793/#794, runtime-boundary preflight #798, local custom mission loader #505) is unchanged.

## Technical Context

**Language/Version**: Python 3.13 (resolved via `uv run --python 3.13 …`; `.python-version` is currently pinned to `3.13.12`, which may be uninstallable on the test machine — explicit `--python 3.13` works).
**Primary Dependencies**: `typer` (CLI), `rich` (console), `ruamel.yaml` / `pyyaml` (YAML), `pydantic` (`MissionTemplate`, `PromptStep`, `MissionMeta`).
**Storage**: Filesystem only — YAML for runtime templates / contracts / action bundles / DRG; `~/.kittify/runtime/runs/` for run state; `~/.kittify/events/profile-invocations/` for invocation trail.
**Testing**: `pytest` (with `--timeout=120`); the integration walk uses `tmp_path` + `subprocess` git scaffolding (mirrors `tests/integration/test_research_runtime_walk.py`). Coverage threshold is 90% for new code.
**Target Platform**: Local CLI / agent harness on macOS and Linux; no service runtime.
**Project Type**: Single project — `src/specify_cli/` (runtime, CLI), `src/doctrine/` (governance assets), `tests/`.
**Performance Goals**: DRG load + per-action context resolution must stay within 2× the current research-action median (NFR-007). No throughput target; this is single-shot per `spec-kitty next` invocation.
**Constraints**: Zero new mypy-strict errors on changed files (NFR-003); zero new ruff findings (NFR-004); regression suite stays green byte-identically (NFR-002); composition chokepoint must remain `StepContractExecutor` (C-002); no new shipped agent profiles (C-003); dogfood smoke uses `uv --project`, never `--directory` (NFR-005, per #735).
**Scale/Scope**: One built-in mission, 6 actions, ~12 new YAML files (2 runtime templates + 6 contracts + 6×2 action bundle files), ~6 DRG nodes + ~18 edges, 2-3 source-code edits in `runtime_bridge.py` and `executor.py`, 1 new integration test file, 1 dogfood smoke command sequence.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter context (loaded via `spec-kitty charter context --action plan --json`):

- Policy stack: `pytest` (90%+ coverage), `mypy --strict`, `ruff`, `typer`, `rich`, `ruamel.yaml`, integration tests for CLI commands.
- Active directives for plan action:
  - **DIRECTIVE_003** Decision Documentation Requirement — material decisions must be captured with constraints. ✅ This plan documents 7 decisions in a dedicated section with code-grounded evidence.
  - **DIRECTIVE_010** Specification Fidelity Requirement — implementation must remain faithful to the spec; deviations must be reviewed before acceptance. ✅ Every plan decision maps back to FR/NFR/C IDs in spec.md; no implicit deviations.
- Plan tactics: `adr-drafting-workflow`, `premortem-risk-identification`, `requirements-validation-workflow`. ✅ Section "Decisions" is the ADR section; the "Premortem Risks" section enumerates failure modes; "Requirements ↔ Plan map" is the validation workflow.

**Result**: PASS. No charter conflicts. Re-evaluated after Phase 1 design (see end of file).

## Project Structure

### Documentation (this feature)

```
kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/
├── spec.md              # ✅ committed
├── plan.md              # this file
├── research.md          # phase 0 output
├── data-model.md        # phase 1 output (file inventory + DRG node shapes)
├── quickstart.md        # phase 1 output (operator dogfood smoke)
├── contracts/           # phase 1 output (file-shape contracts the implementer renders)
├── checklists/
│   └── requirements.md  # ✅ committed
└── tasks/               # populated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── missions/documentation/
│   ├── mission.yaml                # legacy state machine — KEPT for reference
│   ├── expected-artifacts.yaml     # legacy artifact manifest — KEPT, used as evidence for guard gates only
│   └── mission-runtime.yaml        # NEW — runtime sidecar; mission.key=documentation; 6 steps + accept
├── missions/research/              # reference — UNCHANGED
├── next/runtime_bridge.py          # EDIT: add "documentation" entry to _COMPOSED_ACTIONS_BY_MISSION (~line 274) and add documentation guard branch in _check_composed_action_guard (~after line 588)
└── mission_step_contracts/executor.py # EDIT: add 6 (mission, action) → profile entries to _ACTION_PROFILE_DEFAULTS (~line 49)

src/doctrine/
├── missions/documentation/
│   ├── mission.yaml                # legacy — KEPT
│   ├── expected-artifacts.yaml     # legacy — KEPT
│   ├── mission-runtime.yaml        # NEW — doctrine-side mirror of the runtime sidecar
│   └── actions/                    # NEW — 6 action bundles
│       ├── discover/{index.yaml,guidelines.md}
│       ├── audit/{index.yaml,guidelines.md}
│       ├── design/{index.yaml,guidelines.md}
│       ├── generate/{index.yaml,guidelines.md}
│       ├── validate/{index.yaml,guidelines.md}
│       └── publish/{index.yaml,guidelines.md}
├── mission_step_contracts/shipped/
│   ├── documentation-discover.step-contract.yaml   # NEW
│   ├── documentation-audit.step-contract.yaml      # NEW
│   ├── documentation-design.step-contract.yaml     # NEW
│   ├── documentation-generate.step-contract.yaml   # NEW
│   ├── documentation-validate.step-contract.yaml   # NEW
│   └── documentation-publish.step-contract.yaml    # NEW
└── graph.yaml                      # EDIT: add 6 action:documentation/* nodes + edges

tests/integration/
├── test_research_runtime_walk.py   # reference — UNCHANGED
└── test_documentation_runtime_walk.py # NEW — real-runtime walk

tests/specify_cli/
├── mission_step_contracts/
│   └── test_documentation_composition.py   # NEW — parametrized unit tests for all 6 contracts
├── next/
│   └── test_runtime_bridge_documentation_composition.py # NEW — dispatch + guard parity
└── test_documentation_drg_nodes.py # NEW — DRG node existence + resolve_context non-empty
```

**Structure Decision**: Single project. Files are added under existing directories that already host `software-dev` and `research` analogues; no new package boundaries are introduced.

## Decisions (resolution of spec.md Open Questions)

Each decision below is grounded in a specific file:line citation. Reviewers should be able to verify any decision by clicking the citation.

### Decision D1 — Coexistence of `mission.yaml` and `mission-runtime.yaml`

**Spec OQ #1**: does the new `mission-runtime.yaml` coexist with the legacy `mission.yaml`, or is the legacy file removed?

**Decision**: **Coexistence**. The legacy `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml` files remain on disk, byte-identical, for backward reference (matching how research handled it).

**Evidence**:
- `_resolve_runtime_template_in_root()` at `src/specify_cli/next/runtime_bridge.py:1056-1073` already prefers `mission-runtime.yaml` over `mission.yaml` deterministically when both exist:
  ```python
  paths_to_try = [candidate]
  if candidate.name == "mission.yaml":
      runtime_sidecar = candidate.with_name("mission-runtime.yaml")
      if runtime_sidecar.exists() and runtime_sidecar.is_file():
          paths_to_try = [runtime_sidecar, candidate]
  ```
- `_candidate_templates_for_root()` at `runtime_bridge.py:1018-1045` enumerates candidates in `mission-runtime.yaml`-first order under both `<root>/<mission_type>/` and `<root>/missions/<mission_type>/`.
- `_template_key_for_file()` at `runtime_bridge.py:1048-1053` calls `load_mission_template_file(path)` and returns `template.mission.key`; the resolver only accepts a candidate whose `mission.key == mission_type`.

**Implication**: No loader code change is required. As long as `mission-runtime.yaml` declares `mission.key: documentation` and parses cleanly under the `MissionTemplate` schema, the runtime resolves it ahead of `mission.yaml`. SC-007 is testable by a unit test that calls the same resolver and asserts the resolved path ends in `mission-runtime.yaml`. `_template_key_for_file` returning `None` for the legacy `mission.yaml` (which has `name: "Documentation Kitty"` but no `mission.key`) further guarantees the legacy file cannot win the race.

**Risk**: a future refactor could weaken the precedence. We pin it with a regression test (`test_documentation_drg_nodes.py` will include a `test_documentation_template_resolves_runtime_sidecar` assertion).

### Decision D2 — DRG authoring location

**Spec OQ #2**: are `action:documentation/*` nodes added to the shipped `src/doctrine/graph.yaml`, to a project overlay, or via a calibration step?

**Decision**: **Shipped `src/doctrine/graph.yaml`**, mirroring research exactly (research nodes live at `src/doctrine/graph.yaml:5-19`, edges at `src/doctrine/graph.yaml:577-630`).

**Evidence**:
- Research action nodes are hand-authored as five plain `{urn, kind: action, label}` entries: `src/doctrine/graph.yaml:5-19`.
- Research action edges are hand-authored as `{source: action:research/<x>, target: directive:DIRECTIVE_NNN | tactic:<name>, relation: scope}`: `src/doctrine/graph.yaml:577-630`.
- No extractor or calibration step writes these nodes; they are content-addressed in `graph.yaml`.

**Documentation node shapes (to author)**:

```yaml
- urn: action:documentation/audit
  kind: action
  label: audit
- urn: action:documentation/design
  kind: action
  label: design
- urn: action:documentation/discover
  kind: action
  label: discover
- urn: action:documentation/generate
  kind: action
  label: generate
- urn: action:documentation/publish
  kind: action
  label: publish
- urn: action:documentation/validate
  kind: action
  label: validate
```
(Alphabetical to match the existing file's ordering convention for the `action:` block.)

**Documentation edges (to author)** — chosen to mirror research's directive/tactic mix and to align with the action-bundle `index.yaml` directives lists. Each action gets at least 3 scope edges.

| Action | directives | tactics |
|---|---|---|
| `discover` | DIRECTIVE_003, DIRECTIVE_010 | requirements-validation-workflow, premortem-risk-identification |
| `audit` | DIRECTIVE_003, DIRECTIVE_037 | requirements-validation-workflow |
| `design` | DIRECTIVE_001, DIRECTIVE_003, DIRECTIVE_010 | adr-drafting-workflow, requirements-validation-workflow |
| `generate` | DIRECTIVE_010, DIRECTIVE_037 | requirements-validation-workflow |
| `validate` | DIRECTIVE_010, DIRECTIVE_037 | premortem-risk-identification, requirements-validation-workflow |
| `publish` | DIRECTIVE_010, DIRECTIVE_037 | requirements-validation-workflow |

**Verification**: a new test `tests/specify_cli/test_documentation_drg_nodes.py` asserts `load_validated_graph(repo).get_node('action:documentation/<x>')` is truthy and `resolve_context(graph, 'action:documentation/<x>', depth=2).artifact_urns` is non-empty for every action. This satisfies FR-004, FR-005, SC-002.

### Decision D3 — Guard data source

**Spec OQ #3**: do documentation guard branches enforce `mission.yaml`'s declarative predicates / `expected-artifacts.yaml`, or hardcode artifact checks?

**Decision**: **Hardcoded artifact checks inside `_check_composed_action_guard()`**, mirroring research at `src/specify_cli/next/runtime_bridge.py:560-589`. No new YAML parser. No call into `gap_analysis.py`. No coupling to `expected-artifacts.yaml`.

**Evidence**:
- The research guard branch hardcodes `feature_dir / "spec.md"`, `feature_dir / "plan.md"`, `feature_dir / "source-register.csv"`, `feature_dir / "findings.md"`, `feature_dir / "report.md"`, plus calls to local helpers `_count_source_documented_events()` (`runtime_bridge.py:445-473`) and `_publication_approved()` (`runtime_bridge.py:476-512`) for event-driven gates.
- `_check_composed_action_guard()` already receives `feature_dir: Path` (signature at `runtime_bridge.py:515-522`); no plumbing change is needed.
- `expected-artifacts.yaml` informs **what** to check (the legacy file is the spec for canonical paths) but is not parsed at runtime; the guard inlines the paths it documents.

**Documentation guard branch shape (to author)**:

```python
if mission == "documentation":
    if action == "discover":
        if not (feature_dir / "spec.md").is_file():
            failures.append("Required artifact missing: spec.md")
    elif action == "audit":
        if not (feature_dir / "gap-analysis.md").is_file():
            failures.append("Required artifact missing: gap-analysis.md")
    elif action == "design":
        if not (feature_dir / "plan.md").is_file():
            failures.append("Required artifact missing: plan.md")
    elif action == "generate":
        if not _has_generated_docs(feature_dir):
            failures.append("Required artifact missing: docs/**/*.md (no Markdown files generated under docs/)")
    elif action == "validate":
        if not (feature_dir / "audit-report.md").is_file():
            failures.append("Required artifact missing: audit-report.md")
    elif action == "publish":
        if not (feature_dir / "release.md").is_file():
            failures.append("Required artifact missing: release.md")
    else:
        # Fail-closed default for unknown documentation actions (mirror of research lines 586-588).
        failures.append(
            f"No guard registered for documentation action: {action}"
        )
    return failures
```

A new private helper `_has_generated_docs(feature_dir: Path) -> bool` recursively globs `docs/**/*.md` under `feature_dir` and returns `True` iff at least one matching file exists. This is the simplest predicate that satisfies FR-008(d) without re-parsing `expected-artifacts.yaml` or coupling to `pathlib.Path.match` semantics for `**` (use `Path.rglob('*.md')` rooted at `feature_dir / "docs"` and short-circuit on first hit).

### Decision D4 — PromptStep shape per action

**Spec OQ #4**: which steps bind `contract_ref`, and which use the contract-synthesis path?

**Decision**: **No `contract_ref` on any documentation step.** All six composed steps use the contract-synthesis path, mirroring research (`src/specify_cli/missions/research/mission-runtime.yaml:21-53`).

**Evidence**:
- `PromptStep` schema at `src/specify_cli/next/_internal_runtime/schema.py:401-435` makes both `contract_ref` and `agent_profile` optional, and accepts the YAML alias `agent-profile` via Pydantic `populate_by_name=True`.
- The research mission-runtime.yaml header comment at `src/specify_cli/missions/research/mission-runtime.yaml:9-13` explicitly states: *"Composition uses the contract-synthesis path (no `contract_ref` set on these PromptSteps), so the shipped step contracts under `src/doctrine/mission_step_contracts/shipped/research-*.step-contract.yaml` remain authoritative for action execution."*
- Research's six actual steps each declare only `id`, `title`, optional `depends_on`, `agent-profile`, `prompt_template`, `description`. None declare `contract_ref`. We mirror this byte-for-byte for documentation.

**Documentation `PromptStep` shapes (to author)** — six composed steps + one `accept` terminal step:

| id | title | depends_on | agent-profile | prompt_template |
|---|---|---|---|---|
| `discover` | Documentation Discovery | — | `researcher-robbie` | `discover.md` |
| `audit` | Documentation Audit | `[discover]` | `researcher-robbie` | `audit.md` |
| `design` | Documentation Design | `[audit]` | `architect-alphonso` | `design.md` |
| `generate` | Documentation Generation | `[design]` | `implementer-ivan` | `generate.md` |
| `validate` | Documentation Validation | `[generate]` | `reviewer-renata` | `validate.md` |
| `publish` | Documentation Publication | `[validate]` | `reviewer-renata` | `publish.md` |
| `accept` | Acceptance | `[publish]` | (none — non-composed terminal step) | `accept.md` |

The `prompt_template` filenames are advisory; the contract-synthesis path does not require these files to exist for composition to work (the runtime falls back to a synthesized prompt). The implementer **may** create lightweight templates under `src/specify_cli/missions/documentation/templates/` for parity with research, but they are out-of-scope-for-acceptance — the FRs only require the runtime to advance, not for templates to render specific text.

### Decision D5 — Terminal `accept` step

**Spec OQ #5**: does the runtime schema require a non-composed `accept` step?

**Decision**: **Yes — include an `accept` step** mirroring research at `src/specify_cli/missions/research/mission-runtime.yaml:55-59`. `accept` is **not** added to `_COMPOSED_ACTIONS_BY_MISSION["documentation"]`.

**Evidence**:
- `MissionTemplate` schema at `src/specify_cli/next/_internal_runtime/schema.py:445-450` does not strictly require an `accept` step (`steps: list[PromptStep] = Field(default_factory=list)` — empty list is valid). However, every shipped built-in mission has a terminal `accept` step today (research at `src/specify_cli/missions/research/mission-runtime.yaml:55-59`; software-dev's runtime template has the same shape). Mirroring it preserves operator parity.
- `_COMPOSED_ACTIONS_BY_MISSION` at `src/specify_cli/next/runtime_bridge.py:272-275` does not list `accept` for any mission. `accept` is excluded so that the legacy DAG handler advances the run-state to "accepted" without dispatching through composition. We preserve that contract for documentation.

**Result**: the `documentation` entry added to `_COMPOSED_ACTIONS_BY_MISSION` lists exactly the six action verbs `{discover, audit, design, generate, validate, publish}`. `accept` is the seventh step in the runtime template but does not enter the composition fast path.

### Decision D6 — `generate` artifact predicate

**Spec OQ #6**: is the gate "any Markdown file under `docs/`" or "an explicit top-level `docs/index.md`"?

**Decision**: **"At least one `*.md` file exists recursively under `feature_dir / "docs"`."** (`_has_generated_docs(feature_dir)` returns `True` iff `(feature_dir / "docs").is_dir()` and `next((feature_dir / "docs").rglob("*.md"), None) is not None`.)

**Rationale**:
- The legacy `expected-artifacts.yaml` at `src/specify_cli/missions/documentation/expected-artifacts.yaml:51-56` declares `path_pattern: "docs/**/*.md"` for the `output.docs.generated` artifact key. The simplest predicate that promotes this from non-blocking to blocking without changing the user-facing contract is "any Markdown file matching the pattern".
- Requiring `docs/index.md` specifically would impose a Divio entry-point convention that the legacy mission.yaml does not declare and that some operators (e.g. an iteration that only updates `docs/api/foo.md`) would reasonably skip. The spec says this is plan-time choice; we choose the lower-friction predicate.
- The predicate is observable, has zero false-positive risk on a clean feature_dir (the empty case the integration walk relies on for SC-003), and is symmetric with how research's `gathering` guard counts events (it checks "≥3 source_documented", not "specific event names").

**Risk**: an operator could create `docs/notes.md` and bypass the predicate without producing real output. The plan's mitigation is that **`validate` and `publish`** guards (D7) require explicit `audit-report.md` and `release.md` artifacts — those are the tighter gates on real publication. `generate` is allowed to be a coarse "did anything land" check.

### Decision D7 — `validate` and `publish` artifact paths

**Spec OQ #7**: commit to specific paths so FR-008(e) and FR-008(f) are observable.

**Decision**:
- **`validate` gate**: `feature_dir / "audit-report.md"` must exist.
- **`publish` gate**: `feature_dir / "release.md"` must exist.

**Evidence**:
- `audit-report.md` is already declared as the canonical audit artifact in the legacy `src/specify_cli/missions/documentation/mission.yaml:32` (`optional: [..., audit-report.md, ...]`) and at `src/specify_cli/missions/documentation/expected-artifacts.yaml:79-82` as `optional_always.evidence.audit-report`.
- `release.md` is declared as the canonical publication artifact at `src/specify_cli/missions/documentation/mission.yaml:36` (`optional: [..., release.md, ...]`).
- No other "validation report" or "publication handoff" artifact is referenced anywhere under `src/specify_cli/missions/documentation/` or `src/doctrine/missions/documentation/`.

The choice promotes both from "optional" (legacy mission.yaml status) to "blocking gate" (guard requirement). This matches the spec's directive that gates be "concrete observable files/events", not vague manual assertions. No path renames; we adopt the legacy names.

## Premortem Risks

(Per the `premortem-risk-identification` tactic. Each risk has a mitigation observable in the diff or test code.)

1. **Risk**: `mission.key: documentation` is rejected by the `MissionTemplate` Pydantic schema because some validator hardcodes `software-dev | research`.
   **Mitigation**: Phase 0 research includes a unit test that round-trips the new `mission-runtime.yaml` through `load_mission_template_file()` and asserts `template.mission.key == "documentation"`.

2. **Risk**: `_has_generated_docs(feature_dir)` returns True on `feature_dir / "docs/index.md"` even when the operator deleted `docs/` and re-created it as a single `index.md` placeholder.
   **Mitigation**: Acceptable. The predicate is intentionally permissive at `generate`; the tighter gates are `validate` (audit-report) and `publish` (release.md). Documented in D6 risk note.

3. **Risk**: the new doctrine action bundle `index.yaml` files reference directives or tactics that do not exist in `graph.yaml`, causing `load_validated_graph` to reject the graph.
   **Mitigation**: D2's directive/tactic table only references existing nodes (DIRECTIVE_001/003/010/037 and the four already-existing tactics: `requirements-validation-workflow`, `premortem-risk-identification`, `adr-drafting-workflow`). Phase 0 research includes a fast unit test that loads the validated DRG once before the integration walk runs.

4. **Risk**: the dogfood smoke runs against the source tree (`uv --directory <spec-kitty-repo>`) instead of from a separate temp repo (`uv --project <spec-kitty-repo>`), which #735 documents pollutes the source repo and corrupts JSON output.
   **Mitigation**: The quickstart at `quickstart.md` is the single source of truth for the smoke command sequence; the mission-review skill executes that exact sequence; reviewers grep the smoke evidence section for `--directory` and downgrade to UNVERIFIED on any hit (NFR-005, C-008, C-010).

5. **Risk**: `_check_composed_action_guard()` becomes unwieldy when the documentation branch is added (it already handles software-dev and research). A future seventh mission inheriting the same pattern adds another 30+ lines.
   **Mitigation**: Out of scope for #502. The brief explicitly says no architecture changes to the substrate; refactoring the guard dispatch into a registry is a separate Phase 7 candidate. We document the tech-debt line item in the plan footnotes for the `runtime_bridge.py` PR description, not the spec.

6. **Risk**: a future test author adds `unittest.mock.patch("…_dispatch_via_composition")` to `test_documentation_runtime_walk.py` to make a flake go away, defeating FR-013 / C-007.
   **Mitigation**: The test file's module docstring (mirroring research's at `tests/integration/test_research_runtime_walk.py:1-21`) lists the forbidden patch targets explicitly. The mission-review skill greps the file for any of them; any hit fails review.

## Requirements ↔ Plan map

(Per the `requirements-validation-workflow` tactic. Each spec FR/NFR/C/SC has at least one plan-side artifact that proves it.)

| Spec ID | Plan artifact / decision | Verification |
|---|---|---|
| FR-001, FR-002, FR-010, SC-001 | D1 (loader precedence already in code) + new `mission-runtime.yaml` | `test_documentation_runtime_walk.py::test_get_or_start_run_succeeds_for_documentation` |
| FR-003 | New `mission-runtime.yaml` per D4/D5 | `test_documentation_runtime_walk.py::test_documentation_template_resolves_runtime_sidecar` |
| FR-004, FR-005, FR-006, SC-002 | D2 (DRG nodes + edges + action-bundle index.yaml) | `test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` |
| FR-007, FR-008, FR-009, FR-017, SC-003 | D3, D6, D7 (hardcoded guard branch + fail-closed default) | `test_runtime_bridge_documentation_composition.py::test_guard_failures_*`, `test_documentation_runtime_walk.py::test_unknown_documentation_action_fails_closed` |
| FR-011, FR-012 | Inherited from substrate; no new code | `test_documentation_runtime_walk.py::test_paired_invocation_lifecycle_is_recorded` |
| FR-013, SC-004 | New `test_documentation_runtime_walk.py` with explicit C-007 docstring guard | grep + reviewer enforcement (mission-review) |
| FR-014, NFR-002, SC-005 | No edits to existing test surfaces | full pytest run on the regression-suite list (NFR-002) |
| FR-015 | 6 new step contracts, 6 new action bundles, 6 new profile-default entries, 1 new dispatch entry | unit tests for contract loading + profile defaults + dispatch entry |
| FR-016 | D4 + executor.py edit | `test_documentation_composition.py::test_profile_defaults_per_action` |
| FR-018 | D1 (coexistence) | `test_documentation_template_resolves_runtime_sidecar` (the assertion includes "path ends with `mission-runtime.yaml`, not `mission.yaml`") |
| NFR-001 | Test files enumerated in Project Structure | full pytest run |
| NFR-003 | mypy --strict gate | CI + plan-time `uv run --python 3.13 --extra lint mypy --strict <changed-files>` |
| NFR-004 | ruff gate | CI + plan-time `uv run --python 3.13 --extra lint ruff check <changed-files>` |
| NFR-005, NFR-006, SC-006, C-008, C-010 | quickstart.md (the dogfood smoke command sequence) + mission-review skill enforcement | mission-review evidence section |
| NFR-007 | DRG resolve-context microbenchmark | a small `test_documentation_drg_nodes.py::test_resolve_context_within_research_2x` test |
| C-001, C-002, C-003, C-005, C-009 | No changes to LLM-callsites; no new shipped profiles; contracts have no `expected_artifacts` | inspection + grep gates in mission-review |
| C-004 | "Out of Scope" section in spec is the gate; no plan-side artifact for excluded items | n/a |
| C-006 | D1 (coexistence chosen, justified) | n/a |
| C-007 | C-007 docstring at top of `test_documentation_runtime_walk.py` + mission-review grep | reviewer enforcement |
| SC-007 | D1 + dedicated unit test | `test_documentation_template_resolves_runtime_sidecar` |

## Phase 0 — Research

Phase 0 research has been consolidated into `research.md` (separate file). It captures:

- A code-grounded audit of the loader (`_resolve_runtime_template_in_root`), DRG node/edge shape, `_check_composed_action_guard` research branch, `PromptStep` schema, and existing documentation legacy artifacts.
- Verbatim YAML / Python snippets for the structures the implementer must mirror.
- The five tests in `tests/integration/test_research_runtime_walk.py` that the documentation walk mirrors.

`research.md` resolves all 7 spec Open Questions before tasks are generated.

## Phase 1 — Design & Contracts

Phase 1 outputs:

- `data-model.md` — file inventory (every YAML/Python file added or edited, with its shape and the FR it satisfies) plus DRG node/edge schemas for the six documentation actions.
- `contracts/` — one file per shipped step contract (a "shape contract" describing required keys, action verb, mission key, delegate kinds), plus one DRG-shape contract.
- `quickstart.md` — the operator dogfood smoke command sequence (the same sequence the mission-review skill executes).

These files are committed alongside `plan.md` so the implementer can render YAML directly from the contracts.

## Charter Check (post-design)

Re-evaluation after Phase 1 design:

- **DIRECTIVE_003 Decision Documentation**: ✅ All 7 spec Open Questions resolved with code citations in this plan and in `research.md`.
- **DIRECTIVE_010 Specification Fidelity**: ✅ The Requirements ↔ Plan map shows every spec ID has a plan artifact and a verification target.
- **Charter policy stack** (`pytest`, `mypy --strict`, `ruff`, 90% coverage): ✅ NFR-001/NFR-003/NFR-004 directly enforce these. The Project Structure adds 4 new test files; the integration walk + DRG-node test + composition test + runtime-bridge test give us coverage on every changed surface.
- **Active tactics** (ADR drafting, premortem, requirements validation): ✅ All three sections exist in this plan.

**Result**: PASS. No new gate violations introduced by Phase 1 design.

## Complexity Tracking

(Empty — no charter violations, no scope creep.)

## Branch Strategy (re-stated)

- Current branch at workflow start: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- `branch_matches_target`: `true`

Completed changes will merge into `main`. No alternate landing branch is required.

## Next command

`/spec-kitty.tasks` — break this plan into reviewable work packages. Suggested WP shape:

- WP01 — Runtime sidecar template (both `src/specify_cli/missions/documentation/mission-runtime.yaml` and `src/doctrine/missions/documentation/mission-runtime.yaml`) + unit test that the loader resolves it ahead of legacy `mission.yaml`.
- WP02 — Six shipped step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml` + parametrized contract-loading unit test.
- WP03 — Six action doctrine bundles under `src/doctrine/missions/documentation/actions/<action>/{index.yaml,guidelines.md}`.
- WP04 — DRG wiring: 6 nodes + ~16 edges in `src/doctrine/graph.yaml` + `test_documentation_drg_nodes.py`.
- WP05 — Composition dispatch wiring: `_COMPOSED_ACTIONS_BY_MISSION` entry + 6 `_ACTION_PROFILE_DEFAULTS` entries + composition unit test.
- WP06 — Guard branch (D3+D6+D7) + `_has_generated_docs` helper + runtime-bridge unit test for guard parity and unknown-action fail-closed.
- WP07 — Real-runtime integration walk `tests/integration/test_documentation_runtime_walk.py` mirroring `test_research_runtime_walk.py` (5 tests).
- WP08 — Quickstart (`quickstart.md` already authored at plan time) + dogfood smoke evidence collection in mission-review.

WPs 01..03 are independent and can run in parallel. WP04 can run in parallel with 01..03 once the action verbs are pinned. WP05/WP06 depend on 04 (composition entry is gated by DRG nodes existing). WP07 depends on 01..06. WP08 is the mission-review gate.
