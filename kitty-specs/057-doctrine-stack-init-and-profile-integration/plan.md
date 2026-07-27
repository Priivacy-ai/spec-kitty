# Implementation Plan: Doctrine Stack Init and Profile Integration

**Branch**: `feature/agent-profile-implementation` | **Date**: 2026-03-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/057-doctrine-stack-init-and-profile-integration/spec.md`

## Summary

Wire the doctrine repository layer into the init flow and implement workflow so that:

1. `spec-kitty init` offers doctrine stack setup (accept defaults or inline interview)
2. WP implement workflows resolve and inject agent profile identity fragments
3. Profile inheritance supports merge-by-default with selective exclusion
4. `--feature` is renamed to `--mission` across all 16 CLI commands (backward-compatible)
5. `generic-agent` profile ships in `_proposed/` referencing DIRECTIVE_028

## Technical Context

**Language/Version**: Python 3.12+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic (existing)
**Storage**: Filesystem only (YAML profiles, markdown constitution, JSONL events)
**Testing**: pytest (ATDD + ZOMBIES TDD approach, ruff + mypy quality gates)
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows/WSL)
**Project Type**: Single Python package (`src/specify_cli/` + `src/doctrine/` + `src/constitution/`)
**Performance Goals**: Init defaults ≤2s overhead (NFR-001), profile injection ≤500ms (NFR-002)
**Constraints**: HIC curation gate — all new doctrine artifacts start in `_proposed/` (C-001)
**Scale/Scope**: 16 CLI commands for flag rename, 7+1 agent profiles, 1 constitution defaults file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Directive | Status | Notes |
|-----------|--------|-------|
| DIRECTIVE_001 (Architectural Integrity) | Pass | Profile injection follows existing `_render_constitution_context()` pattern |
| DIRECTIVE_003 (Decision Documentation) | Pass | Architecture assessment written to initiative doc |
| DIRECTIVE_010 (Specification Fidelity) | Pass | Plan traces to all 19 FRs |
| DIRECTIVE_018 (Doctrine Versioning) | Pass | `generic-agent` uses `schema_version: "1.0"` |
| DIRECTIVE_024 (Locality of Change) | Pass | Sequential phases minimize cross-cutting changes |
| DIRECTIVE_025 (Boy Scout Rule) | Pass | `--feature` → `--mission` rename is explicit pre-work |
| DIRECTIVE_028 (Efficient Local Tooling) | Pass | `generic-agent` references this directive; toolguide updated with `rtk` |
| DIRECTIVE_029 (Agent Commit Signing) | N/A | No commit signing changes |
| DIRECTIVE_030 (Test and Typecheck Quality Gate) | Pass | ATDD + ZOMBIES TDD + ruff + mypy enforced per WP |
| DIRECTIVE_031 (Context-Aware Design) | Pass | Profile identity fragments are context-aware governance |
| DIRECTIVE_032 (Conceptual Alignment) | Pass | Glossary updated for `--feature` → `--mission` terminology |

No violations. Gate passed.

## Execution Model

### Sequential Phase Gates

Each phase (A → B → C) is a strictly ordered set of WPs. **All WPs in a phase must be fully reviewed, merged — including worktree cleanup — before starting the next phase.**

No parallel WP execution across phases. Within a phase, WPs may run in parallel only when their file surfaces are disjoint.

### Per-WP Quality Contract

Every WP implementation must follow this execution discipline:

1. **ATDD (Acceptance Test-Driven Development)**: Write acceptance tests first, derived from the WP's acceptance scenarios. Tests must fail before implementation begins.
2. **ZOMBIES TDD**: For each unit of work within the WP, follow the ZOMBIES progression — Zero, One, Many, Boundaries, Interfaces, Exceptions, Simple scenarios.
3. **Ruff**: Run `ruff check .` and `ruff format --check .` before marking WP complete. Zero violations.
4. **Mypy**: Run `mypy` on changed files. Zero new type errors introduced.
5. **Minor Boy Scouting**: When touching a file, fix adjacent lint warnings, add missing type annotations to modified functions, and clean up dead imports — but do not refactor unrelated code.

### WP Completion Checklist

Before moving a WP to `for_review`:

- [ ] All acceptance tests pass
- [ ] All existing tests pass (`pytest tests/ -x`)
- [ ] `ruff check .` clean
- [ ] `ruff format --check .` clean
- [ ] `mypy` on changed files — no new errors
- [ ] Boy Scout cleanup applied to touched files
- [ ] Worktree is clean (`git status` shows no uncommitted changes)

## Project Structure

### Documentation (this feature)

```
kitty-specs/057-doctrine-stack-init-and-profile-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   ├── cli/commands/
│   │   ├── init.py                          # Phase C: doctrine stack choice during init
│   │   ├── accept.py                        # Phase A: --feature → --mission rename
│   │   ├── implement.py                     # Phase A: --feature → --mission rename
│   │   ├── merge.py                         # Phase A: --feature → --mission rename
│   │   ├── lifecycle.py                     # Phase A: --feature → --mission rename
│   │   ├── mission.py                       # Phase A: --feature → --mission rename
│   │   ├── next_cmd.py                      # Phase A: --feature → --mission rename
│   │   ├── research.py                      # Phase A: --feature → --mission rename
│   │   ├── validate_encoding.py             # Phase A: --feature → --mission rename
│   │   ├── validate_tasks.py                # Phase A: --feature → --mission rename
│   │   ├── verify.py                        # Phase A: --feature → --mission rename
│   │   └── agent/
│   │       ├── __init__.py                  # Phase A: --feature → --mission rename
│   │       ├── context.py                   # Phase A: --feature → --mission rename
│   │       ├── feature.py                   # Phase A: --feature → --mission rename
│   │       ├── status.py                    # Phase A: --feature → --mission rename
│   │       ├── tasks.py                     # Phase A: --feature → --mission rename
│   │       └── workflow.py                  # Phase A: rename + Phase B: profile injection
│   └── constitution/
│       └── context.py                       # Phase C: constitution defaults loading
│
├── doctrine/
│   ├── agent_profiles/
│   │   ├── repository.py                    # Phase B: inheritance merge + excluding
│   │   ├── profile.py                       # Phase B: excluding field on model
│   │   ├── shipped/                         # Existing 7 profiles (unchanged)
│   │   └── _proposed/
│   │       └── generic-agent.agent.yaml     # Phase B: new profile
│   ├── constitution/
│   │   └── defaults.yaml                    # Phase C: new defaults file
│   ├── directives/shipped/
│   │   └── 028-search-tool-discipline.directive.yaml  # Pre-work: rtk (done)
│   └── toolguides/shipped/
│       ├── efficient-local-tooling.toolguide.yaml     # Pre-work: rtk (done)
│       └── EFFICIENT_LOCAL_TOOLING.md                 # Pre-work: rtk (done)
│
├── glossary/
│   ├── contexts/orchestration.md            # Phase A: Feature entry update
│   └── historical-terms.md                  # Phase A: --feature alias entry
│
└── tests/
    ├── doctrine/
    │   ├── test_profile_inheritance.py       # Phase B: new test module
    │   ├── test_generic_agent_profile.py     # Phase B: new test module
    │   └── test_profile_context_template.py  # Existing (unchanged)
    ├── specify_cli/cli/commands/
    │   ├── test_mission_flag_rename.py       # Phase A: new test module
    │   └── test_init_doctrine.py             # Phase C: new test module
    └── agent/cli/commands/
        └── test_workflow_profile_injection.py # Phase B: new test module
