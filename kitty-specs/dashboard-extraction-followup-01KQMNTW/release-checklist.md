# Release Checklist — `feature/650-dashboard-ui-ux-overhaul`

This document records the release-readiness state of the
`feature/650-dashboard-ui-ux-overhaul` branch. Anything listed here must
be verified (with operator name and commit reference) before this branch
ships to end users via merge into `main` or any downstream release tag.

The follow-up mission `dashboard-extraction-followup-01KQMNTW` (DRIFT
findings RISK-2 + others) created this file to satisfy FR-009/FR-010 of
that mission and to close the SC-006 gap from parent mission
`dashboard-service-extraction-01KQMCA6`.

## Mandatory verification — Dashboard service extraction (mission #111)

### SC-006 — Live browser smoke-test

> **Source**: parent mission `dashboard-service-extraction-01KQMCA6`,
> Success Criterion SC-006: "`dashboard.js` displays correct data in the
> operator's browser after extraction." T030 in WP05 was a manual smoke
> step that was not formally executed before merge.

| Field | Value |
|-------|-------|
| Verifier (name / handle) | _TBD — fill before tagging_ |
| Verification date (UTC) | _TBD_ |
| Commit at verification (`git rev-parse HEAD`) | _TBD_ |
| Browser used | _TBD (Chrome / Firefox / Safari + version)_ |
| `spec-kitty dashboard` invocation | _TBD (working directory + result)_ |

**Required dashboard checks** (must all be observed in a real browser):

- [ ] Mission list renders for the active project; the active mission is
      highlighted.
- [ ] Kanban view loads for at least one mission and shows lanes
      consistent with `tasks/WP*` files (planned / claimed / in_progress
      / for_review / in_review / approved / done / blocked / canceled).
- [ ] Health endpoint reports `status: ok` and a populated
      `websocket_status`.
- [ ] Sync trigger button (when present in the UI) returns either
      `scheduled` or one of the three documented skip / unavailable
      branches without an error toast.
- [ ] No console errors in the browser dev-tools network or JS panels
      attributable to the dashboard frontend.
- [ ] Viewing a research, contracts, or checklists artifact via the UI
      returns the file content (not a 404 or 500).

**Verdict**: ☐ PASS · ☐ PASS WITH NOTES · ☐ FAIL

**Notes / observations**:

> _Operator records what was tested, on what data, and any deviations
> from the expected behavior here._

---

## Standing release gates (apply on every release tag derived from this branch)

The items below are not specific to this mission's findings; they are
the standing gates that any release of this branch must clear. They are
recorded here so a single artifact gates the branch.

- [ ] All tests pass on the head commit (`pytest` from repo root, with
      the project's pyenv version active).
- [ ] No new unauthorized callers of `ensure_sync_daemon_running` per
      `tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites`.
      The gate now scans both `src/specify_cli/` and `src/dashboard/`.
- [ ] CHANGELOG entry exists for the version that includes this branch.
- [ ] No outstanding ✗ items from the post-merge mission review report
      saved at
      `/tmp/spec-kitty-mission-review-dashboard-service-extraction-01KQMCA6.md`
      that have not been remediated by mission
      `dashboard-extraction-followup-01KQMNTW`.

---

## Process notes

- This file lives **on the branch** so the verification artifact ships
  with the code being verified. When this branch eventually merges into
  `main`, the merge commit's tree will carry this checklist as
  historical evidence.
- The follow-up mission cannot itself complete the SC-006 verification
  — that requires a human operator with a browser. The mission's job is
  to ensure the artifact exists and is committed; whoever cuts the
  release fills the verifier / date / commit fields above before
  tagging.
- If this branch is rebased or amended, the verifier must re-record the
  commit reference and re-perform the browser checks against the new
  HEAD. A previous PASS does not transfer across branch rewrites.
