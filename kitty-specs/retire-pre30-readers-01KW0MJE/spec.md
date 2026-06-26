# Spec: Retire pre-3.0 status/task readers from active runtime

**Mission ID**: 01KW0MJEK2JFDM8VP8Q0EVY1P6  
**Mission Slug**: retire-pre30-readers-01KW0MJE  
**Mission Type**: software-dev  
**Status**: Draft  
**Created**: 2026-06-26  

---

## Problem Statement

The canonical status model since 3.0 is the append-only event log (`status.events.jsonl`) plus derived snapshots (`status.json`). WP frontmatter is for static definition only; the `lane` frontmatter field is a historical/migration-only concept. Yet the active runtime still branches on pre-3.0 project shapes — lane-directory layouts (`tasks/planned/`, `tasks/doing/`, etc.) and frontmatter-lane state — through `is_legacy_format()` calls scattered across task commands, the dashboard, and acceptance scanning. This keeps obsolete code on the hot path and forces every command that touches a WP to handle two different storage shapes indefinitely.

**Root cause**: `legacy_detector.py` lives in the active runtime import graph and is imported by `task_utils/support.py`, `tasks_cli.py`, `dashboard/scanner.py`, `acceptance/__init__.py`, and several other active modules. Every importer re-introduces a `if use_legacy:` branch that can never be removed while unmigrated projects are silently tolerated.

**Desired end state**: Active runtime commands assume a post-3.0 project shape (flat `tasks/WP*.md`, status from `status.events.jsonl`, `mission_id` present). Pre-3.0 projects are detected at the command boundary and fail with a clear migration message. Lane-directory and frontmatter-lane readers survive only inside migration/upgrade code paths, not in production command paths.

---

## Intent Summary

A developer running any active `spec-kitty` command against an unmigrated pre-3.0 project (one that still uses `tasks/{lane}/` subdirectories) receives a non-zero exit with the message:  
> "Pre-3.0 layout detected (tasks/{lane}/ directories or frontmatter lane state). Run `spec-kitty upgrade` to migrate before continuing."  
No mutation occurs. The `spec-kitty upgrade` command continues to work exactly as before — it still locates the lane-directory detector and migrates the project.

---

## Scope

**In scope:**
- Relocating `legacy_detector.py` (and its exports `is_legacy_format`, `get_legacy_lane_counts`, `LEGACY_LANE_DIRS`) from the active runtime import graph to a migration/upgrade-only namespace.
- Adding a command-boundary guard that detects pre-3.0 lane-directory shapes, emits the hard-reject message, and returns non-zero.
- Removing `is_legacy_format()` branch logic from active task/status command paths (`tasks_cli.py`, `task_utils/support.py` → `locate_work_package`, `dashboard/scanner.py`, `acceptance/__init__.py`).
- Verifying all removal targets have zero callers in the active runtime before deletion; de-exporting rather than deleting any symbol still used elsewhere.
- Updating tests that normalize legacy fixtures through active runtime paths to use the upgrade path instead.
- Correcting documentation sections that still describe frontmatter `lane` as a live workflow authority.

