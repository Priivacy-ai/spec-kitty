# Operator ruling — spec phase HALT, mission `design-phase-orchestrator-api-01M1HE6M`

Date: 2026-09-02. Issued by the operator (Human-in-Charge) via the mission orchestrator.

The spec phase HALTed under the R6 early-stop rule after two full R4→R5 rounds: the
severity≥3 finding count rose 1→2 between fresh-sweep rounds rather than falling, so the loop
stopped instead of sampling further rounds. Three findings survived, recorded verbatim in
`spec-fresh-2.yaml`.

**This ruling REPLACES the acceptance bar for SPEC-FRESH2-001.** A verifier handed the
original bar would re-derive the original verdict and HALT the mission a second time on a
question that has now been answered.

## Ruling on SPEC-FRESH2-001 (severity 4) — require parity, via an extracted shared seam

The finding offered two remediations: require the side effects, or document their omission as
a deliberate scope boundary. **The operator chose to require them**, and specifically to reach
them through a seam extracted from `next_cmd.py` that BOTH the host CLI and orchestrator-api
call — not by inlining or duplicating the calls into the orchestrator-api layer.

The spec must therefore require that `answer-decision` performs the equivalent of
`_pair_previous_lifecycle_record`, `_emit_mission_next_invoked` (mission event-log write) and
`_write_issuance_lifecycle_record`, alongside the two engine calls it already specifies.

Rationale, so a plan-phase author need not re-derive it:

1. **The issue's own premise.** #3837 exists because external hosts driving design phases
   today must shell the host CLI, which the boundary rules forbid. A verb that returns the
   right-looking JSON while failing to advance the event and lifecycle logs does not remove
   that need — it replaces a documented boundary violation with a silent behavioural
   divergence, which is worse because nothing surfaces it.
2. **Self-consistency within this mission.** This mission also specifies a `design-status`
   query verb that READS the mission event log. An `answer-decision` that does not write to
   that log makes the mission internally incoherent: its own status verb would under-report
   progress driven through its own answer verb.
3. **Silent success is this repository's named dominant failure mode** (charter; spec-kitty
   overlay §1a; issues #3133, #3212, #3282, #3336). A code path that reports success while
   omitting part of its work is that class exactly, and the charter treats it as a defect
   class rather than a style preference.
4. **Why extract rather than inline.** Inlining would put orchestrator-api code in reach of
   CLI-layer helpers, which the architecture lens would file against at implementation time,
   and would duplicate logic that then drifts from the CLI's own copy. Extraction costs a
   refactor work package; the operator accepted that cost explicitly.

**Consequence for scope, stated so it is not discovered later:** this enlarges the mission.
The plan and tasks phases must carry a work package for the seam extraction, sequenced before
the verbs that depend on it, and must state what happens to the host CLI's own call sites
(behaviour-preserving refactor, covered by a test that fails if either caller stops writing
the logs).

## Ruling on SPEC-FRESH2-002 (severity 3) and SPEC-FRESH2-003 (severity 2)

No operator ruling required — both carry concrete, uncontested remediations and are to be
fixed as written:

- **002**: state explicitly whether `answer-decision`'s `data` carries an equivalent of the
  CLI's `answer` key (the echoed submitted answer), or that it is intentionally omitted and
  why. Either answer is acceptable; silence is not.
- **003**: correct both occurrences of the citation `next_cmd.py:246-248` to
  `next_cmd.py:248-250`, the actual `decide_next(...)` call.

## How the phase closes

One final targeted R4 fix round covering all three findings, then a single R5a anchored
verification against the bar set by this ruling. No further fresh sweep, no further rounds.
All resolved → the phase passes and the whole `reviews/` trail is committed with the phase.
Anything still unresolved → HALT again, back to the operator.
