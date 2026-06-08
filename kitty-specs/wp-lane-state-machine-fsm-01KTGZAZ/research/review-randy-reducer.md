# Adversarial review — randy-reducer (sonnet, leanness)

**Change:** `fix/status-genesis-lane-bootstrap` @ `a43aa6a06`.
**Verdict:** **TRIM-RECOMMENDED.** Core goals achieved (derivation replaces dual-source literal; clobber fix focused). Avoidable complexity below.

## Findings

**1. [MEDIUM] Three zero-caller FSM interface methods.** `wp_state.py`: `current_lane` (property), `may_transition_to()`, `transition_to()` — **zero call sites** in `src/` or `tests/`. Every existing FSM caller uses `.lane` directly. `transition()` itself has no production caller (production goes through `validate_transition` + `emit_status_transition`). Leaner: remove, OR (per operator directive that mandated this interface) document the intent in the ADR and migrate some callers to lock them in. NOTE: this finding conflicts with the operator's explicit requirement for the interface — resolution is to KEEP + lock in, not remove.

**2. [LOW-MED] Stale module docstring `emit.py:15`:** "2. Derive from_lane … (or 'planned')" — now `genesis`. Fix the prose.

**3. [LOW-MED] Stale PLANNED default in `tests/utils.py:75`** (`_seed_canonical_wp_state` uses `Lane(current_lane or "planned")`). Not called on an unseeded WP in the diff, but a ticking inconsistency (would fabricate an illegal planned event for a now-genesis WP).

**4. [MEDIUM] 12 independent `_seed_planned` definitions** across `tests/status/`, `tests/agent/`, `tests/integration/`, `tests/lanes/`, `tests/specify_cli/`, `tests/sync/`, `tests/cli/` — all introduced by the diff, all doing the same `genesis->planned` seed. Leaner: one parameterized fixture in `tests/status/conftest.py` (+ one in `tests/conftest.py` for the rest). At worst two definitions replacing twelve.

**5. [LOW] genesis leaks into every snapshot summary as `"genesis": 0`** (`reducer.py`), contradicting the ADR's "no board-summary key". Three fixtures updated to include it. `test_summary_has_all_lane_keys` passes only against a hand-built fixture. Fix: exclude genesis from the summary dict; make the test enforce the real invariant.

**6. [INFO] `_derive_allowed_transitions` indirection justified; old literal fully gone.** No duplication remains; import-cycle `# noqa: PLC0415` correctly scoped. Lean.

**7. [INFO] `GenesisState` minimal; `# noqa: ARG002` matches existing terminal-state pattern; `display_category → "Planned"` defended by comment.** No board column introduced.

## Verdict rationale
Top items to trim: Findings 4 (twelve `_seed_planned` copies — compounds on every future seeded-WP test) and 1 (three zero-caller FSM methods — but operator-mandated, so KEEP + lock-in rather than remove). Findings 2/3/5 are quick hygiene.
