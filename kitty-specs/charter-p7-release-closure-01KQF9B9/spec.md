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

PR #900 delivered the Phase 7 compatibility registry, bundle migration, hardened provenance models, status provenance regression coverage, and most of the Charter bundle versioning work. Post-merge review found that the public validation gate still does not enforce the full provenance chain:

- `spec-kitty charter bundle validate` parses existing sidecars, but does not call the full synthesis-state validation helper, so synthesized doctrine artifacts can exist without matching provenance sidecars and still pass validation.
- `spec-kitty charter bundle validate --json` can emit Rich/plain text to stdout on provenance failures, which violates the strict JSON contract needed by CI and Charter canaries.

This mission closes those final release blockers so #515 and #469 can be completed with a defensible public gate.

---

## Scope

**In scope**:

- Product repository only: `Priivacy-ai/spec-kitty`
- Wire full synthesis-state validation into the public `charter bundle validate` command
- Preserve strict JSON stdout for all `charter bundle validate --json` success and failure paths
- Add public CLI regression tests for missing sidecars, malformed sidecars, invalid synthesis manifest integrity, and legacy no-synthesis-state projects
- Keep the accepted PR #900 design: sidecars link to the manifest through `synthesis_run_id`; the manifest carries `manifest_hash`
- Complete post-merge GitHub hygiene for #515 and #469 after the release-closure PR merges

**Out of scope**:

- Reopening the accepted `bundle_hash` design unless a reviewer explicitly asks for that contract change
- Changing SaaS, tracker, sync, hosted auth, or external package behavior
- Publishing a package release
- Touching Charter epic #827 or docs issue #828 unless asked separately

---

## User Scenarios & Testing

### Primary scenario — CI rejects incomplete synthesized doctrine state

A CI job runs `spec-kitty charter bundle validate --json` on a project containing synthesized doctrine artifacts under `.kittify/doctrine/**`. If any generated artifact lacks a matching `.kittify/charter/provenance/*.yaml` sidecar, validation exits non-zero and returns a parseable JSON envelope describing the missing provenance.

### Scenario — CI rejects corrupt synthesis manifest

A bundle contains `.kittify/charter/synthesis-manifest.yaml`, but its `manifest_hash` is malformed or no longer matches the manifest contents. `charter bundle validate --json` exits non-zero and returns strict JSON with the manifest integrity error.

### Scenario — Existing malformed sidecar failures remain JSON-safe

A provenance sidecar exists but omits a required v2 field or contains invalid values. `charter bundle validate --json` exits non-zero, emits no Rich/plain text to stdout, and the stdout parses with `json.loads()`.

### Scenario — Legacy projects without synthesis state remain valid

A project with a valid charter bundle but no `.kittify/charter/provenance/`, no synthesis manifest, and no synthesized doctrine artifacts continues to pass `charter bundle validate`. The final gate must not convert non-synthesized legacy projects into false failures.

### Scenario — Complete v2 bundle remains valid

