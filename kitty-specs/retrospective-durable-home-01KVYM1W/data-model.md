# Data Model: Teardown-Surface Hardening + Retrospective Durable Home (Phase 1)

This is a behavior/placement mission — the "entities" are the artifact-kind, the placement authority,
and the teardown contract, not new persisted records.

## Entity — `RETROSPECTIVE` artifact kind

- **Where:** `MissionArtifactKind` enum + `_PRIMARY_ARTIFACT_KINDS` set (`src/mission_runtime/artifacts.py` — shared package).
- **Role:** classifies `retrospective.yaml` as a PRIMARY-partition (durable, tracked) artifact, so the
  placement authority routes it to `kitty-specs/<slug>/`, identically to `spec`/`tasks`.
- **Invariant:** membership in `_PRIMARY_ARTIFACT_KINDS` is the single source of the primary-vs-coord
  decision for the retrospective; no caller may decide placement independently (FR-003).
- **Unit assertion (FR-002):** `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS` MUST hold (an explicit
  set-membership unit test, not merely an integration side-effect).

## Entity — handle-safe PRIMARY entry points (FR-011 / #2136, the foundation)

- **Where:** `src/specify_cli/missions/_read_path_resolver.py` — the CALLERS of the topology-blind primitive
  `primary_feature_dir_for_mission` (`:1212`): the READ leg `resolve_planning_read_dir`'s PRIMARY-partition
  branch (`:1306`, WP01) and the WRITE sites (FR-001/003, WP03). The primitive itself is **NOT** an edit target.
- **Bug (live):** the primitive `:1212` does a raw, handle-BLIND literal compose
  `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug` (`:1240`) and is **deliberately handle-blind**
  (docstring `:1213`). Its PRIMARY callers `resolve_planning_read_dir:1306` and the retrospective write feed it a
  *raw* handle, so a bare `mid8`/`slug` handle composes a *different* dir than the canonical `<slug>-<mid8>`. The
  live exemplars `:1204`/`:1208` and `:820` already pre-canonicalize via `_canonicalize_bare_modern_handle`
  (`:418`); the two PRIMARY entry points above do not.
- **Fix — caller-canonicalization (NOT seam-internal):** canonicalize **in the callers** by reusing
  `_canonicalize_bare_modern_handle` (`:418`) / `_canonicalize_handle` (`:467` — `mission_id`→`mid8`→numeric→
  `slug` disambiguation) BEFORE the blind compose, mirroring the live exemplars `:1204`/`:1208`/`:820`. **Do NOT
  canonicalize inside `primary_feature_dir_for_mission`: it is infinite recursion** (`:418` calls the primitive
  at `:454`); the primitive stays blind by contract. NO parallel resolver (C-006). The `meta.json`-present and
  unresolvable-handle short-circuit legs of the helper MUST stay no-ops (back-compat).
- **No-silent-fallback (WP07 / C-009):** an ambiguous handle propagates `MissionSelectorAmbiguous` — never a
  silent pick. The identity probe runs FIRST so a bare-mid8/numeric handle cannot mask a genuine ambiguity.
- **Inheritance:** curing the handle at the two PRIMARY entry points (read seam + write sites) makes those
  reads/writes handle-safe without mutating the blind primitive — FR-001/002/003 build ON it. WP01 owns the READ
  leg; WP03 owns the WRITE leg (disjoint `owned_files`).
- **Equivalence (NFR-005 / SC-007):** driven THROUGH `resolve_planning_read_dir` (PRIMARY kind), bare-`mid8` ≡
  bare-`slug` ≡ pre-resolved `<slug>-<mid8>` → SAME canonical dir; ambiguous → raises. Asserted by extending
  `tests/missions/test_surface_resolution_equivalence.py`.

## Entity — retrospective home placement authority

- **Where:** `src/specify_cli/missions/_read_path_resolver.py` — the (now handle-safe) function the 6 sites call.
- **Exemplar (CORRECTED):** model the placement authority on **`primary_feature_dir_for_mission`**
  (`src/specify_cli/missions/_read_path_resolver.py:1212`, deliberately **topology-blind**) gated by the
  **`is_primary_artifact_kind`** predicate (`src/mission_runtime/artifacts.py:220`). **REJECTED exemplar:
  `resolve_status_surface`** — it is topology-AWARE (selects the coordination worktree once one exists) and
  would reproduce the coord-routing bug this mission exists to remove. The retrospective home must resolve to
  the primary checkout regardless of topology, exactly as `primary_feature_dir_for_mission` already does.
