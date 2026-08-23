---
affected_files: []
cycle_number: 1
mission_slug: reject-cyclic-lane-graphs-01M0QCK4
reproduction_command:
reviewed_at: '2026-08-23T16:21:21Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Review Feedback — Cycle-selection tests are not mutation-resistant

## Blocking finding

The production implementation correctly sorts traversal roots and neighbors, and all required focused checks currently pass. However, the test intended to prove lexical root selection is vacuous:

- `test_selects_first_cycle_by_sorted_root_and_neighbor_traversal` inserts roots in non-lexical order, but every inserted root leads into the same connected component. Starting at the first inserted root (`lane-e`) still reaches `lane-a` and selects the expected `lane-a -> lane-b -> lane-c -> lane-a` cycle.
- `test_mapping_and_set_insertion_order_do_not_change_cycle` contains only one cycle. Any root traversal order therefore normalizes to the same result.

Consequently, an implementation that traverses mapping insertion order instead of lexical root order can still pass the WP01 tests. This leaves FR-009 and T001's explicit “first encountered by sorted root and neighbor traversal” contract inadequately guarded.

## Required remediation

1. Add a detector test with at least two **disconnected** directed cycles. Insert the lexically larger cycle first, then assert that the cycle whose smallest root is lexically first is selected. Repeat with reversed mapping construction so replacing sorted-root traversal with insertion-order traversal would fail.
2. Add a focused assertion that `str(LaneDependencyCycleError)` identifies the complete closed path, as required by T002 and the WP's Test Strategy. Assert semantic path content rather than incidental punctuation.
3. Re-run and record:
   - `uv run pytest tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py tests/lanes/test_compute.py -q`
   - `uv run ruff check src/specify_cli/lanes/compute.py tests/specify_cli/lanes/test_lane_dependency_cycle_detection.py tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`
   - `uv run mypy --strict src/specify_cli/lanes/compute.py`

## Verified non-findings

- The authoritative gate is inside `compute_lanes`, after complete lane-edge construction and before depth computation.
- Iterative traversal handles graphs beyond Python's recursion limit.
- The typed error, immutable tuple facts, planning-lane membership, directed normalization, and owned-file boundary are correctly implemented.
- Contract fields owned by WP01 match `contracts/lane-dependency-cycle.schema.json`; JSON rendering remains WP02 scope.
- Focused suite: 67 passed; full `tests/specify_cli/lanes`: 129 passed; Ruff and strict mypy passed.
- No prohibited `--feature` usage, silent empty return, dead production seam, frozen-surface edit, or unrelated implementation-file change was found.

## Downstream impact

WP02 and WP03 depend on WP01. They must not start from the rejected revision. After WP01 is resubmitted and approved, their lane agents should use the runtime-provided dependency/rebase command before implementation.
