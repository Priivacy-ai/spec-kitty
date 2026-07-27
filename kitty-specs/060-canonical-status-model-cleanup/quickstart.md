# Quickstart: Canonical Status Model Cleanup

## What This Feature Does

Enforces the 3.0 canonical status model: WP status lives only in `status.events.jsonl`, never in WP frontmatter. Removes dual-authority runtime fallbacks, cleans templates/tests, and hard-fails when canonical state is missing.

## Implementation Sequence

```
Phase A: Bootstrap (finalize-tasks seeds canonical state)
    ↓
Phase B: Generators/Tests (templates + fixtures go lane-free)
    ↓
Phase C: Remove Fallbacks (runtime reads canonical only, hard-fails on missing)
    ↓
Phase D: Fence + Docs (migration-only markers, doc updates, regression tests)
```

**Sequential only** — each phase depends on the previous one.

## Key Files

### Phase A (Bootstrap)
| File | Change |
|------|--------|
| `cli/commands/agent/feature.py` | finalize-tasks emits initial planned events |
| `cli/commands/agent/tasks.py` | finalize-tasks emits initial planned events |
| New: shared bootstrap helper | Scan WPs → check event log → emit → materialize |

### Phase B (Generators/Tests)
| File | Change |
|------|--------|
| `missions/*/templates/task-prompt-template.md` | Remove lane activity log examples |
| `missions/software-dev/templates/tasks-template.md` | Remove lane field docs |
| `missions/software-dev/command-templates/tasks.md` | Remove frontmatter lane from WP examples |
| `tests/conftest.py` | Remove lane from WP fixtures |

### Phase C (Remove Fallbacks)
| File | Change |
|------|--------|
| `tasks_support.py` | WorkPackage.lane: event-log-only, no frontmatter fallback |
| `dashboard/scanner.py` | Remove frontmatter fallback in lane counting |
| `mission_v1/guards.py` | Delete _read_lane_from_frontmatter |
| `next/runtime_bridge.py` | Use lane_reader instead of frontmatter |
| `cli/commands/agent/tasks.py:1088-1115` | Delete bootstrap/sync block in move_task |

### Phase D (Fence + Docs)
| File | Change |
|------|--------|
| `task_metadata_validation.py` | Mark repair_lane_mismatch as migration-only |
| Docs, README, CLAUDE.md | Update status model descriptions |
| New regression tests | Grep-scan for lane in active templates and non-migration code |

## Canonical Status Cheat Sheet

| Question | Answer |
|----------|--------|
| Where does WP lane live? | `status.events.jsonl` (sole authority) |
| What is `status.json`? | Derived snapshot from reducer (read-only view) |
| What is WP frontmatter for? | Static definition + operational metadata only |
| When is canonical state created? | `finalize-tasks` (after `/spec-kitty.tasks`) |
| What happens if event log is missing? | Runtime hard-fails with guidance |
| What happens if WP has no events? | Read commands show "uninitialized"; mutating commands hard-fail |
| Can I read lane from frontmatter? | Only in migration-only code paths |
| Can I write lane to frontmatter? | Only in migration-only code paths |

## Error Messages

Missing event log:
```
Canonical status not found for feature <slug>.
Run `spec-kitty agent feature finalize-tasks --feature <slug>` to bootstrap status.
```

WP without canonical state (mutating command):
```
WP <id> has no canonical status in feature <slug>.
Run `spec-kitty agent feature finalize-tasks --feature <slug>` to initialize.
```

## Regression Tests

After all phases, two regression tests guard against reintroduction:

1. **Template scan**: Grep active template files for `^lane:` in YAML frontmatter position → fail if found
2. **Code scan**: Grep non-migration Python files for `frontmatter.*lane` or `["lane"]` patterns → fail if found outside migration modules
