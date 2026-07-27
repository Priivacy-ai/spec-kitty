# Behavioral Contracts: Implement-Loop Coord-Authority Completion

No HTTP/API surface. The contracts are the read-seam behavior and the gate invariants the
mission must preserve/establish. Each is stated as a testable assertion.

## C-SEAM-1 — PRIMARY-kind reads resolve primary for all topologies

```
resolve_planning_read_dir(repo_root, slug, kind=WORK_PACKAGE_TASK)  # and LANE_STATE, SPEC, ...
  == the primary-checkout mission dir
  FOR topology IN {flat, lanes, coordination}
```
- For a coord-topology mission with a status-only husk + `tasks/WP*.md` on primary, the
  resolved `tasks/` dir exists and contains the WP files (today: husk → missing).
- **Negative:** the function does NOT consult the coord surface for a PRIMARY kind.

## C-SEAM-2 — STATUS-kind reads stay coordination-aware (C-001)

```
resolve_planning_read_dir(repo_root, slug, kind=STATUS_STATE)  # events/state/matrices
  == the coordination surface when materialized
```
- Every routed mixed-read site keeps its STATUS leg on the coord-aware resolver; a routed
  PRIMARY leg must not move the STATUS read. Existing status/matrix tests stay green
  unchanged (NFR-006).

## C-SEAM-3 — no silent fallback (C-002)

- A coord-deleted / ambiguous handle raises the existing structured error on the STATUS
  leg (#1848); routing the PRIMARY leg introduces no silent empty-dir / stale-primary
  fallback.

## C-GATE-1 — dir-read scanner detects inline-call shape

```
scanner flags:   resolver(...) / "tasks"      # inline (NEW)
scanner flags:   d = resolver(...); d / "tasks"# two-hop (existing)
where resolver ∈ {coord-aware resolvers} and the join base is a PRIMARY-kind dir/file
```
- **Self-test (mandatory, FR-007):** a synthetic snippet matching the inline pre-fix shape
  is asserted FLAGGED; a routed (seam) snippet is asserted NOT flagged.

## C-GATE-2 — whole-`src` scope + no silent skip (FR-008)

- The scan walks all of `src/specify_cli/`. Every surfaced coord-aware PRIMARY read is
  either absent (routed) or present in `_DIR_READ_KNOWN_RESIDUALS` with a tracking-issue
  reference. A surfaced site that is neither routed nor pinned fails the gate.

## C-GATE-3 — floors move shrink-only / raise-only-upward (NFR-001, C-005)

```
ROUTED_CANONICALIZER_FLOOR_post  >  ROUTED_CANONICALIZER_FLOOR_pre (27)
ROUTED_CANONICALIZER_FLOOR_post  <  live_routed_census_post           # strict (anti-vacuous)
permanent_allowlist_post (3)     <  permanent_allowlist_pre (7)        # shrink-only twin-guard
```
- The 4 `_canonicalize_bare_modern_handle` entries auto-route via the taught discriminator
  (FR-011); the 3 raw-param permanent sanctions remain.

## C-2140 — is_committed contract (FR-010, C-004)

```
is_committed(primary_spec_path_with_spec_md, repo_root)  == True
is_committed(coord_husk_spec_path_without_spec_md, repo_root) == False   # NEGATIVE assertion
```
- Single-surface check derived from the path argument; no multi-leg OR. Docstring
  describes the primary-surface read.

## C-VALIDATION — verification gate for the mission

- `pytest tests/architectural/test_gate_read_literal_ban.py tests/architectural/test_resolution_authority_gates.py -q` green.
- The new coord-topology fixture proves each routed site reads PRIMARY (RED against
  pre-fix code, GREEN after) — un-stubbed (FR-014).
- Merged-branch verbatim full-gate dry-run pasted in the PR body (NFR-005).
