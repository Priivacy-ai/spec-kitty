# Mission Specification: Teardown-Surface Hardening + Retrospective Durable Home

**Mission ID:** 01KVYM1WS4M2FG00WGJV04N879
**Slug:** retrospective-durable-home-01KVYM1W
**Target branch:** fix/3.2.3-coord-surface-regressions (3.2.3 surface-resolution cluster)
**Mission type:** software-dev
**Tracker:** #2119 (driver, residual of #1771) · **#2136** (caller-side handle-canonicalization at the PRIMARY-read/write entry points — the blind primitive stays blind) folded as the FOUNDATION (FR-011) · **#1890** (phantom recovery command) folded · parent #1878 · cluster #1716/#1868 · RELATE #2125 (atomic-YAML dup, not folded) · **#2123** (lane-worktree data-loss) — code DONE-by-merge (#2129); regression-reference only, see issue-matrix

---

## Summary

A cluster of defects and debt all live on **one surface** — the coordination/lane **teardown
path** and the **terminal-artifact placement** it destroys. This mission hardens that surface as
ONE slice inside ONE spec / ONE ADR / ONE teardown bounded-context:

0. **Handle-safe PRIMARY entry points (the FOUNDATION, #2136):** the topology-blind primitive
   `primary_feature_dir_for_mission` (`_read_path_resolver.py:1212`, handle-blind by contract) is fed a *raw*
   handle by its PRIMARY callers — the READ leg `resolve_planning_read_dir:1306` and #2119's retrospective
   WRITE — so a bare `mid8`/`slug` handle silently diverges from the canonical `<slug>-<mid8>` dir. #2136
   names this "the same root behind #2119." Canonicalize **in the callers** (reusing the existing identity
   resolver, no-silent-fallback), passing the canonical handle DOWN to the blind compose — the primitive
   STAYS blind (folding canonicalization in is infinite recursion, `:418`→`:454`). FR-001/003 build ON this.
1. **Retrospective durable home (the spine, #2119):** `retrospective.yaml` is written into the
   ephemeral coordination worktree (**5 coord-aware resolver sites + 1 hardcoded-legacy payload site
   = 6 home-resolution sites**) and lost on teardown. It must live in the durable **primary** mission
   folder (`kitty-specs/<slug>/`) — the terminal-artifact write-surface twin of the planning-read SSOT.
   The placement authority models on the (now handle-safe) topology-blind `primary_feature_dir_for_mission`
   gated by `is_primary_artifact_kind`, NOT the topology-aware `resolve_status_surface`. #2119 is the
   residual of CLOSED #1771 (which moved the home but kept the coord-aware resolver).
2. **Persist-before-destroy teardown contract:** teardown today can destroy the coordination
   worktree before the retrospective is persisted (merge path) and has no persist step at all
   (`close --discard`). One shared teardown seam must persist, then flatten, then destroy.
3. **Real recovery guidance (#1890):** the teardown/husk warnings point at a non-existent
   `spec-kitty agent worktree repair` command across 8 sites (post-#2135); repoint to the real
   `doctor workspaces --fix` (which exists).
4. **Campsite tidy:** remove two dead worktree-print helpers (one carrying a latent forbidden-term
   landmine), fix two stale prose comments, hoist the `retrospective.yaml` filename literal.

A single ADR records the terminal-artifact-home + topology-aware-teardown contract.

> **Lane-worktree exact-set (#2123) — DONE-by-merge, struck from live scope.** The earlier FR-006
> (target lane worktrees by exact mid8 names, not a `<slug>-*` prefix-match) is **already shipped on the
> base** by PR **#2129** (`c22ac6655`): `_remove_lane_worktrees` removes by exact name via
> `_expected_lane_worktree_dir_names`, and the residual verifier `_verify_discard_complete` is exact-name
> + sibling-safe. No prefix-match survives in code. See the issue-matrix note below; its sibling-survival
> outcome (former SC-004) is retained as a **regression-reference**, not a deliverable. **Tracker nuance:**
> #2129 closed the twin issue **#2127**; **#2123 stays OPEN** (operator close-as-dup-of-#2127 later) —
> this mission does not re-implement it.

---

## User Scenarios & Testing

### Foundation — handle-safe PRIMARY entry points (#2136)

1. An operator addresses a mission by a bare `mid8` (or bare human `slug`) rather than the canonical
   `<slug>-<mid8>` dir name.
2. A PRIMARY read or write (e.g. the retrospective write, or a planning-artifact read via
   `resolve_planning_read_dir`) canonicalizes the handle in the caller, then composes through the
   topology-blind `primary_feature_dir_for_mission`.
3. **Outcome:** the resolved dir is the SAME canonical PRIMARY dir as if the operator had typed the full
   `<slug>-<mid8>` — no handle-blind divergence. *(Today: the bare handle composes a literal, wrong dir.)* An
   ambiguous handle raises `MissionSelectorAmbiguous` (no silent pick).

### Primary — retrospective survives mission close (coordination topology)

1. An engineer runs a coordination-topology mission to completion (coord worktree materialized).
2. The mission produces a retrospective.
3. The engineer closes or merges; the coordination worktree is torn down.
4. **Outcome:** the retrospective is present in `kitty-specs/<slug>/retrospective.yaml`, committed on
   the primary surface — it survives teardown. *(Today: written into `.worktrees/<slug>-coord/` and deleted.)*

### Recovery guidance (#1890)

1. A command hits the coord-empty / husk fallback and prints recovery guidance.
2. **Outcome:** the guidance names a command that exists (`spec-kitty doctor workspaces --fix`),
   never `spec-kitty agent worktree repair`.

### No-regression — flattened / single-branch mission

1. An engineer completes a flattened (non-coordination) mission.
2. **Outcome:** the retrospective home and the teardown behavior are byte-identical to before.

### Lane-worktree safety (#2123) — regression-reference (NOT a deliverable)

Sibling-survival on a prefix-named discard is **already satisfied on the base by #2129**
(`_expected_lane_worktree_dir_names` exact-set + sibling-safe `_verify_discard_complete`). This mission
does not re-implement it; a regression test MAY lock the invariant but no code change is in scope.

### Edge cases

- Merge path: teardown MUST NOT precede retrospective persistence.
- `close --discard`: any produced retrospective is persisted before worktree/branch teardown.
- Read-side retrospective access (status surface) is already correct and MUST stay unchanged.

---

## Slice model

The mission delivers as **ONE slice** inside the single spec. The prior Slice-A/Slice-B split was gated on
PR #2133 (`cli/commands/merge.py` god-module decomposition) being OPEN; **#2133 — along with #2114, #2134,
and #2135 — has now MERGED to `upstream/main` (`e36547461`)**. The merge-side teardown sites #2133 relocated
are now live (`merge/executor.py` cleanup phase + the `cli/commands/merge.py` `--abort` helper), so all FRs —
placement spine, teardown seam, persist-before-destroy, recovery text, and tidy — plan together against one
settled base with no open-PR gate. (A separate #2115/Ray-port planning-read-surface effort is owned by other
maintainers and is **out of #2119 scope** — it is neither a dependency nor a foundation for this mission.)

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `retrospective.yaml` MUST be placed on the durable **primary** mission surface (`kitty-specs/<slug>/`) for every topology, never the ephemeral coordination worktree. The placement authority MUST be modeled on **`primary_feature_dir_for_mission`** (`src/specify_cli/missions/_read_path_resolver.py:1212`, topology-blind) gated by **`is_primary_artifact_kind`** (`src/mission_runtime/artifacts.py:220`) — **NOT** on `resolve_status_surface` (topology-aware; would reproduce the coord-routing bug). The live-coord bug is the coord-aware call at `src/specify_cli/retrospective/writer.py:48` (`resolve_feature_dir_for_slug`). LEAVE `writer.py:52` `_legacy_record_path` (load-bearing `.kittify` back-compat read path). The live-coord behavioral test MUST assert **`".worktrees" not in resolved.parts`** (asserting merely `kitty-specs in parts` is insufficient — it passed flat in #1771; that was the false-green). | Draft |
| FR-002 | A `RETROSPECTIVE` artifact kind MUST be added to the primary-artifact partition so retrospective placement is resolved by the single primary-anchored placement authority (the partition already governing spec/tasks). Anchors: enum `MissionArtifactKind` (`src/mission_runtime/artifacts.py:24`), partition `_PRIMARY_ARTIFACT_KINDS` (`:85`), gate `is_primary_artifact_kind` (`:220`); routing exemplar `primary_feature_dir_for_mission` (`src/specify_cli/missions/_read_path_resolver.py:1212`). An explicit **unit assertion `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`** MUST be added. | Draft |
| FR-003 | ALL retrospective home-resolution sites — **6 sites** (re-censused against HEAD) — MUST resolve the home through ONE primary-anchored placement authority; no site may independently resolve it. The set is: 5 coord-aware-resolver sites — `src/specify_cli/retrospective/writer.py:48` (`resolve_feature_dir_for_slug`), `src/specify_cli/post_merge/retrospective_terminus.py:68` (`resolve_feature_dir_for_slug`), `src/specify_cli/retrospective/lifecycle_events.py:336`, `:411`, `:480` (all `resolve_feature_dir_for_mission`) — plus 1 hardcoded-legacy payload site: `src/runtime/next/_internal_runtime/retrospective_terminus.py:76` `_record_path_str` (today hardcodes `.kittify/missions/<id>/retrospective.yaml` for the event-payload string; must report the actual home). NOTE: two distinct files are named `retrospective_terminus.py` (`post_merge/` and `runtime/next/_internal_runtime/`); the old `retrospective/retrospective_terminus.py` **does not exist**. The behavioral test MUST assert **`".worktrees" not in resolved.parts`**. A **structural test MUST enumerate every home-resolution site by GREP/AST (a hardcoded count is forbidden)** so that adding a 7th independent resolution site fails; rename-vacuous "consolidation" is rejected. LEAVE `writer.py:52` `_legacy_record_path` (load-bearing `.kittify` back-compat read path). | Draft |
| FR-004 | The duplicated coordination-teardown logic MUST be consolidated into ONE shared teardown seam. **On the current base (`e36547461`, post-#2133), the 3 `CoordinationWorkspace.teardown(` call sites are `src/specify_cli/merge/executor.py:795` (inside `_phase_cleanup_worktrees_and_branches` @ `:717`, the merge cleanup phase called from `_run_lane_based_merge_locked` @ `:862`→`:936`), `src/specify_cli/cli/commands/merge.py:270` (the `--abort` helper), and `src/specify_cli/cli/commands/mission_type.py:910` (inside helper `_teardown_coordination_worktree` @ `:904`, reached from close @ `:644` and `--discard` @ `:676`).** STRUCTURAL FINDING: #2133's decomposition moved the merge-path teardown into `merge/executor.py` but **left the `--abort` teardown in `cli/commands/merge.py` (it did NOT migrate into `merge/`)**, so the three sites now span **two packages plus `mission_type`**. The shared seam SHOULD therefore live in **`src/specify_cli/coordination/`** (near `CoordinationWorkspace`), **not** in `merge/` — `merge/` does not own the abort or close/discard call sites. A structural test MUST assert **zero `CoordinationWorkspace.teardown(` call sites exist outside the new seam** (IC-03 anti-rename — a rename that leaves the duplications is rejected). | Draft |
| FR-005 | The shared teardown seam MUST **persist the retrospective to its durable home before destroying** the coordination worktree (persist-before-destroy), then flatten the dangling `coordination_branch`, then destroy. **Merge-path bug (live):** teardown is the second-to-last phase `_phase_cleanup_worktrees_and_branches` (`executor.py:717`, called at `executor.py:936`), while `run_retrospective_postcondition(...)` fires at `merge.py:382` in the OUTER `merge()` only **after** `_run_lane_based_merge` returns → destroy-before-persist. **Discard-path bug (live):** `_discard_mission` (`mission_type.py:662`) calls `_teardown_coordination_worktree` (`:676`) with **NO persist step**. The persist hook for discard goes **ahead of `:676`** (the flatten step `_flatten_discarded_mission` is already present at `:639`, so the seam inherits it). All teardown sites today wrap `CoordinationWorkspace.teardown` in a **swallowing `except Exception`** (`executor.py:805`, `merge.py:271`, `mission_type.py:921`); the shared seam MUST run **persist OUTSIDE that swallow** (a persistence failure must never be absorbed by the destroy best-effort handler). Proven by **destroy-step fault injection**: a test forces the destroy step to fail and asserts the retrospective already exists at its durable home — on BOTH the merge path AND the `mission_type.py` close/`--discard` path. **#2133 shipped `test_phase_cleanup_coord_teardown_failure_is_non_fatal` (`tests/merge/test_executor_coverage.py:616`) asserting teardown-failure is swallowed (i.e. it hard-codes the absence of persist-before-destroy); FR-005 MUST UPDATE that test to the persist-before-destroy contract (persist runs outside the swallow), NEVER delete-to-green (DIR-041).** | Draft |
| ~~FR-006~~ | ~~Lane-worktree teardown MUST target exact mid8-anchored names (#2123).~~ **STRUCK — DONE-by-merge (#2129).** `_remove_lane_worktrees` (`mission_type.py:970`) removes by exact name via `_expected_lane_worktree_dir_names` (`:950`); residual verifier `_verify_discard_complete` (`:777`) is exact-name + sibling-safe. No prefix-match survives. Recorded in the issue-matrix as `done-by-sibling-merge (#2129)`; its sibling-survival outcome (former SC-004) is retained as a regression-reference only. **Tracker #2123 stays OPEN** (#2129 closed twin #2127). | **STRUCK** |
| FR-007 | The non-existent `spec-kitty agent worktree repair` text MUST be removed from **every site** and replaced with the real `spec-kitty doctor workspaces --fix` guidance, enforced by a **repo-wide grep-guard test** that fails if the phantom string survives anywhere (#1890). On the current base (`e36547461`, post-#2135) the phantom string lives at **8 sites**: `cli/commands/_coordination_doctor.py` ×4 (`:220, :293, :338, :345`), `coordination/surface_resolver.py` ×3 (`:109, :119, :782`), + the SOURCE doctrine `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` ×1 (`:509`). **`cli/commands/doctor.py` now has ZERO** — #2135 relocated the former 5 `doctor.py` phantom strings into `_coordination_doctor.py` where they collapsed to 4 (a duplicate was removed in the move). The SKILL.md site is the SOURCE doctrine under `src/doctrine/`, NOT a generated `.agents/` copy. The grep-guard MUST be **count-agnostic** (it greps the whole tree and fails closed on any surviving phantom string regardless of how many sites exist), so the 8-vs-9 census never needs re-pinning. | Draft |
| FR-008 | The two dead worktree helpers (`_list_active_worktrees` @ `src/specify_cli/cli/commands/mission_type.py:78`, `_print_active_worktrees` @ `:313`) MUST be removed; the WP MUST first prove **zero live callers** (delete-and-trust-green is rejected), eliminating the latent prohibited-legacy-term landmine carried in the dead string. | Draft |
| FR-009 | Two stale prose comments in `src/specify_cli/cli/commands/mission_type.py` MUST be corrected: (a) the cross-reference at `:642` ("Same path as merge.py:1568" — `merge.py:1568` no longer exists post-#2133 decomposition: `cli/commands/merge.py` is now 575 lines; the real teardown is the `merge/executor.py` `_phase_cleanup_worktrees_and_branches` cleanup phase + the `cli/commands/merge.py:270` `--abort` helper) MUST point at the real teardown region; (b) the prefix-match comment at `:607` (the `.worktrees/ f"{raw}-" prefix match` prose, introduced as a landmine by #2129's de-prefixing — it describes removal code that no longer exists) MUST be corrected so no maintainer believes a prefix-match still lives. | Draft |
| FR-010 | The `retrospective.yaml` filename literal MUST be hoisted to ONE named constant. **Scope (re-censused — the prior "47 occurrences / 13 files" conflated docstrings and prose): there are 8 hoistable string literals across 6 `.py` files** — `src/runtime/next/_internal_runtime/retrospective_terminus.py:76`, `src/specify_cli/cli/commands/retrospect.py:1025`, `src/specify_cli/post_merge/retrospective_terminus.py:71`, `src/specify_cli/retrospective/lifecycle_events.py:344`, `src/specify_cli/retrospective/summary.py:336` & `:666`, `src/specify_cli/retrospective/writer.py:49` & `:60` — **plus 2 `.tmp` f-string prefixes** at `writer.py:148` & `:424` (literal `retrospective.yaml.tmp.…`). The remaining mentions are docstrings/prose and are NOT in scope. The hoist crosses the **shared-package boundary** (`src/runtime/next` + `src/mission_runtime`-adjacent): consume via the public `spec_kitty`/`mission_runtime` import surface; do not anchor a new cross-boundary import. This is its **OWN WP**. | Draft |
| FR-011 | **(Foundation — #2136)** Every PRIMARY read/write entry point MUST resolve a bare `mid8`/`slug` handle to the canonical `<slug>-<mid8>` directory **before** it composes the path, so a bare handle never silently diverges from a pre-resolved `<slug>-<mid8>` handle. **Live bug:** the topology-blind primitive `primary_feature_dir_for_mission` (`src/specify_cli/missions/_read_path_resolver.py:1212`) does a raw literal compose `get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug` (`:1240`) and is **deliberately handle-blind** (docstring `:1213`). The kind-aware read seam `resolve_planning_read_dir` (`:1244`) feeds it a **raw** handle on its PRIMARY-partition leg (`:1306`), and #2119's retrospective WRITE (FR-001) likewise composes via the raw primitive — so a bare `mid8`/`slug` handle resolves to a *different* dir than the canonical `<slug>-<mid8>` (the handle-blind bug class #2136 names "the same root behind #2119"). **Mechanism — caller-canonicalization (NOT seam-internal): the primitive STAYS handle-blind.** Canonicalizing *inside* `primary_feature_dir_for_mission` is rejected as architecturally impossible: `_canonicalize_bare_modern_handle` (`:418`) itself calls `primary_feature_dir_for_mission` (`:454`) — folding canonicalization into the primitive is **infinite recursion**. Instead, the cure mirrors the EXISTING live exemplars `:1204`/`:1208` and `:820`, which canonicalize in the **caller** via `_canonicalize_bare_modern_handle` (`:418` → `_canonicalize_handle` `:467`, `mission_id`→`mid8`→numeric→`slug`) and pass the *canonical* handle DOWN to the blind compose. FR-011 routes (a) the kind-aware read seam's PRIMARY leg (`resolve_planning_read_dir:1306`) and (b) the retrospective WRITE placement (FR-001/FR-003 sites, owned by WP03) through `_canonicalize_bare_modern_handle` BEFORE the blind compose. The canonicalization MUST reuse the existing identity machinery (NO parallel/bespoke resolver — C-006), preserve **no-silent-fallback** (an ambiguous handle propagates `MissionSelectorAmbiguous`, never a silent pick — the WP07 regression / C-009), and NOT regress the `meta.json`-present and unresolvable-handle short-circuit legs of `_canonicalize_bare_modern_handle`. **Acceptance:** a test drives the PRIMARY-read seam (`resolve_planning_read_dir` for a PRIMARY-partition kind) three ways — a bare-`mid8` handle, a bare-`slug` handle, and a pre-resolved `<slug>-<mid8>` handle — and asserts all three resolve to the SAME canonical dir (no handle-blind divergence); an ambiguous handle raises `MissionSelectorAmbiguous` (extends the equivalence matrix in `tests/missions/test_surface_resolution_equivalence.py`). The blind primitive itself remains unchanged (handle-blind by contract). Folding the cure at the read seam + the write placement makes #2119's write handle-safe at every PRIMARY entry point; FR-001/003 build ON this. **Closes #2136.** | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The `RETROSPECTIVE` kind addition is minimal-surface. | A single set-membership addition to the primary-artifact partition; no new resolver primitive. | Draft |
| NFR-002 | Behavioral correctness is verified against a **live, genuinely-divergent** coordination-topology mission, bound per-FR. | EACH of **FR-001/003** + **FR-005** carries an acceptance test driving a real coord-topology mission where the **coordination surface diverges from primary** (the coord worktree lacks `meta.json`/`lanes.json`). FR-001/003 assert **`".worktrees" not in resolved.parts`**; FR-005 uses **destroy-step fault injection**. The former FR-006 prefix-sibling fixture is **removed** (done-by-#2129). A stubbed resolver, bare-slug, or flattened fixture is rejected as a false-green (the #1771 trap). | Draft |
| NFR-003 | The change is behavior-preserving for non-coordination (flattened/single-branch) missions. | Retrospective home + teardown behavior byte-identical before/after for a flattened mission. | Draft |
| NFR-004 | No touched function exceeds the complexity ceiling. | All touched functions stay within `maxCC ≤ 15` (ruff C901). The pre-existing `_run_lane_based_merge_locked` god-function is OUT of scope (separate debt). The teardown-seam work builds on the already-merged `merge/executor.py` (#2133's decomposition left it at maxCC≤15) — the seam extraction starts from a compliant base. | Draft |
| NFR-005 | The FR-011 caller-canonicalization is **identity-preserving and no-silent-fallback** (#2136 / WP07 / C-009), and the topology-blind primitive `primary_feature_dir_for_mission` STAYS handle-blind (the canonicalization lives in the callers, never inside the primitive — recursion-safety, `:418→:454`). | A handle-equivalence test (extending `tests/missions/test_surface_resolution_equivalence.py`) drives the PRIMARY-read seam (`resolve_planning_read_dir` for a PRIMARY-partition kind) and proves bare-`mid8`, bare-`slug`, and pre-resolved `<slug>-<mid8>` resolve to ONE canonical dir; an ambiguous handle raises `MissionSelectorAmbiguous` (never a silent pick); the `meta.json`-present and unresolvable-handle back-compat legs of `_canonicalize_bare_modern_handle` are unchanged; the blind primitive's signature/behavior is unchanged. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | The retrospective home stays in the PRIMARY-partition **tracked** folder (`kitty-specs/<slug>/`), preserving #1771's tracked/reviewable intent — NOT a gitignored `.kittify/` home. | Draft |
| C-002 | Terminal-artifact placement scope is `retrospective.yaml` ONLY (no other terminal file artifact exists). | Draft |
| C-003 | **All sequencing-gate PRs have MERGED to the base (`upstream/main e36547461`): #2121 (#2120), #2129 (#2127), #2133 (#2057), #2114, #2134, #2135.** The close-path teardown helper (`mission_type.py:_teardown_coordination_worktree`, the seam-anchor) and the lane exact-set (`_remove_lane_worktrees`/`_verify_discard_complete`) are on the base; FR-006 is **done-by-merge** and leaves scope. **#2133 has merged** — its `cli/commands/merge.py` god-module decomposition RELOCATED the merge-path teardown into `merge/executor.py:795` (`_phase_cleanup_worktrees_and_branches` cleanup phase) **but left the `--abort` teardown in `cli/commands/merge.py:270`** (it did NOT migrate into `merge/`), and it shipped `test_phase_cleanup_coord_teardown_failure_is_non_fatal` (`tests/merge/test_executor_coverage.py:616`), which asserts teardown-failure is swallowed — i.e. it hard-codes the absence of persist-before-destroy. Therefore **there is no open-PR gate**: all FRs plan together. The FR-004 seam unifies the now-live three sites (`merge/executor.py:795`, `cli/commands/merge.py:270`, `mission_type.py:910`) — which span TWO packages + `mission_type`, so the seam SHOULD live in `coordination/`, not `merge/` — and FR-005 **updates** the #2133 test to the persist-before-destroy contract (NEVER delete-to-green, DIR-041). **#2135 has merged** — it relocated FR-007's former 5 `doctor.py` phantom strings into `_coordination_doctor.py` (collapsing to 4); `doctor.py` now has zero. FR-007's grep-guard is count-agnostic and fails closed regardless. **(#2114 and #2134 are merged and a NON-ISSUE for #2119: no overlap, no ordering relationship.)** **A separate #2115/Ray-port planning-read-surface effort is owned by other maintainers and is OUT of #2119 scope — neither a dependency nor a foundation.** | Draft |
| C-004 | The read-side retrospective access already uses the correct status surface and MUST remain unchanged; only the record/write home seams are in scope. | Draft |
| C-005 | The orthogonal atomic-YAML write duplication (`writer.py:148`/`:424`) is deliberately NOT folded (RELATE #2125) — it has zero topology payoff and would widen the placement review. | Draft |
| C-006 | FR-011 canonicalizes in the **callers** of the topology-blind primitive (`resolve_planning_read_dir`'s PRIMARY leg `:1306` and the retrospective WRITE placement sites) by reusing the EXISTING `_canonicalize_bare_modern_handle` / `_canonicalize_handle` machinery — it MUST NOT introduce a parallel/bespoke identity resolver (unification-not-parity), MUST NOT reintroduce a silent fallback (the WP07 / C-009 regression), and MUST NOT fold canonicalization into `primary_feature_dir_for_mission` itself (that primitive calls into `_canonicalize_bare_modern_handle`'s callee path → infinite recursion; the primitive stays handle-blind by contract — docstring `:1213`). The cure mirrors the live exemplars `:1204`/`:1208`/`:820`, which canonicalize in the caller and pass the canonical handle DOWN to the blind compose. | Draft |

## Success Criteria

| ID | Outcome (measurable, technology-agnostic) |
|----|-------------------------------------------|
| SC-001 | A retrospective created during a coordination-topology mission is present in the tracked mission folder after the mission is closed or merged (today: lost 100% of the time on coord topology). |
| SC-002 | (a) Every retrospective placement flow (incl. the event-payload path string) resolves through the single primary-anchored authority — an enumerating structural test confirms zero sites resolve independently. (b) Coordination teardown runs through one shared seam (zero `CoordinationWorkspace.teardown(` call sites outside it). |
| SC-003 | Teardown never destroys the coordination worktree before the retrospective is persisted, on both merge and discard paths — proven by destroy-step fault injection. |
| SC-005 | No user-facing recovery guidance references a non-existent command — a **count-agnostic** repo-wide grep-guard confirms the phantom string is gone from every site (incl. the SOURCE `SKILL.md`); the dead worktree helpers and their forbidden-term string are removed. |
| SC-006 | (a) The `retrospective.yaml` filename exists as exactly one named constant across the hoistable literal sites. (b) The two stale prose comments (`mission_type.py:642`, `:607`) are corrected. |
| SC-007 | (Foundation, #2136) A bare-`mid8` handle, a bare-`slug` handle, and a pre-resolved `<slug>-<mid8>` handle all resolve through `primary_feature_dir_for_mission` to the SAME canonical PRIMARY dir (no handle-blind divergence), and an ambiguous handle raises `MissionSelectorAmbiguous` (no silent fallback) — proven by the extended handle-equivalence matrix. |

> **Regression-reference (former SC-004):** Discarding a mission whose slug is a prefix of a sibling's
> leaves the sibling's lane worktrees and uncommitted work untouched, and does not spuriously abort. This
> is **satisfied on the base by #2129** (`_expected_lane_worktree_dir_names` exact-set + sibling-safe
> `_verify_discard_complete`); this mission does not re-implement it. A regression test MAY lock the
> invariant but is not a deliverable.

## Key Entities

- **Retrospective** (`retrospective.yaml`) — the terminal mission artifact produced at mission end.
- **Primary-artifact partition / `MissionArtifactKind`** — the single placement authority.
- **Coordination/lane teardown** — the close/merge lifecycle step that destroys coordination + lane worktrees/branches.

## Domain Language

- **Terminal artifact** — an artifact produced at the end of a mission's lifecycle (the retrospective).
- **Durable home** — the tracked primary mission folder `kitty-specs/<slug>/`.
- **Persist-before-destroy** — the teardown ordering invariant.
- **Exact-set teardown** — targeting lane worktrees by mid8-anchored exact names, not slug-prefix-match (already shipped by #2129).

## Assumptions

- The read-side retrospective status access already uses `resolve_status_surface`; only the
  record/write home seams are vulnerable (live-verify each before editing).
- #2121 (#2120 close-teardown helper), #2129 (#2127 lane exact-set), **and #2133/#2114/#2134/#2135 have ALL
  landed on the base** (`upstream/main e36547461`); there is **no open-PR gate** — the whole mission plans as
  one slice against a settled base.
- A companion ADR ("Terminal-Artifact Durable Home + Topology-Aware Teardown Contract") records the
  placement + persist-before-destroy decision (precedents: kind-aware placement #2101/#2090, read twin #1716).

## Out of Scope

- The shared atomic-YAML writer extraction (RELATE #2125).
- The lane-worktree exact-set re-implementation (#2123) — DONE-by-merge (#2129); regression-reference only.
- Splitting the pre-existing `_run_lane_based_merge_locked` god-function (separate debt; C901 currently passes).
- Any terminal artifact other than `retrospective.yaml` (none exists — C-002).
- Read-side retrospective resolution (already correct — C-004).
- **Follow-on read-surface residual cluster (NOT #2119 FRs):** #2138 (decision-event payload persists slug as
  `mission_id`), #2139 (dual `target_branch` reader with a silent `main` fallback), #2140 (`is_committed`
  spec-read coord-unaware post-#2090) are a cohesive SIBLING cluster of surface-resolution read-surface
  residuals — explicitly OUT of #2119 scope. Recommended as their own small follow-on mission, or parked under
  the #1868/#1716 strangler epic. Folding them here would widen the review past the
  placement+teardown+handle-safety bounded context.

> **#2136 reconciliation note:** the prior Out-of-Scope line deferred "the `resolve_planning_read_dir`
> entry-point handle-canonicalization (#2122)". FR-011 (#2136) now FOLDS the caller-side cure at the PRIMARY
> entry points — `resolve_planning_read_dir`'s PRIMARY-partition leg (`:1306`) canonicalizes its handle BEFORE
> calling the blind `primary_feature_dir_for_mission` (`:1212`), and the WRITE sites do the same — so those
> legs are handle-safe. The primitive itself stays blind (seam-internal canonicalization is infinite recursion,
> `:418`→`:454`). Any STATUS-partition / entry-point-specific residual that #2122 may separately track is NOT
> folded; #2122 remains a follow-on only for whatever sits outside these two PRIMARY entry points.

## Issue Matrix

| Tracker | Disposition |
|---------|-------------|
| #2119 | Driver — retrospective durable home + teardown contract (this mission). |
| #2136 | **Folded as the FOUNDATION (FR-011)** — caller-side handle-canonicalization at the two PRIMARY entry points (`resolve_planning_read_dir`'s PRIMARY leg `:1306` + the retrospective WRITE sites), each canonicalizing BEFORE the blind `primary_feature_dir_for_mission` (`:1212`) compose; the primitive stays blind ("the same root behind #2119"). #2119 owns the deliverable; **Closes #2136.** |
| #1890 | Folded — phantom recovery command (FR-007). #2119 owns the deliverable. |
| #2123 | **done-by-sibling-merge (#2129)** — lane exact-set shipped on base; **stays OPEN** (#2129 closed twin #2127). Sibling-survival is a regression-reference here, not a deliverable. |
| #2133 | **MERGED** (#2057, `cli/commands/merge.py` god-module decomposition) — substrate on the base; relocated the merge-path teardown into `merge/executor.py` and shipped the no-persist test FR-005 must UPDATE. No #2119 deliverable. |
| #2135 | **MERGED** (#2059, `doctor.py` decomposition) — substrate; relocated the FR-007 phantom strings into `_coordination_doctor.py`. No #2119 deliverable. |
| #2114 | **MERGED** — substrate; no overlap with #2119. No deliverable. |
| #2134 | **MERGED** (`agent/mission.py` decomposition) — substrate; different file, no overlap. No deliverable. |
| #2115 | **OUT OF #2119 SCOPE** — the planning-read surface (Ray-port) is a **separate effort owned by other maintainers**; not a dependency, foundation, or deliverable of this mission. |
| #2138 / #2139 / #2140 | **OUT OF #2119 SCOPE — follow-on cluster.** Decision-event payload slug-as-`mission_id` (#2138), dual `target_branch` reader w/ silent `main` fallback (#2139), `is_committed` spec-read coord-unaware post-#2090 (#2140) — a cohesive sibling cluster of read-surface residuals. Recommended as their own small follow-on mission or parked under #1868/#1716. NOT #2119 FRs. |
| #2122 | **Partially superseded by FR-011/#2136.** The PRIMARY entry-point handle-canonicalization that #2122 deferred is now folded (caller-side, at `resolve_planning_read_dir:1306` + the WRITE sites — the blind primitive `primary_feature_dir_for_mission` is unchanged); #2122 remains a follow-on only for any residual outside those two entry points. |

## Suggested Lane Decomposition (for /spec-kitty.plan)

Target **~7 WPs in ONE slice** against the settled base (`upstream/main e36547461`; no open-PR gate). The
**handle-safe seam (FR-011) is the FOUNDATION** — the kind/authority and consolidation WPs build ON it via
`dependencies`; the tidy and recovery WPs are line-disjoint and parallelizable.

- **WP1 — FOUNDATION: handle-safe PRIMARY read seam** (FR-011 / #2136): the topology-blind primitive
  `primary_feature_dir_for_mission` (`_read_path_resolver.py:1212`) STAYS handle-blind (folding canonicalization
  in is infinite recursion — `_canonicalize_bare_modern_handle:418` calls the primitive at `:454`). Instead,
  canonicalize a bare `mid8`/`slug` handle to `<slug>-<mid8>` in the **caller**: the kind-aware read seam
  `resolve_planning_read_dir`'s PRIMARY leg (`:1306`) is routed through `_canonicalize_bare_modern_handle`
  (`:418` → `_canonicalize_handle` `:467`) BEFORE the blind compose, mirroring the live exemplars `:1204`/`:1208`.
  Preserve no-silent-fallback (`MissionSelectorAmbiguous`, WP07/C-009) and the back-compat legs. Extend the
  handle-equivalence matrix (`tests/missions/test_surface_resolution_equivalence.py`) THROUGH the read seam:
  bare-`mid8` ≡ bare-`slug` ≡ `<slug>-<mid8>`; ambiguous → raises. WP1 owns ONLY the read-side canonicalization
  in `_read_path_resolver.py`; **the WRITE-path canonicalization at the FR-001/003 placement sites is owned by
  WP3** (no `owned_files` overlap). **WP2/WP3 reads through the PRIMARY read seam inherit handle-safety.**
- **WP2 — `RETROSPECTIVE` kind + primary-anchored placement authority** (FR-002): add `RETROSPECTIVE` to
  `MissionArtifactKind` (`artifacts.py:24`) + `_PRIMARY_ARTIFACT_KINDS` (`:85`); model the placement authority
  on the now-handle-safe `primary_feature_dir_for_mission` (`:1212`) gated by `is_primary_artifact_kind`
  (`:220`), NOT `resolve_status_surface`. Unit assert `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`. Depends on WP1.
- **WP3 — Consolidate all 6 home-resolution sites onto the authority + handle-safe WRITE** (FR-001/003/011-write):
  `writer.py:48`, `post_merge/retrospective_terminus.py:68`, `lifecycle_events.py:336/:411/:480`,
  `runtime/next/.../retrospective_terminus.py:76`. Each WRITE site canonicalizes its handle via
  `_canonicalize_bare_modern_handle` BEFORE composing through the topology-blind `primary_feature_dir_for_mission`
  (the FR-011 caller-canonicalization on the WRITE leg — WP1 owns the READ leg, WP3 owns the WRITE leg; no file
  overlap). Live-coord behavioral test asserting `".worktrees" not in resolved.parts` + GREP/AST enumerating
  structural test (7th-site fails). LEAVE `writer.py:52`. Depends on WP1+WP2.
- **WP4 — Shared teardown seam** (FR-004): extract ONE seam from the 3 live `CoordinationWorkspace.teardown(`
  sites (`merge/executor.py:795`, `cli/commands/merge.py:270`, `mission_type.py:910`) — span two packages +
  `mission_type`, so seam lives in `coordination/`, NOT `merge/`. Anti-rename structural test (zero teardown
  call sites outside the seam). Depends on WP1.
- **WP5 — Persist-before-destroy in the seam** (FR-005): persist → flatten → destroy; persist OUTSIDE the
  best-effort swallow (`executor.py:805`, `merge.py:271`, `mission_type.py:921`); persist hook ahead of the
  discard teardown (`mission_type.py:676`). Destroy-step fault injection on merge + close/`--discard`.
  **UPDATE** `tests/merge/test_executor_coverage.py:616`
  `test_phase_cleanup_coord_teardown_failure_is_non_fatal` (DIR-041, never delete-to-green). Depends on WP4.
- **WP6 — Recovery-command repoint** (FR-007 / #1890): the 8 phantom `agent worktree repair` sites
  (`_coordination_doctor.py` ×4, `surface_resolver.py` ×3, SOURCE `SKILL.md` ×1) → `doctor workspaces --fix`
  + a count-agnostic repo-wide grep-guard. Line-disjoint; parallelizable.
- **WP7 — Tidy + filename-hoist** (FR-008/009/010): remove the 2 dead helpers (`mission_type.py:78`, `:313`,
  prove zero callers); correct the two stale comments (`:642`, `:607`); hoist the `retrospective.yaml` literal
  to ONE constant (8 literals + 2 `.tmp` f-strings across 6 `.py` files, crossing the shared-package boundary).
  *Planner may split the filename hoist into its own WP if the boundary crossing warrants isolation.*
- **ADR** (`architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md`) lands with WP1/WP2/WP3.
