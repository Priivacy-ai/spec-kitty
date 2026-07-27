# Debugger-Debbie — Pre-PLAN adversarial research (gate-read-surface-completion-01KVW9B0)

**Branch:** `feat/gate-read-surface-completion` @ `42b956e40`
**Lens:** verify the seam/repro claims + find the MISSED sites (the "fixed N of M" trap).
**Directives applied:** D-001 (architectural integrity — fork vs canonical seam), D-032 (conceptual alignment — per-kind seam ↔ topology resolver divergence matrix), D-003 (decision documentation — persist verified/falsified claims). **LIVE evidence over static** — every claim below re-run, not read.

---

## 0. Executive verdict

The mission's core spine claims (FR-001, FR-002, FR-003, FR-006, FR-007, FR-008) all **HOLD on current branch HEAD** — re-verified by live repro/test, not static reading. The spec's enumeration is **substantially accurate but INCOMPLETE in one place**: it under-enumerates **`map-requirements`** as a residual planning-read site (it reads WP-task files — a PRIMARY kind — from the topology-routed `feature_dir`). FR-004's named set (`setup-plan`, `check-prerequisites` tail, `finalize-tasks` verify, `accept`, `record-analysis`) is the right *spine* but is not the complete M-site set; `map-requirements` (#2064 lineage) belongs in the table as a PARTIAL residual.

---

## 1. FR-001 — `setup_plan` spine claim: **VERIFIED (residual is real)**

`setup_plan` (`cli/commands/agent/mission.py:2044`):
- line **2203** → `_find_feature_directory(repo_root, cwd, explicit_feature=...)`
- `_find_feature_directory` (`mission.py:1211`) → line **1254** `resolve_handle_to_read_path(repo_root, raw_handle, require_exists=True)` — the **topology-aware** seam (returns the `-coord` worktree once materialized).
- line **2224** `spec_file = feature_dir / "spec.md"`; the `is_committed`/`is_substantive` reads (lines 2265-2270) check that coord-resolved `spec_file`.

So `setup_plan` reads `spec.md` through `resolve_handle_to_read_path`, **NOT** `resolve_planning_read_dir(kind=SPEC)`. FR-001's claim is exact.

