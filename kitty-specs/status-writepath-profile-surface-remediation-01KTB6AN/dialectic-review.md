# Dialectical Review — status-writepath-profile-surface-remediation-01KTB6AN

Applied the `dialectic-research` tactic to the spec/plan: corroborator (thesis) and refuter (antithesis) run in parallel, blind to each other, then reconciled. Date: 2026-06-05.

## Claims under test

- **C1 (decisive):** Closing #1667 RISK-001 via tests + an integration test as "live caller" + documentation — without wiring a real production write caller — genuinely satisfies #1667 FR-019/FR-020.
- **C2:** Workstreams A and B share zero files / are independently shippable.
- **C3:** FRs fully cover the residual; contracts are implementable as written.
- **C4:** The #1672 narrow slice is correctly scoped and sufficient.

## Verdicts (reconciled)

| Claim | Verdict | Decisive evidence |
|-------|---------|-------------------|
| C1 | **REFUTED** | (1) transition()/save() unit tests already exist — `tests/unit/status/test_mission_status_aggregate.py:410,437,463,528`, added by PR #1682 (`cdc258002`). (2) `agent status emit` (the real write surface) calls `emit_status_transition_transactional` **directly** at `cli/commands/agent/status.py:275`, bypassing `MissionStatus.transition()`. The aggregate write path stays dead in production; D-1 (1b) punts the only unmet half ("no live caller"). |
| C2 | **SURVIVES** | File sets are disjoint (A: `status/aggregate.py`+tests; B: `profiles_cmd.py`, factory, `charter/context.py`, SKILL.md). Independence holds. The plan's "confined to context.py" framing was wrong (see C3). |
| C3 | **REFUTED (multiple errors)** | (a) `_build_doctrine_service` is at `charter/context.py:1235` and builds a plain `DoctrineService(**kwargs)` with **no PackContext**; line 244 is a different function — data-model.md:32 conflated them. (b) 6 callers of `_build_doctrine_service` → wrapping has multi-site blast radius. (c) `_read_meta` is already fail-closed (`aggregate.py:244-278`, #1682) → FR-006 is a no-op. (d) FR-011 is a `ProfileRegistry`→wrapper abstraction swap (NFR-001 byte-identity risk). (e) DIR-032 not met: "abstract base profile" is a new user-facing term absent from the glossary. **Survives:** factory layer-safety (import-safe); FR-007 slug guard is genuinely new. |
| C4 | **WEAKENED** | Ownership hazard is disclosed (C-008/D-3), not hidden. But the technical point binds to C1: extending the ratchet over `agent status emit` proves CWD-invariance of the *direct* transactional path, **not** of `MissionStatus.transition()` — so FR-008 as written would ratchet the wrong surface relative to the mission's stated purpose. |

## Root cause of the errors

The spec/research were built on the `01KT6HVH` **mission-review-report.md** (RISK-001/RISK-006), which was **stale**: follow-up PR #1682 ("address 6 non-blocking findings") landed afterward and already added the transition/save tests and the `_read_meta` fail-closed guard. The investigation did not re-check whether the review's findings had since been remediated. Lesson: verify issue/risk state against *current* `main`, not the artifact that first reported it.

## Salvaged partial truths (refuted ≠ worthless)

- **FR-007 (slug allowlist guard)** is genuinely absent from `MissionStatus.load()` — real, small hardening.
- **Workstream B (#1636)** is substantively valid — the activation-blind `profile list` + missing `profile show` are real gaps; only the contracts need correction (FR-016 line/blast-radius, FR-011 swap vs filter, DIR-032 glossary).
- The refuter surfaced a **separately-actionable finding**: the real #1667 domain-ownership goal (route the live write surface through the aggregate) is unmet and properly belongs to #1673's residue routing — worth tracking, not silently dropping.

## Revised position (synthesis)

1. **Workstream A is ~delivered.** #1682 closed the coverage + fail-closed halves of RISK-001. Reduce A to: **FR-007 only**, and a decision on the write-surface wiring.
2. **Re-open D-1 honestly** as the real fork: **(X)** declare #1667 substantively delivered and **close it** (the live-surface wiring is #1673's job), mission = #1636 + FR-007; **OR (Y)** wire `agent status emit` through `MissionStatus.transition()/.save()` for true FR-019/020 closure, accepting overlap with #1673. **Recommendation: (X)** — the aggregate exists, is tested, and is fail-closed; forcing a re-wire here duplicates #1673 and risks the live write path.
3. **Workstream B stays**, with corrected contracts (FR-016, FR-011, DIR-032).
4. **FR-008** only makes sense under (Y); under (X) it is dropped (the ratchet already covers the read; there is no new aggregate write surface to ratchet).

Provenance: corroborator + refuter subagent transcripts (2026-06-05); all facts re-verified against working-tree `src/` before reconciliation.
