# Contract: Structural Read-Side Gate

**Concern**: IC-06 · **Requirements**: FR-005, FR-006, NFR-003, NFR-004

New test module `tests/architectural/test_no_read_side_bypass.py`, mirroring the
structural write gate `test_no_write_side_rederivation.py`.

## Scope
- Reuse `tests/architectural/_placement_whole_tree_scan.py::scan_scope()` — the
  non-sanctioned `src/**/*.py` set. **Do NOT fork the walk** (NFR-003).
- A symmetry meta-test asserts the read gate and write gate consume the same
  `scan_scope()` object.

## Finding
- Walk `ast.Call`; flag any callee resolving to `candidate_feature_dir_for_mission`
  or `resolve_planning_read_dir` (bare `Name` or `Attribute.attr`).
- Callee identity IS the finding (reads have no `ref` arg; no "seam-derived"
  analog needed).

## Exemptions
- **Sanctioned modules**: `_read_path_resolver.py` (the primitive authority),
  and the infra self-consumers per the classification ledger — asserted
  sanctioned (mirror `resolution.py`'s treatment), not silently skipped.
- **Allow-list**: genuinely-deferred / must-stay-lenient residuals as
  content-descriptor entries (`_ratchet_keys.resolve_descriptor`) with a
  required rationale. **Shrink-only**: a staleness twin-guard reds until a routed
  entry is deleted (FR-006, NFR-004). **No file-scoped blanket exemptions** (C-003).

## MUST pass
- **Bite test**: a planted `candidate_feature_dir_for_mission(root, slug)` in a
  fixture reds; a prose/docstring mention stays green.
- **Non-vacuity**: every allow-list entry proven live by the staleness twin-guard.
- **Green with the migration**: after IC-02..IC-05, the gate is green with a
  documented, shrinking allow-list (gate seeded-red / lands last per C-002).

## MUST NOT
- Fork a second tree walk. Introduce a second read authority. Use a blanket
  file-scoped exemption. Ship a vacuous allow-list entry.
