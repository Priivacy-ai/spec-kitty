# Feature Specification: Constitution Packaging Safety and Redesign

**Feature Branch**: `011-constitution-packaging-safety-and-redesign`
**Created**: 2026-01-12
**Status**: Draft
**Input**: User description: Emergency 0.10.x release to clean up constitution handling before merging the 010 worktree feature. Four goals: (1) Segregate spec-kitty code from operational artifacts, (2) Redesign constitution as optional interactive command, (3) Fix Windows dashboard empty response issue (#71), (4) Fix upgrade migration failures (#70).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe Dogfooding (Priority: P1)

A spec-kitty contributor wants to use spec-kitty commands (specify, plan, constitution) to develop spec-kitty itself, without risk of accidentally packaging their development artifacts into the public release.

**Why this priority**: This is a critical safety issue. Currently, any filled-in constitution during development gets packaged and distributed to all users, overwriting their project-specific values.

**Independent Test**: Can be tested by: (1) Running `/spec-kitty.constitution` in the spec-kitty repo to fill in a constitution, (2) Running `python -m build`, (3) Extracting the wheel and verifying that no filled-in constitution.md exists in the package, only template versions.

**Acceptance Scenarios**:

1. **Given** spec-kitty repo with filled `.kittify/memory/constitution.md`, **When** developer runs `python -m build`, **Then** the resulting wheel contains only template versions under `specify_cli/templates/`, not the filled runtime version
2. **Given** spec-kitty repo, **When** developer runs `/spec-kitty.constitution` and fills in principles, **Then** the filled constitution is stored outside the `src/` tree and never gets packaged
3. **Given** user installs spec-kitty from PyPI, **When** they run `spec-kitty init`, **Then** they receive a blank/placeholder constitution template, not spec-kitty's internal constitution

---

### User Story 2 - Optional Constitution Setup (Priority: P1)

A user initializing a new project wants to decide whether to establish a constitution, and if so, whether it should be minimal or comprehensive, without being blocked from using spec-kitty commands.

**Why this priority**: Constitution should never be a requirement. Solo developers and small teams often don't need formal constitutions.

**Independent Test**: Can be tested by running `spec-kitty init`, declining constitution setup, then successfully running `/spec-kitty.specify`, `/spec-kitty.plan`, and `/spec-kitty.implement` without any constitution-related errors.

**Acceptance Scenarios**:

1. **Given** new project, **When** user runs `/spec-kitty.constitution` and chooses "No, skip it", **Then** command exits successfully and all other spec-kitty commands work without constitution
2. **Given** new project, **When** user runs `/spec-kitty.constitution` and chooses "Yes, minimal", **Then** agent asks 3-5 core questions and generates 1-page constitution
3. **Given** new project, **When** user runs `/spec-kitty.constitution` and chooses "Yes, comprehensive", **Then** agent asks 8-12 questions across technical/tribal knowledge categories and generates 2-3 page constitution
4. **Given** project without constitution, **When** user runs `/spec-kitty.plan`, **Then** Constitution Check section is skipped gracefully

---

### User Story 3 - Dashboard Works on Windows (Priority: P2)

A Windows user wants to use the spec-kitty dashboard to view their kanban board in a web browser.

**Why this priority**: Dashboard is a valuable feature but currently broken on Windows. CLI commands still work, so it's not blocking, but reduces user experience.

**Independent Test**: Can be tested on Windows by running `spec-kitty dashboard`, opening the browser to the dashboard URL, and verifying the kanban board loads without ERR_EMPTY_RESPONSE.

**Acceptance Scenarios**:

1. **Given** Windows 10/11 system, **When** user runs `spec-kitty dashboard`, **Then** server starts and browser shows kanban board
2. **Given** dashboard running on Windows, **When** user navigates to `http://127.0.0.1:9237`, **Then** HTTP response contains HTML content (not empty)
3. **Given** dashboard server starting, **When** initialization encounters Windows-specific signal handling, **Then** server uses platform-appropriate signal methods

---

### User Story 4 - Smooth Upgrades (Priority: P2)

A user running spec-kitty 0.6.4 wants to upgrade to 0.10.12 without manual intervention or migration failures.

**Why this priority**: Users should be able to upgrade seamlessly. Currently, migrations fail partway through, requiring manual file manipulation and deep knowledge of the migration system.

**Independent Test**: Can be tested by: (1) Creating a fresh 0.6.4 project, (2) Running `pip install spec-kitty-cli==0.10.12`, (3) Running `spec-kitty upgrade`, (4) Verifying all migrations succeed without errors.

**Acceptance Scenarios**:

1. **Given** project on 0.6.4 with bash scripts, **When** user upgrades to 0.10.12, **Then** migration 0.7.3 gracefully handles missing template scripts and defers to 0.10.0 cleanup
2. **Given** project upgrading to 0.10.6, **When** migration needs updated mission templates, **Then** templates are copied from package before validation, not just checked
3. **Given** project with legacy .toml command files, **When** upgrade completes, **Then** .toml files are removed and only .md versions remain
4. **Given** upgrade path with overlapping migrations, **When** earlier migration fails, **Then** later migration detects the cleanup is already done and skips gracefully

---

### Edge Cases

- What happens when user has customized constitution and upgrades? (Must preserve their customizations)
- How does system handle worktree constitution sharing after packaging changes? (Worktrees should still share `.kittify/memory/` safely)
- What if dashboard process is killed mid-startup on Windows? (Should cleanup PID files and allow restart)
- What if migration 0.7.3 runs on a system that already deleted bash scripts manually? (Should detect and skip)
- What if user runs `/spec-kitty.constitution` multiple times? (Should offer to update existing constitution, not error)

## Requirements *(mandatory)*

### Functional Requirements

**Goal #1: Segregate Code from Artifacts**

- **FR-001**: Package build MUST only include template files from `src/specify_cli/templates/`, never runtime artifacts from `.kittify/memory/`
- **FR-002**: Constitution template MUST live in `src/specify_cli/templates/memory/` or use existing `src/specify_cli/missions/software-dev/constitution/principles.md`
- **FR-003**: `spec-kitty init` MUST copy constitution template to user's `.kittify/memory/constitution.md` as blank/placeholder
- **FR-004**: `pyproject.toml` force-include MUST NOT package `.kittify/memory/` (remove lines 88, 96)
- **FR-005**: Template manager (`src/specify_cli/template/manager.py`) MUST copy constitution template from package during init
- **FR-006**: Spec-kitty repo itself CAN have `.kittify/memory/constitution.md` with real values for dogfooding without packaging risk

**Goal #2: Redesign Constitution Command**

- **FR-007**: `/spec-kitty.constitution` command MUST ask first question: "Do you want to establish a project constitution?" with options: (A) No, skip it, (B) Yes, minimal, (C) Yes, comprehensive
- **FR-008**: If user chooses "No", command MUST exit successfully or create minimal placeholder without error
- **FR-009**: If user chooses "Yes, minimal", command MUST ask 3-5 core questions: languages/frameworks, testing requirements, PR rejection criteria
- **FR-010**: If user chooses "Yes, comprehensive", command MUST ask 8-12 questions across categories: Technical Foundation, Code Quality, Tribal Knowledge, Workflow, Project Principles
- **FR-011**: Constitution command MUST use one-question-at-a-time interactive discovery (like `/spec-kitty.specify` and `/spec-kitty.plan`)
- **FR-012**: Constitution command MUST present "Project Principles Summary" before writing constitution for user confirmation
- **FR-013**: `/spec-kitty.plan` MUST skip Constitution Check section gracefully if no constitution exists
- **FR-014**: Generated constitution MUST be lean by default (1 page for minimal, 2-3 pages maximum for comprehensive)
- **FR-015**: Constitution questions MUST capture both technical standards AND tribal knowledge (team conventions, lessons learned)
- **FR-016**: Constitution command template (`constitution.md`) MUST be updated to use discovery workflow instead of placeholder-filling approach

**Goal #3: Fix Windows Dashboard (#71)**

- **FR-017**: Dashboard server MUST serve HTTP content on Windows 10/11 (not empty responses)
- **FR-018**: Dashboard initialization MUST use platform-appropriate signal handling (avoid `signal.SIGKILL` on Windows)
- **FR-019**: Dashboard server MUST handle Windows-specific process management (no POSIX-only signals)
- **FR-020**: Dashboard MUST log clear error messages if platform-specific initialization fails

**Goal #4: Fix Upgrade Migrations (#70)**

- **FR-021**: Migration `0.7.3_update_scripts` MUST gracefully handle case where bash scripts no longer exist in package (skip or defer to 0.10.0)
- **FR-022**: Migration `0.10.6_workflow_simplification` MUST copy updated mission templates from package BEFORE checking `can_apply()`
- **FR-023**: Migration `0.10.2_update_slash_commands` MUST remove legacy .toml files when updating to .md format
- **FR-024**: Migration `0.10.0_python_only` MUST remove `.kittify/scripts/tasks/` directory (obsolete Python task helpers)
- **FR-025**: Migrations depending on removed files MUST either skip gracefully or perform equivalent cleanup action
- **FR-026**: Upgrade command MUST provide clear error messages with remediation steps if migration fails
- **FR-027**: Migrations MUST be idempotent (safe to run multiple times)

### Key Entities

- **Template File**: Source file in `src/specify_cli/templates/` that gets packaged and distributed to users; contains placeholders or starter content
- **Runtime Artifact**: User-specific file in `.kittify/memory/` created during spec-kitty usage; contains project-specific data filled in by user/agent
- **Constitution**: Document capturing project's technical standards, code quality practices, tribal knowledge, and governance rules; optional for all users
- **Migration**: Version upgrade script that transforms project structure from old version to new version; must handle cases where expected files are missing
- **Package Manifest** (`pyproject.toml`): Configuration defining what files get included in wheel/sdist distributions; currently incorrectly includes runtime artifacts

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Building spec-kitty package from any branch produces a wheel that contains zero filled-in constitution files (verify with `unzip -l dist/*.whl | grep constitution`)
- **SC-002**: Users running `spec-kitty init` receive constitution template with placeholders, not spec-kitty's internal constitution (verify by installing from test PyPI and checking file contents)
- **SC-003**: 100% of spec-kitty commands (specify, plan, tasks, implement) work on projects without constitutions (verify by running full workflow without `/spec-kitty.constitution`)
- **SC-004**: Dashboard serves HTML content on Windows (verify by curl returning Content-Length > 0 on Windows 10/11)
- **SC-005**: Upgrade from 0.6.4 to 0.10.12 completes without manual intervention (verify in clean VM with 0.6.4 project)
- **SC-006**: Minimal constitution generation completes in under 2 minutes with 3-5 questions
- **SC-007**: Comprehensive constitution generation completes in under 5 minutes with 8-12 questions
- **SC-008**: All migrations from 0.6.x to 0.10.12 are idempotent (running twice produces same result as running once)

### Risk Mitigation

- **Packaging risk eliminated**: Developers can safely dogfood spec-kitty without fear of releasing wrong files
- **Windows user experience restored**: Dashboard feature works on Windows platform
- **Upgrade confidence restored**: Users can upgrade without fear of manual cleanup or broken migrations
- **Constitution friction removed**: Teams can use spec-kitty without being forced to create constitutions they don't need
