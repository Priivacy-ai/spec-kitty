# Implementation Plan: Pack-Path Portability & Language-Scope Authority

**Branch**: `issue/2437-env-var-pack-paths` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/pack-path-env-indirection-01KWY79W/spec.md`

## Summary

Two independent, code-grounded fixes in the doctrine/charter config-resolution domain, folded into one mission as two independent work packages (WP1, WP2) per the pre-spec investigation squad's unanimous recommendation:

- **WP1 (#2437)**: Add env-var indirection (`${SPEC_KITTY_PACK_HOME}/...`) to `OrgPackConfig` pack-path resolution, composing correctly with the existing tilde-expansion, symlink-containment, and legacy-shape support. Expansion happens at `effective_root()` resolution time; the stored config value stays a literal template so it survives a save→load round-trip.
- **WP2 (#2395)**: Replace the interview-first language-inference precedence with a compile-time-persisted, structured language set on the compiled charter (DIRECTIVE_044 unification), so runtime never re-derives from the raw interview transcript once a compiled value exists.

## Technical Context

**Language/Version**: Python 3.11+ (matches project `pyproject.toml` `target-version = "py311"`)
**Primary Dependencies**: `pydantic` (v2, `field_validator`/`model_validator` — already used by `OrgPackConfig`), `ruamel.yaml` (existing config read/write), stdlib `os.path.expandvars` / `os.path.expanduser`
**Storage**: Filesystem config files — `.kittify/config.yaml` (WP1), `.kittify/charter/charter.md` + a new structured sidecar/section for the compiled language set (WP2). No database.
**Testing**: `pytest`, existing project convention (`tests/doctrine/`, `tests/charter/`, `tests/integration/`); `pytest.mark.fast` / `pytest.mark.doctrine` / `pytest.mark.integration` markers per existing test files in each area.
**Target Platform**: Cross-platform CLI (macOS/Linux/Windows) — no platform-specific behavior beyond existing `PurePosixPath`/`PureWindowsPath` handling already present in `org_pack_config.py`.
**Project Type**: Single project (Python CLI package `spec-kitty-cli`, existing `src/` layout).
**Performance Goals**: N/A beyond NFR-001 (no measurable latency added — both changes are pure string/path/regex operations, no new I/O).
**Constraints**: See spec C-001–C-005 (independent WPs, `#2213` out of scope, locked env-var name/fail-closed behavior/unification depth).
**Scale/Scope**: Two focused, single-module changes (`src/doctrine/drg/org_pack_config.py` for WP1; `src/charter/language_scope.py` + `src/charter/compiler.py` + `src/charter/context.py`/`compact.py` call sites for WP2). No new services, no new external dependencies.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Relevant governing principles and how this plan satisfies them:

| Principle / Directive | How this plan complies |
|---|---|
| **Single canonical authority** (Governing Principles; DIRECTIVE_044) | WP1: one resolution seam (`effective_root()`) covers canonical `doctrine.org.packs[].local_path` and legacy `organisation_packs[].path` — no parallel expansion logic. WP2: unifies runtime language resolution onto the compile-time-persisted artifact instead of adding a second runtime-only branch. |
| **Architectural alignment** (DIRECTIVE_001; shared-package-boundary ADR) | WP1 stays inside `src/doctrine/drg/` (already the shared contract module per its own docstring, consumed by both `charter.*` and `specify_cli.*`). WP2 stays inside `src/charter/` and does not introduce a `specify_cli` → `charter` or `charter` → `specify_cli` import violation. |
| **Close defect classes by construction** (DIRECTIVE_043) | WP1: storing the literal template (not the expanded path) makes the round-trip-corruption defect structurally impossible, not just documented. WP2: persisting a structured field at compile time removes the re-derivation branch entirely rather than reordering it. |
| **Test-first / red-first discipline** (DIRECTIVE_034; test-remediation standing order) | WP2's existing pinning test (`test_infer_repo_languages_prefers_interview_answers`) must be run RED against the corrected behavior first, confirming it currently encodes the bug, before being inverted — per the debugger lens's live reproduction. |
| **Boy Scout Rule / locality of change** (DIRECTIVE_025, DIRECTIVE_024) | Both WPs are scoped to their existing home modules; no opportunistic refactor of unrelated code. |

No violations requiring Complexity Tracking. Charter Check re-confirmed after Phase 1 design below — no new gaps introduced by the data-model/contracts artifacts.

## Project Structure

### Documentation (this mission)

