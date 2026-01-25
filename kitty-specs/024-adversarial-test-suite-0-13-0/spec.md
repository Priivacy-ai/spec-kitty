# Feature Specification: Adversarial Test Suite for 0.13.0

**Feature Branch**: `024-adversarial-test-suite-0-13-0`
**Created**: 2026-01-25
**Status**: Draft
**Input**: Deep research into spec-kitty changes since 0.12.0 to create adversarial tests for 0.13.0

## Context

The 0.13.0 release introduces significant changes requiring adversarial validation:

1. **Research Deliverables Separation (ADR 7)** - New `deliverables_path` validation
2. **CSV Schema Enforcement (ADR 8)** - Schema validation and migrations
3. **Pre-Review Validation** - Git state detection before WP review
4. **Gitignore Migration** - Removes blocking patterns from .gitignore
5. **Template Propagation** - Updates 12 agent templates

**Critical Background**: The 0.10.8 release shipped a bug affecting 100% of PyPI users through 8+ releases despite 323 passing tests. All tests used `SPEC_KITTY_TEMPLATE_ROOT` bypass, creating a false sense of security. This test suite must include distribution tests that validate real user experience.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Distribution Test Coverage (Priority: P1)

As a PyPI user installing spec-kitty, I need the test suite to validate what I actually experience, not just what developers test locally.

**Why this priority**: The 0.10.8 catastrophe proved that functional tests alone are insufficient. Distribution tests are the ONLY way to catch packaging failures before users do.

**Independent Test**: Install spec-kitty from local wheel build (not editable install), run research workflow without SPEC_KITTY_TEMPLATE_ROOT, verify templates load correctly.

**Acceptance Scenarios**:

1. **Given** a fresh Python environment with spec-kitty installed from wheel, **When** running `spec-kitty init` without SPEC_KITTY_TEMPLATE_ROOT, **Then** templates are found and project initializes successfully
2. **Given** a PyPI-simulated install, **When** creating a research feature, **Then** `deliverables_path` prompt appears and meta.json is correctly populated
3. **Given** a distribution install, **When** running `spec-kitty upgrade`, **Then** all 12 agent templates are updated with CSV schema documentation

---

### User Story 2 - Path Validation Security (Priority: P1)

As a user configuring `deliverables_path`, the system must prevent me from accidentally or maliciously writing files outside the intended location.

**Why this priority**: Path traversal vulnerabilities can cause data loss, security breaches, or repository corruption.

**Independent Test**: Attempt various malicious path inputs and verify all are rejected with clear error messages.

**Acceptance Scenarios**:

1. **Given** a research feature being configured, **When** setting `deliverables_path` to `../../../etc/passwd`, **Then** validation fails with "directory traversal" error
2. **Given** a macOS filesystem, **When** setting `deliverables_path` to `Kitty-Specs/` (case variation), **Then** validation fails (case-insensitive bypass prevention)
3. **Given** a deliverables_path with symlink to kitty-specs/, **When** validation runs, **Then** the symlink is resolved and rejected
4. **Given** empty string or whitespace for deliverables_path, **When** validation runs, **Then** validation fails with clear error

---

### User Story 3 - CSV Schema Attack Resistance (Priority: P1)

As a user working with research CSVs, the system must handle malformed, malicious, or corrupted CSV files gracefully without data loss or security issues.

**Why this priority**: CSV files are created by agents and users; malformed files can cause validation failures, data corruption, or even formula injection attacks when opened in spreadsheets.

**Independent Test**: Create various malformed CSV files and verify schema validation handles them correctly.

**Acceptance Scenarios**:

1. **Given** a CSV with formula injection payload (`=cmd|'/c calc'!A1`), **When** validation runs, **Then** validation completes without executing formulas (and ideally warns about injection)
2. **Given** a CSV with invalid UTF-8 encoding, **When** validation runs, **Then** clear encoding error is reported (not cryptic exception)
3. **Given** a CSV with duplicate column names, **When** validation runs, **Then** duplicate columns are detected and reported
4. **Given** an empty CSV file, **When** schema validation runs, **Then** clear "empty file" error (not schema mismatch)

---

