# Feature Specification: Doctrine Stack Init and Profile Integration

**Feature Branch**: `057-doctrine-stack-init-and-profile-integration`
**Created**: 2026-03-19
**Status**: Draft
**Input**: User description: "Doctrine Stack Configuration & Agent Profile Integration"

## Clarifications

### Session 2026-03-22

- Q: When a WP has an explicitly set `agent_profile` that can't be resolved, should the workflow fail or warn and continue? → A: Configurable — fail with a blocking error by default (explicit misconfiguration), suppressible via `--allow-missing-profile` flag which degrades to warn-and-continue.
- Q: When `spec-kitty init` is interrupted mid-interview, should the flow be resumable or produce no partial state? → A: Resumable — init checkpoints progress. On next invocation the user is offered the choice to resume the previous session or start over.

### Session 2026-03-20

- Q: When a WP has no `agent_profile` and `generic-agent` hasn't been promoted to `shipped/` yet, what should the workflow do? → A: Skip profile injection with a warning ("Profile not found, proceeding without specialist identity").
- Q: When the user selects "configure manually" during init, which interview profile should it default to? → A: Ask the user which depth they prefer (minimal vs comprehensive), explaining that the comprehensive interview captures their preferred way of working and the system suggests/selects the most appropriate doctrine entries. The aim is smooth onboarding without removing control. The user should be informed about what is happening and how they can customize their constitution later.
- Q: When `/spec-kitty.tasks` generates WP files, should it auto-populate `agent_profile`? → A: Mission templates define the desired agent role/specialization (e.g., `implementer`, `reviewer`, `writer`). The system determines the most appropriate concrete profile based on task content. The user confirms during finalize. Future iterations may make specialist selection more deterministic.
- Q: When a child profile inherits list-type fields (e.g., `directives`, `canonical_verbs`) from its parent, should the child's values replace or merge with the parent's? → A: Merge (union, no duplicates) by default. The `specializes-from` relationship should support an `excluding` option to selectively ignore specific inherited fields or values from the parent profile.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accept Default Doctrine Stack During Init (Priority: P1)

A user runs `spec-kitty init` on a new project. They are offered a choice: accept the predefined doctrine defaults or configure the doctrine stack through an exhaustive interview. They choose to accept defaults. The init flow completes with a fully configured doctrine stack — constitution, directives, and agent profiles — without requiring the user to run a separate `spec-kitty constitution interview` command afterwards.

**Why this priority**: This is the primary onboarding path. Most users want sensible defaults without friction. Today, the constitution interview is a disconnected step users must discover on their own.

**Independent Test**: Run `spec-kitty init` in interactive mode on a fresh project, select "accept defaults" when prompted. Verify that `.kittify/constitution/` is populated with a generated constitution, governance config, and interview answers.

**Acceptance Scenarios**:

1. **Given** a fresh project with no `.kittify/` directory, **When** user runs `spec-kitty init` and selects "accept defaults" at the doctrine stack prompt, **Then** the constitution is generated with predefined defaults and `.kittify/constitution/constitution.md` exists.
2. **Given** a fresh project, **When** user runs `spec-kitty init --non-interactive`, **Then** doctrine defaults are applied automatically without prompting.
3. **Given** a project that already has a constitution, **When** user runs `spec-kitty init`, **Then** the doctrine stack step is skipped with a message indicating an existing constitution was detected.

---

### User Story 2 - Configure Doctrine Stack via Interview During Init (Priority: P1)

A user runs `spec-kitty init` and chooses to configure the doctrine stack explicitly. They are guided through the exhaustive constitution interview (paradigm selection, directive selection, tool configuration) as part of the init flow, rather than having to discover and run `spec-kitty constitution interview` separately.

**Why this priority**: Power users and teams with specific governance requirements need this path. Without it, the interview is disconnected from init and easily missed.

**Independent Test**: Run `spec-kitty init` in interactive mode, select "configure manually" at the doctrine stack prompt. Verify the constitution interview runs inline and produces `.kittify/constitution/interview/answers.yaml` and a generated constitution.

**Acceptance Scenarios**:

1. **Given** a fresh project, **When** user runs `spec-kitty init` and selects "configure manually", **Then** the user is asked which interview depth they prefer: minimal (quick setup) or comprehensive (captures their preferred way of working, system suggests appropriate doctrine entries).
2. **Given** the user selects an interview depth, **When** the interview begins, **Then** the user is informed about what the interview does, how it shapes their constitution, and how they can customize it later.
3. **Given** the user completes the interview within init, **When** init finishes, **Then** constitution artifacts are generated from the interview answers.
4. **Given** a user whose previous init was interrupted mid-interview, **When** they run `spec-kitty init` again, **Then** they are offered the choice to resume the previous session or start over; selecting "start over" discards the checkpoint and begins fresh.

