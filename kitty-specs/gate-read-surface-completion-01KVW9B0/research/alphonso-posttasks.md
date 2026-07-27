# Architect Alphonso — Post-TASKS adversarial review

**Mission:** gate-read-surface-completion-01KVW9B0
**Lens:** ownership + lane-integration soundness (the shared-`mission.py` hazard)
**Date:** 2026-06-24
**Directives applied:** D-001 (Architectural Integrity — component/ownership boundaries),
D-003 (Decision Documentation — verify the shared-file decision is recorded + serialized),
D-031 (Context-Aware Design — out-of-map edits crossing ownership contexts need an explicit
serialization layer). D-041 noted, not load-bearing here (no ratchet under review).

---

## 1. Parallel-`mission.py`-collision verdict

### The lane layout (from lanes.json)

| WP | lane | parallel_group | depends_on_lanes | write_scope incl. mission.py? | actual mission.py edit (from WP prompt) |
|----|------|----------------|------------------|-------------------------------|------------------------------------------|
| WP01 | lane-a | 0 | — | **YES** (owns it) | helper pair retirement (`:1269-1357`) + `_planning_read_dir` |
| WP02 | lane-b | **1** | lane-a | NO (test only) | **`setup_plan` (`:2044`)** out-of-map (T007) |
| WP03 | lane-c | **1** | lane-a | NO (`acceptance/__init__.py`) | none |
| WP04 | lane-d | **1** | lane-a | NO (`tasks.py` + tests) | **`record_analysis` (`:1898`)** out-of-map (T016) |
| WP05 | lane-e | 2 | lane-b, lane-c, lane-d | NO (`artifacts.py` + tests) | `record_analysis` allowlist + sweep (out-of-map) |

### Finding (CONFIRMED HAZARD, but auto-merge-safe)

WP02 (lane-b) and WP04 (lane-d) are in the **same parallel_group (1)** and **both depend
only on lane-a (WP01)** — they run **in parallel while both editing `mission.py`**. This is
exactly the shared-file lane-integration hazard the write-surface mission hit.

**However, the collision is benign IF the auto-merge precondition holds — and it does:**
- WP02 edits **`setup_plan`** only (verified live at `mission.py:2044`).
- WP04 edits **`record_analysis`** only (verified live at `mission.py:1898`).
- The two functions are **~146 lines apart and non-adjacent** — git 3-way auto-merge of two
  lane branches touching disjoint hunks succeeds without conflict.
- The shared helper region (`_resolve_mission_dir_name_primary_anchored` `:1269`,
  `_primary_anchored_feature_dir` `:1327`, and the new `_planning_read_dir`) is **WP01's
  exclusive churn**, already merged before group-1 starts (both deps WP01). WP02 only
  *consumes* `_planning_read_dir`; WP04 only *consumes* it. Neither re-touches the helpers.

So the serialization that protects this is: **WP01 → {WP02, WP04} dependency edge** (which
serializes the helper-vs-consumer ordering), plus the **non-overlapping-function** property
(which makes the WP02‖WP04 parallel hunks auto-mergeable). The prompts document this
correctly (WP01 §Branch Strategy line 114-119; WP02 line 82-85; WP04 line 99-103).

### Recommendation on WP04→WP02 (the question posed)

**Do NOT add a WP04→WP02 dependency.** It is unnecessary and would over-serialize:
- The two edits are provably non-overlapping (`setup_plan` vs `record_analysis`), so
  auto-merge is safe without a dependency edge.
- The real serialization that matters — **WP05 (record_analysis allowlist) AFTER WP04
  (record_analysis read-leg collapse)** — is *already present* (WP05 deps WP04). That is the
  one place two WPs edit the **same function** (`record_analysis`), and it is correctly
  serialized.
- Adding WP04→WP02 would couple two independent fixes and slow the lane for no integration
  benefit.

**Caveat / one-line guard for the implementer:** the auto-merge safety rests entirely on
WP02 and WP04 **staying inside their named functions**. If WP02's "audit all planning reads
in `setup_plan`" (T007 step 2) or WP04's record-analysis collapse drifts into the shared
helper region (`:1269-1357`) or a shared import block, the disjoint-hunk guarantee breaks.
Recommend the implement loop **land WP02 and WP04 sequentially (not literally concurrent)**
even though they may parallelise — a cheap insurance against shared-import-line churn at the
top of the file. This is a *process* note, not a dependency-graph change.

