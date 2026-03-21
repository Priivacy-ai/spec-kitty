# Feature Specification: Agent Skills Pack

**Feature Branch**: `055-agent-skills-pack`
**Created**: 2026-03-21
**Status**: Draft
**PRD Source**: `prd-spec-kitty-agent-skills-pack-v1.md`
**Target**: Spec Kitty 2.0.11+ (`2.x` line only)

## 2.x Architecture Adaptation

The PRD specifies `src/specify_cli/templates/skills/<skill-name>/SKILL.md` as the canonical authored source location. The active 2.x codebase uses a dual-repository pattern where authored content lives in `src/doctrine/` (governance and content) while `src/specify_cli/` holds runtime and CLI implementation. Templates, missions, and governance content already follow this split, and `src/doctrine/` is bundled via `also_copy` in `pyproject.toml`.

**Adaptation**: The canonical authored skill source lives at `src/doctrine/skills/<skill-name>/`. This satisfies the PRD's product intent (one canonical authored source inside Spec Kitty, deterministic packaging and distribution through `spec-kitty init`, wrappers generated from that canonical source) while following the established 2.x content architecture.

The PRD's manifest requirement (tracking installed skill files for sync, repair, and verification) is implemented as a new dedicated managed-file manifest, separate from the existing dossier artifact validation system in `src/specify_cli/dossier/manifest.py`. The dossier manifest validates mission artifacts per step; the new managed-file manifest tracks installer-owned filesystem files for drift detection and repair.

## User Scenarios & Testing

### User Story 1 - Fresh Init Installs Skills (Priority: P1)

A user runs `spec-kitty init` on a new project with Spec Kitty 2.0.11+. After init completes, the selected agents have the canonical skill pack installed in the correct skill roots for their installation class, plus working thin wrappers in their wrapper roots. The user's agent can immediately discover and use the shipped skills.

**Why this priority**: Without distribution through init, no user can access skills. This is the foundational delivery mechanism.

**Independent Test**: Run `spec-kitty init` selecting multiple agents of different installation classes (shared-root-capable, native-root-required, wrapper-only), then verify each agent's skill root and wrapper root contains the expected files.

**Acceptance Scenarios**:

1. **Given** an empty project with no `.kittify/`, **When** the user runs `spec-kitty init` selecting claude (native-root-required), **Then** skills are installed to `.claude/skills/` and wrappers to `.claude/commands/`.
2. **Given** an empty project, **When** the user runs `spec-kitty init` selecting codex (shared-root-capable), **Then** skills are installed to `.agents/skills/` and wrappers to `.codex/prompts/`.
3. **Given** an empty project, **When** the user runs `spec-kitty init` selecting amazonq (wrapper-only), **Then** only wrappers are installed to `.amazonq/prompts/` and no skill root is created.
4. **Given** init completes, **When** the managed manifest is read, **Then** every installed skill file is tracked with its source hash and installation class.

---

### User Story 2 - Managed Manifest Tracks Installed Skills (Priority: P1)

After init or upgrade, a managed-file manifest records every installed skill file so that sync, repair, and verification can operate deterministically. The manifest tracks the source skill, the installed path, the content hash, and the installation class.

**Why this priority**: Without manifest tracking, sync/repair/verification cannot function. This enables all downstream drift management.

**Independent Test**: Run init, inspect the managed manifest file, verify it contains entries for all installed skill files with correct metadata.

**Acceptance Scenarios**:

1. **Given** init installs skill files for 3 agents, **When** the manifest is read, **Then** it contains entries for each installed file with source hash, target path, and installation class.
2. **Given** the manifest exists, **When** a managed skill file is manually deleted, **Then** `spec-kitty verify` detects the missing file and reports it.
3. **Given** the manifest exists, **When** a managed skill file is manually modified, **Then** `spec-kitty verify` detects the content drift.

---

### User Story 3 - Sync and Repair Managed Skill Files (Priority: P2)

When managed skill files are missing or have drifted from the canonical source, the user can repair them. Sync recreates missing files and restores drifted files from the packaged canonical source.

**Why this priority**: Repair is the primary value of manifest tracking. Without it, users must re-run init from scratch to fix drift.