---

### User Story 3 - Agent Identity Loaded Automatically During WP Implementation (Priority: P1)

A developer starts implementing a work package that specifies `agent_profile: implementer` in its frontmatter. The implement workflow automatically resolves the profile and injects the identity fragment into the prompt — the agent operates under that profile's identity, specialization boundaries, and directive references without any manual setup.

**Why this priority**: This is the core integration that makes profiles actionable. Without it, profiles are metadata that agents ignore.

**Independent Test**: Create a WP with `agent_profile: implementer` in frontmatter, run the implement workflow, and verify the rendered prompt contains the implementer's initialization declaration, specialization, and directive references.

**Acceptance Scenarios**:

1. **Given** a WP with `agent_profile: implementer` in frontmatter, **When** `spec-kitty agent workflow implement WP01` runs, **Then** the implement prompt includes the implementer profile's identity fragment (name, purpose, specialization, directives, initialization declaration).
2. **Given** a WP with `agent_profile: architect` in frontmatter, **When** the implement workflow runs, **Then** the architect profile is loaded instead of the implementer profile.
3. **Given** a WP with no `agent_profile` field in frontmatter, **When** the implement workflow runs, **Then** the `generic-agent` profile is loaded as the default. If `generic-agent` is not available (not yet promoted), the workflow warns "Profile not found, proceeding without specialist identity" and continues without profile injection.
4. **Given** a WP with `agent_profile: nonexistent-profile`, **When** the implement workflow runs without `--allow-missing-profile`, **Then** the workflow fails with a blocking error identifying the unresolvable profile. **When** run with `--allow-missing-profile`, the workflow warns "Profile not found, proceeding without specialist identity" and continues.

---

### User Story 4 - Start Ad-Hoc Session via Profile-Context Command (Priority: P2)

A user invokes `/spec-kitty.profile-context architect` to start an advisory session. The command template is deployed to all configured agents and the session loads the architect profile's identity, specialization, and directive references.

**Why this priority**: Enables the architect, implementer, and reviewer profiles to be used interactively for advisory sessions. Depends on the profile-context template being deployed via upgrade migration.

**Independent Test**: Run `spec-kitty upgrade` on a project, verify `spec-kitty.profile-context.md` exists in the configured agent directories. Invoke the slash command and verify profile data is loaded from the CLI.

**Acceptance Scenarios**:

1. **Given** a project with `spec-kitty upgrade` applied, **When** user checks agent command directories, **Then** `spec-kitty.profile-context.md` exists for all configured agents.
2. **Given** the profile-context command is available, **When** user invokes `/spec-kitty.profile-context reviewer`, **Then** the agent loads the reviewer profile via `spec-kitty agent profile show reviewer` and adopts the profile identity.

---

### User Story 5 - Ship Generic Agent Profile (Priority: P2)

The `generic-agent` profile ships as a proposed doctrine artifact with a single directive reference to DIRECTIVE_028 (Efficient Local Tooling). It serves as the default for WPs that do not specify an explicit profile. The profile is proposed via `_proposed/` and only promoted to `shipped/` after explicit HIC curation approval.

**Why this priority**: Required as the default fallback for User Story 3. Must exist before WP profile loading can default gracefully.

**Independent Test**: Verify `generic-agent.agent.yaml` exists in `_proposed/` with valid schema, a single directive reference to DIRECTIVE_028, and a broad specialization. Verify it is NOT in `shipped/` without HIC approval.

**Acceptance Scenarios**:

1. **Given** the feature is implemented, **When** checking `src/doctrine/agent_profiles/_proposed/`, **Then** `generic-agent.agent.yaml` exists with valid schema.
2. **Given** the generic-agent profile, **When** inspecting its directive references, **Then** exactly one directive is referenced (DIRECTIVE_028 — Efficient Local Tooling).
3. **Given** the generic-agent profile, **When** checking `src/doctrine/agent_profiles/shipped/`, **Then** `generic-agent.agent.yaml` does NOT exist there (requires HIC curation to promote).

---

### User Story 6 - Profile Inheritance Resolution (Priority: P1)

The `AgentProfileRepository` supports profile inheritance via a `specializes-from` field in profile YAML. Child profiles declare only their delta — unspecified fields inherit from the parent profile. This enables specialized profiles (e.g., a future Python specialist) to extend role profiles (e.g., `implementer`) without duplicating their full definition.

