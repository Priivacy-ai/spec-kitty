# Implementation Plan: ToolSurfaceContract Residual Closeout

**Branch**: `feat/tool-surface-contract-residuals` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/tool-surface-contract-residuals-01KV4S5B/spec.md`

## Summary

Close the four verified spec→code gaps that PR #1948 left in epic #1945: (1) the four missing native-profile-projection finding codes + three manifest provenance fields (#1940), (2) registry-backed `SKILL_ONLY_AGENTS`/`VALID_AGENTS` (#1941), (3) an actually-CI-enforced docs-contract lint (#1942), and (4) the user-facing migration guide + a deterministic `doctor skills` error-schema test (#1944/#1965). Four largely independent lanes over an ATDD-first protection suite; backward-compat (frozen `doctor skills --json` + `agent config` interfaces) is a hard gate throughout.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), pydantic v2 (tool_surface frozen models), pytest (markers: `fast`/`integration`/`unit`/`git_repo`); GitHub Actions (`.github/workflows/ci-quality.yml`, `dorny/paths-filter` shards); `spec-kitty-events`/`spec-kitty-tracker` external deps — **unchanged**.
**Storage**: JSON manifests under `.kittify/` (`agent-profiles-manifest.json`, `command-skills-manifest.json`, `skills-manifest.json`); doctrine/docs files.
**Testing**: pytest, ATDD-first (DIRECTIVE_034); `ruff` + `mypy --strict` on new/touched code; `diff-cover` changed-line coverage; backward-compat pinned by frozen baselines (`test_doctor_skills_*`, `test_agent_config_compat.py`).
**Target Platform**: Linux/macOS dev + CI (GitHub Actions Ubuntu runners).
**Project Type**: single (CLI tool / `src/specify_cli/` + `src/specify_cli/tool_surface/`).
**Performance Goals**: inherit NFR-001 from #1948 — `doctor tool-surfaces` ≤5s across configured tools (no regression).
**Constraints**: backward-compat frozen interfaces (NFR-001); complexity ≤15; zero `feature*` aliases (NFR-003); the #1942 gate MUST be collected by a real CI shard and fail on drift (NFR-004); the #1965 `locate_project_root` change must not alter resolution for real `.kittify/` projects (C-003).
**Scale/Scope**: 4 residual work-streams; ~6–8 source/test files + 1 docs page + 1 CI-workflow edit.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Terminology Canon (DIRECTIVE_032 / NFR-003):** Tool / Agent / Tool Surface kept distinct; `ToolSurfaceContract` naming; no `feature*` aliases. ✅ enforced by `tests/architectural/test_no_legacy_terminology.py`.
- **Shared Package Boundary:** no edits to `spec_kitty_events`/`spec_kitty_tracker` (consumed via public imports only). ✅ none planned.
- **Test & Typecheck Quality Gate (DIRECTIVE_030):** ruff + mypy --strict clean; new branches/helpers get focused tests in the same WP. ✅ planned.
- **Specification Fidelity (DIRECTIVE_010) / C-004:** implement the canonical finding-code + manifest vocabulary already specified in `kitty-specs/tool-surface-contract-01KV2K2P/data-model.md`; do not re-invent. ✅ confirmed in research.
- **Sonar:** complexity ≤15; repeated literals → constants; no effect-free except handlers. ✅ planned.

No charter violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/tool-surface-contract-residuals-01KV4S5B/
├── plan.md              # This file
├── research.md          # Phase 0 — the 4 resolved plan decisions
├── data-model.md        # Phase 1 — finding-code + manifest-field deltas
├── quickstart.md        # Phase 1 — per-work-stream validation scenarios
├── contracts/           # Phase 1 — profile-findings + manifest schema contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── tool_surface/
│   ├── findings.py                 # IC-01: add 4 profile finding-code constants
│   ├── profiles/
│   │   ├── manifest.py             # IC-01: +source_path/source_hash/projection_version
│   │   ├── projection.py           # IC-01: emit the 4 finding codes at their conditions
│   │   └── renderers.py            # IC-01: name/format validation feeding profile-name-invalid
│   └── docs.py                     # IC-03: docs-contract linter (already correct)
├── cli/commands/agent/config.py    # IC-02: registry-backed SKILL_ONLY_AGENTS/VALID_AGENTS
└── core/paths.py                   # IC-04: locate_project_root SPECIFY_REPO_ROOT authority

tests/specify_cli/tool_surface/
├── providers/ profiles/            # IC-01 + IC-00 tests (per-finding-code)
└── test_docs.py                    # IC-03: re-mark unit→integration (+ adversarial drift test)

.github/workflows/ci-quality.yml    # IC-03: add tool_surface path-filter to a shard
docs/ (how-to or migration)         # IC-04: user-facing Tool-vs-Agent upgrade guide
```

