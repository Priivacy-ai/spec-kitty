---
work_package_id: WP04
title: Artifact filename seam — relocate + resolver + call-site conversion (surface C green,
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
- C-001
- NFR-003
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rc3-charter-gate-predicate-inversion-01M0GGT1
base_commit: d82052e660f6042db6a45bb00b4e523ba7e6dde5
created_at: '2026-08-21T13:46:31.059827+00:00'
subtasks: []
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/runtime/resolver.py
create_intent:
- src/doctrine/missions/expected_artifact_manifest.py
- tests/specify_cli/runtime/test_configured_artifact_name.py
- tests/doctrine/missions/test_expected_artifact_manifest_relocation.py
execution_mode: code_change
owned_files:
- src/specify_cli/dossier/manifest.py
- src/specify_cli/dossier/__init__.py
- src/specify_cli/dossier/indexer.py
- src/doctrine/missions/__init__.py
- src/doctrine/missions/expected_artifact_manifest.py
- src/doctrine/missions/step_projection.py
- src/specify_cli/runtime/resolver.py
- src/specify_cli/analysis_report.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/cli/commands/agent_retrospect.py
- tests/specify_cli/runtime/test_configured_artifact_name.py
- tests/doctrine/missions/test_expected_artifact_manifest_relocation.py
- tests/dossier/test_manifest.py
- tests/dossier/test_manifest_guard_parity.py
- tests/sync/test_dossier_pipeline.py
role: implementer
tags:
- artifact-seam
- doctrine
- C-001
- green-characterization
tracker_refs: []
---

# WP04 — Artifact filename seam: green refactor (#3599)

## Context (see plan.md §3 WP04a, ADR)
Build `artifact_kind → filename` from the single per-type authority `expected-artifacts.yaml` `path_pattern` (read-only via `src/doctrine/missions/repository.py:362 get_expected_artifacts`), twinning the template seam. **Green characterization — NFR-003 byte-compatible for the four built-ins; no behaviour change.**

**Every new test file MUST declare a routed `pytestmark` (CI collection gate, POST-TASKS §pedro):** `test_configured_artifact_name.py` → `pytestmark = [pytest.mark.unit, pytest.mark.fast]`; `test_expected_artifact_manifest_relocation.py` → `pytestmark = [pytest.mark.fast, pytest.mark.doctrine]`.

## Red-first / characterization (ATDD)
1. **AC-9 load-bearing** (`test_configured_artifact_name.py`): all four built-ins resolve their canonical names through `resolve_configured_artifact_name`; **patching the per-type `path_pattern` source changes the output of EACH converted call site** — the resolver, `_HASH_INPUTS`, **the accept triple (`acceptance/__init__.py`), AND the retrospective precondition (`agent_retrospect.py`)** — proving each literal was removed, not shadowed. Assert the built-in filenames unchanged (NFR-003).
2. **AC-12 pins** (`test_configured_artifact_name.py`): the specific raises — `_substantive.py:281` `ValueError("Unknown kind: …")` and `mission_feature_resolution.py:62-66` `KeyError` "no silent default" — for an unmapped third kind (pin-and-defer). *(Pins live behaviour; those files stay read-only in WP04.)*
3. **C-001 relocation** (`test_expected_artifact_manifest_relocation.py`): `from doctrine.missions import ExpectedArtifactManifest` works **AND the legacy `from specify_cli.dossier.manifest import ExpectedArtifactManifest` still resolves at RUNTIME** (not just under TYPE_CHECKING); `tests/architectural/test_layer_rules.py` + `test_doctrine_public_surface.py` + `test_no_dead_symbols.py` stay green.

## Implementation (ordered — see plan.md §3 WP04a)
1. **Relocate** `ExpectedArtifactManifest`/`ExpectedArtifactSpec`/`ArtifactClassEnum` from `src/specify_cli/dossier/manifest.py:168` → `src/doctrine/missions/expected_artifact_manifest.py`; give the new module its own `__all__` (C-007) and enroll the three names in the doctrine public surface (`src/doctrine/missions/__init__.py` `__all__`). **Consumers (POST-TASKS-corrected):** (a) `dossier/indexer.py`; (b) `dossier/__init__.py:12-15,50-52` re-export from the new home; (c) `ManifestRegistry` uses the class at **RUNTIME** (`load_manifest`→`model_validate`, `from_yaml_file`) — **do NOT use a `TYPE_CHECKING`-only import (it `NameError`s at runtime while mypy stays green)**; instead relocate cleanly and keep `manifest.py`'s import-time isolation via a **lazy function-local import** (the existing `_doctrine_repository()` `# noqa: PLC0415` pattern) or a PEP 562 module `__getattr__` re-export so `from specify_cli.dossier.manifest import ExpectedArtifactManifest` keeps working lazily; (d) the three test importers `tests/dossier/test_manifest.py:458`, `tests/dossier/test_manifest_guard_parity.py:39`, `tests/sync/test_dossier_pipeline.py:234`. Direction `specify_cli→doctrine` stays legal.
2. Add `resolve_configured_artifact_name` + `required_artifacts_for(step)` in `src/specify_cli/runtime/resolver.py`, sourcing `path_pattern` by **consuming** `repository.py:362 get_expected_artifacts` read-only; `project_artifact_name_set` beside `project_template_set` (`step_projection.py:100`); charter bundle slot stays `Mapping[str, Any]` (C-001). **Audit all 10 tags resolve to today's built-in filenames.**
3. Convert **all three name-literal call sites** to the resolved name set (byte-compat, NFR-003): `_HASH_INPUTS` (`analysis_report.py:33`); the **accept triple** (`SPEC_FILE`/`PLAN_FILE`/`TASKS_FILE`, `src/specify_cli/acceptance/__init__.py`); the **retrospective precondition** (`for required in ("spec.md","plan.md","tasks.md")`, `src/specify_cli/cli/commands/agent_retrospect.py:247`). *(The `_PRESENCE_FILE_TAGS` contents + `validate_feature_structure` conversion + the stray-touch delete are WP05.)*

## DoD / validation surface
`PWHEADLESS=1 pytest tests/specify_cli/runtime/ tests/doctrine/ tests/dossier/ tests/sync/test_dossier_pipeline.py tests/architectural/test_layer_rules.py tests/architectural/test_doctrine_public_surface.py tests/architectural/test_no_dead_symbols.py -q` green (note the **runtime** `load_manifest` path exercised, not just types); all three name literals (`_HASH_INPUTS`, accept triple, retrospect precondition) read the resolved set; built-in outputs byte-identical; new module has `__all__`; ruff + mypy clean. Run `tests/architectural/test_ci_collection_completeness.py` to confirm the new test files route.
