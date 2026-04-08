# Implementation Plan: Mission Terminology Cleanup and Machine-Facing Alignment

**Mission Slug**: `077-mission-terminology-cleanup`
**Date**: 2026-04-08
**Spec**: [/private/tmp/241/spec-kitty/kitty-specs/077-mission-terminology-cleanup/spec.md](spec.md)
**Branch**: `main` (start), planning base `main`, merge target `main`, `branch_matches_target=true`

## Summary

Lock the canonical Mission Type / Mission / Mission Run terminology boundary into every operator-facing surface in the main CLI (Scope A — `#241`), then perform a gated machine-facing alignment cleanup of residual `feature_*` payloads (Scope B — `#543`). The technical approach is a small typer-agnostic selector-resolution helper that runs *after* typer parses arguments but *before* any business logic. Multi-alias `Option` declarations are removed; canonical and deprecated alias flags are declared as separate parameters and reconciled by the helper, which raises `typer.BadParameter` on dual-flag conflict and emits a hidden-style deprecation warning on legacy alias use. The orchestrator-api stays canonical-only and is not wired through the helper. Doctrine skills, agent-facing docs, and the inverse-drift sites (`--mission` used to mean blueprint/template) are updated in parallel work packages. CI grep guards prevent the drift from returning, scoped to live first-party surfaces only.

## Technical Context

**Language/Version**: Python 3.11+ (charter mandate; existing spec-kitty codebase requirement)
**Primary Dependencies**: `typer` (CLI framework, charter), `rich` (console output, charter), `pytest` (testing, charter), `mypy --strict` (type checking, charter)
**Storage**: None. This mission modifies CLI parameter declarations, helper modules, doctrine skill markdown, doc markdown, contract tests, and the existing `upstream_contract.json`. No persisted state changes. No new database tables. No new disk artifacts beyond the new helper module and the new contract-test file.
**Testing**: `pytest` with `≥ 90%` coverage on touched modules (charter + NFR-005). Existing CLI test harness uses `typer.testing.CliRunner` and `capsys`/`caplog`; new tests follow the same pattern. Headless test execution via `PWHEADLESS=1 pytest tests/` (project-level convention).
**Target Platform**: Linux, macOS, Windows 10+ (charter cross-platform requirement). The selector-resolution helper is pure Python with no platform-specific behavior.
**Project Type**: Single-project Python CLI library (`src/specify_cli/`).
**Performance Goals**: Selector resolution adds `< 5ms p95` to `mission current` cold-start vs validated baseline `54269f7c` (NFR-001). The helper is a constant-time check with at most one warning emit, no I/O.
**Constraints**:
- The orchestrator-api 7-key envelope at `src/specify_cli/orchestrator_api/envelope.py::make_envelope` must not be widened (C-010). The canonical key set at HEAD `35d43a25` is exactly: `contract_version`, `command`, `timestamp`, `correlation_id`, `success`, `error_code`, `data`. Any future change to this key set must come with a documented C-010 amendment in the same PR.
- No file under `kitty-specs/**` (other than `077-mission-terminology-cleanup/`) or under `architecture/**` may be modified (C-011).
- The `upstream_contract.json` file (`src/specify_cli/core/upstream_contract.json`) is the authoritative machine-readable list of forbidden CLI flags, payload fields, commands, and error codes for the orchestrator-api surface. It already lists `--feature` as a forbidden CLI flag for the orchestrator-api (`forbidden_cli_flags: ["--feature"]`). This mission does not modify the orchestrator-api section of that file.
- All §3.3 non-goals from the spec are locked: no `mission_run_slug`, no `MissionRunCreated` rename, no `kitty-specs/*/` directory rename, no `aggregate_type="MissionRun"`.
**Scale/Scope**: Verified blast radius from spec §8.3: 16 files in `src/specify_cli/**` mention `--feature`, 7 mention `mission-run`, 22 files under `src/specify_cli/cli/commands/**` declare some form of mission selector (verified during planning research). The new helper module is one file. The new contract-test file is one file with 9 grep guards. The doctrine/docs scope per FR-022 is `src/doctrine/skills/**` + `docs/**` (excluding `docs/migration/**`) + top-level `README.md` + top-level `CONTRIBUTING.md` + the Unreleased section of top-level `CHANGELOG.md`. Verified live drift in top-level `README.md` at lines 883 and 910 must be cleaned up; historical version entries in `CHANGELOG.md` are explicitly excluded.

