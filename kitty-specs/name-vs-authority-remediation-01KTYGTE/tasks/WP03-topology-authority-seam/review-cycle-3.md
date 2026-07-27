---
affected_files: []
cycle_number: 3
mission_slug: name-vs-authority-remediation-01KTYGTE
reproduction_command:
reviewed_at: '2026-06-12T20:24:00Z'
reviewer_agent: claude:opus:reviewer-renata:reviewer
verdict: approved
wp_id: WP03
---

# WP03 Review — Cycle 2 re-review (reviewer-renata) — APPROVED

> Artifact note: the cycle-1 rejection was filed with `cycle_number: 2` (off-by-one),
> so this approval — the genuine second review event, performed 2026-06-12 ~20:24 UTC —
> is recorded as `review-cycle-3.md` to restore the latest-artifact ordering the merge
> gate validates. The approval itself was executed at review time via
> `move-task WP03 --to approved` with the arbiter override documented in the
> `review_artifact_override_*` fields of `review-cycle-2.md`.

**Verdict: PASS.** Both cycle-1 blockers fixed and independently verified; the cycle-2
diff (`4788a4583..9a4385ecf`) touches ONLY `coordination/surface_resolver.py` and
`tests/specify_cli/coordination/test_worktree_topology.py`.

## Blocker 1 — unused-ignore under CI-authoritative mypy: FIXED
- `surface_resolver.py:104` now `# type: ignore[misc, unused-ignore]` with expanded
  dual-invocation rationale.
- CI invocation `mypy --strict src/specify_cli src/charter src/doctrine` → exactly
  **82 errors** (pre-existing baseline), zero in surface_resolver.
- Single-file run clean ("Success: no issues found").

## Blocker 2 — untested lock-root flip: FIXED
- Two new real-`git worktree add` regression tests:
  `test_emit_lock_root_for_coord_worktree_is_canonical_primary`
  (`emit._feature_status_lock_root`) and
  `test_lifecycle_lock_root_for_coord_worktree_is_canonical_primary`
  (`work_package_lifecycle._repo_root_for_lock`) — worktree registered UNDER
  `.worktrees/...-coord`, asserting canonical-primary lock root and cross-context
  agreement.
- **Reviewer-run mutation check**: disabled the canonical-root branch
  (`if False and topology in (...)`) in BOTH `emit.py` and
  `work_package_lifecycle.py` → both tests RED with the correct failure
  (lock root = worktree-local instead of canonical); `git checkout --` restored →
  GREEN; tree confirmed clean.

## Scope and gates
- C-002 fence intact: `status_transition.py`, `aggregate.py`, `merge.py` = 0 commits
  on the whole lane.
- 20 seam + decision-table tests pass; ruff clean on both files.
- Cycle-1 non-blocking adjudications (fixture modifications, dead-symbol in-flight
  allowlist, `is_under_worktrees_segment` shape-proposal scope, R3 semantics) were
  untouched by the cycle-2 diff and stand un-relitigated.
