# Quickstart — Validation Batteries

How to prove the mission's two load-bearing properties for any migrated gate.
These are the acceptance batteries behind NFR-001/NFR-002/SC-001/SC-002.

## Motion battery (NFR-001 — 0 false reds)
For each migrated gate, prove pure code motion keeps it green:

1. **Blank/comment insert** — insert N blank lines above a guarded, allow-listed
   site in the guarded production module; run the gate → **green**.
2. **Multi-line insert** — insert a helper function above the site → **green**.
3. **Symbol relocation** (WS2 only) — move an allow-listed symbol to another
   module, name + body unchanged; run `test_no_dead_symbols` → **green**, no
   allow-list edit.
4. **Cross-lane line shift** — simulate a rebase that shifts every line in the
   file (e.g. prepend a module docstring) → **green**.

Automate as a parametrized self-test that applies the motion to an in-memory copy
of the source and asserts the gate's finding-set / key-set is unchanged.

## Bite battery (NFR-002 — 100% caught)
For each migrated gate, prove it still fails on a genuine offender:

1. **New un-allowlisted offender** — plant a new banned call / dead `__all__`
   export / raw path join → gate **reds**, names it.
2. **Resurrected/removed** — remove the last caller of a live symbol (dead) or
   re-add a deleted banned call → **reds**.
3. **Same-qualname sibling (the D-1 case)** — in the SAME function as a
   sanctioned allow-listed site, plant a *second, un-sanctioned* offender with an
   identical token line → the gate **reds** (proves exactly-one resolution +
   key-equal staleness did not silently absorb it under the sanctioned entry).
4. **WS2 T004** — mark one of a same-name pair dead (`doctrine.tactics::ArtifactKind`)
   while its sibling is sanctioned → `test_no_dead_symbols` **reds** the dead one
   (proves the key is not bare-name).

## Meta-guard (FR-004) smoke
- Plant an integer line component in an authoritative seed anywhere under
  `tests/architectural/` → `test_ratchet_positional_anchor_ban` **reds**.
- The two DIR-041-compliant YAMLs' non-authoritative `line:` fields and the
  count-floor baselines → **stay green** (authoritative-vs-diagnostic rule).

## Suite gate (NFR-004)
`PWHEADLESS=1 uv run pytest tests/architectural/ -q` → **869 passed / 0 failed**
(4 skipped) at every WP boundary.
