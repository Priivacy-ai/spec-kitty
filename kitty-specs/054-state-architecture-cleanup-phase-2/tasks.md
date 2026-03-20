# Work Packages: State Architecture Cleanup Phase 2

**Inputs**: Design documents from `kitty-specs/054-state-architecture-cleanup-phase-2/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, quickstart.md

**Tests**: Targeted tests included per cleanup area (required by spec).

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: Shared Atomic Write Utility (Priority: P0)

**Goal**: Extract the atomic-write pattern from `feature_metadata.py` into a shared utility at `src/specify_cli/core/atomic.py` so all 9 stateful write paths can reuse it.
**Independent Test**: `pytest tests/specify_cli/test_atomic_write.py -v` passes. The `feature_metadata.py` module still works after refactor.
**Prompt**: `tasks/WP01-shared-atomic-write-utility.md`
**Requirement Refs**: FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, NFR-001, C-004

### Included Subtasks
- [x] T001 Create `src/specify_cli/core/atomic.py` with public `atomic_write()` function
- [x] T002 Refactor `src/specify_cli/feature_metadata.py` to import from `core.atomic` instead of private `_atomic_write()`
- [x] T003 Create `tests/specify_cli/test_atomic_write.py` with success, interrupt, mkdir, bytes/str, and cleanup tests

### Implementation Notes
- Extract the exact pattern from `feature_metadata.py:_atomic_write()` (lines 84-108)
- Add `mkdir: bool = False` parameter for callers that need `parent.mkdir(parents=True, exist_ok=True)`
- Support both `str` (encoded to UTF-8) and `bytes` (raw) content
- Use `.atomic-` prefix (not `.meta-`) to distinguish from legacy usage
- Ensure `BaseException` catch for cleanup (handles KeyboardInterrupt)

### Parallel Opportunities
- WP01 can run in parallel with WP02, WP06, WP07, WP08.

### Dependencies
- None (foundation package).

### Risks & Mitigations
- Permission preservation: `os.replace()` may not preserve file permissions on some platforms → test with `stat` checks.

---

## Work Package WP02: Active-Mission Fallback Removal (Priority: P1)

**Goal**: Remove project-level `.kittify/active-mission` fallback from manifest, verify, and diagnostics so mission resolution uses feature-level `meta.json`.
**Independent Test**: Create a project with a research-mission feature and no `.kittify/active-mission`; confirm verify/diagnostics resolve `research`.
**Prompt**: `tasks/WP02-active-mission-fallback-removal.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004

### Included Subtasks
- [x] T004 Remove `_detect_active_mission()` from `src/specify_cli/manifest.py` and refactor `FileManifest` to not carry `active_mission` property
- [x] T005 Update `src/specify_cli/verify_enhanced.py` to accept `feature_dir: Path | None` parameter and resolve mission from `meta.json`
- [x] T006 Update `src/specify_cli/dashboard/diagnostics.py` to accept `feature_dir: Path | None` and resolve mission per-feature
- [x] T007 Update `src/specify_cli/cli/commands/mission.py` `current_cmd()` to show explicit "no active feature detected" instead of project-level fallback
- [x] T008 Add/update tests: manifest without active_mission, verify with feature context, diagnostics with feature context

### Implementation Notes
- `FileManifest.__init__()` currently sets `self.active_mission = self._detect_active_mission()` and derives `self.mission_dir` from it. After removing, callers that need mission context must resolve it from feature `meta.json` via `get_mission_for_feature()`.
- `verify_enhanced.py::run_enhanced_verify()` uses `manifest.active_mission` for file integrity checks. Refactor to accept `feature_dir` and call `get_mission_for_feature(feature_dir, project_root)`.
- The CLI `current_cmd()` (lines 186-231) has two branches: feature-detected (uses `get_mission_for_feature`) and no-feature (uses `get_active_mission`). Change the no-feature branch to report "no feature context" instead.

### Parallel Opportunities
- T004, T005, T006, T007 touch different files and can be developed concurrently by the same agent.

### Dependencies
- None.

