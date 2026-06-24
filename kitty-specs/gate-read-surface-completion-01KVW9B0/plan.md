# Implementation Plan: Gate-command Read-surface Completion

**Branch**: `feat/gate-read-surface-completion` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/gate-read-surface-completion-01KVW9B0/spec.md`

## Summary

Complete the **read side** of #2106's write re-partition: every planning-lifecycle
GATE/verify command must resolve planning-artifact reads through the single
kind-aware seam (`resolve_planning_read_dir`, post-#2106) instead of the
topology-aware resolver (→ coord) or a bespoke per-command workaround. The
pre-plan squad established this is a **brownfield consolidation**, not a 2-site
patch: ~13-15 planning-read sites across 3 modules, with **4 bespoke workarounds
to retire onto one canonical seam** (FR-009) plus a **literal-ban ratchet**
(FR-010) so the cluster cannot regrow. Two lanes: **A** (the gate-read spine +
consolidation + ratchet) and **B** (lock the 3 already-landed #1716 residual
fixes with scenario-driving guards). Forward-only; behavior-neutral for flattened
missions; build on #2106's seam (no new resolver, C-001/C-006).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `missions._read_path_resolver` (`resolve_planning_read_dir`, `primary_feature_dir_for_mission`, `candidate_feature_dir_for_mission`, `resolve_handle_to_read_path`); `mission_runtime.artifacts` (`is_primary_artifact_kind`, `MissionArtifactKind`, `_COORD_RESIDUE_FILENAMES`, the kind partition); `cli/commands/agent/mission.py` (`setup_plan`, `_find_feature_directory`, the `_ARTIFACT_TYPE_TO_KIND` map at :1106, record-analysis, the primary-anchor helper pair); `cli/commands/agent/tasks.py` (`map-requirements`, `resolve_feature_dir_for_mission`); `acceptance/__init__.py` (the ~9-read accept cluster, `status_feature_dir`); `ownership/validation.py`; `runtime/next/runtime_bridge.py`
**Storage**: Git branches/worktrees + `meta.json` mission identity (no DB)
**Testing**: pytest — `tests/architectural/` (FR-010 literal-ban ratchet + behavioral two-surface guard), `tests/missions/` + `tests/specify_cli/` (per-command red-first repros via the real entry points, composed `<slug>-<mid8>` fixtures), flattened-regression
**Target Platform**: Linux/macOS developer CLI
**Project Type**: single (Python CLI / library)
**Performance Goals**: N/A (planning-lifecycle CLI operations; no hot path)
**Constraints**: build on #2106's `resolve_planning_read_dir`, no parallel/new resolver (C-001/C-006); unification not parity, scoped to PLANNING kinds — STATUS read leniency survives (C-002); preserve KEEP transients #1718/#1848 (C-003); forward-only (C-004); planning paths only via the kind-aware seam, no direct `<dir>/<artifact>.md` joins (C-005)
**Scale/Scope**: ~13-15 planning-read sites + 4 bespoke helpers to retire + 1 chokepoint helper + 1 architectural ratchet + 3 lock-the-fix guards + behavioral verification

## Charter Check

*GATE: charter context is `compact` (no project charter file).* No charter gates
to evaluate; standard doctrine applies (DIRECTIVE_034 red-first via pre-existing
entry points, DIRECTIVE_041 behavioral-not-structural guards, unification-not-parity,
realistic production-shaped fixtures). Section satisfied.

## Project Structure

### Documentation (this mission)

```
kitty-specs/gate-read-surface-completion-01KVW9B0/
├── plan.md              # This file
├── research.md          # Phase 0 (consolidates the 4-lens pre-plan squad)
├── data-model.md        # Phase 1 (the planning-read site map + kind→surface model)
├── contracts/           # Phase 1 (gate-read seam contract + ratchet contract)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── mission_runtime/
│   └── artifacts.py              # kind partition + self-bookkeeping allowlist (IC-05)
├── specify_cli/
│   ├── missions/_read_path_resolver.py   # resolve_planning_read_dir — the canonical seam (IC-01)
│   ├── cli/commands/agent/
│   │   ├── mission.py            # setup_plan (IC-02), record-analysis double-resolution (IC-04),
│   │   │                         #   primary-anchor helper pair retirement (IC-01); _ARTIFACT_TYPE_TO_KIND:1106
│   │   └── tasks.py              # map-requirements WP-tasks read (IC-04)
│   ├── acceptance/__init__.py    # the ~9-read accept cluster, status_feature_dir split (IC-03)
│   ├── ownership/validation.py   # #2088 dep-exemption guard (IC-09)
│   └── runtime/next/runtime_bridge.py   # #2091 mid8 guard (IC-08)

