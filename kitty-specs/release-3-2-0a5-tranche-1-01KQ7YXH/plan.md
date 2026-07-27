# Implementation Plan: 3.2.0a5 Tranche 1 — Release Reset & CLI Surface Cleanup

**Mission ID**: `01KQ7YXHA5AMZHJT3HQ8XPTZ6B` (mid8 `01KQ7YXH`)
**Mission Slug**: `release-3-2-0a5-tranche-1-01KQ7YXH`
**Mission Type**: software-dev
**Branch contract**: planning/base/merge target = `release/3.2.0a5-tranche-1` (`branch_matches_target = true`)
**Date**: 2026-04-27
**Spec**: [spec.md](./spec.md)
**Phase**: 1 — Design & Contracts (Phase 0 captured in [research.md](./research.md))

## Branch Strategy

- **Current branch at plan start**: `release/3.2.0a5-tranche-1`
- **Planning/base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target for completed changes**: `release/3.2.0a5-tranche-1`
- **branch_matches_target**: `true`

## Summary

Stabilization tranche of nine release-hygiene fixes for the 3.2.0a5
prerelease. Two of the nine FRs (FR-006 hidden-alias, FR-007 decision
command shape) are already correct in the tree and collapse to
"close-with-evidence" regressions; the other seven ship genuine code or
content changes. The largest WP is the `/spec-kitty.checklist` surface
removal (FR-003), which is bulk-edit-classified across 27 REMOVE files and
6 KEEP references. The riskiest WP is the FR-002 schema_version clobber
fix in the upgrade runner — root-caused during planning, fixed by a
two-line call-order swap plus a regression test.

## Technical Context

