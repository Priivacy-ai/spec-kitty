# WP04 Review Feedback — Mission-Review Correction

## Verdict

Rejected. Commit `ead3fa201` correctly makes the real modern, stored
`topology: lanes` approval transition and trailing annotation durable and keeps
the tested stored `single_branch`, flat, and explicit-coordination paths green.
However, its new predicate is broader than the required stored-topology scope.

## Blocking finding — inferred legacy LANES is treated as stored LANES

`_lanes_annotation_transaction_available()` calls
`migration.backfill_topology.read_topology()`. That reader intentionally derives
a topology when `meta.json` has no stored `topology` key. Consequently, an
unbackfilled legacy mission with `meta.json` plus a valid `lanes.json` is
classified as `MissionTopology.LANES` and can enter the new transactional
annotation path. This changes the legacy behavior the correction was required
to preserve.

Independent reproduction against `ead3fa201` constructed a Git repository with
an unbackfilled `meta.json`, a valid `lanes.json`, no coordination branch, and
transaction availability. Calling `_lanes_annotation_transaction_available()`
returned `True`. The contract requires this case to remain uncommitted; only an
explicitly stored `"topology": "lanes"` may gain the new commit parity.

## Required correction

- Gate the new path on the literal, fail-closed stored topology value from
  `meta.json`; do not use a reader whose missing-key behavior derives topology.
- Require the stored value to be exactly `MissionTopology.LANES.value` before
  consulting `_transaction_topology_available()`.
- Preserve existing explicit coordination-branch routing unchanged.
- Add a compatibility regression for a valid legacy/unbackfilled lanes mission
  (`lanes.json` present, `topology` absent) proving the annotation remains on the
  historical uncommitted path.
- Keep the existing real-Git stored-LANES test proving the target ref contains
  both approval transition and trailing note, status files are clean, and the
  annotation commit does not include `snapshot-latest.json`.

## Review evidence

- Focused owned and compatibility suite: `59 passed`.
- Exact stored-LANES, flat, and architectural compatibility nodes: `3 passed`.
- Ruff across the touched/compatibility surfaces: passed.
- Strict mypy reported four diagnostics at pre-existing unchanged lines 139,
  155, 164, and 641 of `status_transition.py`; the correction diff begins near
  line 1400 and introduced none of them.
- `git diff --check ead3fa201^ ead3fa201`: passed.
- No dossier file or ownership-undeclared file is modified by the correction
  commit; the two modified files are declared WP04 ownership surfaces.

