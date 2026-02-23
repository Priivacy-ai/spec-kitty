# Feature Specification: Mission Handoff Package & Version Matrix

**Feature Branch**: `045-mission-handoff-package-version-matrix`
**Created**: 2026-02-23
**Status**: Draft
**Target Branch**: `2.x`

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Downstream Team Replays a Mission Deterministically (Priority: P1)

A downstream team (e.g., spec-kitty-saas dashboard team) receives the committed handoff package and can reconstruct the exact mission state, artifact set, and event sequence produced during the plan-context-bootstrap-fix wave on spec-kitty 2.x — without access to the original developer environment.

**Why this priority**: Deterministic replay is the primary acceptance gate for this wave. All other deliverables (matrix note, verification note, generator script) exist to support and validate this property.

**Independent Test**: A clean checkout of spec-kitty 2.x can read the handoff package and confirm the namespace tuple, event count, and artifact list match the committed artifacts without running any feature code.

**Acceptance Scenarios**:

1. **Given** the handoff package is committed to 2.x, **When** a downstream team reads the ordered event stream, **Then** every event is uniquely identifiable, carries the namespace tuple, and the sequence is deterministically ordered with no gaps.
2. **Given** the handoff package, **When** a downstream team reads the artifact manifest snapshot, **Then** every expected artifact is listed with its class, path pattern, and required/optional status as of handoff time.
3. **Given** the handoff package, **When** a downstream team reads the artifact tree snapshot, **Then** every artifact actually present in the feature directory at handoff time is catalogued with a content fingerprint, and any expected-but-absent artifact is explicitly flagged as absent.
4. **Given** the handoff package, **When** a downstream team reads the namespace tuple, **Then** they can construct an unambiguous identity key covering: project scope identifier, feature slug, target branch, mission key, manifest version, and step_id (if applicable).

---

### User Story 2 — Team Member Regenerates the Handoff Package (Priority: P2)

A spec-kitty team member checks out 2.x, runs the committed generator command, and produces a handoff package equivalent to the committed one — same namespace tuple, same artifact list, same event order.

**Why this priority**: Reproducibility ensures the committed package stays honest. Without a generator, the package can drift silently from reality after subsequent commits.

**Independent Test**: Run the generator command in a fresh shell against the same feature directory and diff its output against the committed package files.

**Acceptance Scenarios**:

1. **Given** spec-kitty 2.x is checked out and the target feature directory exists, **When** the generator command is run with no additional setup, **Then** it produces all four handoff package components: event stream, artifact manifest snapshot, artifact tree snapshot, namespace tuple.
2. **Given** the generator command is run in a fresh environment, **When** it completes, **Then** the namespace tuple in the output matches the committed one field-for-field (timestamps are allowed to differ on rerun).
3. **Given** a different branch (not 2.x), **When** the generator command is run, **Then** the output namespace tuple reflects the actual branch and cannot be silently confused with the committed 2.x package.

---

### User Story 3 — CI and Downstream Repos Align to the Version Matrix (Priority: P2)

A CI pipeline author or downstream repository maintainer reads the version matrix note and can determine: which exact git ref of spec-kitty 2.x to target, which event and runtime versions apply, what replay commands to use, and what artifact classes and paths to expect — all from the matrix note alone.

**Why this priority**: Without a concrete matrix note, downstream teams must inspect source code to determine versions and paths, producing integration drift across teams.

**Independent Test**: The matrix note alone is sufficient to write a CI version-pin check. No source code inspection required.

**Acceptance Scenarios**:

1. **Given** the committed matrix note, **When** a CI author reads it, **Then** they find the exact git commit SHA (or tag) of spec-kitty 2.x used for this wave, with no ambiguity.
2. **Given** the matrix note, **When** a downstream team looks up replay commands, **Then** they find executable command examples using the concrete feature slug from this wave, with expected output paths stated.
3. **Given** the matrix note, **When** a team queries expected artifact classes and paths, **Then** every artifact class from the mission's taxonomy is listed with its canonical path pattern — none are omitted.
4. **Given** the matrix note lists spec-kitty-events and spec-kitty-runtime version pins, **When** a downstream team reads them, **Then** they can verify compatibility without running any code.

