# Post-Spec Adversarial Squad — Convergent Findings

**Mission**: mission-completion-terminal-state-01M129MV
**Point-cut**: post-spec
**Date**: 2026-08-28
**Lenses (profile-loaded, read-only)**: architect-alphonso (structure/seams), debugger-debbie
(live-evidence/repro), reviewer-renata (anti-laziness/fakeable), planner-priti
(scope/sequencing/terminology)

This document records the **convergent evidence** that survived independent scrutiny, with
file:line anchors, so the plan phase has a grounded map. The spec was revised to fold these
findings; this is the audit trail behind that revision.

---

## F1 — BLOCKER (converged: reviewer + debugger): cancellation provenance is auto-synthesized

The spec pivots on "canceled-with-a-non-empty-reason" as the honest-ending signal. But the
canonical `move-task` command **always fabricates a non-empty reason**:

`src/specify_cli/cli/commands/agent/tasks_transition_core.py:307-317`
```python
emit_reason: str | None = note_text if note_text else None     # --note "" is falsy → None
if force and not emit_reason:
    emit_reason = f"Force move to {target_lane}"                # --force, no note → non-empty
if not emit_reason:
    emit_reason = f"Force move to {target_lane}" if force else f"move-task: {old_lane} -> {target_lane}"
```

Consequences (both fatal to the spec as originally written):
- **FR-001 guard is auto-forgeable**: a silent `move-task WP --to canceled --force` (no `--note`)
  records `reason="Force move to canceled"` — non-empty — so an *undocumented* cancellation
  passes acceptance identically to a documented replan. Exactly the "cancellation used to skip
  work silently" that FR-003 exists to prevent.
