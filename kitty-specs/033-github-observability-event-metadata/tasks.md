# Work Packages: GitHub Observability Event Metadata

**Inputs**: Design documents from `kitty-specs/033-github-observability-event-metadata/`
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — the spec requires test coverage for event emission metadata.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work package is independently deliverable and testable.

**Prompt Files**: Each work package references a matching prompt file in `tasks/`.

---

## Work Package WP01: GitMetadataResolver + ProjectIdentity Extension (Priority: P0)

**Goal**: Create the new `git_metadata.py` module with `GitMetadata` dataclass, `GitMetadataResolver` service (branch/SHA with 2s TTL cache, repo slug derivation with validation), and extend `ProjectIdentity` with the `repo_slug` override field.
**Independent Test**: Instantiate `GitMetadataResolver`, call `resolve()`, verify `GitMetadata` contains correct branch, SHA, and repo slug from the current git repo.
**Prompt**: `tasks/WP01-git-metadata-resolver.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T001 Create `GitMetadata` dataclass in `src/specify_cli/sync/git_metadata.py`
- [ ] T002 Create `GitMetadataResolver` class with constructor (`repo_root`, `ttl`, `repo_slug_override`)
- [ ] T003 Implement `_resolve_branch_and_sha()` — subprocess calls to `git rev-parse`
- [ ] T004 Implement `resolve()` with 2s TTL cache via `time.monotonic()`
- [ ] T005 Implement repo slug derivation (`_derive_repo_slug_from_remote`, `_validate_repo_slug`, `_resolve_repo_slug`)
- [ ] T006 Add graceful degradation for all failure modes (no git, not a repo, detached HEAD, timeout)
- [ ] T007 Extend `ProjectIdentity` with `repo_slug` field (`to_dict`, `from_dict`, persistence)

### Implementation Notes
- Single new file `src/specify_cli/sync/git_metadata.py` (~200 lines)
- Small modification to `src/specify_cli/sync/project_identity.py` (~20 lines delta)
- Follow existing patterns: `@dataclass`, `subprocess.run()`, `logging.getLogger(__name__)`
- Repo slug parsing: strip `.git`, handle SSH (`@`+`:`) vs HTTPS, extract path after host

### Parallel Opportunities
- T001-T006 (git_metadata.py) and T007 (project_identity.py) touch different files — can be written in parallel

### Dependencies
- None (foundation work package)

### Risks & Mitigations
- SSH URL edge cases (GitLab subgroups): research.md R1 documents parsing algorithm with test matrix
- subprocess hangs: use `timeout=5` on all subprocess calls

---

## Work Package WP02: Emitter Integration (Priority: P0)

**Goal**: Wire `GitMetadataResolver` into `EventEmitter` and inject three new fields (`git_branch`, `head_commit_sha`, `repo_slug`) into every emitted event via the `_emit()` method. Update test fixtures.
**Independent Test**: Emit any event (e.g., `emit_wp_status_changed`), verify the returned event dict contains the three new fields.
**Prompt**: `tasks/WP02-emitter-integration.md`
**Estimated Size**: ~300 lines

### Included Subtasks
- [ ] T008 Add `_git_resolver` field to `EventEmitter` dataclass
- [ ] T009 Add `_get_git_metadata()` lazy-loading method to `EventEmitter`
- [ ] T010 Inject `git_branch`, `head_commit_sha`, `repo_slug` into `_emit()` event dict
- [ ] T011 Update test fixtures in `tests/sync/conftest.py` for git resolver mock

### Implementation Notes
- Modify `src/specify_cli/sync/emitter.py` (~30 lines delta)
- Follow existing pattern: `_identity` field → `_get_identity()` → used in `_emit()`
- New fields go right after `project_slug` in the event dict
- conftest.py gets new `mock_git_resolver` fixture + updated `emitter` fixture

### Parallel Opportunities
- None within this WP (sequential: field → method → injection → fixtures)

### Dependencies
- Depends on WP01 (requires `GitMetadataResolver` and `GitMetadata` classes)

### Risks & Mitigations
- Circular import: use lazy import in `_get_git_metadata()` (same pattern as `_get_identity()`)
- Existing tests break: update emitter fixture with mock resolver so existing tests pass unchanged

---

## Work Package WP03: Unit Tests for GitMetadataResolver (Priority: P1)

**Goal**: Comprehensive unit test coverage for `GitMetadataResolver` — all resolution paths, cache behavior, repo slug parsing, validation, and graceful degradation.
**Independent Test**: `python -m pytest tests/sync/test_git_metadata.py -x -v` passes with 100% branch coverage of `git_metadata.py`.
**Prompt**: `tasks/WP03-unit-tests.md`
**Estimated Size**: ~450 lines

### Included Subtasks
- [ ] T012 [P] Test `GitMetadata` dataclass and `GitMetadataResolver` construction
- [ ] T013 [P] Test branch/SHA resolution from subprocess (normal branch, detached HEAD, worktree)
- [ ] T014 [P] Test TTL cache behavior (cache hit within 2s, cache miss after 2s, cache refresh)
- [ ] T015 [P] Test repo slug derivation (SSH, HTTPS, no `.git` suffix, GitLab subgroups, no remote)
- [ ] T016 [P] Test repo slug validation and config override precedence
- [ ] T017 [P] Test graceful degradation (no git binary, not in repo, subprocess timeout, permission error)

### Implementation Notes
- New file `tests/sync/test_git_metadata.py` (~300 lines)
- Use `unittest.mock.patch` for subprocess calls (don't actually call git in tests)
- Use `time.monotonic()` mocking for TTL cache tests
- Follow existing test patterns from `tests/sync/test_events.py`

### Parallel Opportunities
- All subtasks test independent aspects — can be written in any order

### Dependencies
- Depends on WP01 (requires `git_metadata.py` to exist)
- Can run in parallel with WP02

### Risks & Mitigations
- Subprocess mocking: patch at `specify_cli.sync.git_metadata.subprocess.run` (module-level import)
- time.monotonic mocking: patch at `specify_cli.sync.git_metadata.time.monotonic`

---

## Work Package WP04: Envelope Tests, Integration Tests + Docs (Priority: P1)

**Goal**: Verify new fields appear in emitted events end-to-end, test backward compatibility, update event envelope documentation.
**Independent Test**: `python -m pytest tests/sync/test_events.py tests/sync/test_event_emission.py -x -v` passes; docs contain all 15 envelope fields.
**Prompt**: `tasks/WP04-integration-tests-and-docs.md`
**Estimated Size**: ~400 lines

### Included Subtasks
- [ ] T018 [P] Test new envelope fields present in emitted events (`tests/sync/test_events.py`)
- [ ] T019 [P] Test fields are `null` when git is unavailable (`tests/sync/test_events.py`)
- [ ] T020 Integration tests for git metadata in CLI command emissions (`tests/sync/test_event_emission.py` or `tests/specify_cli/cli/commands/test_event_emission.py`)
- [ ] T021 [P] Test offline replay compatibility with events containing new fields
- [ ] T022 Update event envelope documentation in `docs/` or `architecture/`

### Implementation Notes
- Modify existing test files: `tests/sync/test_events.py` (~50 lines added), `tests/sync/test_event_emission.py` (~40 lines added)
- New tests follow existing `TestEventEnvelope` class patterns
- Documentation: add event envelope reference to `docs/event-envelope.md` (new file, ~80 lines)

### Parallel Opportunities
- T018-T021 (test files) and T022 (docs) touch different files — parallel-safe

### Dependencies
- Depends on WP01 + WP02 (requires resolver module AND emitter integration)

### Risks & Mitigations
- Existing test regressions: run full sync test suite after changes
- Documentation drift: reference contracts/event-envelope.md as canonical source

---

## Dependency & Execution Summary

```
WP01 (GitMetadataResolver + ProjectIdentity)
  │
  ├──→ WP02 (Emitter Integration) ──→ WP04 (Integration Tests + Docs)
  │
  └──→ WP03 (Unit Tests) ─────────→ WP04 (Integration Tests + Docs)