---

### User Story 4 — Team Confirms Setup-Plan Context Tests Are Green (Priority: P3)

A team member or reviewer reads the verification note and confirms at a glance that all four setup-plan context test scenarios are passing on the exact 2.x commit used for this handoff.

**Why this priority**: The verification note is an evidence gate — it documents the test state that authorises the handoff. It can be read independently of the package itself.

**Independent Test**: The verification note stands alone: read it to determine pass/fail status, scenario coverage, branch and commit, and the command to reproduce the run.

**Acceptance Scenarios**:

1. **Given** the verification note is committed, **When** a reviewer reads it, **Then** they see: test file(s) and scenario names, pass/fail counts, branch name, exact commit SHA, and the re-run command.
2. **Given** the verification note covers the four required scenarios, **When** a reviewer checks coverage, **Then** all of the following are confirmed green: (a) fresh session + multiple features → deterministic ambiguity error, (b) fresh session + explicit `--feature` → successful plan setup, (c) explicit feature + missing spec.md → hard error with remediation, (d) invalid feature slug → validation error.
3. **Given** the verification note, **When** a reviewer wants to rerun the tests, **Then** running the stated command from a clean 2.x checkout produces the same pass/fail result.

---

### Edge Cases

- What happens when the feature directory has no status events at handoff time — is the event stream empty or absent?
- What happens when an expected artifact in the manifest has no matching file in the feature directory — is it flagged explicitly or silently skipped?
- What happens if the generator command is run on a branch other than 2.x — does the namespace tuple reflect the correct branch or silently inherit the wrong one?
- How is `step_id` populated in the namespace tuple when the wave has no explicit step boundary assigned?
- Is the committed handoff snapshot still valid for replay if the event stream is appended to after the handoff commit?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The handoff package MUST contain an ordered event stream export in a line-delimited format where each entry is independently parseable and carries the full namespace context.
- **FR-002**: The event stream MUST preserve original event insertion order so replay produces the same state sequence as the original run — no re-sorting is permitted.
- **FR-003**: The handoff package MUST contain an artifact manifest snapshot capturing the expected artifact set for the mission type at handoff time, including each artifact's class, path pattern, and required or optional status.
- **FR-004**: The handoff package MUST contain an artifact tree snapshot enumerating every artifact actually present in the feature directory at handoff time, each entry carrying a content fingerprint for integrity verification.
- **FR-005**: The handoff package MUST contain a namespace tuple record with at minimum: project scope identifier, feature slug, target branch, mission key, manifest version, and provision for an optional step_id field.
- **FR-006**: Expected-but-absent artifacts MUST appear explicitly in the artifact tree snapshot as absent entries — silent omission is not acceptable.
- **FR-007**: All four handoff package components MUST be committed as files in the spec-kitty 2.x repository at a deterministic, documented location relative to the feature directory.
- **FR-008**: A generator command or script MUST be committed alongside the package. Running it against the same feature directory MUST reproduce an equivalent package without requiring developer environment setup beyond a standard 2.x checkout.
- **FR-009**: The generator command MUST write to stdout or a named output path — it MUST NOT silently overwrite the committed package files without an explicit flag.
- **FR-010**: The version matrix note MUST be committed to 2.x as a human-readable document identifying: the exact git ref (commit SHA or tag) of spec-kitty 2.x for this wave, spec-kitty-events and spec-kitty-runtime version pins or git refs, at least one executable replay command example using the concrete feature slug, and expected artifact classes with canonical path patterns.
- **FR-011**: The version matrix note MUST include version strings expressed as inline code blocks or structured headings, making them machine-scannable for CI version-pin extraction without parsing prose.
- **FR-012**: The verification note MUST document: which test files and scenario names were run, pass/fail counts, the exact branch name and commit SHA where tests ran, and the command to reproduce the run.
- **FR-013**: The verification note MUST confirm all four setup-plan context scenarios green: (a) ambiguity error on multiple features, (b) success on explicit `--feature`, (c) hard error on missing spec.md, (d) validation error on invalid slug.

