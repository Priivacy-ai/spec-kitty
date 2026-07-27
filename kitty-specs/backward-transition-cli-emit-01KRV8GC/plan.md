# Implementation Plan: CLI Backward-Transition Emit Path

**Branch**: `main` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)
**Mission ID**: 01KRV8GCG83GH1K12CWQ52SNW5 | **Mid8**: 01KRV8GC
**Input**: [kitty-specs/backward-transition-cli-emit-01KRV8GC/spec.md](./spec.md)

## Summary

Add a single backward-direction detection check at the existing emit boundary in `src/specify_cli/cli/commands/agent/tasks.py:move_task()`. When the user did NOT pass `--force` AND the requested `target_lane` precedes the current canonical lane in the forward order, the CLI auto-promotes `emit_force = True` and synthesizes a canonical reason string `"backward rewind: <from> -> <to>[: <feedback-ref>]"`. The change is local: ~30 lines of code in the hotspot region (lines 1700–1740) plus a private module-level helper next to `_lane_targets_for_emit`. New tests under `tests/cli/commands/` cover the four review-rejection family members, the forward-transition non-regression, the explicit-`--force` non-regression, and a wire-shape regression that loads Mission 1's `wp-status-changed-approved-rewind-valid` fixture from the `spec_kitty_events` package as the oracle.

## Technical Context

