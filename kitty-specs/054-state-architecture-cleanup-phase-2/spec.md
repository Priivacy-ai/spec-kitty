# Feature Specification: State Architecture Cleanup Phase 2

**Feature Branch**: `054-state-architecture-cleanup-phase-2`
**Created**: 2026-03-20
**Status**: Draft
**Input**: Obsidian evidence vault audit refresh (007-spec-kitty-2x-state-architecture-audit, 2026-03-20)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Feature-Level Mission Verification (Priority: P1)

A developer runs `spec-kitty verify --check-files` on a project containing a research-mission feature. The verification resolves the mission from the feature's `meta.json` (not a stale or absent project-level `.kittify/active-mission` marker) and validates the correct file set for that feature's mission.

**Why this priority**: The current fallback to project-level `active-mission` can silently validate the wrong mission file set. This is the highest-impact correctness bug identified in the audit — it affects verify, diagnostics, and manifest flows in production.

**Independent Test**: Create a project with a research-mission feature and no `.kittify/active-mission` file. Run verify and diagnostics; confirm they resolve `research` (not the `software-dev` default).

**Acceptance Scenarios**:

1. **Given** a project with a research-mission feature and no `.kittify/active-mission` marker, **When** `spec-kitty verify --check-files` runs against that feature, **Then** verification uses the `research` mission manifest — not `software-dev`.
2. **Given** a project with a stale `.kittify/active-mission` containing `software-dev` and a feature whose `meta.json` says `research`, **When** diagnostics runs against that feature, **Then** diagnostics reports the feature's actual mission (`research`).
3. **Given** a project with multiple features using different missions, **When** verify runs per-feature, **Then** each feature is verified against its own mission, independently.

---

### User Story 2 - Dead Mission Code Removal (Priority: P1)

A contributor reading the codebase finds a single, clear mission-resolution path with no deprecated writers, dead helpers, or duplicated parsing. The removed code no longer confuses code navigation or creates the illusion of alternative resolution paths.

**Why this priority**: Three separate code paths (a dead writer, a dead resolver, and a duplicated parser) all reference the same deprecated state surface. This is a maintenance hazard and a source of confusion when debugging mission-related behavior.

**Independent Test**: Grep for `set_active_mission`, `get_active_mission_key`, and `.kittify/active-mission` reads outside the migration that removes it; confirm zero production hits.

**Acceptance Scenarios**:

1. **Given** the codebase after cleanup, **When** searching for `set_active_mission()`, **Then** no production code references it (only the migration and its removal note).
2. **Given** the codebase after cleanup, **When** searching for `get_active_mission_key()`, **Then** it is either deleted entirely or retained only as an internal helper used by the single supported resolver.
3. **Given** the manifest module, **When** inspecting `FileManifest.active_mission`, **Then** it no longer reads `.kittify/active-mission` and instead requires explicit feature context.

---

### User Story 3 - Atomic Write Safety for Stateful Paths (Priority: P2)

A developer's state files are not corrupted or left half-written when a CLI operation is interrupted (e.g., Ctrl-C during sync, dashboard start, or workspace context save). All stateful write paths use write-to-temp-then-rename semantics.

**Why this priority**: `meta.json` was hardened to atomic writes, but 9 other stateful write paths still use plain `write_text()` / `json.dump()` / `yaml.dump()` / `toml.dump()`. A power failure or interruption during any of these writes can corrupt state.

**Independent Test**: For each converted path, simulate write interruption (mock `os.replace` to raise) and confirm the original file is untouched.

**Acceptance Scenarios**:

1. **Given** any of the 9 target write paths, **When** the write operation is interrupted, **Then** the original file content is preserved intact.
2. **Given** a successful write, **When** inspecting the written file, **Then** it contains the complete new content with no partial writes.
3. **Given** the codebase after cleanup, **When** searching for direct `write_text()` or `json.dump(open(...))` patterns in the 9 target modules, **Then** none remain — all use the shared atomic-write utility.