**Structure Decision**: Single-project CLI. All code changes live in the existing `tool_surface` bounded context, `cli/commands/agent/config.py`, and `core/paths.py`; one CI-workflow edit; one docs page. No new packages.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-00 — Backward-compat + adversarial protection suite (ATDD-first)

- **Purpose**: Author/verify the protection net FIRST so every later lane is change-detected: the frozen `doctor skills --json` baseline + `agent config` compat tests stay green, and the #1942 adversarial negative test (injected docs drift → CI fails) is written before the wiring. **Folded-in pre-refactor (FOLD-PRE, pre-tasks scan):** delete the dead duplicate `model.SurfaceFinding` (`tool_surface/model.py:62-72`, ~11 LOC) + its stale 7-field test in `test_model.py` (~14 LOC) — zero live importers (all live reporting uses `findings.SurfaceFinding`); removing it clears the type-name ambiguity *before* IC-01 adds new finding codes (#1948 documented this dead dup; campsite-cleaning per spec delivery stance).
- **Relevant requirements**: NFR-001, NFR-004, DIRECTIVE_034, `atdd-adversarial-acceptance`, `formalized-constraint-testing`, `dead-weight-elimination`.
- **Affected surfaces**: `tests/specify_cli/.../test_doctor_skills_*`, `test_agent_config_compat.py`, new `tests/specify_cli/tool_surface/test_docs.py` adversarial case, `tool_surface/model.py` (+ `test_model.py` trim).
- **Sequencing/depends-on**: none (first).
- **Risks**: must not weaken what the frozen tests assert; the negative test must fail for the right reason (unregistered path), not incidental error; `test_model.py` must drop the stale `SurfaceFinding` test or it won't compile after the deletion.

### IC-01 — Native profile-projection diagnostics + manifest provenance (#1940)