**Independent Test**: Delete or modify an installed skill file, run sync/repair, verify the file is restored to match the canonical source.

**Acceptance Scenarios**:

1. **Given** a managed skill file is deleted, **When** the user runs sync/repair, **Then** the file is recreated from the canonical packaged source.
2. **Given** a managed skill file has been modified, **When** the user runs sync/repair, **Then** the file is restored to match the canonical source and the manifest is updated.
3. **Given** all managed skill files are intact, **When** the user runs sync/repair, **Then** no changes are made.

---

### User Story 4 - Canonical Skill Content Works End-to-End (Priority: P2)

At least one shipped skill (`spec-kitty-setup-doctor`) is authored with proper SKILL.md, references, and scripts that an agent can discover, trigger on correct user phrases, and execute a useful workflow.

**Why this priority**: Validates the entire skill authoring and distribution pipeline from canonical source to agent consumption.

**Independent Test**: Install `spec-kitty-setup-doctor` via init, verify it contains correct frontmatter (name, description), trigger phrases, workflow steps, references, and that the skill content is agent-consumable.

**Acceptance Scenarios**:

1. **Given** init installs `spec-kitty-setup-doctor`, **When** the installed SKILL.md is read, **Then** it has valid frontmatter with `name` and `description`, positive trigger phrases, and explicit negative scope boundaries.
2. **Given** the skill is installed, **When** it references diagnostic scripts or references, **Then** those sibling files are also installed and accessible.

---

### User Story 5 - Framework Capability Matrix Distribution (Priority: P2)

Skills are installed into the correct roots based on each agent's installation class from the framework capability matrix: shared-root-capable agents use `.agents/skills/` (and optionally vendor-native roots), native-root-required agents use their vendor-specific skill root, and wrapper-only agents receive only wrappers.

**Why this priority**: Correct per-agent distribution is essential for cross-framework portability.

**Independent Test**: Run init selecting one agent from each installation class, verify the skill files appear in the correct root directories.

**Acceptance Scenarios**:

1. **Given** a shared-root-capable agent (e.g., copilot), **When** init runs, **Then** skills are placed in `.agents/skills/`.
2. **Given** a native-root-required agent (e.g., claude), **When** init runs, **Then** skills are placed in `.claude/skills/`.
3. **Given** a wrapper-only agent (e.g., amazonq), **When** init runs, **Then** no skill root is created and only wrappers are installed.

---

### User Story 6 - Upgrade Installs Modern Skill Pack (Priority: P3)

Existing 2.0.11+ projects that did not previously have the skill pack can receive it through the upgrade flow.

**Why this priority**: Important for adoption but secondary to fresh init behavior.

**Independent Test**: Start with a 2.0.11 project without skills, run upgrade, verify skills are installed and manifest is populated.

**Acceptance Scenarios**:

1. **Given** an existing 2.0.11 project without skills, **When** upgrade runs, **Then** the modern skill pack is installed for all configured agents.
2. **Given** an existing 2.0.11 project with skills already installed, **When** upgrade runs, **Then** skill files are updated only if the canonical source has changed.

---

### Edge Cases

