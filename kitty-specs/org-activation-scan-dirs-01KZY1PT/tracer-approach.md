# Tracer: Approach

## Specify phase (2026-08-13)

This mission is the **D2** half of a two-defect P0 pair (`up-org-pack-load-integrity`):
`_org_scan_dirs` (`src/charter/activation/kind_vocabulary.py:200-209`) scans only
`<org_root>/<plural>/built-in/`, a layout no real org pack uses, so any `charter activate` call
silently evicts every org-pack artifact of that kind from the filtered DRG. The sibling defect,
**D1** (issue #3384 — org-graph load requires a root-level `*.graph.yaml`), is owned by a
separate, already-in-progress mission (`org-pack-drg-root-graph-guard`) and is explicitly out of
scope here except as verification criteria contingent on that mission's fix landing.

The approach is a **surgical production fix plus a red-first regression test**, not a rewrite:
`_org_scan_dirs` gains a second scan entry for the flat `<root>/<plural>` layout (the one the
live loader, `DoctrineService._org_dirs` / `BaseDoctrineRepository`, actually reads) alongside
the existing `<root>/<plural>/built-in` entry, which is kept for backward compatibility with any
pack still using the legacy shape. The spec pins the recursive-flag choice for the new entry
(`recursive=False`, matching the live loader's non-recursive org-layer glob) so the
implementation doesn't have to re-derive it from scratch.

The regression test is specified at the level that matters to an operator — `filter_graph_by
_activation`'s output after a real `charter activate` call — not only at the `_org_scan_dirs`
unit level, per the mission's authored scope. The pre-existing unit test file
(`tests/charter/test_kind_vocabulary_scan_roots.py`, `TestOrgScanDirsHelper`) is extended rather
than replaced, since it already exists and currently pins the old (buggy) behavior.

D1's verification-only obligation (named-diagnostic check, `<org_root>/drg` alternative-location
check) is written as two explicitly contingent, low-priority FRs (FR-004/FR-005) that this
mission's own completion does not depend on — they exist so a later pass has a fixed target
instead of re-deriving the question once #3384 lands.
