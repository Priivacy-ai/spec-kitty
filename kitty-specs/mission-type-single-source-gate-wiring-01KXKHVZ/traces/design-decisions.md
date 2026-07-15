# Tracer — Design Decisions

Seeded at planning; appended during implementation; assessed at close.

## DD-1 — Canonical accessor lives in the doctrine layer (not charter)

`doctrine → charter` is forbidden; `charter → doctrine` is legal. The single authority for "the built-in
mission-type set" therefore lives in doctrine (next to `MissionTypeRepository`), and charter consumers reach
it lazily. This keeps unification without inverting the layer dependency.

## DD-2 — Unification, not parity (rosters derive; they are not guarded literals)

Per charter Governing Principle + gotcha 6, the rosters are *derived* from the accessor, not kept as literals
with a drift-guard test. A guard test would leave two authorities in sync — that is parity, the anti-pattern.

## DD-3 — rc35 migration reads the LIVE repository (operator override of squad rec) — C-004

**Trade-off, accepted by the operator on 2026-07-15.** The pre-spec squad (paula) recommended keeping the
version-pinned rc35 migration roster a frozen literal + a drift-guard test, to preserve historical migration
determinism: a project replaying/upgrading through rc35 after a 5th built-in type ships should get exactly
the four types rc35 promised. The operator chose instead to have the migration read
`MissionTypeRepository.default().ids()` at `apply()` time, so it auto-picks-up new types and stays coherent
with the single source. Consequence to remember: rc35's *written* activation set is now a function of
whatever built-ins ship at run time, not a fixed historical snapshot. If a future mission needs deterministic
replay of rc35, revisit this.

## DD-4 — `load_action_index`: present ⇒ well-formed; absent ⇒ empty (broad fail-loud) — operator decision

The operator chose the broad line: a present-but-unparseable YAML also raises `ActionIndexError`, not just a
parseable-but-wrong-shape index. Only a genuinely-missing file stays a silent fallback. This fully closes the
FR-013 false-pass class rather than matching the issue's narrower "malformed-but-parseable" wording.

## DD-5 — #2666 built-in scope now; project/org override coverage deferred

The action-grain multi-root engine is explicitly out of scope in `action_grain.py`. Wiring the built-in scan
into `doctor doctrine` + a CI gate closes "fires nowhere outside pytest"; full project-tier override collision
detection is a tracked follow-up under #2652.

## DD-6 — Delivery order is correctness-bearing (C-002/C-003)

#2667 before #2666 (else the wired gate is partially vacuous over a silently-degraded index). The `__all__`
re-add (#2666 FR-010) must land with its src caller (FR-009) or the dead-symbol gate fails. #2668 last to
absorb churn on the two shared lines.
