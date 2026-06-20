# Research — Read-Side Surface-Resolver Adoption (#2046)

All decisions verified against the live 01KVGCE8 tree on `feat/read-side-surface-resolver-adoption`
(the anti-laziness squad confirmed no phantom dependencies).

## D-1 — C-007: runtime_bridge → FOLD IN (boundary-safe), not carve-out
- **Decision**: route `runtime/next/runtime_bridge.py:_resolve_runtime_feature_dir` (:2431-2450, its own `_resolve_mission_ulid`→`resolve_mid8` cascade) through the seam.
- **Rationale**: `runtime_bridge.py` ALREADY imports `from specify_cli.missions._read_path_resolver import …` (line 87) and `resolve_mission_read_path` (:2443), plus `specify_cli.core/.mission/.status/.sync`. The Shared-Package-Boundary makes `runtime/next` the canonical *runtime* home but it already consumes `specify_cli` surfaces; importing the new seam (also in `_read_path_resolver`) introduces ZERO new boundary edge. The squared concern (paula F-2: "runtime must not import the seam") does not apply — the edge exists.
- **Alternatives**: carve-out (document runtime as out-of-scope) — REJECTED: it would leave the one module the boundary tests most scrutinize carrying a parallel mid8 cascade, defeating the consolidation. Re-home the seam to a shared low-level package — REJECTED: unnecessary; `_read_path_resolver` is already the blessed shared home and runtime already imports it.

## D-2 — Seam shape: LIFT the orchestrator prototype, do not re-invent
- **Decision**: `resolve_handle_to_read_path(repo_root, handle)` = `assert_safe_path_segment(handle)` → `_read_primary_meta(repo_root, handle)` → `resolve_declared_mid8(meta, handle)` → `if not mid8 and declares_coordination: raise` (fail-closed) → `resolve_mission_read_path(repo_root, handle, mid8)`.
- **Rationale**: `orchestrator_api/commands.py:_resolve_mission_dir` (≈285-347) + `_read_primary_meta` (:251) ALREADY implement this exact, working, topology-gated pattern (the M5 fail-closed reference). `resolve_declared_mid8(meta, mission_slug) -> str` (`surface_resolver.py:453`) is the canonical cascade. Factor `_read_primary_meta` + the gate out of the orchestrator so the orchestrator becomes a seam consumer (eliminating its now-duplicate logic) rather than a 7th cascade.
- **Alternatives**: build the seam from the mid8-blind CLI bootstraps — REJECTED: those are the broken thing (no guard, no mid8 derivation).

## D-3 — The #1718 trap is structurally avoided (verified)
- **Decision/finding**: deriving mid8 is ORTHOGONAL to the create-window→primary contract. `resolve_mission_read_path` chooses coord **only when its worktree directory exists on disk** (`_read_path_resolver.py:240-245`); `test_read_path_resolver_transitional.py:45-55` passes a NON-empty mid8 yet resolves PRIMARY because `.worktrees/...-coord` is absent. So the seam may derive a non-empty mid8 and still fall to primary in the create window.
- **Binding invariant (FR-005)**: the seam routes through `resolve_mission_read_path` (existence-gated), NEVER `resolve_status_surface_with_anchor` (which composes + returns the coord path for a declared-unmaterialized coord, `:744` — routing reads through it WOULD regress #1718). Mutation test enforces this.

## D-4 — The defect is the CASCADE, not the raw join (squad F-4)
- **Decision**: scope + success measure target "bespoke mid8 cascade feeding `resolve_mission_read_path` outside the seam." `tasks.py:4047` (blind `resolve_mid8(slug, mission_id=None)`) and `acceptance.py` (own `meta.mid8`→`mid8_from_slug` cascade) carry the defect with NO raw join — a raw-join-only grep is fakeable. The audit confirms 6+ parallel cascades; only `orchestrator_api` is already correct.
- **Site ledger** (FR-002, code-verified — 8 direct `resolve_mission_read_path` callers in `src/`): raw-join read-CLI residuals = `context.py:72`, `mission.py:1327/1378` (THREE #2046 allowlist entries) + `decision.py:464` (D-6 factory-boundary allowlist entry — consolidated here, not a #2046 residual). Bespoke cascades = `workflow.py:302-324`, `mission_runtime/resolution.py:_mid8_from_primary_meta`, `runtime_bridge.py:2431-2450`, `tasks.py:4047`, `acceptance/__init__.py:590-606` (`_status_read_feature_dir`). Seam source (re-pointed by WP01) = `orchestrator_api:346`. **No "already-routed, leave-alone" set remains** — the earlier ledger mislabeled `tasks.py`/`acceptance.py`, both of which carry a parallel cascade per D-4.

## D-5 — Guard must add a NEW discriminator (squad F-3); cell flips by re-derivation (F-5)
- **Decision**: FR-006 = AST selection-callsite ratchet (new direct `resolve_mission_read_path`/bespoke-`resolve_mid8` call outside the seam → FAIL) + the seam runtime empty-mid8 gate. Proven by two-axis mutation AND a pre/post-tree discrimination check. Reusing the raw-JOIN guard alone is vacuous.
- **Decision**: flip cells / drain allowlist by re-running `discover_rows()` + the matrix on the MIGRATED tree (not literal line edits); `SLUG_NAMES ⊇ {raw_handle, handle}` frozen; re-injection mutation proves the net was not narrowed. After rebase onto landed 01KVGCE8/main, re-verify the 4 allowlist keys + 4 `*/bare` xfail rows still exist before draining/flipping (C-001).
