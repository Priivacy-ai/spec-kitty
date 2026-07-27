# Research: Teardown-Surface Hardening + Retrospective Durable Home (Phase 0)

All decisions resolved by the 3-lens discovery squad (priti/paula/alphonso) + the spec-review squad
(alphonso/renata). Findings: `docs/engineering_notes/3-2-3-surface-resolution-cluster/`. No open
NEEDS CLARIFICATION. Claims re-verified live on the current base `upstream/main e36547461` (post-#2133/#2114/#2134/#2135).

## Decision 1 — Placement authority: extend the existing partition, do not invent

The retrospective home must resolve through the **existing** kind-aware partition, not a new resolver.
- **Decision:** add a `RETROSPECTIVE` member to `_PRIMARY_ARTIFACT_KINDS` (`src/mission_runtime/artifacts.py:85`,
  shared package) and route home resolution through the primary-anchored authority, modeled on the
  topology-blind **`primary_feature_dir_for_mission`** (`src/specify_cli/missions/_read_path_resolver.py:1212`)
  gated by the **`is_primary_artifact_kind`** predicate (`src/mission_runtime/artifacts.py:220`).
- **Exemplar correction:** the authority MUST NOT model on **`resolve_status_surface`** — that resolver is
  **topology-AWARE** (it selects the coordination worktree once one exists), which is exactly the
  coord-routing bug this mission removes. `resolve_status_surface` is the correct exemplar only for the
  *read-side* status access (unchanged, C-004); for the *write* home it is the **rejected** exemplar.
  `primary_feature_dir_for_mission` is already the topology-invariant primary-anchor that
  `mission_runtime.resolve_placement_only` uses.
- **Rationale:** unification-not-parity; one owning authority. The read-twin (#1716/#2106) and the
  kind-aware placement ADR (#2101/#2090) set the precedent. Single set-membership = minimal surface (NFR-001).
- **Alternatives rejected:** a new bespoke resolver (parallel authority — the exact split-brain we're
  removing); modeling on the topology-aware `resolve_status_surface` (reproduces the coord-routing bug); a
  gitignored `.kittify/missions/<id>/` home (loses #1771's tracked/reviewable intent, C-001).

## Decision 2 — It is ONE home-resolution operation duplicated across 6 sites (re-censused — not 4)

- **Decision:** consolidate all **SIX** sites onto the authority. Re-censused against HEAD, the real set is
  5 coord-aware-resolver sites + 1 hardcoded-legacy payload site:
  - `retrospective/writer.py:48` (`resolve_feature_dir_for_slug`)
  - `post_merge/retrospective_terminus.py:68` (`resolve_feature_dir_for_slug`)
  - `retrospective/lifecycle_events.py:336`, `:411`, `:480` (all `resolve_feature_dir_for_mission`)
  - `runtime/next/_internal_runtime/retrospective_terminus.py:76` `_record_path_str` (event-payload string;
    today hardcodes `.kittify/missions/<id>/retrospective.yaml` — must report the actual home).
- **Census correction:** the earlier "4 sites" was the false-green keystone. Two files share the name
  `retrospective_terminus.py` (`post_merge/` and `runtime/next/_internal_runtime/`); the previously-cited
  `retrospective/retrospective_terminus.py` **does not exist**. `lifecycle_events.py` has **three** emitter
  sites (`:336`, `:411`, `:480`), not one. The hardcoded payload lives in the `runtime/next/` terminus
  (`:76`), not the `post_merge/` one.
- **LEAVE:** `writer.py:60` `_legacy_record_path` — load-bearing `.kittify` back-compat read path (NOT a
  home-resolution site).
- **Rationale:** after the file re-homes, the *event payload* would still report the legacy path, re-splitting
  the brain; and the two extra lifecycle emitters and the second terminus file are independent resolutions.
  FR-003's "no site independently resolves" requires all six. The **enumerating structural test MUST derive
  the set by GREP/AST (a hardcoded count is forbidden)** so adding a 7th independent resolution fails it.
- **Alternatives rejected:** fixing only a subset of sites (leaves a residual split — a latent #2119 regression).

## Decision 3 — One shared teardown seam + persist-before-destroy

- **Decision:** extract one `_teardown_coordination_topology` seam from the 3 live (post-#2133)
  `CoordinationWorkspace.teardown(` call sites — `merge/executor.py:795` (merge cleanup phase
  `_phase_cleanup_worktrees_and_branches`@:717), `cli/commands/merge.py:270` (the **`--abort`** helper),
  `mission_type.py:910` (the close/`--discard` path, helper `_teardown_coordination_worktree`@:904); the seam
  runs **persist (retro) → flatten (`coordination_branch`) → destroy**. Fixes the merge-path
  destroy-before-persist and the `close --discard` no-persist gap. **Seam home:** #2133 relocated the
  merge-path teardown into `merge/executor.py` but **left the `--abort` teardown in `cli/commands/merge.py`**,
  so the three sites span two packages + `mission_type` → the seam lives in **`coordination/`**, not `merge/`.
- **Swallow-isolation (corrected):** each call site is today wrapped in a **swallowing `except Exception`**
  (`executor.py:805`, `merge.py:271`, `mission_type.py:921` — all "best-effort"). The shared seam MUST run
  **persist OUTSIDE that swallow** so a persistence failure is never silently absorbed. The destroy-step fault
  injection MUST be injected **at the destroy step** (not at persist) on BOTH the merge path and the
  `mission_type.py` close/`--discard` path.
- **Anti-rename routing:** a structural test asserts **zero `CoordinationWorkspace.teardown(` call sites exist
  outside the new seam** (a rename leaving the 3 duplications is rejected).
- **Rationale:** the duplication is why the ordering bug exists in one path and not the other; one seam makes
  the invariant attachable once and provable by destroy-step fault injection (FR-005).
- **Alternatives rejected:** patching each path's ordering separately (leaves the duplication; the invariant
  re-drifts on the next edit).

## Decision 4 — Lane-worktree exact-set (mid8-anchored): DONE-by-merge (#2129), regression-reference only

- **Decision (now STRUCK from code scope):** exact mid8-anchored lane-worktree names from `lanes.json` (never
  a `<slug>-*` prefix-match) are **already shipped on the base by #2129** — `_remove_lane_worktrees`
  (`mission_type.py:970`) removes by exact name via `_expected_lane_worktree_dir_names` (`:950`), and
  `_verify_discard_complete` (`:777`) is exact-name + sibling-safe. No prefix-match survives in code.
- **Scope correction:** the original FR-006 (#2123) is **DONE-by-merge**. #2123 stays OPEN on the tracker
  (#2129 closed twin #2127), but no #2119 code change is in scope. A regression test MAY lock the
  sibling-survival invariant but is not a deliverable.
- **Rationale:** the prefix-match deleted a sibling mission's worktree incl. uncommitted work (silent data
  loss, #2123) and spuriously aborted discard on a sibling — both closed on the base by #2129's exact-set.
- **Alternatives rejected:** re-implementing the exact-set inside #2119 (redundant — already on the base).

## Decision 5 — All sequencing-gate PRs have MERGED: one slice, no open-PR gate

- **Decision:** #2121 (#2120), #2129 (#2127), **and #2133 (#2057), #2114, #2134, #2135 have ALL merged** to the
  base (`upstream/main e36547461`). There is **no open-PR gate** — the whole mission plans as ONE slice. #2133's
  decomposition relocated the merge-path teardown into `merge/executor.py:795` (cleanup phase) but **left the
  `--abort` teardown in `cli/commands/merge.py:270`**; the FR-004 seam unifies the three live sites and lives
  in `coordination/`. FR-005 **updates** #2133's no-persist test (`tests/merge/test_executor_coverage.py:616`).
- **Rationale:** with the gating decomposition landed, the placement spine, teardown seam, persist-before-destroy,
  recovery text, and tidy all plan against one settled base — sequenced internally only by `dependencies`
  (foundation WP → consolidation + teardown WPs).
- **Out of scope:** a separate #2115/Ray-port planning-read-surface effort is owned by other maintainers — it
  is neither a dependency nor a foundation for #2119.
- **Alternatives rejected:** retaining the Slice-A/Slice-B split (the gate it was predicated on is gone).

## Decision 6 — The ADR records the contract

- **Decision:** one ADR — "Terminal-Artifact Durable Home + Topology-Aware Teardown Contract" — with two
  bindings: (a) terminal artifacts resolve to the durable, **handle-safe** PRIMARY home via the
  `MissionArtifactKind` partition (Binding A now refined with the #2136 entry-point handle-safety); (b) topology
  teardown is persist-before-destroy.
- **Rationale:** it is the write-surface twin of the coord-empty-fallback read ADR; future terminal
  artifacts inherit the contract. Precedents: #2101/#2090 (placement), #1716 (read twin).

## Decision 7 — Fold #2136 (handle-safe entry points) as the FOUNDATION (FR-011) via CALLER-canonicalization (primitive stays blind)

- **Decision:** canonicalize a bare `mid8`/`slug` handle **in the CALLERS** of the topology-blind
  `primary_feature_dir_for_mission` (`_read_path_resolver.py:1212`) — specifically the READ leg
  `resolve_planning_read_dir`'s PRIMARY-partition branch (`:1306`, WP01) and the WRITE sites (FR-001/003, WP03)
  — reusing the EXISTING `_canonicalize_bare_modern_handle` (`:418`) / `_canonicalize_handle` (`:467`) identity
  machinery, and passing the canonical handle DOWN to the blind compose. **The primitive `:1212` STAYS
  handle-blind by contract (docstring `:1213`); it is NOT modified.** #2136 names this "the same root behind
  #2119": since #2119's retrospective write composes through this primitive (FR-001), curing the handle at the
  write callers makes the write handle-safe. FR-011 is the foundation WP; FR-001/002/003 build on it.
- **Why NOT seam-internal (the rejected mechanism — live-verified):** canonicalizing *inside*
  `primary_feature_dir_for_mission` is **architecturally impossible — infinite recursion**:
  `_canonicalize_bare_modern_handle` (`:418`) itself calls `primary_feature_dir_for_mission` at `:454`
  (verified on HEAD), so the primitive calling the helper that calls the primitive recurses forever. The
  primitive is deliberately blind (docstring `:1213`), and the canonical pattern is the caller wrapping the
  helper and passing the resolved handle in — exactly what the live exemplars `:1204`/`:1208` and `:820`
  already do. FR-011 mirrors that exemplar at the two PRIMARY entry points.
- **Live verification (current base `e36547461`/HEAD):** `:1212` does the raw literal compose at `:1240` —
  handle-blind by contract. The live exemplars `:1204`/`:1208` and `:820` already canonicalize in the caller
  via `_canonicalize_bare_modern_handle` and pass the canonical handle to the blind compose. The READ leg
  `resolve_planning_read_dir:1306` and the retrospective WRITE composition still feed the primitive a *raw*
  handle — those are the two sites FR-011 fixes. The canonicalization helper, its identity probe, and its
  no-silent-fallback (`MissionSelectorAmbiguous`) already exist and are tested by
  `tests/missions/test_surface_resolution_equivalence.py` (extend it through the read seam).
- **Rationale:** caller-canonicalization at the two PRIMARY entry points cures the handle where it enters path
  resolution, preserving the blind primitive's single topology-invariant compose (which recursion forbids
  mutating anyway). No parallel resolver (unification-not-parity, C-006); no silent fallback (WP07/C-009). The
  ownership splits cleanly: WP01 owns the READ leg (`_read_path_resolver.py`), WP03 owns the WRITE leg (the 6
  placement sites) — disjoint `owned_files`.
- **Alternatives rejected:** seam-internal canonicalization inside `primary_feature_dir_for_mission` (infinite
  recursion, `:418`→`:454`); a new bespoke identity resolver (parallel authority — the split-brain we remove);
  leaving #2136 as a separate follow-on (it is #2119's own root, and #2119's write would otherwise compose a
  handle-blind path).

## Decision 8 — The #2138/#2139/#2140 read-surface residual cluster is OUT of scope (follow-on)

- **Decision:** #2138 (decision-event payload persists slug as `mission_id`), #2139 (dual `target_branch`
  reader with a silent `main` fallback), #2140 (`is_committed` spec-read coord-unaware post-#2090) are a
  cohesive SIBLING cluster of read-surface residuals — NOT folded as #2119 FRs.
- **Rationale:** they share the surface-resolution theme but sit on the read side, outside #2119's
  placement+teardown+seam bounded context; folding would widen the review. Recommended as their own small
  follow-on mission, or parked under the #1868/#1716 strangler epic.
- **Alternatives rejected:** folding them into #2119 (scope creep past the bounded context).

## Brownfield pre-tasks checks (standing cadence)

- **Foldable issues:** #2119/#1890 folded; **#2136 folded as the FOUNDATION (FR-011 — same root behind #2119)**;
  #2123 done-by-#2129 (regression-reference); #2125 (atomic-YAML dup) deliberately RELATE-d out (orthogonal).
  The #2138/#2139/#2140 read-surface residual cluster is a deliberate OUT-of-scope follow-on (Decision 8).
- **Split-brain/LOC scan:** the **6-site** home duplication (re-censused: 5 coord-aware resolvers +
  1 hardcoded payload) + 3-site teardown duplication ARE the finding (Decisions 2-3) — addressed by
  consolidation, not deferred. The `retrospective.yaml` literal is a separate hoist (re-censused: **8 string
  literals + 2 `.tmp` f-strings across 6 `.py` files**; the earlier "13-file / 47-occurrence" conflated
  docstrings and prose) crossing the shared-package boundary (FR-010, its own WP). The `_run_lane_based_merge_locked`
  god-function is OUT (C901 passes; separate debt).
- **Deprecations:** none due in the touched surfaces; the legacy `.kittify` back-compat probe is
  intentionally preserved (load-bearing).
