# Quickstart / Validation — Read-Side Surface-Resolver Adoption (#2046)

Validation scenarios (each maps to a Success Criterion). Use production-shaped fixtures
(26-char ULID mission_id, real `.worktrees/<slug>-<mid8>-coord/` layout).

1. **Bare-slug coord read reaches coord (SC-001 + SC-002):**
   - Build a coord-fresh mission; run `spec-kitty agent context` / `agent mission` / `decision` / `acceptance` with the BARE slug.
   - Assert the resolved dir == the coordination-worktree dir (NOT the primary checkout).
   - Re-run `tests/missions/test_surface_resolution_equivalence.py`: `coord-fresh/bare` + `coord-behind/bare` PASS; diff to that file = only 2 removed xfail markers.

2. **Create-window still primary (SC-005, #1718):**
   - Declare a coordination_branch but do NOT materialize the worktree; bare-slug read → PRIMARY.
   - Mutation: route a declared-unmaterialized coord through the surface → `test_read_path_resolver_transitional.py` + the matrix create-window cell FAIL.

3. **Traversal rejected (FR-004):** `handle = "../etc"` → seam raises at `assert_safe_path_segment` before any join.

4. **Selection-authority guard bites (SC-004):**
   - Inject a NEW direct `resolve_mission_read_path(...)` / bespoke `resolve_mid8` call into a read CLI outside the seam → AST ratchet FAILS; revert → PASSES.
   - The ratchet PASSES on the adopted tree but WOULD HAVE FAILED on the pre-mission tree (pre/post discrimination).

5. **Residual drains by fix (SC-006):** the 4 `_ALLOWLISTED_RAW_JOINS` read-CLI entries gone because `discover_rows()` (SLUG_NAMES retaining `{raw_handle, handle}`) re-discovers zero; re-inject a `KITTY_SPECS_DIR/raw_handle` join → guard FAILS.

6. **No regression (NFR-002):** `<slug>-<mid8>` / full-id reads resolve the same dir as before across all read CLIs.