```

**Structure Decision**: Extends existing `src/specify_cli/` and `src/doctrine/` packages. No new top-level packages. All new test modules follow existing `tests/` mirror structure.

## Implementation Phases

### Phase A: Pre-work (Sequential, 2 WPs)

**Goal**: Clean terminology foundation before adding new code.

**WP-A1: `--feature` → `--mission` CLI Flag Rename**
- Scope: All 16 CLI commands listed above
- Pattern: Add `--mission` as primary typer.Option, keep `--feature` as hidden alias
- Deprecation helper: Create shared utility function `resolve_mission_or_feature(mission, feature)` that:
  - Returns `mission` if provided
  - Returns `feature` with deprecation warning if provided
  - Raises error if both provided with different values
  - Returns `None` if neither provided
- Update all help text to use "mission" terminology
- Update existing tests to cover both flags
- New tests: happy path `--mission`, alias `--feature` with warning, conflict error, same-value silent
- Requirements: FR-017, FR-018, C-005
- Files: 16 command files + 1 new utility + 1 new test module

**WP-A2: Glossary Update**
- Scope: Update `Feature` entry in `glossary/contexts/orchestration.md` to note CLI flag deprecation
- Add `--feature` CLI flag as deprecated alias entry in `glossary/historical-terms.md`
- Verify glossary semantic integrity (run glossary checks if available)
- Requirements: FR-019, SC-008
- Files: 2 glossary files

**Phase A gate**: Both WPs reviewed, merged, worktrees cleaned. All 16 commands accept `--mission`. Existing tests pass.

---

### Phase B: Core Profile Infrastructure (Sequential, 3 WPs)

**Goal**: Profile inheritance, generic-agent, and workflow injection.

**WP-B1: Profile Inheritance — Merge-by-Default with Excluding**
- Scope: Update `AgentProfileRepository.resolve_profile()` to change list merge semantics from replace to union (no duplicates)
- Add `excluding` field to `AgentProfile` model in `profile.py` — supports both field-level (`excluding: [directives]`) and value-level (`excluding: {directives: [DIRECTIVE_010]}`)
- Update `resolve_profile()` merge logic: for each list field, merge parent + child (union), then apply excluding removals
- Cycle detection: `validate_hierarchy()` already exists — verify it catches cycles during resolution, not just validation
- ATDD: Write acceptance tests from User Story 6 scenarios (single-level, multi-level, excluding field-level, excluding value-level, missing parent error, cycle error)
- ZOMBIES: Zero profiles → one child → many-level chain → boundary (excluding nonexistent value) → interface (resolve_profile return type) → exception (cycle, missing parent)
- Requirements: FR-016, C-006, SC-006
- Files: `repository.py`, `profile.py`, new `tests/doctrine/test_profile_inheritance.py`

**WP-B2: Generic-Agent Profile in `_proposed/`**
- Scope: Create `src/doctrine/agent_profiles/_proposed/generic-agent.agent.yaml`
- Single directive reference: DIRECTIVE_028 (Efficient Local Tooling)
- Broad specialization (primary_focus: "General-purpose task execution")
- No `specializes-from` (root profile)
- Must pass existing agent-profile JSON schema validation (C-004)
- Must NOT exist in `shipped/` (C-001)
- ATDD: Write acceptance tests from User Story 5 scenarios (exists in _proposed, DIRECTIVE_028 reference, not in shipped, schema valid)
- Requirements: FR-011, FR-012, C-001, C-004, SC-005
- Files: 1 new YAML profile, new `tests/doctrine/test_generic_agent_profile.py`

**WP-B2.5: Human-in-Charge Sentinel Profile**
- Scope: Make it possible to assign a WP to a human explicitly, rather than to an AI agent, using the existing `agent_profile` field as the assignment surface
- Design: `human-in-charge` is a **workflow sentinel**, not a true agent identity. It carries `sentinel: true` in its YAML schema. The workflow checks `profile.sentinel` and switches to human-execution mode: no agent context injection, no initialization declaration, WP rendered as a human task in the kanban
- Create `src/doctrine/agent_profiles/_proposed/human-in-charge.agent.yaml`:
  - `sentinel: true`
  - `primary_focus: "Human execution — this WP requires direct human action or collaborative human-AI work"`
  - No `specializes-from`, no `directive-references`, no `initialization-declaration`
  - Must NOT exist in `shipped/` (C-001)
- Schema update: add optional `sentinel: bool` field to `AgentProfile` model (`profile.py`)
- Usage: a WP author sets `agent_profile: human-in-charge` in frontmatter to signal human execution
- Workflow injection (WP-B3) checks: `if resolved_profile.sentinel → skip injection, emit "Human-in-charge WP: no agent identity injected"`
- Kanban / dashboard: render HiC WPs with a distinct indicator (e.g. `👤`) distinguishing them from agent-assigned WPs
- Add "Human-in-Charge WP" to `glossary/contexts/identity.md` (or `orchestration.md`): a work package with `agent_profile: human-in-charge` indicating the deliverable requires direct human execution; the HiC remains responsible, no specialist identity is injected
- ATDD: sentinel profile exists in _proposed, schema valid, sentinel=true, not in shipped; workflow skips injection for sentinel profiles; kanban shows distinct marker
- Requirements: FR-007 (extends — profile field is assignment surface), FR-008 (sentinel is a special case of the generic-agent default path), SC-002
- Files: 1 new YAML profile, `profile.py` schema update, `tests/doctrine/test_human_in_charge_profile.py`

**WP-B3: Workflow Profile Injection**
- Scope: Add `_render_profile_context()` function to `workflow.py` following the `_render_constitution_context()` pattern
- Read `agent_profile` from WP frontmatter (ruamel.yaml parsing)
- Default to `generic-agent` when field is absent (FR-008)
- Resolve profile via `AgentProfileRepository.resolve_profile()`
- **Sentinel check**: if `resolved_profile.sentinel is True`, skip injection entirely and log "Human-in-charge WP: no agent identity injected" (introduced by WP-B2.5)
- Render identity fragment: name, purpose, specialization, directives, initialization declaration
- Inject into implement prompt alongside constitution context
- Warning path: if profile not found (nonexistent or generic-agent not promoted), emit "Profile not found, proceeding without specialist identity" and skip injection
- ATDD: Write acceptance tests from User Story 3 scenarios (implementer injection, architect injection, missing profile warning, no field → generic-agent default, human-in-charge → no injection)
- Requirements: FR-006, FR-007, FR-008, FR-009, NFR-002, NFR-003, SC-002, SC-003
- Files: `workflow.py`, new `tests/agent/cli/commands/test_workflow_profile_injection.py`

**Phase B gate**: All 4 WPs reviewed, merged, worktrees cleaned. Profile inheritance works. Generic-agent and human-in-charge exist in `_proposed/`. Implement workflow injects profiles and respects sentinel flag.

---

### Phase C: Init-Time Doctrine (Sequential, 3 WPs)

**Goal**: Doctrine stack setup during init, profile-context deployment, task template integration.

**WP-C1: Constitution Defaults File + Init Integration**
- Scope: Create `src/doctrine/constitution/defaults.yaml` with predefined paradigm/directive/tool selections
- Extend `init.py` to offer doctrine stack choice after `.kittify/` skeleton creation:
  - "Accept defaults" → load `defaults.yaml`, call `constitution generate` with those selections
  - "Configure manually" → ask interview depth (minimal/comprehensive), delegate to existing `constitution interview` flow inline
  - Skip if constitution already exists (FR-004)
  - `--non-interactive` applies defaults automatically (FR-005)
  - **Resume/restart on interrupt** (FR-020): if a previous init was interrupted mid-interview, on next invocation offer "Resume previous session" or "Start over". Checkpoint stored in `.kittify/.init-checkpoint.yaml` (or similar). Selecting "Start over" discards the checkpoint.
- Inform user about what interview does, how to customize later (FR-015)
- **Deliverable: update/create user journey** in `architecture/2.x/user_journey/` documenting the full init flow including the resume/restart decision point and the resume/restart path
- ATDD: Write acceptance tests from User Stories 1 and 2 scenarios (including US-2 scenario 4: resume after interrupt)
- Requirements: FR-001, FR-002, FR-003, FR-004, FR-005, FR-015, FR-020, NFR-001, C-002
- Files: `init.py`, new `defaults.yaml`, new `tests/specify_cli/cli/commands/test_init_doctrine.py`, new `architecture/2.x/user_journey/init-doctrine-flow.md`

**WP-C2: Profile-Context Upgrade Migration**
- Scope: Create migration that deploys `profile-context.md` command template to all configured agent directories during `spec-kitty upgrade`
- Use `get_agent_dirs_for_project()` helper (config-aware, C-003)
- Template source: `src/doctrine/templates/command-templates/profile-context.md` (already created)
- Migration must be idempotent (re-running upgrade doesn't duplicate)
- ATDD: Write acceptance tests from User Story 4 scenarios
- Requirements: FR-010, SC-004, C-003
- Files: New migration file in `src/specify_cli/upgrade/migrations/`, tests

**WP-C3: Task Template Role Hints + Profile Suggestion**
- Scope: Add `agent_role` field to mission template task definitions
- During `/spec-kitty.tasks` generation, use role hint + task content to suggest concrete `agent_profile` for each WP
- Write `agent_profile` into WP frontmatter for user confirmation during `finalize-tasks`
- ATDD: Write acceptance tests from FR-013/FR-014 scenarios
- Requirements: FR-013, FR-014, SC-002
- Files: Mission template YAML, task generation logic, finalize-tasks logic

**Phase C gate**: All 3 WPs reviewed, merged, worktrees cleaned. Init offers doctrine setup. Profile-context deploys via upgrade. Task templates suggest profiles.

## Dependency Graph

```
Phase A (pre-work):
  WP-A1 (flag rename) → WP-A2 (glossary)