---

### User Story 4 - Constitution Git Policy Enforcement (Priority: P2)

A team member clones the repository and gets the constitution (answers, library) as shared team knowledge, while `references.yaml` (local machine-specific state) is excluded from Git to prevent merge conflicts. The state contract, `.gitignore`, and code are all aligned on this policy.

**Why this priority**: The constitution defines the project's way of working and must be committed. But `references.yaml` contains local machine paths that cause unnecessary merge conflicts. The current state is ambiguous — the state contract says `inside_repo_not_ignored` for all of them but no policy is enforced.

**Independent Test**: Clone the repo; confirm `answers.yaml` and `library/*.md` are present; confirm `references.yaml` is gitignored. Run `state_contract.py` validation; confirm no drift warnings.

**Acceptance Scenarios**:

1. **Given** the repo after cleanup, **When** checking `.gitignore`, **Then** `.kittify/constitution/references.yaml` is listed as ignored.
2. **Given** the repo after cleanup, **When** checking `.gitignore`, **Then** `.kittify/constitution/interview/answers.yaml` and `.kittify/constitution/library/*.md` are NOT ignored.
3. **Given** the state contract, **When** inspecting constitution entries, **Then** `answers.yaml` and `library/*.md` are `authoritative`, while `references.yaml` is `local_runtime`.
4. **Given** any migration that touches constitution state, **When** it runs, **Then** it respects the committed/ignored boundary.

---

### User Story 5 - Acceptance Implementation Deduplication (Priority: P2)

A contributor maintaining acceptance logic finds a single canonical implementation (in `specify_cli.acceptance`) and a thin import wrapper (in `scripts/tasks/acceptance_support.py`) that delegates to it. Changes need only be made once.

**Why this priority**: Two near-copy implementations is active maintenance overhead. The regression test that keeps them aligned proves the duplication is a known risk. Reducing to one true implementation eliminates that risk.

**Independent Test**: Modify a validation rule in `acceptance.py`; confirm the standalone `tasks_cli.py` path reflects the change without separate edits.

**Acceptance Scenarios**:

1. **Given** the codebase after cleanup, **When** inspecting `acceptance_support.py`, **Then** it contains only import-and-delegate calls to `specify_cli.acceptance` (no duplicated logic).
2. **Given** the CLI acceptance path, **When** running acceptance, **Then** behavior is identical to before the deduplication.
3. **Given** the standalone `tasks_cli.py` acceptance path, **When** running acceptance, **Then** behavior is identical to before the deduplication.

---

### User Story 6 - Legacy Bridge Import Hardening (Priority: P3)

When the `legacy_bridge` module is missing or fails to import on a 2.x installation, the system raises a clear error instead of silently skipping compatibility view updates. Developers diagnosing missing frontmatter updates are no longer misled by silent swallowing of import failures.

**Why this priority**: The transitional `ImportError` fallback was appropriate during initial development (WP06 not yet merged), but `legacy_bridge.py` is now in-tree and tested. A missing import now indicates a real packaging regression, not a planned transitional state.

**Independent Test**: Patch the import to raise `ImportError`; confirm the emit call raises (or logs a clear error) instead of silently succeeding.

**Acceptance Scenarios**:

1. **Given** a 2.x installation where `legacy_bridge` import fails, **When** `emit_status_transition()` is called, **Then** it raises a clear error (not silently skipped).
2. **Given** a normal 2.x installation, **When** `emit_status_transition()` is called, **Then** the legacy bridge updates proceed as before.
3. **Given** the test suite, **When** running tests for emit, **Then** there is a test that injects `ImportError` for `legacy_bridge` and asserts the error is surfaced.

---

### User Story 7 - Vault Notes Updated (Priority: P3)

After all cleanup is complete, the Obsidian evidence vault reflects the implementation outcome — what changed, what was intentionally left, and any new evidence discovered during implementation.

