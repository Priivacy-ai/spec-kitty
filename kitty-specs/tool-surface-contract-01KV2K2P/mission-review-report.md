# Mission Review Report: tool-surface-contract-01KV2K2P

**Reviewer**: Claude (post-merge mission review, original analysis)
**Date**: 2026-06-14
**Mission**: `tool-surface-contract-01KV2K2P` — ToolSurfaceContract: Unified Tool Surface Registry
**Baseline commit**: `789d34b04^` (`6ec742e84`) → mission squash `789d34b04`
**HEAD at review**: `c56f7899c`
**WPs reviewed**: WP01–WP09 (all `done`)

---

## Gate Results

### Gate 1 — Contract tests
- Command: `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/contract/`
- Exit code: 0
- **Result: PASS** — 258 passed (47.7s). (One non-fatal `sync.server_auth_failure` warning — auth not logged in; not a code defect.)

### Gate 2 — Architectural tests
- Command: `.venv/bin/python -m pytest tests/architectural/`
- Exit code: non-zero — **5 failed, 356 passed**
- **Result: FAIL** — 4 of the 5 failures are mission-caused (see Drift/Risk findings). The 5th (`test_runtime_charter_doctrine_boundary`) is PRE-EXISTING — the mission's diff does not touch `src/runtime/` (verified: empty diff under `src/runtime/`).

| Failing test | Mission-caused? | Finding |
|---|---|---|
| `test_no_dead_modules::test_no_new_dead_modules_under_src` | **YES** | DRIFT-1 |
| `test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported` | **YES** | DRIFT-2 / RISK-1 |
| `test_pytest_marker_convention::test_every_test_file_declares_a_pytestmark_marker` | **YES** | RISK-2 |
| `test_docs_cli_reference_parity::test_visible_paths_match_reference` | **YES** | DRIFT-3 |
| `test_runtime_charter_doctrine_boundary::test_runtime_has_no_new_direct_doctrine_imports` | NO (pre-existing) | — |

### Gate 3 — Cross-repo E2E
- **Result: N/A (environmental)** — the `spec-kitty-end-to-end-testing` repo is not present in this workspace. This mission delivers a host-internal CLI surface registry; it claims no new cross-repo behavior, so the four floor scenarios (`dependent_wp_planning_lane`, `uninitialized_repo_fail_loud`, `saas_sync_enabled`, `contract_drift_caught`) do not exercise this mission's code. No `mission-exception.md` authored because no mission code change requires an e2e scenario. Recommend running the suite in CI where the e2e repo is available.

### Gate 4 — Issue Matrix
- File: `kitty-specs/tool-surface-contract-01KV2K2P/issue-matrix.md`
- Rows: 11. Empty / `unknown` verdicts: 0. `in-mission` survivors: 0. `deferred-with-followup` missing handle: 0.
- All verdicts terminal: `#1945 fixed`, `#1935 verified-already-fixed`, `#1936–#1944 fixed`.
- **Result: PASS**

> **Hard-gate rule:** a FAIL on Gate 2 forces the Final Verdict to FAIL.

---

## FR Coverage Matrix — 18/18 functionally covered

| FR | Brief | WP | Test evidence | Adequacy |
|----|-------|----|---------------|----------|
| FR-001 | Single registry returns all surfaces for a tool | WP01/03/04 | `test_registry`, live `build_registry` (8 defs/tool) | ADEQUATE |
| FR-002 | `doctor tool-surfaces --json` machine-readable + finding codes | WP03 | `integration/test_doctor_tool_surfaces_cli`, schema-validated live | ADEQUATE |
| FR-003 | Covers all surface kinds | WP03/04/05/06/09 | live run emits 7 kinds | ADEQUATE |
| FR-004 | `--kind` filter | WP03 | CLI filter test + live | ADEQUATE |
| FR-005 | Stable kebab finding codes | WP03 | `test_findings` (islower, no `_`) | ADEQUATE |
| FR-006 | Repair runnable w/o manual edit | WP03/04/05 | no-stub `--fix` verified per provider | ADEQUATE |
| FR-007 | `doctor skills --json` backward-compat | WP02 | frozen `doctor_skills_baseline.json` | ADEQUATE |
| FR-008 | `agent config list/status/sync` unchanged | WP02/07 | `test_agent_config_compat` + WP07 byte-stable diff | ADEQUATE |
| FR-009 | No config migration on upgrade | WP02 | compat gate | ADEQUATE |
| FR-010 | Wrap installers as providers (preserve logic) | WP03/04/05 | providers delegate (verified) | ADEQUATE |
| FR-011 | Migration/compat early gate | WP02 | 26 baselines | ADEQUATE |
| FR-012 | Project native agent profiles | WP06 | `profiles/test_projection` + live (16 profiles) | ADEQUATE |
| FR-013 | Profiles get manifest/doctor/repair | WP06 | `profiles/test_manifest`, live `--fix` | ADEQUATE |
| FR-014 | `RESEARCH_GAP` for unsupported tools | WP06 | `research-gap-surface` emitted (codex) | ADEQUATE |
| FR-015 | Plugin bundle projection + pre-publish validation | WP09 | `bundles/*`, `test_plugin_bundle` | ADEQUATE |
| FR-016 | No auto-install / no marketplace publish | WP09 | negative-assertion tests (reproduced) | ADEQUATE |
| FR-017 | Docs path validation against registry | WP08 | `test_docs` (drift-injection reproduced) | ADEQUATE |
| FR-018 | Distinct surface kinds in output | WP01/04/05 | live output separation | ADEQUATE |

