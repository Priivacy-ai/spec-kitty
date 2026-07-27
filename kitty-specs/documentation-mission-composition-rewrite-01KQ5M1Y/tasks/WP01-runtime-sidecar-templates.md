---
work_package_id: WP01
title: Runtime Sidecar Templates
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-010
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-documentation-mission-composition-rewrite-01KQ5M1Y
base_commit: 1af027188ec1fd7c005aaf52edc5de716d106c63
created_at: '2026-04-26T19:57:07.798114+00:00'
subtasks:
- T001
- T002
- T003
shell_pid: "49278"
agent: "claude:opus-4.7:reviewer-renata:reviewer"
history:
- action: created
  at: '2026-04-26T19:46:00Z'
  by: tasks
authoritative_surface: src/specify_cli/missions/documentation/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/documentation/mission-runtime.yaml
- src/doctrine/missions/documentation/mission-runtime.yaml
- tests/specify_cli/test_documentation_template_resolution.py
tags: []
---

# WP01 — Runtime Sidecar Templates

## Objective

Author the runtime sidecar `mission-runtime.yaml` for the documentation mission in both the CLI tree (`src/specify_cli/missions/documentation/`) and the doctrine tree (`src/doctrine/missions/documentation/`), so the loader at `src/specify_cli/next/runtime_bridge.py:1056-1073` resolves the new sidecar ahead of the legacy `mission.yaml`. Add a unit test that pins this resolution.

## Context

The loader's sidecar precedence is already in place. Verbatim:

```python
# src/specify_cli/next/runtime_bridge.py:1062-1066
paths_to_try = [candidate]
# Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
if candidate.name == "mission.yaml":
    runtime_sidecar = candidate.with_name("mission-runtime.yaml")
    if runtime_sidecar.exists() and runtime_sidecar.is_file():
        paths_to_try = [runtime_sidecar, candidate]
```

`_template_key_for_file(path)` (`runtime_bridge.py:1048-1053`) gates each candidate by `template.mission.key == mission_type`. The legacy `src/specify_cli/missions/documentation/mission.yaml` declares `name: "Documentation Kitty"` but no `mission.key`, so it cannot satisfy the gate. As long as the new `mission-runtime.yaml` declares `mission.key: documentation` and parses cleanly under `MissionTemplate`, the loader resolves the sidecar.

This WP is the runnability gate (FR-001/FR-002/FR-003/FR-010/FR-018). Without it, no other WP can be tested end-to-end.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution lane: allocated by `spec-kitty agent mission finalize-tasks`. Enter the WP via `spec-kitty agent action implement WP01 --agent <name>` from the project root checkout. The CLI creates/uses the lane worktree under `.worktrees/<slug>-<mid8>-lane-<x>/`.

## Subtasks

### T001 — Author `src/specify_cli/missions/documentation/mission-runtime.yaml`

**Purpose**: introduce the runtime sidecar that the loader resolves for `mission_type='documentation'`.

