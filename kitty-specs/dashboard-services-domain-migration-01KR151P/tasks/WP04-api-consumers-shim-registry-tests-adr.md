---
work_package_id: WP04
title: API Consumers, Shim Registry, Tests, and ADR
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-009
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- NFR-001
- NFR-002
- NFR-005
- C-002
- C-006
planning_base_branch: feature/645-api-surface-completion-mission-c
merge_target_branch: feature/645-api-surface-completion-mission-c
branch_strategy: Planning artifacts for this feature were generated on feature/645-api-surface-completion-mission-c. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/645-api-surface-completion-mission-c unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Governance and Enforcement
assignee: ''
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "3013658"
history:
- at: '2026-05-07T12:36:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: architecture/2.x/shim-registry.yaml
execution_mode: code_change
owned_files:
- src/dashboard/api/app.py
- src/dashboard/api/deps.py
- src/dashboard/api/routers/missions.py
- src/dashboard/api/routers/health.py
- src/dashboard/api/routers/sync.py
- architecture/2.x/shim-registry.yaml
- tests/architectural/test_dashboard_boundary.py
- architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md
- architecture/2.x/adr/README.md
tags: []
---

# Work Package Prompt: WP04 – API Consumers, Shim Registry, Tests, and ADR

## Branch Strategy

- **Planning/base branch at prompt creation**: `feature/645-api-surface-completion-mission-c`
- **Final merge target for completed work**: `feature/645-api-surface-completion-mission-c`
- **Implement command**: `spec-kitty implement WP04 --base WP02`
- **Depends on**: WP01 + WP02 + WP03. The boundary-test exemption removal (T019) is only
  safe after all `specify_cli/` callers have been updated.

---

## Objectives & Success Criteria

Update all `dashboard/api/` consumers to import directly from `specify_cli.missions.*`
(so shims have zero dependents at merge time). Register all four shims in
`architecture/2.x/shim-registry.yaml`. Tighten the existing C-009 architectural boundary
test by removing the CLI exemption and narrowing the `specify_cli/dashboard/` exclusion.
Write the P1 and P2 regression tests. File the Phase B ADR.

**Done when**:
- `spec-kitty doctor shim-registry` → clean, zero warnings
- `pytest tests/architectural/test_dashboard_boundary.py -v` → all pass, zero violations
- Synthetic violation test catches a planted `from dashboard.services.registry import ...` in a fixture file
- P1 and P2 regression tests pass
- OpenAPI snapshot test passes (unchanged — wire shapes not affected)
- ADR filed and cross-linked
- `grep -rn "from dashboard.services" src/dashboard/api/` → empty (all callers updated)

## Context & Constraints

**Spec**: `kitty-specs/dashboard-services-domain-migration-01KR151P/spec.md` — FR-009, FR-013, FR-014, FR-015, FR-016, FR-017
**Data model**: `kitty-specs/dashboard-services-domain-migration-01KR151P/data-model.md` — §4 (shim YAML entries), §5 (boundary test changes), §6 (regression test contracts)
**Research**: `kitty-specs/dashboard-services-domain-migration-01KR151P/research.md` — R-004 (boundary test strategy), R-005 (shim YAML schema)

**Key finding from R-004**: `test_no_upstream_dashboard_imports` already exists in
`tests/architectural/test_dashboard_boundary.py` and enforces the C-009 rule. It has two
exemptions:
1. `_ALLOWED_BOUNDARY_FILES` contains `specify_cli/cli/commands/dashboard.py` — REMOVE after WP01
2. Entire `specify_cli/dashboard/` subtree is skipped — NARROW after WP02+WP03

WP04 does NOT add a new assertion; it removes the exemptions that were the only reason
the test didn't already fail.

---

## Subtasks & Detailed Guidance

### Subtask T016 – Update `dashboard/api/app.py` and `deps.py`

**Purpose**: Ensure the two FastAPI app-level files that import `MissionRegistry` use the
canonical path. After this, they no longer depend on the shim.

**Steps**:

1. `src/dashboard/api/app.py` — find the `MissionRegistry` import:
```python
# OLD (may be deferred inside `create_app` or `lifespan`):
from dashboard.services.registry import MissionRegistry
# NEW:
from specify_cli.missions.registry import MissionRegistry
```

2. `src/dashboard/api/deps.py` — same pattern:
```python
# OLD:
from dashboard.services.registry import MissionRegistry
# NEW:
from specify_cli.missions.registry import MissionRegistry
```

3. Verify: `grep -n "from dashboard.services" src/dashboard/api/app.py src/dashboard/api/deps.py` → empty.

**Files**:
- `src/dashboard/api/app.py`
- `src/dashboard/api/deps.py`

**Parallel?**: Yes — T016 and T017 are independent file sets.

