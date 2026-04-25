# Mission Review Report — `local-custom-mission-loader-01KQ2VNJ`

**Mission slug:** `local-custom-mission-loader-01KQ2VNJ`
**Mission number (display-only):** 99
**Squash-merge commit:** `e0c065ca`
**Baseline used for diff:** `cedb77ff` (the #798 preflight fix)
**Reviewer:** Mission Review (post-merge, READ-ONLY)
**Date:** 2026-04-25

---

## Step 1 — Orient (event log + WP status)

All 8 work packages reached `approved` and were merged via lane-a:

| WP | First implementer | Final reviewer | Cycles | Final lane |
| --- | --- | --- | --- | --- |
| WP01 | claude (initial) | claude:opus:reviewer-renata | 2× into in_progress (one short pre-review touch-up) | approved |
| WP02 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP03 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP04 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP05 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP06 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP07 | claude:sonnet:implementer-ivan | claude:opus:reviewer-renata | 1 | approved |
| WP08 | claude:sonnet:curator-carla | claude:opus:reviewer-renata | 1 | approved |

No `rejected` event in `kitty-specs/local-custom-mission-loader-01KQ2VNJ/status.events.jsonl`; no arbiter overrides. The orchestrator's recollection of "all 8 WPs passed cleanly on first try" matches the event log.

## Step 2 — Spec absorbed

13 FRs (FR-001 … FR-013), 5 NFRs (NFR-001 … NFR-005), 8 constraints (C-001 … C-008). Locked decisions of note:

* **R-001** retrospective marker spelled `id == "retrospective"` on the *last* step — locked.
* **R-002** non-builtin tier shadowing a built-in key is rejected with `MISSION_KEY_RESERVED`; non-builtin keys shadowed across non-builtin tiers warn with `MISSION_KEY_SHADOWED`.
* **R-003** profile resolution: `PromptStep.agent_profile` (alias `agent-profile`); `_ACTION_PROFILE_DEFAULTS` MUST NOT be expanded.
* **R-004** custom-mission contracts are *synthesized* in-memory from the loaded template; the on-disk repository is unchanged.
* **R-005** composition-gate widens for any step whose template entry sets `agent_profile`; built-in dispatch path stays byte-identical.
* **R-008** validation errors emit `{"result", "error_code", "message", "details", "warnings"}`; exit codes 0 / 1 / 2.

## Step 3 — Git timeline

```
$ git log cedb77ff..HEAD --oneline | wc -l
56
$ git diff cedb77ff..HEAD --stat | tail -1
56 files changed, 8513 insertions(+), 13 deletions(-)
```

File ownership map (paths are repo-relative; full paths on disk under `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/`):

| Surface | Owner WP | Status |
| --- | --- | --- |
| `src/specify_cli/next/_internal_runtime/schema.py` (PromptStep gains `agent_profile`, `contract_ref`) | WP01 | merged |
| `src/specify_cli/mission_loader/errors.py` (closed enum) | WP02 | merged |
| `src/specify_cli/mission_loader/validator.py` | WP02 | merged |
| `src/specify_cli/mission_loader/retrospective.py` | WP02 | merged |
| `src/specify_cli/mission_loader/contract_synthesis.py` | WP03 | merged |
| `src/specify_cli/mission_loader/registry.py` | WP03 | merged |
| `src/specify_cli/next/runtime_bridge.py` (`_should_dispatch_via_composition` widening + `_resolve_step_agent_profile`) | WP04 | merged |
| `src/specify_cli/mission_loader/command.py` + `cli/commands/mission_type.py` (`run` subcommand) | WP05 | merged |
| `tests/fixtures/missions/erp-integration/mission.yaml` + integration tests | WP06 | merged |
| `.github/workflows/ci-quality.yml` `mission-loader-coverage` job (lines 908-944) | WP07 | merged |
| `docs/reference/missions.md` | WP08 | merged |
| `src/specify_cli/next/_internal_runtime/discovery.py` (`RESERVED_BUILTIN_KEYS`, `is_reserved_key`, `discover_missions_with_warnings`) | WP02 + carry-overs | merged |
| `src/specify_cli/mission_step_contracts/executor.py` (table-comment delta only; 4-line note) | WP04 | merged |

## Step 4 — WP review history confirmed clean

No `tasks/WP*/review-cycle-N.md` files were generated for this mission (we checked `kitty-specs/local-custom-mission-loader-01KQ2VNJ/tasks/` — only the WP*-*.md task definitions and `README.md` exist). Each WP went `for_review` → `in_progress`/`in_review` → `approved` exactly once. No rejections.

## Step 5 — FR / NFR / Constraint trace

Status legend: ADEQUATE = covered with live test asserting the live code path; PARTIAL = covered but with a caveat below; MISSING = no coverage; FALSE_POSITIVE = test passes only because the live code path is mocked or the implementation is dead.

| ID | Spec section | WP owner | Test file / function | Live code path | Status |
| --- | --- | --- | --- | --- | --- |
| FR-001 | spec.md §FR / contracts/mission-run-cli.md | WP05 | `tests/integration/test_mission_run_command.py::test_run_command_starts_runtime_with_json_output` | `mission_loader/command.py::run_custom_mission` + Typer `mission_type.py::run_cmd` | **PARTIAL** — see F-1: happy-path test mocks `runtime_bridge.get_or_start_run` so the runtime never starts and the contract-resolution gap (F-1) is invisible at this layer. |
| FR-002 | spec.md §FR | WP02 | `tests/unit/mission_loader/test_loader_facade.py::test_*_precedence_*` | `discovery.py::_build_tiers` + `discover_missions_with_warnings` | ADEQUATE |
| FR-003 | spec.md §FR | WP02 | `test_loader_facade.py::test_loads_from_overrides`, `..._loads_from_mission_pack_manifest` | `discovery.py::_scan_root` + `_collect_from_manifest` | ADEQUATE |
| FR-004 | contracts/validation-errors.md | WP02 | `tests/unit/mission_loader/test_validator_errors.py` (parametrized) | `mission_loader/validator.py` | **PARTIAL** — every code is covered EXCEPT `MISSION_CONTRACT_REF_UNRESOLVED` and `MISSION_KEY_AMBIGUOUS`, which the WP02 implementer deferred to "WP05 run-start"; WP05 never raised them. See F-2. |
| FR-005 | spec.md §FR | WP02 | `tests/unit/mission_loader/test_retrospective_marker.py::test_marker_*` + `test_validator_errors.py::test_missing_retrospective_*` | `mission_loader/retrospective.py` + validator step 4 | ADEQUATE |
| FR-006 | spec.md §FR | WP04 | `tests/integration/test_custom_mission_runtime_walk.py::test_paired_invocation_records_carry_contract_action` | `runtime_bridge.py::_dispatch_via_composition` | **FALSE_POSITIVE for production** — test mocks `StepContractExecutor.execute` so the missing registry-shadow lookup (F-1) does not surface. The `test_erp_full_walk` test drives the engine directly and never reaches the bridge. |
| FR-007 | spec.md §FR | WP04 | `test_custom_mission_runtime_walk.py::test_erp_full_walk` (decision_required handling) | engine planner | ADEQUATE |
| FR-008 | spec.md §FR | WP04 | `test_validator_errors.py::test_step_without_binding_*` + `test_contract_synthesis.py::test_synthesizes_one_contract_per_step` | validator + `contract_synthesis.synthesize_contracts` | ADEQUATE for *synthesis*; PARTIAL for *runtime use* — the synthesized contract is never consulted by `StepContractExecutor` (F-1). |
| FR-009 | spec.md §FR | WP06 | `test_erp_full_walk` + `test_run_custom_mission_starts_runtime_for_erp_fixture` | engine + loader | ADEQUATE for engine-only walk; **PARTIAL** for the bridge dispatch path because the run_custom_mission test stubs `get_or_start_run`. |
| FR-010 | spec.md §FR | WP04 | `tests/specify_cli/next/test_runtime_bridge_composition.py` (37 cases) + `test_custom_mission_runtime_walk.py::test_software_dev_specify_dispatch_unchanged` | `runtime_bridge.py::_should_dispatch_via_composition` built-in fast path | ADEQUATE (37/37 pass; built-in dispatch byte-identical) |
| FR-011 | spec.md §FR | WP02 | `test_loader_facade.py::test_reserved_key_shadow_rejected_*` + `test_mission_run_command.py::test_reserved_key_shadow_returns_error_envelope` | validator reserved-key check | ADEQUATE |
| FR-012 | spec.md §FR | WP04 | `test_custom_mission_runtime_walk.py::test_paired_invocation_records_carry_contract_action` | `decide_next_via_runtime` → `_dispatch_via_composition` | **FALSE_POSITIVE for production** — same root cause as FR-006. |
| FR-013 | spec.md §FR | WP05 | `test_mission_run_command.py::test_*_returns_error_envelope` | `command.py::_validation_error_result` | ADEQUATE |
| NFR-001 | spec.md §NFR (perf p95 < 250ms) | WP07 | `tests/perf/test_loader_perf.py::test_load_p95_under_250ms` | validator full pipeline | ADEQUATE — re-run during this audit: PASSED in 3.22 s. |
| NFR-002 | spec.md §NFR (closed enum, stable wire spelling) | WP02 | `test_validator_errors.py::test_*_code_string_is_stable` (incl. the unreached codes) | `mission_loader/errors.py::LoaderErrorCode` | **PARTIAL** — codes that have no production raiser have only string-stability tests. See F-2. |
| NFR-003 | spec.md §NFR (≥ 90% coverage on new modules) | WP07 | `.github/workflows/ci-quality.yml` job `mission-loader-coverage` lines 908-944 | CI gate | ADEQUATE — re-run locally: 96.62% total, all 6 source files at 100% except `validator.py` 90% (defensive paths). Floor met. |
| NFR-004 | spec.md §NFR (ERP suite < 10s) | WP07 | `test_custom_mission_runtime_walk.py` (whole module) + WP06 fixture timing | n/a | ADEQUATE — module ran in ~1.66 s during this audit. |
| NFR-005 | spec.md §NFR (mypy --strict) | WP07 | CI lint job | n/a | **PARTIAL** — `mypy --strict` over `src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py src/specify_cli/next/_internal_runtime/schema.py` reports 8 errors, all in transitive imports (`jsonschema`, `yaml`) or the existing pre-mission `schema.py:179` (`Returning Any`). None of the new mission_loader modules introduce mypy errors. The transitive errors are pre-existing and not regressions of this mission, but the spec's wording ("Zero `mypy --strict` errors on new / changed modules") is technically met for new code only. |
| C-001 | No SaaS / install surface | n/a | reviewer grep | n/a | ADEQUATE |
| C-002 | No `spec_kitty_runtime` imports under src/ | n/a | `tests/architectural/test_shared_package_boundary.py` | n/a | ADEQUATE — re-run: 8 tests passed. |
| C-003 | No legacy DAG fall-through | WP04 | `test_runtime_bridge_composition.py` 37-case parametrization | bridge gate | ADEQUATE |
| C-004 | Invocation JSONL only via ProfileInvocationExecutor | WP04/WP05 | grep + executor structure | bridge dispatcher | ADEQUATE — `_dispatch_via_composition` only invokes `StepContractExecutor.execute`. |
| C-005 | Retrospective is structural-only | WP02/WP03 | `test_retrospective_marker.py` | retrospective.py + validator + synthesis skip | ADEQUATE |
| C-006 | CLI routes; never generates | n/a | reviewer audit of `command.py` and bridge | n/a | ADEQUATE |
| C-007 | One new subcommand on existing `mission` group | WP05 | `mission_type.py::run_cmd` | n/a | ADEQUATE |
| C-008 | Tests use `tmp_path` | all | every WP06+ test fixture | n/a | ADEQUATE |

## Step 6 — Drift and gap analysis (anti-pattern hunt)

Findings detailed below. Anti-pattern numbering follows the mission-review skill's checklist.

### F-1 — CRITICAL: Synthesized contract registry has no production reader

**Anti-pattern 2** — *dead code: a new module with no live caller in the production code path.*

**File / line evidence:**
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/command.py` lines 88-94: `command.run_custom_mission` registers synthesized contracts via `registry.register(synthesize_contracts(report.template))`.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/registry.py` defines `lookup_contract` (line 132) and `registered_runtime_contracts` (line 107) as the façade meant to overlay the on-disk repository.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_step_contracts/executor.py` line 144: `selected_contract = contract or self._contracts.get_by_action(context.mission, context.action)` — calls the on-disk `MissionStepContractRepository` directly, never `lookup_contract` or the in-memory `RuntimeContractRegistry`.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/next/runtime_bridge.py` line 503: `result = StepContractExecutor(repo_root=repo_root).execute(context)` — instantiates a fresh executor with no override; no `contract=` parameter passed.

**Production impact:** when an operator runs `spec-kitty mission run erp-integration --mission erp-q3-rollout`, then `spec-kitty next ...`, the runtime advances onto a composed step (e.g., `query-erp` with `agent_profile: researcher-robbie`). The bridge's `_should_dispatch_via_composition` returns True (R-005 widening), `_dispatch_via_composition` instantiates a `StepContractExecutor` against `~/repo/.kittify/doctrine/mission_step_contracts/`, and `executor.execute(context)` calls `self._contracts.get_by_action("erp-integration", "query-erp")`. The on-disk repository has no such contract — none was ever written there (the contracts only live in the in-memory `RuntimeContractRegistry` singleton). The executor raises `StepContractExecutionError("No step contract found for mission/action erp-integration/query-erp")`. The bridge catches it and surfaces `composition failed for erp-integration/query-erp: ...` as a `Decision.guard_failures`, blocking the run. Custom missions cannot actually advance.

**Why tests didn't catch it:**
- `test_paired_invocation_records_carry_contract_action` (FR-006/FR-012) patches `StepContractExecutor.execute` directly, so the `get_by_action` lookup is bypassed.
- `test_run_command_starts_runtime_with_json_output` (FR-001) patches `runtime_bridge.get_or_start_run` so no run is actually started.
- `test_erp_full_walk` (FR-007/FR-009) drives `engine.next_step` directly — it walks the engine planner only, never the bridge `_dispatch_via_composition`. The engine planner does not call the executor at all.
- No integration test exercises the live `decide_next_via_runtime` path against a custom mission.

**WP attribution:** the contract-resolution wiring sits at the WP04/WP05 boundary. WP03 built the registry (correctly), WP04 widened the gate (correctly), WP05 registered into the singleton (correctly). The missing piece is a one-line change in `_dispatch_via_composition` — it must look up the synthesized contract via `lookup_contract(...)` (or build a per-call `MissionStepContractRepository` whose `get_by_action` is augmented) and pass it as `executor.execute(context, contract=...)`. None of WP04/WP05 implementers added that call; none of the reviewers caught the dead code; the FR-006 / FR-012 test surface mocks `execute` and so cannot distinguish "empty-registry → fail" from "registry-resolves → pass".

**Severity: HIGH.** v1 of the loader is shipped with a fully-validated, fully-discovered, fully-synthesized custom-mission contract that the runtime cannot find at advance-time. Built-in dispatch is unaffected (FR-010 is fine — `_ACTION_PROFILE_DEFAULTS` and the on-disk software-dev contracts both still resolve), so this is invisible to existing software-dev users; but FR-001/FR-006/FR-009/FR-012 ("Operators can run a project-authored custom mission end-to-end with the same observable behavior as a built-in mission") is not actually achievable with merged code.

### F-2 — MEDIUM: `MISSION_CONTRACT_REF_UNRESOLVED` and `MISSION_KEY_AMBIGUOUS` are dangling enum codes

**Anti-pattern 3** — *FR mapped to WP frontmatter but no live code raises it.*

**Evidence:**
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/errors.py` line 32: `MISSION_KEY_AMBIGUOUS = "MISSION_KEY_AMBIGUOUS"`.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/errors.py` line 37: `MISSION_CONTRACT_REF_UNRESOLVED = "MISSION_CONTRACT_REF_UNRESOLVED"`.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/validator.py` lines 11-15 (docstring): "The `MISSION_CONTRACT_REF_UNRESOLVED` code is declared in `LoaderErrorCode` but is intentionally NOT raised here -- that cross-module check happens at run-start in WP05".
- `tests/unit/mission_loader/test_validator_errors.py` lines 277-304: the tests for these two codes only assert string stability; neither code has a `validate_custom_mission(...)` call that produces it.
- `grep -rn 'MISSION_CONTRACT_REF_UNRESOLVED\|MISSION_KEY_AMBIGUOUS' src/` confirms only the enum declaration in `errors.py` and the explanatory docstring in `validator.py`. No production raiser, anywhere.

**Production impact:** Operators who set `contract_ref: foo` on a step pointing to a non-existent contract id will not see `MISSION_CONTRACT_REF_UNRESOLVED`. Behavior at runtime depends on whether the executor finds the referenced contract: if unresolved on-disk, the path collapses into the F-1 surface (`StepContractExecutionError("No step contract found ...")`), losing the structured operator-fixable code. Behavior contract for tooling (NFR-002: "100% of FR-004 cases covered by named error codes") is technically violated for the `contract_ref` case.

`MISSION_KEY_AMBIGUOUS` is documented as "reserved for future use" so it's a forward-compat reservation; lower severity, but the enum remains an unkept promise.

**Severity: MEDIUM.** Closing this requires either (a) actually raising `MISSION_CONTRACT_REF_UNRESOLVED` from `command.run_custom_mission` after registering synthesized contracts (resolve `contract_ref` against the on-disk repository or the synthesized set; emit the structured error if the id has no record), and (b) either implementing `MISSION_KEY_AMBIGUOUS` as an actual rejection path or downgrading the contract-doc to reflect that discovery's first-tier-wins is deterministic and "ambiguous" cannot occur.

### F-3 — LOW: `RuntimeContractRegistry` v1 lifetime is process-singleton with no clear

**Anti-pattern 6** — *silent state retention; no exit-of-block cleanup.*

**Evidence:**
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/command.py` lines 88-94: deliberately bypasses the `registered_runtime_contracts` `with` block: "v1 holds the shadow for the rest of the process; tests clear the registry directly between cases."
- `command.py` line 103: clears the registry only on the failure-to-start branch.
- Spec/plan §R-004 says the synthesizer "registers in-process for the lifetime of the run." The implementation registers for the lifetime of the *process* — a strict superset. No cleanup happens at run-end.

**Production impact:** if a single Python process invokes `run_custom_mission` for two different mission keys, the second run will see the first run's contracts shadowing its own (only when ids collide; given `id = f"custom:{mission_key}:{step.id}"`, collisions only happen for the same mission key). For the tested 1-shot CLI invocations this is invisible. Mostly cosmetic; flagged for future work that may run the loader in a long-lived process.

**Severity: LOW.**

### F-4 — LOW: `_build_discovery_context` duplicated between bridge and command

**Anti-pattern 8** — *ownership drift at shared file boundaries* (mild).

**Evidence:**
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/command.py` lines 138-152.
- `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/next/runtime_bridge.py` lines 782-789.

The implementer left an explicit comment ("module-private; we duplicate the construction here so this module does not depend on a private surface"). Acceptable per WP05 reviewer's accepted note. Future drift risk is real but very small (5 lines). Keeping a TODO to either de-duplicate or commit to the boundary.

**Severity: LOW.**

### F-5 — LOW: `validator._try_recover_from_warning` and `_classify_load_failure` have a final pragmatic-`pragma: no cover` arm

**Anti-pattern 6** — *silent empty-result return guarded by `# pragma: no cover`*.

**Evidence:** `/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_loader/validator.py` lines 415-423 and 181-196, 401-411 — all `except Exception: # pragma: no cover` blocks that fall through into `MISSION_YAML_MALFORMED`. The defensive shape is fine and well-bounded; flagged only because exhaustive coverage is one of the spec NFRs and the surface is intentionally untested. The 90% gate currently exempts these arms via `# pragma: no cover` rather than via real test exercise. Not a bug; a documentation point so future reviewers don't think the gate is being lowered.

**Severity: LOW.**

### Anti-patterns that did NOT find a regression

* **AP-1 synthetic-fixture-pass:** `test_erp_full_walk` is real-engine-driven (no `MagicMock`); FR-007 (decision_required) is exercised on the live planner. PASS.
* **AP-4 dispatcher whitelist regression:** `_should_dispatch_via_composition` is exhaustively parametrized in `tests/specify_cli/next/test_runtime_bridge_composition.py` (37 cases) and passes; built-in dispatch is byte-identical. PASS.
* **AP-5 TOCTOU:** N/A.
* **AP-7 locked-decision violation:**
  * `_ACTION_PROFILE_DEFAULTS` was *not* expanded (`/Users/robert/spec-kitty-dev/spec-kitty-20260425-192136-VUIM7c/spec-kitty/src/specify_cli/mission_step_contracts/executor.py` lines 39-45 still hold the original 5 entries — FR-008 honored).
  * Built-in regression check: 37/37 cases of `test_runtime_bridge_composition.py` pass — FR-010 honored.
  * `test_shared_package_boundary.py` — 8/8 pass — C-002 honored.
  * Invocation JSONL is only written by `ProfileInvocationExecutor.invoke` inside `StepContractExecutor.execute` — C-004 honored.

## Step 7 — Risk identification (boundary conditions)

| Risk | Where | Severity |
| --- | --- | --- |
| Synthesized contract not consulted at runtime (F-1) | `_dispatch_via_composition` line 503 | HIGH |
| `MISSION_CONTRACT_REF_UNRESOLVED` and `MISSION_KEY_AMBIGUOUS` declared but unraised (F-2) | `errors.py` lines 32, 37 | MEDIUM |
| Process-lifetime registry without explicit lifetime (F-3) | `command.py` line 88 | LOW |
| Duplicated `_build_discovery_context` (F-4) | `command.py` line 138 / `runtime_bridge.py` line 782 | LOW |
| `_resolve_step_agent_profile` swallows arbitrary `Exception` and returns None (could mask bugs) | `runtime_bridge.py` line 353 | LOW — defensive, but logs nothing. Consider `logger.debug(..., exc_info=True)` so a corrupted frozen template surfaces in operator logs. |
| `validate_custom_mission` returns early on first error from a list — single error per envelope; spec example shows single error which is consistent. Operators with multiple problems must iterate. Documented but worth surfacing in `quickstart.md`. | `validator.py` line 198 / `command.py::_validation_error_result` line 157 | LOW |

## Step 8 — Security review

* **No subprocess calls** in the new `mission_loader/` package.
* **File path operations** all use `Path` against operator-supplied directory roots (`tmp_path` in tests, `repo_root / .kittify / missions / <key>` in production). The reserved-key rejection happens *before* file content is read, but the discovery scan itself does open files in any tier — including the user-home tier (`~/.kittify/missions/`). A malicious user-global mission YAML cannot escape Pydantic schema validation, but it could trigger the full `discover_missions_with_warnings` parse on start. This is the same surface as the pre-existing built-in discovery; no new attack vector introduced.
* **YAML loading uses `yaml.safe_load`** in both `discovery._scan_root` and `schema.load_mission_template_file` — safe.
* **Authentication:** N/A — no SaaS, no install, no network.
* **Reserved-key check is earlier than parse** for operator clarity, but `discovery.discover_missions_with_warnings` does *load* every mission file (including ones that would later be rejected as reserved). Acceptable for v1 since file-load is bounded.

No security findings.

## Step 9 — Final verdict

**Verdict: PASS WITH NOTES.** All 8 WPs reached `approved`, the architectural boundary stays green, every closed-set FR gate-test is in place, and the per-package coverage gate runs at 96%+ locally. **However, F-1 is a real production gap** (custom missions will not advance through `spec-kitty next` because the executor never reads from the synthesized-contract registry), and the FR-006/FR-012 tests as currently written cannot detect it. F-2 leaves two enum codes unraised in production. The mission is releasable for the validator + CLI surface (FR-001, FR-002, FR-003, FR-004 partial, FR-005, FR-008 synthesis, FR-010, FR-011, FR-013) but needs a follow-up patch for the runtime-execution path before any operator can practically use the loader for the FR-009 ERP-style end-to-end walk.

### Findings summary (5-item top-of-list for the orchestrator)

1. **F-1 (HIGH) — Wire `RuntimeContractRegistry` into `_dispatch_via_composition`.** Either (a) modify `runtime_bridge._dispatch_via_composition` (line 503) to resolve the contract via `mission_loader.lookup_contract(f"custom:{mission}:{action}", repository=executor._contracts)` and pass it as `executor.execute(context, contract=resolved)`, or (b) augment `StepContractExecutor.__init__` to consult `get_runtime_contract_registry()` *before* the on-disk repository in `get_by_action`. Add a regression test that drives `decide_next_via_runtime` against the ERP fixture without mocking the executor.
2. **F-2 (MEDIUM) — Either raise `MISSION_CONTRACT_REF_UNRESOLVED` from `run_custom_mission` after synthesis, or remove it from the closed enum.** Same for `MISSION_KEY_AMBIGUOUS`. NFR-002 ("100% of FR-004 cases covered by named error codes") is technically violated for the `contract_ref` failure path.
3. **F-3 (LOW) — Document or fix the process-lifetime registry.** WP05 deliberately skipped `registered_runtime_contracts` `with` block; if the design intent is process-lifetime, the docstring in `command.py` is good enough — but the spec says "registers in-process for the lifetime of the run". Reconcile.
4. **F-5 (LOW) — Either drop the `# pragma: no cover` arms in `validator._classify_load_failure` (there are 3) or reflect the intentional defensive coverage gap in NFR-003 prose.** Coverage gate currently passes only because of these pragmas.
5. **NFR-005 (PARTIAL) — Investigate the `mypy --strict` errors on transitive imports.** Eight errors in `jsonschema` / `yaml` / pre-existing `schema.py:179` are pre-mission and not regressions, but the spec's "Zero `mypy --strict` errors on new / changed modules" wording could be read more strictly. Consider installing `types-PyYAML` and `types-jsonschema` in the lint job.

### Test-run verifications captured during this audit

| Suite | Result | Wall-clock |
| --- | --- | --- |
| `tests/specify_cli/next/test_runtime_bridge_composition.py` | 37/37 PASS | 3.82 s |
| `tests/architectural/test_shared_package_boundary.py` | 8/8 PASS | (combined) |
| `tests/perf/test_loader_perf.py` | 2/2 PASS | 3.22 s combined with boundary |
| `tests/unit/mission_loader/ tests/integration/test_mission_run_command.py tests/integration/test_custom_mission_runtime_walk.py tests/next/test_composition_gate_widening.py tests/next/test_prompt_step_schema_extensions.py` | 84/84 PASS | 1.66 s |
| `pytest --cov=src/specify_cli/mission_loader --cov-fail-under=90` over loader tests + integration | 61/61 PASS, 96.62% coverage | 0.71 s |
| `mypy --strict` over `src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py src/specify_cli/next/_internal_runtime/schema.py` | 8 errors in transitive imports / pre-existing schema.py | n/a |

End of report.
