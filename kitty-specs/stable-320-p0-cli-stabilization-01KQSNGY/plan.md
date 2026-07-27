# Implementation Plan: 3.2.0 Stable P0 CLI Stabilization

**Mission ID**: `01KQSNGYG5B5AGH90CB81JEVMG`
**Mission slug**: `stable-320-p0-cli-stabilization-01KQSNGY`
**Branch**: `main`
**Date**: 2026-05-04
**Spec**: `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/spec.md`
**Input**: Mission specification from `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/spec.md`

## Summary

This mission prepares the Spec Kitty CLI for stable `3.2.0` by closing four P0 stabilization gaps:

- #967: status bootstrap and emit tests can hang.
- #904: a latest rejected review-cycle artifact can coexist with approved or done WP state.
- #968: retired `checklist` command leftovers can leave active registries, generated assets, and counts inconsistent.
- #964: generated skill files can miss required YAML frontmatter.

The technical approach is deliberately targeted: inspect the current implementation seams for each issue, add focused regression coverage first where practical, fix the smallest reliable boundary, and validate the combined command/skill surface with fresh local generation evidence. The review-state fix uses the product decision from the spec: fail closed by default and require durable structured override evidence for intentional supersession.

## Technical Context

**Language/Version**: Python 3.11+ for CLI and library code.
**Primary Dependencies**: Typer for CLI commands, Rich for console output, ruamel.yaml for frontmatter parsing, pytest for regression tests, mypy strict mode for typed code paths.
**Storage**: Repository-local Markdown/YAML frontmatter artifacts, JSON/JSONL status artifacts, generated command/skill files, and git-tracked mission artifacts.
**Testing**: Focused pytest suites for status, review consistency, post-merge/merge preflight, runtime command inventory, skill generation, and installer cleanup; ruff over touched source and tests; mypy strict checking over the project type-check gate.
**Target Platform**: Cross-platform CLI on Linux, macOS, and Windows 10+.
**Project Type**: Single Python CLI/library repository.
**Performance Goals**: Previously hanging status paths fail or finish within 30 seconds during validation; typical CLI operations remain under the charter target of 2 seconds for representative projects.
**Constraints**: No hosted auth, tracker, SaaS sync, or network requirement for default tests. Any intentional hosted sync path on this computer must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
**Scale/Scope**: Four scoped P0 issues only; expected implementation touches status tests/runtime seams, review artifact consistency, command/skill registry and installer surfaces, and generation tests.

## Branch Contract

- Current branch at plan start: `main`
- Intended planning/base branch: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target`: `true`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter area | Plan response | Gate |
|---|---|---|
| Python 3.11+ and project dependency stack | Plan stays inside the existing Python CLI and uses Typer, Rich, ruamel.yaml, pytest, and existing project utilities. | PASS |
| Testing standards | Each scoped issue gets focused regression coverage. Status hang validation runs with a 30-second timeout. CLI command behavior gets integration-style coverage where command surfaces change. | PASS |
| Type checking and linting | New typed seams should satisfy strict typing where touched; final validation includes `uv run ruff check src tests` and `uv run mypy --strict src/specify_cli src/charter src/doctrine`. | PASS |
| CLI performance | Status hang mitigation must bound tests without weakening runtime semantics; no broad runtime rewrite is planned. | PASS |
| Cross-platform support | Avoid POSIX-only assumptions in timeout, file-lock, path, and generated asset logic; prefer existing project abstractions. | PASS |
| User customization preservation | Checklist cleanup must remove only package-managed stale files or ignore unknown files safely; name-based deletion alone is not acceptable. | PASS |
| Branch terminology | Artifacts name actual branch values and use repository root checkout terminology. | PASS |
| Mission terminology | New operator-facing language uses Mission terminology and avoids legacy domain aliases. | PASS |
| SaaS contract boundary | Mission does not alter hosted routes, auth, tracker control plane, sync protocols, or `spec-kitty-saas`. | PASS |

No charter violations are expected. If implementation discovers a need to alter hosted contracts, broaden cleanup heuristics, or redesign status/runtime behavior, that must stop the mission for review before proceeding.

## Project Structure

### Documentation

```text
/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── command-surface-generation.md
│   ├── review-verdict-consistency.md
│   └── status-test-boundedness.md
├── checklists/
│   └── requirements.md
└── tasks/
```

### Source Code

```text
/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/
├── src/
│   ├── specify_cli/
│   │   ├── cli/commands/
│   │   ├── post_merge/
│   │   ├── review/
│   │   ├── runtime/
│   │   ├── shims/
│   │   ├── skills/
│   │   └── status/
│   └── doctrine/
│       └── skills/
└── tests/
    ├── post_merge/
    ├── review/
    ├── runtime/
    ├── specify_cli/
    ├── status/
    └── tasks/
