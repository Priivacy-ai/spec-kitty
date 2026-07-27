# Feature Specification: ~/.kittify Runtime Centralization

**Feature Branch**: `036-kittify-runtime-centralization`
**Created**: 2026-02-09
**Status**: Draft
**Phase**: 1A — Local-First Runtime Convergence Plan
**Input**: Phase 1A seed prompt from cross-repo convergence orchestration (013)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Upgrade Across All Projects (Priority: P1)

A developer managing multiple Spec Kitty projects upgrades the CLI via `pip install --upgrade spec-kitty-cli`. On the next `spec-kitty` invocation in any project, shared runtime assets (missions, templates, commands, scripts, AGENTS.md) are automatically updated in the user-global `~/.kittify/` directory. No per-project `spec-kitty upgrade` or `spec-kitty init` is required.

**Why this priority**: This is the core value proposition — eliminating per-project upgrade friction and version drift, the #1 user pain point.

**Independent Test**: Run `pip install --upgrade`, invoke any spec-kitty command in an existing project, verify the global runtime is updated and the project resolves updated assets.

**Acceptance Scenarios**:

1. **Given** CLI version 2.5.0 installed with `~/.kittify/cache/version.lock` reading "2.4.0", **When** user runs any `spec-kitty` command, **Then** `ensure_runtime()` updates `~/.kittify/` assets to 2.5.0 and writes "2.5.0" to `version.lock`
2. **Given** CLI version 2.5.0 installed with `version.lock` reading "2.5.0", **When** user runs any `spec-kitty` command, **Then** `ensure_runtime()` returns in <100ms without acquiring a file lock
3. **Given** `~/.kittify/` does not exist (fresh install), **When** user runs any `spec-kitty` command, **Then** `ensure_runtime()` creates `~/.kittify/` with all package-managed assets and writes `version.lock`

---

### User Story 2 - Project-Specific Overrides (Priority: P1)

A power user has customized a template (e.g., `spec.md`) for a specific project. After the centralization upgrade, their customization continues to take precedence over the global version. They can place customized files in `.kittify/overrides/templates/` and these always resolve first.

**Why this priority**: Blocking issue if customizations silently break — equal priority with upgrade automation.

**Independent Test**: Place a custom template in `.kittify/overrides/templates/`, run a command that resolves that template, verify the override is used.

**Acceptance Scenarios**:

1. **Given** project has `.kittify/overrides/templates/spec.md`, **When** CLI resolves `spec.md`, **Then** the project override is used (priority 1)
2. **Given** project has NO override but has legacy `.kittify/templates/spec.md`, **When** CLI resolves `spec.md`, **Then** the legacy file is used (priority 2) with a deprecation warning
3. **Given** project has neither override nor legacy file, **When** CLI resolves `spec.md`, **Then** `~/.kittify/missions/{mission}/templates/spec.md` is used (priority 3)
4. **Given** no file exists at any resolution tier, **When** CLI resolves a template, **Then** a `FileNotFoundError` is raised — no silent fallback

---

### User Story 3 - Legacy Project Backward Compatibility (Priority: P1)

A user with existing projects (pre-centralization `.kittify/` layout) upgrades the CLI. All their projects continue to work without running `spec-kitty migrate`. Legacy project assets resolve via the deprecation tier (priority 2) with visible warnings recommending migration.

**Why this priority**: Zero-downtime upgrade is essential for adoption.

**Independent Test**: Use a pre-centralization project layout, run spec-kitty commands, verify everything works with deprecation warnings emitted.

**Acceptance Scenarios**:

1. **Given** pre-centralization project with customized templates in `.kittify/templates/`, **When** user runs spec-kitty commands, **Then** legacy templates resolve and deprecation warning is emitted (F-Legacy-001)
2. **Given** pre-centralization project with no customizations in `.kittify/`, **When** user runs spec-kitty commands, **Then** legacy files resolve identically and deprecation warning is emitted (F-Legacy-002)
3. **Given** pre-centralization project with stale `.kittify/templates/spec.md` differing from global, **When** CLI resolves `spec.md`, **Then** legacy version resolves (backward compat) with deprecation warning (F-Legacy-003)