**Why this priority**: Stale audit documentation creates false confidence. The vault must remain the living source of truth for the state architecture audit.

**Independent Test**: Read the vault notes; confirm they reference the cleanup commit(s), updated findings, and any deferred items.

**Acceptance Scenarios**:

1. **Given** the completed cleanup, **When** reading the vault's refresh findings, **Then** each of the 7 cleanup areas has an implementation outcome recorded.
2. **Given** the completed cleanup, **When** reading the evidence log, **Then** new evidence entries reference specific commits and test results.

---

### Edge Cases

- What happens when a project has no features at all (only project-level state) and verify runs? → Verify should report "no features to verify" rather than falling back to project-level mission.
- What happens when `meta.json` exists but has no `mission` field? → Treat as `software-dev` default (existing behavior) but emit a warning.
- What happens when `references.yaml` is already tracked in Git history? → The `.gitignore` addition prevents future commits; existing history is preserved (no force-remove from history).
- What happens when an atomic write's temp file is left behind after a crash? → The next write attempt should succeed by overwriting the stale temp file. Temp files should be in the same directory as the target (for same-filesystem rename guarantee).
- What happens when `acceptance_support.py` is imported standalone without `specify_cli` installed? → The thin wrapper should raise a clear `ImportError` with a message directing the user to install `spec-kitty-cli`.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Feature-level mission resolution | As a developer, I want verify/diagnostics to resolve mission from the feature's `meta.json` so that non-software-dev features are validated correctly. | High | Open |
| FR-002 | Remove active-mission fallback from manifest | As a developer, I want `FileManifest` to stop reading `.kittify/active-mission` so that stale project-level state cannot override feature truth. | High | Open |
| FR-003 | Remove active-mission fallback from verify | As a developer, I want `verify_enhanced.py` to require explicit feature context for mission-sensitive checks so that verification is always correct. | High | Open |
| FR-004 | Remove active-mission fallback from diagnostics | As a developer, I want dashboard diagnostics to resolve mission per-feature so that diagnostic output is accurate. | High | Open |
| FR-005 | Delete `set_active_mission()` | As a contributor, I want the dead deprecated writer removed so that the codebase has no misleading API. | High | Open |
| FR-006 | Delete or consolidate `get_active_mission_key()` | As a contributor, I want the dead resolver helper removed or made the single supported resolver so that there is one path, not three. | High | Open |
| FR-007 | Remove duplicate active-mission parsing from manifest | As a contributor, I want manifest to use the retained resolver (or no resolver, if feature context is always required) so that parsing is not duplicated. | High | Open |
| FR-008 | Atomic writes for runtime_bridge | As a developer, I want `.kittify/runtime/feature-runs.json` written atomically so that interruption cannot corrupt it. | Medium | Open |
| FR-009 | Atomic writes for workspace_context | As a developer, I want `.kittify/workspaces/*.json` written atomically. | Medium | Open |
| FR-010 | Atomic writes for constitution context | As a developer, I want `.kittify/constitution/context-state.json` written atomically. | Medium | Open |
| FR-011 | Atomic writes for dashboard lifecycle | As a developer, I want `.kittify/.dashboard` written atomically. | Medium | Open |
| FR-012 | Atomic writes for sync clock | As a developer, I want `~/.spec-kitty/clock.json` written atomically. | Medium | Open |
| FR-013 | Atomic writes for sync auth | As a developer, I want `~/.spec-kitty/credentials` written atomically. | Medium | Open |
| FR-014 | Atomic writes for sync config | As a developer, I want `~/.spec-kitty/config.toml` written atomically. | Medium | Open |
| FR-015 | Atomic writes for tracker config | As a developer, I want tracker config payloads written atomically. | Medium | Open |
| FR-016 | Atomic writes for upgrade metadata | As a developer, I want `.kittify/metadata.yaml` written atomically. | Medium | Open |
| FR-017 | Commit constitution answers and library | As a team member, I want `answers.yaml` and `library/*.md` tracked in Git so that the project's way of working is shared. | Medium | Open |
| FR-018 | Ignore constitution references | As a team member, I want `references.yaml` gitignored so that local machine-specific state does not cause merge conflicts. | Medium | Open |
| FR-019 | Update state contract for constitution policy | As a contributor, I want the state contract to classify constitution surfaces correctly (authoritative vs local_runtime). | Medium | Open |
| FR-020 | Deduplicate acceptance to single implementation | As a contributor, I want `acceptance_support.py` to delegate to `acceptance.py` so that changes are made in one place. | Medium | Open |
| FR-021 | Harden legacy_bridge import in emit | As a developer, I want a missing `legacy_bridge` import on 2.x to raise a clear error so that packaging regressions are not silently hidden. | Low | Open |
| FR-022 | Remove stale WP06 transitional comment | As a contributor, I want the `# WP06 not yet available` comment removed so that the code reflects current reality. | Low | Open |
| FR-023 | Update Obsidian vault with outcomes | As a project maintainer, I want the audit vault updated with implementation results so that the audit remains current. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Atomic write durability | All atomic writes must use write-to-temp-then-rename on the same filesystem, guaranteeing either full old content or full new content after any interruption. | Reliability | High | Open |
| NFR-002 | No behavior regression | All existing test suites pass after cleanup. No user-visible behavior changes except where deprecated behavior is explicitly removed. | Compatibility | High | Open |
| NFR-003 | Test coverage per cleanup area | Each of the 7 cleanup areas has at least one targeted test proving the new behavior. | Quality | Medium | Open |
| NFR-004 | State contract consistency | `state_contract.py` entries match the actual `.gitignore` and code behavior with zero drift. | Correctness | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Python 3.11+ | All code must be compatible with Python 3.11+. | Technical | High | Open |
| C-002 | Preserve working behavior | No removal of non-deprecated working behavior. Only deprecated code paths are removed. | Technical | High | Open |
| C-003 | Ruff compliance | All changes must pass `ruff check .` and `ruff format --check .`. | Technical | High | Open |
| C-004 | Same-filesystem atomic rename | Temp files for atomic writes must be created in the same directory as the target file to guarantee `os.replace()` atomicity. | Technical | Medium | Open |
| C-005 | No forced Git history rewrite | `references.yaml` is added to `.gitignore` but not force-removed from Git history. | Process | Medium | Open |
| C-006 | Vault update required | The Obsidian evidence vault must be updated as part of this feature, not deferred. | Process | Medium | Open |

### Key Entities

- **StateSurface**: An entry in `state_contract.py` representing a file or directory with a classification (`authoritative`, `local_runtime`, `derived`, `compatibility`, `deprecated`, etc.) and Git boundary metadata.
- **Mission**: A project workflow type (`software-dev`, `research`, `documentation`) resolved from feature `meta.json` — no longer from project-level markers.
- **AtomicWriter**: A shared utility that writes content to a temp file in the target directory and then atomically renames it to the target path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero project-level active-mission reads remain in production code outside the removal migration.
- **SC-002**: All 9 stateful write paths use atomic write-then-rename semantics, verified by targeted tests.
- **SC-003**: `state_contract.py` classifies `references.yaml` as `local_runtime` and `.gitignore` excludes it; `answers.yaml` and `library/*.md` are `authoritative` and tracked.
- **SC-004**: `acceptance_support.py` contains zero duplicated logic — only import-and-delegate calls.
- **SC-005**: A test exists that injects `ImportError` for `legacy_bridge` and asserts the error is surfaced (not silently swallowed).
- **SC-006**: All existing tests pass (`pytest tests/ -q` exits 0).
- **SC-007**: The Obsidian vault evidence log contains entries referencing implementation commits and test results for all 7 cleanup areas.
