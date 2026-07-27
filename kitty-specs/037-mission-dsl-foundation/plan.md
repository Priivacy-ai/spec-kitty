# Implementation Plan: Mission DSL Foundation

**Branch**: `037-mission-dsl-foundation` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Target Branch**: `2.x`
**Depends On**: Phase 1A (036-kittify-runtime-centralization) merged

## Summary

Replace static YAML phase lists in mission definitions with enforced state machine workflows powered by the `transitions` library (pytransitions). Define a v1 Mission YAML schema with states, transitions, guards (6 declarative expression primitives), typed inputs/outputs, and on_enter/on_exit hooks. Load via `MarkupMachine` with `auto_transitions=False` and `send_event=True`. Maintain backward compatibility with v0 phase-list missions via a `PhaseMission` wrapper. Define 3 differentiated missions (software-dev, research, plan). Provide a provisional `emit_event()` interface as a thin boundary for Phase 2.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: `transitions>=0.9.2` (new), pydantic v2, PyYAML, jsonschema (existing)
**Storage**: Filesystem only (YAML mission configs, JSONL event logs)
**Testing**: pytest (existing suite of 2032+ tests)
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows)
**Project Type**: Single Python package (`specify_cli`)
**Performance Goals**: Mission loading <200ms including schema validation and machine construction
**Constraints**: Must not break existing 2032+ test suite; v0 backward compat required

## Constitution Check

*No constitution file found — section skipped.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/037-mission-dsl-foundation/
├── spec.md               # Feature specification
├── plan.md               # This file
├── meta.json             # Feature metadata
├── checklists/
│   └── requirements.md   # Quality checklist
├── research.md           # Phase 0 research output
├── data-model.md         # Phase 1 data model
└── tasks.md              # Work package breakdown
```

### Source Code (repository root)

```
src/specify_cli/
├── mission.py                       # EXISTING: Mission class, MissionConfig (Pydantic v2)
│                                    #   MODIFY: Add load_mission() entry point with v0/v1 dispatch
│
├── mission_v1/                      # NEW subpackage: v1 state machine missions
│   ├── __init__.py                  # Public API: StateMachineMission, PhaseMission, load_mission
│   ├── schema.py                    # JSON Schema definition for v1 mission YAML
│   ├── runner.py                    # MissionRunner: MarkupMachine wrapper + model
│   ├── guards.py                    # Guard expression compiler (6 primitives)
│   ├── events.py                    # Provisional emit_event() interface
│   └── compat.py                    # PhaseMission v0 wrapper
│
├── missions/                        # EXISTING: mission YAML directories
│   ├── software-dev/
│   │   └── mission.yaml             # MODIFY: Add v1 state machine definition
│   ├── research/
│   │   └── mission.yaml             # MODIFY: Add v1 state machine definition
│   ├── plan/                        # NEW: plan mission
│   │   └── mission.yaml             # NEW: v1 state machine definition
│   └── documentation/
│       └── mission.yaml             # KEEP: v0 format (backward compat demo)
│
tests/
├── unit/
│   └── mission_v1/                  # NEW: unit tests for v1 mission system
│       ├── test_schema.py           # Schema validation tests
│       ├── test_runner.py           # MarkupMachine runner tests
│       ├── test_guards.py           # Guard expression compiler tests
│       ├── test_events.py           # emit_event tests
│       └── test_compat.py           # PhaseMission v0 wrapper tests
│
├── integration/
│   ├── test_mission_loading.py      # NEW: v0/v1 dispatch + 3 mission loading
│   └── test_mission_guards.py       # NEW: guard evaluation with feature context
```

**Structure Decision**: New `mission_v1/` subpackage alongside existing `mission.py`. The existing `Mission` class stays unchanged. `load_mission()` in `mission_v1/__init__.py` is the new entry point that dispatches v0 vs v1. The existing `Mission` class is wrapped by `PhaseMission` for v0 compat.

## Key Design Decisions

### D1: New subpackage vs modifying mission.py

**Decision**: New `mission_v1/` subpackage.
**Rationale**: `mission.py` is 748 lines with stable Pydantic models. Adding ~500 lines of state machine code would create a monolith. A subpackage allows clean separation of concerns while the existing module stays backward-compatible.

### D2: MarkupMachine loading approach

**Decision**: Load mission YAML, extract `states`/`transitions`/`initial` keys, pass as dict to `MarkupMachine(**config)`.
**Rationale**: MarkupMachine natively accepts dict configs matching its serialization format. No custom parser needed. The YAML schema maps directly to MarkupMachine's expected input.

### D3: Guard expression compilation

**Decision**: Parse guard expression strings (e.g., `artifact_exists("spec.md")`) at load time into bound methods on the model. Use a registry of 6 guard factories.
**Rationale**: Compile-time validation catches typos early. Runtime evaluation is a simple method call. The registry is extensible for future phases.

### D4: Event emission boundary

**Decision**: `emit_event(type: str, payload: dict)` writes to a JSONL file in the feature directory. No event store integration in Phase 1B.
**Rationale**: Thin boundary that Phase 2 can replace. JSONL is simple, human-readable, and doesn't require additional dependencies.

### D5: PhaseMission adapter pattern

**Decision**: `PhaseMission` wraps a v0 `Mission` object and generates a synthetic linear state machine with auto-generated transitions (phase1 -> phase2 -> ... -> done).
**Rationale**: Existing callers using `Mission.get_workflow_phases()` continue to work. New code can use the state machine interface uniformly.

### D6: JSON Schema validation approach

**Decision**: Use `jsonschema` library (already available in the ecosystem) for v1 schema validation before MarkupMachine construction.
**Rationale**: JSON Schema provides declarative validation with precise error messages. Pydantic v2 would require new model classes for the v1 format, duplicating the MarkupMachine config. JSON Schema validates the YAML dict directly.

## Data Model

### v1 Mission YAML Schema

```yaml
# Top-level v1 mission structure
mission:
  name: string           # Machine-readable identifier
  version: string        # Semantic version (X.Y.Z)
  description: string
  display_name: string   # Optional human name

