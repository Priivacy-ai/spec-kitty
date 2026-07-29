# Contract: Coord-Authority Gate Idiom (FR-010) — implements ADR 2026-06-26-1

**Not a new ADR** — a citation contract for the gate change. Cites `2026-06-24-1` C-006, `2026-06-26-1` (gate-extension mechanism + non-vacuity confirmation), `2026-07-23-1`.

## Move A (default, STRENGTHENING) — route `decisions/emit.py` off the allowlist
Convert `decisions/emit.py:_mission_dir:71` to the kind-aware seam so it no longer calls the kind-blind `resolve_feature_dir_for_mission`. This drops the live write census 4→3 and requires, in the same change:
1. Re-pin `COORD_AUTHORITY_WRITE_FLOOR` 4→3 and `coord_authority_baseline` (with rationale).
2. Remove the stale `resolution_gate_allowlist.yaml` entry (staleness twin-guard).
3. Remove `emit.py` from `_COORD_WRITE_BY_DESIGN` (else `test_coord_authority_by_design_modules_classified_write` reds).
The `status.events.jsonl` COORD write MUST still land on the coord surface (no regression to primary).

## Move B (conditional) — recognize `write_target(<COORD kind>)` as sanctioned authority
Author ONLY if a seam-routed writer must resolve via the kind-blind resolver. Recognition MUST be **def-use gated** (the result of `write_target(kind=...)` flows to the write), mirroring `is_def_use_canonical`. A module/name-proxy exemption is forbidden.

## Non-vacuity proof (DIRECTIVE_003 obligation)
Record, in this contract and the gate module docstring, a test proving the gate still FAILS on: (a) a `write_target()` call with no `kind`, and (b) a re-introduced kind-blind wrong-surface write. A literal-vs-literal assertion is vacuous and disallowed.

## Sequencing
FR-010 is an **enabler** — it blocks the writer-routing concerns (IC-03…IC-07) only insofar as those route `emit.py`; new writers routed purely via `write_target` are invisible to the gate (D-6).