### Risks & Mitigations
- Breaking callers of `FileManifest.active_mission` or `FileManifest.mission_dir` → grep all usages before removing.

---

## Work Package WP03: Dead Mission Code Deletion (Priority: P1)

**Goal**: Delete deprecated `set_active_mission()`, unused `get_active_mission_key()`, and update the state contract to reflect removal.
**Independent Test**: Grep for `set_active_mission`, `get_active_mission_key` in production code returns zero hits.
**Prompt**: `tasks/WP03-dead-mission-code-deletion.md`
**Requirement Refs**: FR-005, FR-006, FR-007

### Included Subtasks
- [ ] T009 Delete `set_active_mission()` from `src/specify_cli/mission.py`
- [ ] T010 Delete `get_active_mission_key()` from `src/specify_cli/core/project_resolver.py` and remove from `src/specify_cli/core/__init__.py` exports
- [ ] T011 Update `src/specify_cli/state_contract.py` — remove `active_mission_marker` entry entirely
- [ ] T012 Add `.kittify/active-mission` to `.gitignore` (prevent accidental recommit of legacy markers)
- [ ] T013 Update/remove tests referencing deleted functions (`tests/runtime/test_project_resolver.py`, any test calling `set_active_mission`)

### Implementation Notes
- `set_active_mission()` is at mission.py:523-566. It's deprecated since v0.8.0 with no production callers.
- `get_active_mission_key()` is at project_resolver.py:107-134. Only tests reference it.
- When removing from state_contract, also remove the import of `DEFAULT_MISSION_KEY` if it was only used for this entry.
- Check if any migration references `set_active_mission()` — the `m_0_8_0_remove_active_mission.py` migration may import it. If so, keep a minimal stub or inline the logic in the migration.

### Parallel Opportunities
- T009, T010, T011, T012 touch different files and can proceed concurrently.

### Dependencies
- Depends on WP02. Active-mission reads must be removed before deleting the code they call.

### Risks & Mitigations
- Migration breakage: `m_0_8_0_remove_active_mission.py` may import the function being deleted → check and handle.

---

## Work Package WP04: Atomic Write Conversion — Local State Files (Priority: P2)

**Goal**: Convert 5 local-state write paths to use the shared `atomic_write()` utility.
**Independent Test**: For each converted path, mock `os.replace` to raise and confirm original file is untouched.
**Prompt**: `tasks/WP04-atomic-write-local-state.md`
**Requirement Refs**: FR-008, FR-009, FR-010, FR-011, FR-016, NFR-001

### Included Subtasks
- [x] T014 [P] Convert `src/specify_cli/next/runtime_bridge.py` — `_save_feature_runs()`: replace `path.write_text(json.dumps(...))` with `atomic_write(path, content, mkdir=True)`
- [x] T015 [P] Convert `src/specify_cli/workspace_context.py` — `save_context()`: replace `context_path.write_text(json.dumps(...))` with `atomic_write(context_path, content)`
- [x] T016 [P] Convert `src/specify_cli/constitution/context.py` — `_write_state()`: replace `path.write_text(json.dumps(...))` with `atomic_write(path, content, mkdir=True)`
- [x] T017 [P] Convert `src/specify_cli/dashboard/lifecycle.py` — `_write_dashboard_file()`: replace `dashboard_file.write_text(...)` with `atomic_write(dashboard_file, content, mkdir=True)`
- [x] T018 [P] Convert `src/specify_cli/upgrade/metadata.py` — `ProjectMetadata.save()`: replace `open() + yaml.dump()` with serialize-to-string then `atomic_write(path, content, mkdir=True)`

### Implementation Notes
- Each conversion follows the same pattern: serialize content to string first, then call `atomic_write(path, content, mkdir=True)`.
- For `metadata.py` (T018): the header comment + yaml.dump must be serialized to a string buffer first (use `io.StringIO`), then passed to `atomic_write`.
- For `dashboard/lifecycle.py` (T017): the multi-line format (url, port, token, pid) is already assembled as a string before `write_text`.
- All 5 files currently call `path.parent.mkdir(parents=True, exist_ok=True)` before writing — the `mkdir=True` parameter on `atomic_write` handles this.

