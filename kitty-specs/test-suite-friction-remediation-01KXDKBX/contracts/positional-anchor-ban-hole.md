# Contract — Positional-anchor ban: seed-tuple laundering hole (IC-04 / FR-005, P1)

## Behaviour
- GIVEN a module-level allowlist seed constant holding a raw `(rel_path, int_line)` tuple,
  AND that `int_line` reaches the 2nd positional arg of `composite_key(source, N)` / `composite_key_from_file(path, N)` via an intermediate loop or local variable,
  WHEN the positional-anchor ban runs,
  THEN it MUST flag the seed as a banned int-to-line-sink (the laundering vector is closed).
- GIVEN a `composite_key(source, N)` where `N` is a genuine live line obtained from `code_tokens_by_line(...)` at runtime,
  WHEN the ban runs,
  THEN it MUST NOT flag it (no false positive on legitimate content-addressed keys).

## Non-fakeable evidence
- A regression fixture that *attempts* the laundering fails the ban.
- `git grep -nE '\.py", *[0-9]{3}\)' tests/architectural/` returns **zero** (the residual raw seed tuples in `test_no_write_side_rederivation.py` / `test_trio_seam_only.py` are converted to content-addressed keys).
- `test_ratchet_positional_anchor_ban.py` is green on the real (non-fixture) tree.

## Notes
- The predicate stays **int-to-line-sink**, not "positional anchor in general" — `module::Name` / `path::qualname` symbol-identity keys are explicitly allowed (they are the relocation-proof keys, and banning them would be circular with FR-014's permanent census deferral).
