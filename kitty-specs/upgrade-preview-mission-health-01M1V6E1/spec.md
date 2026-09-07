# Mission Specification: Upgrade Preview Reliability and Mission Corpus Health

**Mission Branch**: `codex/upgrade-preview-mission-health`
**Created**: 2026-09-06
**Status**: Approved for planning after independent three-lens review
**Audience**: Spec Kitty maintainers and automation operators
**Input**: Full mission for #3900-#3903; external tooling-friction ledger and evidence-backed workarounds.

## Confirmed Intent

The operator confirmed on 2026-09-06 that the four issue acceptance sections
are the brief and a separate discovery interview should be skipped.
A maintainer or automation operator previews an upgrade before consenting to
changes. Preview must not change project/global assets, must disclose repairs
even when versions match, and must reject invalid downgrade targets consistently.
Separately, maintainers repair four known corpus audit failures without inventing
identities, discarding history, or treating upgrade consent as repair consent.

Local consolidation targets the topic branch above. The publication PR targets
`main`; never push directly to `origin/main`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect Without Changes (Priority: P1)

An operator previews on a machine with absent, stale, or current global assets
without implicitly consenting to install or refresh anything.

**Why this priority**: Preview is a trust boundary.
**Independent Test**: Public CLI subprocesses with isolated homes and complete
before/after snapshots, including ignored files, directories, and symlinks.

**Acceptance Scenarios**:
1. **Given** absent global runtime/commands/skills, **when** human or JSON dry-run
   executes, **then** no project/home assets are created, removed, or changed.
2. **Given** stale managed assets and customizations, **when** either mode
   previews, **then** both remain unchanged and required work is reported.
3. **Given** current assets, **when** previews repeat, **then** all remain read-only.

### User Story 2 - Understand All Repairs (Priority: P1)

An operator can distinguish no versioned migrations from no changes.

**Why this priority**: Same-version upgrades currently hide hundreds of writes.
**Independent Test**: Preview/apply on identical realistic fixtures and compare
path-level operations against complete actual writes, not only git diff.

**Acceptance Scenarios**:
1. **Given** current version metadata with missing/stale commands, skills,
   profiles, or manifests, **when** preview executes, **then** human and machine
   output disclose intended repairs and global/project scope.
2. **Given** equivalent unchanged fixtures, **when** planned repair is applied,
   **then** every generated-surface write is represented in the plan, while
   unchanged surfaces are not falsely reported as changes.
3. **Given** repaired assets, **when** preview/apply repeat, **then** the plan
   contains no remaining repair writes and apply changes nothing.
4. **Given** user-owned or non-applicable surfaces, **when** planning/application
   executes, **then** ownership/applicability agree and conflicts are disclosed
   rather than custom content silently overwritten.

### User Story 3 - Consistent Target Verdicts (Priority: P1)

Automation receives the same upgrade-target validity verdict as a human.

**Why this priority**: ALLOW for a forbidden downgrade is misleading.
**Independent Test**: Public CLI human/JSON matrix of lower/equal/higher,
prerelease, malformed targets and independent compatibility blockers.

**Acceptance Scenarios**:
1. **Given** a lower target, **when** either mode previews, **then** it explicitly
   reports downgrade rejection and reason, never ALLOW from schema compatibility.
2. **Given** equal/higher targets, **when** previewed, **then** target validity
   agrees without bypassing independent compatibility or supported-target checks.
3. **Given** malformed target input, **when** previewed, **then** explicit
   validation replaces accidental ALLOW or unhandled traceback.
4. **Given** any rejected target, **when** preview completes, **then** assets
   remain unchanged irrespective of JSON process-exit normalization.

### User Story 4 - Trustworthy Mission History (Priority: P1)

A maintainer restores the committed corpus to a blocker-free audit.

**Why this priority**: Readiness depends on coherent identity and status evidence.
**Independent Test**: Audit the real corpus, inspect four original failures,
repair using supported paths and provenance, then re-audit the entire corpus.

**Acceptance Scenarios**:
1. **Given** identity-less `R2-T1-local-legacy-removal` and
   `reject-cyclic-lane-graphs-01M0QCK4`, **when** investigated, **then**
   historical evidence determines whether to restore real identity or relocate
   non-mission artifacts, never fabricate metadata to silence the audit.
2. **Given** drift in `doctrine-drg-silent-drop-boundary-01M0PE7E` and
   `symbolkey-source-module-01M0B0SF`, **when** reconciled, **then** snapshots
   agree with authoritative events while retaining verdicts and provenance.
3. **Given** the repaired corpus, **when**
   `doctor mission-state --audit --fail-on teamspace-blocker --json` runs,
   **then** exit is zero and all four original blockers are gone.
4. **Given** upgrade consent only, **when** mission-state defects are encountered,
   **then** upgrade does not implicitly authorize or apply mission-state repair.

### Edge Cases

- Absent roots, stale and warm assets, ignored paths, symlinks, missing/stale or
  malformed manifests, disabled agents, mixed package/user-owned content.
