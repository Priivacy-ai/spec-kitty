# Contract — Standing Positional-Anchor Ban (IC-METAGUARD, FR-004)

New test `tests/architectural/test_ratchet_positional_anchor_ban.py`. Generalizes
DIR-041 `anchoring.is_file_line_anchor` / `FORBIDDEN_POSITIONAL_FIELDS` from the
Contract Registry to every ratchet allow-list. Delivers #2077's recurrence guard.

## What it scans
- **All Python** under `tests/architectural/`: allow-list seed constants
  (module-level tuples/frozensets/dicts feeding a set-membership or comparison).
- **The two YAML allow-lists**: `resolution_gate_allowlist.yaml`,
  `inline_meta_read_allowlist.yaml`.

## Rule
- **BAN**: an integer used as a *line anchor* in an **authoritative comparand** —
  a seed/key later read for set-membership, key-equality, or staleness comparison.
- **PERMIT**:
  1. A **non-authoritative `line:` locator** field explicitly documented as
     "navigation only; no comparison/membership/count reads it" (the existing
     convention in the two YAMLs).
  2. **Count-floor baselines** (an integer that is a *count*, not a position).
  3. An `occurrence` ordinal inside a ContentDescriptor (a scan index, not a line).

## Authoritative-vs-diagnostic detection
Classify a tuple/field as authoritative iff its value flows into a
set-membership/`==`/`<=` comparison against a live finding. A field only read for
error messages / navigation is diagnostic. When in doubt, the seed carries an
explicit marker (e.g. a `# diagnostic-locator` comment or a typed wrapper) so the
guard's classification is not a heuristic.

## Enumeration duty (FR-014)
The guard's report enumerates the two **deferred** `path::qualname` census
allow-lists (`test_org_activation_seam._BUILTIN_ONLY_ALLOWLIST`,
`test_coord_read_residuals_closeout._IDENTITY_CALLSHAPE_KNOWN_RESIDUALS`) as
known-relocation-anchored-but-out-of-scope, with the follow-up reference.

## Sequencing
Written **red-first**; goes green only once every in-scope WS1 line seed is
migrated. It must NOT be merged before the WS1 migrations (else it reds them and
blows NFR-004). Non-vacuity self-test: plant an int line anchor in a scratch
authoritative seed → guard reds.