```

- **Sequence**: WP01 → [WP02 ‖ WP03] → WP04
- **Parallelization**: WP02 and WP03 can run simultaneously after WP01 completes
- **MVP Scope**: WP01 + WP02 = functional git metadata in events (no tests or docs)
- **Full Scope**: All 4 WPs = tested, documented feature

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Create GitMetadata dataclass | WP01 | P0 | No |
| T002 | Create GitMetadataResolver class + constructor | WP01 | P0 | No |
| T003 | Implement _resolve_branch_and_sha() | WP01 | P0 | No |
| T004 | Implement resolve() with TTL cache | WP01 | P0 | No |
| T005 | Implement repo slug derivation + validation | WP01 | P0 | No |
| T006 | Add graceful degradation | WP01 | P0 | No |
| T007 | Extend ProjectIdentity with repo_slug | WP01 | P0 | Yes |
| T008 | Add _git_resolver field to EventEmitter | WP02 | P0 | No |
| T009 | Add _get_git_metadata() lazy-loading method | WP02 | P0 | No |
| T010 | Inject three new fields into _emit() | WP02 | P0 | No |
| T011 | Update test fixtures in conftest.py | WP02 | P0 | No |
| T012 | Test GitMetadata + resolver construction | WP03 | P1 | Yes |
| T013 | Test branch/SHA resolution | WP03 | P1 | Yes |
| T014 | Test TTL cache behavior | WP03 | P1 | Yes |
| T015 | Test repo slug derivation | WP03 | P1 | Yes |
| T016 | Test repo slug validation + override | WP03 | P1 | Yes |
| T017 | Test graceful degradation | WP03 | P1 | Yes |
| T018 | Test new envelope fields in events | WP04 | P1 | Yes |
| T019 | Test fields null when git unavailable | WP04 | P1 | Yes |
| T020 | Integration tests for CLI command emissions | WP04 | P1 | No |
| T021 | Test offline replay with new fields | WP04 | P1 | Yes |
| T022 | Update event envelope documentation | WP04 | P1 | Yes |
