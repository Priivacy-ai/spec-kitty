---
work_package_id: WP03
title: "IC-EMIT-DEDUP — retire #2511's per-door pre-derivation"
dependencies:
- WP02
requirement_refs:
- FR-005
- NFR-006
tracker_refs: []
planning_base_branch: rework/ray-cluster-aggregation
merge_target_branch: rework/ray-cluster-aggregation
branch_strategy: Planning artifacts for this mission were generated on rework/ray-cluster-aggregation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rework/ray-cluster-aggregation unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "379242"
history:
- created at planning (tasks) — retires the #2511 per-door pre-derivation now that the shared emit layer (WP02) is primary-correct
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/commands.py
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-005
(note the explicit "**Depends on FR-003**" clause — this WP cannot land ahead of WP02),
[plan.md](../plan.md) §IC-EMIT "WP decomposition (MANDATED by the post-plan squad — split into
two WPs)" (this WP is "WP-B: FR-005 removal") and the paragraph explaining *why* the dependency is
structural, not just preferred ("the orchestrator door … blocks *solely* through `:444` once the
per-door pre-derivation is gone. Removal is dead-code-safe…"), and [research.md](../research.md)
"Decision: close the fail-open at the shared emit layer, not per-door". **Do not start this WP
until WP02 has actually landed and `coordination/status_transition.py:444` is primary-correct** —
removing the per-door patch before that lands would reopen the fail-open on the orchestrator-api
path with nothing left to catch it.

## Objective
PR #2511 patched the orchestrator-api door's fail-open locally, by pre-deriving
`subtasks_complete` in `orchestrator_api/commands.py` (~:1418-1430) *before* calling into the
shared emit layer — a per-door workaround for a shared-layer bug. Now that WP02 has fixed the
shared layer at its actual source (`coordination/status_transition.py:444`, which the
orchestrator door reaches via `emit_status_transition_transactional` → `_prepare_event`), this
per-door pre-derivation is redundant: it duplicates logic the shared layer now does correctly,
and its own comment block (already in the file) documents the exact bug WP02 fixed. This WP
removes it cleanly, adapts its test coverage to the new shared-layer wiring, and confirms the
dead-code gate stays green.

## Subtasks

### T015 — Remove the #2511 per-door pre-derivation block
In `orchestrator_api/commands.py`, delete the block at ~:1418-1430:

```python
if subtasks_complete is None and not force:
    # Subtask-gate parity with native move-task (#2510): left as None,
    # the emit-time inference reads tasks.md off the STATUS feature
    # dir — the coord worktree husk mid-mission, where tasks.md (a
    # PRIMARY-partition artifact) never exists — and FAILS OPEN,
    # letting WPs into for_review with every subtask unchecked.
    # Derive server-side from the PRIMARY planning surface instead;
    # an explicit caller assertion keeps working, --force bypasses.
    from specify_cli.status.emit import _infer_subtasks_complete

    subtasks_complete = _infer_subtasks_complete(
        _planning_read_dir(main_repo_root, mission), wp
    )
```

including its function-local `from specify_cli.status.emit import _infer_subtasks_complete`
import. After removal, `subtasks_complete` (a parameter/local already threaded through this
function) is left as whatever the caller passed — `None` when the caller didn't assert it — and
flows unchanged into `TransitionRequest(..., subtasks_complete=subtasks_complete, ...)` a few
lines below (confirm the exact variable name and downstream usage in the live file before
deleting; do not rename `subtasks_complete` — only remove the block that pre-populates it). The
orchestrator door now blocks **solely** through `coordination/status_transition.py:444`'s
`_prepare_event`, which WP02 already made primary-correct. Confirm the `if to_lane ==
Lane.FOR_REVIEW:` guard and `_enforce_for_review_commit_gate(...)` call immediately above/around
this block are otherwise untouched — this subtask removes exactly the dead block, nothing
adjacent. **Campsite bonus**: deleting this block also drops `orchestrator_api/commands.py::transition`
back under the mccabe complexity ceiling (it currently sits at 15) — a free win from this
removal, not extra scope to chase separately.

### T016 — Adapt the #2511 test coverage to the shared-layer behavior
Open `tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py` (created by #2511) and
judge each test against the removal: any test that asserts on the **removed** per-door mechanism
specifically (e.g. mocking/patching `orchestrator_api.commands._infer_subtasks_complete` or the
now-deleted local import) needs to be re-pointed at the **observable** behavior — the orchestrator
door still blocks a `for_review` transition on unchecked primary rows, it now does so via the
shared emit layer rather than the per-door patch. This is judge-the-test, not delete-the-test: the
#2511 tests were pinning a mechanism that has been consolidated, not a requirement that has gone
away. Re-run each test post-removal; for any that fail because they asserted the *mechanism*
(e.g. call-count on the deleted local import) rather than the *outcome* (blocked/allowed), rewrite
them to assert the outcome through the same production path used in WP02's
`test_infer_subtasks_primary.py` (native orchestrator-api call, unchecked primary rows → blocked;
all-checked → allowed; `--force` → bypasses). Do not delete coverage — the orchestrator-api
door blocking on unchecked subtasks is still a real, tested requirement; only the assertion
mechanism changes.

### T017 — Dead-code gate + full verification
Confirm the removal is dead-code-safe as the plan asserts:
- `_infer_subtasks_complete` (in `status/emit.py`) still has its other production callers intact —
  **four** production callers remain after removing the fifth (orchestrator-side) call:
  `status/emit.py:535`, `status/emit.py:690`, `status/aggregate.py:717`,
  `coordination/status_transition.py:444`. It is not orphaned (4 > 0).
- `_planning_read_dir` (the orchestrator-api's own local resolver variant, distinct from the
  canonical `resolve_planning_read_dir` WP02 threads elsewhere — see spec.md C-002's explicit
  callout of this distinction) still has 15+ other uses in `orchestrator_api/commands.py` — its
  removal from this one call site does not orphan the function itself.
- The function-local import at the old ~:1426 is gone with the block — grep the file afterward to
  confirm no dangling reference to `_infer_subtasks_complete` remains in `commands.py`.

Run `uv run pytest tests/architectural/ -k dead -q` (or the repo's actual dead-symbol gate test —
locate it via `tests/architectural/` if the `-k dead` filter doesn't match; check
`test_no_dead_symbols.py` and related modules) plus
`uv run pytest tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py -q`. Then
`uv run ruff check src/specify_cli/orchestrator_api/commands.py
tests/specify_cli/orchestrator_api/test_transition_subtask_gate.py` and `uv run mypy
src/specify_cli/orchestrator_api/commands.py` — zero new issues, zero new suppressions.

## Branch Strategy
Planning base branch and merge target branch are both `rework/ray-cluster-aggregation`;
`spec-kitty implement WP03` allocates an execution worktree per the lane computed from
`lanes.json`. **Depends on WP02** — this WP's removal is only safe once
`coordination/status_transition.py:444` is primary-correct; do not implement out of order.

## Definition of Done
- The #2511 per-door pre-derivation block (`orchestrator_api/commands.py` ~:1418-1430) and its
  function-local import are removed; `subtasks_complete` flows through unmodified from the caller.
- `test_transition_subtask_gate.py` still proves the orchestrator door blocks unchecked-row
  transitions and allows checked/forced ones, now via the shared emit layer.
- Dead-code gate green: `_infer_subtasks_complete` keeps its **four** remaining production callers
  (`status/emit.py:535`, `status/emit.py:690`, `status/aggregate.py:717`,
  `coordination/status_transition.py:444`), `_planning_read_dir` keeps its other 15+ uses, nothing
  orphaned by the removal.
- `uv run pytest tests/specify_cli/orchestrator_api/ -q` and the dead-symbol architectural test
  green; `uv run ruff check` + `uv run mypy` clean, zero new suppressions; full
  `tests/architectural/` 0-failed.

## Risks
- **Landing ahead of WP02** — the single biggest risk for this WP is sequencing: if the removal
  merges before `status_transition.py:444` is actually primary-correct, the orchestrator-api path
  reopens the fail-open with no per-door patch left to catch it. Verify WP02's DoD is met (not
  just "WP02 is `done` in the tracker") before starting T015.
- **Test judgment error** — deleting #2511 coverage instead of re-pointing it would silently drop
  a real regression guard; conversely, leaving a test that asserts the now-gone mechanism would
  make the suite red for the wrong reason. Read each test's assertion carefully before deciding
  keep/re-point/delete.
- **Dead-code false negative** — a hasty grep might miss a secondary reference to the deleted
  import or block (e.g. in a docstring or comment elsewhere) that documentation-drifts after this
  removal; do a full-file diff review, not just a targeted grep.

## Reviewer Guidance
Confirm: the #2511 block and its comment are fully removed (not commented out); no residual
`_infer_subtasks_complete` import remains in `commands.py`; the adapted tests assert observable
orchestrator-door behavior through the production path, not the removed mechanism; dead-code gate
run output is attached/referenced showing `_infer_subtasks_complete` and `_planning_read_dir` both
retain live callers; ruff/mypy clean; confirm via git log/diff that this WP's changes are
sequenced after WP02's merge (no rebase-order surprises).

## Activity Log
- {{TIMESTAMP}} — system — Prompt created at planning (tasks).
- 2026-07-12T12:20:38Z – claude:sonnet:python-pedro:implementer – shell_pid=379242 – Assigned agent via action command
- 2026-07-12T12:43:06Z – user – shell_pid=379242 – APPROVE (opus renata): #2511 per-door block+import removed (arch flag cleared), door blocks via shared emit layer, 4 tests re-pointed to production route, dead-code gate 20 green (4 callers), ruff/mypy clean (5d2ea5ffb)
