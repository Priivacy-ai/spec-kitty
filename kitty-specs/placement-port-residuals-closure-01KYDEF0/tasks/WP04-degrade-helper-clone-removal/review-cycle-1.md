# WP04 Review — Cycle 1: REJECTED

FR-005 mandates **behavior-preserving** consolidation. The migration of
`bookkeeping_commit._resolve_bookkeeping_commit_target` changed behavior on a
**reachable production path** and left 4 existing tests red. This is a real
regression, not a nit. SC-004 (0 verbatim clones) and MR-1 lockstep are fine;
the defect is the fail-closed migration.

## Issue 1 (BLOCKING) — bookkeeping_commit regresses the resolvable-mission + `branch=None` path

**File:** `src/specify_cli/git/bookkeeping_commit.py:196-207`
(`_resolve_bookkeeping_commit_target`)

The new code raises `ActionContextError` **unconditionally** when `branch is None`,
*before* attempting resolution:

```python
if branch is None:
    raise ActionContextError(...)   # fires even when the mission is fully resolvable
return resolve_write_target_or_degrade(repo_root, mission_slug, kind=kind, degrade_ref=branch)
```

The ORIGINAL only raised when `branch is None` **AND** resolution was impossible.
For a bootstrapped, resolvable mission (meta.json present), the original skipped the
`meta_exists` gate and returned the resolved placement-port target via
`resolve_placement_only(...)` — regardless of `branch` being `None`.

**Why it is reachable (not theoretical):** `post_merge/retrospective_terminus.py:245`
calls `commit_merge_bookkeeping(...)` with **no `branch=` argument** (defaults to
`None`). Post-merge/close, the mission is always resolvable, so the original returned
the resolved PRIMARY target and committed the retrospective. The new code raises
`ActionContextError` first, so — because the retrospective terminus is fail-open —
**every retrospective commit now silently fails** (warns "could NOT be committed",
leaves the event-log/`retrospective.yaml` append uncommitted). Silent data-loss
regression on both the `spec-kitty merge` and `mission close` paths.

**Proof (tests green on base 072c7ca, red on this lane):**
- `tests/specify_cli/post_merge/test_retrospective_triggering.py::TestRetrospectiveCommit::test_captured_retrospective_is_committed` — FAIL
- `...::test_capture_failed_event_is_committed` — FAIL
- `...::test_idempotency_heals_a_previously_failed_commit` — FAIL
  (warning literally reads: `commit_merge_bookkeeping: mission '017-my-test-mission'
  requires a degrade-path 'branch' when resolution may fail.`)

**Required fix:** preserve the original semantics — the fail-closed raise must fire
only when resolution actually cannot produce a target, not before the attempt. For
the `branch is None` case, still try to resolve (meta-exists gate + `resolve_placement_only`)
and raise only if that path degrades. E.g. resolve-first, then raise if unresolved:

```python
if branch is not None:
    return resolve_write_target_or_degrade(repo_root, mission_slug, kind=kind, degrade_ref=branch)
# fail-closed: no degrade path — resolve or raise (never degrade silently)
# (attempt real resolution; raise ActionContextError only if it cannot resolve)
```

Do NOT reintroduce the verbatim clone to do this — extend the shared seam if needed
(e.g. a sentinel/`degrade_ref=None` fail-closed mode, or a thin resolve-or-raise wrapper),
keeping SC-004 intact.

## Issue 2 (BLOCKING) — broken test from removed import

**File:** `tests/regression/test_birth_cutover.py:859`
(`test_coord_seed_commit_targets_coord_branch_via_real_placement_port`)

`AttributeError: module 'specify_cli.git.bookkeeping_commit' has no attribute
'resolve_placement_only'`. The test monkeypatches
`bookkeeping_commit.resolve_placement_only`, but WP04 removed that import from the
module (resolution moved into the helper). Green on base, red on this lane.
Update the patch target to the new seam
(`mission_runtime.write_target_degrade.resolve_placement_only` or wherever the helper
resolves) so the coord-seed real-placement-port assertion still exercises the routing.
Note this file is outside `owned_files`; add a coordination note when you touch it.

## Issue 3 (non-blocking, fix while here) — tests pin the wrong contract + one vacuous test

**File:** `tests/mission_runtime/test_write_target_degrade.py`

- The bookkeeping tests only cover `branch=None` + mission **missing** → raise. They
  never exercise `branch=None` + mission **resolvable** (the regressed happy path),
  which is exactly why this suite passed while production broke. Add a behavioral pin
  for that case (resolvable mission, `branch=None` → returns the resolved target, does
  NOT raise) so the fix is durably protected.
- `TestScenario004VerbatimCloneRemoval::test_no_verbatim_mission_meta_exists_clones`
  is a `pass` placeholder (anti-pattern: vacuous test). Make it a real assertion (run
  the SC-004 grep in-process / assert the module set) or delete it — a green `pass`
  advertises coverage it does not provide.

## What passed (for the next cycle)
- SC-004: `grep -rn _mission_meta_exists src/` → only `write_target_degrade.py`. Clones deleted. PASS.
- MR-1 lockstep: `__init__.__all__` and `_PUBLIC_SURFACE` both add `resolve_write_target_or_degrade`;
  `tests/architectural/test_mission_runtime_surface.py` GREEN (13 passed incl. new tests). PASS.
- decision_log fail-open preserved via `degrade_ref=destination_ref`. PASS.
- kind-parameterization preserved (`kind=` threaded through). PASS.
- Campsite: only `owned_files` code touched (Issue 2 fix will need `test_birth_cutover.py`
  — record the coordination note).

## Anti-pattern checklist verdict
1. Dead code — PASS (helper has 2 live callers). 2. Synthetic/vacuous test — **FAIL**
(Issue 3). 3. Silent empty return — N/A. 4. FR coverage — **FAIL** (FR-005 behavior
regressed, Issue 1). 5. Frozen surface — PASS. 6. Locked decision — **FAIL** (FR-005
"NO behavior change" violated). 7. Shared-file ownership — note needed for
`test_birth_cutover.py` (Issue 2). 8. Production fragility — **FAIL** (unconditional
`raise` on a fail-open production path, Issue 1).
