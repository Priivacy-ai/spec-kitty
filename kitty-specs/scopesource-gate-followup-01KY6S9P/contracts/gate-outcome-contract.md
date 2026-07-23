# Contract: `GateOutcome.SOURCE_MISMATCH` — warn-shaped, fail-open by construction

**Traces**: FR-011, SC-004, C-003 (no new hard-stop)
**Homes**: `pre_review_gate.py:748-756` (member), `verdict_aggregation.py:58-138` (allowlists),
`tasks_move_task.py:1156-1184` (console ladder)

## The member

```python
# round-trip: skip: illustrative enum add — executable coverage in tests/review/test_pre_review_gate_engine.py
class GateOutcome(StrEnum):
    NO_COVERAGE = "no_coverage"
    NO_NEW_FAILURES = "no_new_failures"
    NEW_FAILURES = "new_failures"
    UNVERIFIED_BASELINE = "unverified_baseline"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    SOURCE_MISMATCH = "source_mismatch"   # NEW — warn-shaped, distinct reason
```

| Property | Value |
|----------|-------|
| Verdict shape | warn: `transition_applied=True`, `run_state=COMPLETED`, distinct `reason` |
| Emitted by | `_evaluate_via_scope_source` (`pre_review_gate.py:851-909`), at diff time, when head identity ≠ a **known** `baseline.source_identity` |
| NOT | `NO_COVERAGE` (empty-scope/no-config) and NOT `NEW_FAILURES` (block) — never overload either |
| `reason` | names both identities, e.g. `"baseline captured under GateCoverageScopeSource/junit_xml; head ran under DeclaredCommandScopeSource/text — failure identities are not comparable"` |

## Fail-open-by-allowlist proof obligation

Both hard-stop paths are **member-explicit allowlists**, so a new member fails open automatically. The
mission MUST assert this with a test and MUST NOT edit the filters (FR-011).

| Path | Site | Filter | `SOURCE_MISMATCH` present? |
|------|------|--------|---------------------------|
| Terminal (hard-stop) | `verdict_aggregation.py:58-60` (`_TERMINAL_OUTCOMES`), consumed `:99-104` | `frozenset({TIMED_OUT, CANCELLED})` | no → never terminal |
| Block (hard-stop) | `verdict_aggregation.py:138`, predicate `_should_block` `:107-111` | `v.outcome is GateOutcome.NEW_FAILURES` | no → never blocks |
| Warn / proceed | `verdict_aggregation.py:148-154` | fall-through default | yes → `WARN_PROCEED` |

**Assertion (SC-004):** feed `aggregate_verdicts([GateVerdict(outcome=SOURCE_MISMATCH, …)],
block_enabled=True, force=False)` → `decision == WARN_PROCEED`, `should_exit is False`,
`transition_applied is True`. Do the same via a full for_review transition and assert the move
completes (no `Exit(1)`), a `SOURCE_MISMATCH` console warn is shown, and it is neither a silent pass
nor a `NO_COVERAGE`.

## Console-ladder invariant (the ONE live edit)

`_mt_pre_review_gate_console_warning` (`tasks_move_task.py:1156-1184`) today ends in an
**unconditional** fall-through (`:1184` — `return "[dim]…no new failures[/dim]"`). Any non-handled
member renders as a clean pass. Rewrite:

```python
# round-trip: skip: illustrative ladder shape — executable coverage in tests/.../test_tasks_move_task*.py
    if outcome is GateOutcome.NEW_FAILURES:
        ...                                              # unchanged (:1166-1173)
    if outcome in (GateOutcome.NO_COVERAGE, GateOutcome.UNVERIFIED_BASELINE):
        ...                                              # unchanged (:1174-1181)
    if outcome in (GateOutcome.TIMED_OUT, GateOutcome.CANCELLED):
        ...                                              # unchanged (:1182-1183)
    if outcome is GateOutcome.SOURCE_MISMATCH:           # NEW explicit branch
        return f"[yellow]Pre-review regression gate: source/parse-mode mismatch — {verdict.reason}[/yellow]"
    if outcome is GateOutcome.NO_NEW_FAILURES:           # was the implicit fall-through
        return "[dim]Pre-review regression gate: no new failures[/dim]"
    return f"[dim]Pre-review regression gate: {outcome.value}[/dim]"   # DEFENSIVE else — never a green pass
```

**Invariant:** after this change no `GateOutcome` member renders as "no new failures" unless it *is*
`NO_NEW_FAILURES`. A test enumerates every member through the ladder and asserts none but
`NO_NEW_FAILURES` yields the clean-pass string; the defensive `else` renders `outcome.value`.

## What this contract does NOT change

- `_TERMINAL_OUTCOMES` and the `NEW_FAILURES` block filter — left exactly as-is (C-003); their
  member-explicitness IS the fail-open proof.
- `aggregate_verdicts` precedence / `AggregateDecision` (`verdict_aggregation.py:63-154`).
- `GateVerdict` dataclass (`pre_review_gate.py:759-768`).
</content>