**Verdict: PARALLEL-SAFE (conditional).** No graph change required; flag the
stay-in-your-function constraint to the implementers.

---

## 2. Site #14 (finalize-tasks COMMIT) ownership verdict — **DEFECT (P1): UNOWNED, DROPPED**

This is the most serious finding.

- **data-model.md row 14** lists **`finalize-tasks` COMMIT** (`mission.py`, finalize-tasks
  cmd) as **"RESIDUAL — write-side (IC-01/04)"** — resolves the *protected repo primary
  `main`* instead of the mission `target_branch` (a **live dogfood repro**).
- **spec.md FR-004** enumerates it explicitly in the anti-"fixed N of M" list:
  *"~13-15 reads **+ the finalize-tasks commit**, across 3 modules … and **`finalize-tasks`
  COMMIT** (live dogfood repro — resolves the protected repo primary `main` …; see
  `research/dogfood-finalize-tasks-repro.md`)."*
- **spec.md FR-009(e)** makes it a named consolidation target: *"**(e) `finalize-tasks`'s
  commit-surface resolution** … must resolve via the same kind-aware seam — the write-side
  twin."*

**Yet NO WP implements it.** Grep across all 10 WP prompts: `finalize-tasks` appears only as
a **KEEP / already-primary** *read* mention (WP01 lines 101, 166, 190; WP06 line 85) and as
the **test entry point** for the unrelated #2088 guard (WP08). The COMMIT/write-side
re-point (row 14 / FR-009(e)) is **mentioned nowhere in any subtask**. tasks.md has no T-row
for it. The acceptance-matrix rows for FR-004/FR-009 are unfilled boilerplate
(`"TODO: replace with a real acceptance criterion"`, `verified_by: null`) so the gap is not
caught there either.

**Why it slipped:** data-model.md tags row 14 "IC-01/04", but:
- IC-01 (WP01) is scoped to the **primary-anchor read helper pair** and the chokepoint — its
  DoD says nothing about a commit/write surface; it even lists `finalize-tasks` as a *KEEP*.
- IC-04 (WP04) is scoped to **map-requirements read + record-analysis read-leg collapse** —
  its negative scope explicitly excludes write/placement.
- So row 14 was assigned to two ICs whose WPs both **declared it out of their scope.** It
  fell through the seam between them.

**Verdict: site #14 is UNOWNED.** It is an in-scope, spec-enumerated (FR-004 + FR-009(e)),
live-dogfood-repro residual that **no WP will fix**. This is a "fixed N of M" gap of exactly
the kind FR-004/FR-009 were written to prevent.

**Recommendation (pick one before implement):**
1. **Preferred:** add subtasks to **WP04** (it already owns the record-analysis/`mission.py`
   write-adjacent region and the FR-009 collapse mandate) — a red-first dogfood repro driving
   `finalize-tasks` COMMIT to resolve `target_branch` not protected `main`, + the write-seam
   re-point. WP04 already declares an out-of-map `mission.py` edit, so the ownership envelope
   exists. **This pushes the WP02‖WP04 collision risk up**, because WP04 would then touch a
   third `mission.py` region (finalize-tasks cmd) — verify that region is also disjoint from
   `setup_plan`; if finalize-tasks is adjacent to setup_plan, escalate WP04→WP02 serialization
   for *that* reason.
2. Or carve a **new WP** (lane, deps WP01) owning the finalize-tasks commit-surface
   exclusively, so the write-side twin is a first-class, separately-reviewable site.
3. At minimum: if deliberately deferred, **move row 14 to spec.md Out-of-Scope** and strike it
   from FR-004/FR-009(e) — do not leave it enumerated-but-unbuilt (that is a false coverage
   claim the WP06 ratchet and WP10 behavioral guard will not catch, since both are read-only).

---

## 3. owned_files / authoritative_surface correctness

