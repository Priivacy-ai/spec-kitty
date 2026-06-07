# Live reproduction: status split-brain / branch-vs-coordination desync

**Captured:** 2026-06-07 · **Mission:** execution-state-canonical-surface-01KTG6P9
**Why this matters:** This is a concrete, reproducible instance of the exact defect class this mission remediates — multiple status readers disagreeing (US4 single-owner facade) and CWD/branch-vs-coordination dependence (US2 parity ratchet, US3 residue routing). It blocked the mission's own implement-review loop. The parity ratchet (WP01) and the status-facade consolidation (WP07–WP10) are the regression gate + fix for precisely this.

## Symptom

After a successful-looking `finalize-tasks` ("✓ Bootstrapped canonical status: 13 WPs seeded"), `spec-kitty agent action implement WP01` fails:

```
Error: WP WP01 has no canonical status. Run `spec-kitty agent mission finalize-tasks ...` to initialize.
```

Re-running `finalize-tasks` does not fix it (idempotent "13 WPs seeded", still no lane state).

## Three readers, three different answers (the split-brain)

| Command / reader | What it reports for WP01 | Source it reads |
|------------------|--------------------------|-----------------|
| `agent tasks status` | **13 planned** | lenient reader over the lifecycle log (`WPCreated` ⇒ planned) |
| `agent status emit WP01 --to planned` | **"Illegal transition: planned -> planned"** (i.e. already planned) | transition validator, derives current = planned from lifecycle log |
| `agent status materialize` | **"0 events → 0 WPs"** | lane-state reducer (flat `from_lane`/`to_lane` schema) |
| `agent action implement WP01` | **"no canonical status"** | lane-state reader (same as materialize) |
| `agent status doctor` | **"canonical status not initialized (event log missing/empty)"** | lane-state initialization check |

## Root cause (traced)

- The mission's `status.events.jsonl` contains **only lifecycle-schema events** (`schema_version: 5.0.0`, `event_type`/`aggregate_id`/`payload`): `MissionCreated`, `Specify*`, `Plan*`, `Tasks*`, and **13× `WPCreated`**. **Zero lane-state events** (`from_lane`/`to_lane`).
- The canonical lane-state model (`materialize`, `implement`, `doctor`) reads the **flat lane-state schema** and therefore sees **0 events**. Other (older/migrated) missions in the repo carry flat lane-state events and work fine.
- `finalize-tasks` bootstrap prints success but never persists the `planned` lane-state transitions the lane machine needs — neither on the `feat/execution-state-strangler` checkout nor on the `kitty/mission-…` coordination worktree (both copies are lifecycle-only).
- Net: the **write path** (emit/transitions, lifecycle-aware) and the **read path** (implement/materialize, lane-state-only) are split; finalize seeds the former's view but not the latter's. The `coordination_branch` indirection (status committed to the coordination branch, loop run from the target checkout) is the desync surface.

## Deadlock

The canonical unblock (`emit` the initial `planned` state) is itself rejected, because emit's validator already believes the state is `planned`. So the two readers cannot be reconciled through canonical commands without either (a) fixing the `finalize-tasks` bootstrap upstream, or (b) a coordination-topology remediation, or (c) force-driving lane events (improvises canonical status — disallowed by the canonical-sources discipline).

## Disposition

Tie to **#1589** (coordination status desync) and **#1666** (epic). Mission scope already covers the fix: US2 parity ratchet (WP01) must FAIL on exactly this CWD/branch-dependent divergence; US4/US5 collapse the multiple status readers onto one owning facade so `tasks status`, `materialize`, and the transition validator can never disagree again. Recommend this reproduction be referenced by WP01's negative-control test and WP07–WP10's acceptance.
