# Implementation Plan: Local Custom Mission Loader

**Mission**: `local-custom-mission-loader-01KQ2VNJ`
**Date**: 2026-04-25
**Spec**: [spec.md](./spec.md)
**Branch contract**: current=`main`, planning_base=`main`, merge_target=`main`, branch_matches_target=true.

## Summary

Add a v1 local custom mission loader so project-authored mission YAML under `.kittify/missions/<key>/`, `.kittify/overrides/missions/<key>/`, and existing mission-pack hooks can run as first-class peers to the four built-in missions. The loader extends the existing internal-runtime discovery (no parallel loader), adds a structural validator (with stable error codes and `--json` shape), introduces `spec-kitty mission run <key> --mission <slug>` as a thin CLI surface, and lifts the composition-dispatch hard-guard from `software-dev`-only to "any mission whose runtime template marks per-step profile resolution explicitly". Built-in mission behavior is preserved by leaving `_ACTION_PROFILE_DEFAULTS` untouched and gating composition on the new per-step `agent_profile` field — built-ins keep their current path, custom missions take a parallel-but-shared composition path. Retrospective execution stays out of scope; only structural marker validation.

## Technical Context

| Field | Value |
| --- | --- |
| Language / Version | Python 3.11+ (charter) |
| Primary Dependencies | `typer`, `rich`, `ruamel.yaml`, `pydantic` (existing); `spec_kitty_events` (PyPI). No new external deps. |
| Storage | Filesystem only (YAML under `.kittify/`, runtime snapshots under existing `.kittify/runtime/`). |
| Testing | `pytest` with `pytest --cov` enforcing ≥ 90% on new code; `mypy --strict`; `ruff check`. |
| Target Platform | macOS / Linux dev environments + CI. |
| Project Type | Single project (CLI). |
| Performance Goals | Loader p95 < 250ms (NFR-001); ERP fixture suite < 10s (NFR-004). |
| Constraints | No `spec_kitty_runtime` imports; no legacy DAG fall-through; no SaaS / install. |
| Scale / Scope | One reference custom mission (ERP fixture); validator handles ≤ 50 steps per mission. |

## Charter Check

Charter mode at action plan: `compact` (already loaded for specify, action-scoped doctrine reused).

| Charter constraint | Stance in this plan |
| --- | --- |
| pytest with 90%+ test coverage for new code | Enforced via `pytest --cov` configured to fail under 90% on the new modules listed in §Source Code. |
| mypy --strict must pass | All new modules type-checked under `mypy --strict`; new fields use Pydantic v2 typed models. |
| Integration tests for CLI commands | A new integration suite under `tests/integration/test_mission_run_command.py` exercises `spec-kitty mission run` end-to-end against the ERP fixture. |
| DIRECTIVE_003 (Decision Documentation) | All planning decisions recorded in `research.md`. |
| DIRECTIVE_010 (Specification Fidelity) | Each FR / NFR / C is cross-referenced from the design artifacts; mission-review will verify FR coverage. |
| Tactic: premortem-risk-identification | §Risks below applies the premortem lens. |
| Tactic: requirements-validation-workflow | §Requirements traceability ties every FR to a verifying test. |
| Tactic: adr-drafting-workflow | An ADR-style decision capture in `research.md` covers the load-time contract synthesis decision and the composition-gate widening. |

No new charter conflicts surfaced. **Charter Check: PASS.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/local-custom-mission-loader-01KQ2VNJ/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── mission-run-cli.md        # CLI command contract (args + JSON shape)
│   └── validation-errors.md      # Stable error code enumeration
├── spec.md              # already exists
├── checklists/requirements.md
├── meta.json
└── tasks/               # populated by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── next/_internal_runtime/
│   ├── discovery.py         # extend: tier ordering kept; add reserved-key shadow rejection
│   ├── schema.py            # extend: PromptStep gains optional agent_profile (alias agent-profile) + optional retrospective marker convention; MissionTemplate gains validation hook
│   └── loader.py            # NEW: thin façade combining discover_missions + load_mission_template + validate_custom_mission
├── mission_loader/          # NEW package: validator + custom mission entry point
│   ├── __init__.py
│   ├── errors.py            # closed enum of error codes; structured payload model
│   ├── validator.py         # validate_custom_mission(template) -> ValidationReport
│   ├── retrospective.py     # has_retrospective_marker(template) -> bool
│   ├── contract_synthesis.py # build MissionStepContract records from a custom MissionTemplate
│   └── command.py           # spec-kitty mission run logic (callable, decoupled from Typer)
├── cli/commands/
│   └── mission_type.py      # extend: register `mission run` subcommand wired to mission_loader.command
├── mission_step_contracts/
│   └── executor.py          # extend: profile_hint sourced from per-step agent_profile when present (no _ACTION_PROFILE_DEFAULTS expansion)
└── next/runtime_bridge.py   # extend: composition gate widens to "mission_template declares composed steps" rather than only software-dev