**Language/Version**: Python 3.11+ (charter: `Python 3.11+ (existing spec-kitty codebase)`)
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), pytest (tests), mypy --strict (typing), `spec_kitty_events` (consumed for `Lane` enum + conformance fixtures)
**Storage**: N/A — wire-shape change only; no persistence change
**Testing**: `uv run pytest tests/cli/commands tests/status -k "move_task or status or transition" -q` for the targeted run; `uv run pytest tests/ -q` for the full suite; `uv run ruff check src/specify_cli/` for lint; `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` (or the project's documented typing gate for this file) for typing; 90%+ coverage of new code per the charter's coverage policy
**Target Platform**: PyPI-published CLI (`spec-kitty`) consumed in any local repo with planning artifacts
**Project Type**: single (Python CLI)
**Performance Goals**: targeted-test runtime ≤ 30s wall-clock (NFR-001); full suite must not regress
**Constraints**: No wire-shape changes to `WPStatusChanged` payload (NFR-005, C-006); no mutation of 22 dev evidence events (C-004); backward-compat on explicit-`--force` path (FR-011, C-006); ≥90% coverage on new code (NFR-004)
**Scale/Scope**: ~30 LOC in hotspot + private helper + ~6 new test methods (≈ 200–250 LOC of tests). Touches one source file (`tasks.py`), adds ≤ 2 test files

## Charter Check

| Charter dimension | Status | Notes |
|---|---|---|
| Python 3.11+ + typer/rich/ruamel.yaml/pytest/mypy | ✅ Pass | No new dependencies; uses existing imports |
| 90%+ test coverage for new code | ✅ Pass plan | FR-008 + FR-009 tests cover both new code paths (backward branch + reason synthesis) |
| `mypy --strict` must pass | ✅ Pass plan | Reuses existing `Lane` enum + existing `resolve_lane_alias` helper — both are typed |
| Integration tests for CLI commands | ✅ Pass plan | FR-008 tests invoke `move-task` end-to-end against a synthetic in-memory feature dir |
| No agent-directory copies edited | ✅ Pass | `tasks.py` is in `src/specify_cli/`, not under `.claude/` / `.amazonq/` etc. |
| Shared-package boundary | ✅ Pass | Consumes `spec_kitty_events` via public imports (`from spec_kitty_events.status import Lane`); no vendoring |

Action doctrine (`plan` action) directives are satisfied by this plan + spec + research.md (Phase 0 below).

## Project Structure

### Documentation (this mission)

```
kitty-specs/backward-transition-cli-emit-01KRV8GC/
├── spec.md
├── plan.md                 # This file
├── meta.json
├── checklists/requirements.md
├── research.md             # Phase 0: hotspot + helper + fixture-load research
├── data-model.md           # Phase 1: variable + payload entity recap
├── quickstart.md           # Phase 1: sibling-mission consumer recipe (Mission 3)
└── contracts/
    └── auto-promote-backward-emit.md   # Phase 1: the local code contract
```

### Source Code (repository root)

```
src/specify_cli/
└── cli/commands/agent/
    └── tasks.py                         # MODIFY — hotspot lines 1700-1740 + add private helper

tests/cli/commands/
└── test_move_task_backward_emit.py      # NEW — FR-008 + FR-009 tests
```

**Structure Decision**: Single Python CLI package. All work is local to `src/specify_cli/cli/commands/agent/tasks.py` + a new test file. No new modules, no cross-module refactors.

## Implementation Strategy

### Approach

1. **Detect backward direction** at the existing emit boundary using the same canonical forward order already encoded inside `_lane_targets_for_emit`. Factor that order out as a private module-level constant (`_CANONICAL_FORWARD_ORDER`) so both the existing helper and the new detector reference it. This is the only restructuring; no behavior change to the existing helper.
2. **Add a private helper** `_is_backward_transition(current_lane: str, target_lane: str) -> bool` that returns True iff both lanes are in the canonical forward order AND the target index is strictly less than the current index. Returns False if either lane is outside the forward set (terminal-lane exits etc. remain explicit-`--force` territory per FR-007).
3. **Modify the hotspot** at lines ~1710-1712. Replace:
   ```python
   emit_force = force
   if not emit_reason:
       emit_reason = f"Force move to {target_lane}" if force else f"move-task: {old_lane} -> {target_lane}"
   ```
   with logic that:
   - Detects backward direction (helper above).
   - If user did NOT pass `--force` AND move is backward (FR-003): set `emit_force = True`, synthesize the canonical reason `"backward rewind: {old_lane} -> {target_lane}"` and append `": <feedback-ref>"` when a feedback URI is available (from `--review-feedback-file` or the rejected-review-result `review_ref`).
   - If user passed `--force` explicitly (FR-011): preserve today's `"Force move to <to>"` text.
   - If move is forward (FR-004): preserve today's `"move-task: <from> -> <to>"` text and DO NOT auto-promote.
4. **Backward transition_targets pruning** (FR-006). When the auto-promotion fires, the existing `transition_targets = _lane_targets_for_emit(old_lane, canonical_lane)` expansion at lines 1727-1729 returns `[target]` for non-forward pairs (current behavior; verified in research.md), so no change is required — but plan adds a regression test that confirms exactly one event is emitted for backward auto-promoted moves.
5. **Wire-shape regression test** (FR-009). Load `wp-status-changed-approved-rewind-valid` via `spec_kitty_events.conformance.load_fixtures("edge_cases")`. Drive `move_task()` for an `approved → planned` transition (synthetic feature dir, no `--force`). Capture the emitted event from `status.events.jsonl` (or via the test bridge already used by existing `tests/cli/commands/test_move_task_*` files). Assert `force`, `reason`-prefix, `from_lane`, `to_lane` match the fixture.

### Phase deliverables

| Phase | Output | Maps to |
|---|---|---|
| Phase 0 (research) | `research.md` resolving: exact existing helper behavior; feedback-ref source priority; test driver pattern; CHANGELOG/changelog policy | All FRs |
| Phase 1 (design) | `data-model.md`, `contracts/auto-promote-backward-emit.md`, `quickstart.md` | FR-001, FR-002, FR-005, FR-009 |
| Phase 2 (tasks) | `tasks.md` + WP files | All FRs |
| Phase 3 (implement) | Source + test edits | FR-001 through FR-012 |
| Phase 4 (review) | All gates green | NFR-001 through NFR-005, SC-001 through SC-005 |

### Risk + Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `_lane_targets_for_emit` semantics for backward pairs change subtly when refactoring | Low | Medium | Keep refactor surgical: only extract `_CANONICAL_FORWARD_ORDER` constant. Helper body unchanged. Regression test (FR-008e) verifies forward expansion unchanged. |
| The `--review-feedback-file` parameter name varies / is not always available on the `move_task` Typer signature | Medium | Low | Research.md step 2 confirms exact parameter name and how it threads to the emit block. If absent in some code paths (e.g. internal callers), synthesize the URI from `mission_slug`/`wp_id`/`timestamp` as a fallback. |
| Existing `emit_reason` may already be non-empty when arriving at line 1711 (some upstream branch set it) | Medium | Medium | Research.md confirms current control flow. The new logic only overrides when `not emit_reason` (preserve upstream-set reason on backward moves if they were intentional — the upstream branch knows more). The auto-promote `emit_force=True` still fires regardless. |
| A test that already asserts `force=False` on a backward move-task call (false negative under the old contract) | Medium | High — would fail | Research.md step 4 greps tests for assertions on `force=False` paired with backward lane targets. Any matches will be itemized for plan/tasks; if found, they get updated to reflect the new contract. |
| FR-009 regression test imports a fixture-by-id that doesn't resolve | Low | Medium | Mission 1 merged the fixture and manifest entry; verified by `spec-kitty-events` mission-review. Test confirms `load_fixtures("edge_cases")` succeeds and the id is present. |

### Cycle preview

Estimated WP shape after `/spec-kitty.tasks`:

- WP01 — Backward detector + emit-path fix (source change in `tasks.py`)
- WP02 — Family + wire-shape tests (`test_move_task_backward_emit.py` + any existing-test updates)

Two WPs, both small. WP01 owns the source; WP02 owns tests + verification gates. WP02 depends on WP01. Both can be authored in sequence in the same lane.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| (none) | — | — |

No charter violations. The change is the smallest possible local fix that satisfies the contract.
