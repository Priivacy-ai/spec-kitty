# Implementation Plan: Agent Profile System

*Path: kitty-specs/045-agent-profile-system/plan.md*

**Branch**: `feature/agent-profile-implementation` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/045-agent-profile-system/spec.md`
**Origin Branch**: `2.x` | **Target Branch**: `feature/agent-profile-implementation`

## Summary

The Agent Profile System introduces a structured identity framework for agents within the doctrine domain. Six work packages (WP01-WP04, WP06-WP07) are already implemented on the feature branch, delivering the core domain model, repository, schema validation, shipped profiles, ToolConfig rename, and CLI commands.

Nine remaining work packages deliver: doctrine as a separate PyPI package (WP05), ToolConfig migration with YAML key rename (WP08), CI alignment (WP09), shipped directives (WP10), agent interview (WP11), init CLI (WP12), structure templates (WP13), mission schema integration (WP14), and profile inheritance resolution (WP15).

**Key architectural decisions:**
- **Doctrine packaging**: Separate PyPI package (`doctrine`) with its own `pyproject.toml`, versioned independently. `spec-kitty-cli` declares it as a dependency.
- **Init mechanism**: Tool-specific context fragment generation (stateless, parallelism-safe). No session files.
- **Inheritance merge**: Shallow merge — child keys override parent keys one level deep within each section; parent keys absent from child are preserved.
- **Methodology**: ATDD/TDD test-first across all remaining WPs.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic, typer, rich, ruamel.yaml, pytest
**Storage**: Filesystem (YAML profiles, YAML directives, JSON Schema, YAML config)
**Testing**: pytest with 90%+ coverage, mypy --strict
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Dual-package (doctrine + specify_cli)
**Performance Goals**: CLI operations < 2 seconds (constitution requirement)
**Constraints**: No database, no network dependencies for profile operations
**Scale/Scope**: 7 shipped profiles + unlimited project profiles, 19 directive files, 4 mission schemas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | Both packages target Python 3.11+ |
| pytest with 90%+ coverage | PASS | Existing tests at 120+ target; ATDD/TDD enforced |
| mypy --strict | PASS | All new code must pass strict type checking |
| CLI operations < 2s | PASS | Profile operations are filesystem-only, well within budget |
| Cross-platform | PASS | Filesystem paths use `pathlib`; no OS-specific APIs |
| Git required | PASS | Feature branch workflow, no new git dependencies |
| PyPI distribution | REQUIRES ATTENTION | `doctrine` must be a new PyPI package (WP05) |
| Pre-commit hooks pass | PASS | No new hooks introduced |

**Constitution Violation**: The introduction of a second PyPI package (`doctrine`) is an architectural expansion beyond the single-package model. This is justified because:
- Agent profiles are a doctrine domain concept, not a CLI concern
- Separation enables independent versioning and reuse
- The constitution's PyPI distribution gate is satisfied by adding `doctrine` to the release workflow

## Project Structure

### Documentation (this feature)

```
kitty-specs/045-agent-profile-system/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/spec-kitty.tasks - NOT created here)
```

### Source Code (repository root)

```
src/doctrine/                              # SEPARATE PYPI PACKAGE (new pyproject.toml in WP05)
├── pyproject.toml                         # NEW — independent package config
├── __init__.py
├── agent_profiles/                        # DONE (WP01-WP04)
│   ├── __init__.py
│   ├── profile.py                         # AgentProfile, Role, TaskContext
│   ├── repository.py                      # Two-source loader, hierarchy, matching
│   │                                      # + resolve_profile() (WP15)
│   ├── capabilities.py                    # RoleCapabilities
│   ├── validation.py                      # Schema validation, file detection
│   └── shipped/                           # 7 reference profiles
│       ├── implementer.agent.yaml
│       ├── reviewer.agent.yaml
│       ├── architect.agent.yaml
│       ├── planner.agent.yaml
│       ├── designer.agent.yaml
│       ├── researcher.agent.yaml
│       └── curator.agent.yaml
├── directives/                            # WP10 — 19 directive YAML files
│   ├── test-first.directive.yaml          # EXISTS
│   ├── 001-*.directive.yaml               # NEW (18 more)
│   └── ...
├── schemas/
│   ├── agent-profile.schema.yaml          # DONE (WP03)
│   ├── directive.schema.yaml              # EXISTS
│   └── mission.schema.yaml                # UPDATED (WP14 — agent-profile field)
├── missions/                              # EXISTS — mission definitions
│   ├── software-dev/
│   │   ├── mission.yaml                   # UPDATED (WP14 — agent-profile per state)
│   │   └── mission-runtime.yaml           # UPDATED (WP14 — agent-profile per step)
│   └── ...
├── templates/
│   └── structure/                         # WP13 — NEW
│       ├── REPO_MAP.md
│       └── SURFACES.md
├── paradigms/                             # EXISTS
├── tactics/                               # EXISTS
├── styleguides/                           # EXISTS
└── toolguides/                            # EXISTS

