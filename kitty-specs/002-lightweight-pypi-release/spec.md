# Feature Specification: Lightweight PyPI Release Workflow
*Path: [kitty-specs/002-lightweight-pypi-release/spec.md](kitty-specs/002-lightweight-pypi-release/spec.md)*

**Feature Branch**: `002-lightweight-pypi-release`  
**Created**: 2025-11-02  
**Status**: Draft  
**Input**: User description: "ad a pypi release but leak no secrets into the git repo"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tag-Based Release Publishing (Priority: P1)

As the sole maintainer, I want to publish to PyPI simply by tagging a release once the main branch is ready so that packaging and distribution happen automatically without manual steps.

**Why this priority**: Shipping to PyPI reliably is the core outcome; without it the new workflow has no value.

**Independent Test**: Push a semantic version tag on a ready main branch and confirm the process builds, validates, and publishes the package to PyPI using stored secrets.

**Acceptance Scenarios**:

1. **Given** the main branch contains a bumped semantic version and updated changelog, **When** I push a matching `vX.Y.Z` tag, **Then** the automated process builds distributions, validates them, and publishes the release to PyPI.
2. **Given** the release tag is created without updating the project version, **When** the automated process runs, **Then** it fails before publishing and reports the version mismatch so I can correct it.

---

### User Story 2 - Feature Branch Readiness Checks (Priority: P2)

As the maintainer, I want guidance and automation that confirm my feature branch work is ready for release before I merge to main so that I avoid broken PyPI builds.

**Why this priority**: A consistent pre-release checklist keeps the process lightweight while preventing regressions introduced by fast iteration.

**Independent Test**: Follow the documented feature branch flow, run the readiness checks, and verify they pass or flag issues before merging.

**Acceptance Scenarios**:

1. **Given** I finish work on a feature branch, **When** I follow the readiness steps (tests, version bump selection, changelog entry), **Then** I receive automated confirmation that the branch can be merged or a clear list of blockers.

---

### User Story 3 - Secret Hygiene Safeguards (Priority: P3)

As the maintainer, I want guardrails that keep PyPI credentials in secure storage so that I never leak secrets into the repository while still shipping quickly.

**Why this priority**: Maintaining trust and avoiding credential rotation work depends on secrets never landing in version control.

**Independent Test**: Inspect repository contents and workflow configuration to confirm credentials are only referenced via managed secret storage, and attempt to run the process locally without secrets checked in.

**Acceptance Scenarios**:

1. **Given** I set the PyPI API token as a hosted secret, **When** the release workflow runs, **Then** it accesses the token from secret storage and no plain-text credential appears in the repository or build logs.
2. **Given** the secret is missing or revoked, **When** a release runs, **Then** the process halts safely with guidance on restoring credentials rather than falling back to an insecure default.

### Edge Cases

- What happens when a release tag is lower than or equal to the latest published version (should block publication and prompt for a correct increment)?
- How does the workflow handle a missing or expired PyPI API token (should stop before packaging and provide remediation guidance)?
- What happens if main receives a direct commit instead of a feature branch merge (should be detected and flagged for version/readiness review)?
- How does the process react when readiness checks fail (must prevent the merge or release until issues are resolved)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide a documented feature branch workflow that outlines how to branch from main, keep changes isolated, and prepare a release-ready merge back to main.
- **FR-002**: Enforce that main cannot accept direct commits; merges must originate from feature branches that pass the defined readiness checks.
- **FR-003**: Require semantic version updates (major/minor/patch) in project metadata and changelog entries before merging a release candidate to main.
- **FR-004**: Automatically build and validate the distributable package from the release commit before any publication step executes.
- **FR-005**: Publish the validated package to PyPI whenever the maintainer pushes a semantic version tag that matches the updated project version.
- **FR-006**: Source PyPI credentials exclusively from managed secret storage so no secrets are stored in the repository or printed in plaintext outputs.
- **FR-007**: Notify the maintainer immediately with actionable guidance when readiness checks, packaging validation, or publication steps fail.
- **FR-008**: Record release notes linked to each semantic version so the maintainer can communicate changes externally and audit what shipped.

### Key Entities *(include if feature involves data)*

- **Feature Branch**: A short-lived line of development created from main; tracks readiness status, version selection, and changelog updates for a specific change set.
- **Release Tag**: A semantic version identifier applied to the release commit; used to trigger automation and link documentation, changelog notes, and published artifacts.
- **PyPI Artifact**: The packaged distribution uploaded to PyPI; includes associated metadata (version, description, changelog link) prepared during release.
- **Managed Secret**: Securely stored credential (e.g., PyPI token) referenced by workflows; must remain outside version control and have rotation guidance.

## Assumptions

- The repository is hosted on a platform that supports branch protection rules and managed secrets for automation.
- The maintainer continues to own packaging responsibilities, including updating the changelog and selecting semantic version increments.
- PyPI remains the authoritative distribution channel, and credentials can be rotated without breaking historical releases.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Within the first three releases, 100% of semantic version tags result in successful PyPI publications without manual intervention.
- **SC-002**: Preparing a release-ready feature branch (tests, version bump, changelog, checks) requires no more than 15 minutes of manual effort on average.
- **SC-003**: Over a 30-day period after adoption, zero direct commits land on main; all changes flow through feature branches that execute readiness checks.
- **SC-004**: Across the first three releases, automated secret scanning and workflow logs reveal zero instances of PyPI credentials or sensitive values stored in the repository or exposed in plaintext.
