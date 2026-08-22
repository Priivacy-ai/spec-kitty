# Tasks: Lane base honoring (M1, P0)

**Mission**: rc3-lane-base-honoring-01M0GGRC | **Issue**: #3571 (P0) | **Target**: `main`
**Planning base**: `main` | **Merge target**: `main`

This is an **atomic point-fix**: the `allocate_lane_worktree` / `create_lane_workspace` signature
change and every caller must land together, and all changes touch the same small set of core files
(`worktree_allocator.py`, `implement_support.py`, `implement.py`, `for_review_gate.py`,
`orchestrator_api/commands.py`). The ownership model (non-overlapping `owned_files`) and the coupling
make this a **single lane / single work package**. Red-first is mandatory (C-003, ADR 2026-07-17-1).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----|
| T001 | Red-first AC-1 seam-level test (RED on upstream/main; coord-fixture fidelity) | WP01 | |
| T002 | Thread `base: str\|None=None`; drop the `mission_branch=base` smuggle; record true honored parent | WP01 | |
| T003 | `UnhonorableBaseError(StructuredError)` + 4 pre-side-effect fail-loud sites (D3 reuse/recovery, D2/FR-009 dep-lane, FR-010 detached pre-create guard) + orchestrator except-tuple listing | WP01 | |
| T004 | Legacy route base substitution (C-005/FR-006); relocate+guard success print (FR-005); FR-008 docstring | WP01 | |
| T005 | FR-011 `for_review` gate reads the recorded honored base (+ no-regression coord default) | WP01 | |
| T006 | Tests: AC-2 legacy, AC-3 fail-loud (reuse/recovery/dep), AC-4 both-directions + silence | WP01 | |
| T007 | Tests: FR-010 detached atomicity, FR-011 gate (base + no-regression coord), NFR-004 envelope, FR-007 planning-warning | WP01 | |
| T008 | Rewrite `tests/cli/commands/test_implement_base_flag.py` (retire smuggle-assertion, unmock); gates (ruff/mypy/targeted) + swap-back proof | WP01 | |

---

## Work Packages

### WP01 — Thread `--base` into lane allocation; fail loud; honor base at the for_review gate

**Goal**: Make `implement --base <ref>` actually root a coord-topology lane on `<ref>` (root cause of
#3571), hard-error where the base cannot be honored, and make the `for_review` gate measure against the
lane's actual honored base. Preserve the legacy route (#1684) byte-for-byte on the `base=None` path.

**Priority**: P0 (release-blocking). **This is the MVP and the entire mission.**

**Independent test**: `PWHEADLESS=1 .venv/bin/python -m pytest tests/specify_cli/lanes/ tests/lanes/ tests/cli/commands/test_implement_base_flag.py -q` green after the fix; the AC-1 seam-level test is RED on `upstream/main` and GREEN after (swap-back proof).

**Included subtasks**: T001, T002, T003, T004, T005, T006, T007, T008

**Requirement coverage**: FR-001..011, NFR-001..005, AC-1..4 (see per-subtask map in the WP prompt).

**Implementation sketch**:
1. T001 — write the red-first seam-level AC-1 test first; confirm it is symptom-RED on `upstream/main`.
2. T002 — thread the explicit `base` param end-to-end; drop the smuggle; fix provenance recording.
3. T003 — add the typed error + the four pre-side-effect fail-loud guards.
4. T004 — legacy substitution + success-print relocation/guard + docstring.
5. T005 — for_review gate honored-base resolution.
6. T006–T008 — the remaining tests, the pre-existing-test rewrite, and the full gate + swap-back proof.

**Dependencies**: none (single WP).

**Risks**: legacy-route base starvation (mitigated by routing base through the topology-aware allocator);
dep-tip ancestry re-import (resolved by FR-009 fail-loud); detached-base atomicity (pre-create guard);
success-print over-firing (guard predicate); for_review no-regression (pin the default coord case).

**Estimated prompt size**: ~550 lines.

---

## MVP scope

WP01 is the whole mission — a single atomic P0 fix.
