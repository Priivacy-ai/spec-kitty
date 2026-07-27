# Implementation Plan: Read-Side Surface-Resolver Adoption

**Branch**: `feat/read-side-surface-resolver-adoption` (stacked on 01KVGCE8; → `main` via the combined PR) | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification `kitty-specs/read-side-surface-resolver-adoption-01KVJPEQ/spec.md` (source: GitHub #2046)

## Summary

Adopt 01KVGCE8's canonical surface resolver across every operator READ path. Extract ONE guarded
`resolve_handle_to_read_path(repo_root, handle)` seam in `missions/_read_path_resolver.py` —
**lifted from the working prototype `orchestrator_api/commands.py:_resolve_mission_dir`** (guarded
segment → `_read_primary_meta` → `resolve_declared_mid8` → fail-closed coord-declared topology gate →
`resolve_mission_read_path`, which is worktree-existence-gated). Route the three #2046 raw-join
read-CLI bootstraps + the D-6 `decision.py:464` raw-join + the five bespoke mid8-cascades
(`workflow`, `resolution`, `runtime_bridge`, `tasks:4047`, `acceptance`) through it; flip 01KVGCE8's
`coord-fresh/bare` + `coord-behind/bare` equivalence cells green by **re-pointing the matrix read_path
observation leg to the seam** (option b — the primitive stays mid8-blind by design), add a
selection-authority guard, and drain the three #2046 residual audit-allowlist entries (+ the D-6
entry as a consolidation consequence) by re-derivation (not by blinding the net).
The disease is **bespoke mid8 cascades feeding `resolve_mission_read_path` outside one seam** — not
merely raw `KITTY_SPECS_DIR/<handle>` joins.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib `pathlib`; 01KVGCE8 surfaces (all verified present, no phantom): `coordination/surface_resolver.resolve_declared_mid8` (`:453`), `resolve_status_surface_with_anchor`, `missions/_read_path_resolver.{resolve_mission_read_path, assert_safe_path_segment-call, _ALLOWLISTED-via-guard}`, `orchestrator_api/commands.{_resolve_mission_dir, _read_primary_meta}` (the reference prototype), `core/paths.assert_safe_path_segment` (`:40`), the `tests/architectural/surface_resolution_audit/` machinery + the load-bearing guard, and the `tests/missions/test_surface_resolution_equivalence.py` matrix (the `*/bare` strict-xfail cells)
**Storage**: filesystem — `kitty-specs/<slug>[-mid8]/` (primary) vs `.worktrees/<slug>-<mid8>-coord/` (the divergent read surfaces); primary `meta.json` is the mid8-derivation anchor
**Testing**: pytest — per-read-CLI end-to-end tests (bare-slug × coord-fresh → coord dir), the equivalence-matrix `*/bare` cells, a create-window mutation, the selection-authority AST ratchet + the seam runtime empty-mid8 gate, traversal-rejection
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single (CLI library: `src/specify_cli` + `src/runtime/next`)
**Performance Goals**: no regression — read resolution is one extra primary-meta read + mid8 derivation (already what the orchestrator prototype does); no benchmark gate
**Constraints**: `ruff` + `mypy --strict` 0 on changed code (no new `# noqa`/`# type: ignore`); migrate-don't-wrap (C-003, no new parallel resolver); the #1718 create-window contract must not regress (C-004); SLUG_NAMES retains `{raw_handle, handle}` (C-002 anti-blind); no version prescription (C-005); rebase onto landed 01KVGCE8/main + re-verify allowlist keys & xfail rows before draining (C-001)
**Scale/Scope**: 1 new seam + ~9 read-path adoption sites (4 raw-join: 3 #2046 + decision.py D-6; 5 bespoke-cascade incl. runtime fold-in, tasks.py:4047, acceptance) + 1 extended guard + 4 allowlist drains + 2 equivalence-cell flips. Bounded; no codebase-wide rename.

## Charter Check

*GATE: passes before Phase 0; re-checked post-design.*

- **Tests for new functionality / ATDD**: satisfied — per-CLI end-to-end tests (SC-002), the `*/bare` cell flips (SC-001), the two-axis guard mutation (SC-004), the create-window mutation (SC-005), the residual re-injection mutation (SC-006).
- **Code Quality (ruff/mypy --strict 0, complexity ≤ 15)**: satisfied — NFR-001; the seam is a small extraction.
- **Canonical seams (#1868)**: directly advanced — one read seam + a selection-authority guard binding read selection to it.
- **Terminology Canon**: Mission; `feature_dir`/`feature_slug` are existing field/var names only.
- **Migrate-don't-wrap / no shadow path (#1993)**: C-003 binding — adoption routes through the seam; no new parallel resolver.
- **Security (path-traversal)**: FR-004 closes the un-guarded `KITTY_SPECS_DIR/raw_handle` composition at the three #2046 read-CLI sites + the D-6 `decision.py:464` join (none pre-validate today) by routing through `assert_safe_path_segment`.
- **Shared Package Boundary**: C-007 resolved FOLD-IN (see research D-1) — `runtime_bridge.py` already imports `specify_cli.missions._read_path_resolver`, so routing its `_resolve_runtime_feature_dir` through the seam is boundary-safe; no carve-out.
- **Not a bulk edit**: this is targeted adoption (different code per site), NOT a same-string rename — `change_mode` stays normal, no `occurrence_map.yaml`.
- No charter violations → no Complexity Tracking entries.

## Project Structure

```
src/specify_cli/
├── missions/_read_path_resolver.py     # NEW seam resolve_handle_to_read_path (IC-01) — blessed home
├── coordination/surface_resolver.py    # resolve_declared_mid8 (consumed, unchanged)
├── orchestrator_api/commands.py        # _resolve_mission_dir / _read_primary_meta (reference prototype; re-point to seam — IC-02)
├── cli/commands/agent/context.py       # :72 raw-join residual → seam (IC-02)
├── cli/commands/agent/mission.py       # :1327/:1378 raw-join residuals → seam (IC-02)
├── cli/commands/decision.py            # :464 D-6 raw-join → seam (consolidation, IC-02)
├── cli/commands/agent/workflow.py      # :302-324 _mid8_for_mission_read_path bespoke cascade → seam (IC-02)
├── cli/commands/agent/tasks.py         # :4047 mid8-blind bespoke cascade → seam (F7 residual, IC-02)
├── acceptance/__init__.py              # :590-606 _status_read_feature_dir bespoke cascade → seam (IC-02)
└── (mission_runtime/resolution.py)     # _mid8_from_primary_meta bespoke cascade → seam (IC-02)

src/runtime/next/runtime_bridge.py      # _resolve_runtime_feature_dir bespoke cascade → seam (IC-02, FOLD-IN per C-007)

tests/
├── architectural/surface_resolution_audit/  # EXTEND: SLUG_NAMES + selection-callsite ratchet (IC-04)
├── architectural/test_single_mission_surface_resolver.py  # drain 4 residual allowlist entries (IC-05)
├── missions/test_surface_resolution_equivalence.py        # flip 2 */bare cells; narrow 2 reasons (IC-03)
└── <per-CLI end-to-end + create-window mutation + traversal tests>  # IC-06
```

**Structure Decision**: single-project CLI. The seam centralizes in `_read_path_resolver.py` (already the blessed `KITTY_SPECS_DIR` path-constructor home). Adoption touches read-path call sites only; the surface resolver and the equivalence-matrix assertion body are NOT modified (FR-003 freezes them).

## Complexity Tracking

No charter violations — none.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs. Sequencing encodes the Tidy-First flow: extract seam → migrate read paths → flip cells by re-derivation → guard → drain by re-derivation.

### IC-01 — Extract the guarded `resolve_handle_to_read_path` seam (FR-001, FR-004, FR-005-invariant)
- **Purpose**: One guarded read-side entry point, lifted from the working `_resolve_mission_dir` prototype: `assert_safe_path_segment(handle)` → `_read_primary_meta(repo_root, handle)` → `resolve_declared_mid8(meta, handle)` → **fail-closed gate** (`if not mid8 and declares_coordination: raise`) → `resolve_mission_read_path(repo_root, handle, mid8)` (worktree-existence-gated). NEVER `resolve_status_surface_with_anchor` (the #1718 trap).
- **Relevant requirements**: FR-001, FR-004, FR-005 (binding invariant)
- **Affected surfaces**: `missions/_read_path_resolver.py` (new seam); factor the shared `_read_primary_meta`/gate out of `orchestrator_api/commands.py` to avoid a 7th cascade.
- **Sequencing/depends-on**: none — FIRST.
- **Risks**: the seam must route through `resolve_mission_read_path` (existence-gated), not the surface — encode as a unit test that a declared-but-unmaterialized coord + non-empty derived mid8 still resolves PRIMARY (the exact #1718 cell). Reuse the orchestrator gate verbatim; do not re-invent.

### IC-02 — Migrate the read paths to the seam (FR-002, C-007)
- **Purpose**: Route every bespoke mid8-cascade read path through the seam — the disease is the cascade, not just the raw join. Three #2046 raw-join residuals (`context.py:72`, `mission.py:1327/1378`) + the D-6 raw-join `decision.py:464` (consolidation) + five bespoke cascades (`workflow.py:302-324`, `mission_runtime/resolution.py:_mid8_from_primary_meta`, `runtime_bridge.py:2431-2450` FOLD-IN, `tasks.py:4047`, `acceptance/__init__.py:_status_read_feature_dir`). `orchestrator_api` is the seam source (re-pointed by WP01). Grounded by the 8-caller enumeration (FR-002).
- **Relevant requirements**: FR-002, C-003, C-007
- **Affected surfaces**: the 7 read-path sites above; `runtime_bridge.py` (boundary-safe — already imports `_read_path_resolver`).
- **Sequencing/depends-on**: IC-01.
- **Risks**: behavior-preserving for non-bare-slug handles (NFR-002); each migrated site's resolved dir must be unchanged for `<slug>-<mid8>`/full-`mission_id`. The bespoke cascades have subtle differences (workflow's `_load_coord_branch_meta`, resolution's `mission_id[:8]` fallback) — the seam's `resolve_declared_mid8` must subsume each; verify per-site.

### IC-03 — Bare-slug coord resolution + cell flips (FR-003, FR-005, FR-008)
- **Purpose**: With the seam deriving mid8 from primary meta, a bare-slug coord read reaches the coord surface **through the seam**. The low primitive `resolve_mission_read_path` stays mid8-blind by design (option b — that empty-mid8 direct call is the bypass FR-006 guards), so the matrix's read_path observation leg must be **re-pointed to the seam**. Flip ONLY `coord-fresh/bare` + `coord-behind/bare` (read_path-only divergence) green; sanctioned diff = (i) re-point the read_path closure in `_entry_points`, (ii) remove those two `xfail` markers, (iii) narrow two reasons — assertion logic / `_observe` / `Outcome` / `_MATRIX` topology builders FROZEN. Narrow `coord-empty/bare` + `coord-deleted/bare` reasons from `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` to a reason naming only the remaining aggregate divergence.
- **Relevant requirements**: FR-003, FR-005, FR-008
- **Affected surfaces**: `tests/missions/test_surface_resolution_equivalence.py` (read_path observation leg re-point + markers/reasons — sanctioned cross-edit to 01KVGCE8's file per the gate protocol).
- **Sequencing/depends-on**: IC-01 + IC-02 (the seam + read_path adoption make the cells agree). Gate on the create-window cell staying green (C-004).
- **Risks**: the flip is by re-pointing the read_path leg to the seam + re-derivation (re-run the matrix), NOT a weakened assertion. C-001 re-verify the four `*/bare` cells/markers exist after rebase. Do NOT drag the aggregate `*/slug-mid8` cells (out of scope, FR-008); reviewer greps that `_assert_equivalent`/`_observe`/`Outcome`/`_MATRIX` are untouched.

### IC-04 — Selection-authority guard, two halves (FR-006)
- **Purpose**: Bind read SELECTION (not just path-shape) to the seam. (a) Extend `surface_resolution_audit` AST machinery with a selection-callsite ratchet: a NEW direct `resolve_mission_read_path` call OR a NEW bespoke `resolve_mid8`/`KITTY_SPECS_DIR/<handle>` mid8-cascade in a read path outside the seam allowlist FAILS. (b) A seam runtime fail-closed gate raises on empty-mid8-against-declared-coord (the IC-01 gate, asserted by mutation).
- **Relevant requirements**: FR-006, #1868, C-002
- **Affected surfaces**: `tests/architectural/surface_resolution_audit/audit.py` (new discriminator), `tests/architectural/test_single_mission_surface_resolver.py` (or a sibling guard).
- **Sequencing/depends-on**: IC-02 (the allowlist reflects the migrated state).
- **Risks**: do NOT satisfy via the existing raw-JOIN guard (vacuous). Two-axis mutation + a pre/post-tree discrimination check (the ratchet PASSES on the adopted tree but WOULD HAVE FAILED on the pre-mission tree) — the anti-vacuous proof.

### IC-05 — Drain the residual allowlist BY FIX (FR-007)
- **Purpose**: The three #2046 read-CLI `_ALLOWLISTED_RAW_JOINS` entries (`context.py:72`, `mission.py:1327/1378`) — plus the D-6 `decision.py:464` entry as a consolidation consequence — drain because `discover_rows()` (SLUG_NAMES unchanged) re-discovers zero raw joins there after IC-02 — NOT by removing tokens from the net.
- **Relevant requirements**: FR-007, SC-006
- **Affected surfaces**: `tests/architectural/test_single_mission_surface_resolver.py` (`_ALLOWLISTED_RAW_JOINS`).
- **Sequencing/depends-on**: IC-02 + IC-04.
- **Risks**: a re-injection mutation (inject a `KITTY_SPECS_DIR/raw_handle` join into a read CLI on the adopted tree → guard FAILS) proves the net was not silently narrowed. `SLUG_NAMES ⊇ {raw_handle, handle}` is a frozen invariant.

### IC-06 — End-to-end CLI proof + create-window + traversal tests (SC-002, SC-005, NFR-003)
- **Purpose**: The matrix tests primitives, never a read CLI — so add per-read-CLI end-to-end tests (bare-slug × coord-fresh → coord dir, NOT primary) for `context`/`mission`/`decision`/`acceptance`; the create-window mutation (declared-unmaterialized coord + derived non-empty mid8 → PRIMARY); the traversal-rejection test (FR-004).
- **Relevant requirements**: SC-002, SC-005, FR-004, NFR-002/003
- **Affected surfaces**: new/extended test modules under `tests/specify_cli/cli/commands/` + `tests/mission_runtime/`.
- **Sequencing/depends-on**: IC-01 + IC-02.
- **Risks**: realistic fixtures (26-char ULID, real `.worktrees/<slug>-<mid8>-coord/` layout). The per-CLI test is the proof the matrix cannot give — do not let the cell flips stand in for CLI adoption.

## Post-Planning Brownfield Checks

*(recorded per standing practice; run at plan time — see research.md D-2..D-4 for detail)*

- **Foldable-issue search** — the read-side residual neighborhood: #2046 (driver), #2007 (epic, read side), #1868 (seam authority), #1993 (shadow-path), #1718 (create-window). No NEW foldable issue found beyond these (the aggregate error-type convergence is the named separate follow-on, NOT folded). No scope bloat.
- **Split-brain / duplication scan** — the squad already found the headline: 6+ parallel mid8 cascades (the disease). All are in FR-002 scope (4 raw-join + workflow + resolution + runtime). The reference prototype (`_resolve_mission_dir`) is the canonical one IC-01 factors out. No additional unmapped duplication.
- **LOC / scope** — bounded: 1 seam + 7 adoption sites + 1 guard extension + test additions; no codebase-wide rename. Refactor-overlap minimal (the seam is new; sites are disjoint files).
- **Deprecation check** — no due deprecation in this surface to remove. The legacy plan-template-asset path (flagged by the fold-in op) is unrelated. The `specify_cli.next` deprecation (3.3.0) is out of this mission's surface.
- Outcome: no scope expansion beyond the 8 FRs; the create-window mutation (C-004) is the safety mechanism for the bare-slug fix; C-007 resolved FOLD-IN.
