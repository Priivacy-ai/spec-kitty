# Paula Patterns — Post-TASKS adversarial review

**Profile applied:** `paula-patterns` (architecture-scout / duplication lens). This is
the exact recurrence-and-ownership surface Paula exists for: a mission whose entire
reason-to-exist is to RETIRE parallel planning-surface resolutions onto one canonical
seam. Lens = "does the WP decomposition CONSOLIDATE, or does it re-create the parallel
impls per-WP?"

**Verdict (headline): REAL consolidation on the READ side — with ONE material coverage
hole (site #14 finalize-tasks COMMIT) that, left as-is, re-creates the very class the
mission exists to kill, on the write side.**

---

## 1. Consolidation integrity — REAL (read side)

WP01 is a genuine chokepoint-seam foundation, not a per-WP patch:

- WP01 (`WP01...md:123-148`, T001) adds ONE module-level `_planning_read_dir(repo_root,
  slug, *, artifact_type)` that wraps `_artifact_kind_for` + `resolve_planning_read_dir`.
  It does NOT invent a new resolver (C-001 honored — it wraps the existing
  `_read_path_resolver.py:1244` seam). T002/T003 (`:150-194`) RETIRE the bespoke
  primary-anchor helper pair (`mission.py:1308,1327`) onto it, and T004 (`:196-209`) is
  an explicit "no parallel primary-anchor path survives" audit. This is the real
  brownfield-consolidation shape (one seam, N callers).

- The consumers genuinely FUNNEL through WP01's seam, they do NOT reconstruct resolution:
  - WP02 (`WP02...md:131-134`): `spec_read_dir = _planning_read_dir(repo_root,
    mission_slug, artifact_type="spec")` — consumes the chokepoint.
  - WP03 (`WP03...md:94,103,131`): calls `resolve_planning_read_dir(kind=...)` directly
    (legitimate — acceptance lives outside `mission.py`; the contract explicitly permits
    consuming the underlying seam, C-001 forbids a NEW resolver, not the existing one).
  - WP04 (`WP04...md:143,154`): `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)` for
    map-requirements and `_planning_read_dir` for the record-analysis read leg.
  - WP05 sweep + WP06 ratchet layer on top.

  None of WP02/03/04 stand up a second resolver. The dependency chain (WP02/03/04 →
  WP01; WP05 → WP02/03/04; WP06 → WP01-05) serializes the shared `mission.py` and makes
  the seam exist before anyone consumes it. **Consolidation is real, not fake.**

## 2. Site #14 (finalize-tasks COMMIT) — NOT assigned to any WP. COVERAGE GAP. (BLOCKER)

This is the one that re-creates the parallel impl. The site was folded into FR-004 +
FR-009(e) + data-model row 14 AFTER the WPs were written, and **no WP picked it up.**

Evidence it is unowned:
- `grep -niE 'finalize-tasks|COMMIT'` across all 10 WP files: every `finalize-tasks`
  hit is either the KEEP read/verify (`WP01...md:101,190`; `WP06...md:85`) or the #2088
  ownership-validator entry point (`WP08`). **No WP body, subtask, or DoD owns the
  finalize-tasks COMMIT/WRITE surface.**
- data-model row 14 (`data-model.md:33`) tags it **RESIDUAL — write-side (IC-01/04)**;
  FR-009(e) (`spec.md:80`) calls it "the write-side twin, must resolve via the same
  kind-aware seam."
- WP04 — the only WP touching a write surface (record-analysis) — explicitly scopes
  AROUND it: it preserves the record-analysis write anchor and never mentions
  finalize-tasks (`WP04...md:156-161`).
- WP10's behavioral net (`WP10...md:113-114`, T031) drives only `setup_plan` / accept /
  `map_requirements` / `record_analysis` — finalize-tasks COMMIT is absent, so it is
  not even verified at closeout despite WP10 carrying `FR-009`.
- The seam CONTRACT is read-only: `read_planning_artifact(...)`, G-1..G-5 all say
  "read"; there is no write/commit clause (`contracts/gate-read-seam.md:5-31`).
- The mission's own dogfood repro (`research/dogfood-finalize-tasks-repro.md:18-28`)
  says finalize-tasks resolves its commit branch to the protected `main` **regardless of
  topology or current branch**, and the implement phase "likely hits the same class."

**Impact:** this is exactly the whack-a-field / parallel-impl failure mode Paula guards.
Reads get consolidated onto the seam; the finalize-tasks WRITE keeps its bespoke
commit-to-primary resolution. The mission ships claiming FR-009 ("no parallel
implementation survives") while a parallel write resolution survives — and the
implement loop will be blocked by the refusal-to-commit-to-`main` the repro already hit.

**Remediation (pick one):**
- (a) Add a **new WP** (or a subtask to WP04, which already owns the record-analysis
  write seam and a `mission.py` out-of-map edit) that routes the finalize-tasks
  planning-artifact COMMIT through the kind-aware WRITE seam (the `_ARTIFACT_TYPE_TO_KIND`
  map at `mission.py:1106` is the ready-made lookup), with a red-first test driving
  `finalize-tasks` and asserting the commit targets `target_branch`, not protected `main`.
- (b) Extend the seam contract + FR-010 ratchet to the WRITE side (see §3).
- Minimum: the new WP/subtask MUST appear in WP10's behavioral net (T031) and the
  issue-matrix (#2102 commit-home facet, `spec.md:108`).

## 3. Literal-ban ratchet (WP06) — STRONG for reads, BLIND to the write twin

- For READS the ratchet is non-vacuous: WP06 T022-T024 (`WP06...md:105-147`) scans
  gate-command entry functions for direct `<dir>/{spec,plan,tasks,research,data-model}.md`
  joins AND for planning reads via `resolve_handle_to_read_path` /
  `_find_feature_directory` / `resolve_feature_dir_for_mission`, with an anti-mutant
  proof (T024) that a re-introduced join → RED. It reuses the canonical AST helper and
  scopes to gate-command surfaces (precision over recall). This is a real gate, not a
  vacuous assertion — patched-but-not-consolidated read code would NOT pass it.

- **BUT the ratchet says nothing about the COMMIT-to-primary.** Both the ratchet
  contract (`contracts/gate-read-seam.md:33-44`) and WP06's objective (`WP06...md:59-63`)
  are exclusively about "planning-artifact READ." A finalize-tasks commit that resolves
  its write surface to protected `main` via a bespoke resolution would **pass the
  ratchet green** — the ratchet does not detect the write-side parallel impl. So even
  with WP06 in place, FR-009(e) remains documentation, not a gate.

  **Remediation:** if §2 is fixed in code, extend the FR-010 ratchet (WP06 T022) to also
  flag a planning-artifact COMMIT/WRITE that resolves to the repo primary `main` outside
  the kind-aware write seam — otherwise a future finalize-tasks-shaped command silently
  re-commits to `main`.

## 4. Per-WP DoD fakeability (consolidation angle)

Read-leg DoDs are sound — they cannot be marked done while leaving a bespoke read:
- WP01 DoD (`WP01...md:246-257`) requires the FR-009 audit "no parallel primary-anchor
  planning-read path survives" — a surviving bespoke read fails the DoD.
- WP04 DoD (`WP04...md:186-194`) requires the record-analysis double-resolution
  COLLAPSED and is explicit that only the read leg moves (write preserved). Good — it
  cannot collapse the read while leaving a double read.
- WP06 ratchet is the cross-WP backstop for surviving reads.

**The one fakeable seam is the write twin (§2):** every WP can hit "done" — WP04 with its
write anchor "preserved," WP10 with its four-command behavioral net green, WP06 ratchet
green — while the finalize-tasks COMMIT keeps its bespoke primary resolution, because no
DoD anywhere asserts the finalize-tasks write surface. The parallel WRITE impl survives a
fully-green mission. That is the decomposition's blind spot.

## Scout summary matrix

| Lens | Finding | Severity |
|------|---------|----------|
| Consolidation integrity (read) | REAL — WP01 chokepoint, WP02/03/04 consume it, no parallel read resolver | OK |
| Site #14 finalize-tasks COMMIT | UNOWNED by any WP/subtask/DoD/contract/ratchet; FR-009(e)+data-model row 14 dangling | **BLOCKER** |
| Ratchet strength (read) | STRONG, non-vacuous, scoped, anti-mutant | OK |
| Ratchet strength (write) | BLIND — does not flag commit-to-primary; FR-009(e) unenforceable | **HIGH** |
| DoD fakeability | Read DoDs sound; WRITE twin fakeable (mission green w/ parallel write surviving) | **HIGH** |
