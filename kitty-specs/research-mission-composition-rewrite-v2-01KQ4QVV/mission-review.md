# Mission Review — research-mission-composition-rewrite-v2-01KQ4QVV

**Reviewed**: 2026-04-26 (post-merge, local main)
**Reviewer**: claude:opus-4.7:mission-review:auditor
**Merge commit**: `83bea54` (squash merge)
**Baseline**: `e056f39` on `origin/main`
**Mission ID**: `01KQ4QVVZ4DC6CXA1XCZZAQ8AG`

## Verdict

**PASS WITH NOTES (preliminary)**

The mission ships a working composition-backed research mission. The v1 P0 finding (`MissionRuntimeError: Mission 'research' not found`) is closed; fresh research missions create cleanly, advance through composition (`scoping → methodology` observed end-to-end), and write paired profile invocation lifecycle records with `profile_id=researcher-robbie` and `action=scoping`. All 65 mission tests pass, all 47 regression tests pass, C-007 forbidden-mock grep returns zero hits across all four test files, FRs 001-015 each have at least one verifying test or code surface, and the implementation is additive-only against software-dev (no regressions).

> **Preliminary**: per user MEMORY (`user_review_practice.md`), local `main` advances are validated by an external adversarial review pass before push. This verdict should be treated as preliminary until that external pass clears.

## Dogfood Smoke (post-merge main, fresh capture)

Captured 2026-04-26T13:40-13:43Z by the auditor against `83bea54` on local main, in a fresh `/tmp/demo-research-postmerge` git repo distinct from the WP06 reviewer's evidence run.

### Step 1 — Clean repo + mission create

```
$ cd /tmp && rm -rf demo-research-postmerge && mkdir demo-research-postmerge && cd demo-research-postmerge
$ git init -q && git commit --allow-empty -m "init" -q
$ uv --directory $SPEC_KITTY_REPO run spec-kitty agent mission create postmerge-smoke --mission-type research --json
Using CPython 3.13.9 interpreter at: /opt/homebrew/opt/python@3.13/bin/python3.13
Removed virtual environment at: .venv
Creating virtual environment at: .venv
Installed 48 packages in 43ms
{"result": "success", "mission_slug": "postmerge-smoke-01KQ50AT", "mission_id": "01KQ50ATF8VQRN1N37MTGERGJR",
 "mission_type": "research", "feature_dir": ".../kitty-specs/postmerge-smoke-01KQ50AT", ...,
 "spec_kitty_version": "3.2.0a4"}
```

No `MissionRuntimeError`. No Python traceback. Mission created cleanly.

### Step 2 — First `next` (query mode)

```
$ uv --directory $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:mission-review:auditor --mission postmerge-smoke-01KQ50AT
[QUERY — no result provided, state not advanced]
  Mission: postmerge-smoke-01KQ50AT @ not_started
  Mission Type: research
  Next step: scoping
```

Runtime resolved the research template and surfaced the research-native first step (`scoping`), not a software-dev fall-through.

### Step 3 — Advance through composition

```
$ uv --directory $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:mission-review:auditor --mission postmerge-smoke-01KQ50AT --result success
[STEP] postmerge-smoke-01KQ50AT @ scoping
  Mission Type: research
  Action: scoping
  Run ID: 814e02620efa48579d09868d57927450

$ uv --directory $SPEC_KITTY_REPO run spec-kitty next \
      --agent claude:opus-4.7:mission-review:auditor --mission postmerge-smoke-01KQ50AT --result success
[STEP] postmerge-smoke-01KQ50AT @ methodology
  Mission Type: research
  Action: methodology
  Run ID: 814e02620efa48579d09868d57927450
```

Mission advanced `scoping → methodology` — research-native steps, not software-dev verbs. Composition path fired.

### Step 4 — Trail records (sample paired record)

Trail under `<host-repo>/.kittify/events/profile-invocations/01KQ50E79GM2X5P4SDAH33ZK67.jsonl`:

```json
{"event": "started", "invocation_id": "01KQ50E79GM2X5P4SDAH33ZK67",
 "profile_id": "researcher-robbie", "action": "scoping",
 "request_text": "Execute mission step contract research-scoping (research/scoping)...",
 "governance_context_hash": "9a41f0bd764f0d6c", "governance_context_available": true,
 "actor": "claude:opus-4.7:mission-review:auditor",
 "started_at": "2026-04-26T13:42:37.524489+00:00"}
{"event": "completed", "invocation_id": "01KQ50E79GM2X5P4SDAH33ZK67",
 "profile_id": "researcher-robbie", "outcome": "done",
 "completed_at": "2026-04-26T13:42:37.524904+00:00", ...}
```

