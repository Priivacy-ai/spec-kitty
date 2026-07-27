# Implementation Plan: Merge Done-Marking Surface Resolver

**Branch**: `main` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)
**Input**: `kitty-specs/merge-done-surface-resolver-01KTDVHZ/spec.md`
**Mission ID**: 01KTDVHZKGCHCW6HQ4V577PNES

---

## Summary

Introduce a single `resolve_status_surface(repo_root, mission_slug)` function in `src/specify_cli/coordination/` that returns the canonical `status.events.jsonl` path for a mission, accounting for coordination-branch topology. Wire both `_mark_wp_merged_done` and `_assert_merged_wps_reached_done` in `src/specify_cli/cli/commands/merge.py` to consume it, eliminating the write/read surface divergence that causes post-merge WPs to show `approved` (80%) instead of `done` (100%). Broaden the fix with a full merge-path audit (FR-005) and regression tests that exercise both functions without mocking them against a mission fixture that includes `coordination_branch`.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, mypy (--strict)
**Storage**: `status.events.jsonl` (append-only JSONL event log, one per mission)
**Testing**: pytest with 90%+ coverage on new code; integration tests for changed workflow boundaries; no mocking of `_mark_wp_merged_done` or `_assert_merged_wps_reached_done` in regression tests (C-004)
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Performance Goals**: Sub-millisecond surface resolution per WP (single `meta.json` read, no git I/O beyond existing)
**Constraints**: No circular imports (C-003); legacy missions without `coordination_branch` must be unaffected (C-002); `status.events.jsonl` schema unchanged (C-001)
**Scale/Scope**: Single-file fix in `merge.py` (~1797-1864 LOC range), one new function in `coordination/`, fixture additions to 2 existing test files, one committed audit artifact

---

## Charter Check

- **Python 3.11+**: Confirmed (project standard, DIR-002).
- **mypy --strict**: Required on all new code (DIR-006). The surface resolver must be fully type-annotated; `Path` return type, both parameters typed.
- **90%+ test coverage**: Required on new code (charter). Regression tests must cover both planning-only and code-change merge paths with `coordination_branch` set (FR-007, FR-008).
- **No security issues**: No credential or secret handling in this change. Paths only.
- **CHANGELOG.md entry required**: This is a behavioral fix; it must be documented in `CHANGELOG.md` (DIR-009 — breaking change for any caller that relied on the post-merge assertion silently passing when `coordination_branch` was set).
- **Terminology**: "Mission" (not "Feature") throughout all new code, comments, and docs (Terminology Canon).

**Gate: PASS** — no violations.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/merge-done-surface-resolver-01KTDVHZ/
├── plan.md              # This file
├── research.md          # Phase 0 output (Debbie five-paradigm synthesis)
├── data-model.md        # Phase 1 output (surface resolver interface)
├── contracts/
│   └── surface-resolver.md   # Function interface contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks)

Note: The FR-005 audit artifact is committed as an inline code comment in `src/specify_cli/cli/commands/merge.py` adjacent to the done-marking loop, not as a standalone file.
```

### Source Code (affected paths)

```
src/specify_cli/
├── coordination/
│   ├── status_transition.py     # existing — coord-branch routing (~lines 318, 334)
│   └── surface_resolver.py      # NEW — resolve_status_surface()
└── cli/
    └── commands/
        └── merge.py             # changed — wire resolver into _mark_wp_merged_done (line 223)
                                 #           and _assert_merged_wps_reached_done (line 348)

tests/
├── specify_cli/
│   └── cli/
│       └── commands/
│           └── test_merge.py    # changed — T015 section: add coord-branch fixtures (no mock)
└── merge/
    └── test_merge_done_recording.py   # changed — add coord-branch fixture (no mock)
