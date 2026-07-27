# Contract — Inline meta.json Read Ratchet (new gate)

**Requirement**: FR-006 · **NFR-002** · **IC-06**

## Purpose

Establish the first architectural gate that keeps inline `json.loads(<meta_path>)` reads drained after IC-05
routes them onto `load_meta`. Modeled on the existing `test_resolution_authority_gates.py` +
`resolution_gate_allowlist.yaml` machinery — do NOT invent a weaker shape.

## The scanner

An AST/heuristic scanner over `src/` that flags an inline meta read: a `json.loads(...)`/`json.load(open(...))`
whose argument derives from a `meta.json` path (var names `meta_path|meta_file|meta_json|target_meta_path`, or a
`<dir> / "meta.json"` join), **excluding** `mission_metadata.py` internals and the `task_utils` adapter.

## Gate mechanics (all four required — this is the non-vacuity contract)

1. **Integer floor** — `INLINE_META_READ_FLOOR = <post-drain count>`; the live count MUST be `≤ floor`.
2. **Margin** — a `FLOOR_MARGIN`; `live − margin ≤ floor < live` (prevents a floor pinned far above the live
   count from masking regressions).
3. **Routed-count floor (anti-mass-allow-list)** — mirrors `ROUTED_CANONICALIZER_FLOOR`: the number of routed
   (`load_meta*`) sites has its own floor and can only rise. An attempt to "drain" by mass-allow-listing rather
   than routing trips this floor.
4. **Composite-key allow-list with stale-entry detection** — each remaining/deferred site is a
   `{key, rationale, issue}` entry. `allowlist_keys − live_keys` non-empty ⇒ FAIL (a routed-away entry must be
   deleted, never left masking). Every deferred `m_0_13_*` entry carries a filed follow-up issue number.

## Invariants

- **INV-C2**: a newly-introduced inline meta read goes RED (self-test plants one and asserts the gate bites).
- **Shrink-only**: the floor may only decrease across missions; a raise requires an explicit justified edit.
- **No vacuous exemption**: a deferral is an allow-list entry (rationale + issue), never a scanner path-exclude
  of a whole tree (the `migration/` blanket-exclude is rejected — only `m_0_13_*` is deferred, per-entry).

## Self-tests (ship with the gate)

- `test_new_inline_meta_read_is_flagged` — plant → RED.
- `test_allowlist_entries_are_still_live` — stale-entry twin-guard.
- `test_routed_count_floor_blocks_mass_allowlist` — mass-allow-list attempt → RED.
