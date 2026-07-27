# Implementation Plan: Workflow Parity Fixes 988/989/991

**Branch**: `fix/workflow-parity-988-989-991` | **Date**: 2026-05-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/workflow-parity-988-989-991-01KRKTT5/spec.md`

## Summary

Three surgical fixes to make the preview/dry-run surfaces of the Spec Kitty CLI agree with their real counterparts:

1. **#988** — Teach `spec-kitty next --json` to share the canonical claim discovery used by `spec-kitty agent action implement`, so the JSON payload exposes a concrete `wp_id` when the explicit action would auto-claim one. When the claim path declines selection on purpose, surface a structured `selection_reason`.
2. **#989** — Treat a missing `baseline_merge_commit` as a hard fail for modern numbered missions in `spec-kitty review --mode lightweight`, with a structured error code and remediation guidance. Legacy/historical missions opt-in to the relaxed path via an explicit schema marker.
3. **#991** — Wire the existing real-merge review-artifact consistency gate into the `merge --dry-run` path so `REJECTED_REVIEW_ARTIFACT_CONFLICT` surfaces in both human and JSON output. Keep the success path of dry-run unchanged.

Each fix is paired with at least one regression test that fails before the fix and passes after it.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (strict)
**Storage**: Filesystem only (YAML/JSON frontmatter under `kitty-specs/<mission>/`)
**Testing**: pytest with focused suites for `merge`, `review`, `next`, `agent` CLI commands; mypy --strict; 90%+ test coverage for new code per charter
**Target Platform**: macOS / Linux CLI (developer + CI workstations)
**Project Type**: single (CLI library + tests)
**Performance Goals**: Added regression tests complete in under 5 seconds aggregate (NFR-002)
**Constraints**: No network access required by new tests; no `SPEC_KITTY_ENABLE_SAAS_SYNC` dependency (NFR-003); structured error codes must be greppable (NFR-004)
**Scale/Scope**: Three command surfaces touched (`next`, `review`, `merge`), each via a small wiring change reusing existing logic. Estimated under 400 LOC of production code change + new tests.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The charter (loaded via `charter context --action plan`) requires:

- **typer/rich/ruamel.yaml/pytest** stack — ✅ honored (no new deps).
- **mypy --strict** must pass — ✅ all new code will be fully typed; existing types reused.
- **pytest with 90%+ coverage for new code** — ✅ each fix introduces at least one regression test exercising the affected branch.
- **Integration tests for CLI commands** — ✅ the three regression tests are CLI-level (use the existing CLI runner harness).
- **DIRECTIVE_003 (Decision Documentation)** — ✅ this plan captures why each preview surface is being aligned to the real surface and the trade-off considered (lightweight legacy compatibility).
- **DIRECTIVE_010 (Specification Fidelity)** — ✅ FRs and SCs map 1:1 onto the three CLI surface changes; no deviation from spec is planned.

No gate violations. No `[NEEDS CLARIFICATION]` markers remain.

## Project Structure

### Documentation (this feature)

```
kitty-specs/workflow-parity-988-989-991-01KRKTT5/
├── plan.md              # This file (/spec-kitty.plan output)
├── research.md          # Phase 0 output (this command)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
└── tasks.md             # Phase 2 output (NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/
│   ├── merge.py                 # dry-run path — add review-artifact gate invocation (#991)
│   ├── review.py                # lightweight mode — add structured failure for missing baseline (#989)
│   └── next.py                  # next --json — call canonical claim discovery (#988)
├── next/                        # canonical claim/discovery primitives reused by next --json
├── agent/action/
│   └── implement.py             # source of canonical claim algorithm (read-only here)
├── merge/
│   └── preflight.py             # existing review-artifact consistency gate reused by dry-run
├── post_merge/
│   └── review_artifact.py       # existing real-merge consistency gate logic (read-only here)
└── status/                      # WP lane lookups (read-only here)

tests/
├── specify_cli/cli/commands/
│   ├── test_merge.py            # extended: dry-run regression for #991
│   ├── test_review.py           # extended: lightweight regression for #989
│   ├── review/test_mode_resolution.py  # mode-resolution coverage stays green
│   └── test_next.py             # extended: claimable wp_id regression for #988 (or test_next_json.py)
├── post_merge/
│   └── test_review_artifact_consistency.py  # stays green
└── agent/
    └── test_action_implement.py  # stays green
```

**Structure Decision**: Single-project layout, unchanged. All three fixes live inside the existing `src/specify_cli/cli/commands/` package by calling into already-existing helpers from `merge/`, `post_merge/`, and `next/`. No new top-level package or module is introduced.

## Complexity Tracking

No charter violations.
