# Charter Contract Cleanup Tranche 1

**Mission ID:** `01KQATS4HJS0HY02VF05FCP57T`
**Mission Slug:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Mission Type:** software-dev
**Target Branch:** `main`
**Created:** 2026-04-28

## Purpose

### TLDR

Make the landed Charter product gate truthful and CI-green via JSON synthesis contract fixes, golden-path E2E prompt-file hardening, and CI mypy hygiene — one product-repo PR.

### Context

Release PR #864 shipped the Charter epic, but current `main` still has Charter CLI `--json` envelope contract gaps (warning leakage on stdout, missing `result` / `adapter` / `written_artifacts` fields, dry-run paths derived from placeholder `PROJECT_000`), a weak prompt-file assertion in the golden-path E2E (#844), and a `CI Quality` `e2e-cross-cutting` failure caused by missing `mypy` in that job.

This mission produces one PR against `Priivacy-ai/spec-kitty:main` from branch `fix/charter-827-contract-cleanup` that closes those contract truths, hardens the E2E, restores green CI, and verifies (does not rewrite) the retrospective and path-traversal regression guards.

External end-to-end coverage (#827 Tranche 3), plain-English acceptance scenarios, end-user documentation (#828), and Phase 7 schema/provenance hardening (#469) are explicit later tranches and are out of scope for this mission.

## Domain Language

| Canonical term | Meaning | Avoid these synonyms |
|---|---|---|
| Charter synthesize CLI | The `spec-kitty charter synthesize` command surface, including `--json` and `--adapter fixture` flags | "synth", "charter compile" |
| Synthesis envelope | The JSON object emitted to stdout when `--json` is set | "synth output", "synth result blob" |
| Written artifacts | The list of doctrine files actually staged or promoted by a synthesize run | "outputs", "files", "produced docs" |
| Issued action | A `kind=step` envelope produced by the runtime that requires the agent to perform a prompted action | "step", "task envelope" |
| Blocked decision | A runtime envelope that halts a step with a non-empty human-readable `reason` | "halt", "stopped step" |
| Prompt file | The on-disk prompt artifact that an issued action points to | "prompt", "instruction file" |
| Dry-run staged path | The artifact path that the synthesize pipeline reports during `--dry-run` and that must match the path used by a real run | "preview path", "planned path" |
| Regression guard | A previously-fixed bug whose fix must remain intact (verify, do not rewrite) | "old fix", "legacy patch" |

## User Scenarios & Testing

### Primary Scenario: Charter synthesize emits a strict, contracted JSON envelope

**Actor:** A developer or automation that runs `spec-kitty charter synthesize --adapter fixture --json` against a fresh project to seed Charter doctrine.

**Trigger:** The user invokes the synthesize command with `--json` set.

**Happy path:**

1. The command runs synthesis (including evidence gathering).
2. The command emits exactly one JSON document to stdout — nothing else, even if evidence warnings were produced.
3. The JSON document contains, at minimum: `result: "success"`, `adapter` with `id` and `version`, `written_artifacts` (the real list of staged/promoted files), and `warnings` (possibly empty).
4. The exit code is `0`.
5. The caller can pass the stdout into `json.loads(...)` without preprocessing.

**Acceptance:**

- AC-001 The full stdout parses as a single JSON document via `json.loads(stdout)` even when evidence warnings exist.
- AC-002 The success envelope contains the four contracted fields named above; missing any one of them is a hard failure.
- AC-003 `written_artifacts` lists files that the run actually staged or promoted; no entry is fabricated from `kind:slug` selectors.

### Scenario: Dry-run paths match real-run paths

**Actor:** A developer running `spec-kitty charter synthesize --dry-run --json` to preview what would be written.

**Trigger:** The user wants to know the exact target paths before allowing a write.

**Happy path:**

1. The dry-run reports a list of staged target paths.
2. A subsequent non-dry-run with the same inputs writes to exactly those paths.
3. No user-visible string contains the placeholder `PROJECT_000`.

**Acceptance:**

- AC-004 For an input where provenance yields a non-placeholder artifact ID (for example `PROJECT_001`), the dry-run envelope reports the same target path the non-dry-run would write.
- AC-005 No `--json` envelope, log message, or error message visible to the user contains `PROJECT_000`.

### Scenario: Golden-path E2E rejects empty prompt files

**Actor:** CI / a developer running the Charter epic golden-path E2E.

**Trigger:** `tests/e2e/test_charter_epic_golden_path.py` runs to completion against the real synthesizer.

**Happy path:**

1. The E2E inspects every issued-action (`kind=step`) envelope.
2. For each issued action, the test asserts a `prompt_file` (or documented public equivalent) field exists, is not `None`, is not empty, and resolves to a real prompt file on disk.
3. For every blocked decision, the test asserts a non-empty `reason` is present and does not require a prompt file.
4. If any issued action lacks a resolvable prompt file, the test fails with a clear message.

**Acceptance:**

- AC-006 An issued action whose prompt path is missing, `None`, empty, or unresolvable causes the E2E to fail, not silently pass.
- AC-007 A blocked decision with a non-empty `reason` and no prompt file passes that check.

### Scenario: CI `e2e-cross-cutting` is honest about mypy

**Actor:** CI on a PR.

**Trigger:** The `e2e-cross-cutting` job runs `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py`.

**Happy path:**

1. Either `mypy` is available in the job and the test runs and passes against the real strict configuration; or
2. `mypy` is intentionally absent from the job, in which case the test reports a clear, actionable skip or failure that names the missing extra and how to install it. Silent passes are not acceptable.

**Acceptance:**

- AC-008 The `e2e-cross-cutting` job exits cleanly when run against current main with this mission's fixes applied; no `python -m mypy: not found` failures remain unaddressed.

### Scenario: Regression guards verified intact

**Actor:** The implementing agent during this mission.

**Trigger:** The mission begins.

**Happy path:**

1. Before touching any product code, the agent runs the regression-guard test suite listed in NFR-001 against current `main`.
2. All listed tests pass; no edits are made to those code paths.
3. If any regression guard fails, that finding is treated as a new in-scope item and a fix is added to this mission.

**Acceptance:**

- AC-009 `tests/next/test_retrospective_terminus_wiring.py`, `tests/retrospective/test_gate_decision.py`, and `tests/doctrine_synthesizer/test_path_traversal_rejection.py` all pass on the feature branch with no rewrites of their underlying production code unless a regression was actually observed.

### Edge Cases & Exception Paths

- A synthesize run that produces zero written artifacts must still emit a contracted envelope with `written_artifacts: []`, not omit the field.
- A synthesize run with multiple warnings must place every warning inside the JSON envelope's `warnings` array (or send all of them to stderr) — partial leakage is a contract failure.
- A blocked decision that also carries a prompt path is acceptable; a blocked decision without a `reason` is not.
- The `Protect Main Branch` failure observed on the release merge is treated as release-process hygiene; if confirmed not to be product-code-fixable, it is filed or updated as a separate GitHub issue rather than addressed in this PR.
- Any command path that touches hosted auth, tracker, SaaS sync, or sync behavior must be invoked with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set in the environment.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | `charter synthesize --json` emits exactly one JSON document to stdout when `--json` is set, even when evidence warnings are produced. Warnings are placed inside the envelope (preferred) or routed to stderr; nothing non-JSON is written to stdout before, after, or interleaved with the envelope. | Pending |
| FR-002 | `charter synthesize --adapter fixture --json` success envelope includes the contracted fields `result`, `adapter` (containing `id` and `version`), `written_artifacts`, and `warnings`. Useful legacy fields (for example `target_kind`, `target_slug`, `inputs_hash`, `adapter_id`, `adapter_version`) may remain for compatibility, but the four contracted fields are mandatory. | Pending |
| FR-003 | `written_artifacts` is sourced from the actual staged-and-promoted artifact list returned by the write pipeline (typed staged-artifact entries or the real stage paths). It is never derived from `kind:slug` selectors or any other lossy reconstruction. For fresh-project seed mode, the already-known written file list is used. | Pending |
| FR-004 | The `--dry-run --json` envelope reports target paths identical to the paths a subsequent non-dry-run with the same inputs would write. Dry-run output is driven by typed staged-artifact entries, not from placeholder identifiers. | Pending |
| FR-005 | No user-visible CLI surface (stdout, stderr, JSON envelope, log line, error message) contains the placeholder string `PROJECT_000`. The placeholder remains an internal-only token. | Pending |
| FR-006 | The Charter epic golden-path E2E (`tests/e2e/test_charter_epic_golden_path.py`) asserts that every `kind=step` / issued-action envelope carries a `prompt_file` field (or documented public equivalent) with a value that is present, non-null, non-empty, and resolves to an existing prompt file on disk (test-project-relative path or absolute path that exists, or a documented shipped prompt artifact). | Pending |
| FR-007 | The same E2E permits a blocked decision to carry a non-empty `reason` instead of a prompt file. A blocked decision without a non-empty `reason` is a test failure. | Pending |
| FR-008 | `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` runs cleanly in the `e2e-cross-cutting` CI job: either `mypy` is available in that job environment and the test passes, or the test deterministically skips/fails with an actionable message that names the missing lint extra. The test no longer fails because `python -m mypy` is silently absent. | Pending |
| FR-009 | The retrospective and path-traversal regression guards remain intact: `runtime_bridge.py` gates retrospective emission before terminal completion (or uses a buffered emitter), blocked terminal completion does not emit `MissionRunCompleted` to the real sync emitter, `retrospective/schema.py` accepts uppercase/mixed-case contract IDs (for example `DIRECTIVE_NEW_EXAMPLE`, `PROJECT_001`) while still rejecting traversal, and `tests/next/test_retrospective_terminus_wiring.py` exercises the real opt-in runtime bridge with a recording emitter and asserts no completion event was emitted. Verification only — no rewrite unless a regression is observed. | Pending |
| FR-010 | The golden-path E2E continues to call `charter synthesize --json` against the real synthesizer (no hand-seeded `.kittify/doctrine`), `_parse_first_json_object` parses the full stdout via `json.loads(...)`, and `_run_next_and_assert_lifecycle` hard-fails when the lifecycle log is absent. Verification only — no rewrite unless a regression is observed. | Pending |
| FR-011 | After product fixes land and CI is green, GitHub issue hygiene is applied: `#844` is closed or commented with evidence only after FR-006 and FR-007 are merged; `#827` receives a comment naming exactly what this tranche closed and what remains; `#848` is updated if the mypy / uv-lock / environment issue is resolved or reclassified. `#827` and `#828` are not closed by this mission. | Pending |
| FR-012 | The mission produces exactly one PR against `Priivacy-ai/spec-kitty:main` from feature branch `fix/charter-827-contract-cleanup`, scoped to the `spec-kitty` repository only. | Pending |
| FR-013 | If the `Protect Main Branch` failure observed on the prior release merge is determined to be release-process hygiene rather than product-code-fixable, a GitHub issue is filed or updated to track it; otherwise it is fixed in this PR. The mission does not silently ignore the failure. | Pending |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | The required local test gate passes on the feature branch before PR open | All five commands listed in start-here.md §"Required Product-Repo Test Gate" exit 0: `uv run pytest tests/e2e/test_charter_epic_golden_path.py -q`; `uv run pytest tests/agent/cli/commands/test_charter_synthesize_cli.py tests/integration/test_json_envelope_strict.py tests/integration/test_charter_synthesize_fresh.py -q`; `uv run pytest tests/next/test_retrospective_terminus_wiring.py tests/retrospective/test_gate_decision.py tests/doctrine_synthesizer/test_path_traversal_rejection.py -q`; `uv run pytest tests/cross_cutting/test_mypy_strict_mission_step_contracts.py -q`; `uv run ruff check src tests` | Pending |
| NFR-002 | No regressions in CI checks that pass on current `main` | Every CI check that is green on `origin/main` at branch-cut time remains green on the PR head; net new failures are zero | Pending |
| NFR-003 | Test coverage for new code | Code added or modified in this mission carries automated test coverage at the repository's existing standard (90%+ line coverage for new/changed code, per the project policy summary) | Pending |
| NFR-004 | Strict type-check coverage for new and modified runtime code | `uv run mypy --strict` passes for all modified files in `src/specify_cli/cli/commands/charter.py` and `src/charter/synthesizer/write_pipeline.py` (if touched), and for `src/specify_cli/mission_step_contracts/executor.py` per the existing cross-cutting rule | Pending |
| NFR-005 | Hosted-surface command rule | 100% of commands in this mission's tests, fixtures, and examples that touch hosted auth, tracker, SaaS sync, or sync behavior are invoked with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` | Pending |
| NFR-006 | Single-PR scope discipline | The diff for this mission lives in exactly one PR; the PR touches files only inside the `spec-kitty` repository | Pending |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Single product-repo PR. Only the `spec-kitty` repository is modified in this mission. The sibling repos `spec-kitty-end-to-end-testing` and `spec-kitty-plain-english-tests` are not touched. | Active |
| C-002 | Out of scope: external E2E canaries (`#827` Tranche 3 in `spec-kitty-end-to-end-testing`), plain-English acceptance scenarios (in `spec-kitty-plain-english-tests`), end-user documentation parity (`#828`), and Phase 7 schema versioning / provenance hardening (`#469`). These are explicitly later tranches. | Active |
| C-003 | Verify-do-not-rewrite. Items in start-here.md §"Already Fixed, But Must Stay Covered" are validated by running their tests; their underlying production code is not rewritten unless the verification step actually fails. | Active |
| C-004 | The `Protect Main Branch` failure on the release merge may be release-process hygiene rather than product-code-fixable. If so, it is captured as a GitHub issue rather than fixed inside this PR. | Active |
| C-005 | Machine rule: any test or command path that touches hosted auth, tracker, SaaS sync, or sync behavior runs with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set. | Active |
| C-006 | Issue closure discipline. `#827` and `#828` are not closed by this mission. `#844` is only closed after FR-006 and FR-007 land. `#848` is updated only after the mypy/uv-lock/environment situation is resolved or reclassified. | Active |
| C-007 | Authoritative briefing source: `/Users/robert/spec-kitty-dev/spec-kitty-20260428-193814-MFDsf5/start-here.md`. Where this spec and start-here.md disagree on intent, start-here.md wins until the spec is updated through a documented decision. | Active |

## Success Criteria

- SC-001 A caller can pipe `spec-kitty charter synthesize --json` stdout straight into a JSON parser in 100% of fresh-project synthesize runs that previously emitted warnings, with zero parse errors caused by warning leakage.
- SC-002 An automated assertion proves that every `--adapter fixture --json` success envelope contains `result`, `adapter`, `written_artifacts`, and `warnings`; that assertion fails the build if any field is missing.
- SC-003 For every input where provenance yields a non-placeholder artifact ID, the dry-run reported target paths are byte-identical to the paths the non-dry-run writes; the placeholder `PROJECT_000` appears in zero user-visible outputs.
- SC-004 The Charter epic golden-path E2E fails in fewer than 30 seconds when an issued action lacks a resolvable prompt file, with a message that names the offending action and the missing/empty prompt path.
- SC-005 The `e2e-cross-cutting` CI job exits with status 0 on a PR branch built from current `main` plus this mission's changes, with no `python -m mypy: not found` errors recorded.
- SC-006 The required local test gate (NFR-001) passes locally on the feature branch before PR submission, captured as terminal evidence in the PR description.
- SC-007 GitHub issues `#844`, `#827`, and `#848` reflect post-mission status with evidence comments referencing this PR; `#827` and `#828` remain open.
- SC-008 The PR merges into `Priivacy-ai/spec-kitty:main` with all required CI checks green and zero net-new failing checks compared to current `main`.

## Key Entities

- **Synthesis envelope** — the strict JSON object emitted by `spec-kitty charter synthesize --json`. Contains `result`, `adapter`, `written_artifacts`, `warnings`, and may carry legacy compatibility fields. Authored in `src/specify_cli/cli/commands/charter.py`.
- **Staged artifact** — a typed entry returned by the synthesizer's write pipeline (`src/charter/synthesizer/write_pipeline.py`) describing the kind, identifier, and target path of a doctrine artifact that was staged or promoted. The envelope's `written_artifacts` list is derived from these entries.
- **Issued action envelope** — a runtime-emitted envelope of `kind=step` instructing the agent to perform a prompted action. Carries a prompt path field; consumed by the golden-path E2E.
- **Blocked decision envelope** — a runtime-emitted envelope that halts a step. Must carry a non-empty `reason`; may omit a prompt path.
- **Prompt file** — an on-disk markdown/text artifact pointed at by an issued action envelope. May be test-project-relative, absolute, or a documented shipped prompt artifact path.
- **Regression-guard test set** — `tests/next/test_retrospective_terminus_wiring.py`, `tests/retrospective/test_gate_decision.py`, and `tests/doctrine_synthesizer/test_path_traversal_rejection.py`. Verified, not rewritten.

## Assumptions

- A1 The `_parse_first_json_object` helper in the golden-path E2E currently uses `json.loads(stdout)` over the full stdout (per start-here.md verification list). This mission preserves that, but FR-001 also requires the producer side to emit strict JSON regardless.
- A2 The Charter synthesizer's write pipeline already returns a typed staged-artifact list (or can be extended to do so without changing public types). If the staged-artifact return shape needs to grow, edits to `src/charter/synthesizer/write_pipeline.py` are in scope.
- A3 The golden-path E2E builds a real test project where prompt files have predictable, resolvable paths; the assertion in FR-006 can therefore distinguish "prompt path is wrong" from "test project setup is broken."
- A4 The `Protect Main Branch` failure described in start-here.md is not caused by code in `src/`. If diagnosis proves otherwise, it is fixed in this PR (FR-013).
- A5 The agent has authority to file or update GitHub issues under the rules in C-006 and FR-013, including unsetting `GITHUB_TOKEN` to use keyring scopes when needed (per CLAUDE.md guidance).

## Out of Scope

- External end-to-end canaries in `spec-kitty-end-to-end-testing` (local-only and SaaS-enabled trusted-runner canaries) — `#827` Tranche 3.
- Plain-English acceptance scenarios in `spec-kitty-plain-english-tests` — `#827` Tranche 3.
- End-user documentation parity for the Charter epic — `#828`.
- Phase 7 schema versioning and provenance hardening — `#469`.
- Any change to repos other than `spec-kitty`.
- Any rewrite of regression-guard production code that is currently passing.

## Dependencies

- `gh` CLI authenticated for `Priivacy-ai/spec-kitty` (issue hygiene in FR-011, FR-013).
- `uv` available locally to run the test gate in NFR-001.
- The current `origin/main` HEAD as the baseline against which "no regressions" (NFR-002) is measured.
- The brief at `/Users/robert/spec-kitty-dev/spec-kitty-20260428-193814-MFDsf5/start-here.md` (per C-007).

## Decision Log

No deferred decisions at this time. No `[NEEDS CLARIFICATION]` markers were required: the user-supplied brief was comprehensive, and reasonable defaults were applied where the brief allowed (for example, choosing "warnings inside envelope" as the preferred FR-001 placement, with stderr permitted as an alternative).