- Equal version and empty migration list with outstanding surface repair.
- Prerelease ordering, malformed versions, unsupported targets, schema blockers.
- Human review evidence not represented by snapshot reduction; preserve it.
- Non-mission directories under the corpus; preserve references when relocating.
- Newly observed blockers must be diagnosed, not hidden with weaker audit gates.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Read-only preview | As an operator, I require both public CLI dry-run modes to perform zero project/global asset mutations for absent, stale, and warm assets. | High | Approved |
| FR-002 | Complete visibility | As an operator, I need all intended global/project generated-surface repairs disclosed, including same-version/no-migration cases. | High | Approved |
| FR-003 | Plan/apply agreement | As an operator, I require planned repair paths and operation kinds to match actual writes on unchanged equivalent fixtures, distinguishing unchanged surfaces. | High | Approved |
| FR-004 | Repair idempotence | As an operator, I require a second repair to change nothing and subsequent preview to show no remaining repair writes. | High | Approved |
| FR-005 | Target parity | As an automation operator, I require human/JSON validity agreement for lower/equal/higher and malformed targets, with explicit downgrade rejection independent of exit normalization. | High | Approved |
| FR-006 | Independent compatibility | As an operator, I require target validation not to conceal independent compatibility blockers or bypass supported-target policy. | High | Approved |
| FR-007 | Identity classification | As a maintainer, I need both named identity-less directories classified and repaired or relocated from recorded provenance without fabricated identity. | High | Approved |
| FR-008 | Snapshot evidence | As a maintainer, I require both named drifted snapshots reconciled against authoritative events without losing review verdicts or provenance. | High | Approved |
| FR-009 | Corpus health | As a maintainer, I require the full committed corpus to pass the TeamSpace-blocker audit with all four original failures resolved. | High | Approved |
| FR-010 | Separate consent | As an operator, I require upgrade consent to remain distinct from mission-state repair consent. | High | Approved |
| FR-011 | Delivery traceability | As a maintainer, I need every issue traced through spec, WP, tests, code/data, independent review, and terminal issue-matrix evidence. | High | Approved |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Mutation precision | Preview shows zero additions, deletions, content/symlink-target, permission, or modified-timestamp changes under audited project/home roots; read access times excluded. | Reliability | High | Approved |
| NFR-002 | Machine compatibility | Preserve the pinned strict legacy JSON consumer/schema contract; do not assume additional fields are compatible. A negotiated or separately documented machine plan may extend repair detail. Parse complete stdout as one JSON value and explicitly represent target rejection. | Compatibility | High | Approved |
| NFR-003 | Non-vacuous evidence | Every repaired defect has a witnessed failing-first check through its existing entry point and a passing final check; no fixture stubs away the defect. | Testability | High | Approved |
| NFR-004 | Preservation | Zero user-owned assets or historical event records discarded or overwritten without explicit ownership/provenance justification. | Integrity | High | Approved |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical authority | Reuse canonical planning, ownership, version-validation and event-state authorities; do not create competing interpretations. | Architecture | High | Approved |
| C-002 | Scope | No release/version bump, broad governance rewrite, hosted API change, or mass cleanup of the prior 3,739 audit warnings and 22,496 informational findings. | Scope | High | Approved |
| C-003 | Safe execution | Keep SaaS sync disabled; perform destructive verification only in isolated disposable fixtures. | Operations | High | Approved |
| C-004 | Lifecycle | Execute specify, plan, tasks, analyze, independent implement/review, accept, local consolidation, and post-consolidation mission review; publish via PR only. | Process | High | Approved |
| C-005 | Friction ledger | Maintain an out-of-repo ledger with exact commands, observed failures, workarounds and reporting dispositions. | Process | High | Approved |
| C-006 | Honest recovery | Record workflow blockers and use narrow safe workarounds or obvious fixes; never fabricate completed gates or review verdicts. | Process | High | Approved |

### Key Entities *(include if feature involves data)*

- **Upgrade preview**: read-only compatibility and intended-work explanation.
- **Repair plan**: path-level intended operations, scope, reasons, ownership and
  applicability/conflicts; distinct from the migration list.
- **Managed surface**: package-owned runtime, command, skill, profile or manifest.
- **Mission identity**: immutable historical identity, not an audit placeholder.
- **Authoritative event history**: evidence governing materialized mission status.
- **Status snapshot**: derived state that must agree with its authoritative history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All required preview scenarios leave audited assets unchanged.
- **SC-002**: All actual repair writes are disclosed before consent on equivalent
  fixtures; a repaired fixture has zero remaining repair writes.
- **SC-003**: Every parity-matrix target receives matching validity and reason.
- **SC-004**: Full gated corpus audit reports zero TeamSpace blockers with no
  loss of historical evidence and all four original failures resolved.
- **SC-005**: All four issues have independently checked acceptance evidence and
  the consolidated mission has its review, retrospective, and friction ledger.

## Sources and Assumptions

- [#3900](https://github.com/Priivacy-ai/spec-kitty/issues/3900): preview side effects.
- [#3901](https://github.com/Priivacy-ai/spec-kitty/issues/3901): omitted repairs.
- [#3902](https://github.com/Priivacy-ai/spec-kitty/issues/3902): target divergence.
- [#3903](https://github.com/Priivacy-ai/spec-kitty/issues/3903): corpus blockers.
- Baseline: `c0054153b9bce0778cf41a85d11ecd4e9650031d` (PR #3888).
- Behavior repair, not a bulk identifier/text rename.
- JSON may retain documented zero process exit; its payload must still reject
  invalid targets. Process success is not upgrade approval.
- Snapshot equality proves absence of persistent effects, not absence of
  transient write-then-delete operations; test write-capable planning seams
  separately. Independent snapshot checks must detect ignored-file changes,
  symlink retarget/deletion, and chmod before being used as evidence.
- The operator confirmed the brief and branch workflow; no product decisions
  are deferred. The plan owns implementation design.