### Key Entities

- **HandoffPackage**: The complete set of committed artifacts representing one mission run's state — event stream, artifact manifest snapshot, artifact tree snapshot, and namespace tuple. Scoped to one feature and wave.
- **NamespaceTuple**: A structured identity record that uniquely scopes a handoff package to a (project, feature, branch, mission, manifest-version) combination, with optional step_id.
- **ArtifactManifestSnapshot**: A point-in-time copy of the expected artifact manifest for the mission type and step, capturing required and optional artifact specs at handoff time.
- **ArtifactTreeSnapshot**: A point-in-time enumeration of artifacts actually present in the feature directory, each entry carrying a content fingerprint and a present/absent status.
- **VersionMatrix**: A human-readable document pinning exact dependency versions, git refs, and replay commands for downstream integration.
- **VerificationNote**: A concise evidence document confirming which test scenarios passed on which branch and commit.
- **GeneratorCommand**: A minimal, self-contained invocation (script or single CLI call) that produces a HandoffPackage from a feature directory on a clean 2.x checkout.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A downstream team can replay the handoff mission deterministically — given only the committed package, they reconstruct the same artifact state without access to the original developer environment.
- **SC-002**: The version matrix note is self-sufficient for CI — a version-pin check can be written referencing only the matrix note, with zero source code inspection required.
- **SC-003**: The generator command produces an equivalent handoff package in a single invocation from a clean 2.x checkout with no additional setup steps.
- **SC-004**: The verification note is complete in one read — pass/fail status, all four scenario names, branch and commit SHA, and the re-run command are all present with no follow-up required.
- **SC-005**: All four plan-context-bootstrap scenarios are confirmed green in the verification note against the exact 2.x commit SHA used for the handoff.

## Assumptions

- The plan-context-bootstrap-fix code is already merged and validated on origin/2.x before this feature begins implementation.
- The spec-kitty status event log and expected artifact manifest structure already exist for the target feature; no new event emission infrastructure needs to be built.
- The namespace tuple `project_scope_id` field uses local project directory identity (not a globally unique SaaS-issued UUID), since global namespace unification is deferred per PRD §15.2.
- A "minimal generator script" means a shell script or single CLI invocation committed to the repo — not a new Python module or registered subcommand.
- The handoff package files are committed inside or adjacent to the kitty-specs feature directory, not published as a separate release artifact.
- The version matrix format is markdown-first with machine-scannable version strings as inline code blocks or structured headings — not a separate YAML schema document.
- `step_id` is optional and may be `null` for waves that do not have explicit step boundaries assigned.

## Dependencies

- Plan-context-bootstrap-fix must be merged and validated on origin/2.x before this feature ships.
- Existing status event log and expected artifact manifest structures in spec-kitty 2.x serve as the data sources; no new event types are required.
- spec-kitty-events and spec-kitty-runtime version refs must be resolvable from the 2.x branch at handoff generation time.

## Out of Scope

- Building a new exporter CLI subcommand, Python module, or reusable framework for handoff generation.
- SaaS dossier projection schema design, SaaS ingestion pipeline, or dashboard rendering of the handoff package.
- Global project UUID namespace resolution and cross-org feature identity (deferred to PRD §15.2 and §15.3).
- Automated CI enforcement or gating on version matrix pins.
- Handoff packages for any feature or wave beyond the plan-context-bootstrap-fix sprint.
- Access control, redaction, or sensitivity classification of handoff artifacts.
