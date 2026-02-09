# Work Packages: ~/.kittify Runtime Centralization

**Inputs**: Design documents from `kitty-specs/036-kittify-runtime-centralization/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Included — test fixtures F-Legacy-001..003, F-Pin-001, F-Bootstrap-001 and quality gates G2, G3, G5, G6 are acceptance requirements.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Global Runtime Home + Package Asset Discovery (Priority: P0)

**Goal**: Implement `get_kittify_home()` with cross-platform support and package asset source discovery. Create the `runtime/` subpackage skeleton.
**Independent Test**: `get_kittify_home()` returns correct paths on all platforms; package asset locations are discoverable.
**Prompt**: `tasks/WP01-global-runtime-home.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [x] T001 Create `src/specify_cli/runtime/` subpackage with `__init__.py`
- [x] T002 Implement `get_kittify_home()` in `src/specify_cli/runtime/home.py`
- [x] T003 Implement `get_package_asset_root()` in `src/specify_cli/runtime/home.py`
- [x] T004 [P] Write unit tests for cross-platform path resolution in `tests/unit/runtime/test_home.py`
- [x] T005 [P] Write unit tests for `SPEC_KITTY_HOME` env var override in `tests/unit/runtime/test_home.py`

### Implementation Notes
- `get_kittify_home()`: `SPEC_KITTY_HOME` env var > `Path.home() / ".kittify"` (Unix) > `platformdirs.user_data_dir("kittify")` (Windows)
- `get_package_asset_root()`: `importlib.resources.files("specify_cli")` > `Path(specify_cli.__file__).parent` > `SPEC_KITTY_TEMPLATE_ROOT` env var
- No fallback mechanisms — raise errors for invalid paths

### Parallel Opportunities
- T004 and T005 can run in parallel after T001-T003

### Dependencies
- None (starting package)

### Risks & Mitigations
- Windows path testing on Unix CI: mock `os.name` and `platformdirs`

---

## Work Package WP02: ensure_runtime() with File Locking (Priority: P0)

**Goal**: Implement atomic global runtime populate/update on CLI startup with file locking for concurrency safety.
**Independent Test**: `ensure_runtime()` correctly populates `~/.kittify/`, handles version matches (fast path), and serializes concurrent access.
**Prompt**: `tasks/WP02-ensure-runtime.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T006 Implement `_merge_package_assets()` in `src/specify_cli/runtime/merge.py`
- [x] T007 Implement `ensure_runtime()` with file locking in `src/specify_cli/runtime/bootstrap.py`
- [x] T008 Implement `populate_from_package()` in `src/specify_cli/runtime/bootstrap.py`
- [x] T009 Write unit tests for `_merge_package_assets()` in `tests/unit/runtime/test_merge.py`
- [x] T010 Write unit tests for `ensure_runtime()` in `tests/unit/runtime/test_bootstrap.py`
- [x] T011 Write concurrency tests (G5) in `tests/concurrency/test_ensure_runtime_concurrent.py`
- [x] T012 Write interrupted update recovery test (F-Bootstrap-001)

### Implementation Notes
- File locking: `fcntl.flock()` on Unix, `msvcrt.locking()` on Windows — platform detection at import time
- Fast path: read `version.lock`, compare, return — no lock acquired
- Slow path: acquire exclusive lock, double-check version, build temp dir, merge, write `version.lock` last
- MANAGED_DIRS: `missions/software-dev`, `missions/research`, `missions/documentation`, `missions/plan`, `missions/audit`, `missions/refactor`, `scripts/`
- MANAGED_FILES: `AGENTS.md`
- NEVER_TOUCH: `config.yaml`, `missions/custom/`, `cache/` (except `version.lock`)

### Parallel Opportunities
- T009, T010, T011 can run in parallel after T006-T008

### Dependencies
- Depends on WP01 (`get_kittify_home()`, `get_package_asset_root()`)

### Risks & Mitigations
- Concurrent corruption: file lock serializes all updates; test with multiprocessing
- Interrupted update: version.lock written last; no lock = incomplete = retry next start

---

## Work Package WP03: 4-Tier Asset Resolution (Priority: P0)

**Goal**: Implement the 4-tier resolution algorithm (override > legacy > global > package default) and integrate with existing template resolution call sites.
**Independent Test**: Resolution returns correct file from correct tier; legacy tier emits deprecation warnings; missing files raise `FileNotFoundError`.
**Prompt**: `tasks/WP03-four-tier-resolver.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [x] T013 Implement `ResolutionTier` enum and `ResolutionResult` dataclass in `src/specify_cli/runtime/resolver.py`
- [x] T014 Implement `resolve_template()`, `resolve_command()`, `resolve_mission()` in `src/specify_cli/runtime/resolver.py`
- [x] T015 Implement `_warn_legacy_asset()` deprecation warning
- [x] T016 Integrate resolver into `Mission.get_command_template()` in `src/specify_cli/mission.py`
- [x] T017 Integrate resolver into init template preparation in `src/specify_cli/cli/commands/init.py`
- [x] T018 Write resolution precedence tests (G2) in `tests/unit/runtime/test_resolver.py`
- [x] T019 Write legacy resolution tests (F-Legacy-001, F-Legacy-002, F-Legacy-003) in `tests/unit/runtime/test_resolver.py`