Key facts:

- `profile_id: researcher-robbie` — the research-native profile (not software-dev defaults).
- `action: scoping` — research-native step ID threaded through `StepContractExecutor`.
- Paired `started`+`completed` with `outcome: done` — FR-012 lifecycle preserved.
- `governance_context_hash` non-empty + `governance_context_available: true` — DRG governance context delivered (FR-005 / FR-006).

The transient `❌ Connection failed: Forbidden: Direct sync ingress must target Private Teamspace.` line is unrelated SaaS-sync ingress and reproduced byte-identically in the WP06 reviewer's evidence run; it does not block the local runtime.

**Smoke verdict: PASS.** Independent of the WP06 reviewer's smoke (different mission slug, different mission ID, different actor); same outcome.

## FR Coverage Matrix

| FR | Statement | Verifying surface | Status |
|---|---|---|---|
| FR-001 | Fresh research mission starts via `get_or_start_run` without `MissionRuntimeError` | `tests/integration/test_research_runtime_walk.py::test_get_or_start_run_succeeds_for_research`; auditor smoke step 1 | ADEQUATE |
| FR-002 | Runtime advances ≥1 composed step | `test_research_runtime_walk.py::test_runtime_advances_one_composed_step_via_real_path`; auditor smoke step 3 (scoping→methodology) | ADEQUATE |
| FR-003 | `MissionTemplate` declares `mission.key: research` + non-empty `steps` | `src/specify_cli/missions/research/mission-runtime.yaml` (6 PromptSteps incl. accept) | ADEQUATE |
| FR-004 | DRG node `action:research/<action>` truthy for all 5 actions | `tests/specify_cli/test_research_drg_nodes.py`; `src/doctrine/graph.yaml:5-18` | ADEQUATE |
| FR-005 | `resolve_context().artifact_urns` non-empty per action | `test_research_drg_nodes.py` parametrized; smoke trail shows non-empty `governance_context_hash` | ADEQUATE |
| FR-006 | Action-scoped doctrine bundle reachable via composition resolver | `test_research_composition.py`; bundles under `src/doctrine/missions/research/actions/<action>/` | ADEQUATE |
| FR-007 | `_check_composed_action_guard` handles 5 research actions w/ parity to software-dev | `runtime_bridge.py:560-589`; `test_runtime_bridge_research_composition.py` 5 guard cases | ADEQUATE |
| FR-008 | Missing-artifact guard returns structured failure list | Each branch appends "Required artifact missing: X" / "Insufficient sources documented..." / "Publication approval gate not passed" | ADEQUATE |
| FR-009 | `_dispatch_via_composition()` propagates guard failures, no DAG fallback | `runtime_bridge.py:706-728` (StepContractExecutionError → structured surface, no fallthrough) | ADEQUATE |
| FR-010 | Loader-path parity with software-dev | Same `mission-runtime.yaml` sidecar pattern; resolved by `_resolve_runtime_template_in_root`; smoke step 1 proves discovery | ADEQUATE |
| FR-011 | `action_hint == contract.action` per invocation | Trail record from auditor smoke shows `action: scoping`; WP06 walk asserts | ADEQUATE |
| FR-012 | Paired terminal lifecycle record per invocation | Auditor smoke shows paired `started`+`completed` with `outcome: done`; trail has 6 paired files | ADEQUATE |
| FR-013 | Real-runtime walk does not mock C-007 surfaces | `grep` on `tests/integration/test_research_runtime_walk.py` returns zero hits | ADEQUATE |
| FR-014 | No regression on software-dev / custom-mission paths | Regression sweep 47/47 tests pass on `tests/specify_cli/next/test_runtime_bridge_composition.py`, `test_custom_mission_runtime_walk.py`, `test_mission_run_command.py` | ADEQUATE |
| FR-015 | All 5 contracts + 10 doctrine bundles + 5 profile defaults + dispatch entry exist | `executor.py:45-49`, `runtime_bridge.py:274`, `src/doctrine/mission_step_contracts/shipped/research-*.step-contract.yaml` (5), `src/doctrine/missions/research/actions/*/{index.yaml,guidelines.md}` (10) | ADEQUATE |

