# Mission Review Report: templates-as-config-01KXMS1G

**Reviewer**: Codex (GPT-5), post-merge mission review  
**Date**: 2026-07-16  
**Mission**: `templates-as-config-01KXMS1G` — Templates as Mission Configuration  
**Source issue**: [#2658](https://github.com/Priivacy-ai/spec-kitty/issues/2658)  
**Baseline commit**: `6bd1d4b1b5be5318d323bfd666b7bc155087b7de`  
**HEAD at frozen review**: `534bd432076ee2c06b42538af2f2ef0149faa13b`  
**E2E harness HEAD**: `4ab0e9b6d1725092c335644f51621781c18f13a1`
**WPs reviewed**: WP01–WP05 (all `done`)

## Executive Summary

The merged implementation realizes #2658's doctrine → charter → core template authority swap. All nine functional requirements have live code and adequate behavioral coverage, no out-of-scope #2659–#2661 retirement work was pulled in, and all product findings found during post-merge and adversarial review were remediated. Frozen local contract, architecture, focused, lint, and type gates pass.

The overall mission-review verdict remains **FAIL** because mandatory Cross-Repo E2E Gate 3 is not fully green and no valid operator exception exists. After repairing the drift harness and replacing a nominal planning smoke test with a real four-WP lifecycle, five scenarios pass. The remaining authenticated SaaS scenario xfails because no endpoint is configured. No #2658 product defect was observed in that environmental non-pass, but the hard-gate policy does not permit treating it as success.

## Gate Results

### Gate 1 — Contract tests

- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_TEST_DB_NAME=test_templates_as_config_frozen_contract uv run pytest -q tests/contract`
- Exit code: `0`
- Result: **PASS**
- Evidence: `293 passed, 3 skipped, 0 failed` in 45.78s. Teardown emitted nonfatal unauthenticated final-sync diagnostics after the tests; local contract success remained intact.

### Gate 2 — Architectural tests

- Command: `env -u SPEC_KITTY_ENABLE_SAAS_SYNC SPEC_KITTY_TEST_DB_NAME=test_templates_as_config_frozen_arch uv run pytest tests/architectural -q`
- Exit code: `0`
- Result: **PASS**
- Evidence: `1,014 passed, 4 skipped, 0 failed` in 792.83s at clean, unchanged HEAD `534bd432`.

### Gate 3 — Cross-repo E2E

- Command: `env -u SPEC_KITTY_SAAS_ENDPOINT -u SK_E2E_SAAS_URL SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_REPO=<spec-kitty> SK_E2E_SPEC_KITTY_REPO=<spec-kitty> SK_E2E_SPEC_KITTY_BIN=<spec-kitty>/.venv/bin/spec-kitty .venv/bin/python -m pytest scenarios/ -vv -ra`
- Exit code: `0` (not sufficient for the hard gate because one required scenario xfailed)
- Result: **FAIL — no operator exception**
- Evidence at E2E commit `4ab0e9b`: `5 passed, 1 xfailed` in 147.59s.
  - `contract_drift_caught`: PASS after installing its packaging-test dependency and staging the fake events candidate after Spec Kitty.
  - `uninitialized_repo_fail_loud`: all three command cases PASS.
  - `dependent_wp_planning_lane`: PASS after exercising three sequential code WPs, one dependent planning-artifact WP, review/approval, acceptance, Spec Kitty's PR-bound lane merge, a simulated PR merge, and commit/deliverable ancestry checks.
  - `saas_sync_enabled`: XFAIL because neither `SPEC_KITTY_SAAS_ENDPOINT` nor `SK_E2E_SAAS_URL` is configured.
- Classification: the sole non-pass is an environmental prerequisite on the available evidence, not an observed #2658 code defect. Hard-gate policy still requires a green run or a valid human-authored exception. TF-060 records why process exit zero cannot be treated as success when a required scenario xfails.

### Gate 4 — Issue Matrix

- File: `kitty-specs/templates-as-config-01KXMS1G/issue-matrix.md`
- Rows: `1`
- Empty or `unknown` verdicts: `0`
- Deferred rows missing follow-up: `0`
- Result: **PASS** (`#2658` is `fixed`)

## Additional Frozen Validation

- Changed-test corpus from the mission merge base: `251 passed, 0 failed`, with four known `DoctrineLayerCollisionWarning` warnings, in 70.79s.
- Ruff lint across all 16 changed Python files: PASS.
- Strict mypy across the five changed production files: PASS.
- Ruff format differences are baseline-only: the same ten files require formatting at the mission merge base.
- Range `git diff --check` reports intentional Markdown hard-break spaces in generated planning artifacts. Three unintended trailing spaces in the retrospective/WP history were removed during report finalization; no source or test whitespace defect was present.

## FR Coverage Matrix

| FR | Delivered behavior | WP | Adequate live evidence | Verdict |
|---|---|---|---|---|
| FR-001 | Activated context lazily projects doctrine `MissionType.template_set`. | WP01 | `tests/charter/test_resolved_mission_type_context.py`, `tests/doctrine/missions/test_mission_type_repository.py` | ADEQUATE |
| FR-002 | Complete immutable mapping is artifact-sourced, never profile-string-sourced. | WP01 | Exact mapping, immutability, deterministic projection, and profile-isolation tests | ADEQUATE |
| FR-003 | Specification and plan readers select semantic keys through resolved context. | WP02–WP04 | `tests/specify_cli/core/test_feature_creation.py`, `tests/specify_cli/cli/commands/agent/test_mission_setup_plan_phases.py` | ADEQUATE |
| FR-004 | Existing five-tier precedence remains authoritative after filename selection. | WP02–WP04 | `tests/runtime/test_resolver_unit.py`, `tests/integration/test_mission_type_resolution_integration.py`, CLI smoke | ADEQUATE |
| FR-005 | Null/missing configuration never borrows software-development content. | WP02–WP04 | Typed failure matrix plus live command-boundary failure tests | ADEQUATE |
| FR-006 | Missing keys/files identify mission type and artifact kind actionably. | WP02–WP04 | Resolver, specification, and planning error-path tests | ADEQUATE |
| FR-007 | Shipped software-development spec/plan winners and bytes remain compatible. | WP03–WP05 | Exact package and project-override parity evidence plus live integration tests | ADEQUATE |
| FR-008 | Transitional parity scaffold ran and was removed before merge. | WP05 | Recorded four-node parity replay plus `tests/architectural/test_no_parity_scaffold.py` | ADEQUATE |
| FR-009 | Enduring doctrine and integration coverage remains after scaffold removal. | WP05 | Frozen architecture/contract/251-test corpus and semantic reappearance guard | ADEQUATE |

## NFR and Constraint Review

| Item | Evidence | Verdict |
|---|---|---|
| NFR-001 — <100 ms hot path | Lazy projection; performance nodes passed in the frozen changed corpus | PASS |
| NFR-002 — deterministic ordered content | Repeated/cached resolution and immutable mapping tests | PASS |
| NFR-003 — zero shipped content change | Exact winner path, tier, mission, and bytes verified | PASS |
| NFR-004 — doctrine plus integration coverage | Doctrine repository/context and both production readers are exercised | PASS |
| C-001/C-002 — activation and single authority | Charter activation gates doctrine projection; no parallel registry | PASS |
| C-003 — no profile-string authority | Profile-level `template_set` is excluded from resolved mapping source | PASS |
| C-004 — no parity scaffold | Source and stale bytecode reappearance guard passes | PASS |
| C-005 — sibling retirement scope | Meta-less fallback remains isolated for #2660; no enumeration/tree deletion added | PASS |
| C-006 — no release commitment | No version/release change | PASS |

## Resolved Review Findings

| Finding | Resolution evidence |
|---|---|
| Plan setup read mission identity from a meta-less coordination surface | Uses canonical planning read directory; distinct-surface regression test; commit `56fea12cb` |
| Architectural golden count and marker baselines failed | Baselines repaired and full architecture gate restored; commit `7ba3163c3` |
| Squash merge lost newer traces/review normalization | Traces and WP history restored; commits `7312785ab`, `4219dfa0e` |
| Squash merge lost canonical acceptance/VCS provenance from `meta.json` | Exact accepted fields restored from the still-ancestral acceptance commit while preserving `baseline_merge_commit` and `mission_number`; recorded as TF-066 |
| Unsafe configured filenames could escape or alias paths | Safe portable segment validation and tests; commits `bbdcfc0f1`, `24c03dabc`, `eed625ae4` |
| Corrupt/present-invalid metadata entered typeless compatibility behavior | One strict snapshot; present invalid data fails before mutation; commits `c654c4016`, `cca980a81`, `fbbd158ea` |
| Supported legacy `mission` metadata was rejected | Canonical compatibility reader used from the same strict snapshot; commit `d7ac5737b` |
| Architecture guard overfit aliases, dead code, and exact statement shape | 309 lines of mutation theater removed; semantic authority/typeless guards retained; commit `d7ac5737b` |
| Architecture documentation described live slots as reserved | Mission-type and runtime-loop docs updated; commits `d7ac5737b`, `534bd4320` |
| E2E drift scenario lacked `build` and overwrote its fake dependency | Dependency installed and fake staged last; sibling commit `615f1a6` |
| Dependent-WP E2E claimed a four-WP merge but stopped after planning | Replaced with real dependent code/planning lanes, approvals, acceptance, merge, and ancestry checks; sibling commit `4ab0e9b` |

## Drift Findings

No unresolved #2658 implementation drift remains. The exact meta-less software-development template fallback is retained because spec C-005, the mission research/contract, and original sibling issue #2660 assign its removal to the later retirement slice. It is not inferred for a known activated mission type.

## Risk Findings

### RISK-1 — Mandatory SaaS E2E evidence is unavailable

**Type**: ENVIRONMENT / RELEASE EVIDENCE  
**Severity**: HIGH for release gating; not an observed product defect  
**Trigger**: run the mandatory sibling scenarios while logged out and with no configured endpoint.

The gate cannot prove authenticated SaaS behavior on this machine. Completion requires legitimate authentication and endpoint configuration, or a schema-valid human operator exception for a genuinely environmental scenario. No credentials or waiver were invented during review.

## Silent Failure Candidates

No new silent-default path was found. Null/missing mappings and unresolved configured files raise `TemplateConfigurationError`. The physically absent-metadata plan branch is an explicit, tested compatibility decision owned for later removal by #2660; malformed or identity-less present metadata does not enter it.

## Security Notes

| Surface | Assessment | Result |
|---|---|---|
| Configured filename | Doctrine/overlay-authored value must be one portable safe segment; traversal, separators, absolute paths, Windows device names, and trailing aliases are rejected. | PASS |
| Metadata symlink | Readable links are accepted; only broken/self-loop links fail so corruption cannot impersonate absence. | PASS |
| Manually constructed resolved context | Not treated as authenticated; only cheap path safety is enforced. Normal CLI contexts come from charter activation. | PROPORTIONATE |
| Subprocess/network/auth | #2658 introduces no new subprocess, HTTP, token, or credential path. | N/A |

## Final Verdict

**FAIL — mandatory Cross-Repo E2E Gate 3 still has one required xfail and no valid operator exception.**

### Verdict rationale

The implementation itself is spec-faithful, fully covered, locally gate-clean, and has no remaining blocking product or security finding. The binary FAIL is imposed solely by the documented hard-gate rule: the authenticated SaaS scenario xfails in the available environment because no endpoint is configured. A green authenticated/endpoint run or valid human-authored exception is required before this report can be revised to PASS.

### Open items

- Authenticate Spec Kitty and configure a reachable dev SaaS endpoint, then rerun Gate 3; alternatively provide a valid per-scenario human operator exception where policy permits.
- Tooling-friction reconciliation is complete: all TF-001–TF-067 mappings and newly filed reports are recorded in `traces/tooling-friction-issue-map.md`.
- Issue #2660 remains the owner of meta-less software-development template fallback removal.

## Retrospective Reminder

The merge-authored retrospective is present at `kitty-specs/templates-as-config-01KXMS1G/retrospective.yaml`. The canonical follow-through remains:

- `spec-kitty retrospect summary` for cross-mission aggregation.
- `spec-kitty agent retrospect synthesize --mission templates-as-config-01KXMS1G` to inspect proposals (dry-run by default).
- Add `--apply` only when staged proposals have been reviewed and mutation is intended.

If the runtime expects a mirrored `.kittify/missions/<mission_id>/retrospective.yaml` and it is absent after cleanup, escalate that mismatch rather than fabricating a second record.
