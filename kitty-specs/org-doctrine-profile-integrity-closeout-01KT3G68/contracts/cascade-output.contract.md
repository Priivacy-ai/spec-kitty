# Contract — Activation/cascade operator output (FR-008, I-5)

## C1 — No stale deferral warning
- **Given** an activatable artifact
- **When** `spec-kitty charter activate <kind> <id> --cascade all` runs (and the `deactivate` equivalent)
- **Then** the output MUST NOT contain "not yet implemented" or "deferred" (cascade-deferral) text
- **And** cascade still performs correctly (referenced targets activated; shared-reference-safe on deactivate)

## C2 — Coherent single message
- The command emits one coherent cascade result; it does not simultaneously claim the feature is unimplemented and report cascade results.

## Implementation note (R3, revised — A2/P-2/DD-3)
- The fix is to **delete both** stale warning branches in `pack_manager` (the `if cascade:` ~424-429 AND the `if not cascade:` ~417-423 for activate; ~493-498 for deactivate). Passing `cascade=False` does NOT work — it merely fires the *other* "deferred" branch. The `cascade` parameter is vestigial (no behavioral effect; real cascade is CLI-owned via `charter.cascade`).

## Test
- A test asserts the absence of "not yet implemented"/"deferred" in `--cascade` output for **both** activate and deactivate, alongside the existing cascade-behavior assertions.
- **Update existing tests (DD-4):** `test_activate_cascade_calls_with_true` and `test_activate_cascade_flag_accepted` pin the old behavior and MUST be updated to the new contract.
