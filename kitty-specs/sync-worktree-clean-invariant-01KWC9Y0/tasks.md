# Tasks: Worktree-Clean Sync Invariant

**Mission**: `sync-worktree-clean-invariant-01KWC9Y0` · **Issue**: [#2263](https://github.com/Priivacy-ai/spec-kitty/issues/2263)
**Planning base / merge target**: `fix/sync-worktree-clean-invariant`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

4 work packages, 19 subtasks. Decision C (deterministic `build_id`) is the foundation; everything else swaps call sites, makes tracker reads report-only, and enforces the invariant with a parametrized test.

## Subtask Index

| ID | Description | WP | Parallel |
|------|-------------|----|----------|
| T001 | Add deterministic `derive_build_id(project_uuid, node_id)` helper + NAMESPACE constant | WP01 | |
| T002 | Wire deterministic `build_id` into `with_defaults` (only when missing) | WP01 | |
| T003 | Honor uninitialized-checkout edge (C-IR-4): never persist on read paths | WP01 | |
| T004 | Unit tests: determinism, legacy stability, complete-identity unchanged, no-write | WP01 | |
| T005 | Module constants + `mypy --strict` / `ruff` clean | WP01 | |
| T006 | Swap `emitter.py:100,115` `ensure_identity` → `resolve_identity` | WP02 | |
| T007 | Swap `sync/routing.py:47`, `sync/events.py:180`, `sync/__init__.py:253`, `sync/dossier_pipeline.py:233` | WP02 | |
| T008 | Swap `tracker/origin.py:452`, `cli/commands/tracker.py:680` (read-context only) | WP02 | |
| T009 | Confirm `init.py:99,863` stay on `ensure_identity` (write boundary) | WP02 | |
| T010 | Integration test: emit on incomplete-identity checkout — no write + stable identity | WP02 | |
| T011 | `_maybe_upgrade_binding_ref` report-only (no `save_tracker_config` on reads) | WP03 | [P] |
| T012 | Read callers surface `pending_binding_upgrade` (+ optional notice) | WP03 | [P] |
| T013 | Explicit `tracker bind`/apply still persists `binding_ref` | WP03 | [P] |
| T014 | Tracker tests: read = no write + reports; explicit bind = persists | WP03 | [P] |
| T015 | Invariant test harness: SaaS-enabled fixture + porcelain/config snapshot | WP04 | |
| T016 | Parametrized no-dirty-tree assertion over the full command surface | WP04 | |
| T017 | Disabled/unauth variant — commands side-effect-free | WP04 | |
| T018 | `record-analysis` guard regression: real dirt caught; allowlist not grown | WP04 | |
| T019 | Extensibility guard + serial daemon/real-port handling + flake check | WP04 | |

---

## WP01 — Deterministic identity completion (foundation)

- **Goal**: Make a minted `build_id` deterministic from `(project_uuid, node_id)` so `resolve_identity` returns a stable identity with no write (Decision C). Foundation for the call-site migration.
- **Priority**: P1 (keystone — WP02 depends on it).
- **Independent test**: `resolve_identity` called twice on a legacy checkout missing `build_id` returns identical `(project_uuid, build_id)`; complete identities are returned unchanged; no `config.yaml` write occurs.
- **Dependencies**: none.
- **Requirements**: FR-002, NFR-001.
- **Estimated prompt size**: ~330 lines.

### Included subtasks
- [x] T001 Add deterministic `derive_build_id(project_uuid, node_id)` helper + NAMESPACE constant (WP01)
- [x] T002 Wire deterministic `build_id` into `with_defaults` only when missing (WP01)
- [x] T003 Honor uninitialized-checkout edge (C-IR-4): never persist on read paths (WP01)
- [x] T004 Unit tests: determinism, legacy stability, complete-identity unchanged, no-write (WP01)
- [x] T005 Module constants + mypy/ruff clean (WP01)

### Implementation sketch
Add a pure helper deriving `build_id = uuid5(NAMESPACE, f"{project_uuid}:{node_id}")`; call it from `with_defaults` in place of `generate_build_id()` **only when `build_id` is None**; leave write-authorized `project_uuid` minting unchanged; ensure `resolve_identity` never writes or mints `project_uuid` when it is absent; cover with focused unit tests.

---

## WP02 — Migrate read-path identity call sites

- **Goal**: Route every read/emit/background `ensure_identity` call site to the side-effect-free `resolve_identity`, keeping `ensure_identity` only at write-authorized boundaries.
- **Priority**: P1.
- **Independent test**: emitting a status event on an incomplete-identity checkout leaves `git status --porcelain` and `config.yaml` byte-identical, and identity is stable across two emits.
- **Dependencies**: WP01 (deterministic `build_id` must exist first, or the swaps introduce drift).
- **Requirements**: FR-001, FR-002, FR-003, FR-008.
- **Estimated prompt size**: ~360 lines.

### Included subtasks
- [x] T006 Swap emitter.py:100,115 ensure_identity → resolve_identity (WP02)
- [x] T007 Swap sync routing/events/__init__/dossier_pipeline call sites (WP02)
- [x] T008 Swap tracker/origin.py:452, cli/commands/tracker.py:680 (read-context only) (WP02)
- [x] T009 Confirm init.py:99,863 stay on ensure_identity (write boundary) (WP02)
- [x] T010 Integration test: emit on incomplete-identity checkout — no write + stable identity (WP02)

### Implementation sketch
Mechanical swaps with per-site read-context verification; explicitly leave `init` untouched; one integration test proving the emit path is side-effect-free and stable.

---

## WP03 — Tracker binding_ref report-only on read paths

- **Goal**: Stop read-like tracker ops (`status`/`sync_pull`/`sync_push`/`sync_run`/`map_list`) from persisting `binding_ref` to `config.yaml`; surface available upgrades instead. Persist only on explicit bind/apply.
- **Priority**: P1.
- **Independent test**: a read op with a changed server `binding_ref` writes nothing and reports `pending_binding_upgrade`; an explicit `tracker bind` persists.
- **Dependencies**: none (parallel with WP01/WP02).
- **Requirements**: FR-001, FR-004.
- **Estimated prompt size**: ~300 lines.

### Included subtasks
- [x] T011 _maybe_upgrade_binding_ref report-only (no save_tracker_config on reads) (WP03)
- [x] T012 Read callers surface pending_binding_upgrade (+ optional notice) (WP03)
- [x] T013 Explicit tracker bind/apply still persists binding_ref (WP03)
- [x] T014 Tracker tests: read = no write + reports; explicit bind = persists (WP03)

### Implementation sketch
Change `_maybe_upgrade_binding_ref` to return the pending ref instead of persisting; thread it onto read results; ensure an explicit bind path calls `save_tracker_config`; cover both directions with tests.

---

## WP04 — Worktree-clean invariant enforcement + guard regression

- **Goal**: Encode INV-1 as a parametrized no-dirty-tree contract test across the command surface, plus a regression guard proving `record-analysis` still catches real dirt and the allowlist did not grow.
- **Priority**: P1.
- **Independent test**: the parametrized test passes for every covered command and fails if a covered command dirties the tree; `record-analysis` still refuses a real source edit.
- **Dependencies**: WP01, WP02, WP03 (it asserts the whole fix).
- **Requirements**: FR-005, FR-006, FR-007.
- **Estimated prompt size**: ~360 lines.

### Included subtasks
- [x] T015 Invariant test harness: SaaS-enabled fixture + porcelain/config snapshot (WP04)
- [x] T016 Parametrized no-dirty-tree assertion over the full command surface (WP04)
- [x] T017 Disabled/unauth variant — commands side-effect-free (WP04)
- [x] T018 record-analysis guard regression: real dirt caught; allowlist not grown (WP04)
- [x] T019 Extensibility guard + serial daemon/real-port handling + flake check (WP04)

### Implementation sketch
Build a fixture for a clean SaaS-enabled checkout; snapshot porcelain + config; parametrize over the command surface; add disabled/unauth and guard-regression cases; mark daemon/real-port variants serial.

---

## Dependencies

```
WP01 ──> WP02 ──┐
                 ├──> WP04
WP03 ───────────┘
```

- **Parallelizable now**: WP01 and WP03 (no deps).
- **After WP01**: WP02.
- **Last**: WP04 (needs WP01+WP02+WP03).

## MVP scope

WP01 + WP02 deliver the core dirty-tree fix for the identity path (the most common cause). WP03 closes the tracker dirt source. WP04 makes the whole thing regression-proof. All four are needed for full acceptance; WP01→WP02 is the smallest shippable slice.

## Requirement coverage

FR-001 → WP02, WP03 · FR-002 → WP01, WP02 · FR-003 → WP02 · FR-004 → WP03 · FR-005 → WP04 · FR-006 → WP04 · FR-007 → WP04 · FR-008 → WP02, WP04. (NFR-001 → WP01; NFR-002 verified by construction via WP04's no-write proxy; NFR-003/004 → cross-cutting.)