### Implementation Notes
- Resolution order: (1) `.kittify/overrides/{type}/{name}` > (2) `.kittify/{type}/{name}` + deprecation warning > (3) `~/.kittify/missions/{mission}/{type}/{name}` > (4) `PACKAGE_DIR/defaults/{type}/{name}` > raise FileNotFoundError
- Legacy tier emits warning via Python logging: `"Legacy asset resolved: {path} — run 'spec-kitty migrate' to clean up"`
- `resolve_template()` needs `name`, `project_dir`, `mission` parameters
- `resolve_command()` and `resolve_mission()` have similar signatures

### Parallel Opportunities
- T016 and T017 integration can run in parallel
- T018 and T019 tests can run in parallel

### Dependencies
- Depends on WP01 (`get_kittify_home()`)

### Risks & Mitigations
- Breaking existing template resolution: careful integration testing; run full test suite after changes

---

## Work Package WP04: spec-kitty migrate Command (Priority: P1)

**Goal**: Implement the `spec-kitty migrate` CLI command for explicit per-project cleanup of legacy shared assets.
**Independent Test**: `migrate --dry-run` reports correct dispositions; `migrate` removes identical copies, moves customized to overrides, keeps project-specific.
**Prompt**: `tasks/WP04-migrate-command.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T020 Implement `classify_asset()` function in `src/specify_cli/runtime/migrate.py`
- [ ] T021 Implement `execute_migration()` function in `src/specify_cli/runtime/migrate.py`
- [ ] T022 Implement `spec-kitty migrate` CLI command in `src/specify_cli/cli/commands/migrate_cmd.py`
- [ ] T023 Write migration classification tests (G3) — dry-run correctness, idempotency
- [ ] T024 Write migration customization tests — F-Legacy-003 (customized moved to overrides)

### Implementation Notes
- File classification via `filecmp.cmp(shallow=False)` — byte-identical comparison
- Categories: IDENTICAL (remove), CUSTOMIZED (move to `overrides/`), PROJECT_SPECIFIC (keep), UNKNOWN (keep + warn)
- PROJECT_SPECIFIC paths: `config.yaml`, `metadata.yaml`, `memory/`, `workspaces/`, `logs/`
- CLI flags: `--dry-run` (report only), `--verbose` (file-by-file detail), `--force` (skip confirmation)
- Idempotency: running twice produces same result with no errors

### Parallel Opportunities
- T023 and T024 tests can run in parallel

### Dependencies
- Depends on WP01 (`get_kittify_home()`) and WP03 (resolver context for determining what constitutes "shared assets")

### Risks & Mitigations
- Accidental data loss: `--dry-run` as default safety; require `--force` for unattended operation

---

## Work Package WP05: spec-kitty config --show-origin (Priority: P2)

**Goal**: Add `--show-origin` flag to `spec-kitty config` that displays resolved asset paths with tier labels.
**Independent Test**: Running `config --show-origin` shows each resolved asset with correct tier label.
**Prompt**: `tasks/WP05-config-show-origin.md`
**Estimated Size**: ~280 lines

### Included Subtasks
- [ ] T025 Implement `show_origin()` function that enumerates all resolvable assets
- [ ] T026 Add `--show-origin` flag to existing config CLI command
- [ ] T027 Write tests for `--show-origin` output (1A-14, 1A-15)
- [ ] T028 [P] Implement version pin warning for `runtime.pin_version` in config (F-Pin-001, 1A-16)

### Implementation Notes
- Enumerate: templates (spec.md, plan.md, tasks.md, etc.), missions (software-dev, research, etc.), commands, scripts, AGENTS.md
- For each asset, call resolver and capture `ResolutionResult` with tier label
- Display format: `Template: spec.md\n  Resolved: <path> (<tier label>)`
- Pin warning: check for `runtime.pin_version` in project config, emit "pinning not yet supported" warning

### Parallel Opportunities
- T028 (pin warning) independent of T025-T027

### Dependencies
- Depends on WP03 (resolver)

### Risks & Mitigations
- Existing `config` command structure may need adaptation; review current CLI structure before modifying

---

## Work Package WP06: Enhanced spec-kitty doctor (Priority: P2)

**Goal**: Add global runtime health checks to `spec-kitty doctor`.
**Independent Test**: Doctor detects missing `~/.kittify/`, version mismatch, mission corruption, and stale legacy assets.
**Prompt**: `tasks/WP06-enhanced-doctor.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T029 Implement global runtime health check functions in `src/specify_cli/runtime/doctor.py`
- [ ] T030 Integrate global checks into existing `spec-kitty doctor` command
- [ ] T031 Write test: missing `~/.kittify/` detected (1A-11)
- [ ] T032 Write test: `version.lock` mismatch detected (1A-12)
- [ ] T033 Write test: corrupted mission directory detected (1A-13)
- [ ] T034 Write test: stale legacy assets counted with migration recommendation (1A-10)