## Charter Check

**GATE**: Must pass before Phase 0 research. Re-check after Phase 1 design.

The charter at `/private/tmp/241/spec-kitty/.kittify/charter/charter.md` was loaded at plan start. The most material section for this mission is the **Terminology Canon (Mission vs Feature)** policy, especially the Regression Vigilance addendum dated `2026-04-06`.

| Charter requirement | This plan satisfies it by | Status |
|---|---|---|
| **§Languages and Frameworks**: Python 3.11+, typer, rich, pytest, mypy --strict | Selector-resolution helper is pure Python typer-using code; warnings use Rich `Console(stderr=True)` matching the codebase pattern; all new tests are pytest. | ✅ Pass |
| **§Testing Requirements**: 90%+ coverage, mypy --strict, integration tests for CLI commands | NFR-005 requires ≥ 90% coverage on touched modules; new helper has full unit coverage; FR-006/FR-021 verified by integration tests against real typer CLI runners; all new code is type-annotated and mypy-strict-clean. | ✅ Pass |
| **§Code Quality**: 1 approval, CI checks must pass, pre-commit hooks must pass | Standard PR flow. No new pre-commit hooks introduced. | ✅ Pass |
| **§Terminology Canon → Hard-break policy**: "do not introduce or preserve `feature*` aliases ... when the domain object is a Mission" | The spec already excludes payload field renames and aggregate-type changes (locked non-goals §3.3 + C-001/C-006/C-008/C-009). For CLI flags, the charter explicitly carves out: "`--feature` is only acceptable as a hidden secondary alias." This plan implements exactly that — see Charter Reconciliation below. | ⚠️ Reconcile |
| **§Terminology Canon → Hyper-vigilance**: "Every PR that adds a new typer.Option ... MUST use --mission as the primary name. --feature is only acceptable as a hidden secondary alias." | The selector-resolution helper enforces this at the parameter-declaration level: canonical `--mission` is the primary parameter; `--feature` is a separate hidden parameter (`hidden=True` in its `typer.Option` declaration) that is reconciled by the helper. New PRs cannot accidentally re-introduce visible `--feature` because the contract test in §12.2 / new `tests/contract/test_terminology_guards.py` greps for visible `--feature` declarations and fails the build. | ✅ Pass (after reconciliation) |
| **§Terminology Canon → Authoritative contract**: "The upstream contract at `src/specify_cli/core/upstream_contract.json` lists `--feature` as a **forbidden CLI flag** for new code. This is authoritative." | This contract is structured by surface: the `orchestrator_api` key contains `forbidden_cli_flags: ["--feature"]`. The orchestrator-api surface already enforces this (verified at `tests/contract/test_orchestrator_api.py:164`). This plan does not modify that section. The plan does add a parallel main-CLI contract-test file that asserts the canonical state for the human-facing CLI, which is governed by the charter's "hidden secondary alias" carve-out, not by the orchestrator-api forbidden-list. | ✅ Pass |
| **§Architecture: Branch and Release Strategy → All new features target main** | This mission lands on `main` per the deterministic branch contract. | ✅ Pass |
| **§Local Docker Development Governance** | Not applicable. This mission does not touch `spec-kitty-saas`. | N/A |

### Charter Reconciliation (the one tension this plan resolves)

**The tension**: The spec §11.1 (which I authored before reading the charter in detail) describes `--feature` as a "deprecated compatibility alias" with stderr deprecation warnings, and treats it as a publicly visible flag during the migration window. The charter says `--feature` is acceptable only as a **hidden secondary alias** and that the upstream contract lists it as forbidden for new code.

**The resolution**: These are reconcilable, and the resolution does not require changing the spec's behavior — only being explicit about *visibility*. The hidden-alias approach satisfies both the charter and the spec:

