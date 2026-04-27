# Mission Review — Documentation Mission Composition Rewrite (#502)

**Reviewer**: claude:opus-4.7:reviewer-renata (mission-review skill)
**Date**: 2026-04-26
**Mission**: `documentation-mission-composition-rewrite-01KQ5M1Y` (issue #502)
**Mission number**: 101
**Baseline commit**: `62ec07b952d53e215857cd0e1c1eb7bf3f1a32dc` (origin/main pre-mission)
**HEAD (merged)**: `1c03e2f4d6db6861610cbe4cc9ae340414a5bd8f`
**Work packages**: WP01..WP07 (all approved on review cycle 0)

---

## Git timeline summary

`git log 62ec07b9..HEAD --oneline` shows the full mission cadence: per-WP "Start implementation", "Move to for_review", "Move to approved" tuples, dossier snapshots, and the final squash merge `1c03e2f4` (`feat(kitty/...): squash merge of mission`). The squash merge alone touches only `runtime_bridge.py` (+40) and `executor.py` (+6); the rest of the deliverable (YAML files, action bundles, DRG nodes, tests, mission docs) accumulates across the per-WP chore commits. Diff stat 62ec07b9..HEAD = **55 files changed, 6626 insertions(+)** with the expected sub-tree breakdown:

| Track | Path | Status |
|---|---|---|
| Runtime sidecar (specify_cli) | `src/specify_cli/missions/documentation/mission-runtime.yaml` | present (+66 lines) |
| Runtime sidecar (doctrine) | `src/doctrine/missions/documentation/mission-runtime.yaml` | present (+66 lines) |
| 6 step contracts | `src/doctrine/mission_step_contracts/shipped/documentation-{discover,audit,design,generate,validate,publish}.step-contract.yaml` | present (44–51 lines each) |
| 12 action bundle files | `src/doctrine/missions/documentation/actions/<action>/{index.yaml,guidelines.md}` | present (all 12) |
| DRG (graph.yaml) | `src/doctrine/graph.yaml` (+84 lines) | present; `grep -c "action:documentation/" src/doctrine/graph.yaml` ⇒ **28** (6 nodes + 22 scope edges) |
| Runtime bridge | `src/specify_cli/next/runtime_bridge.py` (+40 lines) | present; new `_COMPOSED_ACTIONS_BY_MISSION` documentation entry, `_has_generated_docs` helper, documentation guard branch |
| Executor profile defaults | `src/specify_cli/mission_step_contracts/executor.py` (+6 lines) | present; 6 `(documentation, X) → profile` entries |
| 5 new test files | tests under `tests/integration/`, `tests/specify_cli/`, `tests/specify_cli/mission_step_contracts/`, `tests/specify_cli/next/` | present (846 LOC total) |

No expected change is missing from the diff. No file edited by multiple WPs ended up with conflicting content.

---

## FR Coverage Matrix

| FR | Spec gist | WP owner | Test file | Adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | Fresh documentation mission MUST start via `get_or_start_run` without `MissionRuntimeError` | WP06 | `tests/integration/test_documentation_runtime_walk.py::test_get_or_start_run_succeeds_for_documentation` | ADEQUATE | Test calls real `get_or_start_run`, asserts `state.json` bootstrapped + `run_ref.mission_key=='documentation'`. |
| FR-002 | Runtime advances at least one composed step (no legacy DAG fallback) | WP05/WP06 | `..._runtime_walk.py::test_composition_advances_one_documentation_step` + `..._runtime_bridge_documentation_composition.py::test_documentation_in_composed_actions` | ADEQUATE | Snapshot's `completed_steps` advances; decision.mission stays documentation; `documentation` is in `_COMPOSED_ACTIONS_BY_MISSION` with all 6 verbs. |
| FR-003 | `MissionTemplate` MUST exist at both `src/specify_cli/...` and `src/doctrine/...` | WP01 | `test_documentation_template_resolution.py::test_documentation_runtime_template_declares_correct_mission_key` | ADEQUATE | Loads template, asserts `mission.key=='documentation'`, `len(steps)==7`, exact step IDs. |
| FR-004 | `load_validated_graph(repo).get_node('action:documentation/<x>')` truthy for each action | WP04 | `test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` (parametrized over 6 actions) | ADEQUATE | Reads real on-disk graph; calls real `load_validated_graph`. |
| FR-005 | `resolve_context(...)` non-empty `artifact_urns` per action | WP04 | same as FR-004 | ADEQUATE | `assert ctx.artifact_urns` after real `resolve_context`. |
| FR-006 | Action bundle reachable via DRG (not just MissionTemplateRepository) | WP03/WP04 | `test_documentation_drg_nodes.py::test_action_bundle_matches_drg_edges` | ADEQUATE | Asserts 1-to-1 mapping between bundle slug-form and graph URN-form (via `_SLUG_TO_URN` lookup). |
| FR-007 | `_check_composed_action_guard` parity with research/software-dev | WP05 | `test_runtime_bridge_documentation_composition.py::test_known_action_passes_when_artifact_present` (parametrized) + `..._runtime_walk.py::test_missing_artifact_blocks_with_structured_failure` | ADEQUATE | Happy path (no failures with all 6 artifacts) + sad path (failures with missing) tested. |
| FR-008 | Structured failure list naming missing artifact for each verb | WP05 | `test_runtime_bridge_documentation_composition.py::test_guard_fails_when_artifact_missing` (parametrized over 5 actions w/ artifacts) + `test_generate_guard_fails_with_empty_docs_root` | ADEQUATE | Each gate exercised; failure message exact-substring matched. |
| FR-009 | Guard failures propagate as structured errors, no DAG fallback | inherited (WP05) | `..._runtime_walk.py::test_missing_artifact_blocks_with_structured_failure` | ADEQUATE | Returns failures from real bridge; no fallback path entered. |
| FR-010 | Loader path same as software-dev/research | WP01 | `test_documentation_template_resolution.py::test_documentation_runtime_sidecar_wins_over_legacy_mission_yaml` | ADEQUATE | Calls real `_resolve_runtime_template_in_root`. |
| FR-011 | `action_hint == contract.action` | substrate (WP06) | `..._runtime_walk.py::test_paired_invocation_lifecycle_is_recorded` | ADEQUATE | Asserts trail's `action` field is in documentation action set. |
| FR-012 | Paired terminal record (`done`/`failed`) | substrate (WP06) | same as FR-011 | ADEQUATE | Asserts `completed` event with valid outcome paired with `started`. |
| FR-013 | Real-runtime test does not mock the 6 forbidden surfaces | WP06 | `test_documentation_runtime_walk.py` | ADEQUATE | C-007 grep against the file returns zero substantive matches; module docstring lists the prohibition; tests call real APIs. |
| FR-014 | Existing software-dev/research/custom-mission tests unchanged | WP07 | `evidence/regression.md` + my re-run | ADEQUATE | Re-ran 6 protected suites: 127/127 PASS in 14.43s. |
| FR-015 | 6 contracts, 6 bundles, 6 profile defaults, documentation in composed map | WP02/WP03/WP05 | `test_documentation_composition.py::test_contract_loads_with_correct_keys` (parametrized) + `..._runtime_bridge_documentation_composition.py` | ADEQUATE | Contracts validated structurally; profile defaults asserted; composed entry asserted. |
| FR-016 | Profile defaults: discover/audit→researcher-robbie, design→architect-alphonso, generate→implementer-ivan, validate/publish→reviewer-renata | WP05 | `..._runtime_bridge_documentation_composition.py::test_profile_defaults_per_action` | ADEQUATE | Parametrized over all 6 verb→profile pairs; reads real `_ACTION_PROFILE_DEFAULTS`. |
| FR-017 | Unknown documentation action MUST return `"No guard registered for documentation action: <name>"` | WP05/WP06 | `..._runtime_walk.py::test_unknown_documentation_action_fails_closed` + `..._runtime_bridge_documentation_composition.py::test_unknown_documentation_action_fails_closed` | ADEQUATE | Exact-string match `failures == ["No guard registered for documentation action: ghost"]`. |
| FR-018 | Loader resolves `mission-runtime.yaml` ahead of legacy `mission.yaml` | WP01 | `test_documentation_template_resolution.py::test_documentation_runtime_sidecar_wins_over_legacy_mission_yaml` | ADEQUATE | Asserts `resolved.name == "mission-runtime.yaml"`. Both files exist on disk (verified). |

**FR coverage**: 18/18 ADEQUATE. No PARTIAL, MISSING, or FALSE_POSITIVE rows.

---

## SC Coverage Matrix

| SC | Outcome | Evidence | Status |
|---|---|---|---|
| SC-001 | Fresh documentation mission can be created and advanced | `..._runtime_walk.py::test_get_or_start_run_succeeds_for_documentation` + smoke evidence (`kind=query, mission=documentation, preview_step=discover` from `next.json`) | PASS |
| SC-002 | Each action has DRG node + non-empty resolved context | `test_documentation_drg_nodes.py::test_each_documentation_action_has_drg_node_and_context` | PASS |
| SC-003 | Missing artifacts produce structured guard failures + unknown-action fail-closed | `..._runtime_walk.py::test_missing_artifact_blocks_with_structured_failure` + `test_unknown_documentation_action_fails_closed` | PASS |
| SC-004 | Real-runtime test passes without bypassing composition surfaces | C-007 grep against `tests/integration/test_documentation_runtime_walk.py` returns **0 substantive matches**; only docstring listing | PASS |
| SC-005 | NFR-002 regression suites pass | Re-run: **127/127 pass** on the 6 protected suites in 14.43s; full mission test set: 48/48 pass in 20.97s | PASS |
| SC-006 | Mission-review PASS verdict carries dogfood smoke evidence | `evidence/smoke.md` (254 lines) shows `mission == "documentation"`, `preview_step == discover`, all `uv run --project` (3 hits), zero `--directory` substantive hits, temp repo OUTSIDE spec-kitty tree | PASS |
| SC-007 | Documentation runtime template resolves before legacy mission.yaml | `test_documentation_template_resolution.py::test_documentation_runtime_sidecar_wins_over_legacy_mission_yaml` (asserts `resolved.name == "mission-runtime.yaml"`); also asserted in `..._runtime_walk.py::test_documentation_template_resolves_runtime_sidecar` | PASS |

**SC coverage**: 7/7 PASS.

---

## NFR / Constraint Coverage Matrix

| ID | Threshold | Verification | Status |
|---|---|---|---|
| NFR-001 | Real-runtime walk + parametrized unit tests for all 6 actions | 5 new test files, 48 tests across them; integration walk has 6 tests | PASS |
| NFR-002 | 100% pass on 6 protected suites | Re-run on HEAD: 127 passed, 0 failed (`tests/specify_cli/mission_step_contracts/`, `test_runtime_bridge_composition.py`, `test_runtime_bridge_research_composition.py`, `test_research_runtime_walk.py`, `test_custom_mission_runtime_walk.py`, `test_mission_run_command.py`) | PASS |
| NFR-003 | Zero NEW mypy-strict findings on changed files | `evidence/lint.md`: 1 finding total (`executor.py:106` `[no-any-return]`); proven pre-existing on baseline by inspecting `git show 62ec07b9:src/specify_cli/mission_step_contracts/executor.py:106` (untouched). Delta = 0. | PASS |
| NFR-004 | Zero NEW ruff findings | `evidence/lint.md`: `All checks passed!` exit 0 | PASS |
| NFR-005 | Smoke uses `uv run --project`, never `--directory` | `evidence/smoke.md` V3: `grep -E "uv (run|--).*--directory" /tmp/wp07-smoke-transcript.txt` returns no matches; `grep -c -- "--project"` returns 3 | PASS |
| NFR-006 | Trail records carry action/profile/lifecycle | `..._runtime_walk.py::test_paired_invocation_lifecycle_is_recorded` reads real JSONL records, asserts `action` ∈ doc-action-set, `outcome` ∈ {done, failed}, paired started+completed | PASS |
| NFR-007 | Documentation `resolve_context` median ≤ 2× research median | `test_documentation_drg_nodes.py::test_resolve_context_within_research_2x` (median of 5 runs × 6 actions vs 5 runs × 5 research actions); test passes in re-run | PASS |
| C-001 | No host LLM calls | grep `openai|anthropic` in `runtime_bridge.py` and `executor.py` returns only `actor_type="llm"` identity strings (not API client imports) | PASS |
| C-002 | Composition chokepoint stays `StepContractExecutor` | No new direct `ProfileInvocationExecutor.invoke` call sites added in documentation paths; `runtime_bridge.py` documentation branch only uses `_check_composed_action_guard` and dispatches via existing `_dispatch_via_composition` path | PASS |
| C-003 | `_ACTION_PROFILE_DEFAULTS` additions limited to documentation; no wildcards | Diff shows only 6 explicit `("documentation", "<verb>") → "<profile>"` entries; no wildcard keys | PASS |
| C-004 | Out-of-scope items not touched | No retrospective/explain/sync changes in diff; no `.python-version` edit; no #805 cast change | PASS |
| C-005 | No edits to research/software-dev branches in `_check_composed_action_guard` | `git show 1c03e2f4 -- src/specify_cli/next/runtime_bridge.py | grep -E "^\+|^-" | grep -E "research\|software-dev"` returns **zero matches**; documentation branch is purely additive | PASS |
| C-006 | Legacy `mission.yaml` coexists | `ls src/specify_cli/missions/documentation/` and `src/doctrine/missions/documentation/` both list `mission.yaml` alongside `mission-runtime.yaml` | PASS |
| C-007 | No mocks of forbidden symbols in integration walk | Final grep against `tests/integration/test_documentation_runtime_walk.py` ⇒ **0 substantive matches** for the entire forbidden symbol regex | PASS |
| C-008 | WP07 evidence committed | `kitty-specs/.../evidence/{regression,lint,smoke}.md` all present in tree | PASS |
| C-009 | No `expected_artifacts` on contracts | `grep -n "expected_artifacts" src/doctrine/mission_step_contracts/shipped/documentation-*.step-contract.yaml` returns 6 hits — all are **comments** stating `"forbids expected_artifacts on contracts or steps"`; no actual key declared. Test `test_documentation_composition.py::test_contract_loads_with_correct_keys` enforces `_ALLOWED_TOP_LEVEL_KEYS = {schema_version, id, action, mission, steps}` and rejects `expected_artifacts` on each step | PASS |
| C-010 | Smoke from temp repo OUTSIDE spec-kitty tree | `evidence/smoke.md` V4: temp path `/var/folders/.../docs-smoke-XXXXXX.../repo` is outside the spec-kitty checkout | PASS |

---

## Drift Findings

None observed. Each plan decision D1–D7 is verified in code:

- **D1** (coexistence): both `mission.yaml` files retained; loader test `test_documentation_runtime_sidecar_wins_over_legacy_mission_yaml` enforces precedence.
- **D2** (DRG authoring location): nodes/edges live in `src/doctrine/graph.yaml` directly (28 occurrences of `action:documentation/`); `test_action_bundle_matches_drg_edges` enforces 1-to-1 with action bundles.
- **D3** (hardcoded guard checks): `runtime_bridge.py` documentation branch checks `feature_dir / "spec.md"`, etc. without parsing `expected-artifacts.yaml`.
- **D4** (no `contract_ref`): the runtime sidecar steps declare only id/title/depends_on/agent-profile/prompt_template/description.
- **D5** (`accept` not in `_COMPOSED_ACTIONS_BY_MISSION`): `test_documentation_in_composed_actions` asserts `"accept" not in _COMPOSED_ACTIONS_BY_MISSION["documentation"]`. Documentation entry contains exactly the 6 composed verbs.
- **D6** (`generate` predicate "any *.md under docs/"): `_has_generated_docs` rglob's `*.md` under `feature_dir / "docs"`; `test_generate_guard_passes_with_one_md_under_docs` exercises it.
- **D7** (`validate=audit-report.md`, `publish=release.md`): hardcoded in the guard branch and tested via `test_guard_fails_when_artifact_missing` parametrization.

No locked-decision violations.

---

## Risk Findings

None at HIGH or CRITICAL severity. Two LOW notes (informational, non-blocking):

1. **LOW — Coarse `generate` predicate**: per plan D6 (acknowledged risk note), an operator could create `docs/notes.md` and pass the gate without producing real output. Mitigation already in spec: tighter gates at `validate` (audit-report.md) and `publish` (release.md). Documented; not a regression vs the spec.
2. **LOW — Guard dispatch growing**: per plan premortem #5, `_check_composed_action_guard` now handles software-dev + research + documentation; future seventh mission inherits the linear conditional ladder. Plan explicitly defers this refactor to Phase 7. Out of scope for #502.

---

## Silent Failure Candidates

I scanned the new code paths for silent error paths:

- `_has_generated_docs(feature_dir)` returns `False` when `(feature_dir / "docs")` is not a directory, which causes `_check_composed_action_guard` to append `"Required artifact missing: docs/**/*.md ..."` — this is the desired fail-closed behavior, not a silent pass.
- `next(docs_root.rglob("*.md"), None) is not None`: explicit fall-through with sentinel; no exception swallowing.
- The documentation guard branch has an `else:` clause that appends the fail-closed `"No guard registered for documentation action: <action>"` message — verified via `test_unknown_documentation_action_fails_closed` against `mission="documentation", action="ghost"`.
- No new bare `except`, `except Exception: pass`, `return None`, or `return ""` patterns introduced in the documentation diff.

No silent failure candidates.

---

## Security Notes

Light pass (internal substrate, no external surface):

- No new `subprocess` calls with `shell=True` introduced in `runtime_bridge.py` or `executor.py`.
- No new `requests`, `urllib`, `httpx`, or other HTTP client imports introduced.
- `_has_generated_docs(feature_dir)` constrains its glob root to `feature_dir / "docs"` (no user-controlled dynamic component); no path traversal risk.
- The new `_check_composed_action_guard` documentation branch only does `Path.is_file()` / `Path.is_dir()` checks against `feature_dir / <hardcoded-name>`; no command execution or template interpolation.
- Trail records emitted by `ProfileInvocationExecutor` are still under `~/.kittify/events/profile-invocations/` (or `<repo>/.kittify/...`) — same surface as the landed research path.

No security issues.

---

## Cross-WP Integration Notes

The plan's two-WP-touch concern was `runtime_bridge.py` (WP05 dispatch + WP06 walk reads). Both lanes landed cleanly: WP05 added the dispatch entry, profile defaults, guard branch, and helper; WP06 only read those surfaces from tests. No double-edit conflicts.

`graph.yaml` was edited only by WP04. Action bundle index files were authored only by WP03 and **read** by WP04's `test_action_bundle_matches_drg_edges`, which enforces the 1-to-1 mapping that protects against drift between WP03 and WP04 outputs.

The mission's per-WP review history (events log, 54 lines) shows zero rejections, zero forced transitions, zero arbiter overrides. All WPs landed on review cycle 0.

---

## Final Verdict: **PASS**

### Verdict rationale

- All 18 FRs have ADEQUATE test coverage; no PARTIAL/MISSING/FALSE_POSITIVE rows.
- All 7 SCs are PASS, including the hard-gated SC-006 dogfood smoke from a temp repo outside the spec-kitty tree using `uv run --project` (NFR-005 / C-010).
- All 7 NFRs and all 10 Constraints (C-001..C-010) are observably satisfied; the C-007 forbidden-symbol grep against the integration walk returns zero substantive hits.
- Re-running the protected NFR-002 suites on HEAD: 127/127 PASS.
- Re-running the 5 new test files: 48/48 PASS.
- Plan decisions D1..D7 are all observable in the merged code; no locked-decision violations.
- mypy/ruff zero new findings; the single mypy item flagged in evidence is pre-existing baseline (#805).
- WP cadence is clean: zero rejections, zero forced transitions, zero arbiter overrides; all WPs approved on review cycle 0.
- No silent-failure candidates introduced.
- No security regressions: no new shell exec, HTTP, or path-traversal surface.
- The smoke evidence shows `mission == "documentation"`, `preview_step == "discover"`, three `uv run --project` invocations, zero substantive `--directory` hits.

### Open items (non-blocking)

1. **Generate gate is coarse** (plan D6 risk #2 acknowledged): an operator can pass `generate` with `docs/notes.md` only. Mitigated by `validate` (audit-report.md) and `publish` (release.md) being tighter blocking gates. No action needed for #502.
2. **Guard dispatch ladder growth** (plan premortem #5): a future seventh mission will add another 30-line conditional. Refactoring `_check_composed_action_guard` into a registry is a Phase 7 candidate. Out of scope for #502.
3. **Pre-existing mypy item at `executor.py:106`**: tracked under #805 hygiene; explicitly carved out in spec NFR-003 ("baseline errors are not regressed").

No blocking findings.