- **No real owned_files OVERLAP** across WPs. Every `owned_files` set is disjoint:
  WP01 `mission.py`(+test); WP02 test only; WP03 `acceptance/__init__.py`(+test);
  WP04 `tasks.py`(+2 tests); WP05 `artifacts.py`(+2 tests); WP06-WP10 each a single test file.
  The mission.py contention is handled as **declared out-of-map edits** (WP02/WP04/WP05), which
  the ownership validator does **not** see — confirming the squad-prompt premise that the
  validator's "no overlap" pass is **necessary but not sufficient**; the dependency-graph +
  non-overlapping-function discipline (Finding 1) is what actually protects it.
- **authoritative_surface prefix check:** all sound except a stylistic note —
  - WP09 `authoritative_surface: tests/specify_cli/test_mid8_direct_routing.py` is a **file**,
    not a directory prefix, but it does prefix its single owned_file (same path). OK.
  - WP04 `authoritative_surface: …/tasks.py` prefixes its primary owned_file `tasks.py`; its
    two test owned_files are NOT under that surface — acceptable (tests are create_intent
    companions), but note WP04's *real* center of gravity spans `tasks.py` **and** an
    out-of-map `mission.py` region not reflected in either surface or owned_files. Cosmetic;
    no action required beyond the Finding-2 fix.
- **No defect** that blocks implement on this axis.

---

## 4. Dependency-graph soundness

Edges (from lanes.json `depends_on_lanes`, mapped to WPs):

```
WP01 ─┬─> WP02 ─┐
      ├─> WP03 ─┼─> WP05 ─> WP06 ─> WP10
      └─> WP04 ─┘                     ^
WP07 ───────────────────────────────┤
WP08 ───────────────────────────────┤
WP09 ───────────────────────────────┘
```

- **No cycle.** DAG is acyclic; parallel_group numbers (0..4) are a valid topological layering.
- **WP05** deps WP02/03/04 — correct: it sweeps the modules those WPs re-pointed, and
  serializes the **record_analysis** shared-function edit behind WP04. Sound.
- **WP06** (literal-ban ratchet) deps WP01-05 — correct: it must fence the *consolidated*
  state, so it has to follow every consolidation WP. Sound.
- **WP10** deps all (WP01-09) — correct: behavioral closeout over the whole surface incl. the
  Lane-B guards. Sound.
- **WP07/WP08/WP09** deps `[]` — correct: Lane-B lock-the-fix guards against already-landed
  fixes (#2091/#2088/#2074), parallelisable from base. Sound.
- **Missing edge — none mechanically**, BUT the **finalize-tasks COMMIT (Finding 2)** has no
  node at all, so there is no edge to be missing — the work simply isn't in the graph. If
  Finding 2 is resolved by adding it to WP04, no new edge is needed (WP04 already deps WP01);
  if a new WP, it should dep WP01 and feed WP06 + WP10.
- **No WP can start before its real prerequisite.** The only real-prerequisite coupling beyond
  the declared edges is the WP02‖WP04 same-file parallel edit (Finding 1), which is
  auto-merge-safe by the non-overlapping-function property — not a missing edge.

**Verdict: dependency graph is SOUND** (acyclic, correctly layered) — with the caveat that it
is sound over an **incomplete node set** (site #14 absent).

---

## Summary of verdicts

1. **WP02‖WP04 parallel mission.py:** PARALLEL-SAFE (conditional). Same parallel_group,
   different functions (`setup_plan` vs `record_analysis`, ~146 lines apart) → auto-merge-safe.
   **Do NOT add WP04→WP02.** Process note: land them sequentially as cheap insurance; flag
   "stay in your function" to implementers.
2. **Site #14 finalize-tasks COMMIT:** **P1 DEFECT — UNOWNED.** In-scope per FR-004 + FR-009(e)
   + data-model row 14 (live dogfood repro), but no WP implements it; assigned to IC-01/04
   whose WPs both declare it out-of-scope. Fix before implement (add to WP04, or new WP, or
   explicitly defer to Out-of-Scope).
3. **owned_files / authoritative_surface:** no real overlap; all surfaces prefix an owned_file
   (WP09 is a file-as-surface, benign). No blocker.
4. **Dependency graph:** SOUND — acyclic, correctly layered (WP05←WP02/03/04, WP06←WP01-05,
   WP10←all, WP07/08/09 from base). Caveat: sound over an incomplete node set (see Finding 2).