- What happens when a user has custom files in a skill root directory that collide with managed skill names?
- How does the system handle a project where `.agents/skills/` was manually created before init?
- What happens when init is interrupted mid-skill-installation?
- How does the system behave when the canonical skill source is missing from the package (corrupted install)?
- What happens when a user manually modifies a managed skill file and then runs verify?

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical skill source layout | Skills are authored in `src/doctrine/skills/<skill-name>/` with SKILL.md, optional references/, scripts/, and assets/ subdirectories. | High | Open |
| FR-002 | Init distributes skills | `spec-kitty init` installs the canonical skill pack into correct skill roots for each selected agent based on the framework capability matrix. | High | Open |
| FR-003 | Installation class routing | Init uses the capability matrix to route skills: shared-root-capable to `.agents/skills/`, native-root-required to vendor-specific skill roots, wrapper-only agents receive no skills. | High | Open |
| FR-004 | Managed-file manifest creation | Init creates a managed-file manifest tracking every installed skill file with source hash, target path, installation class, and skill name. | High | Open |
| FR-005 | Manifest persistence | The managed-file manifest is persisted in `.kittify/` and survives across sessions. | High | Open |
| FR-006 | Verify detects drift | `spec-kitty verify` reads the managed manifest, checks each tracked file for existence and content integrity, and reports missing or drifted files. | High | Open |
| FR-007 | Sync restores managed files | Sync/repair recreates missing managed skill files and restores drifted files from the packaged canonical source. | Medium | Open |
| FR-008 | Wrapper generation unchanged | Existing thin wrapper generation into wrapper roots continues to work unchanged alongside skill installation. | High | Open |
| FR-009 | Ship spec-kitty-setup-doctor | The `spec-kitty-setup-doctor` skill is authored with SKILL.md, references, and scripts following PRD section 8 guidance. | Medium | Open |
| FR-010 | Skill frontmatter | Each shipped skill has minimal frontmatter: `name` and `description` only, with specific positive triggers and explicit negative scope boundaries in the description. | Medium | Open |
| FR-011 | Upgrade installs skills | The upgrade flow installs the modern skill pack into existing 2.0.11+ projects that lack it. | Medium | Open |
| FR-012 | No duplicate skill names | Verification detects duplicate skill names across installed roots where relevant. | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Init speed | Skill installation adds less than 2 seconds to the total init execution time. | Performance | Medium | Open |
| NFR-002 | Manifest size | The managed manifest file remains under 50KB for a full 12-agent installation with all 8 skills. | Storage | Low | Open |
| NFR-003 | Test coverage | New code has 90%+ test coverage with pytest. | Quality | High | Open |
| NFR-004 | Type safety | All new code passes mypy --strict with no type errors. | Quality | High | Open |
| NFR-005 | Local-first operation | All skill distribution, manifest, verify, and sync operations work fully offline without network access. | Availability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | 2.0.11+ only | No pre-2.0.11 compatibility code. The feature targets the modern 2.x runtime line exclusively. | Technical | High | Open |
| C-002 | No separate legacy pack | A single modern pack is shipped. No legacy or split pack is introduced. | Product | High | Open |
| C-003 | Preserve wrapper behavior | Existing wrapper generation and wrapper roots must continue to function unchanged. | Technical | High | Open |
| C-004 | Doctrine content layer | Canonical skill source must reside in `src/doctrine/skills/`, following the 2.x dual-repository architecture. | Technical | High | Open |
| C-005 | Separate from dossier manifest | The managed-file manifest is a new dedicated system, not an extension of `src/specify_cli/dossier/manifest.py`. | Technical | High | Open |
| C-006 | PRD-defined skill surface | Only the 8 skills defined in PRD section 7 are shipped. No additional skills are added without PRD update. | Product | Medium | Open |
| C-007 | Minimal frontmatter | Skill frontmatter contains only `name` and `description` by default, per PRD design principle 9. | Technical | Medium | Open |

### Key Entities

- **CanonicalSkill**: A skill authored in `src/doctrine/skills/<skill-name>/` containing SKILL.md and optional references/, scripts/, assets/ subdirectories. Represents the single source of truth for skill content.
- **ManagedFileManifest**: A persistent record (in `.kittify/`) tracking every installed skill file with its source hash, target path, installation class, and originating skill name. Enables verify, sync, and repair.
- **InstallationClass**: One of shared-root-capable, native-root-required, or wrapper-only. Determines which roots receive skill files for each agent.
- **SkillRoot**: A directory where an agent discovers skills (e.g., `.claude/skills/`, `.agents/skills/`). Distinct from wrapper roots (e.g., `.claude/commands/`).

## Success Criteria

### Measurable Outcomes

- **SC-001**: A user can run `spec-kitty init` on Spec Kitty 2.0.11+ and receive working skills and wrappers for every selected agent without manual file copying.
- **SC-002**: `spec-kitty verify` detects 100% of missing or drifted managed skill files when compared against the manifest.
- **SC-003**: Sync/repair restores all missing or drifted managed skill files to match the canonical source with zero manual intervention.
- **SC-004**: Wrapper-only agents continue to receive working wrappers with no regressions from skill pack introduction.
- **SC-005**: The `spec-kitty-setup-doctor` skill is installable, discoverable by the target agent, and contains complete setup/verify/recovery guidance.
