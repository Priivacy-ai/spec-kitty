# Mission Specification: Gate-command Read-surface Completion

**Mission ID**: 01KVW9B0XFXPKTBE77QT3KRSW8
**Slug**: gate-read-surface-completion-01KVW9B0
**Branch**: feat/gate-read-surface-completion
**Epic**: #1716 (coordination topology coherence) · **Driver**: #2107 · **Bundles**: #2085, #2102, #2088, #2091 · **Companion**: #2100
**Predecessor**: #2106 write-surface-coherence (write side), #2099/#147 (read side, tasks phase)

> This is the **#1716 residual-cluster closeout mission**. Its primary spine is the
> gate-command read-surface completion (#2107/#2085/#2102); it additionally locks two
> adjacent coordination-coherence residuals that are already fixed at the seam but
> lack a dedicated regression guard (#2091 `next` mid8, #2088 ownership-overlap
> dependency-exemption — both re-verified live + reopened to be closed *within* this
> mission with a scenario-driving red-first guard, not a re-litigation of the fix).

## Summary

The write-side mission #2106 made artifact **placement** kind-aware (`MissionArtifactKind`)
and re-partitioned planning + identity kinds onto the primary `target_branch`,
adding the per-kind read seam `resolve_planning_read_dir(repo_root, slug, *, kind)`.
It re-pointed the **tasks-phase** reads but did **not** re-point the
planning-lifecycle **GATE/verify command reads** (`setup-plan`, `accept`,
`record-analysis`). Those still resolve through the topology-aware
`resolve_handle_to_read_path` / `_find_feature_directory`, which routes to the
**coordination** worktree for a coord-topology mission — where the planning
artifact (spec.md/plan.md) no longer lives after #2106 moved the write to primary.

**Result (live-reproduced on `main` @ ea7dc75c5):** on a coord-topology / protected-primary
mission, `setup_plan` reads `coord/spec.md`, which does not exist (spec.md is now on
primary), and emits `SPEC_FILE_MISSING` / blocks. The same class affects the accept
gate. This mission completes the read side: re-point the gate-command reads onto the
per-kind `resolve_planning_read_dir` seam so author-on-primary and verify-from-primary
agree. Unification, not parity — the coord worktree is an internal materialization for
status, not a planning-read surface.

## User Scenarios & Testing

**Primary actor:** an agent (or operator) running the planning lifecycle on a
coord-topology mission (protected-primary repo with a coordination branch).

**Scenario 1 — setup-plan after spec-commit (the driver, #2107).**
Given a coord-topology mission whose `spec.md` was committed to the primary
`target_branch` by `spec-commit` (post-#2106 behavior), when the agent runs
`spec-kitty agent mission setup-plan --mission <slug>`, then setup-plan reads
`spec.md` from the **primary** surface (via `resolve_planning_read_dir(kind=SPEC)`),
finds it substantive, and advances the plan phase — it does **not** read the
coordination worktree and block with `SPEC_FILE_MISSING`.

**Scenario 2 — accept gate (#2107 accept facet / #2085).**
Given a coord-topology mission with planning artifacts on primary and the
acceptance-matrix where the status model places it, when the agent runs the
accept gate, then it reads each artifact from its kind's canonical surface
(planning → primary; status/acceptance → its placed surface) and does not
misresolve the folder.

**Scenario 3 — record-analysis dirty-tree preflight (#2102).**
Given a mission whose working tree contains spec-kitty's own bookkeeping files
(`meta.json`, `.kittify/encoding-provenance/global.jsonl`), when the agent runs
record-analysis, then the dirty-tree preflight correctly classifies those as
coordination/bookkeeping residue (allowlisted) and does not falsely block on
spec-kitty's own metadata.

**Scenario 4 — flattened mission regression.**
Given a flattened/single-branch mission (no coordination branch), when any of the
above gate commands run, then behavior is identical to today (planning and status
both on `target_branch`) — no regression.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `setup_plan` MUST read `spec.md` (and any planning artifact it consults) via the per-kind `resolve_planning_read_dir(repo_root, slug, kind=SPEC)` seam, not the topology-aware `resolve_handle_to_read_path`/`_find_feature_directory`. (#2107 setup-plan facet, driver) | Planned |
| FR-002 | The accept gate is a **multi-site cluster** (~9 planning reads): it reads `spec/plan/tasks/research/data-model` off the coord-aware `status_feature_dir` (`acceptance/__init__.py:1179-1187`, `_missing_artifacts:596`). Each **planning-kind** read MUST move to the per-kind seam (→ primary); the **STATUS/acceptance reads** (status.events.jsonl, acceptance-matrix) MUST stay on `status_feature_dir` untouched. The risk is splitting the single `status_feature_dir` variable per-partition without breaking the status/events read. (#2107 accept facet / #2085) | Planned |
| FR-003 | (#2102) The record-analysis dirty-tree preflight is a **self-bookkeeping allowlist** concern, NOT a planning-seam read (`ANALYSIS_REPORT` is a COORD-partition kind — `artifacts.py:109`). spec-kitty's own bookkeeping files (`meta.json`, `.kittify/encoding-provenance/global.jsonl`) currently classify `kind=None` → not allowlisted → the preflight falsely blocks. Add them to a self-bookkeeping allowlist (`_COORD_RESIDUE_FILENAMES` / a dedicated allowlist at `artifacts.py:113`), kept **separate** from the coord-residue partition (so "stale primary spec.md = real dirt" still holds). Also collapse the record-analysis manual coord-then-primary **double-resolution** (`mission.py:1980`) onto the canonical seam. | Planned |
| FR-004 | All planning-lifecycle GATE/verify commands that read OR commit planning artifacts MUST consult the single kind-aware surface seam — **no command may reconstruct a planning path via topology routing, a direct `<dir>/<artifact>.md` join, or a resolution to the repo primary.** Enumerated residual sites (the anti-"fixed N of M" list; ~13-15 reads + the finalize-tasks commit, across 3 modules): `setup_plan` read (`mission.py:2224`), the accept cluster (FR-002, ~9 reads), `map-requirements` WP `tasks/*.md` (`tasks.py:3727`), and **`finalize-tasks` COMMIT** (live dogfood repro — resolves the protected repo primary `main` instead of the mission `target_branch`; see `research/dogfood-finalize-tasks-repro.md`). Already-primary (NOT residual, leave): `check-prerequisites`, `finalize-tasks` *read*, record-analysis write. | Planned |
| FR-005 | (Companion, #2100) Route the residual inline `json.loads(meta…read_text())` reads in the touched modules through the canonical `load_meta` adapter. Scope: the modules this mission edits + the high-traffic surface-resolver/status reads; the full ~62-site backlog beyond touched modules stays deferred. | Planned |
| FR-006 | (#2091) The `next` command MUST build a well-formed coordination branch — `mid8` derived from `mission_id` via `resolve_mid8`, never empty (the fix exists at `runtime/next/runtime_bridge.py:205-231`). This mission adds a dedicated **red-first regression guard driving the exact reported failure** (empty-mid8 → malformed coord branch → `git worktree add` 128) through the `next` entry point, then closes the issue within the mission matrix. | Planned |
| FR-007 | (#2088) The ownership-overlap validator MUST exempt dependency-ordered WP pairs that legitimately share `owned_files` (the fix exists at `ownership/validation.py:161` via `_dependency_reachability`, caller threads `_wp_dependencies` at `mission.py:3521`). This mission adds a dedicated **red-first regression guard** driving the reported scenario (same-lane sequential WPs sharing an owned glob) through `finalize-tasks --validate-only`, then closes the issue within the mission matrix. | Planned |
| FR-008 | (#2074-instance) Fix the stale `tests/specify_cli/test_mid8_direct_routing.py::test_mission_type_read_mid8_truncates_then_declines` — its fixture writes `full.json`/`explicit.json`/`bare.json`, but `_read_mission_mid8` (`mission_type.py:632`) reads `<dir>/meta.json` via `load_meta` and ignores the filename → returns `""` (the test is RED only because the fixture drifted; `resolve_mid8` product code is correct). Re-pin the fixture to write a production-shaped `meta.json` (via the canonical mission factory, per the #2074 CT3 direction), so the test actually exercises the `resolve_mid8` routing parity it claims to guard. This is the mid8-read sibling of FR-006/FR-007's "lock the fix" theme. | Planned |
| FR-009 | (Consolidation — squad-found, the real fix) **Retire the bespoke planning-surface workarounds onto the single canonical seam** so no parallel implementation survives: (a) `setup_plan`'s inline coord read (`mission.py:2224`); (b) record-analysis's coord-then-primary double-resolution (`mission.py:1980`, with FR-003); (c)+(d) the bespoke primary-anchor helper pair (`mission.py:1308,1327`); **(e) `finalize-tasks`'s commit-surface resolution** (it routes the planning-artifact commit to the protected repo primary `main` instead of the mission `target_branch` — the write-side twin, must resolve via the same kind-aware seam). Fold onto `resolve_planning_read_dir` / the kind-aware write seam (the `_ARTIFACT_TYPE_TO_KIND` map at `mission.py:1106` is the ready-made kind lookup). One canonical seam, N callers; brownfield consolidation, not a per-site patch. | Planned |
| FR-010 | (Ratchet — makes FR-004 and FR-009(e) enforceable) Add an **architectural literal-ban ratchet test** with TWO arms: (read arm) no gate-command entry function may directly join `<feature_dir>/{spec,plan,tasks,research,data-model}.md` or reconstruct a planning-read path via topology routing — all planning-artifact reads go through the kind-aware seam; (**write arm**) no write-branch resolver (`get_feature_target_branch`, `resolve_target_branch`, the `finalize-tasks` commit-branch resolution) may anchor its `meta.json` lookup to `candidate_feature_dir_for_mission` (→ coord → fallback protected repo primary `main`) instead of `primary_feature_dir_for_mission` / the kind-aware write seam (the write twin, FR-009(e); WP00). Non-vacuity is proven by a MANDATORY runnable synthetic-AST self-test (both arms), with the enumerated surface/resolver set pinned. Without this, FR-004/FR-009(e) are documentation, not a gate, and a future command silently re-reads coord or re-commits to `main`. | Planned |

## Non-Functional Requirements

| ID | Requirement | Threshold/Measure |
|----|-------------|-------------------|
| NFR-001 | Behavior-neutral for flattened/single-branch missions. | A flattened-mission regression test shows identical gate behavior pre/post (planning+status both on `target_branch`). |
| NFR-002 | Red-first reproduction via the PRE-EXISTING entry points. | Each FR has a test that drives the real command/resolver (e.g. `setup_plan`, not the new seam directly) and is RED on pre-fix code, GREEN after. The triage repros (`repro_2107_setupplan.py`) are the seed. **Hazard:** the setup-plan/accept red-first tests MUST use a composed `<slug>-<mid8>` primary dir — a bare-slug fixture masks the coord/primary divergence behind handle canonicalization (false-green). For FR-006/FR-007, revert the product guard to prove the new guard goes RED. |
| NFR-003 | No new CLI surface. | The `kind` argument to the read seam is internal; no new command/flag introduced. |
| NFR-004 | The behavioral guard is non-vacuous and anti-mutant. | A test proves setup-plan reads PRIMARY for a coord-topology mission (kills the "reads coord" mutant); regressing the read to `resolve_handle_to_read_path` turns it RED. |

## Constraints

| ID | Constraint |
|----|------------|
| C-001 | Build on #2106's `resolve_planning_read_dir` + `MissionArtifactKind` partition and #2099's read surfaces. Do NOT introduce a parallel read resolver. |
| C-002 | Unification not parity — remove the topology-routed planning-read for gate commands; the coord worktree is an internal status materialization, not a planning-read surface. No fallback to the old route. **Scope "no fallback" to PLANNING kinds only** — the STATUS/acceptance read leniency (e.g. `acceptance/__init__.py:749`, status.events.jsonl/acceptance-matrix) MUST survive untouched. |
| C-003 | Preserve the KEEP transients from 01KVRJ6P (create-window #1718, coord-deleted #1848) — only planning-artifact gate reads stop consulting coord, not the status/transient probes. |
| C-004 | Forward-only; no migration logic for already-split missions. |
| C-005 | Planning-artifact paths in gate-command entry functions are obtained ONLY through the kind-aware seam (`resolve_planning_read_dir` / a single chokepoint helper); direct `<dir>/{spec,plan,tasks,research,data-model}.md` joins are prohibited and enforced by the FR-010 ratchet. |

## GitHub Issues Addressed

| Issue | Facet | Intended verdict |
|-------|-------|------------------|
| #2107 | setup-plan + accept gate reads on protected-primary/coord topology | fixed (driver) |
| #2085 | acceptance-matrix gate / accept facet | fixed |
| #2102 | record-analysis dirty-tree allowlist + bookkeeping commit-home | fixed |
| #2091 | `next` malformed coord branch (empty mid8) — lock the fix with a scenario-driving guard | verified-already-fixed / regression-guarded |
| #2088 | ownership-overlap validator dependency-exemption — lock the fix with a guard | verified-already-fixed / regression-guarded |
| #2100 | residual inline meta-reader sweep (in-mission scope only) | partial / deferred-with-followup (touched modules only) |
| #2074 | CT3 test-factory drift — this mission fixes the `test_mid8_direct_routing` instance (FR-008) via a production-shaped `meta.json` fixture; #2074 owns the broader factory-delegation work | relates / instance-fixed |
| #1868 | epic — canonical seams / mission identity (mid8 routing facet: FR-006/FR-008) | advances |
| #1878 | umbrella — coordination placement/identity strangler | advances |
| #1716 | epic — coordination topology coherence | advances |

## Out of Scope

- The full ~62-site #2100 meta-reader backlog beyond touched modules (deferred).
- Any change to the write/placement side (#2106 owns that; this is read-only completion).
- `tests/runtime/` gate-path + #2109 red orphans (handled in a separate CI-gating PR).