### Parallel Opportunities
- All 5 subtasks touch independent files — fully parallelizable.

### Dependencies
- Depends on WP01 (shared `atomic_write()` utility must exist).

### Risks & Mitigations
- YAML serialization to string: `yaml.dump()` with `StringIO` destination may differ slightly from direct file dump → test output matches.

---

## Work Package WP05: Atomic Write Conversion — Sync and Config (Priority: P2)

**Goal**: Convert 4 sync/config write paths to use the shared `atomic_write()` utility, handling special cases (file locks, existing atomic impl, TOML/YAML serialization).
**Independent Test**: For each converted path, verify atomic semantics (interrupt leaves original intact).
**Prompt**: `tasks/WP05-atomic-write-sync-config.md`
**Requirement Refs**: FR-012, FR-013, FR-014, FR-015, NFR-001

### Included Subtasks
- [x] T019 Convert `src/specify_cli/sync/clock.py` — `LamportClock.save()`: replace inline `tempfile.mkstemp + os.replace` with `atomic_write(self._storage_path, content, mkdir=True)`
- [x] T020 Convert `src/specify_cli/sync/auth.py` — `CredentialStore.save()`: add `atomic_write()` inside the existing `self._acquire_lock()` context; keep file lock + 600 permissions
- [x] T021 [P] Convert `src/specify_cli/sync/config.py` — `set_server_url()`: replace `open() + toml.dump()` with serialize-to-string then `atomic_write(path, content, mkdir=True)`
- [x] T022 [P] Convert `src/specify_cli/tracker/config.py` — `save_tracker_config()`: replace `open() + YAML.dump()` with serialize-to-string then `atomic_write(path, content, mkdir=True)`

### Implementation Notes
- **clock.py** (T019): Already has atomic write logic (lines 62-87). Replace with the shared utility. The `json.dump(data, f, indent=2)` becomes `json.dumps(data, indent=2)` → `atomic_write(path, content)`.
- **auth.py** (T020): Uses `filelock` for concurrent access. The atomic write goes INSIDE the lock context. After `atomic_write`, apply `os.chmod(path, 0o600)` on non-Windows.
- **config.py** (T021): `toml.dump(config, f)` → `toml.dumps(config)` → `atomic_write(path, content, mkdir=True)`.
- **tracker/config.py** (T022): Uses `ruamel.yaml.YAML.dump()`. Serialize to `io.StringIO` first, then `atomic_write(path, stream.getvalue(), mkdir=True)`.

### Parallel Opportunities
- T021 and T022 are fully independent. T019 and T020 also independent but both in `sync/`.

### Dependencies
- Depends on WP01 (shared `atomic_write()` utility must exist).

### Risks & Mitigations
- `auth.py` permission preservation: `os.replace()` doesn't preserve permissions → apply `os.chmod` after replace.
- `toml.dumps()` availability: Verify the `toml` library supports `dumps()` (it does in `tomli_w` and `toml`).

---

## Work Package WP06: Constitution Git Policy Enforcement (Priority: P2)

**Goal**: Enforce the hybrid Git policy: commit `answers.yaml` + `library/*.md` (shared team knowledge), ignore `references.yaml` (local machine state). Align `.gitignore`, `state_contract.py`, and code.
**Independent Test**: `git check-ignore .kittify/constitution/references.yaml` returns the path; `git check-ignore .kittify/constitution/interview/answers.yaml` returns nothing.
**Prompt**: `tasks/WP06-constitution-git-policy.md`
**Requirement Refs**: FR-017, FR-018, FR-019, NFR-004

### Included Subtasks
- [x] T023 Add `.kittify/constitution/references.yaml` to `.gitignore` (scope tightly — only this specific file, not wildcards)
- [x] T024 Update `src/specify_cli/state_contract.py`: `constitution_references` → `LOCAL_RUNTIME` / `IGNORED`; `constitution_library` → `AUTHORITATIVE` / `TRACKED`; `constitution_interview_answers` → `AUTHORITATIVE` / `TRACKED`
- [x] T025 Remove "Git boundary decision deferred to constitution cleanup sprint" notes from state contract entries
- [x] T026 Add test to `tests/specify_cli/test_state_contract.py` validating new classifications match actual `.gitignore` and Git status