**Why this priority**: Inheritance resolution is a prerequisite for the `generic-agent` to serve as a meaningful base profile. Role profiles should be composable, and the inheritance mechanism enables project-level specializations without forking shipped profiles.

**Independent Test**: Create a child profile that `specializes-from: implementer`, verify it inherits the parent's unspecified fields (purpose, mode_defaults, collaboration) while overriding its declared delta (specialization, directives).

**Acceptance Scenarios**:

1. **Given** a child profile with `specializes-from: implementer`, **When** the profile is resolved by `AgentProfileRepository`, **Then** unspecified fields are inherited from the `implementer` profile.
2. **Given** a child profile that overrides `specialization.primary_focus`, **When** resolved, **Then** the child's primary focus is used while other inherited fields remain intact.
3. **Given** a child profile that declares additional `directives`, **When** resolved, **Then** the child's directives are merged with the parent's (union, no duplicates).
4. **Given** a child profile with `excluding: [directives: [DIRECTIVE_010]]`, **When** resolved, **Then** the parent's DIRECTIVE_010 is excluded from the merged result.
5. **Given** a multi-level chain (grandchild → child → parent), **When** resolved, **Then** inheritance cascades correctly through each level, with merge and exclusion applied at each step.
6. **Given** a profile that `specializes-from` a non-existent parent, **When** resolved, **Then** the repository raises a clear error identifying the missing parent.

---

### User Story 7 - Rename `--feature` to `--mission` (Pre-work, Priority: P2)

As a Boy Scout pre-work item, CLI commands that currently accept `--feature` gain `--mission` as the canonical flag. `--feature` is preserved as a backward-compatible alias that emits a deprecation warning. This prevents 056's new init and workflow code from introducing fresh `--feature` references that would need renaming later.

