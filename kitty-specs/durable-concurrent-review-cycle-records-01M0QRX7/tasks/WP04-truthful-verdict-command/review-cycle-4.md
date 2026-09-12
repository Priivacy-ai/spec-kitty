---
affected_files: []
cycle_number: 4
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T08:35:57Z'
reviewer_agent: codex-mission-integration-audit
wp_id: WP04
---

# WP04 review feedback — cycle 3

## Verdict: changes requested

WP04's focused command suite passes, but the issue-pinned production-path gate
still exposes one genuine command-layer coherence defect. When two automatic
reviewers save rejection verdicts for the same WP concurrently, the verdict
queue correctly makes the second writer wait and both evidence artifacts become
distinct committed Git blobs. The second successful command nevertheless emits
an authoritative status event with no `review_result`.

This violates T019's requirement that a verified verdict-evidence outcome and
its authoritative event remain coherent. It also violates the confirmed
operator policy for this mission: verdict saves wait in line, the later save
wins after the earlier save completes, and both records are preserved.

## Reproduction

The defect was reproduced from the exact WP05 cycle-1 reviewed integration
state at commit `2892c7de499e52cb5e55f6c9184fd1982f7beeee`:

```text
uv run python -m pytest \
  tests/integration/test_review_durability_matrix.py::test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations \
  -n0 -q --tb=short
```

It fails on round 0 with an
`authoritative_event_mismatch`. Retained repository evidence for that round
shows:

1. reviewer A commits `review-cycle-1.md` and emits `in_review -> planned`
   with the exact `ReviewResult`;
2. reviewer B waits behind reviewer A, commits distinct
   `review-cycle-2.md`, and emits `planned -> planned`;
3. reviewer B's event has the correct mission, WP, actor, review pointer, and
   successful command event ID, but `review_result` is absent.

The same baseline was intentionally recorded red when WP01 was approved at
`1bef5f30f105e80bbf40d920ebcb59920b32bcf6`; it was a forward production gate
for this command-integration package, not a regression caused by WP05 or by test
order.

## Exact production cause

`src/specify_cli/cli/commands/agent/tasks_move_task.py` persists reviewer B's
verified rejected cycle onto `st.rejected_review_result`, but
`_mt_hop_review_result()` returns that result only while the authoritative hop
still leaves `in_review`. By the time the queued second writer emits, reviewer
A has moved the authoritative state to `planned`, so the helper discards the
verified result and the `planned -> planned` event is written without verdict
authority.

The queue, evidence allocation, Git commit, governed-ref read-back, and event
serialization are all functioning. The defect is specifically the command's
selection of the `ReviewResult` for the serialized second verdict.

## Required correction

Within WP04's owned command orchestration surface:

1. Preserve the exact `ReviewResult` produced by a verified automatic rejected
   review-cycle write.
2. When that queued verdict targets `planned`, attach the exact verified result
   to its authoritative event even if an earlier queued writer has already made
   the current authoritative lane `planned`.
3. Preserve the event's exact reviewer, `changes_requested` verdict, canonical
   review-cycle pointer, mission identity, WP identity, and returned event ID.
4. Do not synthesize the result from CLI arguments after the fact; use the
   verified cycle's canonical `ReviewResult`.
5. Do not broaden the verdict queue to status emission, do not nest the status
   lock around Git, and do not add retry behavior. Preserve the established lock
   order and ten-second wait-in-line contract.
6. Do not collapse the second save into a state refusal or discard its evidence.
   The later queued verdict must become the current authoritative verdict after
   its distinct evidence is committed.

## Required tests

Add a focused WP04-owned real-command regression that deterministically holds
writer A inside the evidence commit seam and starts writer B against the same
WP. It must prove:

- writer B cannot enter its evidence commit until writer A releases;
- both commands finish inside the ten-second budget;
- two distinct evidence pointers exist and both exact blobs are committed at
  the governed review-cycle destination;
- both returned event IDs resolve exactly once through the production event
  reader;
- each event carries its own exact reviewer, verdict, reference, mission, and
  WP tuple;
- the later event is the current verdict; and
- removing the second-hop `ReviewResult` propagation makes the regression fail
  causally.

After the focused test passes, rerun the exact issue-pinned node above and the
full affected integration command recorded in WP05 feedback. The latter may
remain red only for separately reopened WP01 oracle drift until that correction
lands; this production mismatch itself must be gone.

## Ownership and scope

This correction belongs to WP04 because T019 owns verified-outcome propagation
and event gating in:

- `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
- `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`

Do not edit WP01's frozen integration matrix from WP04. Do not reopen or modify
WP02's queue primitive or WP03's retained-evidence primitive; both behaved as
specified in this reproduction.