### Implementation Notes
- `.gitignore` entry must be scoped to exactly `.kittify/constitution/references.yaml` — not `references.*` or broader patterns that could catch other files.
- `state_contract.py` currently has these entries around lines 237-311. Update `authority` and `git_class` fields.
- The "deferred" notes appear in the `notes=` field of each StateSurface entry. Replace with a note referencing this feature (e.g., "Policy enforced in 054").
- No migration needed — `.gitignore` changes take effect immediately.

### Parallel Opportunities
- All subtasks are in different files (except T024/T025 both in state_contract.py).

### Dependencies
- None.

### Risks & Mitigations
- `references.yaml` already tracked in Git history: Adding to `.gitignore` stops future tracking but doesn't remove from history. This is intentional (C-005).

---

## Work Package WP07: Acceptance Implementation Deduplication (Priority: P2)

**Goal**: Consolidate acceptance logic into `acceptance.py` as the single canonical implementation. Reduce `acceptance_support.py` to a pure re-export wrapper.
**Independent Test**: Modify a validation rule in `acceptance.py`; confirm both CLI and standalone `tasks_cli.py` paths reflect the change.
**Prompt**: `tasks/WP07-acceptance-deduplication.md`
**Requirement Refs**: FR-020, NFR-002

### Included Subtasks
- [x] T027 Move `ArtifactEncodingError` exception class from `acceptance_support.py` to `acceptance.py`
- [x] T028 Move `normalize_feature_encoding()` from `acceptance_support.py` to `acceptance.py`
- [x] T029 Move `_read_text_strict()` from `acceptance_support.py` to `acceptance.py`
- [x] T030 Align `AcceptanceSummary` — ensure `path_violations` field is consistent (present in canonical, was missing in standalone)
- [x] T031 Rewrite `acceptance_support.py` as pure re-export wrapper (~25 lines: imports + `__all__`)
- [x] T032 Update `tests/specify_cli/test_acceptance_regressions.py` — parity test should now validate re-exports match canonical `__all__`

### Implementation Notes
- `ArtifactEncodingError` is at acceptance_support.py:50-62. Custom exception with UTF-8 diagnostics.
- `normalize_feature_encoding()` is at acceptance_support.py:346-420. Converts Windows-1252/Latin-1 to UTF-8, maps smart quotes/dashes to ASCII.
- `_read_text_strict()` is at acceptance_support.py:305-309. Raises `ArtifactEncodingError` on decode failure.
- `detect_feature_slug()` diverges: standalone lacks `announce_fallback` param. Merge into canonical with `announce_fallback: bool = True` (backward compatible).
- The parity test at test_acceptance_regressions.py:321-355 checks `__all__` subset and signature parity. After dedup, `acceptance_support.__all__` should equal `acceptance.__all__`.

### Parallel Opportunities
- T027, T028, T029 can be done together (moving functions). T030-T032 follow after.

### Dependencies
- None.

### Risks & Mitigations
- Import path breakage: `scripts/tasks/acceptance_support.py` must remain importable with the same names → re-export wrapper ensures this.
- Signature divergence in `detect_feature_slug`: use optional `announce_fallback` param with default → backward compatible.

---

## Work Package WP08: Legacy Bridge Import Hardening (Priority: P3)

**Goal**: Make `legacy_bridge` a hard import in `emit.py` so missing module raises immediately instead of being silently swallowed. Remove stale WP06 transitional comment.
**Independent Test**: Patch `legacy_bridge` import to raise `ImportError`; confirm `emit_status_transition()` raises (not silently succeeds).
**Prompt**: `tasks/WP08-legacy-bridge-hardening.md`
**Requirement Refs**: FR-021, FR-022, NFR-002

