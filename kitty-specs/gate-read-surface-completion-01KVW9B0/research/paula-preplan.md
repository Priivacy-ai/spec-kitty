# Paula Patterns — pre-PLAN adversarial research (gate-read-surface-completion-01KVW9B0)

**Profile applied:** `paula-patterns` (architecture-scout / brownfield logical-duplication lens).
**Branch:** `feat/gate-read-surface-completion` @ current (HEAD `42b956e40`).
**Lens question:** does the spec UNDERSIZE the scope? (Standing pattern: a "one operation
duplicated across N sites" cluster is always undersized at spec time.)

---

## 1. Is the gate-read fix ONE operation duplicated across N sites? — YES.

The operation is: **"resolve the read directory for a planning artifact (spec/plan/tasks/
data-model/research/checklist/lanes), which after #2106 lives on PRIMARY even for a
coord-topology mission."**

### The canonical seam already exists (C-001 holds)
- `resolve_planning_read_dir(repo_root, slug, *, kind)` —
  `src/specify_cli/missions/_read_path_resolver.py:1244`. Keys on the SINGLE write-side
  partition via `mission_runtime.is_primary_artifact_kind` (`artifacts.py:202`):
  PRIMARY-partition kind → `primary_feature_dir_for_mission` (topology-blind PRIMARY);
  STATUS-partition kind → `candidate_feature_dir_for_mission` (topology-aware coord).
- PRIMARY partition (`artifacts.py:85`): SPEC, DATA_MODEL, RESEARCH, CHECKLIST,
  FINALIZED_EXECUTION_PLAN, TASKS_INDEX, WORK_PACKAGE_TASK, LANE_STATE, PRIMARY_METADATA.
  → all seven planning kinds resolve PRIMARY. This is the kind-keyed authority.
- **Only `cli/commands/agent/tasks.py` consumes it** (lines 367, 1072, 1135). Every other
  gate/verify command still hand-rolls the resolution.

### N parallel reimplementations of "find the planning dir" (the duplication)
The same operation is open-coded with **four different, divergent workarounds**, none of
which call the canonical seam:

| Site | file:line | How it resolves the planning read | Verdict |
|------|-----------|-----------------------------------|---------|
| **setup_plan** (DRIVER #2107) | `cli/commands/agent/mission.py:2224` | `feature_dir = _find_feature_directory(...)` (coord-aware) then `feature_dir / "spec.md"` | **THE BUG** — no workaround applied → reads coord → `SPEC_FILE_MISSING` (`:2227-2245`). The code comment at `:2251-2261` even *documents* that `spec_file` is on the coord surface. |
| **record_analysis** (#2102) | `cli/commands/agent/mission.py:1928` + `1980` | resolves `feature_dir` coord-aware, then **re-resolves** `write_feature_dir = primary_feature_dir_for_mission(...)` because "coord worktree lacks spec.md" (`:1970-1980`) | hand-patched per-site workaround #1 |
| **finalize-tasks / check-prerequisites** | `cli/commands/agent/mission.py:1308` (`_resolve_mission_dir_name_primary_anchored`), `:1327` (`_primary_anchored_feature_dir`), used at `:1857` & `:2916` | a *separate* PRIMARY-anchoring helper pair that bypasses the coord gate | hand-patched per-site workaround #2 (two bespoke helpers) |
| **accept gate** (#2085/#2107) | `acceptance/__init__.py:1179-1187` | reads `status_feature_dir / "spec.md"`, `/plan.md`, `/research.md`, `/data-model.md`, `/quickstart.md`, `/tasks.md` AND `_missing_artifacts(status_feature_dir)` (`:596`, all 6 required+optional planning kinds) off the **coord** dir, while a `_primary_anchor_feature_dir` helper exists (`:753`, used only at `:1107`) but is NOT used for these planning reads | **un-fixed** — same class as setup_plan, ×~9 reads |

**This is the textbook paula whack-a-field shape:** record_analysis and finalize-tasks each
grew their own ad-hoc "anchor to primary" patch; setup_plan and accept never got one; the
ONE seam that encodes the partition (`resolve_planning_read_dir`) is adopted by exactly one
module. The fix is to **strangle every planning read onto the seam**, not to add a fifth
per-site patch.

---

## 2. Literal / path-construction duplication (latent split-brain sites)

Hand-rolled `feature_dir / "<planning>.md"` joins where `feature_dir` came from a
topology-aware resolver (i.e. could be coord):

- `acceptance/__init__.py:1179,1180,1183,1184` (+1181 quickstart, +1182 tasks) — off `status_feature_dir`.
- `acceptance/__init__.py:596-602` `_missing_artifacts` — SPEC/PLAN/TASKS required + QUICKSTART/DATA_MODEL/RESEARCH optional, off the passed dir (coord).
- `acceptance/__init__.py:609-635` `normalize_feature_encoding` — `resolve_feature_dir_for_mission` (topology-aware) then normalizes every planning file.
- `acceptance/__init__.py:402` `_iter_work_packages` — `resolve_feature_dir_for_mission` then `tasks/` dir (WORK_PACKAGE_TASK = PRIMARY).
- `cli/commands/agent/mission.py:2224,2225,3031` (setup_plan spec/plan; analysis planning_dir/spec.md).
- `cli/commands/research.py:94` `plan_path = feature_dir / "plan.md"`.
- Codebase-wide: **40** `feature_dir / "<planning>.md"`-style joins (grep), many fed by
  `candidate_feature_dir_for_mission` / `resolve_feature_dir_for_mission` callers (≈30
  call sites of those two topology-aware resolvers). Not all are gate reads, but each is a
  latent coord-shadowing site for a PRIMARY-partition artifact.

**Ratchet gap:** there is no guard forbidding `<topology-aware-dir> / "<planning-file>"`.
The seam is opt-in; nothing prevents regrowth (a sixth command will read coord again).

---

## 3. Does the FR set cover the duplication, or only the named symptoms?

**Partially. FR-004 is the right instinct but under-specified.**

- FR-001 (setup-plan), FR-002 (accept), FR-003 (record-analysis dirty-tree) name the three
  driver symptoms. Good.
- **FR-004** *says* "ALL planning-lifecycle GATE/verify commands … MUST consult the single
  per-kind read seam — no command may reconstruct a planning-read path via topology
  routing." This is the correct consolidation requirement — **but it enumerates only
  `setup-plan, check-prerequisites tail, finalize-tasks verify, accept, record-analysis`.**
  It does NOT call out:
  - the **~9 distinct planning reads inside `acceptance/__init__.py`** (`_check_needs_clarification`
    6 files, `_missing_artifacts` 6 files, `normalize_feature_encoding`, `_iter_work_packages`)
    — accept is named as ONE site but is really a cluster;
  - the existing **bespoke primary-anchor helpers** (`_primary_anchored_feature_dir`,
    `_resolve_mission_dir_name_primary_anchored`, `_status_read_feature_dir`,
    `_primary_anchor_feature_dir`) that should be **retired in favour of the seam**, not
    left alongside it (else the duplication persists);
  - the record_analysis **double-resolution** (`feature_dir` coord + `write_feature_dir`
    primary, `mission.py:1980`) which is the manual version of what the seam does;
  - `cli/commands/research.py:94` (plan read) and `mission.py:3031` (analyze planning_dir).
- **No FR mandates a literal-ban ratchet** to stop a future command re-reading coord.
  Without it the mission patches today's offenders and the pattern regrows (paula's whole
  reason for existing).

**Sizing verdict: the spec UNDERSIZES the cluster.** It frames 3 driver symptoms + a
catch-all FR-004 that reads as "a handful of commands." The real surface is **~13-15
distinct planning-read sites across 3 modules (`agent/mission.py`, `acceptance/__init__.py`,
`research.py`)**, PLUS **4 bespoke anchor helpers to retire**, PLUS **the record_analysis
double-resolution to collapse**. accept (#2085) alone is ~9 reads, not one. Undersized by
roughly **4-5×** on read-site count, and it is MISSING the consolidation/ratchet that
prevents regrowth.

The FR-006/FR-007/FR-008 lock-the-fix items are correctly scoped (regression guards for
already-fixed seams) and are NOT part of the duplication cluster.

---

## 4. Consolidation recommendation

**Canonical-seam shape (already present — adopt, don't reinvent):**
`resolve_planning_read_dir(repo_root, slug, kind=<MissionArtifactKind>)` is the single
kind-keyed authority. Every gate/verify command that reads a planning artifact must call it
with the artifact's kind and read off the returned dir. No command computes a planning-read
dir from a topology-aware resolver.

**Strangle list (sites to re-point), in priority order:**
1. `agent/mission.py:2224-2225` setup_plan spec/plan → `resolve_planning_read_dir(kind=SPEC|FINALIZED_EXECUTION_PLAN)`. (DRIVER)
2. `acceptance/__init__.py:1179-1187` + `_missing_artifacts:596` + `_check_needs_clarification`
   — resolve each planning file via its kind; keep `status.events.jsonl`/acceptance-matrix on
   the topology-aware (STATUS) route. accept is a *cluster*, plan it as such.
3. `acceptance/__init__.py:402,609-631` `_iter_work_packages` / `normalize_feature_encoding`
   → planning kinds via the seam.
4. `agent/mission.py:1980` record_analysis — collapse the manual coord-then-primary
   double-resolution onto `resolve_planning_read_dir` (the dirty-tree preflight keeps the
   coord placement-ref via the STATUS route — that's correct and matches C-003/C-PLACE-1).
5. **Retire the bespoke helpers** `_primary_anchored_feature_dir`,
   `_resolve_mission_dir_name_primary_anchored`, `_primary_anchor_feature_dir` once the seam
   covers their callers (finalize-tasks/check-prerequisites) — otherwise the parallel
   implementation survives and re-drifts. (Verify the `#11/#1718/#1692` materialized-empty-coord
   intent is preserved by the seam's PRIMARY-partition arm — it is: it goes topology-blind to
   primary, which is exactly what these helpers hand-rolled.)
6. `research.py:94` plan read.

**Literal-ban ratchet (prevent regrowth — ADD an FR):**
An architectural test that flags `<dir> / "spec.md" | "plan.md" | "tasks.md" |
"data-model.md" | "research.md" | "quickstart.md"` (and the `tasks/` dir) when `<dir>` is
sourced from `candidate_feature_dir_for_mission` / `resolve_feature_dir_for_mission` /
`resolve_handle_to_read_path` / `_find_feature_directory` in a gate/verify command — i.e.
"planning read off a topology-aware dir" is the ban. Seed it allowlisting the legitimate
STATUS reads. This is the C6-style ratchet from the 01KVRJ6P playbook; without it FR-004 is
documentation, not a gate.

**KEEP (do not touch — C-003 transients):** status.events.jsonl / status.json /
acceptance-matrix.json / issue-matrix / analysis-report reads stay on the topology-aware
(STATUS/COORD) route; the #1718 create-window and #1848 coord-deleted probes stay. The
record-analysis *placement-ref* (coord) is correct — only its *spec.md read/write* moves.

---

## Verdict

**The spec is UNDERSIZED for the duplication cluster.** It correctly identifies the operation
(planning-read mis-routed to coord) and the canonical seam (`resolve_planning_read_dir`,
C-001), and FR-004 reaches for consolidation — but it (a) enumerates ~5 "commands" where the
real surface is **~13-15 distinct planning-read sites** (accept/#2085 alone is ~9), (b) does
not name the **4 bespoke primary-anchor helpers** that must be retired or the duplication
persists, (c) does not call out the record_analysis **double-resolution** to collapse, and
(d) lacks a **literal-ban ratchet** to stop regrowth — the single highest-leverage item for a
whack-a-field cluster. Estimated undersize: **~4-5× on read-site count**, plus the missing
consolidation+ratchet. Recommend: re-frame FR-002 as a multi-site accept cluster, add an
FR to retire the bespoke helpers onto the seam, and add an FR for the literal-ban ratchet.
