# Data Model — Documentation Mission Composition Rewrite

**Phase**: 1 (design)

This document is the file inventory and shape contract for every artifact added or edited by this mission. It is the implementer's checklist; tasks.md will reference it directly.

## File inventory

### NEW — runtime sidecar templates

| Path | Shape contract | FRs |
|---|---|---|
| `src/specify_cli/missions/documentation/mission-runtime.yaml` | `MissionTemplate` YAML; see [Runtime template shape](#runtime-template-shape) below. | FR-003, FR-010, FR-018, SC-007 |
| `src/doctrine/missions/documentation/mission-runtime.yaml` | byte-for-byte mirror of the specify_cli copy (same shape; doctrine side is the canonical authoring location for downstream consumers). | FR-003 |

### NEW — shipped step contracts

Six files under `src/doctrine/mission_step_contracts/shipped/`. Each follows the existing schema (no new top-level fields per spec C-009).

| Path | Action verb | FRs |
|---|---|---|
| `documentation-discover.step-contract.yaml` | `discover` | FR-015, FR-016 |
| `documentation-audit.step-contract.yaml` | `audit` | FR-015, FR-016 |
| `documentation-design.step-contract.yaml` | `design` | FR-015, FR-016 |
| `documentation-generate.step-contract.yaml` | `generate` | FR-015, FR-016 |
| `documentation-validate.step-contract.yaml` | `validate` | FR-015, FR-016 |
| `documentation-publish.step-contract.yaml` | `publish` | FR-015, FR-016 |

See [Step contract shape](#step-contract-shape) below.

### NEW — action doctrine bundles

Twelve files under `src/doctrine/missions/documentation/actions/<action>/`:

| Path | Shape | FRs |
|---|---|---|
| `discover/index.yaml` | action bundle index (action + directives + tactics + empty styleguides/toolguides/procedures) | FR-006 |
| `discover/guidelines.md` | governance guidelines markdown for the action | FR-006 |
| `audit/index.yaml`, `audit/guidelines.md` | same | FR-006 |
| `design/index.yaml`, `design/guidelines.md` | same | FR-006 |
| `generate/index.yaml`, `generate/guidelines.md` | same | FR-006 |
| `validate/index.yaml`, `validate/guidelines.md` | same | FR-006 |
| `publish/index.yaml`, `publish/guidelines.md` | same | FR-006 |

See [Action bundle shape](#action-bundle-shape) below.

### EDIT — DRG graph

| Path | Edits |
|---|---|
| `src/doctrine/graph.yaml` | add 6 nodes (urn=`action:documentation/<verb>`, kind=`action`, label=`<verb>`); add ~16 scope edges from each action URN to its directives/tactics. See [DRG node and edge shapes](#drg-node-and-edge-shapes) below. |

### EDIT — runtime bridge dispatch

| Path | Edits |
|---|---|
| `src/specify_cli/next/runtime_bridge.py` | (1) add `"documentation": frozenset({"discover", "audit", "design", "generate", "validate", "publish"})` to `_COMPOSED_ACTIONS_BY_MISSION` (~line 274); (2) add a `if mission == "documentation": …` branch to `_check_composed_action_guard()` after the research branch (~line 588 in the current file); (3) add a private `_has_generated_docs(feature_dir: Path) -> bool` helper module-level. |

### EDIT — profile defaults

| Path | Edits |
|---|---|
| `src/specify_cli/mission_step_contracts/executor.py` | add 6 entries to `_ACTION_PROFILE_DEFAULTS` (~line 49): `("documentation", "discover"): "researcher-robbie"`, `("documentation", "audit"): "researcher-robbie"`, `("documentation", "design"): "architect-alphonso"`, `("documentation", "generate"): "implementer-ivan"`, `("documentation", "validate"): "reviewer-renata"`, `("documentation", "publish"): "reviewer-renata"`. |

### NEW — tests

| Path | Purpose | FRs |
|---|---|---|
| `tests/integration/test_documentation_runtime_walk.py` | real-runtime walk; mirrors `test_research_runtime_walk.py`; 6 tests (start, sidecar resolves, composition advances, paired lifecycle, missing-artifact guard failure, unknown-action fail-closed). C-007 docstring at top. | FR-001, FR-002, FR-007, FR-008, FR-013, FR-017, SC-001, SC-003, SC-004, SC-007, NFR-001 |
| `tests/specify_cli/mission_step_contracts/test_documentation_composition.py` | parametrized loading + profile-default tests for all 6 contracts. | FR-015, FR-016, NFR-001 |
| `tests/specify_cli/next/test_runtime_bridge_documentation_composition.py` | dispatch entry + `_check_composed_action_guard` parity for documentation; explicit unknown-action fail-closed. | FR-007, FR-008, FR-009, FR-017, NFR-001 |
| `tests/specify_cli/test_documentation_drg_nodes.py` | DRG node + `resolve_context` non-empty for each documentation action; microbenchmark vs research median (NFR-007). | FR-004, FR-005, FR-006, NFR-007 |

### KEPT — legacy files (no edits)

| Path | Status |
|---|---|
| `src/specify_cli/missions/documentation/mission.yaml` | kept; loader skips it because of D1 precedence; coexists for reference. |
| `src/doctrine/missions/documentation/mission.yaml` | kept; same reasoning. |
| `src/specify_cli/missions/documentation/expected-artifacts.yaml` | kept; the canonical declaration of artifact paths the new guard branch hardcodes. |
| `src/specify_cli/missions/documentation/templates/` | kept, unchanged; the contract-synthesis path tolerates missing prompt templates. |

## Runtime template shape

`mission.key: documentation` is the load gate; without it `_template_key_for_file` returns `None` and the loader falls back to the legacy `mission.yaml` (which itself returns `None` on key check, yielding `None` overall, which is the failure FR-001 forbids).

```yaml
# src/specify_cli/missions/documentation/mission-runtime.yaml
mission:
  key: documentation
  name: Documentation Kitty
  version: "2.0.0"

steps:
  - id: discover
    title: Documentation Discovery
    agent-profile: researcher-robbie
    prompt_template: discover.md
    description: Identify documentation needs, target audience, and the iteration mode (initial / gap-filling / mission-specific).

  - id: audit
    title: Documentation Audit
    depends_on: [discover]
    agent-profile: researcher-robbie
    prompt_template: audit.md
    description: Analyze existing documentation and produce gap-analysis.md.

  - id: design
    title: Documentation Design
    depends_on: [audit]
    agent-profile: architect-alphonso
    prompt_template: design.md
    description: Plan documentation structure, Divio types, and generator configuration in plan.md.

  - id: generate
    title: Documentation Generation
    depends_on: [design]
    agent-profile: implementer-ivan
    prompt_template: generate.md
    description: Produce documentation artifacts under docs/.

  - id: validate
    title: Documentation Validation
    depends_on: [generate]
    agent-profile: reviewer-renata
    prompt_template: validate.md
    description: Verify Divio adherence, accessibility, and completeness; emit audit-report.md.

  - id: publish
    title: Documentation Publication
    depends_on: [validate]
    agent-profile: reviewer-renata
    prompt_template: publish.md
    description: Prepare documentation for release and emit release.md handoff.

  - id: accept
    title: Acceptance
    depends_on: [publish]
    prompt_template: accept.md
    description: Validate documentation completeness, quality gates, and readiness for publication.
```

## Step contract shape

Each contract follows the existing shipped schema, mirroring `src/doctrine/mission_step_contracts/shipped/research-scoping.step-contract.yaml`. No new top-level fields. Per spec C-009, contracts must NOT add an `expected_artifacts` field. Example for `discover`:

```yaml
# src/doctrine/mission_step_contracts/shipped/documentation-discover.step-contract.yaml
schema_version: "1.0"
id: documentation-discover
action: discover
mission: documentation
steps:
  - id: bootstrap
    description: Load charter context for this action
    command: "spec-kitty charter context --action discover --role discover --json"
    inputs:
      - flag: --profile
        source: wp.agent_profile
        optional: true
      - flag: --tool
        source: env.agent_tool
        optional: true

  - id: capture_documentation_needs
    description: Capture target audience, iteration mode, and goals; emit spec.md.
    delegates_to:
      kind: directive
      candidates:
        - 010-specification-fidelity-requirement
        - 003-decision-documentation-requirement

  - id: validate_scope
    description: Validate documentation scope boundaries and feasibility.
    delegates_to:
      kind: tactic
      candidates:
        - requirements-validation-workflow

  - id: write_spec
    description: Write spec.md to kitty-specs/{mission_slug}/
    command: "Write spec.md in kitty-specs/{mission_slug}/"

  - id: commit_spec
    description: Commit the documentation spec to main branch.
    delegates_to:
      kind: directive
      candidates:
        - 029-agent-commit-signing-policy
        - 033-targeted-staging-policy
```

The other 5 contracts mirror this shape with action-appropriate substeps and `delegates_to` references. The `contracts/` directory of this plan contains a one-paragraph spec per contract describing the substep verbs and delegate references the implementer must use.

## Action bundle shape

Each action bundle has two files:

```yaml
# src/doctrine/missions/documentation/actions/discover/index.yaml
action: discover
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

The `guidelines.md` is governance prose for the action — the same authoring style as `src/doctrine/missions/research/actions/scoping/guidelines.md`. ~30-50 lines per action, focused on what makes a good output for that phase, written for the host LLM to consume as action-scoped doctrine.

## DRG node and edge shapes

### Nodes (add to `src/doctrine/graph.yaml` `nodes:` block, alphabetical within the `action:` URN family)

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

### Edges (add to `src/doctrine/graph.yaml` `edges:` block)

Each action gets a block of `relation: scope` edges. The full set:

```yaml
# discover
- source: action:documentation/discover
  target: directive:DIRECTIVE_003
  relation: scope
- source: action:documentation/discover
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:documentation/discover
  target: tactic:requirements-validation-workflow
  relation: scope
- source: action:documentation/discover
  target: tactic:premortem-risk-identification
  relation: scope

# audit
- source: action:documentation/audit
  target: directive:DIRECTIVE_003
  relation: scope
- source: action:documentation/audit
  target: directive:DIRECTIVE_037
  relation: scope
- source: action:documentation/audit
  target: tactic:requirements-validation-workflow
  relation: scope

# design
- source: action:documentation/design
  target: directive:DIRECTIVE_001
  relation: scope
- source: action:documentation/design
  target: directive:DIRECTIVE_003
  relation: scope
- source: action:documentation/design
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:documentation/design
  target: tactic:adr-drafting-workflow
  relation: scope
- source: action:documentation/design
  target: tactic:requirements-validation-workflow
  relation: scope

# generate
- source: action:documentation/generate
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:documentation/generate
  target: directive:DIRECTIVE_037
  relation: scope
- source: action:documentation/generate
  target: tactic:requirements-validation-workflow
  relation: scope

# validate
- source: action:documentation/validate
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:documentation/validate
  target: directive:DIRECTIVE_037
  relation: scope
- source: action:documentation/validate
  target: tactic:premortem-risk-identification
  relation: scope
- source: action:documentation/validate
  target: tactic:requirements-validation-workflow
  relation: scope

# publish
- source: action:documentation/publish
  target: directive:DIRECTIVE_010
  relation: scope
- source: action:documentation/publish
  target: directive:DIRECTIVE_037
  relation: scope
- source: action:documentation/publish
  target: tactic:requirements-validation-workflow
  relation: scope
```

Each action has at least 3 scope edges (matching research's lowest action `output`, which has 3 scope edges). The action-bundle `index.yaml` directives + tactics lists must match the corresponding edges 1-to-1; the validation test `test_documentation_drg_nodes.py::test_action_bundle_matches_drg_edges` enforces this.

## Guard branch shape

```python
# src/specify_cli/next/runtime_bridge.py — _check_composed_action_guard
# (insert after the research else-branch around line 588)

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
            failures.append(
                "Required artifact missing: docs/**/*.md "
                "(no Markdown files found under docs/)"
            )
    elif action == "validate":
        if not (feature_dir / "audit-report.md").is_file():
            failures.append("Required artifact missing: audit-report.md")
    elif action == "publish":
        if not (feature_dir / "release.md").is_file():
            failures.append("Required artifact missing: release.md")
    else:
        # Fail-closed default for unknown documentation actions.
        failures.append(
            f"No guard registered for documentation action: {action}"
        )
    return failures
```

The new helper:

```python
def _has_generated_docs(feature_dir: Path) -> bool:
    """Return True if at least one *.md file exists under feature_dir / 'docs'."""
    docs_root = feature_dir / "docs"
    if not docs_root.is_dir():
        return False
    return next(docs_root.rglob("*.md"), None) is not None
```

## Validation summary

| Spec ID | Validated by |
|---|---|
| FR-001..FR-002 | `test_documentation_runtime_walk.py::test_get_or_start_run_succeeds_for_documentation` + `test_composition_advances_one_documentation_step` |
| FR-003 | `test_documentation_runtime_walk.py::test_documentation_template_resolves_runtime_sidecar` |
| FR-004..FR-006 | `test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` |
| FR-007..FR-009 | `test_runtime_bridge_documentation_composition.py::test_guard_failures_*` |
| FR-010 | implicit — uses the same `load_mission_template` discovery walk; covered by FR-001 test |
| FR-011..FR-012 | `test_documentation_runtime_walk.py::test_paired_invocation_lifecycle_is_recorded` |
| FR-013, SC-004 | C-007 docstring at the top of `test_documentation_runtime_walk.py` + reviewer grep |
| FR-014, NFR-002, SC-005 | full pytest run on the regression-suite list |
| FR-015 | `test_documentation_composition.py::test_all_six_contracts_load_cleanly` |
| FR-016 | `test_documentation_composition.py::test_profile_defaults_per_action` |
| FR-017 | `test_documentation_runtime_walk.py::test_unknown_documentation_action_fails_closed` (and unit-level test in `test_runtime_bridge_documentation_composition.py`) |
| FR-018, SC-007 | `test_documentation_template_resolves_runtime_sidecar` |
| NFR-001 | full new-test-file inventory |
| NFR-003, NFR-004 | mypy --strict + ruff in CI |
| NFR-005, SC-006, C-008, C-010 | `quickstart.md` smoke + mission-review evidence enforcement |
| NFR-006 | invocation-trail records inspected in the integration walk |
| NFR-007 | `test_documentation_drg_nodes.py::test_resolve_context_within_research_2x` |
