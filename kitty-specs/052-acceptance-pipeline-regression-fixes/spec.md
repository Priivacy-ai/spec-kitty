# Feature Specification: Acceptance Pipeline Regression Fixes

**Feature Branch**: `052-acceptance-pipeline-regression-fixes`
**Created**: 2026-03-19
**Status**: Draft
**Input**: Bug report with 4 verified regressions (P0–P2) in the acceptance/verification pipeline

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accept a clean feature without self-inflicted dirty repo (Priority: P1)

A developer completes all work packages for a feature and runs `spec-kitty accept`. The acceptance pipeline verifies that the repo is clean, all WPs are in the `done` lane, and the feature is ready. The acceptance succeeds and the commit SHA is recorded.

**Why this priority**: This is the core acceptance flow. If `materialize()` rewrites `status.json` with a fresh `materialized_at` timestamp before the git-cleanliness check, every clean feature fails acceptance — a total blocker.

**Independent Test**: Run `spec-kitty accept` on a feature where all WPs are done and the repo is clean. Acceptance must succeed without reporting `status.json` as modified.

**Acceptance Scenarios**:

1. **Given** a feature with all WPs in `done` lane and a clean git working tree, **When** `collect_feature_summary()` is called, **Then** the repo remains clean (no `status.json` modification appears in `git status`) and `summary.ok` is `True`.
2. **Given** a feature with all WPs in `done` lane and a clean git working tree, **When** `collect_feature_summary()` is called twice in succession, **Then** the second call also reports a clean repo.
3. **Given** a feature with genuinely uncommitted changes, **When** `collect_feature_summary()` is called, **Then** `summary.ok` is `False` and the dirty files are reported correctly.

---

### User Story 2 - Acceptance commit SHA persisted to meta.json (Priority: P1)

After acceptance succeeds and a commit is created, the resulting commit SHA is recorded in `meta.json` under both `accept_commit` and in the `acceptance_history` entry. External tools and future commands can look up when and how a feature was accepted.

**Why this priority**: Without the SHA in `meta.json`, the acceptance record is ephemeral — it exists only in the return object of one function call, then disappears.

**Independent Test**: Run `spec-kitty accept` to completion, then inspect `meta.json`. The `accept_commit` field and the latest `acceptance_history` entry must contain the real commit SHA.

**Acceptance Scenarios**:

1. **Given** a successful acceptance that creates a git commit, **When** the commit completes, **Then** `meta.json` is updated with the commit SHA in `accept_commit` and in `acceptance_history[-1].accept_commit` before the function returns.
2. **Given** a successful acceptance, **When** `meta.json` is read after the function returns, **Then** the stored SHA matches the actual git commit.

---

### User Story 3 - Standalone task scripts work from repo checkout (Priority: P2)

A developer (or CI job) invokes `tasks_cli.py` or `acceptance_support.py` directly via `python3 path/to/tasks_cli.py --help` from a repo checkout, without having `spec-kitty` pip-installed. The script starts and runs correctly.

**Why this priority**: These scripts carry an implicit contract (shebang, local `sys.path` bootstrap, "no external dependencies" docstring) that they work standalone from a checkout.

**Independent Test**: From a clean checkout with no pip install, run `python3 src/specify_cli/scripts/tasks/tasks_cli.py --help`. It must print help text without `ModuleNotFoundError`.

**Acceptance Scenarios**:

1. **Given** a repo checkout without `spec-kitty` pip-installed, **When** `python3 tasks_cli.py --help` is invoked, **Then** the script starts and prints help text.
2. **Given** a repo checkout without `spec-kitty` pip-installed, **When** `acceptance_support.py` functions are imported by `tasks_cli.py`, **Then** all `specify_cli.*` imports resolve via the `sys.path` bootstrap.

---

### User Story 4 - Malformed event log produces structured CLI error (Priority: P3)

A feature's `status.events.jsonl` contains invalid JSON (corruption, manual edit, merge artifact). When a user runs `spec-kitty accept`, the CLI reports the problem as a structured error message — not an unhandled exception traceback.

**Why this priority**: While malformed event logs are uncommon, an unhandled `StoreError` crash is a poor user experience and makes diagnosis harder.

**Independent Test**: Write invalid JSON into a feature's `status.events.jsonl`, then run `spec-kitty accept`. The CLI must display a user-friendly error and exit cleanly.

**Acceptance Scenarios**:

1. **Given** a feature with a malformed `status.events.jsonl`, **When** `spec-kitty accept` is run, **Then** a structured error message is displayed (e.g., "Status event log is corrupted: ...") and the command exits with a non-zero code.
2. **Given** a feature with a malformed `status.events.jsonl`, **When** `collect_feature_summary()` is called, **Then** it raises `AcceptanceError` (not `StoreError`).

---

### Edge Cases

- What happens when `status.json` does not yet exist (first materialization)?
- What happens when `meta.json` is read-only or missing?
- What happens when `status.events.jsonl` is empty (zero bytes)?
- What happens when `status.events.jsonl` has a mix of valid and invalid lines?
- What happens when the git commit during acceptance fails (e.g., hook rejection)?
- What happens when `tasks_cli.py` is invoked from a location outside the repo tree?

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Defer materialization until after cleanliness check | As a developer, I want `collect_feature_summary()` to check git cleanliness before calling `materialize()`, so that the check does not produce a false dirty state. | Critical | Open |
| FR-002 | Persist acceptance commit SHA to meta.json | As a developer, I want `perform_acceptance()` to write the commit SHA back to `meta.json` after creating the acceptance commit, so that the acceptance record is durable. | High | Open |
| FR-003 | Bootstrap sys.path in standalone scripts | As a developer, I want standalone scripts (`tasks_cli.py`, `acceptance_support.py`) to add the repo `src/` root to `sys.path` before importing `specify_cli.*`, so that direct invocation works from a checkout. | High | Open |
| FR-004 | Catch StoreError in acceptance CLI | As a developer, I want `accept.py` (or `collect_feature_summary()`) to catch `StoreError` from the event store and convert it to a user-facing `AcceptanceError`, so that malformed event logs produce structured CLI output. | Medium | Open |
| FR-005 | Fix standalone acceptance_support.py copy | As a developer, I want the same fixes (FR-001, FR-002, FR-003, FR-004) applied to the standalone copy of `acceptance_support.py` shipped in `scripts/tasks/`, so both copies behave identically. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No new dependencies | Fixes must not introduce any new external dependencies beyond what is already in the codebase. | Maintainability | High | Open |
| NFR-002 | Test coverage for regressions | Each of the 4 bugs must have at least one dedicated test that would have caught the regression. | Reliability | High | Open |
| NFR-003 | Standalone entrypoint test | At least one test must verify that the standalone script entrypoint can import all its dependencies without a pip install. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Dual-copy consistency | Both `src/specify_cli/scripts/tasks/acceptance_support.py` and `scripts/tasks/acceptance_support.py` must receive identical fixes. | Technical | High | Open |
| C-002 | No vendoring | The standalone script fix must use `sys.path` manipulation, not vendoring or copying `specify_cli` modules into the scripts directory. | Technical | High | Open |
| C-003 | Preserve existing test suite | All existing tests must continue to pass. No test modifications except adding new tests for the regressions. | Technical | High | Open |
| C-004 | Target branch 2.x | All work targets the `2.x` branch. | Process | High | Open |

### Key Entities

- **`collect_feature_summary()`**: Gathers acceptance prerequisites (git cleanliness, WP lane states, event log). Located in `src/specify_cli/acceptance.py` and `src/specify_cli/scripts/tasks/acceptance_support.py`.
- **`perform_acceptance()`**: Orchestrates the acceptance workflow — summary collection, commit creation, metadata recording. Same two locations.
- **`materialize()`**: Status reducer that replays events into `status.json`. Located in `src/specify_cli/status/reducer.py`. Rewrites `status.json` with fresh `materialized_at` on every call.
- **`StoreError`**: Exception raised by `src/specify_cli/status/store.py` on JSONL parse failures.
- **Standalone scripts**: `tasks_cli.py` and `acceptance_support.py` in `src/specify_cli/scripts/tasks/` — shipped as directly-executable entrypoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean feature can be accepted on first attempt — `collect_feature_summary()` does not modify `status.json` before checking git cleanliness.
- **SC-002**: After acceptance, `meta.json` contains the real commit SHA in both `accept_commit` and `acceptance_history[-1].accept_commit`.
- **SC-003**: `python3 src/specify_cli/scripts/tasks/tasks_cli.py --help` succeeds from a repo checkout without pip install.
- **SC-004**: A malformed `status.events.jsonl` produces a structured CLI error message, not an unhandled traceback.
- **SC-005**: Each regression has at least one new test that fails before the fix and passes after.