**NFRs:** NFR-001 (<5s/19 tools) PASS (~1.6s measured). NFR-002 (mypy strict, 0) PASS. NFR-004 (no `doctor skills` schema regression) PASS (frozen baseline).

The functional contract is fully and adequately realized. **The FAIL verdict is driven solely by mission-caused architectural-gate regressions (hygiene/CI-visibility), not by any FR gap, locked-decision violation, or security defect.**

---

## Drift Findings

### DRIFT-1: Two orphaned WP01 skeleton modules are dead code
**Type**: DEAD-CODE (architectural gate `test_no_dead_modules`)
**Severity**: MEDIUM
**Evidence**:
- `src/specify_cli/tool_surface/builtins.py` — `register_builtin_definitions()` / `supported_tool_keys()` stub from WP01. `grep -rn 'tool_surface.builtins' src/` returns ZERO importers. Superseded by `service.build_registry()` (WP03+).
- `src/specify_cli/tool_surface/providers/base.py::AbstractSurfaceProvider` — WP01 protocol. Real providers use `providers/protocol.py::ReportingSurfaceProvider` (`service.py:39,120`); `AbstractSurfaceProvider` appears only in a `protocol.py` docstring, never imported. 
**Analysis**: WP01 was approved as a "structural skeleton"; WP03 then introduced the canonical `service.build_registry` + `providers/protocol.ReportingSurfaceProvider` and never retired the WP01 stubs. The per-WP reviews each looked correct in isolation; the orphaning is only visible cross-WP. Fails the repo-wide dead-module gate (runs in CI `integration-tests-core-misc`, not the per-WP `tests/specify_cli/tool_surface/` suite — which is why it slipped through). Fix: remove both, or wire `builtins.register_builtin_definitions` into `build_registry` and make providers implement `AbstractSurfaceProvider`.

### DRIFT-2: New public symbols exported but unimported
**Type**: DEAD-SYMBOL (architectural gate `test_no_dead_symbols`)
**Severity**: LOW-MEDIUM
**Evidence**: `specify_cli.cli.commands.agent.surface_presence::ToolSurfacePresence` and `::GlobalCommandDirResolver` (WP07) are in `__all__` but no `src/` file imports them.
**Analysis**: WP07 over-exported internal helpers. Either drop them from `__all__` (keep as internals) or add a rationale + tracker to `_SYMBOL_ALLOWLIST`.

### DRIFT-3: New visible CLI command absent from the generated CLI reference
**Type**: DOCS-PARITY (architectural gate `test_docs_cli_reference_parity`)
**Severity**: MEDIUM
**Evidence**: `test_visible_paths_match_reference` fails — the visible `doctor tool-surfaces` command path is not present in the generated CLI command reference doc.
**Analysis**: The mission added a user-visible command (FR-002) but did not regenerate/update the CLI reference. WP08's docs lint validates *path* references, not the *command* reference parity, so it didn't catch this. Fix: regenerate the CLI reference doc to include `doctor tool-surfaces`.

---

## Risk Findings

### RISK-1: Stale dead-code allowlist entries (now wired)
**Type**: TEST-MAINTENANCE (architectural gate `test_no_dead_symbols`)
**Severity**: LOW
**Location**: `tests/architectural/test_no_dead_symbols.py::_SYMBOL_ALLOWLIST`
**Evidence**: `session_presence.writers.claude_code::SESSION_START_CMD`, `::SESSION_STOP_CMD` (now used by WP04), and `skills.manifest_store::fingerprint`, `::fingerprint_file` (now used by WP06) are still in the allowlist but now have live callers; the gate requires removing them.
**Analysis**: The mission legitimately wired previously-dead symbols (a *good* change) but didn't update the allowlist that recorded them as dead. Fix: remove the 4 entries from `_SYMBOL_ALLOWLIST`.

### RISK-2: 12 new test files omit the required `pytestmark` marker
**Type**: CI-VISIBILITY (architectural gate `test_pytest_marker_convention`)
**Severity**: MEDIUM
**Location**: `tests/specify_cli/tool_surface/bundles/test_{claude,copilot,model}.py`, `integration/test_{agent_config_compat,compat_support,doctor_tool_surfaces_cli,migration_compat}.py`, `profiles/test_{manifest,projection,renderers}.py` (+ others).
**Trigger**: marker-based CI profile selection.
**Analysis**: These files declare no `pytestmark`, so they are invisible to the project's marker-based CI profiles — the mission's tests pass locally (222 green) but a marker-filtered CI job may not collect them, silently reducing CI coverage of exactly this mission's surface. Fix: add the project-standard `pytestmark` to each file.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|----------|-----------|---------------|-------------|
| `tool_surface/providers/managed_skills.py:~201` | managed-skill file present but unreadable (`OSError` in `_content_hash`) | drift check skipped → reports `present` | LOW — bounded to hash comparison, not error masking; benign edge (already noted in retro-notes). Not a blocking silent-swallow. |

