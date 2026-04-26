# Research — Documentation Mission Composition Rewrite

**Phase**: 0 (research)
**Status**: complete; all 7 spec Open Questions resolved with code-grounded evidence
**Audit baseline**: `62ec07b952d53e215857cd0e1c1eb7bf3f1a32dc` on `origin/main`
**Reference**: `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/research.md` (if needed for cross-check; the research mission's #504 work is the closest landed analog)

## R-001 — Loader resolution path

**Question (spec OQ #1)**: how does `spec-kitty next` for `mission_type='documentation'` choose between `mission.yaml` and `mission-runtime.yaml`?

**Decision**: coexistence; `mission-runtime.yaml` is preferred deterministically.
**Rationale**: the loader at `src/specify_cli/next/runtime_bridge.py:1056-1073` already implements sidecar-first precedence. Verbatim:

```python
def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    for candidate in _candidate_templates_for_root(root, mission_type):
        if not candidate.exists() or not candidate.is_file():
            continue

        paths_to_try = [candidate]
        # Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
        if candidate.name == "mission.yaml":
            runtime_sidecar = candidate.with_name("mission-runtime.yaml")
            if runtime_sidecar.exists() and runtime_sidecar.is_file():
                paths_to_try = [runtime_sidecar, candidate]

        for path in paths_to_try:
            template_key = _template_key_for_file(path)
            if template_key == mission_type:
                return path.resolve()

    return None
```

`_candidate_templates_for_root` (`runtime_bridge.py:1018-1045`) enumerates candidates in this order under each search root:

```
<root>/<mission_type>/mission-runtime.yaml
<root>/<mission_type>/mission.yaml
<root>/missions/<mission_type>/mission-runtime.yaml
<root>/missions/<mission_type>/mission.yaml
<root>/mission-runtime.yaml
<root>/mission.yaml
```

`_template_key_for_file` (`runtime_bridge.py:1048-1053`) uses `load_mission_template_file(path)` and only accepts a candidate whose `template.mission.key == mission_type`. The legacy documentation `mission.yaml` declares `name: "Documentation Kitty"` (top-level) but no `mission.key`, so even if precedence were inverted the legacy file would fail key validation and be skipped.

**Alternatives considered**:
- *Replace the legacy file outright*. Rejected: research kept its legacy `mission.yaml` for reference and any external docs reader expecting it would break. Coexistence has zero cost since the loader precedence already exists.
- *Remove the legacy `mission.yaml` and migrate downstream consumers*. Rejected: out of scope per spec C-004; we are not allowed to change SaaS / tracker / sync architecture, and the legacy file is also referenced by `expected-artifacts.yaml` consumers we have not audited.

**Evidence test**: a new unit test `test_documentation_template_resolves_runtime_sidecar` (in the integration walk file) calls `_resolve_runtime_template_in_root(...)` (or its package-internal equivalent) and asserts the resolved path basename is `mission-runtime.yaml`.

## R-002 — DRG node and edge shape for action nodes

**Question (spec OQ #2)**: where and how are `action:documentation/*` nodes authored?

**Decision**: hand-author 6 nodes + edges in `src/doctrine/graph.yaml`, mirroring research at `src/doctrine/graph.yaml:5-19` (nodes) and `src/doctrine/graph.yaml:577-630` (edges).

**Verbatim research node block (lines 5-19)**:

```yaml
- urn: action:research/gathering
  kind: action
  label: gathering
- urn: action:research/methodology
  kind: action
  label: methodology
- urn: action:research/output
  kind: action
  label: output
- urn: action:research/scoping
  kind: action
  label: scoping
- urn: action:research/synthesis
  kind: action
  label: synthesis
```

**Verbatim research edge sample (lines 577-588)**:

```yaml
- source: action:research/scoping
  target: directive:DIRECTIVE_003
  relation: scope
- source: action:research/scoping
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:research/scoping
  target: tactic:requirements-validation-workflow
  relation: scope
- source: action:research/scoping
  target: tactic:premortem-risk-identification
  relation: scope
```

**Existing directives + tactics referenced** (verified live in `graph.yaml`):
- `directive:DIRECTIVE_001` (Architectural Integrity Standard) — `graph.yaml:34-36`
- `directive:DIRECTIVE_003` (Decision Documentation Requirement) — `graph.yaml:37+`
- `directive:DIRECTIVE_010` (Specification Fidelity Requirement)
- `directive:DIRECTIVE_037` (Living Documentation Sync) — referenced by research/output edges
- `tactic:requirements-validation-workflow`
- `tactic:premortem-risk-identification`
- `tactic:adr-drafting-workflow`

These four tactics + three directives suffice for all six documentation actions; no new doctrine artifacts are needed.

**Action-bundle `index.yaml` shape** (`src/doctrine/missions/research/actions/scoping/index.yaml`, verbatim):

```yaml
action: scoping
directives:
  - 010-specification-fidelity-requirement
  - 003-decision-documentation-requirement
tactics:
  - requirements-validation-workflow
  - premortem-risk-identification
styleguides: []
toolguides: []
procedures: []
```

The bundle's directive/tactic lists use the *human slug form* (e.g. `010-specification-fidelity-requirement`), while `graph.yaml` edges use the URN form (`directive:DIRECTIVE_010`). The implementer must keep both lists in sync per action.

**Verification**: `tests/specify_cli/test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` calls `load_validated_graph(repo).get_node('action:documentation/<x>')` and `resolve_context(graph, 'action:documentation/<x>', depth=2)` for each of the six actions and asserts both are non-empty / `artifact_urns` is non-empty.

## R-003 — Guard data source

**Question (spec OQ #3)**: hardcoded artifact paths or driven by `mission.yaml` / `expected-artifacts.yaml`?

**Decision**: hardcoded inside `_check_composed_action_guard()`, mirroring research at `src/specify_cli/next/runtime_bridge.py:560-589`.

**Verbatim research branch**:

```python
if mission == "research":
    if action == "scoping":
        if not (feature_dir / "spec.md").is_file():
            failures.append("Required artifact missing: spec.md")
    elif action == "methodology":
        if not (feature_dir / "plan.md").is_file():
            failures.append("Required artifact missing: plan.md")
    elif action == "gathering":
        if not (feature_dir / "source-register.csv").is_file():
            failures.append("Required artifact missing: source-register.csv")
        if _count_source_documented_events(feature_dir) < 3:
            failures.append("Insufficient sources documented (need >=3)")
    elif action == "synthesis":
        if not (feature_dir / "findings.md").is_file():
            failures.append("Required artifact missing: findings.md")
    elif action == "output":
        if not (feature_dir / "report.md").is_file():
            failures.append("Required artifact missing: report.md")
        if not _publication_approved(feature_dir):
            failures.append("Publication approval gate not passed")
    else:
        failures.append(
            f"No guard registered for research action: {action}"
        )
    return failures
```

The function signature (`runtime_bridge.py:515-522`) already receives `feature_dir: Path`, so no plumbing change is needed. The two helpers (`_count_source_documented_events`, `_publication_approved`) are local to `runtime_bridge.py`. We add a new private helper `_has_generated_docs(feature_dir)` in the same module for the documentation `generate` predicate.

## R-004 — `PromptStep` schema and `agent-profile` alias

**Question (spec OQ #4)**: `contract_ref` or contract-synthesis path?

**Decision**: contract-synthesis (no `contract_ref`).

**Schema (`src/specify_cli/next/_internal_runtime/schema.py:401-435`)**:

```python
class PromptStep(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    prompt: str | None = None
    prompt_template: str | None = None
    expected_output: str | None = None
    requires_inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    raci: RACIAssignment | None = None
    raci_override_reason: str | None = None
    agent_profile: str | None = Field(default=None, alias="agent-profile")
    contract_ref: str | None = None
```

`populate_by_name=True` lets YAML use either `agent-profile` (canonical, used by research) or `agent_profile`. We use the hyphenated alias for parity with research.

**Verbatim research example (`src/specify_cli/missions/research/mission-runtime.yaml:21-32`)**:

```yaml
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
```

No step has `contract_ref`. The contract-synthesis path is selected by absence.

**Alternatives considered**:
- *Add `contract_ref: documentation-<action>` to each step*. Rejected: research's deliberate choice to omit `contract_ref` is documented in its mission-runtime.yaml header comment and we want byte-symmetry. The shipped contracts under `src/doctrine/mission_step_contracts/shipped/documentation-*.yaml` remain authoritative without being explicitly referenced from PromptStep.

## R-005 — Terminal `accept` step

**Decision**: include `accept` as the seventh step; do **not** add it to `_COMPOSED_ACTIONS_BY_MISSION`.

**Evidence**: research's accept step (`src/specify_cli/missions/research/mission-runtime.yaml:55-59`):

```yaml
  - id: accept
    title: Acceptance
    depends_on: [output]
    prompt_template: accept.md
    description: Validate research completeness and readiness for publication.
```

`MissionTemplate` schema does not require `accept` (`src/specify_cli/next/_internal_runtime/schema.py:445-450` defines `steps: list[PromptStep] = Field(default_factory=list)`), but every shipped built-in mission has one. We mirror.

`_COMPOSED_ACTIONS_BY_MISSION` (`src/specify_cli/next/runtime_bridge.py:272-275`) does not include `accept` for any mission; the legacy DAG handler advances run-state to "accepted" without composition. We preserve that contract.

## R-006 — `generate` artifact predicate

**Decision**: "at least one `*.md` file under `feature_dir / "docs"`".

**Implementation sketch**:

```python
def _has_generated_docs(feature_dir: Path) -> bool:
    docs_root = feature_dir / "docs"
    if not docs_root.is_dir():
        return False
    return next(docs_root.rglob("*.md"), None) is not None
```

**Source-of-truth alignment**: matches `path_pattern: "docs/**/*.md"` in `src/specify_cli/missions/documentation/expected-artifacts.yaml:51-56`.

**Rejected alternative**: requiring `docs/index.md`. Too restrictive; some operators only update `docs/api/foo.md` in iteration mode and would not produce a fresh `docs/index.md`. The legacy mission.yaml declares no Divio entry-point requirement.

## R-007 — `validate` and `publish` artifact paths

**Decision**:
- `validate` ⇒ `feature_dir / "audit-report.md"` exists.
- `publish` ⇒ `feature_dir / "release.md"` exists.

**Evidence**:
- `src/specify_cli/missions/documentation/mission.yaml:32` (legacy): `audit-report.md` listed under `artifacts.optional`.
- `src/specify_cli/missions/documentation/mission.yaml:36` (legacy): `release.md` listed under `artifacts.optional`.
- `src/specify_cli/missions/documentation/expected-artifacts.yaml:79-82`: `evidence.audit-report` declared with `path_pattern: "audit-report.md"`.

No other validation/publish artifact name appears anywhere under `src/specify_cli/missions/documentation/` or `src/doctrine/missions/documentation/`. The plan adopts the existing names (no renames).

## Reference test shape — `tests/integration/test_research_runtime_walk.py`

The documentation walk mirrors the research walk. Key scaffolding:

```python
"""Real-runtime integration walk for the research mission.

C-007 enforcement (spec constraint, FINAL GATE):
    The following symbols MUST NOT appear in any unittest.mock.patch target
    in this file. Reviewer greps; any hit blocks approval and blocks the
    mission from merging.

        - _dispatch_via_composition
        - StepContractExecutor.execute
        - ProfileInvocationExecutor.invoke
        - _load_frozen_template (and any frozen-template loader)
        - load_validated_graph
        - resolve_context
"""

from specify_cli.next._internal_runtime.engine import _read_snapshot
from specify_cli.next.runtime_bridge import (
    _check_composed_action_guard,
    decide_next_via_runtime,
    get_or_start_run,
)


def _init_min_repo(repo_root: Path) -> None:
    # git init, config user, README, initial commit
    ...


def _scaffold_research_feature(repo_root: Path, mission_slug: str) -> Path:
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_type": "research"}),
        encoding="utf-8",
    )
    return feature_dir
```

Documentation walk mirrors:
- `_scaffold_documentation_feature(repo_root, mission_slug)` writes `meta.json` with `{"mission_type": "documentation"}` and the legacy required artifacts (`spec.md`, `gap-analysis.md`, `plan.md`, plus a `docs/index.md`, `audit-report.md`, `release.md`) for the happy-path tests.
- 5 tests:
  1. `test_get_or_start_run_succeeds_for_documentation` — start without `MissionRuntimeError`.
  2. `test_documentation_template_resolves_runtime_sidecar` — assertion on resolver output.
  3. `test_composition_advances_one_documentation_step` — composition advances `discover` and the next-issued step is `audit`.
  4. `test_paired_invocation_lifecycle_is_recorded` — paired `started`/`completed` records with documentation-native action names.
  5. `test_missing_artifact_blocks_with_structured_failure` — empty feature_dir produces guard failure naming `spec.md`.
  6. `test_unknown_documentation_action_fails_closed` — `_check_composed_action_guard("ghost", feature_dir, mission="documentation")` returns `["No guard registered for documentation action: ghost"]`.

## Cross-cutting verifications planned

- `mypy --strict` on `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/mission_step_contracts/executor.py`, all 6 new step contracts (YAML — schema-validated by `pytest`), and the new test file. NFR-003 says zero new findings.
- `ruff check` on the same set. NFR-004.
- A microbenchmark in `test_documentation_drg_nodes.py` that times `resolve_context` on documentation actions and compares the median to the research median (NFR-007).

## Open items left for implementation

- The exact directive/tactic mix per documentation action (D2 table in `plan.md`) is the only authoring choice that is not byte-deterministic from the spec. The plan commits to a specific mix; the implementer may swap individual edges if the action-bundle `index.yaml` and `graph.yaml` lists disagree. The unit test that loads the validated graph will catch any mismatch.
