# Tasks: P1 Dependency Cycle Cleanup

**Mission**: `p1-dependency-cycle-cleanup-01KQFXVC`
**Branch**: `main` → merges to `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Create `src/specify_cli/identity/project.py` (move all content from `sync/project_identity.py`, inline `generate_node_id`) | WP01 | [P] |
| T002 | Replace `src/specify_cli/sync/project_identity.py` with backward-compat shim re-exporting from `identity.project` | WP01 | [P] |
| T003 | Update `src/specify_cli/dossier/drift_detector.py`: change 1 runtime import line to use `identity.project` | WP01 | [P] |
| T004 | Create `tests/architectural/test_dossier_sync_boundary.py`: AST-based guard asserting no `dossier → sync` imports | WP01 | [P] |
| T005 | Verify WP01: ruff clean + dossier/sync/architectural tests pass; zero `dossier → sync` grep | WP01 | |
| T006 | Create `src/specify_cli/status/adapters.py`: callback registry with `DossierSyncHandler`, `SaasFanOutHandler`, `register_*`, `fire_*` | WP02 | [P] |
| T007 | Update `src/specify_cli/status/emit.py`: remove lazy `from specify_cli.sync.*` imports; call `fire_dossier_sync` / `fire_saas_fanout` | WP02 | [P] |
| T008 | Register sync handlers at startup in `src/specify_cli/sync/__init__.py` (or daemon entry) | WP02 | [P] |
| T009 | Create `tests/architectural/test_status_sync_boundary.py`: AST-based guard asserting no `status → sync` imports | WP02 | [P] |
| T010 | Verify WP02: ruff clean + status/sync/contract/architectural tests pass; zero `status → sync` grep | WP02 | |

## Work Packages

---

### WP01 — P1.2: Relocate ProjectIdentity

**Priority**: High
**Estimated prompt size**: ~380 lines
**Parallelizable with**: WP02 (no shared files)
**Dependencies**: none

**Goal**: Move the `ProjectIdentity` dataclass and all its helpers from `sync/project_identity.py` to `specify_cli/identity/project.py`, replace the original with a backward-compat shim, update the single dossier caller, and add an architectural guard test.

**Success criteria**:
- `grep -r "from specify_cli.sync" src/specify_cli/dossier/ --include="*.py"` returns empty
- `uv run pytest tests/dossier tests/sync tests/architectural/test_dossier_sync_boundary.py -q` all pass
- `uv run ruff check src/specify_cli/identity/ src/specify_cli/sync/project_identity.py src/specify_cli/dossier/drift_detector.py` exits 0

**Included subtasks**:
- [ ] T001 Create `src/specify_cli/identity/project.py` with inlined `generate_node_id` (WP01)
- [ ] T002 Replace `src/specify_cli/sync/project_identity.py` with shim (WP01)
- [ ] T003 Update 1 import in `src/specify_cli/dossier/drift_detector.py` (WP01)
- [ ] T004 Create `tests/architectural/test_dossier_sync_boundary.py` (WP01)
- [ ] T005 Full verification run (WP01)

**Implementation sketch**:
1. Create `identity/project.py` by copying `sync/project_identity.py` verbatim, then replace the `from specify_cli.sync.clock import generate_node_id as generate_machine_node_id` line with an inline 3-line stdlib implementation.
2. Replace `sync/project_identity.py` body with `from specify_cli.identity.project import *`-style re-exports for every public name.
3. Patch line 30 of `dossier/drift_detector.py` from `sync.project_identity` → `identity.project`.
4. Write the AST-based boundary test.
5. Run verification.

**Risks**: The inlined `generate_node_id` must match the behavior of `sync.clock.generate_node_id` exactly (same hash algorithm, same output length).

---

### WP02 — P1.3: Status Fan-out Adapter

**Priority**: High
**Estimated prompt size**: ~400 lines
**Parallelizable with**: WP01 (no shared files)
**Dependencies**: none

**Goal**: Decouple `status/emit.py` from `specify_cli.sync` by introducing a callback-registry adapter in `status/adapters.py`, updating `emit.py` to call the adapters, and registering the sync handlers at startup.

**Success criteria**:
- `grep -r "from specify_cli.sync" src/specify_cli/status/ --include="*.py"` returns empty
- `SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/status tests/sync tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py tests/architectural/test_status_sync_boundary.py -q` all pass
- `uv run ruff check src/specify_cli/status/adapters.py src/specify_cli/status/emit.py src/specify_cli/sync/__init__.py` exits 0

**Included subtasks**:
- [ ] T006 Create `src/specify_cli/status/adapters.py` (WP02)
- [ ] T007 Update `src/specify_cli/status/emit.py` (WP02)
- [ ] T008 Register handlers at sync startup (WP02)
- [ ] T009 Create `tests/architectural/test_status_sync_boundary.py` (WP02)
- [ ] T010 Full verification run (WP02)

**Implementation sketch**:
1. Create `status/adapters.py` with two typed callback lists and `register_*` / `fire_*` API.
2. In `status/emit.py`, import `fire_dossier_sync` and `fire_saas_fanout`; remove the two lazy sync imports in the function body; update `_saas_fan_out` to call `fire_saas_fanout(**kwargs)`.
3. In `sync/__init__.py` (or daemon startup), register handlers by calling `register_dossier_sync_handler` and `register_saas_fanout_handler`.
4. Write the AST-based boundary test.
5. Run verification with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

**Risks**: Handler registration must happen before the first `emit_status_transition()` call. If sync is not imported at all (e.g., tests that mock sync), no handlers will be registered, which is correct behavior (fire_* is a no-op).

---

## Parallelization Notes

WP01 and WP02 have zero file overlap and can be implemented concurrently on separate lanes.

WP03 does not exist — each WP owns its own independent architectural test file.

## Final Verification (after both WPs merge)

```bash
uv run ruff check src/specify_cli/dossier src/specify_cli/sync src/specify_cli/status tests

SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest \
  tests/dossier tests/sync tests/status \
  tests/contract/test_body_sync.py tests/contract/test_tracker_bind.py \
  tests/architectural/ \
  -q
```