tests/
├── unit/mission_loader/                          # NEW
│   ├── test_validator_errors.py                  # FR-004, NFR-002 (every error code reachable)
│   ├── test_retrospective_marker.py              # FR-005
│   ├── test_contract_synthesis.py                # FR-008 / FR-006 wiring
│   └── test_loader_facade.py                     # FR-002 / FR-003 precedence + shadow rules
├── integration/
│   ├── test_mission_run_command.py               # FR-001, FR-013 (json shape), FR-009 (ERP)
│   └── test_custom_mission_runtime_walk.py       # FR-006, FR-007, FR-009 (decision_required + composition + paired invocation)
├── architectural/
│   └── test_shared_package_boundary.py           # already passing; this plan keeps it green (C-002)
├── fixtures/missions/
│   └── erp-integration/mission.yaml              # NEW reference fixture (FR-009)
└── specify_cli/next/test_runtime_bridge_composition.py  # extend: assert built-in dispatch unchanged when custom missions register

docs/
└── reference/missions.md   # extend: author guide + closed error code table (NFR-002)
```

## Phase 0 — Outline & Research

See [research.md](./research.md). Key resolved decisions:

1. **R-001 — Retrospective marker spelling.** Lock to `id == "retrospective"` on the final declared step. No `retrospective: true` flag, no `kind: retrospective`. Rationale: minimum-invasive; uses existing `PromptStep.id` field; trivial to validate; no schema change. Alternatives considered: dedicated `retrospective` field, separate `audit_steps` re-purposing. Both rejected for being heavier and inviting silent drift.
2. **R-002 — Shadow-of-built-in policy (resolves FR-011).** REJECT shadowing any of the four built-in mission keys (`software-dev`, `research`, `documentation`, `plan`) with a stable `MISSION_KEY_RESERVED` error. Non-built-in shadowing (project_override over project_legacy, user_global, packs) **warns** with `MISSION_KEY_SHADOWED` and uses the higher-precedence layer. Rationale: prevents accidentally breaking software-dev; preserves the existing override semantics for everything else.
3. **R-003 — Profile resolution surface.** Add `agent_profile: str | None = None` to `PromptStep` with Pydantic field alias `agent-profile`. The composition dispatcher reads it and passes it as `profile_hint` into `StepContractExecutionContext`. `_ACTION_PROFILE_DEFAULTS` is **not** extended.
4. **R-004 — Custom mission step contracts.** Synthesize `MissionStepContract` records from the loaded `MissionTemplate` at load time. Each composed step `s` produces a contract `mission=<mission-key>, action=<s.id>` bound to the loaded YAML's contract steps (a synthetic single-step contract). Allow YAML to optionally point to an existing contract via `contract_ref: <id>` for advanced authors; default is auto-synthesis. The repository remains the system of record at runtime; the synthesizer registers in-process for the lifetime of the run.
5. **R-005 — Composition gate widening.** `_COMPOSED_ACTIONS_BY_MISSION` becomes a fallback table for built-ins. The new gate is: for any mission whose loaded runtime template has `agent_profile` populated on the just-completed step, dispatch via composition. Built-in dispatch path is unchanged (their templates still keep the legacy DAG path because they don't carry `agent_profile`). This gives custom missions composition without altering built-ins.
6. **R-006 — Decision-required step shape.** Custom mission YAML uses the existing `requires_inputs: [<key>]` field on a step to mark it as a decision_required gate. No new field. The engine planner already routes such steps through `decision_required`.
7. **R-007 — Mission-pack discovery.** No new code; mission packs already feed the `project_config` tier in `_build_tiers`. Tests cover that path.
8. **R-008 — `--json` envelope.** Validation errors emit `{"result": "error", "error_code": "<CODE>", "message": "<text>", "details": {...}}` on `--json`; the human channel uses `rich.panel.Panel` with the same fields. CLI exit code = 2 for any validation error; 0 on success; 1 on infrastructure failure.

## Phase 1 — Design & Contracts

See:
- [data-model.md](./data-model.md) — entities, fields, validation rules, invariants.
- [contracts/mission-run-cli.md](./contracts/mission-run-cli.md) — CLI command shape + JSON envelope.
- [contracts/validation-errors.md](./contracts/validation-errors.md) — closed enum of error codes.
- [quickstart.md](./quickstart.md) — operator-facing how-to.

### Integration Points

| Surface | Integration |
| --- | --- |
| `src/specify_cli/next/_internal_runtime/discovery.py` | Add `RESERVED_BUILTIN_KEYS = frozenset({"software-dev", "research", "documentation", "plan"})`; add `validate_no_reserved_shadow(result: DiscoveryResult)`; keep `_build_tiers` unchanged. |
| `src/specify_cli/next/_internal_runtime/schema.py` | Add `agent_profile: str \| None = None` to `PromptStep` with alias `agent-profile`; add `contract_ref: str \| None = None` (forward-compatible). |
| `src/specify_cli/mission_loader/validator.py` (NEW) | Composes existing discovery + `load_mission_template` + structural validator; returns `ValidationReport(template=..., errors=[...], warnings=[...])`. |
| `src/specify_cli/mission_loader/contract_synthesis.py` (NEW) | `synthesize_contracts(template) -> list[MissionStepContract]`; result registered into a per-process `MissionStepContractRepository` shadow at run start. |
| `src/specify_cli/mission_step_contracts/executor.py` | `_resolve_profile_hint` already prefers `context.profile_hint`; the calling site in `runtime_bridge._dispatch_via_composition` learns to read the active step's `agent_profile` from the frozen template and pass it through. No change to `_ACTION_PROFILE_DEFAULTS`. |
| `src/specify_cli/next/runtime_bridge.py` | (a) `_should_dispatch_via_composition` widens to include any step whose template entry has `agent_profile`; (b) `_dispatch_via_composition` reads the step's `agent_profile` and forwards as `profile_hint`. |
| `src/specify_cli/cli/commands/mission_type.py` | Register `@app.command("run")` with args `mission_key: str` and option `--mission <slug>`, `--json/--no-json`. The handler delegates to `mission_loader.command.run(...)`. |
| `docs/reference/missions.md` | Add author guide (custom mission YAML shape, retrospective marker rule, profile rules) + the closed error-code table. |
| Tracker `spec_kitty_tracker` | No tracker changes; events keep flowing through the existing snapshot. |

### Data flow

1. Operator runs `spec-kitty mission run erp-integration --mission erp-q3-rollout`.
2. `mission_type.run_cmd` resolves project root → builds `DiscoveryContext` → calls `mission_loader.command.run`.
3. `mission_loader.command.run` calls `discovery.discover_missions_with_warnings`, then `loader.load_mission_template(mission_key, ctx)`.
4. `validator.validate_custom_mission(template)` runs:
    - schema check (`MissionTemplate.model_validate`)
    - reserved-key check
    - retrospective-marker check
    - per-step profile / contract-binding check
    - returns `ValidationReport`.
5. On error, render JSON or panel and exit 2.
6. On success, `contract_synthesis.synthesize_contracts(template)` registers in-process; the run starts via the existing `runtime_bridge.get_or_start_run` (extended to accept a custom mission template path).
7. `decide_next_via_runtime` advances. For composed steps, the dispatcher picks up `agent_profile` from the frozen template and forwards it. For decision_required steps, the existing planner takes over.

### Requirements traceability

| FR / NFR / C | Verified by |
| --- | --- |
| FR-001 | `tests/integration/test_mission_run_command.py::test_run_command_starts_runtime_with_json_output` |
| FR-002 | `tests/unit/mission_loader/test_loader_facade.py::test_precedence_explicit_over_env`, `..._project_override_over_legacy`, etc. |
| FR-003 | `..._loads_from_kittify_missions`, `..._loads_from_overrides`, `..._loads_from_mission_pack_manifest` |
| FR-004 | `tests/unit/mission_loader/test_validator_errors.py` (one test per closed error code in `contracts/validation-errors.md`) |
| FR-005 | `test_retrospective_marker.py::test_missing_marker_rejected_with_stable_code` |
| FR-006 | `tests/integration/test_custom_mission_runtime_walk.py::test_composed_step_pairs_invocation_records` |
| FR-007 | `..._decision_required_step_pauses_runtime_and_resumes` |
| FR-008 | `test_validator_errors.py::test_step_without_profile_or_contract_rejected`; `test_contract_synthesis.py::test_synthesizes_one_contract_per_step` |
| FR-009 | ERP fixture suite + `test_custom_mission_runtime_walk.py::test_erp_full_walk` |
| FR-010 | `tests/specify_cli/next/test_runtime_bridge_composition.py` (existing 21 tests stay green) |
| FR-011 | `test_loader_facade.py::test_reserved_key_shadow_rejected_with_MISSION_KEY_RESERVED` (resolves via R-002) |
| FR-012 | `test_custom_mission_runtime_walk.py::test_next_advances_custom_mission_after_run_started` |
| FR-013 | `test_mission_run_command.py::test_validation_error_json_envelope_shape_locked` |
| NFR-001 | `tests/perf/test_loader_perf.py::test_load_p95_under_250ms` (uses `pytest --benchmark` or wall-clock assertion) |
| NFR-002 | `test_validator_errors.py` parametrized over the closed error-code enum |
| NFR-003 | `pytest --cov` with fail-under 90 on new modules; CI guard added to `.github/workflows/ci-quality.yml` if not already enforced for the new package |
| NFR-004 | `test_custom_mission_runtime_walk.py::test_erp_full_walk_completes_under_10s` |
| NFR-005 | `mypy --strict src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime` in CI |
| C-001 | No SaaS surfaces touched; reviewer asserts in mission-review |
| C-002 | `tests/architectural/test_shared_package_boundary.py` (already covers this) |
| C-003 | `test_runtime_bridge_composition.py::test_composition_success_skips_legacy_dispatch` (parametrized; existing) |
| C-004 | New code calls `ProfileInvocationExecutor` only via `StepContractExecutor`; reviewer asserts grep |
| C-005 | Validator accepts retrospective marker structurally only — no execution wiring |
| C-006 | New code routes; does not generate. Reviewer asserts |
| C-007 | One new subcommand on existing `mission` group; no new groups |
| C-008 | All tests use `tmp_path` filesystem fixtures |

## Risks (premortem)

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Widening the composition gate breaks built-in dispatch path. | Med | High | Gate is conditional on `agent_profile` being set; built-in templates do not set it; existing 21-case parametrized test in `test_runtime_bridge_composition.py` stays green and is *the* regression trap. |
| Custom mission contract synthesis races with the on-disk repository. | Low | Med | Synthesized contracts live in a per-process registry that takes precedence within the run; on-disk repository unchanged. Lifetime ends when the run terminates. |
| `requires_inputs` semantics already used by built-ins; reusing it for decision_required gates in custom missions could collide. | Low | Med | Built-in templates already use it the same way; the engine treats it identically. Tests assert behavior parity. |
| Operators name a custom mission `software-dev` and discover surprising behavior. | Med | High | R-002 rejects with `MISSION_KEY_RESERVED` at load time. Test enforces. |
| `agent_profile` alias parsing: YAML uses kebab, Python uses snake. | Med | Low | Pydantic field alias `agent-profile` accepts both at parse; internal field is `agent_profile`. Documented in `docs/reference/missions.md`. |
| Validator p95 > 250ms when many packs declared. | Low | Low | Fixture sized at typical project; perf test asserts threshold; if violated, batch parsing optimization is a follow-on. |

## Constitution Gate

This plan does not modify any constitutional artifact. **PASS.**

## Open Items

None. All planning open items resolved (R-001 … R-008). Mission ready for `/spec-kitty.tasks`.

---

**Branch contract (2nd statement)**: current=`main`, planning_base=`main`, merge_target=`main`, branch_matches_target=true. Next command: `/spec-kitty.tasks`.
