# Implementation Plan: Charter Contract Cleanup Tranche 1

**Mission ID:** `01KQATS4HJS0HY02VF05FCP57T`
**Mission slug:** `charter-contract-cleanup-tranche-1-01KQATS4`
**Mid8:** `01KQATS4`
**Mission type:** software-dev
**Branch contract:** current=`main` · planning/base=`main` · merge target=`main` · `branch_matches_target=true`
**Date:** 2026-04-28
**Spec:** [spec.md](./spec.md)
**Research:** [research.md](./research.md)
**Data model:** [data-model.md](./data-model.md)
**Contracts:** [contracts/](./contracts/)
**Quickstart:** [quickstart.md](./quickstart.md)

---

## Summary

Land one PR against `Priivacy-ai/spec-kitty:main` from `fix/charter-827-contract-cleanup` that closes four user-visible contract gaps and one CI hygiene gap on the Charter epic:

1. `charter synthesize --json` becomes strict-JSON on stdout and exposes a contracted `{result, adapter, written_artifacts, warnings}` envelope sourced from real staged-artifact entries (FR-001, FR-002, FR-003).
2. Dry-run paths match real-run paths byte-for-byte; no user-visible output contains the placeholder `PROJECT_000` (FR-004, FR-005).
3. The Charter epic golden-path E2E asserts `prompt_file` is non-null and resolves to an existing prompt artifact for issued actions, and that blocked decisions carry a non-empty `reason` (FR-006, FR-007 — closes `#844`).
4. The `e2e-cross-cutting` CI job installs the `lint` extra so `python -m mypy` is on PATH and `tests/cross_cutting/test_mypy_strict_mission_step_contracts.py` exercises its real strict-typing contract (FR-008 — touches `#848`).
5. Verify-do-not-rewrite the retrospective and path-traversal regression guards (FR-009, FR-010, C-003).
6. Apply post-merge GH issue hygiene against `#844`, `#827`, `#848`. `#827`, `#828`, `#469` remain open as later tranches (FR-011, FR-013, C-002, C-006).

External E2E (`spec-kitty-end-to-end-testing`), plain-English acceptance (`spec-kitty-plain-english-tests`), end-user docs (`#828`), and Phase 7 schema/provenance hardening (`#469`) are explicit later tranches and are out of scope.

## Technical Context

**Language/Version:** Python 3.11+ (`spec-kitty` repo)
**Primary Dependencies:** typer (CLI), rich (console), ruamel.yaml (YAML), pytest (test), mypy (strict typing)
**Storage:** Filesystem only (`.kittify/charter/`, `kitty-specs/`); no DB
**Testing:** pytest with the existing fast/slow/e2e/cross-cutting partition; `uv run pytest`. Lint: `ruff`. Type check: `mypy --strict`.
**Target Platform:** CLI on Linux/macOS; CI on `ubuntu-latest` (`.github/workflows/ci-quality.yml`)
**Project Type:** single-project Python CLI
**Performance Goals:** N/A — contract correctness, not perf
**Constraints:**

- Single-PR scope. Only the `spec-kitty` repo is modified (C-001).
- Hosted-surface commands run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (C-005, NFR-005).
- 90%+ test coverage on new/changed code (NFR-003).
- `mypy --strict` passes on every modified runtime file (NFR-004).
- No regressions in CI checks that pass on current `main` (NFR-002).

**Scale/Scope:** Targeted, surgical. Likely-touched runtime files: 1 (charter CLI command). Possibly-touched runtime files: 1 (synthesizer write pipeline, only if staged-artifact return shape must grow). Test files touched: 5–7. CI workflow files touched: 1 (single-line install-extras change). No new entities, no schema migrations, no public API additions beyond the now-formalised `--json` envelope.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter file present at `.kittify/charter/charter.md`. Action doctrine for `plan` loaded via `spec-kitty charter context --action plan` (DIRECTIVE_003 Decision Documentation, DIRECTIVE_010 Specification Fidelity, plus tactics: adr-drafting-workflow, eisenhower-prioritisation, premortem-risk-identification, problem-decomposition, requirements-validation-workflow, review-intent-and-risk-first, stakeholder-alignment).

