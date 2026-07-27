---
description: "Work package task list for SPEC_KITTY_HOME State Isolation"
---

# Work Packages: SPEC_KITTY_HOME State Isolation

**Inputs**: Design documents from `kitty-specs/spec-kitty-home-isolation-01KW1JXX/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Source**: [GitHub issue #2171](https://github.com/Priivacy-ai/spec-kitty/issues/2171)

**Tests**: Required — this is a correctness/isolation bug fix; every WP carries focused regression tests (spec NFR-004, SC-001..SC-004).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). The keystone WP01 unblocks WP02–WP05 (parallel by subsystem); WP06 closes out with the architectural guard, CLI integration test, and docs.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel (different files/components).

## Path Conventions

- Single project: `src/specify_cli/`, `tests/`.

---

## Work Package WP01: Keystone — get_runtime_root honors SPEC_KITTY_HOME (Priority: P0) 🎯 MVP

**Goal**: Make `specify_cli.paths.get_runtime_root()` read `SPEC_KITTY_HOME` (non-empty) as `base` on all platforms, preserving current defaults when unset. Foundation for every other WP.
**Independent Test**: `get_runtime_root().base == Path($SPEC_KITTY_HOME)` when set (linux/darwin/win32); unset → POSIX `~/.spec-kitty`, Windows platformdirs; empty string falls through; no directories created.
**Prompt**: `/tasks/WP01-keystone-runtime-root-env.md`
**Requirement Refs**: FR-011, FR-012

### Included Subtasks

- [ ] T001 Add `SPEC_KITTY_HOME` env read to `get_runtime_root()` (all platforms, empty = unset, before platform branches) in `src/specify_cli/paths/windows_paths.py`
- [ ] T002 Preserve `RuntimeRoot` purity (frozen, no directory creation) and confirm derived properties unaffected
- [ ] T003 [P] Add env-precedence unit tests (set/empty/unset × linux/darwin/win32) in `tests/paths/test_runtime_root_spec_kitty_home.py`
- [ ] T004 [P] Extend kernel path tests (`tests/kernel/test_paths.py`, `tests/kernel/test_paths_unified_windows_root.py`) for the new base behavior
- [ ] T005 Add a no-directory-creation assertion (resolution is pure)

### Implementation Notes

- Mirror the `get_kittify_home()` walrus-falsy idiom exactly: `if env_home := os.environ.get("SPEC_KITTY_HOME"): base = Path(env_home)`.
- Insert the env check before the existing `win32`/POSIX branches in `get_runtime_root()` (`windows_paths.py:58`).

### Dependencies

- None (foundation).

### Risks & Mitigations

- Empty-string handling must match asset-home behavior → covered by T003.
- Must not create directories → T005.

---

## Work Package WP02: Sync state rerouting (Priority: P0)

**Goal**: Route sync config, event queues + active scope, daemon state, and the Lamport clock through `get_runtime_root().base`, preserving each POSIX suffix; convert the import-time `SPEC_KITTY_DIR` constant to lazy resolution.
**Independent Test**: With `SPEC_KITTY_HOME` set, sync config/queue/active-scope/daemon/clock paths resolve under it; unset POSIX paths byte-identical to today.
**Prompt**: `/tasks/WP02-sync-state-rerouting.md`
**Requirement Refs**: FR-001, FR-004, FR-005, FR-006, FR-007

### Included Subtasks

- [ ] T006 Reroute `SyncConfig` (`sync/config.py:31`) `config_dir`/`config_file` to `get_runtime_root().base`
- [ ] T007 Reroute `sync/queue.py` `_spec_kitty_dir()` (`:362`) → base (feeds credentials, auth dir, legacy + scoped queue, active scope, max-queue-size)
- [ ] T008 Reroute `sync/daemon.py` `_sync_root`/`_daemon_root` and convert module constant `SPEC_KITTY_DIR` (`:94`) to a lazy function, preserving POSIX flat layout
- [ ] T009 Reroute `sync/clock.py` `LamportClock` default_factory (`:37`) + `load()` (`:80`)
- [ ] T010 [P] Add/adjust sync tests (config_file, queue auth+unauth, daemon, clock) under env set/unset

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- POSIX flat layout must be preserved: daemon root = `base` (NOT `base/daemon`); `_sync_root` POSIX = `base/sync`. See research.md D3.
- Module-level constant evaluated at import → make lazy (research.md D5).

---

## Work Package WP03: Auth state rerouting (Priority: P0)

**Goal**: Route the encrypted auth session store (POSIX + Windows) and the token refresh lock through `get_runtime_root()`.
**Independent Test**: With `SPEC_KITTY_HOME` set, auth store and refresh lock resolve under it on POSIX and Windows; unset preserves POSIX layout.
**Prompt**: `/tasks/WP03-auth-state-rerouting.md`
**Requirement Refs**: FR-002, FR-003

### Included Subtasks

- [ ] T011 Reroute `auth/secure_storage/file_fallback.py` `default_store_dir()` (`:36`) → `get_runtime_root().base / "auth"`
- [ ] T012 Normalize `auth/secure_storage/windows_storage.py` default (`:15`) → `get_runtime_root().auth_dir` (Windows normalization, decision DM-01KW1KDHVGWZ0QERDMV1CRJ15S)
- [ ] T013 Reroute `auth/token_manager.py` `_refresh_lock_path()` POSIX branch (`:85`) → `base / "auth" / "refresh.lock"`
- [ ] T014 [P] Add/adjust auth tests (store dir, refresh lock) under env set/unset; fix any test pinning the old Windows path

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- `windows_storage.py` currently hardcodes `Path.home()/.spec-kitty/auth`; normalization changes unset-Windows path — verify `tests/auth/test_secure_storage_file.py` (research.md D4).

---

## Work Package WP04: Tracker state rerouting (Priority: P0)

**Goal**: Route tracker credentials and tracker DB through `get_runtime_root().base` (single-root decision C-003), preserving POSIX flat suffixes.
**Independent Test**: With `SPEC_KITTY_HOME` set, tracker credentials + DB resolve under it; unset POSIX paths unchanged.
**Prompt**: `/tasks/WP04-tracker-state-rerouting.md`
**Requirement Refs**: FR-008

### Included Subtasks

- [ ] T015 Reroute `tracker/credentials.py` `_tracker_root()` POSIX (`:39`) → `get_runtime_root().base` (flat; keep `credentials` suffix)
- [ ] T016 Reroute `tracker/store.py` `_spec_kitty_dir()` (`:14`)/`_trackers_dir()` (`:18`) → `base / "trackers"`
- [ ] T017 [P] Add/adjust tracker tests (credentials, DB path) under env set/unset

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- POSIX tracker creds root = `base` (flat) ≠ `RuntimeRoot.tracker_dir`; keep flat suffix for NFR-001 (research.md D3).

---

## Work Package WP05: State reporting consistency (Priority: P1)

**Goal**: Make `state doctor` resolve/report the same root the runtime uses, and ensure `StateRoot.GLOBAL_SYNC` resolution reflects the authoritative base.
**Independent Test**: `state doctor` reported global-sync root == `get_runtime_root().base` under env set/unset.
**Prompt**: `/tasks/WP05-state-reporting-consistency.md`
**Requirement Refs**: FR-009, FR-010

### Included Subtasks

- [ ] T018 Reroute `state/doctor.py` global-sync resolution (`:141`, `:253`) → `get_runtime_root().base`
- [ ] T019 Ensure `state/contract.py` GLOBAL_SYNC resolution honors the authoritative base (keep declarative surface patterns)
- [ ] T020 [P] Add/adjust state-doctor tests asserting reported root == `get_runtime_root().base` under env set/unset

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- `contract.py` STATE_SURFACES are declarative patterns; the actual resolution lives in `doctor.py` — change resolution, keep the registry as single source of relative patterns.

---

## Work Package WP06: Regression guard, CLI integration, docs (Priority: P1)

**Goal**: Prevent recurrence and document true behavior — architectural guard, end-to-end CLI isolation test, in-repo skill doc update, CHANGELOG.
**Independent Test**: Guard fails if any global-state module hand-rolls `Path.home() / ".spec-kitty"`; CLI test proves all state lands under `SPEC_KITTY_HOME`; full suite + ruff + mypy green.
**Prompt**: `/tasks/WP06-regression-guard-cli-docs.md`
**Requirement Refs**: FR-010, FR-013

### Included Subtasks

- [x] T021 Extend `tests/audit/test_no_legacy_path_literals.py` — no hand-rolled `Path.home() / ".spec-kitty"` in `sync/auth/tracker/state` (allowlist keystone + asset-home + migration/fallback)
- [x] T022 Add CLI integration test (distinct HOME + SPEC_KITTY_HOME → all state under SPEC_KITTY_HOME; default home clean) in `tests/integration/test_spec_kitty_home_cli.py`
- [x] T023 Update `src/doctrine/skills/spk-team-upsun-cli-sync/SKILL.md` (true isolation + verification command)
- [x] T024 Add `CHANGELOG.md` entry (isolation fix + Windows path normalization)
- [x] T025 Run full suite + `ruff` + `mypy --strict` + terminology guard; confirm green

### Dependencies

- Depends on WP01, WP02, WP03, WP04, WP05.

### Risks & Mitigations

- Guard allowlist must be precise (keystone, asset-home `.kittify`, migration/fallback) to avoid false positives.
- Terminology canon for SKILL.md prose → run `tests/architectural/test_no_legacy_terminology.py`.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → {WP02, WP03, WP04, WP05 in parallel} → WP06.
- **Parallelization**: WP02–WP05 are subsystem-isolated (no file overlap) and run concurrently once WP01 lands.
- **MVP Scope**: WP01 (the keystone) is the minimal fix that makes the env var win at the root; WP02–WP05 complete the per-surface contract; WP06 hardens + documents.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP03 |
| FR-003 | WP03 |
| FR-004 | WP02 |
| FR-005 | WP02 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP04 |
| FR-009 | WP05 |
| FR-010 | WP05, WP06 |
| FR-011 | WP01 |
| FR-012 | WP01 |
| FR-013 | WP06 |

### Non-Functional & Constraint Coverage

`map-requirements` validates functional requirements only; NFR/Constraint coverage is tracked here for traceability.

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| NFR-001 (POSIX byte-identical when unset) | WP01, WP02, WP03, WP04, WP05, WP06 |
| NFR-002 (pure resolution, no dir creation) | WP01 |
| NFR-003 (Windows precedence + normalization) | WP01, WP03 |
| NFR-004 (ruff/mypy/≥90% coverage) | WP06 (+ per-WP lint/type runs) |
| NFR-005 (no secrets outside resolved root) | WP03 |
| C-001 (no auto-migration) | WP06 |
| C-002 (in-repo scope only) | WP06 |
| C-003 (single state-root selector) | WP01, WP03, WP04 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Env read in get_runtime_root | WP01 | P0 | No |
| T002 | RuntimeRoot purity | WP01 | P0 | No |
| T003 | Env-precedence tests | WP01 | P0 | Yes |
| T004 | Kernel path tests | WP01 | P0 | Yes |
| T005 | No-dir-creation assertion | WP01 | P0 | No |
| T006 | SyncConfig reroute | WP02 | P0 | No |
| T007 | queue _spec_kitty_dir reroute | WP02 | P0 | No |
| T008 | daemon reroute + lazy constant | WP02 | P0 | No |
| T009 | clock reroute | WP02 | P0 | No |
| T010 | sync tests | WP02 | P0 | Yes |
| T011 | file_fallback reroute | WP03 | P0 | No |
| T012 | windows_storage normalize | WP03 | P0 | No |
| T013 | refresh lock reroute | WP03 | P0 | No |
| T014 | auth tests | WP03 | P0 | Yes |
| T015 | tracker credentials reroute | WP04 | P0 | No |
| T016 | tracker store reroute | WP04 | P0 | No |
| T017 | tracker tests | WP04 | P0 | Yes |
| T018 | doctor reroute | WP05 | P1 | No |
| T019 | contract resolution consistency | WP05 | P1 | No |
| T020 | doctor tests | WP05 | P1 | Yes |
| T021 | architectural guard | WP06 | P1 | No |
| T022 | CLI integration test | WP06 | P1 | No |
| T023 | SKILL.md update | WP06 | P1 | Yes |
| T024 | CHANGELOG entry | WP06 | P1 | Yes |
| T025 | full suite + lint + types | WP06 | P1 | No |
