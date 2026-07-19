# Reviewed Disposition Matrix

**Mission**: `stale-workspace-reproduction-recovery-01KXGR6S`  
**Mission ID**: `01KXGR6SRKX7C1RB77MAWN2R34`  
**Issue**: #2626 (sole claimed issue)  
**Draft PR**: #2641  
**State**: reviewed and authoritative for downstream conditional implementation

## Authorization Rule

This PRIMARY planning artifact is the sole row-specific production authorization
checkpoint. Only rows marked `RED/continue` authorize their named downstream WP.
Rows marked `GREEN/stop` prohibit production changes for that arm. A downstream
implementer must stop and request plan amendment/refinalization if the reached
owner differs from the reviewed owner below.

Spec Kitty 3.2.5 cannot finalize a `planning_artifact` WP owning canonical
`kitty-specs/` paths; upstream gap #2643 records that limitation. The explicit
orchestrator checkpoint is therefore mandatory and may not be replaced by an
implementation handoff or verbal summary.

## Review Metadata

| Field | Value |
|---|---|
| `origin/main` baseline SHA | `2d05c53d03ee794885954410ae6a63c29d432869` |
| WP01 witness commits | cycle 1 `1902ce530759b80e2bbaaa1b134fa8c73de8729e`; approved cycle 2 `ff7eca5e2c248730909d91cddde93c6c01232701` |
| independent reviewer | Reviewer Renata (`reviewer-renata`) |
| review reference | `ff7eca5e2c248730909d91cddde93c6c01232701` |
| approval event | `01KXGVAMKBG68FTJW1R1P10PVZ` |
| coordination status commit | `c2d41927e` |
| review verdict | APPROVED — two exact runs reproduced 5 GREEN / 7 intentional RED; Ruff passed |
| reviewed at | `2026-07-14T17:38:20.907471+00:00` |

## Required Row Schema

Every applicable command/state arm must record: entry point; exact argv; state
classification; baseline SHA; test node ID; result/exit code; event/materialized
state delta; WP/tasks byte delta; PRIMARY/COORD/lane OIDs and commit path sets;
lock/path delta; checkout porcelain; reached owner; RED/GREEN; stop/continue;
authorized downstream WP; reviewer and review reference.

The ordinary `move-task` acceptance row must not use
`--skip-pre-review-gate`. That escape hatch may appear only as a separately
labelled negative control.

## Evidence Legend