| Charter clause | Compliance status | Notes |
|---|---|---|
| **Required dependencies (typer, rich, ruamel.yaml, pytest, mypy)** | ✅ Pass | No new runtime dependencies introduced. The mission uses `mypy` and `pytest` already named in the charter. |
| **`mypy --strict` must pass** | ✅ Pass | NFR-004 binds modified runtime files; FR-008 ensures the `e2e-cross-cutting` CI job actually exercises the contract on every push. |
| **`pytest` with 90%+ test coverage for new code** | ✅ Pass | NFR-003 binds the threshold to all new/changed code. |
| **Integration tests for CLI commands** | ✅ Pass | New/hardened assertions in `tests/integration/test_json_envelope_strict.py`, `tests/integration/test_charter_synthesize_fresh.py`, and `tests/agent/cli/commands/test_charter_synthesize_cli.py` cover the synthesize CLI integration path. |
| **DIRECTIVE_003 — Decision Documentation Requirement** | ✅ Pass | One Decision Moment opened (`01KQAVR8S1299R9N67BTFAD67Q`) and resolved for the mypy CI policy. Captured in research.md R-006 and the decisions index. No undocumented material decisions. |
| **DIRECTIVE_010 — Specification Fidelity Requirement** | ✅ Pass | Plan derives FR-by-FR from spec.md; deviations would require a documented amendment. None proposed. |

**No charter violations.** No `Complexity Tracking` justification needed.

**Re-evaluation after Phase 1 design:** still passes — design artifacts (data-model, contracts, quickstart) align with the directives and tactics; no new dependencies, no schema breaks beyond formalising the already-expected `--json` envelope shape.

## Project Structure

### Documentation (this feature)

```
kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/
├── plan.md                                          # this file
├── spec.md                                          # mission spec
├── research.md                                      # Phase 0 (R-001 .. R-010)
├── data-model.md                                    # Phase 1 — entities + invariants
├── contracts/
│   ├── README.md
│   ├── synthesis-envelope.schema.json               # JSON Schema for charter synthesize --json stdout
│   ├── golden-path-envelope-assertions.md           # E2E test contract
│   └── ci-job-mypy-availability.md                  # e2e-cross-cutting environment contract
├── quickstart.md                                    # verification recipe (NFR-001 commands, etc.)
├── checklists/
│   └── requirements.md                              # spec quality checklist (passed)
├── decisions/
│   └── DM-01KQAVR8S1299R9N67BTFAD67Q.md             # mypy CI policy decision (resolved)
└── tasks/                                           # Phase 2 output — NOT generated by /spec-kitty.plan
```

### Source Code (repository root)

This mission does not introduce new top-level packages. It modifies a small set of existing files:

```
src/
├── specify_cli/
│   └── cli/
│       └── commands/
│           └── charter.py                          # FR-001..FR-005 (likely-touched)
└── charter/
    └── synthesizer/
        └── write_pipeline.py                        # FR-003 only if staged-artifact return shape must grow

tests/
├── agent/cli/commands/
│   └── test_charter_synthesize_cli.py              # FR-001, FR-002 assertions
├── integration/
│   ├── test_json_envelope_strict.py                # FR-001 strict-stdout regression
│   └── test_charter_synthesize_fresh.py            # FR-002 envelope shape on fresh seed
├── charter/synthesizer/
│   └── test_<...>.py                                # FR-003, FR-004, FR-005 (new or hardened)
├── e2e/
│   └── test_charter_epic_golden_path.py            # FR-006, FR-007
├── cross_cutting/
│   └── test_mypy_strict_mission_step_contracts.py  # exercises FR-008 contract — not modified by this mission
├── next/test_retrospective_terminus_wiring.py      # verify-only (FR-009)
├── retrospective/test_gate_decision.py              # verify-only (FR-009)
└── doctrine_synthesizer/test_path_traversal_rejection.py  # verify-only (FR-009)

.github/
└── workflows/
    └── ci-quality.yml                              # FR-008: install extras change in e2e-cross-cutting job
```

**Structure Decision:** Single-project Python CLI. The mission stays inside the existing `src/specify_cli/`, `src/charter/`, `tests/`, and `.github/workflows/` layout. No restructuring.

## Phase 0 Output Summary

See [research.md](./research.md). Ten resolved entries (R-001 … R-010). One Decision Moment opened and resolved (mypy CI policy → install `lint` extra). Zero `[NEEDS CLARIFICATION]` markers remaining.