No `except Exception: return ""`/`None`/`[]` silent-swallow anti-pattern found in mission code.

---

## Security Notes

No findings. The mission introduces no `shell=True`, no unbounded HTTP, no credential handling. Plugin-bundle `--fix` writes confined to a `dist/spec-kitty-plugins/` staging tree (no live agent dir, no network) — FR-016/C-006 prohibition enforced by negative-assertion tests (reproduced by injecting `marketplace_publish` → tests fail; revert → pass). Bundle file writes use `Path` joins anchored to the staging root.

---

## Final Verdict

**FAIL** (hard gate: Gate 2 Architectural).

### Verdict rationale
The mission's **functional delivery is sound** — all 18 FRs are adequately covered by live, schema-conformant code with real (non-synthetic) tests; the 7-provider registry is fully wired; backward-compat baselines are frozen; the FR-016/C-006 prohibition is enforced; locked decisions C-001/C-003/C-005 hold; and there are no security defects. **However**, the formal architectural hard gate (`tests/architectural/`, the repo-wide CI gate that the per-WP `tests/specify_cli/tool_surface/` suites do NOT run) fails with **four mission-caused regressions**: two orphaned dead modules (`builtins.py`, `providers/base.py`), dead public exports + a stale dead-code allowlist, 12 test files missing the `pytestmark` marker, and a CLI-reference parity gap for the new `doctor tool-surfaces` command. Per the hard-gate rule, any Gate-2 FAIL forces a FAIL verdict. These are all hygiene/CI-visibility issues — none affects runtime correctness — but they would fail CI's `integration-tests-core-misc` job and must be remediated in a follow-up before the mission is release-clean. None was documented as an accepted known issue prior to this review.

### Open items (remediation checklist for a follow-up)
1. Remove (or wire) the dead modules `tool_surface/builtins.py` and `tool_surface/providers/base.py`.
2. Drop `ToolSurfacePresence` / `GlobalCommandDirResolver` from `surface_presence.__all__` (or allowlist with rationale).
3. Remove the 4 now-wired symbols from `tests/architectural/test_no_dead_symbols.py::_SYMBOL_ALLOWLIST`.
4. Add `pytestmark` to the 12 new `tool_surface` test files.
5. Regenerate the CLI command reference to include `doctor tool-surfaces`.
6. (Pre-existing, not this mission) `test_runtime_charter_doctrine_boundary` failure — track separately.
7. (Already documented LOW debts) retire the duplicate `model.SurfaceFinding`; tighten WP09 plugin-bundle staging scope; consider surfacing the `managed_skills` unreadable-file edge.

## Remediation Addendum (2026-06-14, post-review)

All four mission-caused Gate-2 findings were remediated on `feat/tool-surface-contract` immediately after this review:
- **DRIFT-1** — deleted the orphaned `tool_surface/builtins.py` and `providers/base.py`; consolidated onto the single canonical `providers/protocol.ReportingSurfaceProvider` (repointed the 4 provider tests). (`463496de3`)
- **DRIFT-2 / RISK-1** — dropped `ToolSurfacePresence`/`GlobalCommandDirResolver` from `surface_presence.__all__`; removed the 4 now-wired entries from `_SYMBOL_ALLOWLIST`. (`1aa2ea949`)
- **RISK-2** — added the project-standard `pytestmark` to the 24 flagged `tool_surface` test files. (`1aa2ea949`)
- **DRIFT-3** — regenerated `docs/reference/cli-commands.md` via `scripts/docs/build_cli_reference.py`; `doctor tool-surfaces` now present. (`4dec7b375`)

**Post-remediation gate state**: the 4 targeted architectural tests PASS (7 tests); full `tests/architectural/` = **360 passed, 1 failed** (only the PRE-EXISTING `test_runtime_charter_doctrine_boundary`, unrelated to this mission); `tests/specify_cli/tool_surface/` = **220 passed** (−2 = the deleted dead-stub tests); ruff + mypy clean. **The mission is now CI-clean for everything it introduced.** The original verdict above is retained as the as-reviewed record; the effective post-remediation status is PASS (the one remaining architectural failure is pre-existing and tracked separately).

## Retrospective Reminder
The retrospective record exists at `.kittify/missions/01KV2K2P989VGC1TZF43ATGCPC/`-equivalent coord path (`kitty-specs/tool-surface-contract-01KV2K2P/retrospective.yaml`), authored via `retrospect create` (helped=8, not_helpful=11, gaps=5 after enrichment). Surface findings with `spec-kitty retrospect summary` and `spec-kitty agent retrospect synthesize --mission tool-surface-contract-01KV2K2P` (dry-run). The five architectural-gate findings above are strong candidates to add as retrospective gaps / a follow-up issue.
