# Issue matrix — org-pack-drg-root-graph-guard-01KZY0QT

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #3384 | Org pack without a root-level `*.graph.yaml` silently zeroes ALL action-scoped doctrine for every mission | fixed | Lane `kitty/mission-org-pack-drg-root-graph-guard-01KZY0QT-lane-a` @ `5105c9d91`: `139410f7f` (IC-01 guard), `d8fc5e14f` (IC-02 dedup), `0cf5cadbb` (IC-03 `OrgDRGFragmentError`), each preceded by its RED-first test commit (`b76407e4a`, `e76c1b99d`, `729421528`). Reviewer verdict `approved`, revert-tests hand-verified: `reviews/wp-WP01.yaml` |
| #3385 | `_org_scan_dirs` scans a phantom layout: one `charter activate` silently drops every org-pack artifact from the DRG | deferred-with-followup | Explicit operator-ruled **non-goal** for this mission — see `reviews/spec.ruling.md` (Q2). Disjoint code path (`src/charter/kind_vocabulary.py::_org_scan_dirs`, reached only via `charter activate`); verified zero-diff in this mission's blast radius. Issue #3385 is itself the tracked follow-up and remains OPEN. |
| #3284 | `main` full suite has 23 untracked failures and 2 errors after bootstrap prewarm | deferred-with-followup | Baseline context only; not addressed here. This mission's gate surface (`tests/charter/` + `tests/architectural/`) was captured **GREEN** before any change — 0 failed / 3611 passed / 6 skipped / 2 xfailed — so #3284's reds lie outside this mission's surface and none were introduced or masked by it. Remains tracked upstream as OPEN. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Notes

- **#3389** (`charter context --json` omits a `procedures[]` array while the text render ships a
  Procedures section) was **filed by this mission** during the spec phase and ruled out of scope
  by the operator; it is referenced in `plan.md` and `reviews/spec.ruling.md` but not in
  `spec.md`, so it carries no row here per this file's own one-row-per-spec-referenced-issue rule.
- **#3283** (shared pytest test-venv lock can time out) is baseline/capacity context referenced in
  `plan.md` only, for the same reason.
