# Research: Gate-command Read-surface Completion (Phase 0)

Consolidates the 4-lens pre-plan adversarial squad (full findings in
`research/{alphonso,debbie,paula,priti}-preplan.md`). All claims live-verified on
`main`/`feat` @ the spec commit.

## Decision 1 — The seam already exists; this is adoption, not invention

`resolve_planning_read_dir(repo_root, slug, *, kind)` (`_read_path_resolver.py:1244`)
already carries the same kind partition the write side got in #2106
(`is_primary_artifact_kind`, `artifacts.py:85`). **No new resolver** (C-001/C-006).
Today only `agent/tasks.py` consumes it; every other gate command hand-rolls the
resolution. → The mission is **adoption + retirement of parallel impls**.

## Decision 2 — It is one operation duplicated across N sites (paula)

The operation = "resolve the read dir for a planning artifact (post-#2106 on
PRIMARY even for coord topology)." Four divergent workarounds exist:

| Workaround | Site | Disposition |
|------------|------|-------------|
| setup_plan inline coord read (the bug) | `mission.py:2224` | retire → seam (IC-02) |
| record-analysis coord-then-primary double-resolution | `mission.py:1980` | collapse → seam (IC-04) |
| bespoke primary-anchor helper pair | `mission.py:1308,1327` | retire → seam (IC-01) |
| accept reads 6 planning files off `status_feature_dir` (coord) | `acceptance/__init__.py:1179-1187`, `:596` | split planning→seam, keep status (IC-03) |

**The spec originally undersized this ~4-5×** (it framed accept as one site; it is
~9 reads). The real surface is ~13-15 planning reads across 3 modules. The fix is
**consolidation to one canonical seam + a literal-ban ratchet**, not per-site patches.

## Decision 3 — The missed site: map-requirements (debbie)

`map-requirements` reads/writes WP `tasks/*.md` (a PRIMARY kind) from the
topology-routed `feature_dir` (`tasks.py:3727` → `resolve_feature_dir_for_mission`
→ coord) while reading spec.md from primary — a partial residual of the same class.
Added to FR-004 (the anti-"fixed N of M" enumeration).

## Decision 4 — FR-003 is an allowlist concern, not a seam-read (alphonso/debbie/priti)

`ANALYSIS_REPORT` is a COORD-partition kind (`artifacts.py:109`). record-analysis
must NOT be modeled as a `kind=SPEC` planning read. The real gap: `meta.json` and
`.kittify/encoding-provenance/global.jsonl` classify `kind=None` → not allowlisted
→ the dirty-tree preflight falsely blocks. Fix = a **self-bookkeeping allowlist**,
kept **separate** from the coord-residue partition (so "stale primary spec.md =
real dirt" survives). This is the one place the spec was conceptually mis-grouped.

## Decision 5 — The ratchet makes FR-004 enforceable (all four lenses)

Without an architectural literal-ban test forbidding direct
`<feature_dir>/{spec,plan,tasks,research,data-model}.md` joins and topology-routed
planning reads, FR-004 is documentation and a sixth command silently re-reads
coord. → FR-010 + C-005. This is the highest-leverage item for a whack-a-field
cluster.

## Decision 6 — One mission, two lanes (alphonso/priti)

Lane A (gate-read spine + consolidation + ratchet: FR-001/002/003/004/005/009/010)
and Lane B (lock the 3 already-landed residual fixes: FR-006/007/008). Splitting
Lane B into its own mission would waste a full spec/plan/tasks cycle for ~3 tests +
one fixture re-pin. Keep together; fence in the plan. Lane B is fully parallelisable
from base (the fixes already exist; the work is scenario-driving red-first guards).

## Risks carried into implementation

- **WP-accept (IC-03) is the core complexity**: splitting the single
  `status_feature_dir` per-partition without breaking the STATUS_STATE/events read
  (`acceptance/__init__.py:1174`) or the status leniency (`:749`).
- **Red-first false-green hazard**: setup-plan/accept tests MUST use a composed
  `<slug>-<mid8>` primary dir; a bare-slug fixture is canonicalized and masks the
  divergence.
- **Shared `mission.py` (4125 LOC)** touched by IC-01/02/04/05 — serialize or
  confine to non-overlapping functions before merging to the lane base.
- **FR-006 path**: the fix is at `src/runtime/next/runtime_bridge.py` (not
  `_internal_runtime/` — correct before anchoring the guard).

## Brownfield pre-tasks checks (per standing cadence)

- **Foldable issues**: #2107/#2085/#2102/#2100/#2091/#2088/#2074 already folded;
  #1716/#1868/#1878 advanced. No additional foldable split-brain issue found beyond
  the cluster.
- **Split-brain/LOC scan**: the duplication cluster IS the finding (Decision 2) —
  addressed by FR-009 consolidation, not deferred.
- **Deprecations**: none due in the touched surfaces.
