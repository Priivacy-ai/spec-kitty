# Post-Merge Mission Review: runtime-mission-execution-extraction-01KPDYGW

**Reviewer**: Reviewer Renata  
**Profile directives**: DIRECTIVE_001, DIRECTIVE_024, DIRECTIVE_030, DIRECTIVE_032  
**Date**: 2026-04-23  
**Mission**: `runtime-mission-execution-extraction-01KPDYGW` (#95) — Runtime Mission Execution Extraction  
**Tracking issue**: [#612 — Extract runtime/mission execution into a canonical functional module](https://github.com/Priivacy-ai/spec-kitty/issues/612)  
**Baseline commit**: `eb32cf0a8118856de9a59eec2635ddda0b956edf`  
**HEAD at review**: `897c53df8`  
**Branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`  
**WPs reviewed**: WP01–WP11 (all approved; 119 files changed, 9,673 insertions, 4,129 deletions)

---

## Summary

The extraction of `src/specify_cli/next/` and `src/specify_cli/runtime/` to a canonical top-level `src/runtime/` package was implemented correctly in terms of module structure, boundary enforcement, shim installation, and documentation. Twelve of sixteen FRs are fully and adequately delivered. The mission **cannot merge to `main` as-is** due to two blocking findings that would break the installed package for every user.

---

## FR Coverage Matrix

| FR | Description | WP | Test evidence | Adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | Canonical runtime package at `src/runtime/` | WP02 | Unregistered-package architectural test | **PARTIAL** | **[DRIFT-1]** absent from pyproject.toml |
| FR-002 | Runtime owns decisioning/bridge/prompts/discovery/agents/orchestration | WP03/04 | 18 modules in `src/runtime/` | ADEQUATE | — |
| FR-003 | Step content stays in mission artefacts | WP03 | Implicit | ADEQUATE | — |
| FR-004 | CLI adapters are thin | WP05 | Diff confirms import-only change in next_cmd.py | ADEQUATE | 4 CLI files missed (RISK-2) |
| FR-005 | Shims have `__deprecated__` + `DeprecationWarning` | WP06 | Manual verification | ADEQUATE | — |
| FR-006 | Shims in registry, CI check passes | WP06 | shim-registry.yaml 14 entries; doctor passed | ADEQUATE | Post-merge hotfix needed (RISK-1) |
| FR-007 | Dependency rules in ownership manifest | WP07 | architecture/2.x/05_ownership_manifest.yaml | ADEQUATE | — |
| FR-008 | Pytestarch `TestRuntimeBoundary` enforces boundary | WP07 | 12 tests, 2.10 s | ADEQUATE | — |
| FR-009 | ProfileInvocationExecutor boundary alias | WP02 | `src/runtime/seams/profile_invocation_executor.py` | ADEQUATE | — |
| FR-010 | StepContractExecutor scaffold | WP02 | Protocol stub with TYPE_CHECKING guard | ADEQUATE | — |
| FR-011 | Regression fixtures captured pre-extraction | WP01 | 4 snapshot files present | **PARTIAL** | 3 of 4 are hand-crafted error docs (RISK-3) |
| FR-012 | Regression test asserts dict-equal post-extraction | WP08 | `test_runtime_regression.py` | **PARTIAL** | Only `next.json` asserts; 3 skip (RISK-3) |
| FR-013 | PresentationSink Protocol, no `rich.*` in runtime | WP02 | rg scan clean; boundary test clean | ADEQUATE | — |
| FR-014 | Migration documentation | WP11 | `docs/migration/runtime-extraction.md` (155 lines) | ADEQUATE | — |
| FR-015 | Occurrence map complete | WP01/09 | 45 files, 57 import lines documented | **PARTIAL** | 4 source files missed (RISK-2) |
| FR-016 | PR cites exemplar + ownership map slice | WP11 | CHANGELOG references charter exemplar | ADEQUATE | — |

**Legend**: ADEQUATE = test constrains the required behaviour; PARTIAL = test exists but uses synthetic fixture or skips cases; MISSING = no test found.

---

## Drift Findings

### DRIFT-1 — `runtime` package not registered in `pyproject.toml` *(CRITICAL — BLOCKING)*

**Type**: PUNTED-FR (invisible hole — FR-001 assumes importability; spec never stated it explicitly)  
**Spec reference**: FR-001 — "Canonical runtime package exists at `src/runtime/`"

**Evidence**:
```toml
# pyproject.toml
packages = ["src/kernel", "src/specify_cli", "src/doctrine", "src/charter"]
# src/runtime is absent
```
```
$ python -c "import runtime"
ModuleNotFoundError: No module named 'runtime'

$ importlib.util.find_spec('runtime')  →  None
```

**Analysis**: Any consumer of this mission who installs `spec-kitty-cli` from PyPI receives a broken installation. `from runtime import PresentationSink` raises `ModuleNotFoundError`. The architectural tests only pass because pytest adds `src/` to `sys.path` via the project's `conftest.py` — not because the package is properly installed. The spec said "canonical top-level package." A package that cannot be imported outside the development checkout is not canonical. Constraint C-006 ("no version bump — `pyproject.toml` stays untouched") was interpreted as "do not modify `pyproject.toml` at all," which prevented the necessary `"src/runtime"` addition to the `packages` list.

**Fix required**: Add `"src/runtime"` to `packages` in `pyproject.toml` before merging to `main`.

---

### DRIFT-2 — Upgrade migrations rewritten to `runtime.*` paths, breaking `spec-kitty upgrade` in installed environments *(HIGH — BLOCKING)*

**Type**: LOCKED-DECISION VIOLATION (spirit of C-001: no changes that alter runtime behaviour)  
**Spec reference**: C-001 — "Pure move + adapter conversion"; NFR-002 — "Zero regressions"

**Evidence**:
```
MigrationDiscoveryError: Failed to import migration module(s):
  m_0_12_0_documentation_mission: No module named 'runtime.discovery'
  m_0_6_7_ensure_missions: No module named 'runtime.discovery'
  m_2_0_6_consistency_sweep: No module named 'runtime.orchestration'
  m_2_0_7_fix_stale_overrides: No module named 'runtime.discovery'
  m_3_1_2_globalize_commands: No module named 'runtime.discovery'
  m_3_2_0a4_safe_globalize_commands: No module named 'runtime.discovery'
```

Before WP09 those migration files used `from specify_cli.runtime.home import ...` (shim — always importable). After WP09 they use `from runtime.discovery.home import ...` (requires `src/runtime` on `sys.path`). In an installed environment without DRIFT-1 fixed, `spec-kitty upgrade` will fail at migration discovery.

The WP09 prompt explicitly stated: *"Exercise extra caution: migrations are version-pinned and may run on arbitrary old project states."* The implementation did not honour this caution.

**Fix required**: Revert upgrade migration modules to shim paths (`from specify_cli.runtime.*`). These migrations should remain on shim paths until `pyproject.toml` registration is confirmed stable across all supported install paths. Alternatively, fix DRIFT-1 first and add an integration test that runs `spec-kitty upgrade` from an installed (not editable) environment.

---

## Risk Findings

### RISK-1 — Shim-registry data loss during merge required a manual hotfix *(MEDIUM)*

**Location**: `architecture/2.x/shim-registry.yaml`, commits `6bb1036a7` and `897c53df8`  
**Trigger condition**: Post-merge `git checkout HEAD -- src/ tests/` worktree-cleanup artefact

The 14-entry shim-registry was silently reduced to `shims: []` during the merge worktree cleanup. The error was caught and corrected via a manual restore from the lane-a commit, but two churn commits are now visible in the mission history. The risk is that a future mission with the same merge pattern may not detect this data loss. The merge tooling (`spec-kitty merge`) should be hardened against stale index artefacts for files outside `src/` and `tests/`.

---

### RISK-2 — 4 source files still on shim import paths (occurrence map incomplete) *(MEDIUM)*

**Location**:
- `src/specify_cli/mission.py:L?` — `from specify_cli.runtime.resolver import resolve_command` (lazy)
- `src/specify_cli/state/doctor.py` — `from specify_cli.runtime.home import get_kittify_home` (module-level + lazy)
- `src/specify_cli/migration/rewrite_shims.py` — `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root`
- `src/specify_cli/cli/commands/agent/status.py` — `from specify_cli.runtime.doctor import run_global_checks`

FR-015 requires the occurrence map to enumerate "every internal caller." These 4 files were not migrated by WP09. They produce `DeprecationWarning` on every invocation and will become `ModuleNotFoundError` at 3.4.0 shim removal unless addressed. Not blocking for the current release window, but must be tracked.

---

### RISK-3 — Regression harness covers only 1 of 4 commands meaningfully *(MEDIUM)*

**Location**: `tests/regression/runtime/test_runtime_regression.py`

Three of four snapshots (`implement.json`, `review.json`, `merge.json`) were captured as hand-crafted error documentation containing an operator `"note"` key — not raw CLI `--json` output. The test harness detects this and calls `pytest.skip`. FR-012 ("regression test asserts post-extraction `--json` output matches fixtures") is effectively satisfied only for `spec-kitty next`. The other three commands — which exercise most of `RuntimeBridge` — have no regression coverage. A silent behavioural change to `spec-kitty agent action implement --json` would pass all tests.

**Fix required**: Re-capture `implement.json`, `review.json`, and `merge.json` using a properly registered reference mission where those commands produce real `--json` output.

---

### RISK-4 — WP10 made undeclared semantic changes to `src/runtime/` source files *(LOW)*

**Location**: `src/runtime/decisioning/decision.py`, `src/runtime/bridge/runtime_bridge.py`, `src/runtime/prompts/builder.py`  
**DIRECTIVE_024**: Locality of Change — changes must stay within the task's declared owned_files

WP10's `owned_files` declared `tests/**` only. WP10's own summary states it "fixed pre-existing source bugs in `src/runtime/`… lazy imports using old shim path." These changes were functionally correct but were performed outside WP10's declared scope and were never reviewed under WP03's acceptance criteria (which owned those files). The traceability gap means the WP03 review never assessed the final state of those files.

---

## Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|---|---|---|---|
| `test_runtime_regression.py` | Snapshot contains `"note"` key | `pytest.skip` | FR-012: 3 of 4 regression cases never assert |
| Upgrade migrations (after WP09) | `runtime.discovery` not on path | `MigrationDiscoveryError` at upgrade time | DRIFT-2: `spec-kitty upgrade` fails in installed environments |

---

## Security Notes

No new subprocess calls, authentication, or network operations were introduced. Path operations in `runtime.discovery.home` and `runtime.discovery.resolver` are direct copies of pre-extraction code with no semantic changes. **No security findings.**

---

## Final Verdict

**FAIL — 2 blocking findings must be resolved before merging to `main`**

| Finding | Severity | Blocking? |
|---|---|---|
| DRIFT-1: `runtime` not in `pyproject.toml` | CRITICAL | **Yes** |
| DRIFT-2: Upgrade migrations use `runtime.*` paths, break in installed envs | HIGH | **Yes** |
| RISK-1: Shim-registry merge data-loss pattern | MEDIUM | No |
| RISK-2: 4 source files still on shim paths | MEDIUM | No |
| RISK-3: Regression harness covers 1 of 4 commands | MEDIUM | No |
| RISK-4: WP10 undeclared changes to `src/runtime/` | LOW | No |

### Required before `main` merge

1. Add `"src/runtime"` to `packages` in `pyproject.toml`
2. Revert upgrade migration modules to `specify_cli.runtime.*` shim paths (or add a full integration test for installed-environment upgrade)
3. Verify `spec-kitty upgrade` succeeds end-to-end in a non-editable install

### Recommended follow-up missions

1. Re-capture regression snapshots for `implement`, `review`, `merge` commands (FR-011/FR-012 completion)
2. Migrate the 4 remaining shim-path source callers (FR-015 completion)
3. Harden `spec-kitty merge` against stale-index worktree cleanup data loss (RISK-1)