```

---

## Phase 0: Research

**Status**: Complete — synthesized from five-paradigm investigation (Debbie invocation ID 01KTDTY8SEPEJMZQFJ2EF84W1M).

See [`research.md`](research.md) for the full synthesis.

Key findings that drive Phase 1 design:

1. **Write path confirmed**: `emit_status_transition_transactional` → `BookkeepingTransaction.acquire` → writes to `.worktrees/<slug>-<mid8>-coord/kitty-specs/.../status.events.jsonl`, committed to the coordination branch ref. Never touches primary checkout.
2. **Read-back path confirmed**: `_assert_merged_wps_reached_done` → `get_wp_lane` → `read_events` → `Path.read_text()` on primary checkout `kitty-specs/<slug>/status.events.jsonl`. Never consults coordination branch.
3. **Ordering compound confirmed**: Assertion fires at `merge.py:1797`; `safe_commit` (flush) is at `merge.py:1864`. The assertion structurally cannot see the write on the current path.
4. **No surface resolver exists**: Both `_mark_wp_merged_done` (line 223) and `_assert_merged_wps_reached_done` (line 348) call `resolve_feature_dir_for_mission` independently but diverge immediately after.
5. **Test gap confirmed**: Zero merge-related test files set `coordination_branch` in any fixture. All tests that call both functions live monkeypatch either `emit_status_transition_transactional` or `get_wp_lane`.
6. **Class recurrence confirmed**: #1589 facet 3 was the same class on the runtime read path. The fix was not propagated to the merge closeout path. No recurrence guard exists at that boundary.
7. **Planning-only path shares the same vulnerability**: The planning-artifact merge path flows through the same `_mark_wp_merged_done` / `_assert_merged_wps_reached_done` loop (lines 1782–1797). It is equally exposed.

---

## Phase 1: Design

**Status**: Complete — see [`data-model.md`](data-model.md) and [`contracts/surface-resolver.md`](contracts/surface-resolver.md).

### Design Decision: Surface Resolver Placement

The resolver is placed in `src/specify_cli/coordination/surface_resolver.py` because:
- It requires knowledge of `coordination_branch` from `meta.json` — the same topology metadata that `coordination/status_transition.py` already reads at lines 318/334.
- `merge.py` already imports from `coordination/` — no new import graph edges required.
- Placing it in `status/` would require `status/` to understand coordination topology, which is a cross-cutting concern that belongs in `coordination/`.
- Avoids circular imports: `coordination/ → status/` is an existing valid edge; reversing it is not.

### Design Decision: What the Resolver Returns

The resolver returns `Path` to the `status.events.jsonl` file on the canonical surface. The caller does not need to know whether that path is inside a coordination worktree or the primary checkout — the resolver encapsulates that decision. Both the `BookkeepingTransaction` write path and the `get_wp_lane` read path ultimately reference a `Path` object; the resolver provides that path.

### Design Decision: Ordering (AC3)

The fix does NOT reorder `safe_commit` relative to the assertion. Instead, the assertion is updated to read from the same surface as the write. Since both now use the resolver, and the write already resolves to the coordination worktree path, the assertion will also resolve there — making the ordering between assertion and `safe_commit` irrelevant. AC3 is satisfied structurally, not by reordering.

### Work Package Decomposition (for /spec-kitty.tasks)

| WP | Title | Scope | Dependencies |
|----|-------|-------|--------------|
| WP01 | Surface Resolver Implementation | New `src/specify_cli/coordination/surface_resolver.py` with `resolve_status_surface()`; unit tests; mypy clean | None |
| WP02 | Merge-Path Audit and Wire Resolver | ATDD failing test (T000); full merge-path audit (code comment in `merge.py`); wire resolver into `_mark_wp_merged_done` and `_assert_merged_wps_reached_done`; fix any additional sites found | WP01 |
| WP03 | Regression Tests | Add coord-branch fixtures to T015 and `test_merge_done_recording.py`; no mocking of the two functions; planning-only + code-change paths; ordering-independence test; 90%+ coverage | WP02 |
| WP04 | CHANGELOG and Final Gate | Write `CHANGELOG.md` entry; verify audit comment in `merge.py`; full suite gate; update spec.md FR statuses | WP03 |

Sequential pipeline: WP01 → WP02 → WP03 → WP04. No parallelism in this mission.