initial: string          # Initial state name (must match a state name)

states:
  - name: string         # State identifier
    display_name: string # Optional
    on_enter: [string]   # Callback method names
    on_exit: [string]    # Callback method names

transitions:
  - trigger: string      # Trigger name (becomes a method on the model)
    source: string | [string]  # Source state(s)
    dest: string         # Destination state
    conditions: [string] # Guard expression strings (AND logic)
    unless: [string]     # Guard expression strings (AND-NOT logic)
    before: [string]     # Pre-transition callbacks
    after: [string]      # Post-transition callbacks

inputs:                  # Optional typed inputs
  - name: string
    type: string | path | url | boolean | integer
    required: boolean
    description: string
    default: any         # Optional default value

outputs:                 # Optional typed outputs
  - name: string
    type: artifact | report | data
    path: string
    phase: string        # Which state produces this output
    description: string

guards:                  # Named guard definitions
  guard_name:
    description: string
    check: string        # Declarative expression

# Legacy v0 fields preserved for backward compat
workflow:
  phases: [...]          # Ignored when states/transitions present
artifacts: {...}
paths: {...}
validation: {...}
mcp_tools: {...}
agent_context: string
task_metadata: {...}
commands: {...}
```

### Guard Expression Primitives

| Expression | Arguments | Returns True When |
|-----------|-----------|-------------------|
| `artifact_exists("path")` | Relative path string | File exists in feature directory |
| `gate_passed("name")` | Gate name string | GatePassed event recorded in event log |
| `all_wp_status("status")` | Status string | All WPs in current phase have this status |
| `any_wp_status("status")` | Status string | At least one WP has this status |
| `input_provided("name")` | Input name string | Named input was provided to the run |
| `event_count("type", min)` | Event type string, int | At least N events of type in log |

### Event Payload Schema

```python
{
    "type": str,            # e.g., "phase_entered", "guard_failed", "guard_passed"
    "timestamp": str,       # ISO 8601
    "mission": str,         # Mission name
    "payload": {            # Type-specific data
        "state": str,       # Current state (for phase events)
        "guard": str,       # Guard name (for guard events)
        "args": list,       # Guard arguments
        "reason": str,      # Failure reason (for guard_failed)
    }
}
```

## Complexity Tracking

No constitution violations. All complexity is necessary for the feature scope.

## Research Notes

### transitions library (pytransitions)

- Version 0.9.3 (latest), MIT license, 6.3k+ GitHub stars
- `MarkupMachine` supports dict-based config loading (ideal for YAML)
- `auto_transitions=False` prevents unguarded `to_<state>()` methods
- `send_event=True` passes `EventData` to all callbacks (carries kwargs, transition metadata)
- Callback execution order: prepare → conditions → unless → before_state_change → before → on_exit → [STATE CHANGE] → on_enter → after → after_state_change → finalize_event
- `conditions` = AND logic (all must return True), `unless` = AND-NOT (all must return False)
- NOT currently in pyproject.toml — must be added as dependency

### Existing mission.py analysis

- `MissionConfig` (Pydantic v2) validates v0 format with `extra="forbid"`
- `Mission` class wraps config with template/command resolution
- `get_workflow_phases()` returns list of dicts — callers use this for phase names
- `discover_missions()` scans `.kittify/missions/` for mission.yaml files
- `get_mission_for_feature()` reads meta.json for per-feature mission key
- No callers currently enforce phase ordering — all advisory
- v0 `MissionConfig.workflow.phases` has `min_length=1`

### Integration points

- `load_mission()` will be the new entry point, called by `get_mission_by_name()` and `Mission.__init__()`
- Guards need access to: feature directory (for artifact_exists), event log (for gate_passed/event_count), WP status (for all_wp_status/any_wp_status)
- `emit_event()` writes to `<feature_dir>/events.jsonl` (NOT the status events.jsonl from feature 034)
