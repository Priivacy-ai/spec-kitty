# Tracer — Approach

Mission: `mission-resolver-port-01KX1C05` · #2173 Phase-2 MissionResolver port.
Seeded at planning. **Append as the approach is refined/validated during implement; assess at close.**

## Intended WP shape — see plan.md Implementation Concern Map (IC-01..IC-06, revised full-trunk)

Superseded by the post-squad plan revision. Canonical IC map is in `plan.md`:
- **IC-01** resolver port + walk trunk (Protocol in `mission_runtime`; adapters in `context`; free
  `resolve_mission` gains `resolver` param).
- **IC-02** thread the seam through the canonicalizer chain + shell callers + the 8 free-fn callers (the
  trunk); NFR-001 identity-leg FS-free test.
- **IC-03** legacy-`<slug>` sentinel reconciliation (D-07).
- **IC-04** ADR + AST gate (seed ~16-walker allowlist) + free-fn-caller audit.
- **IC-05** #2139 reconcile — all ≥9 readers (or triage).
- **IC-06** Clock (12+2 triaged; preserve stamp/datetime; SAFE literal fold) + InstalledVersion + #2447.

Dependency hint: IC-01 → IC-02 → IC-03; IC-04 follows IC-01/02; IC-05/IC-06 independent siblings. Final
lanes decided at finalize-tasks.

## Adopt-don't-duplicate SSOTs (must reuse, verified in scout)
- `PlacementSeam` (`mission_runtime/resolution.py:1266`) — the resolver yields dirs *through* this seam's grammar; do not compose paths (the `test_no_raw_mission_spec_paths.py` gate bites otherwise).
- `_canonicalize_primary_read_handle` (`_read_path_resolver.py:1243`) — handle-form canonicalization delegates here; the port does identity→dir only.
- `resolve_mid8` / `mission_dir_name` (`lanes/branch_naming.py`) — the mid8 SSOT.

## Existing DI precedent to copy (not reinvent)
- `RuntimeEventEmitter` Protocol + `NullEmitter` (`runtime/next/_internal_runtime/events.py:67/95`); wiring `emitter or NullEmitter()` (`engine.py:191`). This is the exact `x or Default()` idiom.

## Verification approach
- Per drained site: full `tests/architectural/` run + repo-wide floor-constant grep, from the **primary checkout** (marker gates are vacuous under `.worktrees/` — NFR-002).
- Floors are shrink-only; a genuine drain lowers a floor, never raises it.

## Refinements during implement
_(append here)_
