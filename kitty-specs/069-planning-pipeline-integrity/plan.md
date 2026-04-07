# Implementation Plan: Planning Pipeline Integrity and Runtime Reliability

**Branch**: `main` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/069-planning-pipeline-integrity/spec.md`

---

## Summary

Fix four structural defects in spec-kitty's planning and runtime surfaces. All four are small, targeted changes to existing modules; the largest work item introduces a new `wps.yaml` manifest format and integrates it into `finalize-tasks`. No new dependencies required. All existing libraries (`pydantic`, `jsonschema`, `ruamel.yaml`) already present.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (YAML parsing), pydantic ≥2.0 (data models), jsonschema (Draft 2020-12 validation) — all present in `pyproject.toml`
**Storage**: Filesystem only (YAML, JSONL, Markdown, JSON)
**Testing**: pytest, mypy --strict, 90%+ coverage on new code (charter requirement)
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: CLI operations <2s; `materialize()` skip-write must not add perceptible latency
**Constraints**: No new required network calls; no changes to `spec-kitty-runtime` package (external); backwards compatibility for missions without `wps.yaml`

---

## Charter Check

Charter file: `.kittify/charter/charter.md` (version 1.1.0)

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | ✅ PASS | All new code targets 3.11+ |
| mypy --strict | ✅ PASS | All new functions will have full type annotations |
| 90%+ test coverage | ✅ PASS | Unit + integration tests planned for every changed function |
| CLI operations <2s | ✅ PASS | All changes are local I/O; no network calls added |
| pytest passing | ✅ PASS | No tests deleted; new tests added |
| ruamel.yaml for YAML parsing | ✅ PASS | `wps_manifest.py` will use ruamel.yaml |
| No new required network calls | ✅ PASS | Constraint C-004 satisfied |

No charter violations.

---

## Project Structure

### Planning artifacts (this feature)

```
kitty-specs/069-planning-pipeline-integrity/
├── spec.md                    # Feature specification
├── plan.md                    # This file
├── research.md                # Phase 0: code review findings and design decisions
├── data-model.md              # Phase 1: module contracts and data shapes
├── checklists/requirements.md # Spec quality checklist
└── tasks/                     # WP prompt files (created in /spec-kitty.tasks)
```

### Source code changes

```
src/specify_cli/
├── status/
│   ├── reducer.py             # MODIFY: deterministic materialized_at + skip-write guard
│   └── views.py               # MODIFY: materialize_if_stale() returns reduce() not materialize()
├── core/
│   ├── wps_manifest.py        # NEW: WpsManifest Pydantic model, loader, tasks.md generator
│   ├── dependency_parser.py   # NO CHANGE (legacy fallback, retained as-is)
│   └── mission_creation.py    # MODIFY: KEBAB_CASE_PATTERN + error message
├── cli/commands/agent/
│   └── mission.py             # MODIFY: finalize-tasks integrates wps.yaml tier 0
├── next/
│   ├── decision.py            # MODIFY: add DecisionKind.query, Decision.is_query field
│   ├── runtime_bridge.py      # MODIFY: add query_current_state() function
│   └── next_cmd.py (cli)      # MODIFY: result default None, query mode branch
├── schemas/
│   └── wps.schema.json        # NEW: published JSON Schema for wps.yaml
└── missions/software-dev/command-templates/
    ├── tasks-outline.md       # MODIFY: produce wps.yaml only (not tasks.md)
    └── tasks-packages.md      # MODIFY: read/update wps.yaml, generate WP files

tests/specify_cli/
├── status/
│   └── test_reducer.py        # ADD: deterministic materialized_at, skip-write tests
├── core/
│   └── test_wps_manifest.py   # NEW: full coverage of wps_manifest module
├── cli/commands/agent/
│   └── test_mission_finalize_tasks.py  # ADD: wps.yaml integration tests
├── next/
│   └── test_next_cmd.py       # ADD: query mode tests
└── core/
    └── test_mission_creation.py  # ADD: digit-prefix slug tests