**Steps**:
1. Read `src/specify_cli/missions/research/mission-runtime.yaml` end-to-end as the template.
2. Create the new file with this exact content (mirrored shape from research):

   ```yaml
   # =============================================================================
   # Runtime Planning Template (v2.0.0) — documentation mission
   # =============================================================================
   #
   # Sidecar planning template alongside the legacy state-machine mission.yaml.
   # Used by spec-kitty next for run-state planning. The CLI-internal runtime
   # owns DAG planning. Live action dispatch for discover/audit/design/generate/
   # validate/publish is handled by StepContractExecutor composition in
   # specify_cli.next.runtime_bridge after this rewrite lands. Composition uses
   # the contract-synthesis path (no contract_ref set on these PromptSteps), so
   # the shipped step contracts under
   # src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml
   # remain authoritative for action execution.

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

3. Verify the file parses as YAML (`yaml.safe_load(open(...))`) without error.
4. Verify `load_mission_template_file(Path("src/specify_cli/missions/documentation/mission-runtime.yaml"))` returns a `MissionTemplate` whose `mission.key == "documentation"` and whose `len(steps) == 7`.

**Files**: `src/specify_cli/missions/documentation/mission-runtime.yaml` (new, ~70 lines).

**Validation**:
- [ ] File parses as YAML.
- [ ] `MissionTemplate` schema accepts the file.
- [ ] `mission.key == "documentation"`.
- [ ] 7 steps total (6 composed + 1 accept).

### T002 — Mirror to doctrine tree

**Purpose**: keep the doctrine-side and specify_cli-side runtime templates in sync (research already does this).

**Steps**:
1. Copy the file authored in T001 to `src/doctrine/missions/documentation/mission-runtime.yaml`. Byte-for-byte identical content.
2. Verify both files are byte-equal: `cmp src/specify_cli/missions/documentation/mission-runtime.yaml src/doctrine/missions/documentation/mission-runtime.yaml` exits 0.

**Files**: `src/doctrine/missions/documentation/mission-runtime.yaml` (new, ~70 lines).

**Validation**:
- [ ] Files are byte-equal.
- [ ] Doctrine-side file parses as YAML and validates against `MissionTemplate` schema.

### T003 — Author template-resolution unit test

**Purpose**: pin loader precedence so a future refactor cannot regress D1.

**Steps**:
1. Create `tests/specify_cli/test_documentation_template_resolution.py`.
2. Author the test (skeleton):

   ```python
   """Regression tests for documentation mission-runtime.yaml resolution.

   D1 of plan.md commits to coexistence of mission.yaml + mission-runtime.yaml.
   The loader must resolve mission-runtime.yaml ahead of the legacy mission.yaml
   for any documentation mission_type.
   """

   from __future__ import annotations

   from pathlib import Path

   from specify_cli.next.runtime_bridge import _resolve_runtime_template_in_root


   def test_documentation_runtime_sidecar_wins_over_legacy_mission_yaml() -> None:
       """The package-level loader resolves mission-runtime.yaml for mission_type='documentation'."""
       package_root = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "missions"
       resolved = _resolve_runtime_template_in_root(package_root, "documentation")
       assert resolved is not None, "loader returned None for mission_type='documentation'"
       assert resolved.name == "mission-runtime.yaml", (
           f"expected mission-runtime.yaml; got {resolved.name}. "
           "If this fails, _resolve_runtime_template_in_root is no longer "
           "preferring the runtime sidecar over the legacy mission.yaml."
       )


   def test_documentation_runtime_template_declares_correct_mission_key() -> None:
       """The runtime sidecar's mission.key must be 'documentation' for loader gate."""
       from specify_cli.next._internal_runtime.schema import load_mission_template_file

       path = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "missions" / "documentation" / "mission-runtime.yaml"
       template = load_mission_template_file(path)
       assert template.mission.key == "documentation"
       assert len(template.steps) == 7  # 6 composed + accept
       step_ids = [step.id for step in template.steps]
       assert step_ids == ["discover", "audit", "design", "generate", "validate", "publish", "accept"]
   ```

3. Run the test: `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/test_documentation_template_resolution.py -v`.

**Files**: `tests/specify_cli/test_documentation_template_resolution.py` (new, ~50 lines).

**Validation**:
- [ ] Both tests pass.
- [ ] No mocks of any forbidden surface (`_dispatch_via_composition`, `StepContractExecutor.execute`, etc. — see C-007).

## Definition of Done

- [ ] T001/T002/T003 complete.
- [ ] `cmp` shows the two `mission-runtime.yaml` files are byte-equal.
- [ ] `pytest tests/specify_cli/test_documentation_template_resolution.py -v` passes.
- [ ] `ruff check src/specify_cli/missions/documentation/mission-runtime.yaml` and the test file pass cleanly (the YAML files don't get ruff-checked; the test file does).
- [ ] `mypy --strict tests/specify_cli/test_documentation_template_resolution.py` passes.

## Risks

1. The `MissionTemplate` Pydantic schema may have a literal validator restricting `mission.key` to a fixed set. If so, the test fails at schema-load time. Mitigation: read `src/specify_cli/next/_internal_runtime/schema.py` `MissionMeta` definition first; if a literal validator exists, the WP needs to extend it (one-line change, in-scope per the plan).
2. The `agent-profile` alias may not match between specify_cli and doctrine YAML loaders. Mitigation: research uses `agent-profile`; we mirror it. If a future schema strictifies on `agent_profile`, both files must update in lockstep.

## Reviewer Guidance

- Verify `cmp` of the two `mission-runtime.yaml` files exits 0.
- Verify the test file's docstring + the test for sidecar precedence + the test for `mission.key` + step list.
- Verify `_resolve_runtime_template_in_root` is imported (not mocked).
- Verify no edits to `runtime_bridge.py`, `schema.py`, or any non-WP-owned file.

## Next command

After WP01 lands, the next-action handler resolves WP02 (or WP03, both independent of WP01). Use:

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-04-26T19:57:09Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=48445 – Assigned agent via action command
- 2026-04-26T20:00:01Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=48445 – T001-T003 complete; cmp shows byte-equal sidecars; 2/2 tests pass; ruff+mypy clean
- 2026-04-26T20:00:29Z – claude:opus-4.7:reviewer-renata:reviewer – shell_pid=49278 – Started review via action command
- 2026-04-26T20:01:52Z – claude:opus-4.7:reviewer-renata:reviewer – shell_pid=49278 – Review passed: runtime sidecar templates byte-equal across both mission roots, 7-step DAG with correct agent-profile defaults and depends_on chain, both tests pass cleanly under ruff/mypy --strict with no mocks.
