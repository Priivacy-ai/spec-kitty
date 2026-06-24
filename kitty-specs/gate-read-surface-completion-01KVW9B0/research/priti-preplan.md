# Pre-PLAN Sizing and Decomposition — Planner Priti

**Lens:** sizing, WP decomposition, dependency/risk map
**Spec:** `gate-read-surface-completion-01KVW9B0/spec.md` (8 FRs)
**Branch:** `feat/gate-read-surface-completion` @ `42b956e40`
**Directives applied:** 003 (decision documentation — all sequencing/split choices documented below)

---

## 1. Sizing verdict: ONE mission, TWO explicit lanes

**Verdict: keep as one mission, but the plan MUST fence two lanes with explicit naming.**

**Rationale (DIRECTIVE-003 traceability):**

Lane A — "Gate-read spine" (FR-001/002/003/004/005): a single root cause (#2107 live-reproduced at `mission.py:2203-2224`), a single class of fix (adopt `resolve_planning_read_dir` across gate commands), and shared acceptance tests (coord-topology + flattened regression matrix). All five FRs touch intersecting call-sites in `cli/commands/agent/mission.py` and `acceptance/__init__.py`; splitting them yields a half-fixed surface.

Lane B — "Lock-the-fix residuals" (FR-006/007/008): test-only or fixture-only work; product code is already correct at `runtime/next/runtime_bridge.py:223-231`, `ownership/validation.py:161`, and `cli/commands/mission_type.py:632`. The shared theme is "write a red-first regression guard for an already-landed fix." No call-site in Lane B overlaps with Lane A's edited files.

**Against splitting into a separate mission:** the residuals (#2091/#2088/#2074) are explicitly tracked in the spec's issue matrix with intent to close them within this mission. A separate mission adds overhead (spec/plan/tasks cycle) for ~3–5 tests and one fixture re-pin. The Eisenhower matrix places them as urgent+low-effort: lock them now while the branch is open. Alphonso's pre-plan concurs (§1 recommendation). Keep as one mission; enforce the lane boundary in the plan.

---

## 2. WP decomposition

### WP skeleton (Lane A spine → Lane B lock)

| WP | FRs | Description | Depends on | Shared surface risk |
|----|-----|-------------|------------|---------------------|
| WP01 | FR-001, FR-004 (partial) | **setup-plan re-point.** Replace `_find_feature_directory` call in `setup_plan()` with `resolve_planning_read_dir(kind=SPEC)`. Add red-first test (NFR-002/NFR-004) via `setup_plan` entry point on coord-topology mission fixture. | — | `mission.py` write (heaviest file in the mission: 4125 LOC) |
| WP02 | FR-002, FR-004 (partial) | **Accept gate re-point.** Split `status_feature_dir` in `acceptance/__init__.py:collect_feature_summary()` into (a) per-kind planning reads (`resolve_planning_read_dir(kind=SPEC/PLAN/TASKS/…)`) and (b) STATUS reads that keep `_status_read_feature_dir`. Re-pin `_missing_artifacts` call to a planning-surface dir. Add coord-topology + flattened regression tests. | WP01 (confirms the per-kind seam works end-to-end before touching accept) | `acceptance/__init__.py` — highest-complexity WP; mixes STATUS-partition and PRIMARY-partition reads on one `status_feature_dir` variable |
| WP03 | FR-003, FR-004 (partial) | **record-analysis dirty-tree allowlist.** Ensure `_enforce_analysis_report_write_preflight()` (`mission.py:892`) correctly classifies `meta.json` and `.kittify/encoding-provenance/global.jsonl` as bookkeeping residue via `is_coordination_artifact_residue_path`. NOTE: record-analysis's artifact kind is COORD-partition (`ANALYSIS_REPORT`); do NOT route its own read through a SPEC-kind seam (design correction from Alphonso §2). Add red-first dirty-tree scenario test. | WP01 | `mission.py` — same file as WP01, but a different function; serialize with WP01 |
| WP04 | FR-004 (sweep), FR-005 | **Chokepoint helper + meta-reader sweep.** Introduce a single kind-aware planning-artifact-path helper (or verify `check-prerequisites` tail and `finalize-tasks` verify already route correctly through the primary-anchored seam). Route residual inline `json.loads(meta…read_text())` in touched modules through `load_meta`. Add an architectural ratchet asserting no gate command directly joins `<feature_dir>/spec.md|plan.md|tasks.md` (makes FR-004 enforceable, per Alphonso §3 + §4). | WP01, WP02, WP03 | `mission.py` + `acceptance/__init__.py` (sweep touches both; must run after WP01–03 are merged to lane base) |
| WP05 | FR-006 | **next mid8 regression guard.** Add red-first test through the `next` command entry point (coord-topology, empty mid8 → malformed branch → `git worktree add` 128). Prove red on pre-fix `runtime_bridge.py` (revert the `if coord_routing_topology and not _mid8: raise` guard). Close #2091 in the mission matrix. | — | `runtime_bridge.py` only; no `mission.py` / `acceptance` contact |
| WP06 | FR-007 | **ownership-overlap dependency-exemption guard.** Add red-first test driving `finalize-tasks --validate-only` with same-lane sequential WPs sharing an `owned_files` glob. Prove red on pre-fix `validation.py` (remove `_dependency_reachability` exemption call). Close #2088. | — | `ownership/validation.py` only |
| WP07 | FR-008 | **mid8-test fixture re-pin.** Re-pin `tests/specify_cli/test_mid8_direct_routing.py::test_mission_type_read_mid8_truncates_then_declines` to write `meta.json` (via canonical mission factory) instead of `full.json/explicit.json/bare.json`. Prove re-pinned test is RED on unfixed fixture, GREEN after. Close #2074 (instance only). | — | `test_mid8_direct_routing.py` only; test-only change |
| WP08 | — | **Issue-matrix + verification.** Run full `tests/architectural/` sweep on the merged lane base; fill in-mission issue matrix verdicts; confirm NFR-001 flattened-mission regression; verify NFR-004 mutant-killing guard. | WP01–WP07 | read-only; no source change |

**Parallelisation opportunity:**
- WP05, WP06, WP07 (Lane B) are fully independent of each other and of WP01–WP04. They can start as soon as WP01 is approved (the mission branch is up), or even in parallel from branch base if the implementer team has capacity.
- WP01 must precede WP02 and WP03 (establishes the seam contract the downstream WPs rely on and reduces merge risk for the heavy `mission.py`).
- WP04 must follow WP01–WP03 (the sweep validates the whole surface after partial re-points land).
- WP08 must follow all.

---

## 3. Risk / ROI ranking (Eisenhower-aligned)

| Rank | WP | FR | Risk level | Rationale |
|------|----|----|-----------|-----------|
| 1 (highest) | WP02 | FR-002 | HIGH | `acceptance/__init__.py` mixes STATUS-partition and PRIMARY-partition reads on a single variable (`status_feature_dir`). Splitting cleanly requires enumerating every read inside `collect_feature_summary` and calling the correct surface per kind. Wrong split silently regresses flattened missions or breaks status-lane reads. Test matrix must cover both topologies. |
| 2 | WP01 | FR-001 | MEDIUM-HIGH | `setup_plan` at `mission.py:2203` is the driver bug (live-reproduced). The fix is a targeted call-site swap, but `mission.py` is 4125 LOC and has many near-call-site guards (SaaS preflight, branch protection) — risk of accidental context-swap. Red-first test guards it but demands care. |
| 3 | WP04 | FR-004/005 | MEDIUM | The chokepoint helper + architectural ratchet are additive but cut across both `mission.py` and `acceptance/__init__.py`. The ratchet (AST-level test) must not be vacuous (cannot match only the literal strings the team happened to add — must be a grep/AST of the actual direct-join pattern). |
| 4 | WP03 | FR-003 | MEDIUM-LOW | Allowlist classification is a single predicate call; the risk is mis-classifying what counts as "bookkeeping residue." The design correction (FR-003 is NOT a planning-read seam fix but an allowlist fix) must be respected — do not route record-analysis's own kind through `resolve_planning_read_dir(kind=SPEC)`. |
| 5 | WP05 | FR-006 | LOW | Product fix is in place. Risk is in writing a convincing red-first test through the `next` entry point without being able to easily revert the existing runtime. Suggest injecting a mock or parametrised fixture that exercises the malformed-branch path. |
| 6 | WP06 | FR-007 | LOW | Product fix is in place. Test via `finalize-tasks --validate-only` is a clean integration-style test using `WPMetadata` stubs (per the spec §3 note). |
| 7 (lowest) | WP07 | FR-008 | VERY LOW | Pure test re-pin. Product code is already correct. Only risk is writing to `meta.json` via an old/hand-built factory instead of the canonical one (see Alphonso §4 / DIRECTIVE-041 note). Use the canonical mission factory. |
| 8 | WP08 | — | — | Gate-check; risk = discovering a gap post-merge. Running arch-gate sweep pre-merge per the post-merge arch-gate adjudication memory. |

**De-risking sequence:** implement WP01 → green → WP02 (hardest, needs WP01 as confidence baseline) → WP03 in parallel with WP02 once WP01 is merged → WP04 after WP02+WP03 → WP05/06/07 in parallel at any point after branch is stable.

---

## 4. Dependency on #2106 surfaces (C-001/C-006)

**Confirmed: `resolve_planning_read_dir` exists and is the single correct seam.** Located at `src/specify_cli/missions/_read_path_resolver.py:1244`. Already imported and used by `tasks.py` (`:1072`, `:1135`). The seam:
- Takes `kind: MissionArtifactKind` and routes to `primary_feature_dir_for_mission` for PRIMARY-partition kinds, `candidate_feature_dir_for_mission` for STATUS-partition.
- Uses `is_primary_artifact_kind` from the public `mission_runtime` package (no parallel classifier — C-006 honored).
- Already handles the C-005 KEEP transients on the STATUS arm (docstring `:1273-1276`).

**No FR requires a new resolver.** All gate commands need only to ADOPT the existing seam; the `_ARTIFACT_TYPE_TO_KIND` dict already exists at `mission.py:1106`. This is purely an adoption mission, not a design mission. Consistent with C-001 ("do NOT introduce a parallel read resolver").

**One smell to watch:** `acceptance/__init__.py` imports `primary_feature_dir_for_mission` and `resolve_feature_dir_for_mission` (lines 7–8) but does NOT yet import `resolve_planning_read_dir`. WP02 must add this import — confirm it does not create a circular import (the existing `tasks.py` import of the same symbol proves it is safe).

**`check-prerequisites` tail needs a secondary audit in WP04:** the current code (`mission.py:1857-1862`) calls `_primary_anchored_feature_dir` with fallback to `_find_feature_directory`. Per FR-004, the fallback to `_find_feature_directory` on a coord-topology mission would still resolve to coord. If `check-prerequisites` reports artifact paths, those paths feed agents who then read files — a path-trust issue. WP04 must enumerate whether this tail reads planning artifact content or only paths; if the former, it falls under FR-004.

---

## 5. Summary table: WP → FR mapping with shared-surface flags

| WP | FRs | Files changed | Shared with another WP? | Serialize? |
|----|-----|---------------|------------------------|------------|
| WP01 | FR-001, FR-004 partial | `mission.py`, test | WP03 shares `mission.py` | WP01 before WP03 |
| WP02 | FR-002, FR-004 partial | `acceptance/__init__.py`, test | WP04 sweeps `acceptance` | WP02 before WP04 |
| WP03 | FR-003, FR-004 partial | `mission.py`, test | WP01 shares `mission.py` | WP01 before WP03 |
| WP04 | FR-004 sweep, FR-005 | `mission.py`, `acceptance/__init__.py`, arch-test | All prior WPs | After WP01+WP02+WP03 |
| WP05 | FR-006 | `runtime_bridge.py`, test | — | Independent |
| WP06 | FR-007 | `ownership/validation.py`, test | — | Independent |
| WP07 | FR-008 | `test_mid8_direct_routing.py` | — | Independent |
| WP08 | — | read-only (arch-sweep) | depends on all | Last |

---

## 6. Design corrections to feed the plan author

Three items from Alphonso's pre-plan that the plan must incorporate (documented here per DIRECTIVE-003):

1. **FR-003 is an allowlist fix, not a planning-read seam fix.** Do not route `record-analysis`'s reads through `resolve_planning_read_dir(kind=SPEC)`. The analysis report kind (`ANALYSIS_REPORT`) is COORD-partition. WP03's change is in `_enforce_analysis_report_write_preflight` — the bookkeeping residue predicate, not the planning-read path.

2. **Add C-005 (proposed):** "Planning-artifact file paths in gate commands are obtained ONLY through `resolve_planning_read_dir` or a helper that delegates to it; direct `<dir>/spec.md|plan.md|tasks.md` joins in gate-command entry functions are prohibited." WP04's ratchet test enforces this.

3. **Sharpen C-001/C-002:** C-001 should add "gate commands ADOPT the existing seam; they MUST NOT add a kind argument to `_find_feature_directory` itself." C-002's "no fallback to the old route" scopes to planning kinds only — the lenient `status_dir if status_dir.exists() else feature_dir` fallback in `_status_read_feature_dir` is a STATUS-partition leniency that must be PRESERVED.
