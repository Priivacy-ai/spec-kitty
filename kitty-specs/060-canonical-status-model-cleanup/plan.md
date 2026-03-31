# Implementation Plan: Canonical Status Model Cleanup

**Branch**: `main` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/060-canonical-status-model-cleanup/spec.md`

## Summary

Enforce the 3.0 canonical status model across the spec-kitty codebase. Bootstrap-first sequencing: (1) add canonical state seeding to finalize-tasks, (2) convert generators/templates/tests to lane-free WPs, (3) remove runtime frontmatter-lane fallbacks and hard-fail on missing canonical state, (4) fence remaining migration-only paths. Net effect: `status.events.jsonl` becomes the sole runtime authority for WP lane state.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), pydantic (status models)
**Storage**: Filesystem only — YAML frontmatter, JSONL event logs, JSON materialized snapshots
**Testing**: pytest (90%+ coverage on new code), mypy --strict
**Target Platform**: Cross-platform CLI
**Project Type**: Single Python package (spec-kitty CLI)
**Constraints**: ~2000+ existing tests; bootstrap-first sequencing to avoid wide test breakage
**Scale/Scope**: ~15 files modified across runtime, templates, tests, and docs

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Python 3.11+ | PASS | |
| typer for CLI | PASS | |
| pytest with 90%+ coverage | PASS | NFR-002 |
| mypy --strict | PASS | NFR-003 |
| TEST_FIRST directive | PASS | Bootstrap added first, then tests converted |

No violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/060-canonical-status-model-cleanup/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── tasks/
```

### Source Code (affected files by phase)

```
src/specify_cli/
├── cli/commands/agent/
│   ├── feature.py           # MODIFY: finalize-tasks bootstrap (Phase A)
│   └── tasks.py             # MODIFY: finalize-tasks bootstrap (Phase A), remove fallback (Phase C)
├── tasks_support.py         # MODIFY: remove frontmatter lane fallback in WorkPackage.lane (Phase C)
├── dashboard/scanner.py     # MODIFY: remove frontmatter fallback in _count_wps_by_lane_frontmatter (Phase C)
├── mission_v1/guards.py     # MODIFY: remove _read_lane_from_frontmatter (Phase C)
├── next/runtime_bridge.py   # MODIFY: remove frontmatter lane read (Phase C)
├── task_metadata_validation.py  # MODIFY: remove repair_lane_mismatch or demote to migration (Phase C/D)
├── status/
│   └── lane_reader.py       # KEEP: already event-log-only (no changes needed)
├── missions/
│   ├── software-dev/templates/
│   │   ├── tasks-template.md         # MODIFY: remove lane field references (Phase B)
│   │   └── task-prompt-template.md   # MODIFY: remove lane activity log examples (Phase B)
│   ├── research/templates/
│   │   └── task-prompt-template.md   # MODIFY: same lane cleanup (Phase B)
│   └── documentation/templates/
│       └── task-prompt-template.md   # MODIFY: same lane cleanup (Phase B)
├── upgrade/migrations/
│   ├── m_0_9_1_complete_lane_migration.py  # KEEP: migration-only (Phase D fence)
│   └── m_2_0_6_consistency_sweep.py        # KEEP: migration-only (Phase D fence)
└── migration/
    └── strip_frontmatter.py  # KEEP: migration-only (Phase D fence)

tests/
├── conftest.py              # MODIFY: remove lane from WP fixtures (Phase B)
└── [various test files]     # MODIFY: update tests that assert frontmatter lane (Phase B/C)
```

## Architecture

### Current State (Dual Authority)

```
WP Frontmatter (lane:)  ←── fallback source ──→  status.events.jsonl (canonical)
        ↑                                                   ↑
        │                                                   │
   templates emit                                   emit_status_transition()
   lane: "planned"                                  writes StatusEvent
        │                                                   │
        ↓                                                   ↓
   tests construct                                  reducer → status.json
   WPs with lane:                                   (materialized snapshot)
```

### Target State (Single Authority)

```
WP Frontmatter                          status.events.jsonl (sole authority)
  (static definition                              ↑
   + operational metadata)               emit_status_transition()
  No lane, review_status,                         │
  review_feedback, progress              finalize-tasks seeds initial "planned"
                                                  │
                                                  ↓
                                          reducer → status.json
                                          (materialized snapshot)
                                                  │
                                          all runtime reads go here
```

### Codebase Inventory (from research)

**Frontmatter lane READ sites** (to be removed in Phase C):
| File | Function | Current behavior |
|------|----------|-----------------|
| `tasks_support.py:293` | `WorkPackage.lane` | Event log first, fallback frontmatter |
| `dashboard/scanner.py:322` | `_count_wps_by_lane_frontmatter()` | Event log first, fallback frontmatter |
| `mission_v1/guards.py:169` | `_read_lane_from_frontmatter()` | Direct frontmatter read |
| `next/runtime_bridge.py:117` | `resolve_action_context()` | `wp_state.get("lane", "planned")` |

**Frontmatter lane WRITE sites** (migration-only after Phase D):
| File | Function | Current behavior |
|------|----------|-----------------|
| `task_metadata_validation.py:123` | `repair_lane_mismatch()` | Writes lane to frontmatter |
| `m_2_0_6_consistency_sweep.py:203` | Normalize | Reads+writes frontmatter lane |
| `m_0_9_1_complete_lane_migration.py:331` | `_ensure_lane_in_frontmatter()` | Creates frontmatter lane |

