# Research: WP Metadata & State Type Hardening

**Mission**: 065-wp-metadata-state-type-hardening  
**Date**: 2026-04-06  
**Status**: Complete — all unknowns resolved via code investigation

---

## Finding 1 — Bootstrap Mutation Surface (#417)

**Decision**: The full set of frontmatter fields that `finalize-tasks` can write or overwrite is known from `src/specify_cli/cli/commands/agent/feature.py:1537–1622`.

**Mutation surface** (all 8 fields written unconditionally before the `--validate-only` fork):

| Field | Source | Condition |
|-------|--------|-----------|
| `dependencies` | Parsed from `tasks.md` via `_parse_dependencies_from_tasks_md()` | Written if field absent or differs from parsed value |
| `planning_base_branch` | Resolved by `_resolve_planning_branch()` | Written if differs from current value |
| `merge_target_branch` | Same as `target_branch` | Written if differs from current value |
| `branch_strategy` | Computed long-form string | Written if differs from current value |
| `requirement_refs` | Parsed from WP files and `tasks.md` | Written if field absent or differs |
| `execution_mode` | Inferred by `infer_ownership()` from WP body | Written only if field absent |
| `owned_files` | Inferred by `infer_ownership()` | Written only if field absent |
| `authoritative_surface` | Inferred by `infer_ownership()` | Written only if field absent |

**Root cause**: The writing loop (lines 1537–1622) runs before the `validate_only` branch at line 1676. The `validate_only` flag currently only suppresses `bootstrap_canonical_state()` writes and the final commit — it does NOT prevent the frontmatter writes above.

**Fix location**: `src/specify_cli/cli/commands/agent/feature.py:1620`  
```python
# Current (broken):
if frontmatter_changed:
    write_frontmatter(wp_file, frontmatter, body)
    updated_count += 1

# Fixed:
if frontmatter_changed and not validate_only:
    write_frontmatter(wp_file, frontmatter, body)
    updated_count += 1
```

**Alternatives considered**:
- Option B (preserve existing `dependencies` in bootstrap): Rejected — doesn't fix `branch_strategy`, `planning_base_branch`, and other fields that bootstrap also overwrites; partial fix only.
- Option C (rename flag): Rejected — violates the universally understood `--validate-only` / `--dry-run` contract.

---

## Finding 2 — tasks.md Header Regex Sites (#410)

**Decision**: Standardize all parsing sites to `#{2,4}` depth. There are 5 sites (the issue counts 4 primary + 1 section-boundary companion).

| Site | File | Line | Current pattern | Problem |
|------|------|------|-----------------|---------|
| WP section parse | `cli/commands/agent/feature.py` | 1953 | `^(?:##\s+(?:Work Package\s+)?\|###\s+)(WP\d{2})` | `####` not matched |
| Subtask inference | `status/emit.py` | 148 | `^##.*\b{wp_id}\b` | `####` not matched |
| Section end | `status/emit.py` | 151 | `^##\s+` | doesn't detect `####` section boundary |
| Subtask start | `cli/commands/agent/tasks.py` | 305 | `##.*{wp_id}\b` | `####` not matched |
| Section end | `cli/commands/agent/tasks.py` | 310 | `##.*WP\d{2}\b` | doesn't detect `####` section end |

**Standardized patterns**:
- WP header match: `^#{2,4}\s+(?:Work Package\s+)?(WP\d{2})(?:\b|:)`
- Section boundary (WP-specific): `^#{2,4}.*\b{wp_id}\b`
- Section end (any heading): `^#{2,4}\s+`

**Alternatives considered**: Requiring strict `##` depth via template enforcement — rejected because it creates a silent failure mode when LLMs deviate; the parser should be tolerant.

---

## Finding 3 — Existing Status Package Structures (#405)

**Decision**: `WPState` ABC and `TransitionContext` dataclass will live in `src/specify_cli/status/` alongside existing models.