```
kitty-specs/pack-path-env-indirection-01KWY79W/
├── spec.md              # Committed
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md         # Phase 1 output
├── checklists/requirements.md
├── decisions/           # DM-* decision records (env-var name, fail-closed, unification depth)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created here)
```

No `contracts/` directory: neither WP exposes a new HTTP/CLI-argument surface requiring an OpenAPI/schema contract. WP1 is a config-parsing behavior change; WP2 is an internal resolution-precedence change. Both are covered by `data-model.md` (value objects / structured fields) instead.

### Source Code (repository root)

```
src/
├── doctrine/
│   └── drg/
│       └── org_pack_config.py     # WP1 — OrgPackConfig, effective_root(), _expand_tilde (renamed/extended)
├── charter/
│   ├── language_scope.py          # WP2 — infer_repo_languages() resolution seam
│   ├── compiler.py                # WP2 — persist structured language set at compile time
│   ├── context.py                 # WP2 — active_languages consumer (read path only, no logic change expected)
│   └── compact.py                 # WP2 — display-only consumer (read path only)

tests/
├── doctrine/
│   ├── test_org_pack_subdir.py           # WP1 — extend with env-var expansion + round-trip cases
│   └── drg/test_org_pack_auto_emit.py    # WP1 — verify no DRG-wiring regression
├── specify_cli/doctrine/test_config.py   # WP1 — legacy shape coverage
├── integration/
│   ├── test_org_pack_missing_path_hard_fails.py  # WP1 — extend for unset-env-var fail-closed case
│   └── test_org_pack_subdir_e2e.py               # WP1 — regression
└── charter/
    └── test_language_scope.py     # WP2 — invert pinning test; add disagreement + structured-field cases
```

**Structure Decision**: Single project, no new top-level directories. Both WPs extend existing modules and existing test files in place; this preserves the "single canonical authority" seam per module (one `OrgPackConfig`, one `infer_repo_languages` resolution path) rather than introducing parallel implementations.

## Complexity Tracking

*No Charter Check violations identified — this section is not applicable.*

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` will translate these into executable WPs — expected to map roughly 1:1 given the squad's independence finding (C-001), but the tasks phase makes that determination.

### IC-01 — Pack-path env-var indirection (WP1 / #2437)

- **Purpose**: Make `OrgPackConfig.local_path` portable across machines/CI via `${VAR}`/`$VAR` expansion, without corrupting the stored config on save and without weakening the `subdir` containment guard.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-001, C-003, C-004.
- **Affected surfaces**: `src/doctrine/drg/org_pack_config.py` (`OrgPackConfig._expand_tilde` → generalize or relocate; `effective_root()`; `_pack_to_yaml_dict`/`save_pack_registry` round-trip path); `tests/doctrine/test_org_pack_subdir.py`; `tests/specify_cli/doctrine/test_config.py`; `tests/integration/test_org_pack_missing_path_hard_fails.py`.
- **Sequencing/depends-on**: none (independent of IC-02).
- **Risks**: The round-trip re-freeze hazard (architect + debugger lenses both confirmed `_pack_to_yaml_dict` re-serializes `str(local_path)`) — the design must store the literal template and expand only at `effective_root()`, not inside the field validator, or the fix will silently self-defeat on first save. The `subdir` no-`..`/no-absolute guard must not receive expansion (scope to `local_path` only).

### IC-02 — Charter-authoritative language-scope resolution (WP2 / #2395)

- **Purpose**: Eliminate the DIRECTIVE_044 split-brain where language extraction runs at both compile time (canonical, from interview) and runtime (re-derivation from the raw transcript), by persisting a structured language set on the compiled charter and making runtime read that value.
- **Relevant requirements**: FR-008, FR-009, FR-010, FR-011, FR-012, NFR-002, C-005.
- **Affected surfaces**: `src/charter/compiler.py` (persist structured `languages` at compile time); `src/charter/language_scope.py` (`infer_repo_languages` reads the compiled value first, interview transcript only as pre-compile fallback); `src/charter/context.py` (`active_languages` consumer — read path); `src/charter/compact.py` (display consumer — read path); `tests/charter/test_language_scope.py` (invert `test_infer_repo_languages_prefers_interview_answers`; add disagreement case; add structured-field case).
- **Sequencing/depends-on**: none (independent of IC-01).
- **Risks**: Existing pinning test currently asserts the buggy behavior — must be corrected (not deleted) per DIRECTIVE_034/041, with a red-first run to confirm the current behavior before flipping. Backward compatibility for charters compiled before this change (no structured field yet) requires the FR-010 fallback path.
