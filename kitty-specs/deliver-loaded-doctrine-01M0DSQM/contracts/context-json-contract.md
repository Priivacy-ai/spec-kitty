# Contract — `charter context --json` Payload (WP-C, versioned)

## C-C1 Typed procedures[] array
- When an action delivers procedures, the `--json` payload carries a top-level `procedures[]` array (the fifth typed array alongside `directives`, `tactics`, `styleguides`, `toolguides`).
- Each `procedures[]` entry carries the same per-entry decoration (`references[]`, `delivery` cadence marker) the other typed arrays carry, via `build_disclosure_payload` / `collect_typed_artifacts`.
- `procedure` is no longer folded ONLY into the flat `references[]` (it remains in `references[]` as before for link completeness, but is now ALSO a typed array).

## C-C2 Asset stays reference-only (stated)
- `asset` remains delivered via `extra_delivered` → surfaced only in `references[]`, with NO typed `assets[]` array.
- This asymmetry is stated deliberately in `context_contract.py` (no resolution/install path exists — #3037).

## C-C3 Versioned-contract bump (atomic)
- `CONTEXT_SCHEMA_VERSION` bumps `1.0.0` → `1.1.0` (MINOR — additive key) in the SAME change that adds the array.
- `"procedures"` is added to `CONTEXT_CONTRACT_TOP_LEVEL_KEYS` in the same change.
- Guard: `tests/charter/test_context_parity.py` — no undeclared top-level key may escape the ledger; the bootstrap-payload structural guard sees `procedures`.

## C-C4 Behaviour preservation
- For an action that delivers NO procedures, `procedures[]` is present-but-empty or absent per the existing typed-array convention (same as `directives`/`tactics` when empty); no other top-level key changes shape.