src/specify_cli/                           # EXISTING PYPI PACKAGE
├── __main__.py                            # DONE (fix applied)
├── core/
│   ├── tool_config.py                     # DONE (WP06) + YAML key update (WP08)
│   └── agent_config.py                    # DONE (WP06) — deprecation shim
├── cli/commands/agent/
│   ├── profile.py                         # DONE (WP07) + interview (WP11) + init (WP12)
│   └── ...
├── constitution/
│   ├── interview.py                       # EXISTS — pattern for agent interview (WP11)
│   └── ...
├── upgrade/migrations/
│   └── m_X_X_X_tool_config_rename.py      # WP08 — NEW migration
└── ...

tests/
├── doctrine/                              # EXISTING test directory
│   ├── test_profile_model.py              # DONE
│   ├── test_profile_repository.py         # DONE + inheritance tests (WP15)
│   ├── test_profile_schema_validation.py  # DONE
│   ├── test_shipped_profiles.py           # DONE
│   ├── test_capabilities.py              # DONE
│   ├── test_directive_consistency.py      # WP10 — NEW
│   ├── test_profile_inheritance.py        # WP15 — NEW
│   └── fixtures/                          # DONE + new fixtures
└── specify_cli/
    └── cli/commands/agent/
        ├── test_profile_cli.py            # DONE + interview tests (WP11) + init tests (WP12)
        └── ...
```

**Structure Decision**: Dual-package layout. `src/doctrine/` becomes an independent PyPI package with its own `pyproject.toml`. `src/specify_cli/` remains the CLI package, declaring `doctrine` as a dependency. Tests stay in the existing `tests/` directory structure.

## Dependency Graph

```
WP05 (Doctrine PyPI Package)
 │
 ├─── WP10 (Shipped Directives & Consistency)     ─┐
 ├─── WP13 (Doctrine Structure Templates)          │  PARALLEL WAVE 1
 ├─── WP14 (Mission Schema Agent Profile)          │  (all independent after WP05)
 ├─── WP15 (Profile Inheritance Resolution)        │
 ├─── WP08 (ToolConfig Upgrade Migration)          │
 └─── WP09 (CI & Test Alignment)                  ─┘
       │
       ├─── WP11 (Agent Profile Interview)          ← depends on WP10 (directive refs)
       │
       └─── WP12 (Agent Initialization CLI)         ← depends on WP11 + WP15
                                                       (init needs resolved profiles
                                                        + interview creates profiles)
