# Enable Plan Mission Runtime Support on 2.x

**Feature**: 041-enable-plan-mission-runtime-support
**Priority**: P0
**Scope**: 2.x branch only (no mainline migration, no doctrine path changes)
**Created**: 2026-02-22

## Executive Summary

The `plan` mission can be created via `/spec-kitty.specify --mission plan`, but the `next` runtime loop blocks with "Mission 'plan' not found" when attempting to progress to implementation. This feature enables the `plan` mission to work end-to-end in the runtime loop by adding required runtime artifacts and mission-scoped command templates on the 2.x branch.

## Problem Statement

**Current Behavior**:
1. `spec-kitty specify "plan adoption feature" --mission plan --json` succeeds and creates a feature with `mission=plan`
2. `spec-kitty next --feature <slug> --agent codex --json` immediately returns blocked with:
   ```
   Failed to start/load runtime run: Mission 'plan' not found ...
   ```
3. The `plan` mission directory exists but lacks critical runtime artifacts:
   - `src/specify_cli/missions/plan/mission-runtime.yaml` (missing)
   - `src/specify_cli/missions/plan/command-templates/` (empty)
   - `src/specify_cli/missions/plan/templates/` (empty)

**Root Cause**:
The runtime bridge (`src/specify_cli/next/runtime_bridge.py`, lines 214, 244, 302) expects:
- A runtime-compatible mission definition (`mission-runtime.yaml`) with schema: `mission.key`, `steps`, `depends_on`, `prompt_template`
- Mission-scoped command templates that the runtime can resolve and execute for each step

Without these artifacts, the runtime cannot discover or load the plan mission.

## Success Criteria

1. **Specification Phase**: On 2.x, in a clean temp project:
   - `spec-kitty specify "test plan feature" --mission plan --json` succeeds
   - Feature created with `mission=plan` in meta.json

2. **Runtime Loop Phase**:
   - `spec-kitty next --feature <slug> --agent codex --json` returns non-blocked status (`step`, `decision_required`, or `terminal`)
   - No "Mission 'plan' not found" error

3. **Command Resolution**:
   - Runtime successfully resolves plan mission command templates: `specify.md`, `research.md`, `plan.md`, `review.md`
   - Each template resolves to a valid command prompt with no missing references

4. **Regression Testing**:
   - No behavior regressions for `software-dev` and `research` missions
   - Existing tests continue to pass

5. **Scope Compliance**:
   - All changes on 2.x branch only
   - No doctrine path migration
   - No changes to unrelated systems (SaaS, telemetry, PR146)

## Functional Requirements

### FR1: Runtime Mission Definition
**Requirement**: Add `mission-runtime.yaml` to `src/specify_cli/missions/plan/`

**Semantics**:
- Mission key: `plan`
- Step sequence: `specify` → `research` → `plan` → `review`
  - Step 1 (`specify`): Entry point, prepare feature definition
  - Step 2 (`research`): Gather research inputs and context
  - Step 3 (`plan`): Design and planning phase
  - Step 4 (`review`): Final review and validation
- No inter-step dependencies (each step depends only on successful completion of previous step)
- Runtime prompt template: Describes how the runtime loop invokes each step

**Constraints**:
- Use existing runtime schema (not new extensions)
- Keep consistent with existing plan mission phases (goals/research/structure/draft/review)
- Compatible with runtime bridge resolver (lines 214, 244, 302)

### FR2: Mission-Scoped Command Templates
**Requirement**: Add four command templates to `src/specify_cli/missions/plan/command-templates/`

**Files to Create**:
- `specify.md` - Command template for specify step
- `research.md` - Command template for research step
- `plan.md` - Command template for plan/design step
- `review.md` - Command template for review step

**Content Guidelines**:
- Each template provides context-aware prompt for its step
- Reference only 2.x-compatible paths (no doctrine paths like `doctrine/prompts/`)
- Can reference shared content templates via relative paths (e.g., `../templates/...`)
- Keep language clear and focused on the step's deliverables

**Constraints**:
- No external service dependencies (self-contained templates)
- Deterministic content (same input = same output)