1. The canonical parameter is `--mission`. Its `typer.Option` declaration is the only one that appears in `--help` output, examples, tutorials, doctrine skills, and reference docs.
2. The `--feature` alias is a **separate** `typer.Option` parameter declared with `hidden=True`. It is parsed by typer when present in argv but does not appear in `--help` output.
3. When `--feature` is provided, the selector-resolution helper emits exactly one yellow stderr warning (matching the existing precedent at `src/specify_cli/cli/commands/agent/mission.py:604`) that names `--mission` as the canonical replacement and points to the migration policy doc.
4. Help text, examples, tutorials, doctrine skills, and reference docs only ever mention `--mission`. There is no documentation surface that teaches `--feature` to a new user. Existing scripts that already pass `--feature` keep working but get a warning telling them to migrate.
5. The CI grep guards in `tests/contract/test_terminology_guards.py` enforce: zero non-hidden `--feature` declarations in CLI command files, zero `--feature` mentions in `src/doctrine/skills/**`, zero `--feature` mentions in `docs/**`. They do NOT scan `kitty-specs/**` or `architecture/**` (FR-022 + C-011).

This resolution will be reflected as a small clarifying edit to spec §11.1 during implementation (changing "deprecated compatibility alias" to "hidden deprecated compatibility alias") so the spec and charter use the same language. The behavior described in §11.1 is unchanged.

**Re-check after Phase 1 design**: See bottom of this file. ✅ Pass.

## Project Structure

### Documentation (this mission)

```
/private/tmp/241/spec-kitty/kitty-specs/077-mission-terminology-cleanup/
├── spec.md              # Already exists (post-review revised)
├── plan.md              # This file
├── research.md          # Phase 0 output (this command)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
│   ├── selector_resolver.md      # Helper interface contract
│   ├── deprecation_warning.md    # Deprecation warning text/format contract
│   └── grep_guards.md            # CI grep-guard contract
├── checklists/
│   └── requirements.md  # Already exists (post-review revised)
├── tasks/               # Phase 2 output (NOT created here)
└── meta.json            # Already exists
```

### Source Code (repository root)

The mission touches three areas of the existing codebase. No new top-level directories. The selector-resolution helper is a single new module under the existing CLI package.

```
src/specify_cli/
├── cli/
│   ├── selector_resolution.py    # NEW — the helper (FR-006, FR-007, FR-021, NFR-002)
│   └── commands/
│       ├── next_cmd.py            # MODIFY — drop multi-alias, hidden --feature
│       ├── mission.py             # MODIFY — drop multi-alias, hidden --feature, fix dual-flag bug (FR-006)
│       ├── agent/
│       │   ├── tasks.py           # MODIFY — 9 selector sites (drop --mission-run, hidden --feature)
│       │   └── mission.py         # MODIFY — inverse drift fix (--mission → --mission-type, line 488)
│       ├── charter.py             # MODIFY — inverse drift fix (--mission → --mission-type, line 67)
│       ├── lifecycle.py           # MODIFY — inverse drift fix (--mission → --mission-type, line 27)
│       └── … (other selector sites discovered by WPA1 audit)
├── core/
│   └── paths.py                   # NO CHANGE — require_explicit_feature stays as-is; the new helper calls it
├── orchestrator_api/              # NO CHANGE (C-010)
│   ├── commands.py                # NO CHANGE — already canonical
│   └── envelope.py                # NO CHANGE — 7-key envelope locked
└── core/
    └── upstream_contract.json     # NO CHANGE in orchestrator_api section

src/doctrine/skills/spec-kitty-runtime-next/
└── SKILL.md                       # MODIFY — drop --mission-run instructions

docs/explanation/
└── runtime-loop.md                # MODIFY — drop legacy selector teaching

# Top-level project docs (in scope per FR-022)
README.md                          # MODIFY — verified drift at lines 883 + 910 (--feature documented as live option)
CONTRIBUTING.md                    # SCAN — no known drift at HEAD 35d43a25, but in-scope per FR-022
CHANGELOG.md                       # SCAN Unreleased section only — historical version entries are excluded by FR-022 + C-011

tests/
├── contract/
│   ├── test_orchestrator_api.py   # NO CHANGE — already asserts --feature is rejected
│   └── test_terminology_guards.py # NEW — 9 CI grep guards (§12.2, FR-022, C-011-aware)
└── specify_cli/cli/commands/
    └── test_selector_resolution.py # NEW — unit + integration tests for the helper
```

**Structure Decision**: Single-project Python CLI. The new helper lives at `src/specify_cli/cli/selector_resolution.py` (one file, no submodule). The new contract-test file lives at `tests/contract/test_terminology_guards.py` and contains 9 grep guards (8 original + Guard 5b for top-level project docs). Inverse-drift sites and tracked-mission selector sites both call the same helper, parameterized for direction (canonical/alias names). No new top-level directories are introduced. Top-level project docs (`README.md`, `CONTRIBUTING.md`, and the Unreleased section of `CHANGELOG.md`) are explicitly in scope per FR-022 and have at least two verified drift sites in `README.md` that must be cleaned up; historical entries in `CHANGELOG.md` and all of `kitty-specs/**` and `architecture/**` are explicitly out of scope per the FR-022 carve-out and C-011.