- **Purpose**: Implement the 4 mandated finding codes (`profile-source-invalid`, `profile-name-invalid`, `profile-overlay-conflict`, `profile-sentinel-skipped`) at their triggering conditions, and add the 3 missing manifest fields (`source_path`, `source_hash`, `projection_version`) → full 8-field provenance, per the canonical `data-model.md`.
- **Relevant requirements**: FR-001, FR-002; DIRECTIVE_010, `generated-code-stewardship`.
- **Affected surfaces**: `src/specify_cli/tool_surface/findings.py`, `profiles/manifest.py`, `profiles/projection.py`, `profiles/renderers.py`; tests under `tests/specify_cli/tool_surface/profiles/`.
- **Sequencing/depends-on**: IC-00 (tests-first).
- **Risks**: manifest schema change must round-trip (load old 6-field entries gracefully / migrate); finding codes are append-only (don't rename the existing 3).

### IC-02 — Registry-backed agent-config sets (#1941)

- **Purpose**: Derive `SKILL_ONLY_AGENTS` from `command_installer.SUPPORTED_AGENTS` (single source) and keep `VALID_AGENTS` a derived union, eliminating the duplicated tool-universe literal — with byte-identical `agent config` accept/reject. **Folded-in (pre-tasks scan):** the scan found a *third* copy — `command_renderer.SUPPORTED_AGENTS` (`skills/command_renderer.py:38`), byte-identical and independently declared; fold its dedup (1-line import from `command_installer`) into this lane so all three co-owners collapse to one authority (no import cycle — both live in `specify_cli.skills`).
- **Relevant requirements**: FR-003, FR-004; `connascence-analysis`, `redundancy-discovery`, DIRECTIVE_001/024, NFR-001.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/config.py`, `src/specify_cli/skills/command_renderer.py`; `tests/.../test_agent_config*.py` (+ "configured Claude with session presence" scenario).
- **Sequencing/depends-on**: IC-00.
- **Risks**: import-cycle risk pulling `command_installer` into `config.py` (verify no cycle; the existing `_register_skill_agent` lazy-import shows a cycle may exist — if so, keep a module-load helper); values must stay identical (frozen compat test).

### IC-03 — Docs-contract lint CI enforcement (#1942)

- **Purpose**: Make the docs-lint a CI-collected fail-on-drift gate: re-mark `test_docs.py` (`unit`→`integration`) AND add a `tool_surface` path-filter entry so an `integration`-collecting shard runs it; prove with the IC-00 adversarial test.
- **Relevant requirements**: FR-005; `quality-gate-verification`, `atdd-adversarial-acceptance`, DIRECTIVE_030.
- **Affected surfaces**: `tests/specify_cli/tool_surface/test_docs.py` (marker), `.github/workflows/ci-quality.yml` (paths-filter + shard mapping).
- **Sequencing/depends-on**: IC-00 (adversarial test exists first).
- **Risks**: marker change must land the test in a shard whose `-m` selector includes it; verify the shard's path-filter + marker combination actually collects it (don't trade one invisibility for another).

### IC-04 — Migration guide + deterministic path resolver (#1944/#1965)

- **Purpose**: Ship the user-facing Tool-vs-Agent upgrade/repair guide under `docs/` (lint-clean, TOC-discoverable); fix `locate_project_root` so `SPECIFY_REPO_ROOT` is authoritative when the path exists (drop the `.kittify/`-present precondition at `paths.py:79`), making `test_doctor_skills_json_error_schema_stable` deterministic without weakening its frozen schema assertion.
- **Relevant requirements**: FR-006, FR-007; DIRECTIVE_037 Living Documentation Sync, DIRECTIVE_034, `formalized-constraint-testing`.
- **Affected surfaces**: `docs/` (new guide + TOC/inventory), `src/specify_cli/core/paths.py`, the doctor-skills test.
- **Sequencing/depends-on**: IC-00.
- **Risks**: the `paths.py` change must not alter resolution for real `.kittify/` projects (they hit the same `get_main_repo_root(env_path)` path) — keep the `env_path.exists()` guard. **Split-brain note (pre-tasks scan):** there are *three* `locate_project_root` definitions — `paths.py` (full: env-var + worktree, 26 callers), `project_resolver.py` (simple `.kittify` walk, no env-var; 4 callers incl. `cli/commands/lint.py` + `cli/helpers.py`), and `__init__.py` (delegates to `project_resolver`). This mission fixes **only `paths.py`** (the doctor/#1965 path); full consolidation is deferred to **#1971** (C-003 + import-cycle risk). The IC-04 WP must explicitly confirm the 4 `project_resolver` callers don't depend on env-var/worktree authority, so a reviewer doesn't block IC-04 for incomplete consolidation.

## Pre-tasks scan outcome (foldable defects & deferred debt)

A randy-reducer split-brain/LOC scan + tracker search ran before task decomposition (per operator request):

- **Folded into this mission:** dead `model.SurfaceFinding` deletion → IC-00; `command_renderer.SUPPORTED_AGENTS` dedup → IC-02. Both are same-surface campsite-cleaning consistent with the spec's delivery stance.
- **Deferred to separate tickets (out of scope here):**
  - **#1971** — full 3-way `locate_project_root` consolidation (too risky for C-003; this mission fixes only the `paths.py` tier).
  - **#1950** — `tool_surface/service.py` provider-discovery seam (no `register_provider` factory; `build_providers()`/`build_registry()` are hardcoded two-site lists). **Verified NOT a conflict risk for this mission's lanes** — IC-01 extends `AgentProfilesProvider` *behavior* and never edits the provider list; IC-03 touches docs/CI only. Structural debt under epic #1945; defer.
- **Deprecation check (ran; NIL-removable in scope):** scanned the touched + adjacent surfaces for deprecated methods/paths and due shim removals. Nothing adjacent is removable in this mission: the surfaces are new (`tool_surface`) or actively-supported (the `agents.available`/`agent config` aliases are **binding** backward-compat per NFR-001, not deprecated); `command_renderer.py:468` "Legacy fallback" is a benign one-line path-stem conditional (not a removable method); shim-registry entries (`specify_cli.glossary`/`next`/`runtime.*`) target `removal_target_release` 3.3.0/3.4.0 — **not due** (current 3.2.0rc44) and out of these surfaces. No deprecation removals folded in.