---

### User Story 4 - Explicit Project Migration (Priority: P2)

A user runs `spec-kitty migrate` to clean up per-project shared asset copies. The command identifies files identical to global versions (removes them), moves customized files to `.kittify/overrides/`, and keeps project-specific files.

**Why this priority**: Important for cleanup but not blocking — projects work without migrating.

**Independent Test**: Run `spec-kitty migrate --dry-run` on a legacy project, verify correct disposition reporting.

**Acceptance Scenarios**:

1. **Given** project with identical and customized shared assets, **When** `spec-kitty migrate --dry-run` runs, **Then** correct file disposition is reported without modifying filesystem (1A-03)
2. **Given** project with customized and identical shared assets, **When** `spec-kitty migrate` runs, **Then** identical copies are removed, customized files move to `.kittify/overrides/`, project-specific files are kept (1A-05)
3. **Given** project already migrated, **When** `spec-kitty migrate` runs again, **Then** identical outcome with no errors on second run (1A-04)

---

### User Story 5 - Debugging Resolution (Priority: P2)

A user is confused about which version of a template is being used. They run `spec-kitty config --show-origin` to see exactly where each resolved asset comes from, with tier labels (override, legacy, global, package default).

**Why this priority**: Debugging tool — needed for trust and support, not daily use.

**Independent Test**: Place files at different resolution tiers, run `config --show-origin`, verify tier labels match.

**Acceptance Scenarios**:

1. **Given** files exist at multiple resolution tiers, **When** `spec-kitty config --show-origin` runs, **Then** each asset's resolved path and tier label is shown (1A-14, 1A-15)
2. **Given** a project with `runtime.pin_version` in config, **When** any command runs, **Then** CLI emits "pinning not yet supported" warning and uses latest global assets (F-Pin-001, 1A-16)

---

### User Story 6 - Health Diagnostics (Priority: P2)

A user runs `spec-kitty doctor` to diagnose issues. The enhanced doctor checks global runtime health — `~/.kittify/` existence, `version.lock` match, mission directory integrity, stale legacy asset count, migration recommendations.

**Why this priority**: Essential for support but not for day-to-day operation.

**Independent Test**: Remove `~/.kittify/`, run `doctor`, verify "missing global runtime" message.

**Acceptance Scenarios**:

1. **Given** `~/.kittify/` is missing, **When** `spec-kitty doctor` runs, **Then** missing global runtime is detected and reported (1A-11)
2. **Given** `version.lock` is stale or absent, **When** `spec-kitty doctor` runs, **Then** version mismatch is detected (1A-12)
3. **Given** managed mission directory is missing from `~/.kittify/`, **When** `spec-kitty doctor` runs, **Then** corruption is detected (1A-13)
4. **Given** project has stale legacy assets, **When** `spec-kitty doctor` runs, **Then** stale count and migration recommendation are shown (1A-10)

---

### User Story 7 - New Project Initialization (Priority: P2)

A user runs `spec-kitty init` for a new project. Only project-specific files are created (config.yaml, metadata.yaml, memory/constitution.md). Shared assets resolve from `~/.kittify/` automatically.

**Why this priority**: Streamlines onboarding but existing init still works.

**Independent Test**: Run `spec-kitty init` in a fresh directory, verify only 3 project-specific files created.

**Acceptance Scenarios**:

1. **Given** a fresh directory with no `.kittify/`, **When** `spec-kitty init` runs, **Then** only project-specific files are created (config.yaml, metadata.yaml, memory/constitution.md)
2. **Given** `~/.kittify/` is populated, **When** a new project runs any spec-kitty command, **Then** shared assets resolve from the global directory

---

### User Story 8 - Concurrent CLI Safety (Priority: P2)

Multiple CLI instances start simultaneously (e.g., parallel CI jobs or terminal tabs). The `ensure_runtime()` file lock serializes updates. No corruption occurs.

**Why this priority**: Safety requirement for CI environments.

**Independent Test**: Launch N parallel `spec-kitty` invocations targeting the same `~/.kittify/`, verify no corruption (F-Bootstrap-001, 1A-06).

**Acceptance Scenarios**:

