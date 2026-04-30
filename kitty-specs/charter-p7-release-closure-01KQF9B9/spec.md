# Charter Phase 7 Release Closure

**Mission ID**: 01KQF9B97EV87WK6753J9KTGEC
**Mission slug**: charter-p7-release-closure-01KQF9B9
**Mission type**: software-dev
**Target branch**: main
**Parent issue**: #469 (Phase 7 of the Charter EPIC #461)
**Primary open issue**: #515 (WP7.3 provenance sidecar hardening)
**Prior merge**: PR #900, merge commit `a9d8cab2b2937abc2647f2f56b9ef386bf872d9f`

---

## Purpose

The prior Phase 7 delivery (PR #900) integrated the compatibility registry, bundle migration, hardened provenance models, and status provenance regression coverage. Post-merge review identified two public-gate blockers that must be resolved before issues #469 and #515 can close and Phase 7 can be treated as release-ready:

1. The bundle validation command does not enforce the full provenance chain: synthesized doctrine artifacts can pass validation even when matching provenance sidecars are absent.
2. The `--json` flag for bundle validation can emit non-JSON content to stdout on failure, breaking CI pipelines and automated consumers that depend on structured output.

This mission closes both blockers, adds regression coverage through the public CLI surface, and completes GitHub issue hygiene after the release PR merges.

---

## Scope

**In scope**:

- Wire full synthesis-state provenance enforcement into the public bundle validation command
- Preserve strict JSON stdout on the `--json` path for success and all failure cases
- Add regression coverage for the reproduced failures via the public CLI surface
- Complete post-merge GitHub hygiene for #515 and #469

**Out of scope**:

- Reopening the accepted PR #900 audit-linkage design
- Changing SaaS, tracker, sync, or hosted authentication behavior
- Publishing a package release
- Reworking Charter epic issues #827 or #828 unless a reviewer explicitly asks

---

## User Scenarios & Testing

### Primary scenario — CI rejects incomplete synthesized doctrine state

A CI job runs bundle validation with `--json` on a project containing synthesized doctrine artifacts. If any artifact lacks a matching provenance sidecar, validation exits non-zero and stdout contains parseable JSON describing the missing provenance.

### Scenario — CI rejects corrupt synthesis manifest

A bundle contains a synthesis manifest whose integrity value is malformed or no longer matches the manifest contents. Bundle validation with `--json` exits non-zero and stdout contains strict JSON with the manifest integrity error.

### Scenario — Malformed sidecar failures remain JSON-safe

A provenance sidecar exists but omits a required field or contains invalid values. Bundle validation with `--json` exits non-zero, writes nothing to stdout except parseable JSON, and the JSON envelope describes the sidecar error.

### Scenario — Legacy projects without synthesis state remain valid

A project with a valid charter bundle but no synthesized doctrine artifacts, no provenance sidecars, and no synthesis manifest passes bundle validation. The new provenance gate must not convert non-synthesized legacy projects into false failures.

### Scenario — Complete v2 bundle passes

A bundle with all synthesized artifacts, matching sidecars, and a valid synthesis manifest exits 0 in both human and JSON modes.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | Bundle validation fails when synthesized doctrine artifacts exist without corresponding provenance sidecars. | Proposed |
| FR-002 | Bundle validation fails when a provenance sidecar references an artifact file that is absent on disk. | Proposed |
| FR-003 | Bundle validation fails when synthesis manifest integrity verification fails, including malformed integrity values or hash mismatch. | Proposed |
| FR-004 | Projects with no synthesis state (no synthesized artifacts, no synthesis manifest, no sidecars) pass validation when all other bundle checks pass. | Proposed |
| FR-005 | `charter bundle validate --json` emits parseable JSON to stdout for both success and every failure path. | Proposed |
| FR-006 | When `--json` is active, no plain-text or formatted-console output is written to stdout before or after the JSON envelope. | Proposed |
| FR-007 | JSON failure envelopes include sufficient detail to identify which artifact or field caused the failure. | Proposed |
| FR-008 | Regression tests exercise every new failure mode — missing sidecar, missing artifact reference, manifest hash failure, and the `--json` path for each — through the public CLI surface. | Proposed |
| FR-009 | All Phase 7 behavior from the prior merge continues to pass: compatibility checks, bundle migration, status provenance output, and model validation. | Proposed |
| FR-010 | After the release PR merges, issue #515 is closed with a note referencing the merge SHA; issue #469 receives a completion summary covering #512, #513, and #515, and is closed if no other Phase 7 acceptance gap remains. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | `charter bundle validate --json` stdout must be parseable for every path covered by regression tests. | 100% of tested paths | Proposed |
| NFR-002 | Validation is local-only and deterministic with no network calls introduced. | 0 network calls | Proposed |
| NFR-003 | Validation completes within an acceptable time for normal bundle sizes. | ≤2 seconds for bundles with up to 50 artifacts on a developer workstation | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Changes are scoped to the `spec-kitty` product repository only. | Active |
| C-002 | The accepted audit-linkage design — sidecars carry a run identifier; the synthesis manifest carries an integrity hash — must not be reopened unless a reviewer explicitly requests the contract change. | Active |
| C-003 | Existing Phase 7 surfaces not required for integration (compatibility registry, migration registration, hashing utilities, status provenance output) must not be reworked. | Active |
| C-004 | SaaS, tracker, sync, and hosted authentication flows are out of scope. | Active |
| C-005 | Package release publication is out of scope for this mission. | Active |

---

## Assumptions

- The accepted PR #900 design for audit linkage is stable: sidecars reference the synthesis run via a run-identifier field; the synthesis manifest carries the integrity hash. No direct bundle-hash field on sidecars is required unless a reviewer explicitly reopens this decision.
- Non-synthesized legacy bundles (no provenance directory, no synthesis manifest, no synthesized artifacts) are valid by design and the new gate must not change that behavior.
- Error details may appear on stderr in any mode; only stdout has the strict JSON contract when `--json` is active.

---

## Success Criteria

1. Bundle validation exits non-zero and reports the missing provenance when doctrine artifacts exist without matching sidecars.
2. Bundle validation exits non-zero and reports the integrity failure when the synthesis manifest is malformed or mismatched.
3. `charter bundle validate --json` stdout is valid JSON for every path covered by regression tests: missing sidecar, missing artifact reference, manifest hash failure, and a passing complete v2 bundle.
4. Legacy bundles with no synthesis state continue to pass validation.
5. Complete v2 bundles with valid sidecars and a valid manifest continue to pass validation.
6. All Phase 7 regression tests from the prior merge continue to pass.
7. Issue #515 is closed and issue #469 receives a completion summary and is closed (if no other Phase 7 gap remains) after the release PR merges.

---

## Release Handoff

Before merge:

- Open one PR against `Priivacy-ai/spec-kitty:main`.
- PR body must reference issues #469 and #515.
- Include reproduction notes for the two fixed blockers.
- Include the test commands run and their outcomes.

After merge:

- Close #515 with the merge SHA and a note that bundle validation now enforces sidecar presence, manifest integrity, and strict JSON failure envelopes.
- Comment on #469 with the merge SHA and a summary of #512, #513, and #515 completion.
- Close #469 if no other Phase 7 acceptance gap remains.
- Leave #827 and #828 untouched unless a reviewer explicitly asks for Charter epic rollup hygiene.