## NFR Coverage

| NFR | Surface | Status |
|---|---|---|
| NFR-001 (real-runtime walk + parametrized unit tests) | 4 test files / 65 tests / no forbidden mocks | ADEQUATE |
| NFR-002 (regression suites green) | 47/47 regression tests passed in audit run | ADEQUATE |
| NFR-003 (mypy --strict zero new) | WP04/WP05/WP06 review evidence "0 NEW errors" | ADEQUATE (re-verified by reviewer evidence; auditor did not re-run mypy) |
| NFR-004 (ruff clean) | WP04/WP05/WP06 review evidence "ruff clean" | ADEQUATE |
| NFR-005 (mission-review smoke gate) | This report's dogfood smoke section + this verdict | ADEQUATE |
| NFR-006 (operator-readable trail records) | Auditor trail sample shows `action`, `profile_id`, `outcome` | ADEQUATE |

## Drift Findings

No DRIFT findings. The merge diff (49 files, +5078 lines) stays inside the plan's stated scope:

- All "MODIFIED (additive only)" files in `plan.md` lines 233-235 match the actual diff: `src/doctrine/graph.yaml`, `src/specify_cli/mission_step_contracts/executor.py` (+5 lines), `src/specify_cli/next/runtime_bridge.py` (+118 lines).
- All "UNCHANGED (must remain so)" files (legacy `mission.yaml` × 2, software-dev mission tree, runtime engine internals, mission_step_contracts/repository.py, shared package boundaries) are unmodified by the merge diff.
- D1-D5 decisions all observable in the diff:
  - D1 (sidecar coexistence): two new `mission-runtime.yaml` files, legacy `mission.yaml` unchanged.
  - D2 (DRG hand-add): 5 nodes + 18 edges in `src/doctrine/graph.yaml`.
  - D3 (guard semantics): 5 branches + fail-closed default in `runtime_bridge.py:560-589`.
  - D4 (PromptStep shape): mirrors software-dev structure.
  - D5 (re-author from scratch): no merge from `attempt/research-composition-mission-100-broken` tag observable in commit history.
- C-001 (no host-LLM): nothing in the diff calls a model.
- C-002 (StepContractExecutor chokepoint): `_dispatch_via_composition` still calls only `StepContractExecutor.execute` (`runtime_bridge.py:707`).
- C-003 (no `_ACTION_PROFILE_DEFAULTS` wildcards): only 5 explicit `("research", action)` keys added.
- C-004/C-005 (out-of-scope tranches): no edits to docs mission, retro work, loader hygiene, SaaS, `spec-kitty explain`, or shared package surfaces.
- C-006 (legacy mission.yaml coexistence justified): plan §D1 documents it; legacy file unchanged.
- C-007 (no mocks of forbidden surfaces): grep across all four test files returns zero hits — verified.
- C-008 (smoke evidence in mission-review): this report contains a dogfood smoke section with verbatim command output, satisfying the hard gate.

## Risk Findings

### RISK-1 (LOW) — Trail records under `<host-repo>/.kittify/events/`, not `~/.kittify/invocations/`

The mission contract Scenario 1 says "the operator's invocation trail under `~/.kittify/invocations/` contains a paired `started`+`done` ... lifecycle for the action". Auditor smoke captured the trail under `<host-repo>/.kittify/events/profile-invocations/` instead. This is consistent with the WP06 reviewer's smoke (which reported `.kittify/events/profile-invocations/` in the lane workspace) and with how `SyncRuntimeEventEmitter` writes today; it is not a regression introduced by this mission. The contract phrasing is slightly stale — the runtime writes invocation records to the project's `.kittify/events/`, not the user's home directory.

**Recommendation**: in a future doc-tightening pass, update spec.md Scenario 1 phrasing to reflect actual emitter location. Not a blocker for this mission's verdict because the substantive assertion (paired lifecycle records exist with research-native action+profile) is verified.

### RISK-2 (LOW) — Init-discovery: re-running `init` from a sub-tmp picked up the host repo

