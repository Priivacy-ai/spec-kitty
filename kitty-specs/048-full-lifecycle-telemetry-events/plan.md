# Implementation Plan: Full-Lifecycle Telemetry Events
*Path: kitty-specs/048-full-lifecycle-telemetry-events/plan.md*

**Branch**: `048-full-lifecycle-telemetry-events` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/048-full-lifecycle-telemetry-events/spec.md`

## Summary

Extend the 043 telemetry foundation to emit ExecutionEvents across all 5 kitty workflow phases (specify, plan, execute, review, merge). The core addition is a generic `spec-kitty agent telemetry emit` CLI command that slash command templates call at the end of each phase. This replaces the current pattern where events only emit when `--agent` and `--model` flags are both provided. Additionally, add `group_by="role"` support to the cost summary for per-phase cost breakdown.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer (CLI), rich (console output), spec_kitty_events (vendored event model)
**Storage**: Per-feature JSONL files (`kitty-specs/<feature>/execution.events.jsonl`) — append-only
**Testing**: pytest with 90%+ coverage, mypy --strict, ruff check
**Target Platform**: Cross-platform (Linux, macOS, Windows 10+)
**Project Type**: Single (Python CLI)
**Constraints**: Fire-and-forget emission (never block workflow), CLI operations < 2 seconds

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | ✅ Pass | Existing codebase requirement |
| Test-first (ATDD + TDD) | ✅ Will follow | Acceptance tests before implementation |
| mypy --strict | ✅ Will follow | Type hints on all new code |
| 90%+ coverage | ✅ Will follow | New CLI command + cost grouping fully tested |
| No spec-kitty-events changes | ✅ Pass | Uses existing Event model as-is |
| Locality of change | ✅ Pass | Changes scoped to telemetry CLI, cost module, and templates |

No constitution violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/048-full-lifecycle-telemetry-events/
├── spec.md              # Feature specification
├── plan.md              # This file
├── meta.json            # Feature metadata
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── execution.events.jsonl  # Telemetry events (dogfooding)
```

### Source Code Changes

```
src/specify_cli/
├── cli/commands/agent/
│   ├── telemetry.py          # ADD: `emit` command (new subcommand on existing typer app)
│   ├── feature.py            # MODIFY: Remove `if agent and model` gate on existing emissions
│   └── workflow.py            # MODIFY: Remove `if agent and model` gate on existing emissions
├── telemetry/
│   └── cost.py               # MODIFY: Add group_by="role" support to cost_summary()
└── missions/software-dev/command-templates/
    ├── specify.md             # MODIFY: Add telemetry emit step at end
    ├── plan.md                # MODIFY: Add telemetry emit step at end
    ├── tasks.md               # MODIFY: Add telemetry emit step at end
    ├── review.md              # MODIFY: Add telemetry emit step at end (supplement move-task)
    └── merge.md               # MODIFY: Add telemetry emit step at end

tests/specify_cli/
├── telemetry/
│   ├── test_emit_command.py   # NEW: Tests for `spec-kitty agent telemetry emit`
│   └── test_cost.py           # MODIFY: Add tests for group_by="role"
└── cli/commands/agent/
    ├── test_telemetry_cli.py  # NEW: Integration tests for emit CLI
    ├── test_feature.py        # MODIFY: Test emission without --agent/--model flags
    └── test_workflow.py       # MODIFY: Test emission without --agent/--model flags
```

**Structure Decision**: All changes fit within the existing module structure. No new packages or architectural changes needed.

## Design Decisions

### 1. Generic Emit Command vs Per-Phase Commands

**Decision**: Single `spec-kitty agent telemetry emit` command with `--role` flag.

**Rationale**: The existing telemetry system already has `emit_execution_event()` which accepts a `role` parameter. A single CLI wrapper with `--role specifier|planner|implementer|reviewer|merger` is simpler than 5 separate commands and matches the existing API.

### 2. Template-Driven Emission

**Decision**: Slash command templates call the emit command as their final step.

**Rationale**: The CLI commands (create-feature, setup-plan) run at the **beginning** of a phase, not the end. The agent runtime does the actual work. Only the template controls when the phase is "done" — so the template's final step is the natural completion hook.

**Template emit step pattern**:
```markdown
## Telemetry (final step)

After completing all steps above, emit a telemetry event:

\```bash
spec-kitty agent telemetry emit \
  --feature <feature-slug> \
  --role <phase-role> \
  --agent <agent-name> \
  --model <model-id>
\```

Include `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms` if your agent runtime provides usage metrics.
```

### 3. Always-Emit Policy

**Decision**: Remove the `if agent and model` guard from existing emissions. Emit events with whatever data is available.

**Rationale**: An event with only `role`, `feature_slug`, and `timestamp` is still valuable — it proves the phase occurred. Silently skipping emission when flags are missing defeats the purpose of lifecycle tracking.

### 4. Cost Summary group_by="role"

**Decision**: Add "role" as a valid `group_by` value to `cost_summary()` and the `cost` CLI command.

**Rationale**: The `role` field in the event payload already encodes the phase (specifier, planner, implementer, reviewer, merger). Adding it as a grouping dimension requires minimal code change — just a new elif branch in `cost_summary()` and a new choice in the CLI.

### 5. Migration for Template Updates

**Decision**: Use config-aware `get_agent_dirs_for_project()` to propagate template updates to all configured agents.

**Rationale**: Per CLAUDE.md, template changes must propagate to all 12 agents. The migration system already handles this pattern.

## Complexity Tracking

No constitution violations to justify.

## Implementation Phases

### Phase 1: CLI Emit Command + Cost Grouping (Core)

1. Add `emit` subcommand to `src/specify_cli/cli/commands/agent/telemetry.py`
   - Flags: `--feature` (required), `--role` (required), `--agent`, `--model`, `--input-tokens`, `--output-tokens`, `--cost-usd`, `--duration-ms`, `--success` (default true), `--wp-id` (default "N/A")
   - Resolves feature directory from `kitty-specs/<feature>/`
   - Calls `emit_execution_event()` — fire-and-forget with exit code 0 always
   - JSON output mode for programmatic use

2. Add `group_by="role"` to `cost_summary()` in `src/specify_cli/telemetry/cost.py`
   - New elif branch: `key = payload.get("role", "unknown")`
   - Add "role" to `click.Choice` in the cost CLI command

3. Remove `if agent and model` gate in `feature.py` and `workflow.py`
   - Change to always emit, with `agent` defaulting to `"unknown"` when not provided

### Phase 2: Template Updates

4. Update slash command templates to include telemetry emit as final step:
   - `specify.md` — emit with `--role specifier`
   - `plan.md` — emit with `--role planner`
   - `tasks.md` — emit with `--role planner` (task generation is part of planning)
   - `review.md` — emit with `--role reviewer` (supplements move-task emission)
   - `merge.md` — emit with `--role merger`

5. Create migration to propagate template updates to all configured agents

### Phase 3: Tests

6. Unit tests for emit CLI command
7. Unit tests for `group_by="role"` cost aggregation
8. Integration tests for always-emit behavior (no --agent/--model flags)