Highlights:

- **R-001/R-002/R-003** define the strict-JSON envelope contract and the typed `WrittenArtifact` shape; both bind FR-001/2/3.
- **R-004** binds dry-run/non-dry-run path parity to a single derivation function and the `PROJECT_000` exclusion.
- **R-005** defines the golden-path E2E assertion shape (issued action vs. blocked decision).
- **R-006** records the resolved mypy CI policy.
- **R-007** binds C-003 to a verify-only protocol with explicit re-classification rule on regression.
- **R-008** binds FR-013 (Protect Main Branch failure) to a diagnose-then-classify rule.
- **R-009/R-010** operationalise the SaaS-sync env-var rule and the post-merge issue-hygiene cadence.

## Phase 1 Output Summary

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md).

- **Six entities** captured: `SynthesisEnvelope`, `AdapterRef`, `WrittenArtifact`, `IssuedActionEnvelope`, `BlockedDecisionEnvelope`, `MissionStepContractsExecutorTypingClaim`.
- **Three contracts** authored:
  - JSON Schema for the synthesize envelope (success and dry-run; legacy fields permitted; `PROJECT_000` excluded).
  - Markdown contract for the E2E test's envelope assertions (issued action requires resolvable prompt; blocked decision requires non-empty reason).
  - Markdown contract for the `e2e-cross-cutting` CI job's mypy availability requirement.
- **Eight cross-cutting validation rules** (V-001 … V-008) mapping spec FRs to test surfaces.
- **Quickstart recipe** captures the five-command local test gate (NFR-001), strict-typing checks on touched files (NFR-004), the `PROJECT_000` regression sweep (FR-005), the SaaS-sync rule (NFR-005), CI verification, and post-merge issue hygiene.

## Risk Register & Pre-mortem (selected)

Per `premortem-risk-identification` tactic. The most plausible failure modes and their mitigations:

| Risk | Likelihood | Mitigation |
|---|---|---|
| Implementing FR-003 requires deeper changes to `write_pipeline.py` than expected, blowing scope | Med | Explicitly scoped in spec FR-003 and quickstart §7. The agent runs the verify-only suite first to fingerprint the current return shape; if it already carries enough provenance, `write_pipeline.py` stays untouched. If not, the extension is additive (new field on existing dataclass / typed entry) and remains a single-PR diff. |
| FR-006 prompt-file resolvability assertion is too strict and breaks legitimate runtime envelopes | Low-Med | The contract in `contracts/golden-path-envelope-assertions.md` allows three resolvability shapes (relative, absolute, documented shipped artifact) and permits multiplexing across stable field names. The agent runs the test against real synthesizer output before final commit. |
| The `Protect Main Branch` failure turns out to be a real product-code bug | Low | FR-013 + R-008 cover both branches: fix-here vs. file-issue. The plan does not pre-commit to either path. |
| Adding `lint` extra to `e2e-cross-cutting` materially extends CI runtime | Low | The `lint` extra adds `mypy`, `ruff`, type stubs, `bandit`, `pip-audit`, `cyclonedx-bom`. Only `mypy` is invoked by tests in this job; the others are dormant. Runtime impact = mypy invocation + a few seconds of pip install. |
| Verification step finds a regression in the "verify-only" guards | Low-Med | C-003 explicitly says: if a regression is observed, it becomes in-scope. The mission already has the FR slots (FR-009, FR-010) to absorb that without re-planning. |
| GH `gh` CLI fails on org-scoped issue ops | Low | CLAUDE.md prescribes `unset GITHUB_TOKEN`. Quickstart §6 documents this. |

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified.*

No charter violations identified. Section intentionally empty.

## Branch Contract (re-statement, per command requirement)

- **Current branch at workflow start:** `main`
- **Planning/base branch:** `main`
- **Final merge target:** `main`
- **`branch_matches_target`:** `true`

The eventual feature branch `fix/charter-827-contract-cleanup` is created at `/spec-kitty.implement` time. Planning artifacts commit to `main`.

## Stop Point

Phase 1 complete. The next operator action is `/spec-kitty.tasks`, which generates the work-package breakdown. **`/spec-kitty.plan` MUST NOT proceed to task generation.**
