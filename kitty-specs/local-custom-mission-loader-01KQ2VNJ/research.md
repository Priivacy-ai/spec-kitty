# Phase 0 Research: Local Custom Mission Loader

This document records the planning-phase research and decisions that ground [plan.md](./plan.md). Each entry follows the ADR-style format from the charter's adr-drafting-workflow tactic: **Decision · Rationale · Alternatives**.

---

## R-001 · Retrospective marker spelling

**Decision.** A custom mission MUST declare a final `PromptStep` whose `id == "retrospective"`. The validator checks one rule: the last entry in `steps[]` (after dependency-aware sort) has `id == "retrospective"`. No execution semantics this tranche.

**Rationale.** Reuses the existing required `id: str` field on `PromptStep` (already validated to be non-empty, unique by virtue of how steps are referenced). No schema migration. Trivial to validate and trivial for authors to learn. The retrospective-execution tranche (#506–#511) can later attach behavior to this same identifier without breaking any v1 mission YAML.

**Alternatives considered.**
- *Add `retrospective: bool` flag on `PromptStep`.* Requires schema migration; the bool is bistate and any value other than `true` becomes a silent failure mode.
- *Add a `kind: Literal["composed", "decision_required", "retrospective"]` field.* Cleaner long-term, but introduces a discriminator that the engine planner does not yet read. Premature.
- *Re-use `audit_steps[]`.* `audit_steps` is for end-of-mission audits, not the retrospective itself; semantics would conflict.

**Verifying test.** `tests/unit/mission_loader/test_retrospective_marker.py::test_missing_marker_rejected_with_stable_code`.

---

## R-002 · Shadow-of-built-in policy (resolves FR-011)

**Decision.** Reject any custom mission whose `mission.key` matches a reserved built-in key with stable error code `MISSION_KEY_RESERVED`. Reserved set is `frozenset({"software-dev", "research", "documentation", "plan"})`. Non-built-in shadowing (e.g., a project_override over a project_legacy entry) emits a warning with code `MISSION_KEY_SHADOWED` and uses the higher-precedence layer per the existing precedence chain.

**Rationale.** Built-in mission keys carry baked-in CLI behavior (`software-dev` drives the `/spec-kitty.specify→implement→review` workflow). Letting an operator silently override `software-dev` with a 7-step ERP YAML risks catastrophic surprise. Rejecting at load time is the cheapest safeguard. Non-built-in shadowing is the *intended* purpose of the override tier; warning preserves the existing override semantics.

**Alternatives considered.**
- *Allow override of built-ins.* Aligns with "everything is a mission", but the current mission system has hard-coded built-in dispatch decisions in `runtime_bridge.py`, `mission_step_contracts/executor.py`, and elsewhere. Allowing override now is a footgun.
- *Warn on built-in shadow rather than reject.* Operators may not see CLI warnings in CI logs. A hard reject at load time forces them to either rename or use a project_override override path. The diagnostic must be unmissable.

**Verifying test.** `test_loader_facade.py::test_reserved_key_shadow_rejected_with_MISSION_KEY_RESERVED`.

---

## R-003 · Profile resolution surface

**Decision.** Add `agent_profile: str | None = None` to `PromptStep` with Pydantic field alias `agent-profile`. The composition dispatcher in `runtime_bridge._dispatch_via_composition` reads this field from the frozen template's matching step and forwards it as `profile_hint` to `StepContractExecutionContext`. The existing `_ACTION_PROFILE_DEFAULTS` table in `mission_step_contracts/executor.py` is **not** modified; it remains the built-in fallback for `software-dev` only.

**Rationale.** `StepContractExecutor._resolve_profile_hint` already raises `StepContractExecutionError` when no profile_hint is provided AND no `_ACTION_PROFILE_DEFAULTS` entry exists for the (mission, action) tuple. So custom missions naturally fail closed if the operator forgets the field — no new error path needed. The Pydantic alias accepts both `agent_profile` and `agent-profile` from YAML, matching the spec's stated alias requirement (FR-008).

**Alternatives considered.**
- *Expand `_ACTION_PROFILE_DEFAULTS` with a per-mission fallback.* Rejected by FR-008 explicitly: "Do not expand software-dev-only `_ACTION_PROFILE_DEFAULTS` as the generic fallback for arbitrary custom missions." Would also entrench coupling between built-in defaults and custom missions.
- *Require profile binding at the `MissionStepContract` level.* Already supported via `contract_ref` (R-004); but operators authoring v1 expect per-step inline declaration to feel ergonomic. Both surfaces remain available.

**Verifying tests.** `test_validator_errors.py::test_step_without_profile_or_contract_rejected`; `test_contract_synthesis.py::test_synthesizes_one_contract_per_step_with_profile_hint`.

---

## R-004 · Custom mission step contracts

**Decision.** At load time, `mission_loader.contract_synthesis.synthesize_contracts(template)` walks each composed step (any step with `agent_profile` set) and builds a single-step `MissionStepContract` record with `mission=<template.mission.key>` and `action=<step.id>`. The result is registered into a per-process `MissionStepContractRepository` shadow that takes precedence within the run; the on-disk repository is unchanged. If a step declares `contract_ref: <existing-id>`, the synthesizer skips synthesis and the repository must already contain that ID; otherwise a `MISSION_CONTRACT_REF_UNRESOLVED` error fires.

**Rationale.** Authors expect to write one YAML file and have it run. Forcing them to also author `mission_step_contracts/*.yaml` for every step doubles the friction. Auto-synthesis preserves the architectural invariant that `StepContractExecutor` runs against a `MissionStepContract` (no bypass) while making the author surface concise. The optional `contract_ref` keeps the door open for advanced authors who want shared contracts across missions.

**Alternatives considered.**
- *Require explicit contract YAML files for every custom step.* Strong consistency with built-ins, but high author overhead. Rejected for v1.
- *Embed full contract content inside `PromptStep` instead of synthesizing.* Couples `MissionTemplate` to contract internals; bad layering. Rejected.

**Verifying tests.** `test_contract_synthesis.py::test_synthesizes_one_contract_per_step`, `..._respects_contract_ref_when_present`, `..._missing_contract_ref_rejected`.

---

## R-005 · Composition gate widening

**Decision.** `runtime_bridge._should_dispatch_via_composition(mission, step_id)` is extended:

- If `(mission, step_id)` is in the existing `_COMPOSED_ACTIONS_BY_MISSION` table, return True (built-ins keep their path).
- Else, look up the active mission's frozen template; if the step with id `step_id` has `agent_profile` set, return True.
- Else return False.

`_dispatch_via_composition` correspondingly reads the step's `agent_profile` from the frozen template (loaded via `_load_frozen_template`, already in scope) and passes it as `profile_hint`.

**Rationale.** Built-in dispatch is fully unchanged: `software-dev` template entries do not carry `agent_profile`, so they hit the first branch only. Custom missions opt into composition by setting `agent_profile`; absent that, they fall through to the legacy DAG handler — which is fine for steps that don't need composition (e.g., a documentation-only step). This satisfies FR-006 and FR-010 simultaneously.

**Alternatives considered.**
- *Expand `_COMPOSED_ACTIONS_BY_MISSION` per loaded custom mission.* Mutating module-level state at runtime is surprising and racy. Rejected.
- *Always dispatch via composition for every custom mission step.* Removes the operator's escape hatch for steps that intentionally don't have a profile (e.g., decision_required gates). Rejected — `requires_inputs` already routes those through the planner before composition would even be considered.

**Verifying tests.** Existing `tests/specify_cli/next/test_runtime_bridge_composition.py` (21 cases) stays green AND new `test_custom_mission_runtime_walk.py::test_composed_step_pairs_invocation_records` exercises the widened gate.

---

## R-006 · Decision-required step shape

**Decision.** Custom missions express decision-required gates by setting `requires_inputs: [<key>]` on a `PromptStep`, exactly the same convention as built-ins. The engine planner (`_internal_runtime/planner.py::plan_next`) already routes such steps through the `decision_required` decision shape; no new code or schema needed.

**Rationale.** Reuses an existing, well-tested mechanism. Authors learn one convention. Test coverage for `decision_required` already exists in the parity / coverage suites (see `tests/specify_cli/next/test_runtime_bridge_composition.py::test_advancement_helper_persists_decision_required_branch`). The ERP fixture's `ask-user` step demonstrates the pattern.

**Alternatives considered.**
- *Add a `kind: decision_required` discriminator.* Same redundancy concern as in R-001. Rejected.
- *Use a separate `decision: { input_key, options }` block.* More expressive (could declare option enumerations), but unnecessary in v1 — `requires_inputs` already names the input key, and the planner-side `DecisionRequest` already accepts options resolved from elsewhere.

**Verifying test.** `test_custom_mission_runtime_walk.py::test_decision_required_step_pauses_runtime_and_resumes`.

---

## R-007 · Mission-pack discovery

**Decision.** No new code. `_internal_runtime/discovery.py::_build_tiers` already constructs the `project_config` tier from `_project_config_pack_paths(project_dir)`, which reads `.kittify/config.yaml mission_packs`. Mission packs are integrated by writing a `mission-pack.yaml` manifest pointing at `mission.yaml` files. The validator and loader treat pack-discovered missions identically to direct `.kittify/missions/<key>/` definitions.

**Rationale.** Re-use over reinvention. The existing path is already test-covered by the discovery suite. Custom missions exposed via packs get the same validation / shadow rules.

**Alternatives considered.** None — the existing path is sufficient.

**Verifying test.** `test_loader_facade.py::test_loads_from_mission_pack_manifest`.

---

## R-008 · `--json` envelope and exit codes

**Decision.** `spec-kitty mission run` and the validator surface use this envelope:

Success:
```json
{
  "result": "success",
  "mission_key": "<key>",
  "mission_slug": "<slug>",
  "mission_id": "<ULID>",
  "feature_dir": "<absolute path>",
  "warnings": [{"code": "MISSION_KEY_SHADOWED", "message": "...", "details": {...}}]
}
```

Validation failure:
```json
{
  "result": "error",
  "error_code": "<CODE>",
  "message": "<human text>",
  "details": {"file": "<path>", "mission_key": "<key>", ...},
  "warnings": []
}
```

Exit codes: 0 success · 2 validation error · 1 infrastructure failure (filesystem, etc.). Without `--json`, the CLI emits a `rich.panel.Panel` containing the same fields.

**Rationale.** `result + error_code + message + details` is the established Spec Kitty CLI convention (`mission create`, `mission status`, `decision verify` all follow it). Exit code 2 distinguishes "operator-fixable" from infrastructure failure (1) so CI scripts can branch.

**Alternatives considered.**
- *Single exit code 1 for all errors.* Loses signal in CI. Rejected.
- *Embed warnings inside `details`.* Couples warnings to errors; rejected — warnings can attach to either success or error.

**Verifying test.** `test_mission_run_command.py::test_validation_error_json_envelope_shape_locked` and `..._success_envelope_shape_locked`.

---

## Open research items

None. All decisions are locked.

## Charter directives applied

- **DIRECTIVE_003 (Decision Documentation Requirement).** Each R-### above captures decision · rationale · alternatives.
- **DIRECTIVE_010 (Specification Fidelity Requirement).** Every decision references the FR / NFR / C it satisfies in [plan.md](./plan.md) §Requirements traceability.
- **Tactic: premortem-risk-identification.** Applied in [plan.md](./plan.md) §Risks.
- **Tactic: requirements-validation-workflow.** Each FR maps to a verifying test in [plan.md](./plan.md) §Requirements traceability.
- **Tactic: adr-drafting-workflow.** R-002, R-004, R-005 are the load-bearing ADR-shaped decisions; the others use the same shape for consistency.