---

### Subtask T017 – Update `dashboard/api/routers/missions.py`, `health.py`, `sync.py`

**Purpose**: Three router files import service symbols from `dashboard.services.*`.
After this update they import directly from `specify_cli.missions.*`, and the shims
have zero dependents in `dashboard/api/`.

**Steps**:

1. `src/dashboard/api/routers/missions.py`:
```python
# OLD:
from dashboard.services.registry import MissionRecord, MissionRegistry, WorkPackageRecord
# NEW:
from specify_cli.missions.registry import MissionRecord, MissionRegistry, WorkPackageRecord
```

2. `src/dashboard/api/routers/health.py`:
```python
# OLD:
from dashboard.services.project_state import ProjectStateService
# NEW:
from specify_cli.missions.project_state import ProjectStateService
```

3. `src/dashboard/api/routers/sync.py`:
```python
# OLD:
from dashboard.services.sync import SyncService
# NEW:
from specify_cli.missions.sync_service import SyncService
```

4. Verify: `grep -rn "from dashboard.services" src/dashboard/api/routers/` → empty.

5. Run: `pytest tests/test_dashboard/test_api_contract.py tests/test_dashboard/test_api_handler.py -q` → all pass.

**Files**:
- `src/dashboard/api/routers/missions.py`
- `src/dashboard/api/routers/health.py`
- `src/dashboard/api/routers/sync.py`

**Parallel?**: Yes — all three are independent.

---

### Subtask T018 – Register shims in `architecture/2.x/shim-registry.yaml`

**Purpose**: Record all four shims under governance so `spec-kitty doctor shim-registry`
can verify them. This activates CI enforcement.

**Steps**:

1. Open `architecture/2.x/shim-registry.yaml`. It currently reads `shims: []`.

2. Replace with (use exact YAML from `data-model.md § 4`):

```yaml
# Compatibility Shim Registry
# Mission: migration-shim-ownership-rules-01KPDYDW (#615)
#
# Schema: kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml
# Rulebook: architecture/2.x/06_migration_and_shim_rules.md
#
# CI enforcement: spec-kitty doctor shim-registry
# Scanner test: tests/architectural/test_unregistered_shim_scanner.py
#
# Baseline (2026-04-19): zero shims present at mission-615 start.
# Every future entry must set grandfathered: false.

shims:
  - path: src/dashboard/services/registry.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/registry.py
    reason: "Phase B service placement remediation — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/mission_scan.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/scan_service.py
    reason: "Phase B service placement remediation — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/project_state.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/project_state.py
    reason: "Phase B service placement remediation — inverted dependency repair (epic #645)"

  - path: src/dashboard/services/sync.py
    grandfathered: false
    owner_mission: dashboard-services-domain-migration-01KR151P
    removal_release: "3.2.0"
    canonical_path: src/specify_cli/missions/sync_service.py
    reason: "Phase B service placement remediation — inverted dependency repair (epic #645)"
```

3. Verify: `spec-kitty doctor shim-registry` → clean output, zero warnings.

**Files**:
- `architecture/2.x/shim-registry.yaml`

**Notes**: If `spec-kitty doctor shim-registry` reports a schema error, check the schema
file at `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml`
for the exact field names required.

---

### Subtask T019 – Tighten `test_no_upstream_dashboard_imports` exemptions

**Purpose**: Now that all violations are fixed, remove the exemptions that were papering
over them. The test becomes a full enforcement net with no holes.

**Steps**:

1. Open `tests/architectural/test_dashboard_boundary.py`. Locate `test_no_upstream_dashboard_imports`.

2. **Remove `dashboard.py` from `_ALLOWED_BOUNDARY_FILES`**. After WP01, `specify_cli/cli/commands/dashboard.py` no longer imports from `dashboard.*`, so the exemption is no longer needed:
```python
# OLD:
_ALLOWED_BOUNDARY_FILES = frozenset({
    src_root / "specify_cli" / "cli" / "commands" / "dashboard.py",
})
# NEW:
_ALLOWED_BOUNDARY_FILES = frozenset()
```

3. **Narrow or remove the `specify_cli/dashboard/` broad exclusion**. After WP02+WP03:
   a. Run: `grep -rn "from dashboard" src/specify_cli/dashboard/` to see what remains.
   b. If the only remaining `dashboard.*` imports in `specify_cli/dashboard/` are in
      files like `__init__.py` or `lifecycle.py` that are genuinely bridge code (e.g.,
      `from dashboard import create_app`), add those specific files to `_ALLOWED_BOUNDARY_FILES`
      and REMOVE the broad path exclusion.
   c. If `specify_cli/dashboard/handlers/*.py` has NO remaining `dashboard.*` imports,
      the broad exclusion can be removed entirely.

   Example narrowing (if `__init__.py` is the only remaining bridge):
   ```python
   _ALLOWED_BOUNDARY_FILES = frozenset({
       src_root / "specify_cli" / "dashboard" / "__init__.py",  # bridges lifecycle
   })
   # Remove the broad specify_cli/dashboard/ path skip from the loop body
   ```