## Complexity Tracking

Charter Check passes after the §Charter Reconciliation note. There is one acknowledged tension between the spec's original §11.1 wording and the charter's "hidden secondary alias" language; the reconciliation does not change behavior, only visibility, and is captured as a small clarifying edit to spec §11.1 during implementation. No other charter violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

## Phase 0: Outline & Research

Research artifact: [research.md](research.md)

The Phase 0 research resolved the following questions before Phase 1 design started:

1. **Q0.1** — Does an existing selector-resolution helper already do what this mission needs?
2. **Q0.2** — How does the existing codebase emit non-fatal CLI warnings to stderr?
3. **Q0.3** — How does typer behave when a single `Option` parameter declares multiple flag aliases, and is there a way to detect dual-flag conflict at the typer layer?
4. **Q0.4** — What is the authoritative scope of `src/specify_cli/core/upstream_contract.json` and how does this mission interact with it?
5. **Q0.5** — Is there already a `tests/contract/test_terminology_guards.py` or similar grep-guard file we should extend instead of creating a new one?
6. **Q0.6** — What is the precise list of inverse-drift sites (where `--mission` currently means "blueprint/template selector")?

All six questions are answered in `research.md`. There are no remaining `[NEEDS CLARIFICATION]` markers in the spec or in the technical context. The three open questions in spec §15 are explicitly deferred design choices, each with a recommended default; they are not Phase 0 blockers.

## Phase 1: Design & Contracts

Phase 1 outputs are complete and committed alongside this plan.

- **`data-model.md`** — Defines the helper's input/output dataclasses and the deprecation-warning event type. Pure in-memory; no persistence.
- **`contracts/selector_resolver.md`** — Python interface contract for the helper, including type signatures, error semantics, and the dual-flag conflict rule (FR-006).
- **`contracts/deprecation_warning.md`** — Exact deprecation warning text format, suppression env var contract, and the single-warning-per-invocation guarantee (NFR-002, NFR-003).
- **`contracts/grep_guards.md`** — CI grep guard contract: which patterns to grep for, which paths to scan, which paths to exclude, and what the failure messages must say (FR-022, C-011).
- **`quickstart.md`** — Implementer-facing walkthrough: clone, run failing tests, implement the helper, wire it through one command end-to-end, run full test suite.

### Agent Context Update

This mission introduces no new third-party dependencies and no new architectural concepts that require the agent context file to be regenerated. The charter already covers the canonical typer/rich/pytest/mypy stack. The mission's behavior is fully captured in the spec, plan, research, data-model, contracts, and quickstart. No CLAUDE.md regeneration is needed.

## Charter Re-Check (Post-Phase-1)

After completing Phase 1 design artifacts, the Charter Check is re-evaluated:

| Re-check item | Result |
|---|---|
| Hidden-alias reconciliation still holds after design | ✅ Yes — `contracts/selector_resolver.md` declares the canonical parameter and the `hidden=True` alias parameter as separate typer parameters; nothing in the contract requires a multi-alias declaration. |
| The new helper file does not introduce a new dependency | ✅ Yes — pure stdlib + typer + rich. |
| The new contract test does not scan `kitty-specs/**` or `architecture/**` | ✅ Yes — `contracts/grep_guards.md` explicitly lists the excluded paths. |
| The orchestrator-api section of `upstream_contract.json` is unchanged | ✅ Yes — the plan and contracts both note this as a hard constraint (C-010). |
| Spec §11.1 will need a small visibility-clarifying edit during implementation | ✅ Acknowledged — this is not a behavior change; it just renames "deprecated compatibility alias" to "hidden deprecated compatibility alias" to match charter language. |

**Charter Re-Check result**: ✅ Pass. No new gates raised by Phase 1 design.

## Branch Strategy Confirmation (2nd mention)

- Current branch at plan completion: `main`
- Planning/base branch: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target` = true

The next command (`/spec-kitty.tasks`) will run from this same branch. No worktree is created during planning; worktrees are created later by `spec-kitty implement WP##` after task finalization computes execution lanes.
