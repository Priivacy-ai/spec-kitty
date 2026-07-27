---
work_package_id: WP02
title: Profile-projection diagnostics & manifest provenance (#1940)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
tracker_refs:
- '1940'
planning_base_branch: feat/tool-surface-contract-residuals
merge_target_branch: feat/tool-surface-contract-residuals
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract-residuals unless the human explicitly redirects the landing branch.
created_at: '2026-06-15T05:20:00+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:opus:python-pedro:implementer"
shell_pid: "3963702"
history:
- date: '2026-06-15'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/findings.py
- src/specify_cli/tool_surface/profiles/**
- tests/specify_cli/tool_surface/profiles/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: **python-pedro**, role: implementer) before anything else. Then return here.

## Objective

Close #1940: implement the **four mandated finding codes** and the **three manifest provenance fields** that PR #1948 specified in `data-model.md` but never landed in code. Canonical vocabulary source: `kitty-specs/tool-surface-contract-01KV2K2P/data-model.md` and this mission's [data-model.md](../data-model.md) + [contracts/profile-findings-and-manifest.md](../contracts/profile-findings-and-manifest.md). **Do not re-invent names** (C-004, DIRECTIVE_010). Governed by `generated-code-stewardship` — the manifest/projection are generated artifacts: keep additions typed, explained, reviewable.

## Context

- `findings.py` currently defines only 3 of 7 profile codes (`native-agent-profile-missing`, `native-agent-profile-drift`, `profile-projection-unsupported`). The 4 missing: `profile-source-invalid`, `profile-name-invalid`, `profile-overlay-conflict`, `profile-sentinel-skipped`.
- `profiles/manifest.py` serializes 6 fields; add `source_path`, `source_hash`, `projection_version` → 8.
- Emit sites live in `profiles/projection.py` (overlay resolution, sentinel skip, source validation) and `profiles/renderers.py` (native-format name validation).

## Subtasks (ATDD — tests first)

### T005 — RED: one focused test per new finding code (drive the CONDITION, not the constant)
In `tests/specify_cli/tool_surface/profiles/` (source→test map: source-invalid/overlay/sentinel → `test_projection.py`; name-invalid → `test_renderers.py`), each test must **construct the real triggering input and assert the code appears in the emitted `SurfaceFinding` list** — NOT `assert findings.PROFILE_SOURCE_INVALID == "..."` (a dead-constant assertion that passes while the emit site is never wired — the exact #1940 silent-drop gap):
- `profile-source-invalid` — feed a canonical profile YAML that fails schema/`AgentProfileRepository` validation → assert emitted.
- `profile-name-invalid` — a profile id/name illegal for the target native format (illegal chars for `.claude/agents/<id>.md`) → assert emitted.
- `profile-overlay-conflict` — two overlay layers claiming the same id incompatibly → assert emitted.
- `profile-sentinel-skipped` — a sentinel/internal profile → assert it is **recorded** as an info finding (never a silent/no-op skip).

### T006 — Add the 4 finding-code constants to `findings.py`
Append-only kebab-case constants matching the contract values. **Do not rename** the existing 3 profile codes.

### T007 — Emit each code at its triggering condition
Wire emission in `profiles/projection.py` + `profiles/renderers.py`:
- source-invalid on validation failure; name-invalid on format-name check; overlay-conflict in overlay resolution; sentinel-skipped on sentinel detection (info, recorded).
- Each finding carries `repair_command` where one applies (per the existing `SurfaceFinding` shape).

### T008 — Manifest provenance (8 fields, SAFE backward-read)
In `profiles/manifest.py` add `source_path`, `source_hash`, `projection_version` to the entry dataclass + serializer + loader. The current loader uses direct `raw["..."]` access — read the **new** keys via `raw.get(...)` with an explicit absent→default (legacy 6-field entries currently KeyError otherwise). **No `except`-swallowing** to "handle" legacy reads (violates the no-empty-except rule and corrupts provenance silently). `source_hash` (source YAML changed) must be independently detectable from `file_hash` (output edited).

### T009 — Provenance + legacy-read tests (real fixtures)
- Round-trip: `load(save(8-field)) == entry`.
- **Named legacy fixture**: `load(<a real 6-field JSON>)` returns a populated entry with `source_path is None` (not a crash, not a swallowed None-entry).
- Exercise the two-hash distinction: one test where the source changed but output didn't, and one the reverse — assert the correct drift signal each way (otherwise the `source_hash`/`file_hash` split is decorative).
- Full `tests/specify_cli/tool_surface/profiles/` green; ruff + mypy --strict clean.

## Branch Strategy

Planning/merge branch: **`feat/tool-surface-contract-residuals`** (PR → `main`). Lane worktree from `lanes.json`. `safe-commit --to-branch feat/tool-surface-contract-residuals`; status transitions from primary CWD.

## Definition of Done

- All 4 codes emit under their conditions (per-code tests green); existing 3 codes unchanged.
- Manifest entries carry all 8 fields; legacy 6-field manifests still load.
- `doctor tool-surfaces --kind agent-profile --json` surfaces the new codes (manual quickstart check).
- ruff + mypy --strict clean; #1940 acceptance criteria met.

## Risks

- Finding codes are **append-only / stable** — renaming the existing 3 is a regression.
- Manifest schema change must not break existing `.kittify/agent-profiles-manifest.json` consumers (backward-read-compat is a hard requirement).

## Reviewer Guidance

Recommended reviewer: **reviewer-renata** (standard). Verify each code emits at the right condition (not collapsed into a generic code), the 8-field manifest round-trips AND reads legacy 6-field entries, and names match `data-model.md` verbatim. Resolves **#1940** → terminal issue-matrix verdict (`fixed`).

## Activity Log

- 2026-06-15T06:04:59Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – Assigned agent via action command
- 2026-06-15T06:17:50Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – Emit-tests per code (assert code in emitted SurfaceFinding list, not dead-constant): source-invalid via repo.skipped_profiles() (invalid project YAML); overlay-conflict via id loaded(builtin)+skipped(project) across layers (architect-alphonso); name-invalid via illegal native filename id (bad/slash) through native_name_violation; sentinel-skipped via human-in-charge recorded as info (never silent). Manifest: 8-field round-trip lossless; named legacy 6-field fixture loads to populated entry with source_path/source_hash/projection_version=None (raw.get defaults, no except-swallow); two-hash distinction tested both directions (source changed/output stable; output edited/source stable). Gates: ruff clean, mypy --strict clean (10 files src+tests), 47/47 profiles tests green. Existing 3 codes unchanged; codes match contract verbatim. One justified out-of-map edit: model.py NativeAgentProfile +3 optional provenance fields (None defaults) required for manifest serialization. Pre-existing unrelated failure (not mine, fails on WP01 base): integration/test_migration_compat.py::test_doctor_skills_json_error_schema_stable.
- 2026-06-15T06:18:40Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3930336 – Started review via action command
- 2026-06-15T06:27:22Z – user – shell_pid=3930336 – Moved to planned
- 2026-06-15T06:28:04Z – claude:opus:python-pedro:implementer – shell_pid=3963702 – Started implementation via action command