4. **Add a synthetic violation fixture test** to verify the check catches violations:
```python
def test_boundary_check_catches_dashboard_import(tmp_path):
    """The boundary checker must detect a planted dashboard.* import."""
    import ast, textwrap
    src_root = Path(__file__).resolve().parents[2] / "src"

    # Synthetic violation: a file that imports from dashboard.services
    fake_file = tmp_path / "fake_domain_module.py"
    fake_file.write_text("from dashboard.services.registry import MissionRegistry\n")

    violations = []
    tree = ast.parse(fake_file.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "dashboard" or node.module.startswith("dashboard."):
                violations.append(f"{fake_file}:{node.lineno}: {node.module}")

    assert violations, "Boundary checker failed to detect the synthetic violation"
```

5. Run the full boundary test: `pytest tests/architectural/test_dashboard_boundary.py -v` → all pass.

**Files**:
- `tests/architectural/test_dashboard_boundary.py`

**Notes**: If after narrowing, the test reports new violations in `specify_cli/dashboard/`
(files you didn't expect), investigate before adding to the allowlist. The goal is a
clean tree, not a longer allowlist.

---

### Subtask T020 – Write P1 regression test

**Purpose**: Prevent cache staleness from regressing. `list_missions()` must return fresh
lane counts after a `status.events.jsonl` append on a warm cache.

**Steps**:

Create `tests/specify_cli/missions/test_registry_cache.py` (or add to it if it exists
from WP01).

Implement `test_list_missions_reflects_appended_event` per the contract in
`data-model.md § 6`:

Key points:
- Bootstrap a minimal `kitty-specs/<mission>/` with `meta.json`, `status.events.jsonl`
  (one `claimed` event), and `tasks/WP01.md`
- Create `MissionRegistry(tmp_path)` and call `list_missions()` → verify `claimed == 1`
- Force a mtime change on `status.events.jsonl` using `os.utime(events_file, ns=(atime_ns, mtime_ns + 1))`
- Write a second event (`to_lane: "done"`) to the file
- Call `list_missions()` again on the **same registry instance**
- Assert `done == 1`, `claimed == 0`

The `os.utime` trick is necessary because some filesystems have 1-second mtime granularity;
bumping `mtime_ns + 1` guarantees the cache key changes regardless of filesystem precision.

**Files**:
- `tests/specify_cli/missions/test_registry_cache.py` (new or extend)

---

### Subtask T021 – Write P2 regression test

**Purpose**: Prevent the `WeakValueDictionary` regression from returning. Same-instance
guarantee for `workpackages_for()`.

**Steps**:

In the same `test_registry_cache.py` file, implement `test_workpackages_for_returns_same_instance`:

```python
def test_workpackages_for_returns_same_instance(tmp_path):
    # ... minimal mission setup (reuse helper from T020) ...
    registry = MissionRegistry(tmp_path)
    registry.list_missions()  # warm the list cache

    mission_id = "<the mission_id from meta.json>"
    wp_reg1 = registry.workpackages_for(mission_id)
    # Do NOT hold any other reference between calls
    wp_reg2 = registry.workpackages_for(mission_id)

    assert wp_reg1 is not None
    assert wp_reg2 is not None
    assert wp_reg1 is wp_reg2, (
        "P2 regression: workpackages_for() returned a different WorkPackageRegistry "
        "instance on the second call. Check that _wp_registries uses a strong dict, "
        "not WeakValueDictionary."
    )
```

**Files**:
- `tests/specify_cli/missions/test_registry_cache.py`

---

### Subtask T022 – File Phase B ADR

**Purpose**: Record the architectural decision for Phase B so future contributors
understand why `dashboard/services/` is a shim tree and when it will be retired.

**Steps**:

1. Create `architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md`.

2. Required sections and content:

```markdown
# ADR 2026-05-07-1: Dashboard Services Move to specify_cli/missions/ (Phase B)

**Status**: Accepted
**Date**: 2026-05-07
**Epic**: #645, #992
**Mission**: dashboard-services-domain-migration-01KR151P

## Context

[Summarize: `specify_cli` was importing from `dashboard.services.*`, inverting the
intended dependency direction. Phase A (Mission C) proved the pattern with new services.
Phase B completes the repair for the four existing services.]

## Decision

Move `MissionRegistry`, `WorkPackageRegistry`, `MissionScanService`,
`ProjectStateService`, `SyncService` from `dashboard/services/` to
`specify_cli/missions/`. Leave compatibility shims for one release cycle.
Fix the list_missions() cache staleness bug (P1) and the WeakValueDictionary
GC bug (P2) as part of the move.

## Rationale

[Reference the placement assessment and the two-reader problem from #992 overview.]

## Consequences

- Positive: `specify_cli` no longer imports from `dashboard.*`; C-009 fully enforced
- Positive: P1 and P2 bugs fixed at the canonical location
- Positive: Single canonical reader for mission/WP state (prerequisite for #992)
- Negative: Phase C (shim retirement) required after `3.2.0` ships
- Neutral: All callers updated in this mission; shims have zero dependents at merge time

## Phase C Plan

After the `3.2.0` tag is published, file a housekeeping mission to:
- Delete the four shims in `dashboard/services/`
- Remove their `shim-registry.yaml` entries
- Delete `dashboard/services/__init__.py` (now empty)
- Delete `dashboard/services/` directory

## Relationship to #992 (Queue Drain Epic)

This mission resolves the multi-reader problem on the read surface (Workstream 1
read side). Write-path authority (Workstreams 2–6) is out of scope and follows
in subsequent missions.
```

3. Add a cross-link entry in `architecture/2.x/adr/README.md`:
```markdown
| 2026-05-07-1 | Dashboard Services Move to specify_cli/missions/ (Phase B) | Accepted |
```

**Files**:
- `architecture/2.x/adr/2026-05-07-1-dashboard-services-phase-b.md` (new)
- `architecture/2.x/adr/README.md` (add row)

---

## Definition of Done

- [ ] `grep -rn "from dashboard.services" src/dashboard/api/` → empty
- [ ] `spec-kitty doctor shim-registry` → clean, 4 shims registered
- [ ] `pytest tests/architectural/test_dashboard_boundary.py -v` → all pass, zero violations
- [ ] Synthetic violation test (`test_boundary_check_catches_dashboard_import`) passes
- [ ] `pytest tests/specify_cli/missions/test_registry_cache.py -v` → P1 and P2 tests pass
- [ ] `pytest tests/test_dashboard/ tests/architectural/ -x -q` → all pass
- [ ] ADR file exists and is cross-linked from `architecture/2.x/adr/README.md`
- [ ] `mypy src/ --strict` → zero new errors introduced by this WP

## Reviewer Guidance

1. Run `grep -rn "from dashboard" src/specify_cli/ src/kernel/` — the only hits should be files explicitly listed in `_ALLOWED_BOUNDARY_FILES` (if any remain). No unregistered violations.
2. Verify the synthetic violation test actually calls the boundary-scanning logic, not just creates a file.
3. Check the P1 regression uses `os.utime(..., ns=(..., mtime_ns + 1))` to guarantee a different cache key, not just `time.sleep(1)`.
4. Check shim YAML entries have `removal_release: "3.2.0"` (string, not int) and `grandfathered: false`.
5. Confirm the OpenAPI snapshot test passes — wire shapes must be byte-identical after the import path changes.

## Activity Log

- 2026-05-07T15:22:05Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2998041 – Started implementation via action command
- 2026-05-07T15:32:15Z – claude:sonnet-4-6:implementer:implementer – shell_pid=2998041 – API consumers updated; 4 shims registered; boundary test exemptions removed; synthetic violation test added; P1/P2 regression tests verified; ADR filed
- 2026-05-07T15:32:55Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=3013658 – Started review via action command
- 2026-05-07T15:36:36Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=3013658 – WP04 approved: T016/T017 dashboard/api callers verified to import from specify_cli.missions.* (zero shim dependents). T018 4 shims registered (all PENDING, all shim files present, programmatic doctor check clean — interactive 'spec-kitty doctor shim-registry' showed empty due to PATH-installed CLI resolving to main repo, not a worktree defect). T019 boundary test tightened: zero unjustified exemptions, 3-file allow-list (server.py FastAPI bootstrap, api_types.py legacy type re-export shim, handlers/features.py lazy DashboardFileReader — all genuine bridges out of WP04 scope), synthetic-violation fixture passes. T020/T021 P1+P2 regression tests pass at canonical home. T022 ADR 2026-05-07-1 filed and cross-linked. Scope additions APPROVED: (1) test_shim_registry_schema replacement is faithful — 'no grandfathered=True' is the durable FR-008 invariant, the prior 'empty-baseline' assertion was structurally impossible after T018; (2) 3-file allow-list contents verified bridge-legitimate. 46/46 architectural+regression tests pass; 453/454 in test_dashboard+architectural pass (sole failure is pre-existing uv.lock drift untouched by this WP). mypy on WP04-edited files identical to main (zero new errors).