### User Story 4 - Git State Detection Accuracy (Priority: P2)

As a user moving a WP to review, the pre-review validation must accurately detect uncommitted work, merge states, and branch divergence.

**Why this priority**: False positives block legitimate reviews; false negatives allow incomplete work to proceed.

**Independent Test**: Create various git states and verify validation correctly identifies each.

**Acceptance Scenarios**:

1. **Given** a worktree in detached HEAD state with changes, **When** validation runs, **Then** detached HEAD is detected and reported
2. **Given** staged but uncommitted changes, **When** validation runs, **Then** error message clearly indicates files are staged but not committed
3. **Given** a merge in progress (MERGE_HEAD exists), **When** validation runs, **Then** merge state is detected before checking other conditions
4. **Given** main branch has moved forward since WP started, **When** validation runs, **Then** stale base is detected and reported

---

### User Story 5 - Migration Robustness (Priority: P2)

As a user running `spec-kitty upgrade`, migrations must handle interruption, concurrency, and error conditions gracefully.

**Why this priority**: Interrupted or concurrent migrations can leave projects in corrupted states requiring manual recovery.

**Independent Test**: Simulate interruption and concurrent execution scenarios.

**Acceptance Scenarios**:

1. **Given** a migration is running, **When** process is killed mid-write, **Then** metadata file is not corrupted (atomic writes)
2. **Given** two `spec-kitty upgrade` commands running simultaneously, **When** both try to run migrations, **Then** one acquires lock and other waits or fails gracefully
3. **Given** a migration fails partway through, **When** user re-runs upgrade, **Then** failed migration is retried (not skipped as "already applied")
4. **Given** read-only .gitignore file, **When** gitignore migration runs, **Then** clear permission error with fix suggestion

---

### User Story 6 - Multi-Parent Merge Edge Cases (Priority: P2)

As a user implementing a WP with multiple dependencies, the auto-merge must handle conflicts and edge cases correctly.

**Why this priority**: Diamond dependencies are common in complex features; merge failures can block development.

**Independent Test**: Create diamond dependency scenarios with various conflict patterns.

**Acceptance Scenarios**:

1. **Given** WP04 depends on WP02 and WP03 which both modify same file, **When** creating WP04 workspace, **Then** merge conflict is detected and clearly reported
2. **Given** a failed multi-parent merge, **When** checking for cleanup, **Then** temporary merge-base branch is removed
3. **Given** dependencies merged in different orders, **When** creating workspace multiple times, **Then** same git tree hash is produced (determinism)

---

### User Story 7 - Workspace Context Integrity (Priority: P3)

As a user working with worktrees, workspace context files must remain consistent and orphaned contexts must be detectable.

**Why this priority**: Corrupted or orphaned contexts cause confusing errors during workflow operations.

**Independent Test**: Create orphaned and corrupted context scenarios.

**Acceptance Scenarios**:

1. **Given** a worktree is deleted manually, **When** running `spec-kitty context cleanup`, **Then** orphaned context JSON is detected and removable
2. **Given** corrupted context JSON (invalid JSON syntax), **When** reading context, **Then** clear corruption error (not cryptic parse failure)
3. **Given** missing .kittify directory, **When** context operations run, **Then** clear error about missing directory with init suggestion

---

### User Story 8 - Context Validation Bypass Prevention (Priority: P3)

As a system maintainer, the context validation decorators must not be bypassable through environment manipulation or path tricks.

**Why this priority**: Nested worktrees cause git corruption; validation must be robust.

**Independent Test**: Attempt various bypass techniques.

**Acceptance Scenarios**:

1. **Given** SPEC_KITTY_CONTEXT environment variable set to "main", **When** running from inside worktree, **Then** filesystem check overrides env var
2. **Given** a directory named `.worktrees` outside actual worktree structure, **When** running implement command, **Then** false positive is avoided
3. **Given** direct Python function call bypassing CLI, **When** implement function called, **Then** decorator still validates context

---

### User Story 9 - Agent Config Manipulation Resilience (Priority: P3)

As a user with custom agent configuration, migrations and commands must handle corrupt or unusual configs gracefully.

**Why this priority**: Config corruption shouldn't cause migrations to fail silently or operate on wrong agents.