```

**Parallelization opportunities:**
- **Wave 1** (after WP05): WP08, WP09, WP10, WP13, WP14, WP15 — all 6 can run in parallel
- **Wave 2** (after WP10): WP11
- **Wave 3** (after WP11 + WP15): WP12

**Optimal timeline**: 4 sequential waves (WP05 → Wave 1 → WP11 → WP12) instead of 9 sequential WPs.

## Work Package Details

### WP05 — Doctrine Wheel Packaging

**Goal**: Extract `src/doctrine/` into a standalone PyPI package.

**Approach**:
1. Create `src/doctrine/pyproject.toml` with package metadata, version, and build config
2. Configure `hatch` build targets to include YAML, markdown, and template files as package data
3. Update root `pyproject.toml` to declare `doctrine` as a dependency of `spec-kitty-cli`
4. Ensure `importlib.resources` or `importlib_resources` is used for shipped data access (not `__file__`-relative paths)
5. Verify wheel contents include all shipped profiles, schemas, directives, and templates

**Key risk**: Path resolution changes. Currently `repository.py` uses `Path(__file__).parent / "shipped"` for shipped profiles. This must work both in editable installs and from wheel-installed packages.

**Test-first**: Write a test that builds the wheel, installs it in an isolated venv, and verifies `import doctrine` + shipped profile loading.

### WP08 — ToolConfig Upgrade Migration

**Goal**: Register migration for AgentConfig→ToolConfig rename + YAML key rename.

**Approach**:
1. Create migration file `m_X_X_X_tool_config_yaml_key_rename.py` in `src/specify_cli/upgrade/migrations/`
2. Migration reads `.kittify/config.yaml`, renames `agents` key to `tools` if present
3. Update `load_tool_config()` in `src/specify_cli/core/tool_config.py` to read `tools` key first, fall back to `agents` with deprecation warning
4. Register migration in the migration registry
5. Update all code that writes to config.yaml to use `tools` key

**Test-first**: Write migration test with fixture config containing `agents` key, verify key renamed after migration, verify backward-compat fallback.

### WP09 — CI & Test Alignment

**Goal**: Ensure doctrine tests run in CI and wheel contents are verified.

**Approach**:
1. Verify `tests/doctrine/` is included in CI test runs (check pytest config / CI workflow)
2. Add wheel content verification test (build wheel, inspect with `zipfile`, assert required files present)
3. Verify `__main__.py` fix works in CI (`python -m specify_cli --help`)
4. Add doctrine package import smoke test to CI

**Test-first**: Write CI-focused tests that validate package structure and importability.

### WP10 — Shipped Directives & Consistency

**Goal**: Create 19 directive YAML files and a consistency test.

**Approach**:
1. Catalog all 19 directive codes referenced across 7 shipped profiles (001-019)
2. Create each directive file following `directive.schema.yaml` format: `schema_version`, `id`, `title`, `intent`, `tactic_refs`, `enforcement`
3. Use `doctrine_ref/directives/` as content reference, adapt to the canonical schema
4. Write consistency test: scan all shipped profiles for directive references, verify each resolves to a file in `src/doctrine/directives/` with matching title

**Test-first**: Write the consistency test first (it will fail until directives are created), then create each directive file until the test passes.

### WP11 — Agent Profile Interview

**Goal**: Interactive `--interview` flow for creating agent profiles.

**Approach**:
1. Follow the constitution interview pattern from `src/specify_cli/constitution/interview.py`
2. Interview questions: profile-id, name, role (from enum), purpose, primary-focus, specializes-from (optional), collaboration partners, directive references (from shipped list), mode defaults
3. Fast path (`--defaults`): only ask profile-id, name, role, purpose, primary-focus
4. Pre-populate role capabilities from `RoleCapabilities` mapping when role is selected
5. Validate generated YAML against `agent-profile.schema.yaml`
6. Write to `.kittify/constitution/agents/<profile-id>.agent.yaml`

**Test-first**: Write tests for interview flow (mocked input), fast-path flow, schema validation of output, role pre-population.

### WP12 — Agent Initialization CLI

**Goal**: `spec-kitty agent profile init <profile-id>` configures the active tool.

**Approach**:
1. Add `init` subcommand to `src/specify_cli/cli/commands/agent/profile.py`
2. Load profile via `AgentProfileRepository`, resolve inheritance (uses WP15's `resolve_profile()`)
3. Detect active tool from config (which agent directories exist)
4. Generate tool-specific context fragment containing: directives list, specialization boundaries, collaboration contracts, mode defaults, initialization declaration
5. Write fragment to the tool's context location (e.g., `.claude/commands/` for Claude Code, `.codex/prompts/` for Codex)
6. Report which artifacts were loaded and where the context was written

**Test-first**: Write tests for context fragment generation, tool detection, file writing, profile-not-found error case.

### WP13 — Doctrine Structure Templates

**Goal**: Ship REPO_MAP and SURFACES templates, integrate with `spec-kitty init`.

**Approach**:
1. Adapt `doctrine_ref/templates/structure/REPO_MAP.md` and `SURFACES.md` to shipped template format with placeholder markers
2. Place in `src/doctrine/templates/structure/`
3. Add a step to `spec-kitty init` bootstrap that offers to generate these files
4. Generation copies templates to project root (or configured docs location) with placeholders ready for customization

**Test-first**: Write tests for template presence in package, placeholder marker structure, init integration.

### WP14 — Mission Schema Agent Profile Integration

**Goal**: Add optional `agent-profile` field to mission schema.

**Approach**:
1. Update `src/doctrine/schemas/mission.schema.yaml`: add optional `agent-profile` property to state items (change states from string array to object array with backward compat)
2. Update runtime DAG step schema in `mission-runtime.yaml` format: add optional `agent-profile` field to step definitions
3. Verify all existing mission YAML files validate against updated schema
4. Do NOT populate `agent-profile` values in existing missions (that's a future orchestration concern)

**Test-first**: Write schema validation tests with and without agent-profile field, backward compatibility tests for existing missions.

### WP15 — Profile Inheritance Resolution

**Goal**: Add `resolve_profile()` with shallow merge and update matching.

**Approach**:
1. Add `resolve_profile(profile_id: str) -> AgentProfile` to `AgentProfileRepository`
2. Walk `specializes-from` chain using `get_ancestors()`, collect ancestor profiles
3. Merge bottom-up: start from root ancestor, shallow-merge each descendant's fields on top
4. Shallow merge = for each section (dict), child keys override parent keys one level deep; parent keys absent from child are preserved
5. Handle edge cases: orphaned reference (warn, return child as-is), cycle (error via existing `validate_hierarchy()`)
6. Update `find_best_match()` to call `resolve_profile()` before scoring, so inherited context participates in matching

**Test-first**: Write tests for single-level inheritance, multi-level chain, orphaned reference, cycle detection, shallow merge semantics, matching with resolved profiles.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Second PyPI package (doctrine) | Domain separation: doctrine concepts are reusable beyond the CLI | Single package conflates CLI tooling with governance domain model; prevents independent versioning |
| 19 directive files in one WP | Shipped profiles already reference all 19 codes | Incremental addition would leave consistency test failing between WPs |