- Test module: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`; every node is
  `test_stale_workspace_transition_matrix[<entry>-<state>]`.
- Fixture Mission: `coord-topo-fixture-01KW2E7A`. All rows assert the real
  registered Typer entry point, exact argv, structured/stdout/stderr result,
  event-log bytes, materialized and independently reduced bytes, WP/tasks bytes,
  PRIMARY/COORD/lane OIDs and ordered commit path sets, review locks, worktree
  path existence, and porcelain for every checkout before the final RED assertion.
- `STATUS` means both `status.events.jsonl` and `status.json` on COORD. `WP`
  means `tasks/WP01-witness.md` on PRIMARY unless a row explicitly records the
  command's COORD/lane placement. `TASKS` means PRIMARY `tasks.md`.
- Every unavailable or divergent row executable-asserts monotonic elapsed time
  `<2s`. The scoped pre-review gate actually ran (`ran=True`) for `move-task`;
  its production result is truthfully `unverified_baseline`, not `no_coverage`.

## Reviewed Rows

| # | Entry/state and exact argv | Result and six-surface delta | Reached owner | Disposition / authorization |
|---|---|---|---|---|
| 1 | `mark-status-healthy`: `agent tasks mark-status T001 --status done --mission coord-topo-fixture-01KW2E7A --json` | exit 0; summary `updated=1`; STATUS/WP unchanged, TASKS changed; PRIMARY advances with only `tasks.md`; COORD/lane unchanged; no lock/path change; all checkouts clean | PRIMARY task tracking | `GREEN/stop`; none |
| 2 | `mark-status-recoverable`: same exact argv | exit 0; identical authoritative bytes/ref placement to row 1; missing lane path remains missing; all existing checkouts clean | PRIMARY task tracking | `GREEN/stop`; none |
| 3 | `mark-status-unavailable`: same exact argv | exit 0 `<2s`; identical authoritative bytes/ref placement to row 1; lane ref/path absent; all existing checkouts clean | PRIMARY task tracking | `GREEN/stop`; none |
| 4 | `mark-status-divergent`: same exact argv | exit 0 `<2s`; identical authoritative bytes/ref placement to row 1 despite persisted lane-z identity; registered lane-a remains clean | PRIMARY task tracking | `GREEN/stop`; none |
| 5 | `move-task-healthy`: `agent tasks move-task WP01 --to for_review --mission coord-topo-fixture-01KW2E7A --agent codex --json` | exit 0 `result=success`; gate ran, `outcome=unverified_baseline`, target `tests/witness_gate`; STATUS/materialized/reduced and WP change, TASKS unchanged; PRIMARY advances with WP only, COORD advances with STATUS only, lane unchanged; no lock/path change; all clean | move-task workspace readiness | `GREEN/stop`; none |
| 6 | `move-task-recoverable`: same exact argv | exit 0 with the same durable transition and exact placement as row 5 even though the registered worktree was missing; path remains missing; no locks; all existing checkouts clean | move-task workspace readiness | `RED/continue`; WP02 |
| 7 | `move-task-unavailable`: same exact argv | exit 0 `<2s` with the same durable transition and exact placement as row 5 despite absent lane branch and path; no locks; all existing checkouts clean | move-task workspace readiness | `RED/continue`; WP02 |
| 8 | `move-task-divergent`: same exact argv | exit 0 `<2s` with the same durable transition and exact placement as row 5 despite persisted lane-z versus registered lane-a; no locks; all checkouts clean | move-task workspace readiness | `RED/continue`; WP02 |
| 9 | `review-healthy`: `agent action review WP01 --agent codex --mission coord-topo-fixture-01KW2E7A` | exit 0; STATUS and WP bytes change, TASKS unchanged; PRIMARY ref does not advance, COORD advances with STATUS+WP, lane advances through STATUS/STATUS/WP/empty commits; one review lock added; lane path exists; PRIMARY WP is left dirty | review claim/commit routing | `RED/continue`; WP04; #2160-adjacent placement residual only |
| 10 | `review-recoverable`: same exact argv | exit 0; missing worktree is recreated; otherwise the exact bytes, ref movement/path sets, added lock, and dirty PRIMARY WP match row 9 | review claim/commit routing | `RED/continue`; WP04; #2160-adjacent placement residual only |
| 11 | `review-unavailable`: same exact argv | exit 1 `<2s` with raw `[Errno 2] No such file or directory`; STATUS/materialized/reduced unchanged after compensation, WP changes, TASKS unchanged; PRIMARY ref unchanged, COORD advances through STATUS+WP+WP commits, lane ref/path absent; no lock; PRIMARY/COORD remain dirty | review claim/commit routing | `RED/continue`; WP04 |
| 12 | `review-divergent`: same exact argv | exit 0 `<2s`; accepts registered lane-a despite persisted lane-z; otherwise the exact bytes, ref movement/path sets, added lock, existing lane path, and dirty PRIMARY WP match row 9 | review claim/commit routing | `RED/continue`; WP04 |

WP03 has no authorized row: WP01 reached the task-command/placement owner for
rows 6–8 and the review claim/commit-routing owner for rows 9–12. WP03 must
therefore execute its declared no-op/verification path and must not edit
production lifecycle code unless a later independently reviewed row reaches its
owner and this matrix is amended and recommitted.

## Charter Exception Handling: Dependency-Ordered Acceptance Witness

**Adversarial approval:** ATDD / Reviewer Renata — **APPROVE**; architecture /
Architect Alphonso — **APPROVE**; runtime-governance — **APPROVE**. This is an explicit,
case-by-case Charter Exception Handling decision, not authorization derived from
generic ownership leeway.

- ATDD reference: `/root/wp02_amend_atdd_review` final re-review — test-first,
  immutable-node, frozen-harness, and six-surface findings resolved.
- Architecture reference: `/root/wp02_amend_arch_review` final re-review —
  approved-or-done/inactive/clean-lane predicate and bounded exception resolved.
- Runtime reference: `/root/wp02_amend_runtime_review`, recovery commit
  `a474d5834` — four lanes, zero merges, `would_modify=[]`, four unchanged WPs,
  clean lane-a/lane-b, and exact witness blob/ref verified.

The exception is justified because WP01 is canonically approved or done,
inactive, and with a clean dependency lane; lane-b contains the exact approved witness blob
`d1f89937dc25353d74615d7305c97e9af00848ee` at ref `ff7eca5e2`; and WP02 then
WP04 are serial dependencies with no concurrent writer. The exception covers one
test-only file and only these exact named-node branches:

- WP02 row 6: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-recoverable]`.
- WP02 row 7: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-unavailable]`.
- WP02 row 8: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[move-task-divergent]`.
- WP04 row 9: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-healthy]`.
- WP04 row 10: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-recoverable]`.
- WP04 row 11: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-unavailable]`.
- WP04 row 12: `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py::test_stale_workspace_transition_matrix[review-divergent]`.

WP02 freezes fixture construction, `_snapshot`, `_observe`,
`_assert_common_record`, the registered invocation path, common six-surface
measurements, and every other node against approved WP01 blob
`d1f89937dc25353d74615d7305c97e9af00848ee` at ref `ff7eca5e2`. WP04 freezes the
same surfaces and rows 1–8 against the approved WP02 blob recorded in its review
handoff. Each WP must commit its named desired-outcome branches test-only, prove
the exact nodes RED on the dependency base, and only then implement production;
expectations cannot change after production work begins. Historical evidence and
the frozen harness remain immutable.

Adding this file to shared `owned_files` is rejected because it would recompute
active topology, conflict with the live workspaces, and recreate the #2644 class
of failure. Duplicating the fixture is prohibited because a parallel witness is
fakeable and would cease to test the reviewed registered path. Starting a fresh
replacement Mission is also rejected because it would discard truthful reviewed
state. The existing PR remains DRAFT, and operator-only readiness/merge is the
final review boundary.

This exception supersedes only ownership-map-leeway step 1 and its corresponding
failure mode for this one file and the named nodes. It grants no general ownership
and does not relax any production ownership boundary.

Required rationale strings for the test-only commits and review handoffs:

- WP02: `Charter exception: WP01 canonically approved or done, inactive, and with a clean dependency lane; witness rows 6–8 only; frozen harness, serial writer, no topology recomputation.`
- WP04: `Charter exception: dependency witness rows 9–12 only; frozen harness, serial writer, no topology recomputation.`

Stop immediately if any recorded adversarial approval is withdrawn or rejected.
Stop unless WP01 is canonically approved
or done, inactive, and with a clean dependency lane. Also stop if the lane-b
ref/blob differs; a concurrent writer exists; dependency order is not satisfied;
any frozen harness, historical evidence, `_MATRIX` name or order, non-named node,
second file, or shared ownership/topology change would be required; or the
PR/operator boundary changes. Return to the orchestrator for a new case-by-case
decision rather than broadening this exception.

WP03 owns no row and remains a production/test no-op. Earlier commit/review
evidence is immutable. Expected deltas may change to the atomic contract, but the
six-surface observation and coverage may not shrink.
