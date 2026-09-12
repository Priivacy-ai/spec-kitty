# Tracer: Design Decisions

## Specify phase (2026-08-13)

**D1/D2 kept strictly separate.** This mission (`org-activation-scan-dirs`, issue #3385, D2)
does not author any change to `src/charter/_drg_helpers.py` or any other code path that
implements issue #3384 (D1)'s fix — that file is read-only evidence in this spec, cited for the
mechanism chain and for the two contingent verification FRs (FR-004/FR-005), never as a target
of a production edit. This was an operator decision made before this mission started (an
already-in-progress sibling mission, `org-pack-drg-root-graph-guard`, owns D1) and is treated as
binding, not relitigated. The reasoning: the two defects are independently reproducible and
independently fixable — D2's fix (finding org-pack directories in their real layout) does not
require D1's fix (accepting an org graph with no root-level `*.graph.yaml`), and landing both in
one mission would either race the sibling mission's D1 fix or duplicate it.

**Smallest-viable-diff over Boy Scout Rule for the touched file.** `src/charter/kind_vocabulary
.py` also contains `_built_in_scan_dir` and `_layer_scan_dirs`, structurally similar helpers
that are not implicated in this defect. Per `RECONCILE_CHANGE_SCOPE_TENSIONS`
(`.kittify/charter/charter.md`), the file set for this change is fixed at
`src/charter/kind_vocabulary.py` (production) plus its test files — the two neighboring
functions are explicitly left alone. This is stated in the spec as a Clarification and a
Constraint (C-003) rather than left implicit, so a later reviewer doesn't read the untouched
functions as an oversight.

**Additive fix, not a replacement.** The chosen fix scans *both* the flat layout and the legacy
`built-in/`-nested layout, rather than swapping one phantom-single-layout bug for a different
phantom-single-layout "fix." This was chosen because nothing in the codebase rules out some org
pack in the wild still using the legacy shape, and the cost of scanning an extra,
usually-nonexistent directory is a single `is_dir()` check.

**Recursive-flag parity with the live loader, stated explicitly.** The new flat-layout scan
entry is specified as non-recursive (`recursive=False`), matching `BaseDoctrineRepository`'s
non-recursive org-layer `glob` (`src/doctrine/base.py:25`, `:159`). This was called out explicitly
in the spec (Edge Cases) rather than left to implementer judgment, because a recursive scan
would silently accept a *different* layout than the live loader's, reopening a narrower version
of the same source-of-truth divergence this mission is closing.