Phase B (core profile):
  WP-B1 (inheritance) → WP-B2 (generic-agent) → WP-B2.5 (human-in-charge sentinel) → WP-B3 (workflow injection)

Phase C (init doctrine):
  WP-C1 (defaults + init) → WP-C2 (profile-context migration) → WP-C3 (task templates)
```

All phases are strictly sequential: A completes → B starts → B completes → C starts.

Within each phase, WPs are sequential as shown above.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Flag rename breaks existing automation | Medium | High | Deprecation warning + backward-compatible alias; existing tests must pass |
| Profile inheritance merge semantics introduce subtle bugs | Medium | Medium | ZOMBIES TDD with boundary cases; existing profile tests as regression safety net |
| Init flow complexity grows too large | Low | Medium | Delegate to existing `constitution interview` and `constitution generate`; init only orchestrates |
| Generic-agent accidentally promoted to shipped | Low | High | C-001 constraint + acceptance test verifying absence from `shipped/` |
| Human-in-charge sentinel mistaken for agent profile | Low | Medium | `sentinel: true` field + schema validation; workflow checks sentinel before injection |
| HiC WP mixed into agent parallelization waves | Low | Medium | Dashboard renders HiC WPs distinctly; task authors assign by convention; no automated guard needed at this stage |

## Complexity Tracking

No constitution violations to justify. All design decisions align with existing patterns.