### Implementation Notes
- Health checks: `~/.kittify/` existence, `version.lock` vs CLI version, expected mission dirs present, legacy asset scan in project
- Each check returns `DoctorCheck(name, passed, message, severity)`
- Rich console output: checkmarks for pass, warnings for issues, error for corruption
- Stale legacy count: scan project `.kittify/` for files that exist at global path

### Parallel Opportunities
- T031-T034 tests can all run in parallel

### Dependencies
- Depends on WP01 (`get_kittify_home()`) and WP02 (`ensure_runtime()` context)

### Risks & Mitigations
- Must not break existing doctor checks; add new section, don't replace existing

---

## Work Package WP07: Streamlined spec-kitty init (Priority: P2)

**Goal**: Update `spec-kitty init` to create only project-specific files. Shared assets resolve from `~/.kittify/`.
**Independent Test**: `init` creates only config.yaml, metadata.yaml, memory/constitution.md. No mission copies.
**Prompt**: `tasks/WP07-streamlined-init.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T035 Modify init template preparation to skip shared asset copying
- [ ] T036 Update init to read templates from global `~/.kittify/` via resolver
- [ ] T037 Ensure agent directory generation reads from global runtime
- [ ] T038 Write tests: init creates only project-specific files
- [ ] T039 Write tests: init with populated `~/.kittify/` resolves shared assets correctly

### Implementation Notes
- Existing `init.py` is ~900 lines. Modify the template copying section (lines 619-630 area)
- Skip: mission copying, template copying, script copying, AGENTS.md copying
- Create only: `.kittify/config.yaml`, `.kittify/metadata.yaml`, `.kittify/memory/constitution.md`
- Agent asset generation (`generate_agent_assets`) should read templates via resolver, not from local `.kittify/`
- Ensure `ensure_runtime()` is called before init (global runtime must exist)

### Parallel Opportunities
- T038 and T039 tests can run in parallel

### Dependencies
- Depends on WP01, WP02, WP03 (global runtime must be operational and resolver must work)

### Risks & Mitigations
- Init is complex (~900 lines); minimize changes to avoid breaking existing flows
- Run full init integration test suite after changes

---

## Work Package WP08: CLI Integration + Entry Point Wiring (Priority: P1)

**Goal**: Wire `ensure_runtime()` into the CLI entry point so it runs on every command. Register new commands (migrate). Final integration testing.
**Independent Test**: Every CLI command triggers `ensure_runtime()` on startup. `migrate` command is accessible. Full end-to-end flow works.
**Prompt**: `tasks/WP08-cli-integration.md`
**Estimated Size**: ~350 lines

### Included Subtasks
- [ ] T040 Wire `ensure_runtime()` into Typer app callback (CLI entry point)
- [ ] T041 Register `migrate` command in CLI app
- [ ] T042 Add `ensure_runtime()` import and call to CLI startup
- [ ] T043 Write end-to-end integration test: fresh install → ensure_runtime → init → resolve
- [ ] T044 Write end-to-end integration test: upgrade → ensure_runtime → legacy project → resolve with warnings
- [ ] T045 Run existing test suite to verify no regressions

### Implementation Notes
- CLI entry point: find Typer `app.callback()` or equivalent main startup hook
- `ensure_runtime()` must be called BEFORE any command handler runs
- `migrate` command registered as `spec-kitty migrate` with `--dry-run`, `--verbose`, `--force`
- End-to-end tests verify the complete flow from install to resolution

### Parallel Opportunities
- T043 and T044 integration tests can run in parallel

### Dependencies
- Depends on WP01, WP02, WP03, WP04, WP05, WP06, WP07 (all components must be ready)

### Risks & Mitigations
- Regression risk: run full existing test suite (2032+ tests) after integration
- Performance impact: verify `ensure_runtime()` fast path is truly <100ms

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02, WP03 (parallel) → WP04, WP05, WP06 (parallel) → WP07 → WP08
- **Parallelization**:
  - WP02 and WP03 can run in parallel (both depend only on WP01)
  - WP04, WP05, WP06 can run in parallel (WP04 needs WP03, WP05 needs WP03, WP06 needs WP01+WP02)
  - WP07 needs WP01+WP02+WP03
  - WP08 is the integration WP and depends on all others
- **MVP Scope**: WP01 + WP02 + WP03 + WP08 constitute the minimum viable centralization (global runtime + resolution + CLI integration)

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create runtime/ subpackage | WP01 | P0 | No |
| T002 | Implement get_kittify_home() | WP01 | P0 | No |
| T003 | Implement get_package_asset_root() | WP01 | P0 | No |
| T004 | Cross-platform path tests | WP01 | P0 | Yes |
| T005 | SPEC_KITTY_HOME override tests | WP01 | P0 | Yes |
| T006 | Implement _merge_package_assets() | WP02 | P0 | No |
| T007 | Implement ensure_runtime() with locking | WP02 | P0 | No |
| T008 | Implement populate_from_package() | WP02 | P0 | No |
| T009 | _merge_package_assets() tests | WP02 | P0 | Yes |
| T010 | ensure_runtime() unit tests | WP02 | P0 | Yes |
| T011 | Concurrency tests (G5) | WP02 | P0 | Yes |
| T012 | Interrupted update recovery test (F-Bootstrap-001) | WP02 | P0 | Yes |
| T013 | ResolutionTier enum and ResolutionResult | WP03 | P0 | No |
| T014 | resolve_template/command/mission functions | WP03 | P0 | No |
| T015 | _warn_legacy_asset() deprecation warning | WP03 | P0 | No |
| T016 | Integrate resolver into Mission class | WP03 | P0 | Yes |
| T017 | Integrate resolver into init.py | WP03 | P0 | Yes |
| T018 | Resolution precedence tests (G2) | WP03 | P0 | Yes |
| T019 | Legacy resolution tests (F-Legacy-001..003) | WP03 | P0 | Yes |
| T020 | classify_asset() function | WP04 | P1 | No |
| T021 | execute_migration() function | WP04 | P1 | No |
| T022 | spec-kitty migrate CLI command | WP04 | P1 | No |
| T023 | Migration classification tests (G3) | WP04 | P1 | Yes |
| T024 | Migration customization tests (F-Legacy-003) | WP04 | P1 | Yes |
| T025 | show_origin() function | WP05 | P2 | No |
| T026 | --show-origin CLI flag | WP05 | P2 | No |
| T027 | --show-origin output tests (1A-14, 1A-15) | WP05 | P2 | Yes |
| T028 | Version pin warning (F-Pin-001) | WP05 | P2 | Yes |
| T029 | Global runtime health check functions | WP06 | P2 | No |
| T030 | Integrate into existing doctor command | WP06 | P2 | No |
| T031 | Missing ~/.kittify/ test (1A-11) | WP06 | P2 | Yes |
| T032 | version.lock mismatch test (1A-12) | WP06 | P2 | Yes |
| T033 | Corrupted mission dir test (1A-13) | WP06 | P2 | Yes |
| T034 | Stale legacy count test (1A-10) | WP06 | P2 | Yes |
| T035 | Skip shared asset copying in init | WP07 | P2 | No |
| T036 | Read templates from global via resolver | WP07 | P2 | No |
| T037 | Agent directory generation from global | WP07 | P2 | No |
| T038 | Init creates only project-specific files test | WP07 | P2 | Yes |
| T039 | Init with populated ~/.kittify/ test | WP07 | P2 | Yes |
| T040 | Wire ensure_runtime() into CLI entry point | WP08 | P1 | No |
| T041 | Register migrate command in CLI | WP08 | P1 | No |
| T042 | ensure_runtime() import and call | WP08 | P1 | No |
| T043 | E2E test: fresh install flow | WP08 | P1 | Yes |
| T044 | E2E test: upgrade with legacy project | WP08 | P1 | Yes |
| T045 | Regression test: full existing suite | WP08 | P1 | No |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: done
- WP02: planned
- WP03: planned
<!-- status-model:end -->