### FR3: Mission-Scoped Content Templates (Conditional)
**Requirement**: Add content templates to `src/specify_cli/missions/plan/templates/` (only if referenced by command templates)

**Decision Logic**:
- If command templates reference a content template (e.g., `../templates/research-outline.md`), create it
- If no references exist, leave directory empty (no artificial templates)

**Constraints**:
- Keep focused on plan mission (don't create generic templates)
- 2.x-compatible paths only

### FR4: Integration Tests
**Requirement**: Add/extend tests proving end-to-end functionality

**Test Coverage**:

a) **Mission Discovery Integration Test**:
   - Create feature with `mission=plan` via CLI
   - Verify `next` command recognizes plan mission
   - Verify non-blocked return status

b) **Command Resolution Test**:
   - Test `resolve_command(..., mission="plan", step="specify")` → resolves to valid template
   - Test for all four steps (specify, research, plan, review)
   - Verify no missing file errors

c) **Regression Tests**:
   - Ensure `software-dev` and `research` missions still resolve correctly
   - Existing tests continue to pass

**Constraints**:
- No external auth/services required
- CI-runnable (deterministic, isolated)
- Keep test determinism (no random data, no external calls)

## Architecture & Implementation Approach

### File Structure (2.x-compatible)
```
src/specify_cli/missions/plan/
├── mission.yaml                    # Existing: planning mission definition
├── mission-runtime.yaml            # NEW: runtime schema for next loop
├── command-templates/              # NEW: mission-scoped command templates
│   ├── specify.md                  # Step 1 prompt
│   ├── research.md                 # Step 2 prompt
│   ├── plan.md                     # Step 3 prompt
│   └── review.md                   # Step 4 prompt
└── templates/                      # NEW: mission-scoped content templates (if needed)
    └── [created only if referenced by command templates]
```

### Key Integration Points

1. **Runtime Bridge** (`src/specify_cli/next/runtime_bridge.py`):
   - Lines 214, 244: Mission discovery and loading
   - Line 302: Command template resolution
   - Once `mission-runtime.yaml` exists, bridge can discover plan mission
   - Once command templates exist, resolver can load them

2. **Command Resolver** (`src/specify_cli/next/command_resolver.py` or similar):
   - Expects mission-scoped templates in `missions/{mission_key}/command-templates/`
   - Returns fully resolved command template for each step

3. **Next Runtime Loop** (`src/specify_cli/next/runner.py` or similar):
   - Calls resolver for each step
   - Executes resolved command prompt
   - Transitions to next step on success

### Step Sequence & Command Flow

```
Feature created with mission=plan
    ↓
User calls: spec-kitty next --feature <slug> --agent codex
    ↓
Runtime bridge loads: mission-runtime.yaml
    ↓
Step 1: specify
  - Resolver loads: command-templates/specify.md
  - Runtime executes specify command
  - Agent provides feature specification
    ↓
Step 2: research
  - Resolver loads: command-templates/research.md
  - Runtime executes research command
  - Agent gathers research context
    ↓
Step 3: plan
  - Resolver loads: command-templates/plan.md
  - Runtime executes plan command
  - Agent designs planning artifacts
    ↓
Step 4: review
  - Resolver loads: command-templates/review.md
  - Runtime executes review command
  - Agent reviews and validates
    ↓
Terminal: Feature planning complete
```

## Testing Strategy

### Unit Tests
- **Mission YAML Parsing**: Verify `mission-runtime.yaml` parses correctly
- **Template Resolution**: Verify each command template resolves without errors
- **Schema Validation**: Verify mission definition matches runtime schema expectations

### Integration Tests
- **End-to-End Specify → Next**:
  - Create feature with `mission=plan`
  - Call `next` command
  - Verify non-blocked status
- **All Step Resolutions**:
  - Test resolver for specify, research, plan, review steps
  - Verify each returns valid template

### Regression Tests
- **Software-Dev Mission**: Existing tests continue to pass
- **Research Mission**: Existing tests continue to pass
- **CLI Commands**: `spec-kitty specify`, `spec-kitty next` work for all missions

## Assumptions