### Included Subtasks
- [x] T033 Move `from specify_cli.status.legacy_bridge import update_all_views` to top-level import in `src/specify_cli/status/emit.py`
- [x] T034 Remove the `except ImportError: pass` block and the `# WP06 not yet available` comment
- [x] T035 Add test to `tests/status/test_emit.py` that patches the import to raise `ImportError` and asserts it propagates
- [x] T036 Update `test_legacy_bridge_import_error_handled` test — it currently asserts silent handling; change to assert the error is NOT silently handled

### Implementation Notes
- Current code (emit.py:288-301):
  ```python
  try:
      from specify_cli.status.legacy_bridge import update_all_views
      update_all_views(feature_dir, snapshot)
  except ImportError:
      pass  # WP06 not yet available
  except Exception:
      logger.warning(...)
  ```
- After change: top-level import + only the `except Exception` catch remains around the `update_all_views()` call.
- The broad `except Exception` for bridge UPDATE failures is intentional and stays — canonical state is already persisted at that point (Step 5 before Step 7).

### Parallel Opportunities
- T033/T034 are in the same file (do together). T035/T036 are test changes (do together).

### Dependencies
- None.

### Risks & Mitigations
- If any downstream packaging accidentally excludes `legacy_bridge.py`, the hard import will fail at module load time. This is intentional — it surfaces the regression immediately.

---

## Work Package WP09: Vault Notes Update and Final Validation (Priority: P3)

**Goal**: Update the Obsidian evidence vault with implementation outcomes, new evidence, and test results. Run full test suite and record results.
**Independent Test**: Read vault notes; confirm each cleanup area has an implementation outcome entry.
**Prompt**: `tasks/WP09-vault-notes-update.md`
**Requirement Refs**: FR-023, NFR-002, NFR-003

### Included Subtasks
- [ ] T037 Update `07-2026-03-20-refresh-findings.md` with implementation outcomes for all 7 areas
- [ ] T038 Add new entries to `08-evidence-log-2026-03-20.md` referencing implementation commits and test results
- [ ] T039 Run full test suite (`PWHEADLESS=1 pytest tests/ -q`) and record results
- [ ] T040 Create `09-implementation-outcome-054.md` with summary of what changed, what was deferred, and what was intentionally left

