# Contract — Activation/cascade operator output (FR-008, I-5)

## C1 — No stale deferral warning
- **Given** an activatable artifact
- **When** `spec-kitty charter activate <kind> <id> --cascade all` runs (and the `deactivate` equivalent)
- **Then** the output MUST NOT contain "not yet implemented" or "deferred" (cascade-deferral) text
- **And** cascade still performs correctly (referenced targets activated; shared-reference-safe on deactivate)

## C2 — Coherent single message
- The command emits one coherent cascade result; it does not simultaneously claim the feature is unimplemented and report cascade results.

## Test
- A test asserts the absence of the deferral substring in `--cascade` output for both activate and deactivate, alongside the existing cascade-behavior assertions.