1. **Runtime Schema**: Existing runtime schema in `mission-runtime.yaml` files (if any) is the canonical format; we follow that pattern
2. **Command Template Format**: Command templates use same format as software-dev mission templates (Markdown with frontmatter/context)
3. **Step Sequence**: Plan mission workflow is: specify → research → plan → review (4 steps, no parallelization)
4. **2.x Stability**: 2.x branch is stable and separate from mainline; no cross-branch merges required
5. **No New Dependencies**: All implementation uses existing Python dependencies (pathlib, ruamel.yaml, typer, etc.)

## Constraints & Scope Boundaries

### In Scope
- Add `mission-runtime.yaml` for plan mission
- Add 4 mission-scoped command templates
- Add any referenced content templates
- Add integration + resolver tests
- 2.x branch only

### Out of Scope
- Doctrine path migration (keep 2.x paths as-is)
- SaaS/API changes
- Telemetry schema redesign
- Mainline migration/refactoring
- Unrelated PR146 changes
- Runtime loop algorithmic changes (use existing step execution)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Template references point to non-existent files | Test resolver for all steps; CI validates on PR |
| 2.x paths conflict with doctrine paths | Keep all paths local to `missions/plan/`; no cross-references |
| Regression in other missions | Run existing tests for software-dev and research; CI gates |
| Runtime schema incompatibility | Follow existing `mission-runtime.yaml` pattern from other missions |
| Test flakiness in CI | Keep tests deterministic; mock external services; no timing-dependent assertions |

## Success Metrics

1. **Functional**: `spec-kitty next --feature <slug> --agent codex` returns non-blocked for plan mission
2. **Coverage**: All 4 steps (specify, research, plan, review) can be resolved and executed
3. **Compatibility**: Zero regressions in software-dev and research missions
4. **Quality**: Integration tests pass in CI without external dependencies
5. **Scope**: All changes on 2.x; no doctrine migration or unrelated changes

## User Scenarios & Testing

### Scenario 1: Create and Progress Plan Feature
**Actor**: Developer using spec-kitty on 2.x branch

**Flow**:
1. Developer runs: `spec-kitty specify "Build OAuth2 integration" --mission plan --json`
2. Feature 041 is created with `mission=plan`
3. Developer runs: `spec-kitty next --feature 041-build-oauth2 --agent codex --json`
4. System returns non-blocked status (not "Mission 'plan' not found")
5. Runtime loads step 1 (specify), executes specify command, agent provides specification
6. Developer runs `next` again to progress to step 2 (research)
7. ... continues through steps 3 (plan) and 4 (review)
8. Feature planning complete

**Acceptance**: No errors, features created successfully, `next` loop unblocked

### Scenario 2: Command Template Resolution
**Actor**: Runtime resolver component

**Flow**:
1. Feature has `mission=plan`
2. Resolver calls: `resolve_command(feature_dir, mission="plan", step="research")`
3. Resolver locates: `src/specify_cli/missions/plan/command-templates/research.md`
4. Template loads successfully with no missing references
5. Resolver returns fully resolved prompt to runtime

**Acceptance**: All 4 steps resolve without errors

### Scenario 3: Regression Check
**Actor**: CI pipeline

**Flow**:
1. Test suite runs existing software-dev mission tests
2. Test suite runs existing research mission tests
3. All tests pass (no regressions)

**Acceptance**: Existing tests pass, new tests added and passing

## Open Questions / Clarifications Needed

None identified at this stage. User has provided explicit requirements, scope boundaries, and acceptance criteria. Implementation can proceed directly to work package generation.

## Definition of Done

- [ ] `mission-runtime.yaml` created and merged to 2.x
- [ ] 4 command templates created and merged to 2.x
- [ ] Content templates created (if needed) and merged to 2.x
- [ ] Integration test added: feature creation + next command progression
- [ ] Resolver test added: all 4 steps resolve successfully
- [ ] Regression tests: software-dev and research missions still pass
- [ ] CI green on 2.x
- [ ] No doctrine path changes, no mainline changes, no PR146 side-effects
- [ ] Feature ready for implementation phase
