# Implementation Plan: Merge Preflight Remote-State Boundary Separation

**Branch**: `main` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)
**Mission ID**: 01KTBE5MPD24VTVFHXKCF8MGHN
**Input**: `kitty-specs/merge-preflight-remote-state-boundary-separation-01KTBE5M/spec.md`

**Branch contract (confirmed twice per policy):**
- Current branch at plan start: `main`
- Intended planning/base branch: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target`: true ✓

---

## Summary

The merge command currently performs a live network fetch against `origin` and blocks local branch integration if the local target is not in sync with the remote. This is architecturally inverted: local merge is a domain-layer operation with no dependency on remote state; the remote-sync check is a publish-layer concern. The fix moves the remote-state fetch and push-safety check to a dedicated push-preflight module, corrects the `TargetBranchSyncStatus` safety predicate, gates the check on push intent at the call site, and adds a `push_requested` field to `MergeState` for correct resume semantics.

Research findings (Phase 0) confirm the exact change surface. Design artifacts (Phase 1) specify the updated value objects and new module interface.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI framework), pytest (testing), mypy (strict mode)
**Storage**: JSON state files at `.kittify/runtime/merge/<mission_id>/state.json`
**Testing**: pytest with ≥90% coverage for modified modules; mypy --strict must pass with zero new type errors; integration tests for CLI merge command
**Target Platform**: Linux, macOS, Windows (cross-platform per project policy)
**Project Type**: Single Python package (`src/specify_cli/`)
**Performance Goals**: Merge invocations without `--push` must perform no network I/O; push-gated fetch must add ≤3 seconds latency on a standard connection
**Constraints**: `MergeState` JSON schema change must be backwards-compatible (absent `push_requested` field → default `False`); no changes to WP-level `run_preflight()`; no changes to `forecast.py`, `status_resolver.py`, or lane resolution

---

## Charter Check

**Policy summary (from `.kittify/charter/charter.md`):**
- mypy --strict passes (no type errors)
- pytest 90%+ coverage for new code
- Integration tests for CLI commands
- Breaking changes documented in CHANGELOG.md

**Gate assessment:**
- ✅ New `push_preflight.py` module requires full type annotation coverage
- ✅ `MergeState.push_requested` field is backwards-compatible; not a breaking change
- ✅ Removing the "focused PR path" guidance from `AGENTS.md` is a documentation correction, not a user-visible breaking change
- ✅ CHANGELOG.md entry required for the behaviour change (local merge no longer blocked by origin sync state)
- ✅ Integration test required: `spec-kitty merge` must complete in an offline or diverged-state git fixture

No charter violations. All gates pass.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/merge-preflight-remote-state-boundary-separation-01KTBE5M/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (via /spec-kitty.tasks — not created here)
```

### Source Code (affected paths)

```
src/specify_cli/merge/
├── preflight.py                    # MODIFY: split is_safe predicate; scope docstring
├── push_preflight.py               # NEW: push-layer remote-state fetch + push-safety check
├── state.py                        # MODIFY: add push_requested field to MergeState
└── [all other files unchanged]

src/specify_cli/cli/commands/
└── merge.py                        # MODIFY: gate _enforce_target_branch_sync_preflight on push

tests/merge/
└── test_target_branch_preflight.py # MODIFY: invert ahead-blocked tests; add regression tests

architecture/3.x/adr/
└── 2026-06-05-1-merge-publish-layer-boundary.md   # NEW: ADR documenting the boundary decision

AGENTS.md                           # MODIFY: remove focused-PR-path workaround guidance
CHANGELOG.md                        # MODIFY: document behaviour change
```

**Structure Decision**: Single project layout. All changes are within the existing package. One new file (`push_preflight.py`) in the existing `merge/` package. One new ADR in `architecture/3.x/adr/`.

---

## Complexity Tracking

No charter violations. No complexity justification required.
