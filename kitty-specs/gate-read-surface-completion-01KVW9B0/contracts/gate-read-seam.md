# Contract: Gate-command Planning-read + Write-surface Seam + Ratchet

Internal API/architectural contract (no HTTP surface).

## Seam contract — READ side

For every planning-lifecycle GATE/verify command that reads a planning artifact:

```
read_planning_artifact(M, artifact) :=
    kind = _ARTIFACT_TYPE_TO_KIND[artifact]        # mission.py:1106 lookup
    dir  = resolve_planning_read_dir(repo_root, M.slug, kind=kind)
    return dir / artifact
```

## Seam contract — WRITE side (the write twin, FR-009(e) / FR-004)

For every planning-lifecycle GATE/verify command that resolves a planning-artifact
**COMMIT / branch**, the mission's `target_branch` is read from `meta.json` on the
**PRIMARY** surface — never the topology-aware candidate (which under coord topology
resolves to the coordination worktree, whose mission dir has no `meta.json`, silently
falling back to the protected repo primary `main`):

```
resolve_commit_branch(M) :=
    meta = primary_feature_dir_for_mission(main_root, M.slug) / "meta.json"
    return meta["target_branch"]                   # NOT candidate_feature_dir_for_mission
```

This is the already-proven shape of `resolve_merge_target_branch` (`core/paths.py:630-675`).
The write-branch resolvers that MUST adopt it: `get_feature_target_branch` (`core/paths.py`),
`resolve_target_branch` (`core/git_ops.py`), and the `finalize-tasks` commit-branch
resolution (`mission.py`). (WP00.)

### Guarantees

- **G-1**: For a PRIMARY-kind artifact (spec/plan/tasks/WP/research/data-model/lanes/meta),
  the read resolves to the primary `target_branch` dir for ALL topologies. (FR-001/002/004)
- **G-2**: For a STATUS/bookkeeping kind (status.events.jsonl, acceptance-matrix,
  analysis-report), the read resolves to its placed surface (coord under coord
  topology) — UNCHANGED. (C-002 status leniency)
- **G-3**: For a flattened/single-branch mission, every read resolves to
  `target_branch` — identical to pre-mission behavior. (NFR-001)
- **G-4**: No gate command reconstructs a planning-read path via topology routing
  or a bespoke primary-anchor helper — all consume the one seam. (FR-009)
- **G-5**: The self-bookkeeping allowlist (`meta.json`, provenance) is consulted by
  the record-analysis dirty-tree preflight and is DISJOINT from the coord-residue
  partition; a stale primary `spec.md` remains non-allowlisted ("real dirt"). (FR-003)
- **G-6** (write twin): For a planning-artifact COMMIT, the resolved commit/branch is the
  mission's `target_branch` for ALL topologies — read from `meta.json` on the PRIMARY
  surface, never the topology candidate (which falls back to the protected repo primary
  `main`). The status/coord commit destinations are UNCHANGED (status events still emit to
  coord). (FR-004 anti-"resolution to the repo primary" + FR-009(e) finalize-tasks commit;
  WP00.)

## Ratchet contract (FR-010 — makes G-4 and G-6 enforceable)

An architectural test (`tests/architectural/`) MUST fail on EITHER arm.

**Read arm** — if any gate-command entry function:

- directly joins `<feature_dir>/{spec,plan,tasks,research,data-model}.md`, OR
- resolves a planning-artifact read through `resolve_handle_to_read_path` /
  `_find_feature_directory` / `resolve_feature_dir_for_mission` (topology-routed).

**Write arm** (G-6) — if any write-branch resolver (`get_feature_target_branch` in
`core/paths.py`, `resolve_target_branch` in `core/git_ops.py`, the `finalize-tasks`
commit-branch resolution in `mission.py`):

- resolves a planning-artifact COMMIT/branch by anchoring its `meta.json` lookup to
  `candidate_feature_dir_for_mission` (→ coord → fallback protected repo primary `main`)
  instead of `primary_feature_dir_for_mission` / the kind-aware write seam.

Allowed (not flagged): the read seam itself, the write seam
(`primary_feature_dir_for_mission` / `resolve_merge_target_branch`), STATUS reads off
`status_feature_dir`, STATUS/coord commit destinations, and the self-bookkeeping allowlist.
The write arm flags ONLY a write-BRANCH resolution anchored to the candidate dir — not
every legitimate topology-aware status read.

The ratchet's non-vacuity is proven by a **MANDATORY runnable synthetic-AST self-test**
(both arms: a violating snippet is FLAGGED, a clean snippet PASSES), with the enumerated
surface/resolver set pinned — not a recorded manual mutation log.

## Anti-mutant / behavioral assertions (IC-11)

- A coord-topology fixture (composed `<slug>-<mid8>` primary dir) MUST show: each
  gate command's PLANNING read ref == `target_branch` **AND** its STATUS read ref ==
  `coord`. (Kills "always coord" and "always primary" mutants.)
- Reverting any IC-02/03/04 site to the topology resolver MUST turn its planning-read
  assertion RED. (Non-vacuous.)
- **Write twin (WP00):** on a coord-topology fixture, `get_feature_target_branch` /
  `resolve_target_branch` / the finalize-tasks COMMIT MUST resolve `target_branch` (NOT
  protected `main`). Reverting the resolver to `candidate_feature_dir_for_mission` MUST turn
  the assertion RED (it resolves `main`). Red proven against the unfixed resolver.
- For #2091/#2088 (Lane B): reverting the product guard MUST turn the new guard RED.

## Caller obligations

Every gate command declares the artifact's kind via `_ARTIFACT_TYPE_TO_KIND` and
reads through the seam. No new CLI surface; `kind` is internal (NFR-003).

On the WRITE side, every command that resolves a planning-artifact commit/branch reads
`target_branch` from `meta.json` on the PRIMARY surface (`primary_feature_dir_for_mission`),
mirroring `resolve_merge_target_branch` — never the topology candidate. (G-6, WP00.)
