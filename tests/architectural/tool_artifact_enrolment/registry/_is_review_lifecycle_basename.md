# Exemption mechanism -- `_is_review_lifecycle_basename`

<!-- Machine-readable exemption-registry row (R-014). Parsed by
     tests/architectural/test_exemption_registry_ratchet.py. ONE mechanism per
     file, so a retirement WP deletes ONLY its own row and never collides with a
     sibling retirement editing a shared file (squad-mandated design; the plan's
     stated reason for rejecting golden-count mode).

     UNLIKE every other row here, this one is NOT `status: expected-present` —
     it is `status: justified-survivor` (plan.md L233-235: "a genuine must-keep
     ... becomes an explicit, justified registry row, never a silent survivor").
     It is not on a retirement track and the overcount/symbol-presence arms are
     not expected to ever go red for it: it stays present for as long as
     `bulk_edit/diff_check.py`'s occurrence-map review needs to exempt the
     mission's own human-authored review/handoff commentary. -->


- mechanism: `_is_review_lifecycle_basename`
- module: `src/specify_cli/bulk_edit/diff_check.py`
- literals: `(none)`
- symbol: `_is_review_lifecycle_basename`
- retirement-wp: `WP15`
- retirement-ref: `IC-07e`
- owner-route: `n/a — genuine survivor, outside is_toolchain_generated_churn's scope`
- status: `justified-survivor`

## Why this cannot route onto the owner (C-010)

IC-07e (WP15) retired the former `RUNTIME_STATE_ALLOWLIST` / `_runtime_state_exemption`
named allowlist. Four of its six basenames (`status.events.jsonl`, `status.json`,
`issue-matrix.md`, `acceptance-matrix.json`) are COORD-partition mission artifacts —
toolchain-generated churn the canonical owner `is_toolchain_generated_churn` already
classifies — so those four now delegate to the owner instead of restating basenames.

The remaining two, `notes.md` and `review-cycle-*.md`, are **human-authored review and
handoff commentary**, not toolchain-generated writes:

- Neither has a `MissionArtifactKind` in `mission_runtime/artifacts.py` — the owner has
  no opinion on them by design (it classifies *generated* coordination/self-bookkeeping
  churn, not operator/reviewer prose).
- Empirically, `is_toolchain_generated_churn(...)` returns `False` for both — for
  `review-cycle-*.md` under `tasks/<WP>/` it even resolves to the PRIMARY
  `WORK_PACKAGE_TASK` kind via the `_COORD_RESIDUE_DIRS["tasks"]` classifier, which is
  correctly NOT coordination residue.
- Forcing these onto the owner would either (a) require growing
  `mission_runtime/artifacts.py` with a review-commentary kind that has nothing to do
  with toolchain-generated churn (polluting the owner's boundary), or (b) silently drop
  the exemption and reintroduce a false block on the mission's own review-cycle/notes
  files during a bulk-edit-mode WP review — a regression C-010 forbids.

`_is_review_lifecycle_basename` is therefore the minimal, narrow, **registered**
survivor for exactly these two basenames: enumerated here so it is visible to any
audit of unowned filename exemptions, never a silent function-local predicate.