**Bootstrap/sync site** (to be removed in Phase C):
| File | Function | Current behavior |
|------|----------|-----------------|
| `tasks.py:1088-1115` | `move_task()` bootstrap | Seeds event from frontmatter when canonical is missing |

**Template sites** (to be cleaned in Phase B):
- `missions/software-dev/templates/tasks-template.md` (lane field docs)
- `missions/*/templates/task-prompt-template.md` (lane activity log examples)
- `missions/software-dev/command-templates/tasks.md` and `tasks-packages.md` (WP examples with lane)

**Already clean** (no changes needed):
- `status/lane_reader.py` — event-log-only
- `move_task()` lane WRITE — already event-log-only via `emit_status_transition()`

## Implementation Phases

### Phase A: Canonical Bootstrap in finalize-tasks

Add canonical state seeding to both finalize-tasks entrypoints. After this phase, every finalized feature has guaranteed canonical state.

**Files**: `feature.py`, `tasks.py` (finalize-tasks functions)

Changes:
1. After existing dependency parsing + validation, scan WP files in the feature
2. For each WP, check if `status.events.jsonl` has any event for that WP
3. If no event exists, call `emit_status_transition()` with `to_lane="planned"`, `actor="finalize-tasks"`, `force=True`
4. After all WPs seeded, call `materialize()` to write `status.json`
5. For `--validate-only`: report which WPs lack canonical state, what would be emitted, without mutating files
6. Both entrypoints must produce identical results (shared helper function)

**Dependencies**: None — this phase adds new behavior without removing old behavior.

### Phase B: Convert Generators and Tests

Update templates and test fixtures so new WPs are generated without frontmatter lane fields.

**Files**: Mission templates, command templates, `tests/conftest.py`, various test files

Changes:
1. Remove `lane: "planned"` from all active WP template frontmatter examples
2. Remove `review_status`, `reviewed_by`, `review_feedback`, `progress` from template frontmatter
3. Remove `lane=` from body activity log examples in templates
4. Remove `history[].lane` from template history examples; keep `at`, `actor/agent`, `action`
5. Update `tests/conftest.py` WP fixtures to omit `lane` from frontmatter
6. Update test files that assert `lane:` in modern WP frontmatter (except migration tests)
7. Add regression test: grep active templates for `^lane:` in frontmatter position → fail if found

**Dependencies**: Phase A must be complete (tests need canonical bootstrap to work without lane).

### Phase C: Remove Runtime Fallbacks + Hard-Fail

Strip frontmatter-lane fallback from all runtime readers. Replace with canonical-only reads and hard-fail on missing state.

**Files**: `tasks_support.py`, `dashboard/scanner.py`, `mission_v1/guards.py`, `next/runtime_bridge.py`, `tasks.py` (bootstrap logic), `task_metadata_validation.py`

Changes:
1. `tasks_support.py:WorkPackage.lane` — remove frontmatter fallback, read event log only. If no canonical state and event log absent: raise with finalize-tasks guidance.
2. `dashboard/scanner.py:_count_wps_by_lane_frontmatter()` — remove frontmatter fallback branch. If event log exists but WP has no event: return "uninitialized". If event log absent: hard-fail.
3. `mission_v1/guards.py:_read_lane_from_frontmatter()` — delete or redirect to event log reader.
4. `next/runtime_bridge.py` — use `get_wp_lane()` from `lane_reader.py` instead of `wp_state.get("lane")`.
5. `tasks.py:move_task()` lines 1088-1115 — delete the frontmatter bootstrap/sync block entirely. If canonical state is missing, hard-fail.
6. `task_metadata_validation.py:repair_lane_mismatch()` — demote to migration-only (see Phase D).

**Dependencies**: Phase A and B must be complete (canonical state exists, tests don't rely on frontmatter).

### Phase D: Fence Migration-Only Paths + Docs

Mark remaining frontmatter-lane readers as migration-only. Update docs.

**Files**: `task_metadata_validation.py`, migration files, docs, README, command help

Changes:
1. `repair_lane_mismatch()` — move to migration-only context or add clear `@migration_only` marker/docstring
2. Existing migrations (`m_0_9_1`, `m_2_0_6`) — no code changes, but add docstring noting these are legacy migration paths that read/write frontmatter lane
3. `migration/strip_frontmatter.py` — no code changes, already migration-only
4. Update active docs: README, CLAUDE.md status model sections, command help text
5. Relabel old "frontmatter-only lane" documentation as historical
6. Add regression test: scan all non-migration Python files for `frontmatter.*lane` or `["lane"]` patterns → fail if found outside migration modules

**Dependencies**: Phase C must be complete.

## Dependency Order

```
Phase A (bootstrap) ← no deps
Phase B (generators/tests) ← Phase A
Phase C (remove fallbacks) ← Phase A, Phase B
Phase D (fence + docs) ← Phase C
```

No parallelization — each phase depends on the previous one. This is the controlled cutover sequence.

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Wide test breakage during Phase B | Run full test suite after each template/fixture change; Phase A guarantees canonical state exists |
| Legacy features without event log | Phase C hard-fail directs users to finalize-tasks; migration tools preserved in Phase D |
| Template changes reintroducing lane later | Phase B adds grep-based regression test scanning active templates |
| Missed frontmatter lane reads | Phase D adds code-scanning regression test for non-migration modules |
