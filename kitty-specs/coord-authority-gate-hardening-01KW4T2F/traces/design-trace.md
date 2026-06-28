# Design Trace — coord-authority-gate-hardening-01KW4T2F

**Purpose:** the "what the fix looks like and why" record. Seeded at spec→plan; append during implement; assess at close.
> Format: `[date] [phase] DECISION — rationale — evidence/constraint`

---

## Seeded during spec (2026-06-27)

1. **[spec] #2214 = scope-unify + parameter-discipline, not inter-procedural.** The arm (`callshape_violations`, test_gate_read_literal_ban.py:551) is intra-procedural; it misses param- and attribute-passed coord dirs. Design: (a) unify the identity arm's scan scope to merge/+lanes/+core (closes the executor scope-asymmetry); (b) a parameter-discipline rule — kind-sensitive fns self-resolve, don't pass feature_dir into a kind-read (matches how both #2212 residuals were fixed). Evidence: alphonso code-state read; the #2212 fix shape.
2. **[spec] #2198 is verify-annotate, NOT greenfield.** The partition-stability gate already exists: test_write_surface_placement_guard.py::test_full_partition_resolves_per_membership (exhaustive disjoint set-equality + anti-mutant). Design: verify completeness + add per-kind rationale (the explicitness gap). The squad's "one-line re-partition reroutes silently" premise is empirically FALSE on this tree.
3. **[spec] #2197 = route + co-land the scan-scope un-mask.** Route runtime_bridge preview_claimable_wp onto the seam (planning_dir+status_dir split, like the #2212 workflow caller) AND extend the live-arm scan to src/runtime/next/ (gate-unmask-paired-with-fix). The one production routing change (C-003).
4. **[spec] CT7 content-anchoring (C-004).** All gates anchor on _ratchet_keys.composite_key (qualname/symbol), never file:line; reuse the closeout non-vacuous floor+MARGIN+self-mutation pattern (test_coord_read_residuals_closeout.py:102-316). C-001: STATUS legs stay coord (the param-discipline + routing must not move a status leg).

<!-- append during implement: per-site route/gate deltas, the arm-extension shape, floor census, any kind re-classification found. -->
