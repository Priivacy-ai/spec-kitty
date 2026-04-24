# Runtime Extraction Remediation

**Mission ID**: `01KPX9DTTAADZW59PV51PQN658`
**Mission slug**: `runtime-extraction-remediation-01KPX9DT`
**Mission type**: `software-dev`
**Target branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
**Created**: 2026-04-23
**Trackers**: [#612 — Extract runtime/mission execution into a canonical functional module](https://github.com/Priivacy-ai/spec-kitty/issues/612)
**Parent mission**: `runtime-mission-execution-extraction-01KPDYGW` (mission #95)
**Review source**: [`docs/development/mission-095-post-merge-review.md`](../../docs/development/mission-095-post-merge-review.md)

---

## Primary Intent

Mission #95 (`runtime-mission-execution-extraction-01KPDYGW`) completed the structural extraction of `src/specify_cli/next/` and `src/specify_cli/runtime/` to a canonical top-level `src/runtime/` package. The post-merge review by Reviewer Renata identified two blocking findings that prevent the feature branch from merging to `main`:

1. **`src/runtime` is not registered in `pyproject.toml`** — the package cannot be imported in any installed environment (PyPI, `pip install`, non-editable installs). This makes the entire extraction non-functional for end users.

2. **Upgrade migration modules import from `runtime.*` paths** — six migration files were rewritten in WP09 to use `runtime.discovery.*` and `runtime.orchestration.*`. Because `runtime` is not a registered package, this causes `MigrationDiscoveryError` when `spec-kitty upgrade` is invoked in any installed environment.

This mission fixes both blocking findings and also resolves four additional source files that were missed by WP09's occurrence map (RISK-2 from the review). These are not blocking but prevent deprecation warning noise and are trivially co-located with the other fixes.

**Scope constraint**: No version bump (`pyproject.toml` version field stays untouched). This mission is purely a correctness fix for mission #95.

---

## User Scenarios & Testing

### Primary actors

- **Package users** — anyone who installs `spec-kitty-cli` from PyPI or via `pip install`.
- **Project operators** — anyone who runs `spec-kitty upgrade` after installing.
- **CI environments** — build pipelines that install from the package distribution and run tests.

### Acceptance scenarios

1. **Installed package imports runtime**
   - **Given** `spec-kitty-cli` is installed via `pip install spec-kitty-cli` (non-editable)
   - **When** `python -c "from runtime import PresentationSink"` is executed
   - **Then** the import succeeds; no `ModuleNotFoundError`.

2. **spec-kitty upgrade completes without MigrationDiscoveryError**
   - **Given** `spec-kitty-cli` is installed (editable or non-editable) with `runtime` registered
   - **When** `spec-kitty upgrade` is run
   - **Then** all migration modules are discovered successfully; no `MigrationDiscoveryError` for any `m_*` module.

3. **spec-kitty --version still works**
   - **Given** the pyproject.toml change is applied
   - **When** `spec-kitty --version` is run
   - **Then** the version string is displayed correctly; no import errors.

4. **Full test suite passes**
   - **Given** all changes from this mission applied
   - **When** `pytest tests/ --ignore=tests/auth -q` is run from the repo root
   - **Then** the test count is at or above the pre-mission baseline (no new failures introduced).

5. **Residual shim-path callers migrated**
   - **Given** the 4 source files with residual `specify_cli.runtime.*` imports are updated
   - **When** `rg "from specify_cli\.next|from specify_cli\.runtime" src/ -l` is run
   - **Then** only shim files (`src/specify_cli/next/` and `src/specify_cli/runtime/`) appear — no other `src/` files.

### Edge cases

- The `pyproject.toml` `packages` field accepts a list of paths; `"src/runtime"` must be added in the same format as existing entries.
- Upgrade migration modules must remain importable in both editable installs (where `src/` is on `sys.path`) and non-editable installs (where only the installed package tree is available). Using the shim path (`specify_cli.runtime.*`) satisfies both.
- The 4 residual callers (`mission.py`, `state/doctor.py`, `migration/rewrite_shims.py`, `cli/commands/agent/status.py`) use lazy imports inside functions in some cases — each file must be read before editing.

---

## Requirements

### Functional Requirements

| ID     | Requirement                                                                                                                                                                                   | Status    |
|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| FR-001 | `pyproject.toml` `packages` list includes `"src/runtime"` so the package is discoverable by setuptools/hatchling in all install modes.                                                       | Confirmed |
| FR-002 | `python -c "from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor"` succeeds in a non-editable installed environment after the change.                       | Confirmed |
| FR-003 | The six upgrade migration files (`m_2_0_6_consistency_sweep.py`, `m_2_0_7_fix_stale_overrides.py`, `m_2_1_3_restore_prompt_commands.py`, `m_2_1_4_enforce_command_file_state.py`, `m_3_1_2_globalize_commands.py`, `upgrade/compat.py`) are reverted to use `specify_cli.runtime.*` shim paths instead of `runtime.*` canonical paths. | Confirmed |
| FR-004 | `spec-kitty upgrade` runs without `MigrationDiscoveryError` in both editable and non-editable install environments.                                                                           | Confirmed |
| FR-005 | The four residual source callers (`src/specify_cli/mission.py`, `src/specify_cli/state/doctor.py`, `src/specify_cli/migration/rewrite_shims.py`, `src/specify_cli/cli/commands/agent/status.py`) are migrated from `specify_cli.runtime.*` to `runtime.*` canonical paths. | Confirmed |
| FR-006 | After all changes, `rg "from specify_cli\.(next\|runtime)" src/ -l` returns only files within `src/specify_cli/next/` and `src/specify_cli/runtime/` (the intentional shim directories). | Confirmed |

### Non-Functional Requirements

| ID      | Requirement                                                                                                                   | Status    |
|---------|-------------------------------------------------------------------------------------------------------------------------------|-----------|
| NFR-001 | The `pyproject.toml` version field is unchanged. No version bump is introduced by this mission.                               | Confirmed |
| NFR-002 | The full test suite (`pytest tests/ --ignore=tests/auth`) passes with no new failures relative to the pre-mission baseline.  | Confirmed |
| NFR-003 | All architectural boundary tests (`tests/architectural/`) continue to pass after the changes.                                 | Confirmed |
| NFR-004 | `spec-kitty --version` and `spec-kitty next --help` continue to work correctly after the pyproject.toml change.              | Confirmed |

### Constraints

| ID   | Constraint                                                                                                                                     | Status    |
|------|------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C-001 | No version bump in `pyproject.toml` — only the `packages` list is modified.                                                                    | Confirmed |
| C-002 | Upgrade migration modules **must** use `specify_cli.runtime.*` shim paths, not `runtime.*` canonical paths. Migrations are version-pinned and must remain importable in environments where `runtime` is not on `sys.path`. | Confirmed |
| C-003 | No changes to `src/runtime/` package files — those files are under mission #95 and are not owned by this mission.                              | Confirmed |
| C-004 | No changes to `src/specify_cli/next/` or `src/specify_cli/runtime/` shim files — those are mission #95 artifacts.                              | Confirmed |
| C-005 | Terminology canon applies: **Mission** (not "feature"), **Work Package** (not "task").                                                          | Confirmed |

---

## Success Criteria

1. **Package importable** — `from runtime import PresentationSink` succeeds in a non-editable `pip install` environment.
2. **Upgrade clean** — `spec-kitty upgrade` runs to completion without `MigrationDiscoveryError` in both editable and non-editable environments.
3. **Test suite stable** — full test suite passes with zero new failures.
4. **No residual shim-path callers** — `rg` scan returns no non-shim `src/` files importing from `specify_cli.next.*` or `specify_cli.runtime.*`.
5. **Blocking findings cleared** — DRIFT-1 and DRIFT-2 from `docs/development/mission-095-post-merge-review.md` are resolved; the review document's verdict changes from FAIL to PASS WITH NOTES.

---

## Key Entities

- **`pyproject.toml`** — the package build configuration; `packages` list must include `"src/runtime"`.
- **Upgrade migration modules** — version-pinned Python files under `src/specify_cli/upgrade/migrations/`; must use shim paths for runtime imports.
- **Shim path** — a `specify_cli.runtime.*` or `specify_cli.next.*` import path; always importable via the deprecation shim installed in mission #95.
- **Canonical path** — a `runtime.*` import path; only importable when `src/runtime` is registered in `pyproject.toml`.
- **Residual callers** — 4 source files in `src/specify_cli/` that were not migrated by WP09 and still use shim paths despite not being migration modules.

---

## Dependencies & Assumptions

### Upstream

- **Mission #95** (`runtime-mission-execution-extraction-01KPDYGW`) — must be at least on branch `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`; all WPs approved. The shims and `src/runtime/` package must be present before this mission's changes can be validated.

### Assumptions

- A1. The pyproject.toml build backend (hatchling or setuptools) uses the `packages` field in the `[tool.hatch.build.targets.wheel]` section; adding `"src/runtime"` to that list is sufficient for wheel builds.
- A2. The shim paths (`specify_cli.runtime.*`) are always importable in any environment where `spec-kitty-cli` is installed, regardless of whether `runtime` is on `sys.path`. This is guaranteed by the shim installation in mission #95 WP06.
- A3. The 4 residual caller files use only public symbols from `runtime.*` (no private `_`-prefixed symbols) — if private symbols are required, the canonical path is safe to use once FR-001 is satisfied.
- A4. **PyPI / non-editable install verification** (FR-002 scope): Full verification that `import runtime` works in a true non-editable (`pip install spec-kitty-cli`) environment is deferred to the release CI pipeline, not to this mission's WP acceptance gates. WP01 T002 verifies importability through the editable install with explicit package registration — sufficient to confirm the `pyproject.toml` change is correct. The CI pipeline catches any wheel-build discrepancies before a release tag is cut.

---

## Out of Scope

- Version bump or changelog additions for `pyproject.toml`.
- Fixing `RISK-1` (merge tooling data-loss pattern) — that requires a separate tooling mission.
- Fixing `RISK-3` (regression harness covers only 1 of 4 commands) — that requires re-registering the reference mission and recapturing snapshots; tracked separately.
- Fixing `RISK-4` (WP10 undeclared changes to `src/runtime/` files) — documentation/traceability only; no code change needed.
- Any changes to `src/runtime/` implementation files.
- Any new CLI commands, new arguments, or behaviour changes.

---

## Open Questions

None at spec time. All decisions are determined by the review findings:
- **pyproject.toml path format**: `"src/runtime"` — matches existing entries (`"src/kernel"`, `"src/specify_cli"`, etc.)
- **Migration revert scope**: All 6 files listed in FR-003 — confirmed by the `MigrationDiscoveryError` stack trace
- **Residual caller migration direction**: to `runtime.*` canonical paths (safe once FR-001 is satisfied, and correct per the occurrence-map completeness requirement of mission #95)