```

---

## Work Packages

### WP01 — Fix status.json dirty-git (#524)
**Scope**: Make `materialize()` idempotent; fix `reduce()` non-determinism; fix `materialize_if_stale()`.
**Files**: `status/reducer.py`, `status/views.py`, `tests/specify_cli/status/test_reducer.py`
**Dependencies**: none
**Key changes**: See `data-model.md` §Modified Module reducer.py and views.py

### WP02 — Add wps_manifest module (#525 core)
**Scope**: New `wps_manifest.py` module with Pydantic model, YAML loader, tasks.md generator, and JSON Schema file.
**Files**: `core/wps_manifest.py` (new), `schemas/wps.schema.json` (new), `tests/specify_cli/core/test_wps_manifest.py` (new)
**Dependencies**: none
**Key changes**: See `data-model.md` §New Module wps_manifest.py and §New File wps.schema.json

### WP03 — Integrate wps.yaml into finalize-tasks (#525 integration)
**Scope**: Update `finalize-tasks` to use wps.yaml as tier 0; regenerate tasks.md from manifest when present.
**Files**: `cli/commands/agent/mission.py`, integration tests
**Dependencies**: WP02 (needs wps_manifest module)
**Key changes**: See `data-model.md` §finalize-tasks integration

### WP04 — Update tasks-outline and tasks-packages templates (#525 prompts)
**Scope**: Rewrite both command templates to produce/consume `wps.yaml` instead of `tasks.md` prose.
**Files**: `missions/software-dev/command-templates/tasks-outline.md`, `missions/software-dev/command-templates/tasks-packages.md`
**Dependencies**: WP02 (schema must exist before templates reference it)
**Key changes**: tasks-outline → output wps.yaml only; tasks-packages → update wps.yaml, still generate WP prompt files

### WP05 — Implement query mode for next (#526)
**Scope**: Change `result` default to `None`; add `query_current_state()`; add `DecisionKind.query`.
**Files**: `next/decision.py`, `next/runtime_bridge.py`, `cli/commands/next_cmd.py`, tests
**Dependencies**: none
**Key changes**: See `data-model.md` §Modified decision.py, §Modified runtime_bridge.py, §Modified next_cmd.py

### WP06 — Fix slug validator (#527)
**Scope**: One regex change + error message update in `mission_creation.py`.
**Files**: `core/mission_creation.py`, `tests/specify_cli/core/test_mission_creation.py`
**Dependencies**: none
**Key changes**: See `data-model.md` §Modified mission_creation.py

---

## Dependency Graph

```
WP01 ───────────────────────────────────────── (independent)
WP02 ────────────────────────────────────────── (independent)
           WP03 depends on WP02
           WP04 depends on WP02
WP05 ───────────────────────────────────────── (independent)
WP06 ───────────────────────────────────────── (independent)
```

Parallel execution possible:
- **Lane A**: WP01, WP05, WP06 (all independent of each other and of WP02/03/04)
- **Lane B**: WP02 → WP03, WP04 (WP03 and WP04 may run in parallel after WP02)

---

## Testing Strategy

### Unit tests (per WP)

**WP01**:
- `test_reduce_deterministic_materialized_at`: same events → same `materialized_at`
- `test_materialize_skips_write_when_unchanged`: two calls → only one write
- `test_materialize_writes_when_events_change`: new event → write occurs
- `test_reduce_empty_events_stable`: empty events → `materialized_at=""` consistently
- `test_materialize_if_stale_does_not_write`: call to `materialize_if_stale()` on clean repo → zero modified files in git tree

**WP02**:
- `test_load_wps_manifest_valid`: parses a valid wps.yaml → correct WpsManifest
- `test_load_wps_manifest_absent`: missing file → returns None
- `test_load_wps_manifest_invalid_schema`: malformed YAML → raises ValidationError with field name
- `test_load_wps_manifest_empty_deps_present`: `dependencies: []` in YAML → field_set includes "dependencies"
- `test_load_wps_manifest_deps_absent`: no `dependencies` key → field_set does NOT include "dependencies"
- `test_generate_tasks_md_preserves_wps`: generated tasks.md includes all WP titles, dep lines, subtask counts

**WP03**:
- `test_finalize_tasks_uses_wps_yaml_when_present`: wps.yaml takes precedence over tasks.md prose
- `test_finalize_tasks_deps_not_overwritten_when_present`: `WP05: dependencies: []` in wps.yaml → WP05 assigned no deps
- `test_finalize_tasks_regenerates_tasks_md`: after finalize, tasks.md content matches manifest
- `test_finalize_tasks_legacy_fallback`: no wps.yaml → prose parser used, behavior unchanged

**WP05**:
- `test_query_mode_does_not_advance`: state counter identical before/after bare call
- `test_query_mode_output_has_label`: output contains `[QUERY — no result provided, state not advanced]`
- `test_result_success_still_advances`: `--result success` retains advancing behavior
- `test_query_mode_json_output`: JSON output includes `"is_query": true`

**WP06**:
- `test_slug_accepts_digit_prefix`: `068-feature`, `001-foo` → no error
- `test_slug_rejects_uppercase`: `User-Auth` → raises MissionCreationError
- `test_slug_rejects_underscore`: `user_auth` → raises MissionCreationError
- `test_slug_rejects_empty`: `""` → raises MissionCreationError

### Integration tests

- SC-001 integration: `spec-kitty agent tasks status` on clean repo → `git status --porcelain` empty
- SC-002 integration: `finalize-tasks` with prose cross-references in WP05 prompt → WP05 deps unchanged
- SC-003 integration: `spec-kitty next --agent claude` without `--result` → step counter unchanged
- SC-004 integration: `spec-kitty agent mission create "068-feature-name"` → no slug error

---

## Backwards Compatibility

| Surface | Impact | Mitigation |
|---------|--------|-----------|
| `status.json` schema | `materialized_at` now reflects last event timestamp, not current time | Schema unchanged; field semantics are "when snapshot was computed" — a past timestamp is valid |
| `spec-kitty next` without `--result` | Previously advanced; now returns query response | Desired behavior change. Agents that relied on bare `next` advancing should add `--result success` |
| Missions without `wps.yaml` | `finalize-tasks` behavior completely unchanged | Legacy fallback always active when `wps.yaml` absent |
| Slug `123-fix` | Previously rejected; now accepted | Accept-side change only; existing valid slugs unaffected |

---

## Branch Contract (final)

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **branch_matches_target**: true

**Next command**: `/spec-kitty.tasks`