**Independent Test**: Create corrupted and edge-case config scenarios.

**Acceptance Scenarios**:

1. **Given** corrupted YAML in config.yaml, **When** migration runs, **Then** clear YAML parse error (not silent fallback to all 12 agents)
2. **Given** config.yaml with agent key that doesn't exist, **When** running agent commands, **Then** unknown agent key is reported
3. **Given** config.yaml missing entirely, **When** migration runs, **Then** explicit warning about missing config before fallback

---

### Edge Cases

- What happens when deliverables_path contains Unicode characters (e.g., `docs/研究/`)?
- How does system handle CSV files larger than 100MB?
- What happens when git index is locked by another process?
- How does validation handle git submodules?
- What happens when agent directory is a symlink?
- How does system handle extremely long file paths (>255 chars)?
- What happens when meta.json is missing `deliverables_path` for existing research feature?

## Requirements *(mandatory)*

### Functional Requirements

**Distribution Tests (tests/distribution/)**
- **FR-001**: Test suite MUST include distribution tests that run WITHOUT `SPEC_KITTY_TEMPLATE_ROOT` environment variable
- **FR-002**: Distribution tests MUST install spec-kitty from wheel (not editable install)
- **FR-003**: Distribution tests MUST validate template bundling for all mission types

**Path Validation Tests**
- **FR-004**: Tests MUST verify directory traversal attacks are blocked (`../`, symlinks)
- **FR-005**: Tests MUST verify case-sensitivity bypass is blocked on case-insensitive filesystems
- **FR-006**: Tests MUST verify empty/whitespace paths are rejected
- **FR-007**: Tests MUST verify paths outside project root are rejected

**CSV Schema Tests**
- **FR-008**: Tests MUST verify CSV injection payloads don't execute
- **FR-009**: Tests MUST verify invalid encodings produce clear errors
- **FR-010**: Tests MUST verify duplicate columns are detected
- **FR-011**: Tests MUST verify empty files are handled distinctly from schema mismatches

**Git State Tests**
- **FR-012**: Tests MUST verify detached HEAD detection
- **FR-013**: Tests MUST verify merge/rebase state detection
- **FR-014**: Tests MUST verify staged-but-uncommitted detection with clear messages
- **FR-015**: Tests MUST verify main branch divergence detection

**Migration Tests**
- **FR-016**: Tests MUST verify atomic metadata writes (interrupt simulation)
- **FR-017**: Tests MUST verify concurrent migration handling
- **FR-018**: Tests MUST verify permission error handling with actionable messages

**Multi-Parent Merge Tests**
- **FR-019**: Tests MUST verify merge conflict detection and cleanup
- **FR-020**: Tests MUST verify deterministic merge ordering
- **FR-021**: Tests MUST verify orphaned merge-base branch cleanup

**Context and Config Tests**
- **FR-022**: Tests MUST verify orphaned context detection
- **FR-023**: Tests MUST verify context validation cannot be bypassed via env vars
- **FR-024**: Tests MUST verify corrupt config.yaml produces clear errors (not silent fallback)

### Key Entities

- **Test Category**: Grouping of related adversarial tests (distribution, path, CSV, git, migration, merge, context, config)
- **Attack Vector**: Specific malicious or edge-case input being tested
- **Expected Behavior**: The correct system response to the attack vector

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of distribution tests pass on clean Python environment without SPEC_KITTY_TEMPLATE_ROOT
- **SC-002**: All identified path traversal vectors produce explicit rejection (no silent failures)
- **SC-003**: CSV validation handles 100% of tested malformed inputs without exceptions bubbling to user
- **SC-004**: Git state detection has zero false negatives (no incomplete work reaches review)
- **SC-005**: Migration interruption at any point leaves system in recoverable state
- **SC-006**: Test suite catches at least 3 previously unknown bugs in 0.13.0 code
- **SC-007**: Test suite runs in under 5 minutes on CI

## Assumptions

- Tests will be written using pytest with existing test infrastructure
- Distribution tests may require separate CI job or test marker for isolation
- Some tests (like concurrent migration) may require multiprocessing
- Symlink tests may behave differently on Windows vs Unix
