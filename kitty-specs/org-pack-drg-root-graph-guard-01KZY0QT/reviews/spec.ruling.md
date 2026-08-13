# Operator ruling — spec phase HALT

**Mission**: `org-pack-drg-root-graph-guard-01KZY0QT` (GitHub issue #3384)
**Phase**: `spec`
**Ruled**: 2026-08-13, by the operator, relayed by the mission orchestrator
**Trigger**: R6 gate HALT after round 4 — the blocking (severity ≥3) count did not fall
(1 → 1) and the surviving finding's severity rose from 3 to 4, so the early-stop rule fired.

This ruling **REPLACES the acceptance bar** for the finding below. A verifier handed the
original bar will re-derive the original verdict and HALT the phase a second time on a
question that has already been answered. Verify against the bar stated here.

---

## SPEC-FRESH4-001 (severity 4) — RULED, bar replaced

**The finding, upheld as factually correct.** It was independently verified against the code
by the orchestrator before ruling:

- `charter context --action <a> --json` exposes typed arrays for `directives`, `tactics`,
  `styleguides` and `toolguides` only. `build_disclosure_payload`
  (`src/charter/progressive_disclosure.py:325`) receives those four via `repos_by_kind` and
  receives `procedure` via `extra_delivered`. Its own docstring states the consequence
  verbatim: the `procedure`/`asset` kinds are *"delivered but not surfaced as their own
  arrays"*.
- The plain-text render **does** emit a distinct Procedures section:
  `src/charter/context_renderers/bootstrap_text.py:106` —
  `_ActionRenderRow("Procedures", "procedure_ids", "procedures", "name", "purpose")`.

So FR-005 / SC-001 / User Story 1 AC1, as written, mandate a procedure-count assertion
through a payload that cannot express one.

**Why it mattered enough to halt**: issue #3384's own reproduction measures
`procedures=10 → 0`. Procedures are one of the five artifact kinds the defect zeroes, so a
regression test that omits them does not prove the fix for that kind.

### The replacement acceptance bar

> Assert the four typed counts (`directives`, `tactics`, `styleguides`, `toolguides`) via
> `charter context --action <a> --json`, and assert the **procedure** count via the
> **plain-text render**, which already ships a Procedures section. All five zeroed kinds stay
> asserted, so the non-vacuous regression gate survives intact.

The finding is **resolved** when FR-005, SC-001 and User Story 1's acceptance criteria state
that split explicitly — the four typed counts from `--json`, the procedure count from the text
surface — and no requirement in the spec claims `--json` exposes a procedure count or a
`procedures` array.

### Rejected alternatives, and why

- **Add a `procedures` typed array to the `--json` payload in this mission.** This is the
  cleanest end state and is *not* being done here: the payload is a versioned public contract
  (`context_schema_version`, and `charter.context_contract`'s key ledger), so extending it is a
  contract change. That is real scope growth on a narrow P0 fix, and it cuts against both
  smallest-viable-diff/locality and the operator's standing Q2 answer to keep this mission to
  one issue. **Filed as a separate follow-up issue instead** (see below).
- **Count procedures out of the top-level `references` link set.** Plausible — `references`
  names every delivered artefact including procedures — but it depends on reference entries
  exposing a kind-filterable URN, which was not confirmed. Not taken.
- **Drop the procedure assertion.** Rejected: procedures are one of the kinds the bug zeroes,
  so this would weaken the mission's flagship non-vacuous gate — the precise outcome the fresh
  sweep raised the finding to warn about, and a violation of charter standing order #5.

### Follow-up filed

The `--json` procedure-array asymmetry is tracked as
[**#3389**](https://github.com/Priivacy-ai/spec-kitty/issues/3389) — *"charter context --json
omits a procedures[] array while the text render ships a Procedures section"*. It is **out of
scope for this mission** and must not be folded into it.

---

## SPEC-FRESH4-002 (severity 2) — NOT ruled; fix normally

Vestigial rule text: the `--json` convention's third carve-out ("may be omitted for
exception-only assertions with no numeric/ID comparison") is never exercised by any User
Story. No bar replacement — this goes through the ordinary fix round like any other finding.
Severity gates halting, not fixing.

---

## Re-entry

Per the review protocol, a HALT is terminal for the loop and there is no resume that carries a
ruling — hence this file. The phase re-enters as: **one final R4 fix round** targeting exactly
SPEC-FRESH4-001 (against the replacement bar above) and SPEC-FRESH4-002, then **a single
R5a anchored verification**, with no fresh sweep and no further rounds. All `resolved` → the
phase passes and the full `reviews/` trail is committed. Anything still `unresolved` → HALT
again, back to the operator.