1. **Given** N CLI processes start simultaneously with stale `version.lock`, **When** all invoke `ensure_runtime()`, **Then** exactly one acquires the lock and updates; others wait and return without corruption (1A-06)
2. **Given** `ensure_runtime()` is interrupted mid-update (no `version.lock` written), **When** next CLI invocation starts, **Then** retry completes successfully (1A-07)

---

### User Story 9 - Cross-Platform Compatibility (Priority: P3)

Spec Kitty works correctly on macOS, Linux, and Windows. Default path is `~/.kittify/` on Unix and `%LOCALAPPDATA%\kittify\` on Windows. `SPEC_KITTY_HOME` environment variable overrides on all platforms.

**Why this priority**: Windows is a secondary platform for the current user base.

**Independent Test**: Set `SPEC_KITTY_HOME` to a non-default path, verify runtime resolves there (1A-08, 1A-09).

**Acceptance Scenarios**:

1. **Given** macOS or Linux, **When** `get_kittify_home()` is called without env override, **Then** returns `~/.kittify/` (1A-08)
2. **Given** Windows, **When** `get_kittify_home()` is called without env override, **Then** returns `%LOCALAPPDATA%\kittify\` via `platformdirs` (1A-08)
3. **Given** any platform with `SPEC_KITTY_HOME` set, **When** `get_kittify_home()` is called, **Then** returns the env var path (1A-09)

---

### Edge Cases

- **Interrupted update recovery**: `ensure_runtime()` interrupted before writing `version.lock` — next CLI start must detect and retry (F-Bootstrap-001)
- **Concurrent race condition**: Multiple processes attempt update simultaneously — file lock must serialize without deadlock (G5)
- **Stale legacy with identical content**: Legacy file byte-identical to global — `migrate` correctly identifies as removable, not customized
- **Legacy file customized**: Legacy file differs from global — `migrate` moves to `overrides/`, does not delete
- **Missing managed mission directory**: Package update deletes a managed directory — `doctor` detects corruption, `ensure_runtime()` repairs on next run
- **Version pinning attempted**: Project config contains `runtime.pin_version` — CLI warns "not yet supported", never honors the pin silently (F-Pin-001)
- **Empty `~/.kittify/` directory**: Directory exists but no contents — treated as fresh, `ensure_runtime()` populates fully
- **Read-only filesystem**: `~/.kittify/` on read-only mount — clear error raised, not silent degradation
- **User custom missions preserved**: `~/.kittify/missions/custom/` never overwritten by `ensure_runtime()` updates

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `get_kittify_home()` function returning the user-global directory path: `~/.kittify/` on macOS/Linux, `%LOCALAPPDATA%\kittify\` on Windows (via `platformdirs`), overridable by `SPEC_KITTY_HOME` environment variable
- **FR-002**: System MUST implement `ensure_runtime()` that runs on every CLI startup and atomically populates/updates `~/.kittify/` from package assets when `version.lock` is missing or stale
- **FR-003**: `ensure_runtime()` fast path MUST complete in <100ms when `version.lock` matches CLI version, without acquiring a file lock
- **FR-004**: `ensure_runtime()` MUST use exclusive file locking (`fcntl.flock` on Unix, `msvcrt.locking` on Windows) to serialize concurrent CLI starts
- **FR-005**: `ensure_runtime()` MUST write `version.lock` last, so incomplete updates are detectable and retried on next CLI start
- **FR-006**: `ensure_runtime()` MUST preserve user data during updates: `~/.kittify/config.yaml` and `~/.kittify/missions/custom/` are never overwritten
- **FR-007**: System MUST implement 4-tier template/command/mission resolution: (1) project `.kittify/overrides/` > (2) legacy project `.kittify/` paths with deprecation warnings > (3) user global `~/.kittify/` > (4) package defaults (bootstrap only)
- **FR-008**: Resolution MUST raise `FileNotFoundError` when a requested asset is not found at any tier — no silent fallback
- **FR-009**: Legacy resolution tier (priority 2) MUST emit a visible deprecation warning when resolved, recommending `spec-kitty migrate`
- **FR-010**: System MUST provide `spec-kitty migrate` command with `--dry-run`, `--verbose`, and `--force` flags for explicit project cleanup
- **FR-011**: `spec-kitty migrate` MUST identify files identical to global versions and remove them; customized files MUST be moved to `.kittify/overrides/`; project-specific files MUST be kept
- **FR-012**: `spec-kitty migrate` MUST be idempotent — running twice produces identical outcome with no errors
- **FR-013**: System MUST provide `spec-kitty config --show-origin` displaying resolved asset paths with tier labels (override, legacy, global, package default)
- **FR-014**: `spec-kitty doctor` MUST check global runtime health: `~/.kittify/` existence, `version.lock` match, mission directory integrity, stale legacy asset count, migration recommendations
- **FR-015**: `spec-kitty init` MUST create only project-specific files (config.yaml, metadata.yaml, memory/constitution.md) — no shared assets copied
- **FR-016**: System MUST handle `runtime.pin_version` in project config by emitting a clear warning ("pinning not yet supported") and using latest global assets — pin MUST NEVER be silently honored
- **FR-017**: Package-managed directories (`missions/software-dev`, `missions/research`, `missions/documentation`, `missions/plan`, `missions/audit`, `missions/refactor`, `scripts/`) and files (`AGENTS.md`) MUST be overwritten on update; `config.yaml`, `missions/custom/`, and `cache/` (except `version.lock`) MUST never be touched
- **FR-018**: All Phase 1A features MUST pass on both `main` and `2.x` branches (lockstep parity gates R4, B1)

### Key Entities

- **Global Runtime Directory (`~/.kittify/`)**: User-global directory containing shared missions, scripts, AGENTS.md, config, and cache. Managed by `ensure_runtime()`.
- **Version Lock (`~/.kittify/cache/version.lock`)**: Text file containing the CLI version string. Written last during updates. Used for fast-path version comparison.
- **Project Override Directory (`.kittify/overrides/`)**: Per-project directory for customized templates/missions that shadow global assets.
- **Legacy Asset**: Shared asset found at old per-project `.kittify/` paths (pre-centralization). Resolves via priority 2 with deprecation warnings during the deprecation window.
- **Resolution Tier**: One of four precedence levels (override, legacy, global, package default) in the asset resolution algorithm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `pip install --upgrade`, all projects resolve updated shared assets on next CLI invocation without any per-project commands
- **SC-002**: `ensure_runtime()` completes in <100ms on the fast path (version match) across all supported platforms
- **SC-003**: Existing projects with pre-centralization `.kittify/` layouts continue to work without migration (zero-downtime upgrade)
- **SC-004**: `spec-kitty init` creates 3 or fewer project-specific files (down from ~50) and completes in <0.5s
- **SC-005**: N concurrent CLI starts produce no corruption in `~/.kittify/` (concurrency safety)
- **SC-006**: `spec-kitty migrate` correctly classifies 100% of files as identical (remove), customized (move to overrides), or project-specific (keep)
- **SC-007**: All 18 acceptance conditions (1A-01 through 1A-18) from the acceptance matrix pass
- **SC-008**: All test fixtures (F-Legacy-001..003, F-Pin-001, F-Bootstrap-001) pass
- **SC-009**: All quality gates (G2 Resolution, G3 Migration, G5 Concurrency, G6 Cross-Platform) pass
- **SC-010**: Branch lockstep parity (R4, B1): all Phase 1A tests pass identically on both `main` and `2.x`

### Assumptions

- `platformdirs` is already a project dependency (verified in pyproject.toml)
- The existing migration infrastructure (20+ migrations, auto-discovery registry) will be extended for Phase 1A
- `fcntl` is available on macOS/Linux; `msvcrt` on Windows — no third-party locking library needed
- The deprecation window for legacy tier (priority 2) will be one major version after Phase 1A stabilizes
- `~/.kittify/` permissions follow user umask defaults — no special permission management required

### Dependencies

- **Phase 1A has no external dependencies** — it is the self-contained starting point
- Phase 1B (Mission DSL Foundation) depends on Phase 1A completion
- Phase 1A must be backported to `main` within the same sprint per lockstep policy