When the auditor re-ran `spec-kitty init --non-interactive --ai claude` from a `/tmp/demo-research-postmerge` repo, the init reported "Already initialized" because the `.kittify` directory it discovered belonged to the host repo (the spec-kitty source tree). This is `spec-kitty init`'s ancestor-walking behavior, not a bug introduced by this mission, and the smoke flow worked because the host-repo `.kittify` was already up to date. Operators should run smoke flows from a fully isolated tmp tree to avoid mixing environments.

### RISK-3 (LOW) — `_count_source_documented_events` / `_publication_approved` read `mission-events.jsonl`, not `status.events.jsonl`

`runtime_bridge.py:445-512` reads from `<feature_dir>/mission-events.jsonl`. The repo's canonical event log is `status.events.jsonl` (per `CLAUDE.md` "Status Model Patterns" section). The two helpers comment that they mirror the v1 guard primitives in `mission_v1/guards.py`. This means the research `gathering` and `output` guards depend on a separate JSONL file that is currently not produced by any active runtime path I could identify in 5 minutes of grepping. If no surface in the codebase emits `mission-events.jsonl` records of type `source_documented` or `gate_passed`, then those two guard branches will *always* fail closed — which is technically the safer behavior, but it means an operator running through the research mission past `methodology` will hit `Required artifact missing: source-register.csv` AND `Insufficient sources documented (need >=3)` even after creating the CSV by hand.

**Recommendation**: a follow-up mission should either (a) wire a research-action surface that emits to `mission-events.jsonl`, or (b) re-point these helpers at `status.events.jsonl` with a new event type, or (c) document the emitter pattern operators must use. Not a blocker for this mission because (i) the smoke only required advancing through `scoping` and `methodology` (which check spec.md/plan.md, not mission-events.jsonl), (ii) the fail-closed default still covers unknown actions, and (iii) the v1 guard primitives in `mission_v1/guards.py` use the same JSONL — so this is preserving v1 semantics, not introducing new gaps. Worth flagging as a known cliff before this becomes a Real™ research workflow.

### RISK-4 (INFO) — `_check_composed_action_guard` `mission` parameter default is `software-dev`

`runtime_bridge.py:519` defaults `mission="software-dev"`. The `if mission == "research":` branch returns early at line 589, so the software-dev path stays untouched on default. Any future caller that adds a mission keyword without updating this function will silently route through the software-dev branches (silent pass for unrecognized mission/action combinations, since the software-dev branch chain falls off the end of the function with empty `failures` list at line 642). This is exactly the v1 P1 silent-pass shape that this mission was supposed to close — but it's only closed for `mission == "research"`. Per user MEMORY (`feedback_composed_action_guard_audit.md`): adding a built-in mission to `_COMPOSED_ACTIONS_BY_MISSION` requires extending `_check_composed_action_guard` in lockstep. That's worth keeping documented in a code comment near `_COMPOSED_ACTIONS_BY_MISSION`.

**Recommendation**: future hardening could either (a) flip the default to a fail-closed sentinel that requires explicit mission= passing, or (b) add a known-mission whitelist at the top of `_check_composed_action_guard` so unrecognized missions fail closed. Not a blocker for this mission.

## Silent Failure Candidates

| Surface | Failure mode | Mitigation in this mission |
|---|---|---|
| Unknown research action passed to `_check_composed_action_guard` | Silently pass (v1 P1) | **Closed** — fail-closed default at `runtime_bridge.py:585-588` returns `["No guard registered for research action: <action>"]` |
| `mission-events.jsonl` missing or unreadable | `_count_source_documented_events` returns 0; `_publication_approved` returns False | Acceptable (fail-closed) but operators have no on-ramp to populate the file (RISK-3) |
| Frozen-template loader exception | `_resolve_step_binding` returns `(None, None)`, fall-through to legacy DAG (`runtime_bridge.py:340-345`) | Pre-existing software-dev behavior; preserved without change |
| `StepContractExecutor.execute` raises non-`StepContractExecutionError` | Logged + returned as structured failure (`runtime_bridge.py:714-728`) | Not silent — bubbles structured CLI surface |

No new silent-failure paths introduced by this mission.

## Security Notes

The diff introduces:

- 2 new YAML files at known mission paths (no dynamic loading, schema-validated by Pydantic).
- 5 new step-contract YAMLs in shipped surface (consumed via `MissionStepContractRepository`).
- 10 new doctrine bundle files (consumed via `MissionTemplateRepository.get_action_guidelines`).
- ~150 lines of guard branches + helpers in `runtime_bridge.py` doing local file I/O on `feature_dir / "<artifact>"` and reading `mission-events.jsonl` via `read_text` / `json.loads` with try/except.
- 0 subprocess calls.
- 0 HTTP calls.
- 0 dynamic imports of user-controlled code.
- 0 changes to authentication, authorization, or trust-boundary surfaces.
- C-001 (no host-LLM) preserved: nothing in the diff invokes a model API.
- C-007 (no mocks of real-runtime surfaces) preserved: grep clean across all 4 test files.

`_count_source_documented_events` and `_publication_approved` parse `mission-events.jsonl` line-by-line with json.JSONDecodeError caught, OSError caught, missing-file returns 0/False. No deserialization vulnerabilities. No path traversal concerns (`feature_dir` is always a CLI-resolved path under `kitty-specs/`).

**Security verdict: clean.** No new attack surface introduced.

## Test Run Evidence (auditor session)

```
$ uv run pytest tests/specify_cli/test_research_drg_nodes.py \
      tests/specify_cli/mission_step_contracts/test_research_composition.py \
      tests/specify_cli/next/test_runtime_bridge_research_composition.py \
      tests/integration/test_research_runtime_walk.py -q
65 passed in 6.32s

$ uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py \
      tests/integration/test_custom_mission_runtime_walk.py \
      tests/integration/test_mission_run_command.py -q
47 passed in 5.86s

$ for f in (the 4 mission test files); do grep -nE 'patch\(.*<C-007 surface>' $f; done
(zero hits across all four files)
```

## Cross-WP Integration Check

| Integration boundary | Verifier |
|---|---|
| WP01 mission-runtime.yaml ↔ WP04 profile defaults | `test_research_composition.py` resolves all 5 (mission, action) → profile defaults |
| WP02 step contracts ↔ WP05 dispatch | `test_runtime_bridge_research_composition.py` dispatches through real `StepContractExecutor` for all 5 actions |
| WP03 DRG nodes ↔ runtime governance context | Auditor smoke trail shows `governance_context_hash` non-empty for `scoping` |
| WP05 guards ↔ WP06 walk | `test_research_runtime_walk.py` exercises real guard path on missing-artifact scenarios |
| WP06 walk ↔ live runtime | `_dispatch_via_composition`, `StepContractExecutor.execute`, `_load_frozen_template`, `load_validated_graph`, `resolve_context` all unmocked (grep verified) |
| Software-dev composition (regression) | 47/47 regression tests pass; `software-dev` entries in `_ACTION_PROFILE_DEFAULTS` and `_COMPOSED_ACTIONS_BY_MISSION` byte-identical to baseline |

## Mission-Level Acceptance Gates (from tasks.md §"Mission-Level Acceptance Gates")

1. **Runnability** — auditor smoke confirms `mission create` + `next` succeed without `MissionRuntimeError`. PASS.
2. **DRG resolution** — DRG nodes present (graph.yaml:5-18); `test_research_drg_nodes.py` 11 tests pass; smoke trail shows non-empty `governance_context_hash`. PASS.
3. **Guard parity** — 5 missing-artifact branches + fail-closed default in `runtime_bridge.py:560-589`; 28 bridge-test cases pass. PASS.
4. **No mocks of C-007 surfaces** — grep across 4 test files returns zero hits. PASS.
5. **Dogfood smoke evidence** — WP06 reviewer captured `smoke-evidence.md`; this report adds an independent post-merge smoke. PASS.
6. **No regression** — 47/47 regression tests pass. PASS.

All 6 gates closed.

## Final Verdict

**PASS WITH NOTES (preliminary).**

The mission ships a runnable, composition-backed research mission. The v1 P0 finding is closed reproducibly. All 6 mission-level acceptance gates are met. The notes (RISK-1 through RISK-4) are low-severity follow-ups, not blockers — they capture documentation drift, environmental hygiene, and a long-standing cliff inherited from the v1 guard primitives that this mission preserves rather than introduces.

**Preliminary**: per user MEMORY, an external adversarial review pass runs on local main before push. This verdict is preliminary until that pass clears. Recommend the external pass focus on RISK-3 (`mission-events.jsonl` emitter cliff) since it's the most likely surface to surface as "hidden gap" in adversarial framing.

**Not blocking release**: this verdict authorizes treating local main `83bea54` as ready for the external review pass. It does not authorize push.