- **Input:** mission handle/slug (canonical), artifact kind.
- **Output:** the durable home dir `kitty-specs/<slug>/` (PRIMARY), regardless of topology.
- **Resolution sites (the consolidation set — FR-003 enumerating test asserts EXACTLY these route through it).**
  It is **6 sites, not 4** (the false-green keystone — re-censused against HEAD): 5 coord-aware-resolver sites +
  1 hardcoded-legacy payload site. NOTE: two distinct files are named `retrospective_terminus.py`
  (`post_merge/` and `runtime/next/_internal_runtime/`); the previously-cited
  `retrospective/retrospective_terminus.py` **does not exist**.
  | # | Site | Today | After |
  |---|------|-------|-------|
  | 1 | `retrospective/writer.py:48` | `resolve_feature_dir_for_slug` (coord-aware) | authority (primary) |
  | 2 | `post_merge/retrospective_terminus.py:68` | `resolve_feature_dir_for_slug` (coord-aware) | authority (primary) |
  | 3 | `retrospective/lifecycle_events.py:336` | `resolve_feature_dir_for_mission` (coord-aware) | authority (primary) |
  | 4 | `retrospective/lifecycle_events.py:411` | `resolve_feature_dir_for_mission` (coord-aware) | authority (primary) |
  | 5 | `retrospective/lifecycle_events.py:480` | `resolve_feature_dir_for_mission` (coord-aware) | authority (primary) |
  | 6 | `runtime/next/_internal_runtime/retrospective_terminus.py:76` `_record_path_str` (event-payload string) | hardcoded `.kittify/missions/<id>/retrospective.yaml` | authority (primary) — reports the actual home |
- **LEAVE UNTOUCHED:** `retrospective/writer.py:60` `_legacy_record_path` — load-bearing `.kittify` back-compat
  read path (records authored before #1771 still resolve through it); it is NOT a home-resolution site.
- **Enumerating structural test (FR-003):** MUST derive the resolution set by **GREP/AST** (forbid a
  hardcoded count) so that adding a 7th independent resolution site fails the test.

## Entity — `_teardown_coordination_topology` seam (the teardown contract)

- **Where:** extracted from the 3 live `CoordinationWorkspace.teardown(` call sites (base `e36547461`,
  post-#2133):
  `src/specify_cli/merge/executor.py:795` (merge path, inside `_phase_cleanup_worktrees_and_branches`@:717,
  the merge cleanup phase called at `:936` from `_run_lane_based_merge_locked`@:862; swallowing
  `except Exception` at `:805`),
  `src/specify_cli/cli/commands/merge.py:270` (the **`--abort`** helper, inside a swallowing
  `except Exception` at `:271`), and
  `src/specify_cli/cli/commands/mission_type.py:910` (the close/`--discard` path, helper
  `_teardown_coordination_worktree`@:904, inside a swallowing `except Exception` at `:921`).
- **Seam home (NEW):** #2133 relocated the merge-path teardown into `merge/executor.py` but **left the
  `--abort` teardown in `cli/commands/merge.py`** (it did NOT migrate into `merge/`). The three sites now span
  TWO packages (`merge/` + `cli/commands/merge.py`) plus `mission_type.py`, so the shared seam SHOULD live in
  **`src/specify_cli/coordination/`** (near `CoordinationWorkspace`), NOT in `merge/` — `merge/` owns neither
  the abort nor the close/discard call site.
- **Swallow-isolation (FR-005, CORRECTED):** all three sites wrap `CoordinationWorkspace.teardown` in a
  **swallowing `except Exception` (best-effort)**. The shared seam MUST run **persist OUTSIDE that swallow**
  — a persistence failure must not be silently absorbed by the destroy-best-effort handler.
- **Contract (ordered steps, the persist-before-destroy invariant):**
  1. **persist** — the retrospective (and any pending terminal artifact) is written to its durable PRIMARY home
     (NOT inside the destroy best-effort swallow);
  2. **flatten** — the dangling `coordination_branch` is cleared from `meta.json`;
  3. **destroy** — the coordination worktree + lane worktrees are removed.
- **Invariant (FR-005):** step 3 never runs before step 1 completes. Proven by **destroy-step fault injection
  injected at the destroy step** (force step 3 to raise → the retrospective already exists at its home), on
  BOTH the merge path and the `mission_type.py` close/`--discard` path.
- **Anti-rename routing (IC-03 / IC-05):** after extraction, **zero `CoordinationWorkspace.teardown(` call
  sites exist outside the new seam** — a structural test asserts this (a rename that leaves the 3 duplications
  in place is rejected). The destroy-step fault-injection test **UPDATES** #2133's
  `tests/merge/test_executor_coverage.py:616` `test_phase_cleanup_coord_teardown_failure_is_non_fatal` to the
  persist-before-destroy contract (never delete-to-green, DIR-041).
- **Lane-worktree targeting (FR-006 — STRUCK, DONE-by-#2129, regression-reference only):** destroy removes
  EXACTLY the mid8-anchored worktree names from `lanes.json` for THIS mission — never a `<slug>-*` prefix
  match. This is **already shipped on the base by #2129**: `_remove_lane_worktrees` (`mission_type.py:970`)
  removes by exact name via `_expected_lane_worktree_dir_names` (`:950`), and `_verify_discard_complete`
  (`:777`) is exact-name + sibling-safe. No prefix-match survives in code; this binding inherits the invariant
  rather than re-implementing it.

## State / transition notes

- The mission lifecycle close/merge path is the only mutator of the teardown contract; the read-side
  retrospective status access is unchanged (uses `resolve_status_surface` already — C-004).
- No schema/migration: `retrospective.yaml` content is unchanged; only its *home* and the *teardown ordering* change.

## Validation rules

- A retrospective produced on a coordination-topology mission MUST be present at `kitty-specs/<slug>/`
  after close/merge (SC-001).
- The recovery-guidance string MUST reference only existing commands (`doctor workspaces --fix`) (SC-005).