### Implementation Notes
- Vault absolute path: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/research/007-spec-kitty-2x-state-architecture-audit/`
- For each of the 7 cleanup areas, record: what was changed, which commits, test results.
- Mark areas in the "Still unresolved" section that are now resolved.
- Add any new findings discovered during implementation.

### Parallel Opportunities
- T037 and T038 can be drafted in parallel. T039 must run after all code changes.

### Dependencies
- Depends on WP01–WP08 (all implementation must be complete before recording outcomes).

### Risks & Mitigations
- Stale references if implementation commits are amended → record commit hashes after final push.

---

## Dependency & Execution Summary

- **Wave 1 (parallel)**: WP01, WP02, WP06, WP07, WP08
- **Wave 2 (parallel)**: WP03 (after WP02), WP04 (after WP01), WP05 (after WP01)
- **Wave 3**: WP09 (after WP01–WP08)
- **MVP Scope**: WP01 + WP02 + WP03 (fixes the highest-impact bug: mission mismatch)
- **Parallelization**: 5 WPs can start immediately; 3 more as soon as their single dependency completes.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP02 |
| FR-002 | WP02 |
| FR-003 | WP02 |
| FR-004 | WP02 |
| FR-005 | WP03 |
| FR-006 | WP03 |
| FR-007 | WP03 |
| FR-008 | WP01, WP04 |
| FR-009 | WP01, WP04 |
| FR-010 | WP01, WP04 |
| FR-011 | WP01, WP04 |
| FR-012 | WP01, WP05 |
| FR-013 | WP01, WP05 |
| FR-014 | WP01, WP05 |
| FR-015 | WP01, WP05 |
| FR-016 | WP01, WP04 |
| FR-017 | WP06 |
| FR-018 | WP06 |
| FR-019 | WP06 |
| FR-020 | WP07 |
| FR-021 | WP08 |
| FR-022 | WP08 |
| FR-023 | WP09 |
| NFR-001 | WP01, WP04, WP05 |
| NFR-002 | WP07, WP08, WP09 |
| NFR-003 | WP09 |
| NFR-004 | WP06 |
| C-001 | All WPs |
| C-002 | WP02, WP03 |
| C-003 | All WPs |
| C-004 | WP01, WP04, WP05 |
| C-005 | WP06 |
| C-006 | WP09 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create `core/atomic.py` with `atomic_write()` | WP01 | P0 | No |
| T002 | Refactor `feature_metadata.py` to use shared utility | WP01 | P0 | No |
| T003 | Tests for atomic_write | WP01 | P0 | No |
| T004 | Remove `_detect_active_mission()` from manifest | WP02 | P1 | Yes |
| T005 | Update verify_enhanced for feature-level mission | WP02 | P1 | Yes |
| T006 | Update diagnostics for feature-level mission | WP02 | P1 | Yes |
| T007 | Update mission CLI for no-feature-context | WP02 | P1 | Yes |
| T008 | Tests for mission resolution changes | WP02 | P1 | No |
| T009 | Delete `set_active_mission()` | WP03 | P1 | Yes |
| T010 | Delete `get_active_mission_key()` + exports | WP03 | P1 | Yes |
| T011 | Remove `active_mission_marker` from state contract | WP03 | P1 | Yes |
| T012 | Add active-mission to .gitignore | WP03 | P1 | Yes |
| T013 | Update/remove tests for deleted functions | WP03 | P1 | No |
| T014 | Convert runtime_bridge.py to atomic_write | WP04 | P2 | Yes |
| T015 | Convert workspace_context.py to atomic_write | WP04 | P2 | Yes |
| T016 | Convert constitution/context.py to atomic_write | WP04 | P2 | Yes |
| T017 | Convert dashboard/lifecycle.py to atomic_write | WP04 | P2 | Yes |
| T018 | Convert upgrade/metadata.py to atomic_write | WP04 | P2 | Yes |
| T019 | Convert sync/clock.py to shared atomic_write | WP05 | P2 | Yes |
| T020 | Convert sync/auth.py (keep lock + permissions) | WP05 | P2 | Yes |
| T021 | Convert sync/config.py to atomic_write | WP05 | P2 | Yes |
| T022 | Convert tracker/config.py to atomic_write | WP05 | P2 | Yes |
| T023 | Add references.yaml to .gitignore | WP06 | P2 | Yes |
| T024 | Update state_contract constitution entries | WP06 | P2 | No |
| T025 | Remove "deferred" notes from state contract | WP06 | P2 | No |
| T026 | Test new constitution classifications | WP06 | P2 | No |
| T027 | Move ArtifactEncodingError to acceptance.py | WP07 | P2 | Yes |
| T028 | Move normalize_feature_encoding() to acceptance.py | WP07 | P2 | Yes |
| T029 | Move _read_text_strict() to acceptance.py | WP07 | P2 | Yes |
| T030 | Align AcceptanceSummary path_violations | WP07 | P2 | No |
| T031 | Rewrite acceptance_support.py as re-export wrapper | WP07 | P2 | No |
| T032 | Update acceptance regression tests | WP07 | P2 | No |
| T033 | Move legacy_bridge to top-level import | WP08 | P3 | No |
| T034 | Remove ImportError catch + WP06 comment | WP08 | P3 | No |
| T035 | Add test for ImportError propagation | WP08 | P3 | No |
| T036 | Update existing test for new behavior | WP08 | P3 | No |
| T037 | Update refresh findings vault note | WP09 | P3 | Yes |
| T038 | Add evidence log entries | WP09 | P3 | Yes |
| T039 | Run full test suite and record results | WP09 | P3 | No |
| T040 | Create implementation outcome note | WP09 | P3 | No |

<!-- status-model:start -->
## Canonical Status (Generated)
- WP01: approved
- WP02: planned
- WP04: in_progress
- WP05: approved
- WP06: approved
- WP07: in_progress
- WP08: approved
<!-- status-model:end -->