- **FR-003 / SC-002 / AS-3 are unreachable**: their trigger ("canceled without a recorded
  reason, e.g. `--force` with no note") cannot be produced by the canonical command; the only
  way to an empty reason is hand-editing the event log, which C-002 forbids and #2945 disclaims.

**Resolution folded**: provenance is redefined as **operator-authored** content, distinguishable
from the tool's synthetic default (`validate.py:126-128` only checks string-truthiness). Mechanism
is a plan decision (candidates: require `--note` and reject the synthetic templates; a dedicated
cancellation-reason field/event; or make force-cancel-without-note record an empty sentinel so the
FR-003 blocker becomes reachable). See revised FR-001/FR-003/C-002 and SC-002.

Anchors: `tasks_transition_core.py:307-317`, `status/validate.py:126-128`.

---

## F2 — HIGH (architect; supersedes planner's "consume is_terminal"): FR-005 is mis-framed

Three different value-sets already encode three different questions:
- `status_lanes.py:22` — `TERMINAL_LANES = {"done","canceled"}` (FSM-terminal: leave-without-`--force`),
  re-exported as `is_terminal()` (`status/transitions.py:20,63`).
- `acceptance/__init__.py:145` — `_ACCEPTED_READY_LANES = {"approved","done"}` (accept-ready),
  **duplicated** at `acceptance/gates_core.py:52` (with a "Duplicated here rather than imported"
  comment) and inlined at `acceptance/summary_core.py:173,202`.
- Other variants: `audit/classifiers/wp_files.py:16` `{"done","approved"}`;
  `migration/rebuild_state.py:140` `{"done","canceled","approved"}`.

Terminality ≠ acceptability ≠ provenance are **three separable decisions**. Naively making accept
consume `is_terminal()` would reject every `approved` WP (approved ∉ {done,canceled}) and accept
`canceled` unconditionally — a severe FR-006/NFR-001 regression.

**Resolution folded**: FR-005 becomes an **acceptable-ending predicate** (e.g.
`is_acceptable_ending(lane, *, has_provenance)`) living in the status/status_lanes package,
consumed by accept **and** merge, that admits `{approved,done}` unconditionally, admits `canceled`
only with provenance, and references canonical `TERMINAL_LANES` solely for the canceled
classification — collapsing the three `_ACCEPTED_READY_LANES` copies onto it (directive 044).

Anchors: `status_lanes.py:22`, `acceptance/__init__.py:145,332-395`, `acceptance/gates_core.py:52`,
`acceptance/summary_core.py:173,202`.

---

## F3 — HIGH (converged: architect + debugger): the reducer snapshot drops `reason`

Accept buckets lanes from the **reduced snapshot**, not raw events
(`acceptance/__init__.py:997,1021`). The per-WP snapshot (`status/reducer.py:166-177`) carries
`lane`, `actor`, `last_transition_at`, `last_event_id`, `force_count` — **not** `reason`. So the
provenance FR-003/C-002 need is absent from the surface accept reads.

**Resolution folded**: the plan must choose the read seam explicitly — (a) project
`cancellation_reason` into the snapshot when `lane==canceled` (a projection change, not a
state-machine change; touches the reducer + its golden tests), or (b) an acceptable-ending
provenance lookup that reads the log by `last_event_id`. Either way the event log stays the
authority (C-002). Captured as revised C-002.

Anchors: `status/reducer.py:166-198`, `acceptance/__init__.py:997,1021`.

---

## F4 — HIGH (converged: architect + debugger): FR-004 is at the wrong granularity

A lane holds **many** WPs (`lanes/models.py:84` `wp_ids: tuple[str,...]`). Merge integrates
per-lane-branch (`merge/executor.py:416-459`) but feeds **every** WP into per-WP assertions:
`all_wp_ids` at `executor.py:1660` → `_enforce_review_artifact_consistency` (`:1671`), `wp_order`
(`:1681`), and `_assert_merged_wps_done_on_target` (`merge/done_bookkeeping.py`), which raises
`typer.Exit(1)` for any WP not `done` on target. A canceled WP has no review artifact and is never
`done`, so it breaks merge in two places before any "skip."

**Resolution folded**: FR-004 re-expressed at WP granularity — canceled WPs excluded from merge's
done/review-artifact assertions and from `wp_order` (single filter point: `executor.py:1660`),
cancellation record retained; a lane whose WPs are **all** canceled is skipped for branch
integration (its branch may not exist). See revised FR-004 + SC-001.

Anchors: `lanes/models.py:84-85`, `merge/executor.py:416-459,1660-1683`,
`merge/done_bookkeeping.py` (`_assert_merged_wps_done_on_target`).

---

## F5 — HIGH (planner): dependency-on-canceled strands the dependent (re-creates the trap)

`core/dependency_graph.py:59` lists `canceled` as a **non-satisfying** dependency lane. Canceling a
depended-upon WP is reachable from `in_progress` **without** `--force` (the #2945 path), leaving a
surviving dependent permanently unclaimable → `planned` → FR-006 blocks accept → the mission is
again permanently non-terminal. This is a **new instance of the identical trap** and a **third**
disagreeing consumer of "is canceled terminal" (`is_terminal` yes / accept-with-provenance yes /
dependency gate no) — precisely the FR-005 anti-pattern. #3432/PR#3713 only fixed the *finalize*
path, not runtime move-task.

**Resolution folded**: promoted from a parked edge case to **FR-009** (+ SC-005) — closure required
(a canceled-with-provenance dependency must not strand a dependent); mechanism is a plan decision
(treat canceled-with-provenance as satisfying/removing the gate, or extend #3713's rejection to the
runtime path).

Anchors: `core/dependency_graph.py:59`, `cli/commands/agent/mission_finalize.py` (#3432 surface).

---

## F6 — HIGH (converged: debugger + reviewer + planner): FR-007/SC-003 rest on a nonexistent signal

The only structured per-WP mode is `WorkProductKind = {code_change, planning_artifact}`
(`ownership/models.py:21-30`) — no "action / post-integration-verifier" value. A detector must key
on **free-text** acceptance-criteria/subtask prose ("after merge", "consecutive runs",
"merge-blocked-when-absent"), a heuristic that cannot honestly guarantee **0% false positives**
(SC-003, AS-2). `research/` was empty; FR-007 is the highest-uncertainty requirement and the #3590
"product-contract decision" #3692 says to settle first.

**Resolution folded**: SC-003 downgraded from "100%/0%" to a **named, enumerable set of trigger
phrases** with a documented precision/recall expectation and explicit false-positive fixtures in
AS-2; the detection signal is a plan-phase decision record (directive 003); FR-007 is sequenced
**independently** of the accept work (US1) and behind that decision. Adding a minimal structured WP
field (`completion_kind: post_integration`) is an in-scope option for the plan to weigh.

Anchors: `ownership/models.py:21-30`, spec FR-007/SC-003/AS-2.

---

## F7 — HIGH (reviewer): regression baseline unpinned; gate-integrity unasserted

NFR-001/SC-004 promise "100% green / 0 regressions" but name no suites and no green baseline —
fakeable by running a subset, especially given the repo's baseline-red gotcha (known-P0 reds on
main, CI-only gates). Separately, the canceled-terminal change lives in the same
`_check_lane_gates`/`_evaluate_acceptance_matrix` path (`acceptance/__init__.py:932-940,1073-1074`)
that classifies lanes, so it can silently shift what `all_done` counts.

**Resolution folded**: NFR-001 now enumerates the concrete regression suites (see F8 list) and pins
the pre-change green baseline commit; a gate-integrity regression is required — a mission with a
canceled WP still runs and can still *fail on* the acceptance-matrix and issue-matrix-verdict gates
(canceled-terminal must not short-circuit sibling gates); and the "every WP canceled → not
complete" guard is an explicit check, not an accident of terminal-lane classification.

Anchors: `acceptance/__init__.py:498,932-940,976,1073-1074`.

---

## F8 — regression homes (debugger + reviewer): where the plan must add coverage

- **Unit (acceptable-ending predicate + provenance)**: `tests/status/test_transitions.py`,
  `tests/status/test_reducer.py` (if a reason slot is added).
- **Command-level accept**: `tests/specify_cli/test_canonical_acceptance.py`,
  `tests/specify_cli/test_acceptance_regressions.py`,
  `tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py` (already
  cancellation-aware — natural home for approved+canceled→eligible and
  canceled-without-operator-provenance→blocker).
- **Merge**: a mid-mission-cancel case whose lane branch exists (matching the #2945 repro), not
  only finalize-time exclusion.
- **Tasks-authoring (FR-007)**: no existing warning test; new coverage needed, including the AS-2
  false-positive fixture.

---

## F9 — LOW / boundary & hygiene (planner + architect + reviewer)

- **#3590 partially addressed**: label C-003 as *partial* (advisory warning + terminal-state exit
  now; decomposition-prevention / completion-contract redesign remain in epic #3550); confirm the
  issue is dispositioned "partial", not "closed". Add a decision record (directive 003) that
  verifier-deliverable missions are deemed **in scope** and handled by advisory warning rather than
  refusal.
- **Boundary vs shipped #3432/PR#3713**: terminal-lane exclusion in lane-compute/finalize already
  shipped; this mission does **not** touch `mission_finalize.py`/lane compute. State it (directive 010).
- **Shared merge surface with backlog #2745** (`merge --skip-lanes` for direct-on-target): FR-004's
  lane-skip predicate should compose with, not preempt, a future direct-on-target skip.
- **`canceled_wps` shape** (NFR-003): pin the object shape (`{wp_id, reason, actor, at}`) so the
  schema assertion is meaningful and carries provenance.
- **Coord-surface read** (architect LOW): the provenance read and FR-004 audit retention must read
  from the coord status surface (`resolve_status_surface`), not the open worktree or primary husk.
- **C-002 latent hazard** (architect MEDIUM): `acceptance/__init__.py:511`
  `get_lane_from_frontmatter` is misleadingly named but reads the event log via `get_wp_lane`
  (`task_utils/support.py:661-689`); no hidden frontmatter reader today. A boy-scout rename
  (`get_wp_canonical_lane`) is out of scope unless free.

---

## Decisions recorded (directive 003)

- **D1** — Verifier-deliverable missions (deliverable is its own verifier) are **in scope** for
  spec-kitty; handled by an **advisory** authoring-time warning (FR-007/FR-008), not refusal. The
  completion-contract redesign is deferred to epic #3550. (#3590 product-contract question.)
- **D2** — Cancellation provenance means **operator-authored** content, distinguishable from the
  CLI's synthetic default reason; a tool-synthesized reason does not satisfy the acceptance gate.
- **D3** — The dependency-on-canceled strand is **pulled into scope** (FR-009); leaving it out
  re-creates the mission's own trap.

## Verdicts

All four lenses returned **CHANGES REQUESTED / REQUEST CHANGES**. No irreconcilable divergence: the
one apparent conflict (FR-005 "consume is_terminal" vs "build an acceptable-ending predicate")
resolved decisively in the architect's favor on cited evidence, subsuming the planner's intent
(use canonical material; do not mint a parallel authority).