A v2 bundle with matching doctrine artifacts, sidecars, valid sidecar fields, and a valid manifest exits 0 in both human and JSON modes.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty charter bundle validate` invokes the same full synthesis-state validation semantics as `charter.bundle.validate_synthesis_state()` or an equivalent shared helper. | Proposed |
| FR-002 | Public bundle validation fails when synthesized `.kittify/doctrine/**` artifacts exist without matching provenance sidecars. | Proposed |
| FR-003 | Public bundle validation fails when provenance sidecars reference missing artifact files. | Proposed |
| FR-004 | Public bundle validation fails when `synthesis-manifest.yaml` integrity verification fails, including malformed `manifest_hash`, hash mismatch, or referenced-state inconsistency. | Proposed |
| FR-005 | Projects with no synthesis state remain valid when existing canonical bundle validation checks pass. | Proposed |
| FR-006 | `spec-kitty charter bundle validate --json` emits parseable JSON to stdout for success and every validation failure introduced or touched by this mission. | Proposed |
| FR-007 | No Rich/plain text is written to stdout before or after the JSON envelope when `--json` is set. Human-readable output may remain in non-JSON mode. | Proposed |
| FR-008 | JSON failure envelopes include actionable error details for provenance parsing errors and synthesis-state validation errors. | Proposed |
| FR-009 | Regression tests exercise the public CLI surface for missing sidecar, invalid sidecar field, invalid manifest hash, legacy no-synthesis-state success, and complete v2 success. | Proposed |
| FR-010 | Existing PR #900 behavior remains intact: version compatibility checks, bundle migration tests, status `--json --provenance`, and synthesis model validation keep passing. | Proposed |
| FR-011 | Post-merge hygiene closes #515 and comments/closes #469 only after the release-closure PR merges and the merge SHA is known. | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Strict JSON contract: every `--json` stdout path covered by this mission must parse with `json.loads(stdout)`. | 100% for tested paths | Proposed |
| NFR-002 | Validation remains local-only and deterministic. No network calls are introduced. | 0 network I/O | Proposed |
| NFR-003 | Validation overhead remains acceptable for normal bundles. | Up to 50 artifacts under 2 seconds on local disk | Proposed |
| NFR-004 | Public CLI behavior remains backward compatible for complete v2 bundles and legacy no-synthesis-state projects. | No intentional regressions | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Scope is the `spec-kitty` product repo only. | Active |
| C-002 | Do not rework the compatibility registry, migration registration, `canonical_yaml()` hashing behavior, or status provenance output unless integration requires a narrow change. | Active |
| C-003 | Treat PR #900's `synthesis_run_id` plus `SynthesisManifest.manifest_hash` design as accepted. Do not add a direct `bundle_hash` sidecar field unless review explicitly reopens the field-level contract. | Active |
| C-004 | Commands that touch SaaS, tracker, or sync flows are out of scope. If any such validation is added later on this machine, run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Active |
| C-005 | Planning artifacts stay on `main`; implementation should happen on `fix/charter-p7-release-closure` at implement time. | Active |

---

## Required Verification

Run at minimum:

```bash
uv run pytest tests/charter/test_bundle_validate_cli.py -q
uv run pytest tests/charter/synthesizer/test_bundle_validate_extension.py -q
uv run pytest tests/specify_cli/cli/commands/test_charter_status_provenance.py -q
uv run pytest tests/doctrine/test_versioning.py tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py -q
uv run ruff check src/specify_cli/cli/commands/charter_bundle.py src/charter/bundle.py tests/charter/test_bundle_validate_cli.py tests/specify_cli/cli/commands/test_charter_status_provenance.py
```

If time permits, also run:

```bash
uv run pytest tests/charter/synthesizer/ tests/charter/test_bundle_validate_cli.py tests/specify_cli/cli/commands/test_charter_status_provenance.py tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py tests/doctrine/test_versioning.py -q
```

---

## Success Criteria

1. `charter bundle validate` exits non-zero for doctrine artifacts without matching provenance sidecars.
2. `charter bundle validate` exits non-zero for invalid or mismatched synthesis manifest integrity.
3. `charter bundle validate --json` stdout is strict JSON for malformed sidecar, missing sidecar, invalid manifest, and success paths.
4. Legacy projects with no synthesis state still pass validation when the existing canonical bundle checks pass.
5. Complete v2 synthesis bundles still pass validation.
6. Existing Phase 7 tests from PR #900 continue passing.
7. The PR references #469 and #515, and post-merge issue hygiene is completed with the merge SHA.

---

## Key Files

| File | Expected role |
|------|---------------|
| `src/specify_cli/cli/commands/charter_bundle.py` | Public `charter bundle validate` command integration and JSON/human output routing |
| `src/charter/bundle.py` | Existing synthesis-state validation helper and manifest/sidecar validation semantics |
| `tests/charter/test_bundle_validate_cli.py` | Public CLI regression tests for validation and JSON envelopes |
| `tests/charter/synthesizer/test_bundle_validate_extension.py` | Existing lower-level synthesis-state validation coverage |
| `tests/specify_cli/cli/commands/test_charter_status_provenance.py` | Regression guard for status provenance behavior |
| `tests/doctrine/test_versioning.py` | Compatibility registry guard |
| `tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py` | Upgrade migration guard |

---

## Release Handoff

Before merge:

- Open one PR against `Priivacy-ai/spec-kitty:main`.
- Mention #469 and #515 in the PR body.
- Include reproduction notes for the two remaining blockers.
- Include exact test commands and outcomes.

After merge:

- Close #515 with the merge SHA and state that `bundle validate` now enforces sidecar presence, manifest integrity, and strict JSON failure envelopes.
- Comment on #469 with the merge SHA and summarize #512, #513, and #515 completion.
- Close #469 if no Phase 7 acceptance gap remains after this PR.
- Leave #827 and #828 untouched unless the reviewer explicitly asks for Charter epic rollup hygiene.

---

## Open Questions

None. This mission is deliberately narrow: close the two reproduced post-PR #900 public gate blockers and finish issue hygiene.