**Existing structures to preserve**:
- `ALLOWED_TRANSITIONS: frozenset[tuple[str, str]]` at `transitions.py:31` — 16 allowed pairs; `WPState.allowed_targets()` must return an identical set for each lane.
- `_GUARDED_TRANSITIONS: dict[tuple[str, str], str]` at `transitions.py:61` — maps transition pairs to guard names; `WPState.can_transition_to()` must evaluate identical guard logic.
- `TERMINAL_LANES: frozenset[str]` at `transitions.py:29` — `{"done", "canceled"}`; `WPState.is_terminal` must match.
- `LANE_ALIASES: dict[str, str]` at `transitions.py:24` — `{"doing": "in_progress"}`; `DoingState` in the ABC hierarchy delegates to `InProgressState`.
- `Lane(StrEnum)` at `models.py:18` — 8 values: PLANNED, CLAIMED, IN_PROGRESS, FOR_REVIEW, APPROVED, DONE, BLOCKED, CANCELED.

**Note**: `Lane` has an `APPROVED` lane (line 25) not listed in the CLAUDE.md 7-lane description. The concrete state hierarchy must include `ApprovedState`.

**Highest-touch consumers for Phase 2 partial migration**:
- `orchestrator_api/commands.py` — 22 occurrences, `_RUN_AFFECTING_LANES = frozenset(["claimed", "in_progress", "for_review"])` ad-hoc
- `next/decision.py` — progress bucketing via if/elif lane chains
- `dashboard/scanner.py` — 18 occurrences, display bucketing

**Non-migrated consumers** (kept on old API, no changes required in this feature): all other files importing from `status.transitions`.

**Rationale**: ABC/dataclass inheritance chosen (Q1=B) over Protocol for explicit contract enforcement and IDE completeness checking. Each concrete class is a `@dataclass(frozen=True)` that inherits from `WPState`.

---

## Finding 4 — CI Job Structure (WP07)

**Decision**: Extract `tests/status/` and `tests/specify_cli/status/` into a new parallel `fast-tests-status` and `integration-tests-status` CI stage.

**Existing CI jobs** (from `.github/workflows/ci-quality.yml`):

```
kernel-tests
├── fast-tests-doctrine  (needs: kernel-tests)  → tests/doctrine/
├── fast-tests-core      (needs: kernel-tests)  → everything else
│   ├── integration-tests-doctrine  (needs: fast-doctrine + fast-core)
│   └── integration-tests-core      (needs: fast-doctrine + fast-core)
│       └── slow-tests / e2e-tests
```

**New parallel stage**:

```
kernel-tests
├── fast-tests-doctrine   (unchanged)
├── fast-tests-status     (NEW) → tests/status/ + tests/specify_cli/status/
├── fast-tests-core       (modified: --ignore=tests/status + --ignore=tests/specify_cli/status)
│   ├── integration-tests-doctrine  (unchanged)
│   ├── integration-tests-status    (NEW, needs: fast-tests-status + fast-tests-core)
│   └── integration-tests-core      (modified: same ignores)
```

**Rationale**: The status test suite (20 test files in `tests/specify_cli/status/`) is logically cohesive and directly related to this feature's changes. Separating it reduces flaky test coupling, improves parallelism, and gives faster feedback on status-layer regressions specifically. This is the first step of a broader core sub-module split strategy.

**Alternatives considered**: Splitting by `tests/specify_cli/` subdirectory only — `tests/status/` at the top level also contains status-related tests and should be co-located in the same CI stage.

---

## Finding 5 — WPMetadata Field Inventory (#410)

**Decision**: Base `WPMetadata` on `FrontmatterManager.WP_FIELD_ORDER` (16 fields in `frontmatter.py:41–58`) plus observed-in-practice additional fields.

**Required fields** (present in all active WP files):
- `work_package_id`, `title`, `dependencies`, `base_branch`, `base_commit`, `created_at`

**Optional fields** (present in post-0.11.0 files):
- `requirement_refs`, `planning_base_branch`, `merge_target_branch`, `branch_strategy`
- `subtasks`, `phase`, `assignee`, `agent`, `shell_pid`, `history`
- `execution_mode`, `owned_files`, `authoritative_surface`
- `mission_id`, `wp_code`, `branch_strategy_override`

**Migration path**: `extra="allow"` initially (no existing WP files require changes). Tighten to `extra="forbid"` after all consumers migrated and all files in `kitty-specs/` pass CI validation.