tests/
├── architectural/   # FR-010 literal-ban ratchet + two-surface behavioral guard (IC-07/IC-11)
├── missions/        # per-command red-first repros, flattened regression (IC-11)
└── specify_cli/     # command-level behavior + FR-008 fixture re-pin (IC-10)
```

**Structure Decision**: Single Python CLI/library. The change concentrates a
canonical kind-aware read seam (`_read_path_resolver`) and retires the bespoke
per-command path reconstructions in `mission.py`/`tasks.py`/`acceptance` onto it,
fenced by an architectural ratchet.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` translates these into WPs.
> The plan fences a **Foundation** (IC-00, the write twin — lands FIRST), **Lane A**
> (spine: IC-01..IC-07) and **Lane B** (lock-the-fix: IC-08..IC-10); IC-11 verifies both.
> Lane B is parallelisable with Lane A's spine after IC-00. IC-00 was added post-tasks by
> the adversarial squad (paula/alphonso/debbie): the finalize-tasks COMMIT (site #14) was
> UNOWNED, and the same-class write-branch misresolution blocks the implement loop.

### IC-00 — Write-surface resolver foundation (the WRITE twin; unblocks the implement loop)

- **Purpose**: Re-point the write-side surface resolution onto the primary/kind-aware seam — the consolidation's WRITE twin (FR-004 anti-"resolution to the repo primary", FR-009(e) finalize-tasks commit). **Fixes the editable CLI so the implement loop runs** (chicken-and-egg blocker — `implement WP##` and `finalize-tasks` misresolve their commit/planning branch to protected `main` until this lands).
- **Relevant requirements**: FR-004, FR-009 (e). C-001/C-002/C-003/C-004.
- **Affected surfaces**: `core/paths.py:617` `get_feature_target_branch`, `core/git_ops.py:371` `resolve_target_branch` (both `candidate_feature_dir_for_mission` → coord → fallback `main`); the finalize-tasks COMMIT in `mission.py` (site #14). The already-proven reference fix: `core/paths.py:630-675` `resolve_merge_target_branch` (uses `primary_feature_dir_for_mission`).
- **Sequencing/depends-on**: none (foundation; lands FIRST — every lane root depends on it). The finalize-tasks `mission.py` edit is a justified out-of-map edit, disjoint from IC-01's chokepoint region; serialized by landing before IC-01.
- **Risks**: out-of-map `mission.py` collision with IC-01 (mitigated by non-adjacent functions + WP00-first ordering); over-reach into status/coord write destinations (only the planning commit/branch moves — C-002/C-003).

### IC-01 — Canonical kind-aware read chokepoint + retire bespoke helpers

- **Purpose**: Establish/confirm the single seam (`resolve_planning_read_dir(kind)`) that every gate command consumes, and **retire the 4 bespoke planning-read workarounds** onto it (the consolidation — one seam, N callers, no parallel impl).
- **Relevant requirements**: FR-004, FR-009. C-001/C-005/C-006.
- **Affected surfaces**: `_read_path_resolver.py:1244` (seam, exists); `mission.py:1308,1327` (primary-anchor helper pair → retire), `:1106` (`_ARTIFACT_TYPE_TO_KIND` kind lookup).
- **Sequencing/depends-on**: IC-00 (write-surface foundation — fixes the editable CLI; lands the finalize-tasks COMMIT `mission.py` edit before IC-01 branches).
- **Risks**: the seam already exists (pure adoption) — the work is retirement without behavior drift; do not introduce a new resolver (C-001 smell).

### IC-02 — setup-plan re-point

- **Purpose**: `setup_plan` reads spec.md via the seam (`kind=SPEC`), not `_find_feature_directory`→`resolve_handle_to_read_path` (→ coord).
- **Relevant requirements**: FR-001. **Affected**: `mission.py:2203/2224`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: red-first MUST use a composed `<slug>-<mid8>` primary dir (bare-slug masks the divergence — false green).

### IC-03 — accept-gate multi-site re-point (highest risk)

- **Purpose**: Move the ~9 planning reads (spec/plan/tasks/research/data-model) off the coord-aware `status_feature_dir` onto the seam; **keep the STATUS/acceptance reads on `status_feature_dir`**.
- **Relevant requirements**: FR-002 (#2085). **Affected**: `acceptance/__init__.py:1179-1187`, `_missing_artifacts:596`, status read `:1174`, leniency `:749`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: splitting the single `status_feature_dir` variable per-partition without breaking the STATUS_STATE/events read — the mission's core complexity (priti/alphonso).

### IC-04 — map-requirements + record-analysis double-resolution

- **Purpose**: Route `map-requirements` WP `tasks/*.md` read (the squad-found missed site) through the seam; collapse record-analysis's manual coord-then-primary double-resolution.
- **Relevant requirements**: FR-004, FR-009. **Affected**: `tasks.py:3727`, `mission.py:1980`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: shared `mission.py` with IC-02/IC-05 — serialize or confine to non-overlapping functions.

### IC-05 — record-analysis self-bookkeeping allowlist (NOT a seam-read)

- **Purpose**: Allowlist spec-kitty's own bookkeeping files (`meta.json`, `.kittify/encoding-provenance/global.jsonl`) in the dirty-tree preflight, kept **separate** from the coord-residue partition (ANALYSIS_REPORT is coord; "stale primary spec.md = real dirt" must hold).
- **Relevant requirements**: FR-003 (#2102). **Affected**: `artifacts.py:113` (`_COORD_RESIDUE_FILENAMES` / a dedicated allowlist).
- **Sequencing/depends-on**: none (independent of the seam).
- **Risks**: conflating the self-bookkeeping allowlist with the coord-residue partition (debbie's invariant hazard).

### IC-06 — in-mission meta-reader sweep

- **Purpose**: Route the residual inline `json.loads(meta…)` reads in the touched modules through `load_meta`.
- **Relevant requirements**: FR-005 (#2100, in-mission scope only). **Affected**: the modules IC-02..IC-05 touch.
- **Sequencing/depends-on**: IC-02..IC-05 (defines the touched set).
- **Risks**: scope creep — the ~62-site backlog stays deferred (Out of Scope).

### IC-07 — literal-ban architectural ratchet

- **Purpose**: An architectural test with TWO arms: (read arm) forbid any gate-command entry function from directly joining `<feature_dir>/{spec,plan,tasks,research,data-model}.md` or topology-routing a planning read; (**write arm**) forbid a write-branch resolver (`get_feature_target_branch`, `resolve_target_branch`, finalize-tasks commit) anchoring its `meta.json` lookup to `candidate_feature_dir_for_mission` (→ `main`) — fences IC-00's fix. Makes FR-004/FR-009(e) enforceable, prevents regrowth. Non-vacuity via a MANDATORY runnable synthetic-AST self-test (both arms).
- **Relevant requirements**: FR-009 (e), FR-010, C-005. **Affected**: `tests/architectural/`.
- **Sequencing/depends-on**: IC-00 (write arm) + IC-01..IC-06 (read arm — ratchet the consolidated state).
- **Risks**: must allow the legitimate STATUS reads + the read/write seams; scope the AST/path scan precisely (avoid false positives on status paths or genuine topology reads).

### IC-08 — #2091 next mid8 guard (Lane B)

- **Purpose**: Dedicated red-first guard for the empty-mid8 → malformed coord branch failure through the `next` entry point (fix exists at `runtime/next/runtime_bridge.py`).
- **Relevant requirements**: FR-006. **Sequencing**: none (Lane B, parallel). **Risks**: revert the guard to prove RED.

### IC-09 — #2088 ownership-overlap guard (Lane B)

- **Purpose**: Dedicated red-first guard for dependency-ordered shared-`owned_files` exemption through `finalize-tasks --validate-only` (fix at `ownership/validation.py:161`).
- **Relevant requirements**: FR-007. **Sequencing**: none (Lane B). **Risks**: revert the exemption to prove RED.

### IC-10 — #2074 fixture re-pin (Lane B)

- **Purpose**: Re-pin `test_mid8_direct_routing` to a production-shaped `meta.json` fixture (via the canonical factory) so it exercises the real `resolve_mid8` routing.
- **Relevant requirements**: FR-008. **Sequencing**: none (Lane B). **Risks**: use the canonical mission factory, not a hand-built dict (DIRECTIVE_041 / #2074).

### IC-11 — Behavioral verification + flattened regression

- **Purpose**: Prove the bifurcation behaviorally (planning read → primary, status read → coord) per command, the flattened-neutral regression, and the FR-006/007 red-first reverts.
- **Relevant requirements**: NFR-001, NFR-002, NFR-004. **Sequencing**: all. **Risks**: the guard must be behavioral (two-surface), not a structural count; composed `<slug>-<mid8>` fixtures.
