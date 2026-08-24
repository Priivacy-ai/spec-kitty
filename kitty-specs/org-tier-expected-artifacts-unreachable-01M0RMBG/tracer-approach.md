# Tracer: Approach — org-tier-expected-artifacts-unreachable-01M0RMBG

Seeded during the plan phase (author subagent), per charter Standing Order #3.

## Why this file set

spec.md's C-001 already fixes the six files (one production module,
`src/charter/org_expected_artifacts.py`, plus five test files). I read all six in full (or
the specific cited line ranges) before writing the plan, specifically to check whether the
set was actually minimal or whether spec.md's Addendum-driven expansion (the three
`tests/dossier/` files) was defensible rather than just asserted. It is: each of
`test_manifest.py`, `test_rebaseline.py`, and `test_indexer.py` independently duplicates a
`_write_org_manifest`-style helper hardcoded to the pre-fix path join, and each exercises
`resolve_org_expected_artifacts` end-to-end (via `ManifestRegistry.load_manifest`,
`rebaseline_snapshot_file`, and `Indexer.index_feature` respectively) with zero mocking of the
resolver itself. I confirmed this by reading each helper directly — they are structurally
identical to `test_org_expected_artifacts.py`'s own `_write_org_expected_artifacts`, just
renamed. Leaving any of the three out would silently regress a currently-GREEN test to RED the
moment FR-001's path join changes, which is a direct, proportional connection to the defect,
not opportunistic scope growth. I did not add a seventh file; C-001's ceiling holds.

## Why this phasing

The phase order (RED-first tests → FR-001/FR-002 implementation → FR-003/004/005 maintenance
→ gate verification) follows directly from NFR-001's own text, which draws a line between
"pinning new behaviour" (FR-001/FR-002 and FR-003's new old-location-returns-None case — these
get RED-first commits) and "tracking already-passing coverage through the anchor move"
(FR-003's helper-fix + five hand-corrected paths, FR-004, FR-005 — maintenance-only, GREEN
throughout). I did not invent this split; I carried it forward from spec.md's NFR-001 row
verbatim rather than re-deriving a different ordering that felt more "natural" to me. The one
judgment call I made was sequencing the maintenance commit(s) strictly *after* the FR-001
implementation commit rather than interleaving them — this keeps the fixture-helper
corrections trivially explainable in review ("these five files track the anchor the previous
commit just moved") rather than landing ahead of the move they're compensating for, which
would read as changing test data with no visible reason yet.

## Alternatives considered and rejected

- **Sibling-fallback (checking both the old and new anchor).** spec.md's Clarifications
  section already rejected this explicitly (C-002, operator-decided) — the old location has
  zero possible existing consumers (unreachable since #3516 introduced it) and no sibling
  org-tier resolver in `resolver.py` checks two locations. I did not re-litigate this in the
  plan; I carried the decision forward and cited C-002 directly rather than re-arguing it from
  first principles. I did independently verify the "no sibling resolver checks two locations"
  claim by reading `_resolve_asset` and `resolve_mission` myself (both check exactly
  one org-tier location each, `org_root / "missions" / <name> / ...`), which confirmed rather
  than merely repeated the spec's framing.
- **A validator gate alongside the resolver fix.** Also already decided out of scope (C-003,
  operator-decided) — I did not propose adding one, and I did not treat the plan's Gate Set
  section as an opportunity to sneak in an authoring-time reachability check under a different
  name; the gate set names CI gates this diff must pass, not new product surface.
- **Growing the file set to include `resolver.py` or `manifest.py` as "documentation" of the
  pattern being matched.** I read both files closely (to confirm the exact sibling pattern
  FR-001 must match) but they are reference material, not touched files — no edit to either is
  needed or proposed. Including them in the six-file set would have been scope creep against
  C-001 for no functional reason.