**LIVE repro (`/tmp/repro_2107_setupplan.py`, re-run):**
```
resolve_planning_read_dir(kind=SPEC)      -> /tmp/repro2107/kitty-specs/demo-coord-mission       (PRIMARY)
resolve_handle_to_read_path (setup-plan)  -> /tmp/repro2107/.worktrees/...-coord/kitty-specs/...  (COORD)
>>> DIVERGENCE: setup-plan facet LIVE.
```
**Realistic-ordering repro** (coord branched off main BEFORE spec authored — the true post-#2106 sequence): coord worktree has **no** `spec.md`, so the coord-resolved `spec_file` → `SPEC_FILE_MISSING`/blocked, while the per-kind seam points at PRIMARY where the spec lives. The block is the reported #2107 failure.

> NB (not a blocker, flag for plan): in the realistic repro the per-kind seam resolved the *bare-slug* primary dir while the spec was committed to the *composed* `<slug>-<mid8>` dir — a handle-canonicalization wrinkle. When the on-disk primary dir is canonical `<slug>-<mid8>` (the normal case), `primary_feature_dir_for_mission` points correctly. The red-first test MUST use a production-shaped composed dir name to avoid masking the fix behind bare-slug resolution.

---

## 2. Definitive M-site enumeration (anti "fixed N of M", FR-004)

All callers of `resolve_handle_to_read_path` / `_find_feature_directory` / `resolve_feature_dir_for_mission` / `primary_feature_dir_for_mission` / `resolve_planning_read_dir` were swept. Only the sites that **read a planning-partition artifact** (`spec.md`/`plan.md`/`tasks.md`/`tasks/WP*.md`/`data-model.md`/`research.md` — `_PRIMARY_ARTIFACT_KINDS`) are gate-read sites; STATUS-partition reads (decisions/index.json, status.events.jsonl, acceptance-matrix.json) keep topology routing CORRECTLY (C-001/C-003).

| Site | file:line | current resolver | planning artifact read | verdict |
|------|-----------|------------------|------------------------|---------|
| **setup-plan** | `mission.py:2203` → `_find_feature_directory` → `resolve_handle_to_read_path` (`:1254`) | **topology-aware (coord)** | `spec.md` (`:2224`), `is_committed`/`is_substantive` (`:2265`) | **RESIDUAL** (FR-001 driver) |
| **accept gate** | `acceptance/__init__.py:1114` `_status_read_feature_dir` → `resolve_handle_to_read_path` (`:749`) | **topology-aware (coord)** | `spec.md`/`plan.md`/`tasks.md`/`research.md`/`data-model.md` (`:1179-1184`), `tasks.md` unchecked (`:1176`), `_missing_artifacts` (`:1187`) | **RESIDUAL** (FR-002) |
| **record-analysis preflight** | `mission.py:1928` `_find_feature_directory` (coord) | topology-aware (coord) drives placement-ref + dirty filter | dirty-tree classify (FR-003) — see §3 | **RESIDUAL** (FR-003 gap is the classifier, not the dir) |
| **record-analysis write/spec-read** | `mission.py:1980` `primary_feature_dir_for_mission`; `analysis_report.py:377` `feature_dir/spec.md\|plan.md\|tasks.md` | **PRIMARY (already)** | spec/plan/tasks hash inputs read from PRIMARY write dir | **OK** (already on primary) |
| **check-prerequisites** | `mission.py:1857` `_primary_anchored_feature_dir` (fallback coord only if no primary) | **PRIMARY-anchored (already)** | `validate_feature_structure(feature_dir)` | **OK** (primary-anchored; not the per-kind seam, but on the right surface — see §5 caveat) |
| **finalize-tasks (read + verify tail)** | `mission.py:2915` `_resolve_mission_dir_name_primary_anchored` → `primary_feature_dir_for_mission` (`:2980`), `planning_dir=_primary_dir` (`:2993`) | **PRIMARY (already)** | `tasks/`, `spec.md`, `tasks.md`, `meta.json` from primary | **OK** (primary-anchored) |
| **map-requirements** | `tasks.py:3727` `_map_requirements_feature_dir` → `resolve_feature_dir_for_mission` (`:401`, action=tasks seam) | **topology-aware (coord)** for `tasks/` | WP `tasks/*.md` frontmatter read+write (`:3775`); spec.md read from PRIMARY (`:3729/3735`, OK) | **PARTIAL RESIDUAL** — **SPEC OMITS THIS** (see §4) |
| decision verify | `decision.py:470` `resolve_handle_to_read_path` | topology-aware (coord) | reads `decisions/index.json` (STATUS kind) | **OK** (correct topology routing, not planning) |
| agent context resolve | `context.py:75` `resolve_handle_to_read_path` | topology-aware | mission-dir resolution, not a planning-artifact read | **OK** (context anchor; downstream callers own their reads) |
| workflow planning-read | `agent/workflow.py:322` `resolve_handle_to_read_path`; `:1094` `primary_feature_dir_for_mission` | mixed | status/branch context | **OK** (status/identity, not gate planning-read) |
| orchestrator_api | `commands.py:281` `resolve_handle_to_read_path` | topology-aware | mission-dir + status | **OK** (status surface) |
| tasks status events | `tasks.py:4147` `resolve_handle_to_read_path` | topology-aware | `status.events.jsonl` (STATUS kind) | **OK** (correct) |

**Spine residuals to fix (planning-read on coord when it should be primary):** `setup-plan`, `accept`, **`map-requirements`**.
**Already-primary (no change needed, but consider routing through the one per-kind seam for uniformity):** `check-prerequisites`, `finalize-tasks`, `record-analysis` write.
**FR-003 is a classifier gap, not a dir-resolution residual** (see §3).

---

## 3. FR-003 (#2102) — record-analysis dirty-tree classifier gap: **VERIFIED**

Preflight `_enforce_analysis_report_write_preflight` (`mission.py:892`) filters dirty paths via `is_coordination_artifact_residue_path(path, mission_slug=...)` (`:924`) under coord topology.

The classifier `_artifact_kind_for_path` (`mission_runtime/artifacts.py:237`) keys on `_COORD_RESIDUE_FILENAMES` (`:113-125`) / `_COORD_RESIDUE_DIRS` (`:127`). **Neither `meta.json` nor `.kittify/encoding-provenance/global.jsonl` appears** in those maps. `.kittify/...` isn't even under `kitty-specs/` so `specs_index` lookup fails → `None`.

**LIVE classification probe:**
```
kitty-specs/<slug>/meta.json                  kind=None  residue_allowlisted=False   <-- would BLOCK
.kittify/encoding-provenance/global.jsonl     kind=None  residue_allowlisted=False   <-- would BLOCK
kitty-specs/<slug>/status.events.jsonl        kind=STATUS_STATE        allowlisted=True
kitty-specs/<slug>/acceptance-matrix.json     kind=ACCEPTANCE_MATRIX   allowlisted=True
```
Both spec-kitty-owned bookkeeping files are classified as **real dirt** → record-analysis preflight falsely blocks. FR-003's claim is exact. **Fix locus per the kind partition:** `meta.json` is `PRIMARY_METADATA` (a `_PRIMARY_ARTIFACT_KINDS` member) — but planning/identity primary kinds are deliberately NOT residue-allowlisted (their stale primary copies are real dirt per the artifacts.py:185 doctrine). So the fix is **not** "add meta.json to `_COORD_RESIDUE_FILENAMES`" — that would mis-state its partition. The mission must decide an **allowlist of self-bookkeeping files that the *preflight* tolerates** (meta.json the command itself may rewrite + the encoding-provenance ledger), distinct from the coord-residue partition. Flag for plan: FR-003 wording ("classify as coordination/bookkeeping residue") risks conflating two concepts — keep the meta/provenance allowlist a SEPARATE preflight concern from coord-residue, or the partition invariant (spec.md primary copy = real dirt) breaks.

---

## 4. MISSED SITE — `map-requirements` (the "fixed N of M" trap)

FR-004 enumerates `setup-plan, check-prerequisites tail, finalize-tasks verify, accept, record-analysis`. It **omits `map-requirements`**, which:
- reads/writes WP `tasks/*.md` frontmatter from `feature_dir = _map_requirements_feature_dir(...)` (`tasks.py:3727`) → `resolve_feature_dir_for_mission` (action="tasks" seam) → **topology-aware → coord worktree** for a coord-topology mission;
- WP-task files are `WORK_PACKAGE_TASK` = **PRIMARY** kind (artifacts.py:93) → they live on primary post-#2106 → coord read/write is the SAME divergence class.

It already reads `spec.md` from PRIMARY (`:3729/3735`), so it's a **PARTIAL** residual (spec ok, WP-task reads wrong). This is exactly the residual the #2064 comment at `_map_requirements_feature_dir` *thought* it fixed ("one read surface … same seam finalize uses") — but finalize re-anchors to `primary_feature_dir_for_mission` AFTER its `_resolve_mission_dir_name_primary_anchored` slug resolution, whereas map-requirements stops at the topology-aware `resolve_feature_dir_for_mission` and never re-anchors the `tasks/` dir to primary. **Recommendation:** add `map-requirements` to the FR-004 M-site table as a residual; its red-first guard drives `map-requirements --batch` on a coord-topology mission and asserts the WP frontmatter write lands on PRIMARY.

---

## 5. Caveat on the "single per-kind seam" framing (FR-004 / C-001)

`check-prerequisites` and `finalize-tasks` are already on the PRIMARY surface but via `_primary_anchored_feature_dir` / `primary_feature_dir_for_mission` — **not** via `resolve_planning_read_dir(kind=...)`. FR-004 says "MUST consult the single per-kind read seam." Literally re-routing these two through `resolve_planning_read_dir` is behavior-neutral (primary kind → `primary_feature_dir_for_mission` internally) and would satisfy "single seam," BUT it would route a STATUS read (if any) through the per-kind branch — verify each call only reads PRIMARY kinds before collapsing. **Flag for plan:** decide whether FR-004 means "every gate planning-read goes through `resolve_planning_read_dir`" (uniformity refactor of 2 already-correct sites) or "no gate read mis-resolves planning to coord" (fix only the 3 real residuals). The spec's NFR-004 (mutant: regressing setup-plan to `resolve_handle_to_read_path` turns RED) only constrains the residual sites — the already-primary sites need a separate non-vacuity story or they're untested no-ops.

---

## 6. FR-006 / FR-007 / FR-008 — lock-the-fix claims

| FR | Claim | Verdict |
|----|-------|---------|
| FR-006 (#2091) | empty-mid8 fix at `runtime/next/runtime_bridge.py:205-231` | **PATH DRIFT**: file is `src/runtime/next/runtime_bridge.py` (NOT `_internal_runtime/`). Fix surface present. Spec's line path needs correcting before the red-first guard anchors to it. Claim (fix exists) holds; cite the right path. |
| FR-007 (#2088) | `_dependency_reachability` exemption; `validation.py:161`; caller threads `_wp_dependencies` at `mission.py:3521` | **VERIFIED**: `_dependency_reachability` at `validation.py:127`, consumed in `validate_no_overlap` at `:161/:194`; caller `validate_ownership(wp_manifests, _wp_dependencies)` at `mission.py:3521`. Exact. |
| FR-008 (#2074) | `_read_mission_mid8` reads `<dir>/meta.json` via `load_meta`, ignores fixture filename → test RED on drift | **VERIFIED LIVE**: `mission_type.py:631` reads `meta_path.parent` via `load_meta`. Test `test_mission_type_read_mid8_truncates_then_declines` writes `full.json`/`bare.json`; `pytest` → `AssertionError: assert '' == '01KV7SFD'`. RED only because fixture drifted; product (`resolve_mid8`) correct. Re-pin to a composed-dir `meta.json`. |

---

## 7. Falsified / flagged claims (D-003 — persist so not re-litigated)

- **FALSIFIED (no FR fails, but accuracy gaps):**
  - FR-004 site list is INCOMPLETE — add `map-requirements`.
  - FR-006 cites the wrong module path (`_internal_runtime/`); correct is `src/runtime/next/runtime_bridge.py`.
  - FR-003 wording risks conflating "self-bookkeeping preflight allowlist" with "coord-residue partition" — keep them separate or the spec.md-primary-copy-is-real-dirt invariant breaks.
- **CONFIRMED no over-claim:** No FR claims a site is residual that #2106 already re-pointed. `check-prerequisites`/`finalize-tasks`/`record-analysis-write` are correctly already-primary; the spec treats them as verify-tail/OK, not as residuals to "fix" — accurate.
- **Red-first hazard:** the setup-plan red-first test MUST use a composed `<slug>-<mid8>` primary dir; a bare-slug fixture masks the divergence behind handle canonicalization (§1 NB).
