# Contract: Coord-Authority Gate Idiom (FR-010) — implements ADR 2026-06-26-1-single-authority-seam-and-call-site-gate

**Not a new ADR** — a citation contract for the gate change. Cites `2026-06-24-1` C-006, `2026-06-26-1-single-authority-seam-and-call-site-gate` (gate-extension mechanism + non-vacuity confirmation), `2026-07-23-1`.

**ADR status note (m5):** `2026-06-26-1-single-authority-seam-and-call-site-gate` is currently `status: Proposed` but is **de-facto shipped** (the gate it governs is live). This mission re-pins the floor that ADR governs (Move A) and names it the Move B amendment target. **Escalated decision (pending HiC):** ratify it to Accepted within WP02, or keep it Proposed-but-shipped with this acknowledgment. Until ratified, treat it as binding-in-practice.

## Move A (default, STRENGTHENING) — route `decisions/emit.py` off the allowlist
Convert `decisions/emit.py:_mission_dir:71` to the kind-aware seam so it no longer calls the kind-blind `resolve_feature_dir_for_mission`. This drops the live write census 4→3 and requires, in the same change:
1. Re-pin `COORD_AUTHORITY_WRITE_FLOOR` 4→3 and `coord_authority_baseline` (with rationale).
2. Remove the stale `resolution_gate_allowlist.yaml` entry (staleness twin-guard).
3. Remove `emit.py` from `_COORD_WRITE_BY_DESIGN` (else `test_coord_authority_by_design_modules_classified_write` reds).
The `status.events.jsonl` COORD write MUST still land on the coord surface (no regression to primary).

**Route ONLY `emit.py` — the other three write sites stay.** `widen/state.py:63`, `agent_tasks_ports.py:322`, and `lanes/recovery.py:765` are **by-design sanctioned** kind-blind coord writes and MUST remain on `resolve_feature_dir_for_mission`; the re-pinned floor (3) counts them to prove non-vacuity. Routing all four → census 0 → vacuous gate (forbidden). See the by-design section of `write-seam-adoption.md`.

**Non-vacuity invariant:** the live kind-blind coord-write census MUST NOT drop below the re-pinned floor of 3. Lowering the floor again requires the same rationale + a preserved non-vacuity proof.

## Move B (conditional) — recognize `write_target(<COORD kind>)` as sanctioned authority
Author ONLY if a seam-routed writer must resolve via the kind-blind resolver. Recognition MUST be **def-use gated** (the result of `write_target(kind=...)` flows to the write), mirroring `is_def_use_canonical`. A module/name-proxy exemption is forbidden. **Move B, if triggered, is an ADR amendment of `2026-06-26-1-single-authority-seam-and-call-site-gate` (the gate mechanism lives there), not a contract-only predicate widen** — amend the ADR in the same change.

## Non-vacuity proof (DIRECTIVE_003 obligation)
Record, in this contract and the gate module docstring, a test proving the gate still FAILS on: (a) a `write_target()` call with no `kind`, and (b) a re-introduced kind-blind wrong-surface write. A literal-vs-literal assertion is vacuous and disallowed.

## Sequencing
FR-010 is an **enabler** — it blocks the writer-routing concerns (IC-03…IC-07) only insofar as those route `emit.py`; new writers routed purely via `write_target` are invisible to the gate (D-6).