**Why this priority**: Terminology drift between "feature" and "mission" causes user confusion (see issue #241). Addressing it as pre-work ensures 056's implementation uses the canonical terminology from the start.

**Independent Test**: Run a command with `--mission`, verify it works. Run the same command with `--feature`, verify it works but emits a deprecation warning. Run with both flags providing conflicting values, verify a clear error.

**Acceptance Scenarios**:

1. **Given** a command that currently accepts `--feature`, **When** the user passes `--mission` instead, **Then** the command works identically.
2. **Given** a command invoked with `--feature`, **When** it executes, **Then** a non-fatal deprecation warning is emitted suggesting `--mission`.
3. **Given** a command invoked with both `--mission X` and `--feature Y` where X != Y, **When** it executes, **Then** a clear error is raised about conflicting values.
4. **Given** existing automation that uses `--feature`, **When** upgraded to this version, **Then** all existing scripts continue to work without modification.

---

### Edge Cases

- What happens when `spec-kitty init` is interrupted mid-interview? Init checkpoints its progress. On the next invocation the user is prompted to choose between resuming the previous interrupted session or starting over. Restarting discards the checkpoint.
- What happens when a project upgrades from a version without profile-context? The upgrade migration deploys the template without affecting existing commands.
- What happens when a WP specifies an `agent_profile` that cannot be resolved? By default, the workflow fails with a blocking error. Pass `--allow-missing-profile` to degrade to a non-fatal warning and continue without injection.
- What happens when `generic-agent` is not yet promoted to shipped? The workflow skips profile injection with a warning ("Profile not found, proceeding without specialist identity") and continues normally.
- What happens when a profile inheritance chain has a cycle (A → B → A)? The repository should detect the cycle and raise a clear error, not recurse infinitely.
- What happens when both `--feature` and `--mission` are provided with the same value? The command should accept it silently (no warning, no error).
- What happens when a child profile's parent is in `_proposed/` but the child is in `shipped/`? The repository should resolve from both directories; the child inherits regardless of the parent's curation status.
- What happens when a child profile excludes a value that the parent doesn't have? The exclusion is silently ignored (no error).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Init doctrine choice | As a user, I want `spec-kitty init` to offer "accept defaults" vs "configure manually" for the doctrine stack so that I don't have to discover the constitution interview separately. | High | Open |
| FR-002 | Init accept defaults | As a user, I want the "accept defaults" option to generate a complete constitution from predefined defaults without additional prompts. | High | Open |
| FR-003 | Init inline interview | As a user, I want the "configure manually" option to run the constitution interview inline within the init flow. | High | Open |
| FR-004 | Init skip existing | As a user, I want init to skip the doctrine stack step if a constitution already exists. | Medium | Open |
| FR-005 | Init non-interactive defaults | As a user, I want `spec-kitty init --non-interactive` to apply doctrine defaults automatically. | Medium | Open |
| FR-006 | WP profile field | As a workflow system, I want WP frontmatter to support an `agent_profile` field that identifies which profile the implementing agent should operate under. | High | Open |
| FR-007 | Workflow profile injection | As an implementing agent, I want the implement workflow to resolve my assigned profile and inject the identity fragment into my prompt so that I operate under the correct specialization and governance. | High | Open |
| FR-008 | Default to generic-agent | As a workflow system, I want WPs without an explicit `agent_profile` to default to `generic-agent`. | High | Open |
| FR-009 | Profile resolution error | As a workflow system, I want a blocking error by default when a WP's explicitly set `agent_profile` cannot be resolved, so that misconfigurations are caught early. The error must be suppressible via `--allow-missing-profile`, which degrades to a non-fatal warning and continues without profile injection. | Medium | Open |
| FR-010 | Profile-context deployment | As a user, I want `spec-kitty upgrade` to deploy the `profile-context.md` command template to all configured agent directories. | Medium | Open |
| FR-011 | Generic-agent proposed | As a doctrine curator, I want the `generic-agent` profile to be created in `_proposed/` with a single directive so that it can go through HIC curation before shipping. | High | Open |
| FR-012 | Generic-agent directive reference | As a doctrine curator, I want the `generic-agent` profile to reference DIRECTIVE_028 (Efficient Local Tooling) as its single directive, so that every agent inherits baseline tooling guidance. No new directive needs to be created — DIRECTIVE_028 already exists in `shipped/`. | High | Open |
| FR-013 | Task template role hint | As a mission designer, I want mission templates to define the desired agent role/specialization per task type (e.g., `implementer`, `reviewer`, `writer`) so that the system can suggest appropriate profiles during task generation. | Medium | Open |
| FR-014 | Task profile suggestion | As a user generating tasks, I want the system to determine the appropriate concrete agent profile for each WP based on the template's role hint (via a deterministic role→profile lookup table, not content analysis), and write the `agent_profile` field into WP frontmatter for my confirmation during finalize. | Medium | Open |
| FR-015 | Init interview transparency | As a user configuring manually during init, I want to be informed about what the interview does, how it shapes my constitution, and how I can customize it later so that I understand the process and retain control. | High | Open |
| FR-020 | Init resume on interrupt | As a user whose `spec-kitty init` was interrupted mid-interview, I want the next invocation to offer me the choice to resume the previous session or start over, so that I don't lose interview progress. Selecting "start over" discards the checkpoint. | High | Open |
| FR-016 | Profile inheritance resolution | As a profile author, I want to declare `specializes-from: <parent-profile>` so that child profiles inherit unspecified fields from the parent without duplicating the full definition. | High | Open |
| FR-017 | Mission flag canonical | As a user, I want `--mission` to be the canonical flag for identifying missions in CLI commands, replacing `--feature` as the primary flag name. | Medium | Open |
| FR-018 | Feature flag deprecation | As a user with existing automation, I want `--feature` to continue working as a backward-compatible alias that emits a deprecation warning suggesting `--mission`. | Medium | Open |
| FR-019 | Glossary update for mission rename | As a glossary maintainer, I want the `Feature` glossary entry in `glossary/contexts/orchestration.md` updated to reflect the CLI flag deprecation (`--feature` → `--mission`) and the `--feature` flag added to `glossary/historical-terms.md` as a deprecated alias. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Init speed with defaults | Accepting doctrine defaults during init adds no more than 2 seconds to the init flow. | Performance | Medium | Open |
| NFR-002 | Profile injection overhead | Profile resolution and injection during implement workflow adds no more than 500ms to prompt rendering. | Performance | Low | Open |
| NFR-003 | Backward compatibility | Projects initialized before this feature continue to work without a doctrine stack — the workflow falls back to `generic-agent` when no profile is specified. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | HIC curation gate | No new doctrine artifacts (profiles, directives, tactics) may be promoted to `shipped/` status without explicit HIC review and approval through the curation flow. All new artifacts must start in `_proposed/`. | Governance | High | Open |
| C-002 | Existing constitution CLI | The existing `spec-kitty constitution interview` and `spec-kitty constitution generate` commands must continue to work independently of the init integration. | Technical | High | Open |
| C-003 | Agent directory config | Profile-context template deployment must respect the agent configuration in `.kittify/config.yaml` — only deploy to configured agents. | Technical | Medium | Open |
| C-004 | Profile schema compliance | The `generic-agent` profile must pass the existing agent-profile JSON schema validation, including the minimum one directive reference requirement. | Technical | High | Open |
| C-005 | Feature flag backward compat | The `--feature` flag must remain accepted for at least one deprecation cycle. Conflicting `--feature` and `--mission` values must produce a clear error. | Technical | Medium | Open |
| C-006 | Inheritance cycle safety | Profile inheritance resolution must detect cycles and raise a clear error rather than recursing infinitely. | Technical | High | Open |

### Key Entities

- **Agent Profile**: Behavioral identity defining an agent's role, specialization, collaboration contract, and governance references. Resolved from shipped or project directories by the `AgentProfileRepository`. Supports inheritance via `specializes-from`.
- **Profile Inheritance**: A child profile declares `specializes-from: <parent-id>` and only specifies its delta. Unspecified fields are inherited from the parent. List-type fields (e.g., `directives`, `canonical_verbs`) merge by default (union, no duplicates). An optional `excluding` key allows selective removal of inherited fields or values. Multi-level chains are supported; cycles are rejected.
- **Constitution**: The governance surface generated from interview answers or defaults. Contains selected paradigms, directives, and tool configuration. Lives in `.kittify/constitution/`.
- **WP Frontmatter `agent_profile` field**: String field in work package YAML frontmatter that identifies which agent profile the implementing agent should operate under. Defaults to `generic-agent` when absent.
- **Profile Identity Fragment**: Markdown fragment rendered by the workflow command containing the profile's name, role, purpose, specialization, directives, and initialization declaration. Injected into the implement prompt.
- **DIRECTIVE_028 (Efficient Local Tooling)**: Existing shipped directive that governs tool selection for repository operations. Referenced by `generic-agent` as its single directive, ensuring all agents inherit baseline tooling guidance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users complete `spec-kitty init` with a fully configured doctrine stack in a single command — no separate `constitution interview` step required.
- **SC-002**: 100% of WP implement workflows inject the correct agent profile identity when `agent_profile` is specified in frontmatter. Unresolvable explicit profiles produce a blocking error by default; `--allow-missing-profile` degrades to a warning and continues.
- **SC-003**: WPs without an explicit `agent_profile` default to `generic-agent` without errors.
- **SC-004**: `/spec-kitty.profile-context` is available as a slash command for all configured agents after `spec-kitty upgrade`.
- **SC-005**: Zero doctrine artifacts are promoted to `shipped/` without HIC curation — all new artifacts start in `_proposed/`.
- **SC-006**: Profile inheritance resolves correctly for single-level and multi-level chains, with cycle detection preventing infinite recursion.
- **SC-007**: All CLI commands accept `--mission` as the canonical flag; `--feature` works as a deprecated alias with a warning.
- **SC-008**: Glossary definitions are updated to reflect the `--feature` → `--mission` terminology change.

## Operational Guidelines

The following directives govern implementation, testing, and agent behaviour across all work packages in this feature. Agents must resolve each directive from the doctrine repository (shipped or project) using the relevant Python APIs (`AgentProfileRepository`, `DoctrineResolver`, or equivalent) rather than hardcoding directive content inline.

| Directive ID | Title | Governing intent |
|---|---|---|
| DIRECTIVE_001 | Architectural Integrity Standard | All changes must respect established component boundaries and the dependency direction `kernel ← constitution/doctrine ← specify_cli`. No cross-layer shortcuts. |
| DIRECTIVE_010 | Specification Fidelity Requirement | Implementation must remain faithful to the approved spec and plan. Deviations require explicit HIC approval and a spec amendment before coding begins. |
| DIRECTIVE_028 | Efficient Local Tooling | Prefer compact, low-noise tooling for repository operations. Avoid commands that generate excessive output or side effects not needed for the task. |
| DIRECTIVE_029 | Agent Commit Signing Policy | Do not configure or require GPG/SSH commit signing in automated or unattended workflows. Signing is a human-in-charge responsibility. |
| DIRECTIVE_030 | Test and Typecheck Quality Gate | All deliverables must pass the full test suite (`pytest`) and static analysis (`mypy`, `ruff`) before handoff or review. No red gates accepted. |
| DIRECTIVE_032 | Conceptual Alignment | Before acting on any shared term (profile, mission, doctrine, constitution), verify that the working definition aligns with the glossary entry. Flag misalignments before proceeding. |
| DIRECTIVE_033 | Targeted Staging Policy | Stage only the files that are expected deliverables for the current work package. No blanket `git add -A` or `git add .`. Review the diff before every commit. |

**Doctrine resolution requirement**: Agents implementing any work package in this feature are to use the relevant Python repositories (e.g., `AgentProfileRepository`, `DoctrineResolver`) to fetch doctrine information at runtime. Directive content, profile definitions, and paradigm references must be resolved dynamically from the doctrine stack, not embedded as static strings in source code.