**Out of scope (deferred):**
- Compatibility inventory and sunset-policy tooling (issue #1059).
- The `--feature` CLI alias migration (issue #1060 / sibling mission).
- Stripping `feature_slug` / `mission_id=None` tolerance from low-level status readers and the reducer — those retain defensive tolerance per LOCKED decision 1.
- Any changes to `spec-kitty upgrade` command behaviour; it must continue to work without change.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | Active task/status commands detect a pre-3.0 project shape (presence of `tasks/{lane}/` subdirectories containing `.md` files) at the command boundary and exit with a non-zero code before any mutation. | Required |
| FR-002 | The hard-reject error message instructs the user to run `spec-kitty upgrade` and identifies which project shape triggered the rejection (lane-directory layout or frontmatter lane state). | Required |
| FR-003 | `legacy_detector.py` (and its public symbols `is_legacy_format`, `get_legacy_lane_counts`, `LEGACY_LANE_DIRS`) is relocated to the migration/upgrade-only namespace (`specify_cli.upgrade.*`) and is no longer importable from the active runtime package surface without a deprecation path. | Required |
| FR-004 | The `is_legacy_format()` branch in `locate_work_package` (`task_utils/support.py`) is removed; the function operates exclusively on the flat `tasks/WP*.md` layout. | Required |
| FR-005 | The `is_legacy_format()` branches in `tasks_cli.py` are removed; the affected commands reject pre-3.0 shapes via the boundary guard (FR-001) before reaching these paths. | Required |
| FR-006 | The `is_legacy_format()` branches in `dashboard/scanner.py` are removed or replaced with a read-only audit path that is not on the mutation hot path. | Required |
| FR-007 | The `is_legacy_format()` branches in `acceptance/__init__.py` are removed; the acceptance scan rejects or skips unmigrated missions with a clear log entry rather than silently normalizing them. | Required |
| FR-008 | Before any symbol is removed, its callers in the active runtime are proven to be zero (grep + import-graph audit). Load-bearing internals that have residual callers are de-exported (removed from `__all__` / public surface) rather than deleted outright. | Required |
| FR-009 | `spec-kitty upgrade` continues to locate and execute the lane-directory migration without any regression; the `m_0_9_0_frontmatter_only_lanes` migration and the upgrade runner are not functionally changed. | Required |
| FR-010 | Tests that previously injected legacy `tasks/{lane}/` fixtures into active runtime code paths are updated to route through `spec-kitty upgrade` (or a migration helper) first, or are converted to upgrade-path tests rather than runtime-path tests. | Required |
| FR-011 | Documentation sections in `docs/status-model.md` and any other doc pages that describe frontmatter `lane` as a live workflow mechanism are updated to mark it as historical/migration-only with a pointer to `spec-kitty upgrade`. | Required |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Deletion safety: no symbol is removed until a zero-caller audit (import-graph + grep) over the active runtime has been completed and recorded in the PR description. | 100% coverage — every removed symbol has a corresponding audit note. | Required |
| NFR-002 | `spec-kitty upgrade` regression: the upgrade command passes its existing integration test suite without modification. | 0 regressions in `tests/` upgrade-path tests. | Required |
| NFR-003 | Active command cold-start overhead: the boundary guard check must not add more than 5 ms to the cold-start path of any command that previously did not stat the `tasks/` directory. | ≤5 ms added latency on a warm filesystem. | Required |
| NFR-004 | Test coverage for the boundary guard: the new hard-reject path must be covered by at least one positive test (pre-3.0 fixture → non-zero exit + correct message) and at least one negative test (post-3.0 fixture → normal execution continues). | ≥2 tests, both in CI green. | Required |
| NFR-005 | Low-level status readers and the event-log reducer retain their existing defensive tolerance for `feature_slug` / `mission_id=None` — these internal paths are NOT tightened in this mission. | Zero changes to `status/store.py` slug/id tolerance logic. | Required |
| NFR-006 | The hard-reject exit code is non-zero and consistent (use exit code 1 or the project-standard error code). No mutation to the project's `kitty-specs/` or any WP file occurs before the guard fires. | 0 mutations observed in pre-3.0 fixture tests. | Required |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Prove zero callers before removal; de-export rather than delete load-bearing internals. The spec explicitly requires this as a mandatory step, not a best-effort check. (Covers LOCKED decision 4.) | Required |
| C-002 | The boundary guard does NOT auto-invoke `spec-kitty upgrade`. It only emits the message and exits. (Covers LOCKED decision 2.) | Required |
| C-003 | `legacy_detector.py` is relocated, not deleted. The migration/upgrade namespace retains full access to `is_legacy_format`, `get_legacy_lane_counts`, and `LEGACY_LANE_DIRS`. (Covers LOCKED decision 3.) | Required |
| C-004 | Low-level status readers (`status/store.py`, `status/reducer.py`) and the reducer's `feature_slug` / `mission_id=None` tolerance are out of scope and must not be changed. (Covers LOCKED decision 1.) | Required |
| C-005 | This mission does not touch the `--feature` CLI alias surface. That is deferred to issue #1060. | Required |
| C-006 | This mission does not build the compatibility-inventory or sunset-policy tooling. That is deferred to issue #1059. | Required |

---

## User Scenarios and Acceptance Scenarios

### Scenario A — Developer runs task command on an unmigrated pre-3.0 project

**Actor**: Developer (CLI user)  
**Trigger**: Runs any active task/status mutation command (e.g., `spec-kitty agent tasks status`, `spec-kitty agent status emit`) targeting a mission that still has `tasks/planned/` or `tasks/doing/` subdirectories containing `.md` files.  
**Happy path**: Command immediately prints the hard-reject message, exits non-zero, and writes nothing.  
**Exception path**: If the user accidentally points at a directory that is not a spec-kitty project, the command fails with its normal "no kitty-specs found" error — not the migration message.

**Acceptance criteria**:  
- Exit code is non-zero.  
- Stderr/stdout contains the phrase "Pre-3.0 layout detected" and "spec-kitty upgrade".  
- No files under `kitty-specs/` are modified.

### Scenario B — Developer runs spec-kitty upgrade on a pre-3.0 project

**Actor**: Developer  
**Trigger**: Runs `spec-kitty upgrade` (or `spec-kitty upgrade --migration 0.9.0_frontmatter_only_lanes`) on the same pre-3.0 project.  
**Happy path**: Upgrade runs as before; WPs are moved from lane subdirectories to flat `tasks/`; post-upgrade, task commands succeed.  
**Acceptance criteria**:  
- `spec-kitty upgrade` exits 0.  
- WP files appear in flat `tasks/` after upgrade.  
- All active task commands succeed on the project after upgrade (no more hard-reject).

### Scenario C — Developer runs task command on a fully migrated post-3.0 project

**Actor**: Developer  
**Trigger**: Runs any active task/status command on a project with only flat `tasks/WP*.md` and a valid `status.events.jsonl`.  
**Happy path**: No detection overhead visible; command executes normally.  
**Acceptance criteria**:  
- No "Pre-3.0 layout detected" message appears.  
- Command exits with its normal success code.

### Scenario D — Audit/review reads a legacy mission artifact

**Actor**: Developer using dashboard or `spec-kitty agent status materialize`  
**Trigger**: Read-only audit of a legacy mission artifact.  
**Happy path**: The operation reports what it finds (or notes the shape is unmigrated) but does not mutate.  
**Acceptance criteria**:  
- No crash or silent data corruption.  
- If the dashboard scanner encounters a legacy mission, it records `is_legacy: true` as a metadata annotation without attempting to normalize it through active runtime paths.

---

## Assumptions

1. Pre-3.0 lane-directory detection is accurately described by the existing `is_legacy_format()` implementation: presence of `tasks/{planned,doing,for_review,done}/` subdirectories containing at least one `.md` file. This definition is reused for the boundary guard.
2. The `m_0_9_0_frontmatter_only_lanes` migration is the sole existing migration that handles pre-3.0 lane-directory layouts. No other migration path needs to be preserved for lane-directory detection.
3. The `tasks_support.py` module (separate from `task_utils/support.py`) re-exports `is_legacy_format` as a pass-through; this export is de-exported as part of FR-003 / FR-004 cleanup.
4. Dashboard read-only usage (`dashboard/scanner.py`, `dashboard/handlers/features.py`) may retain a thin read-only shim to detect and annotate legacy shapes without routing through the active mutation hot path, provided no mutation is triggered.
5. The `test_no_dead_symbols.py` grandfathered entry `specify_cli.scripts.tasks.task_helpers::is_legacy_format` will need updating as part of this mission's test cleanup (FR-010).

---

## Success Criteria

1. Running any active task/status mutation command against a pre-3.0 fixture project returns a non-zero exit code and includes the upgrade instruction message in ≤100 ms of startup (no mutation side effect).
2. Running `spec-kitty upgrade` against a pre-3.0 fixture project continues to succeed with 0 regressions in the upgrade test suite.
3. The module `specify_cli.legacy_detector` is no longer importable from the main active package surface; importing it from the migration namespace (`specify_cli.upgrade.legacy_detector` or equivalent) succeeds.
4. All `if use_legacy` / `if is_legacy_format()` branches are absent from the active runtime paths: `task_utils/support.py`, `tasks_cli.py`, `acceptance/__init__.py`, and the dashboard mutation paths.
5. Documentation in `docs/status-model.md` no longer presents frontmatter `lane` as a live workflow mechanism.
6. Zero new Ruff/mypy violations introduced; Sonar complexity ceiling (≤15) maintained in all touched functions.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `legacy_detector.py` | Module containing `is_legacy_format()`, `get_legacy_lane_counts()`, `LEGACY_LANE_DIRS`. Currently in active runtime; to be relocated to migration/upgrade namespace. |
| Command boundary guard | New function/module called at entry to all active task/status mutation commands; detects pre-3.0 shape and raises a structured `Pre30LayoutError` (or equivalent). |
| `m_0_9_0_frontmatter_only_lanes` | Migration that moves lane-dir WPs to flat `tasks/`. Must continue to work post-relocation. |
| `locate_work_package` | Core function in `task_utils/support.py`; contains the primary `use_legacy` branch to be removed. |
| `tasks_cli.py` | Contains two `is_legacy_format` call sites that route command logic differently for legacy vs. modern shapes. |
| `status.events.jsonl` | Canonical source of truth for WP lane state in post-3.0 projects. |

---

## Domain Language

| Canonical term | Avoid |
|---------------|-------|
| pre-3.0 layout / pre-3.0 project shape | "legacy project", "old project" (ambiguous) |
| command boundary guard | "pre-check", "validator" (vague) |
| lane-directory layout | "legacy lanes", "task subdirectory lanes" |
| migration/upgrade namespace | "legacy namespace" (confusing with the concept being retired) |
| de-export | "hide", "unexport" |