```

**Structure Decision**: Use the existing single-repository CLI layout. Do not introduce new top-level packages for this stabilization mission. Add narrow helper modules only if existing modules lack a testable seam for review-verdict consistency or generated asset inventory checks.

## Phase 0: Research Decisions

Research output is captured in `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/research.md`.

Key decisions:

1. Status hang work begins with deterministic reproduction and fixture/runtime boundary inspection before code changes.
2. Review verdict consistency uses latest-artifact semantics and fails before mutation unless durable override evidence exists.
3. Checklist retirement cleanup treats package ownership as a hard safety boundary.
4. Generated skill frontmatter is verified through fresh generation tests rather than snapshot-only assertions.

## Phase 1: Design And Contracts

Design output:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/data-model.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/status-test-boundedness.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/review-verdict-consistency.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/command-surface-generation.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260504-101120-ahKkaN/spec-kitty/kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/quickstart.md`

No network API contracts are introduced. Contracts are CLI/artifact behavior contracts because this mission changes local command, status, review, and generated asset behavior only.

## Workstream Plan

### WP01 Status Test Hang Stabilization

- Reproduce or inspect #967 with `tests/status` under a 30-second timeout.
- Identify whether the hang comes from bootstrap setup, event emission, background sync, event-loop lifecycle, file locking, or fixture teardown.
- Fix at the smallest reliable boundary.
- Add regression coverage and diagnostics so future hangs produce actionable failure output.

### WP02 Review Verdict Consistency Gate

- Locate all state transitions that can move a WP to `approved` or `done`.
- Define a reusable latest-review-cycle lookup and contradiction check if no existing helper is sufficient.
- Block unsafe transitions before mutation.
- Extend mission status, mission review, and merge preflight diagnostics to reject or block done/approved WPs contradicted by latest rejected artifacts.
- Add explicit override input and durable override record semantics.

### WP03 Retired Checklist Command Cleanup

- Inventory active command registries, packaged templates, generated command counts, runtime doctor expectations, installer cleanup, and docs/comments that mention active counts.
- Remove retired `checklist` from active surfaces.
- Preserve cleanup or ignore behavior for stale package-managed `spec-kitty.checklist*` files.
- Add fresh generation/inventory tests proving agreement.

### WP04 Generated Skill Frontmatter

- Identify the generator path for Codex/global `.agents/skills/.../SKILL.md`.
- Ensure generated skills include host-required YAML frontmatter, including the #964 `spec-kitty.advise` repro.
- Add tests that inspect generated skill files, not only template snapshots.

### WP05 Fresh Surface Smoke And Release Evidence

- Run focused status tests with timeout.
- Run review consistency/post-merge/tasks tests selected by touched files.
- Run runtime/specify_cli generation and installer tests selected by touched files.
- Run ruff over `src` and `tests`.
- Run the repo type-checking gate: `uv run mypy --strict src/specify_cli src/charter src/doctrine`.
- Capture final evidence suitable for closing #967, #904, #968, and #964.

## Risk And Mitigation

| Risk | Mitigation |
|---|---|
| Timeout masks the real status hang | Require root-cause diagnosis or a narrowly justified fixture/adapter isolation fix; do not weaken status semantics. |
| Review gate mutates state before failing | Tests must assert failed rejected-verdict transitions leave WP state unchanged. |
| Override path becomes a silent bypass | Override must be explicit and durably recorded as structured state before transition acceptance. |
| Checklist cleanup deletes user-authored commands | Cleanup must prove package ownership or preserve and warn. |
| Count cleanup misses a consumer registry | Fresh generation tests must compare active registry entries, packaged templates, generated output, and diagnostics. |
| Skill frontmatter fix only updates one template | Tests must inspect generated `SKILL.md` files across the relevant generated surface. |
| JSON stdout regressions | JSON-producing command tests must parse stdout and keep warnings on stderr or structured diagnostics. |

## Complexity Tracking

No charter violations are planned. The mission uses existing repository structure and existing test tools. Any new abstraction must be justified by multiple call sites or by preventing duplicated review-verdict consistency logic across mutation and preflight paths.