| Aspect | Decision |
|--------|----------|
| Language / runtime | Python `>=3.11` (loosened from hard pin `3.13`); `.python-version` becomes `3.11` to match `pyproject.toml::requires-python` |
| Tooling baseline (charter policy) | typer (CLI), rich (console), ruamel.yaml + pyyaml (YAML), pytest (tests), `mypy --strict` (types) |
| Test runner invocation | `PWHEADLESS=1 uv run --extra test pytest …` per `CLAUDE.md` (avoids opening browser windows) |
| Coverage target | 90%+ on new code (charter policy); existing untouched code stays untouched unless inside tranche scope |
| Type-check target | `uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py` (FR-001) and any module touched by FR-002 fix |
| Lint target | `uv run --extra lint ruff check .python-version pyproject.toml src/specify_cli tests` |
| Mode | `change_mode: bulk_edit` for FR-003 (`/spec-kitty.checklist` removal across 27 files); other FRs are localized fixes |
| Bulk-edit gate | DIRECTIVE_035 enforced via [`occurrence_map.yaml`](./occurrence_map.yaml) at the same level as `plan.md` |
| Git hygiene | Auto-commit per Spec Kitty git workflow (see `spec-kitty-git-workflow` skill); no `--no-verify` allowed |
| Tracker integration | Local-only; no SaaS sync calls. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` only when manually exercising hosted commands per `start-here.md` |

## Charter Check (Pre-Design)

Charter loaded via `spec-kitty charter context --action plan --json`. Source:
`/Users/robert/spec-kitty-dev/spec-kitty-20260427-190321-KGr7VE/spec-kitty/.kittify/charter/charter.md`.

| Check | Result | Notes |
|-------|--------|-------|
| **DIRECTIVE_003 — Decision Documentation** | PASS | Decision `01KQ7ZSQKT9DVH7B4GGXWS8DTW` recorded for FR-001; rationales for every FR captured in [research.md](./research.md). |
| **DIRECTIVE_010 — Specification Fidelity** | PASS | Plan derives all FR/NFR/C entries from `spec.md` directly; no fresh requirements introduced. |
| **DIRECTIVE_035 — Cross-File Rename Gate** | PASS (gated by occurrence_map) | `change_mode: bulk_edit` set; `occurrence_map.yaml` enumerates all 27 REMOVE + 6 KEEP occurrences across 8 standard categories. |
| Tooling baseline (typer/rich/ruamel.yaml/pytest/mypy) | PASS | No new top-level dependencies introduced by this tranche. Existing tools cover every fix surface. |
| 90%+ coverage on new code | PASS-by-construction | Each FR ships with at least one new or extended regression test (see [research.md](./research.md) and the WP draft below). |
| `mypy --strict` clean | PASS-by-construction | FR-001 explicitly restores it on `mission_step_contracts/executor.py`; FR-002 fix is two-line and stays inside an existing `mypy --strict`-clean module. |
| Integration tests for CLI commands | PASS-by-construction | E2E smoke tests in `tests/e2e/` extended for FR-005 (init non-git) and FR-008 (mission create clean output). |

## Phase 0 — Outline & Research

Captured in full in [research.md](./research.md). Headline outcomes:

| Item | Status | Smallest-blast-radius shape |
|------|--------|-----------------------------|
| R1 / FR-001 | Decided | `.python-version` → `3.11`; restore strict mypy run separately |
| R2 / FR-002 | Confirmed root cause | Swap `_stamp_schema_version` and `metadata.save` calls at `runner.py:163–164` + regression test |
| R3 / FR-003 + FR-004 | Mapped | 27 REMOVE / 6 KEEP enumerated in [`occurrence_map.yaml`](./occurrence_map.yaml); close #635 as superseded by #815 |
| R4 / FR-005 | Designed | Add one informational line on non-git target near existing "git not detected" branch in `init.py`; do NOT auto-`git init` |
| R5 / FR-006 | Already implemented | Add a single regression test that scans every CLI subcommand's `--help` for `--feature` |
| R6 / FR-007 | Already canonical | Add a single doc/help/snapshot consistency test for the `spec-kitty agent decision` shape |
| R7 / FR-008 + FR-009 | Designed | New `src/specify_cli/diagnostics/dedup.py` with a ContextVar gate + atexit success-flag for shutdown noise |
| R8 / NFR-002 | Decided | Bump `pyproject.toml` to `3.2.0a5`, split CHANGELOG into `[3.2.0a5]` + new `[Unreleased]`, run `tests/release/` |
| R9 / FR-010  | Confirmed root cause (added during `/spec-kitty.tasks`) | Duck-type-skip non-`wp_id` events at `read_events()` in `src/specify_cli/status/store.py:209` + regression test in `tests/status/` |

Two of ten FRs (FR-006, FR-007) collapse to "already fixed; add regression test" per `start-here.md` "Done Criteria". One (FR-010) was discovered live during `/spec-kitty.tasks` when `finalize-tasks` rejected the mission's own DecisionPoint event and was added to scope by user direction. Decision documentation in `spec.md` and `research.md` carries the audit trail.

## Phase 1 — Design & Contracts

### Data Model

This tranche has minimal data-model surface — most work is config files,
CLI output discipline, and removal of templates. The handful of meaningful
entities are captured in [data-model.md](./data-model.md) (project metadata
schema, occurrence-map schema, dedup state).

### Contracts

CLI behavior contracts capturing the testable invariants live in
[contracts/](./contracts/):

- [`upgrade_post_state.contract.md`](./contracts/upgrade_post_state.contract.md) — after `spec-kitty upgrade --yes` succeeds, `spec_kitty.schema_version` MUST be present in `.kittify/metadata.yaml` and downstream `agent` commands MUST NOT gate on `PROJECT_MIGRATION_NEEDED`.
- [`mission_create_clean_output.contract.md`](./contracts/mission_create_clean_output.contract.md) — after a successful `spec-kitty agent mission create --json`, the last stdout line is the closing `}` of the JSON payload, no red error styling appears, and no diagnostic prints repeat within the invocation.
- [`init_non_git_message.contract.md`](./contracts/init_non_git_message.contract.md) — `spec-kitty init` in a directory that is not inside a git work tree MUST emit one informational line directing the user to run `git init`, exactly once per invocation.
- [`decision_command_help.contract.md`](./contracts/decision_command_help.contract.md) — every doc/help/skill-snapshot reference to the decision command resolves to `spec-kitty agent decision { open | resolve | defer | cancel | verify }`. No `spec-kitty decision …` or `spec-kitty agent decisions …` survives.
- [`feature_alias_hidden.contract.md`](./contracts/feature_alias_hidden.contract.md) — every CLI subcommand `--help` output contains zero references to `--feature`. Existing call sites that pass `--feature` continue to work.
- [`checklist_surface_removed.contract.md`](./contracts/checklist_surface_removed.contract.md) — zero references to `/spec-kitty.checklist` across every supported agent's rendered surface; `kitty-specs/<mission>/checklists/requirements.md` still gets created by `/spec-kitty.specify`.
- [`status_event_reader_tolerates_decision_events.contract.md`](./contracts/status_event_reader_tolerates_decision_events.contract.md) — `read_events()` returns successfully for any `status.events.jsonl` containing a mix of lane-transition and mission-level events.

### Quickstart

End-to-end verification flow lives in [quickstart.md](./quickstart.md). It
is the operator-facing playback of every contract above.

### Bulk-Edit Occurrence Map

Materialized at [`occurrence_map.yaml`](./occurrence_map.yaml). Covers all
8 standard categories. Implementing agents MUST consult it before touching
any `/spec-kitty.checklist` reference.

## Charter Check (Post-Design)

| Check | Result | Notes |
|-------|--------|-------|
| DIRECTIVE_003 — Decision Documentation | PASS | All design decisions are anchored in `research.md` with rationale + alternatives; FR-001 has a Decision Moment id. |
| DIRECTIVE_010 — Specification Fidelity | PASS | Every contract in `contracts/` traces to one or more FR/NFR in `spec.md`; no contract introduces behavior outside the spec. |
| DIRECTIVE_035 — Cross-File Rename Gate | PASS | `occurrence_map.yaml` is exhaustive for FR-003 and explicitly classifies KEEP cases. |
| Tooling baseline | PASS | No new dependencies introduced. |
| 90%+ coverage on new code | PASS-by-construction | New tests listed below cover every code change; trivial fixes (FR-006, FR-007) ship with their own scanning regressions. |
| `mypy --strict` clean | PASS-by-construction | FR-001 explicitly restores it; FR-002 changes are two-line; FR-008/9 new module ships with type hints. |
| Integration tests for CLI commands | PASS-by-construction | New e2e tests in `tests/e2e/` for the contracts that are integration-shaped. |

## Premortem (DIRECTIVE-aligned)

Per `premortem-risk-identification` tactic, sabotage scenarios + mitigations:

1. **"FR-002 swap fix doesn't actually unblock the gate"** — Risk: the
   `_stamp_schema_version` raw-YAML round-trip might race with another
   write or fail silently if the file is missing. Mitigation: the regression
   test runs the full CLI smoke (`spec-kitty upgrade --yes` then
   `spec-kitty agent mission branch-context --json`) and asserts the second
   command exits 0. Plus a unit test that asserts the post-save file
   contains `schema_version`.
2. **"FR-003 occurrence map misses a hidden reference"** — Risk: the
   `/spec-kitty.checklist` string survives in a fixture or doc we didn't
   scan. Mitigation: the `checklist_surface_removed` contract is enforced
   by a recursive grep over `src/`, `tests/`, `docs/`, and every agent
   directory listed in `CLAUDE.md` "Supported AI Agents".
3. **"FR-009 ContextVar dedup leaks across tests"** — Risk: a test pollutes
   the dedup state for the next test. Mitigation: `dedup.py` exposes a
   `reset_for_invocation()` helper, and the new test fixture calls it in
   `setup`.
4. **"FR-008 atexit success-flag misfires for failure paths"** — Risk: a
   command that intends to fail still has `success=True` set due to a
   missed code path. Mitigation: the success flag is set only inside the
   final `--json` payload writer, after all decisions are made; failure
   paths short-circuit out before reaching it. The contract test asserts
   the warning still fires when the command fails.
5. **"Migration gate keeps biting in CI even after the fix"** — Risk: CI
   uses cached project state from before the fix. Mitigation: add a
   pyproject-level `tool.spec-kitty.required_schema_version` annotation in
   the dogfood command-set test fixture so any future migration that
   bumps schema is caught at test build, not at user runtime.

## Eisenhower Triage (drives WP order during `/spec-kitty.tasks`)

| Item | Importance | Urgency | Suggested order |
|------|------------|---------|-----------------|
| FR-002 schema_version fix + regression | High | High (blocks every other agent run) | **WP01** |
| NFR-002 release metadata bump | High | High (gates release-prep tests) | WP02 |
| FR-001 .python-version + strict mypy restore | High | Medium | WP03 |
| FR-003+FR-004 `/spec-kitty.checklist` bulk removal | High | Medium | WP04 (largest WP) |
| FR-005 init non-git message | Medium | Medium | WP05 |
| FR-008+FR-009 diagnostic noise (dedup + atexit success-flag) | Medium | Medium (visible noise) | WP06 |
| FR-006 hidden alias regression test | Low | Low | WP07 (close-with-evidence) |
| FR-007 decision shape consistency test | Low | Low | WP07 (close-with-evidence) |
| FR-010 status event reader robustness fix | High | High (blocks finalize-tasks for any mission that uses Decision Moment Protocol) | **WP08** (added live during /spec-kitty.tasks) |

`/spec-kitty.tasks` will materialize these into the actual WP files; the
above is a hint, not a contract.

## Out-of-Scope Reminders

- No new product features (per C-001).
- No removal/rename of `kitty-specs/<mission>/checklists/requirements.md`
  (per C-003).
- No SaaS / tracker repo cloning unless implementation proves it required
  (per C-006); no `SPEC_KITTY_ENABLE_SAAS_SYNC=1` execution unless the
  command genuinely needs it (per C-007).

## Stop Point

Phase 1 is complete. Per `/spec-kitty.plan` template:

> **YOU MUST STOP HERE.**
>
> Do NOT generate `tasks.md`, create work package files, create `tasks/`
> subdirectories, or proceed to implementation.
>
> The user will run `/spec-kitty.tasks` when they are ready to generate
> work packages.

**Branch contract restated for the final report**: planning/base/merge
target = `release/3.2.0a5-tranche-1`; `branch_matches_target = true`. The
mission lands on the same branch it was specified on.
