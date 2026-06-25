# Pre-PLAN Adversarial Research — Architect Alphonso

**Lens:** scope coherence + design soundness
**Spec:** `gate-read-surface-completion-01KVW9B0/spec.md` (#1716 residual-cluster closeout, 8 FRs)
**Repo:** `feat/gate-read-surface-completion` @ `42b956e40`
**Directives applied:** 001 (architectural integrity / boundaries), 003 (decision documentation), 031 (context-aware design / read-authority partition), 032 (conceptual alignment on kind/topology/seam), 041 (tests-as-scaffold — FR-008 lens).

---

## VERDICT

**COHERENT-AS-IS, with one design correction and two scope cautions.**

The binding theme — *"planning-lifecycle GATE commands must read planning artifacts from the per-kind PRIMARY partition, not the topology-routed coord surface"* — is real and load-bearing for FR-001/002/003/004. FR-006/007/008 are a **defensibly-grouped "lock the mid8/identity fix" sub-cluster**, not arbitrary bolt-ons, but they are a *different* engineering activity (regression-guarding already-landed fixes) and should be an explicitly-fenced second lane in the plan. There is a **design gap in FR-003's framing** (see §2) and a **completeness gap in FR-004's enumeration** (see §3). All four constraints are sound; C-001/C-002 need one sharpening.

---

## 1. ONE mission or grab-bag?

**Spine (FR-001/002/004, #2107/#2085) is genuinely one mission.** The bug is a single class with a single root cause, live-reproduced and evidenced:

- `setup_plan` (`cli/commands/agent/mission.py:2203`) resolves `feature_dir` via `_find_feature_directory` → `resolve_handle_to_read_path(require_exists=True)` (`mission.py:1254`), which routes to the **coord** worktree for coord-topology missions, then reads `feature_dir / "spec.md"` (`mission.py:2224`) and emits `SPEC_FILE_MISSING` (`mission.py:2229`) — but post-#2106 `spec.md` (SPEC kind) is a **PRIMARY-partition** artifact (`mission_runtime/artifacts.py:87`). Confirmed root cause.
- Accept gate: `status_feature_dir = _status_read_feature_dir(...)` (`acceptance/__init__.py:1114`) → `resolve_handle_to_read_path` (coord). Then the gate reads `status_feature_dir / "spec.md" | "plan.md" | tasks.md | research.md | data-model.md` (`acceptance/__init__.py:1179-1184`) and `_missing_artifacts(status_feature_dir)` (`:1187`, reads spec/plan/tasks at `:597`). **Every one of those is a PRIMARY-partition kind read off the coord surface** — the exact same misresolution as setup-plan. So FR-002 is the same bug at a second call site, not a separate concern.

**FR-003 (#2102, record-analysis allowlist)** is *adjacent but a different axis* — it's a dirty-tree **write-preflight** classification, not a planning-**read** misresolution (see §2). It belongs (record-analysis is a gate command and the partition is the same authority) but the FR text conflates two things.

**FR-006/007/008 are a coherent sub-cluster, but not the spine.** They are "write a red-first regression guard for an already-landed fix + re-pin a drifted fixture." Evidence the fixes already exist:
- FR-006: `runtime/next/runtime_bridge.py:223-231` — refuses empty `_mid8` on coord-routing missions (the `DecisionGitLogUnavailable` raise is present).
- FR-007: `ownership/validation.py:~161` `validate_no_overlap(..., dependencies=...)` already exempts dependency-ordered pairs (`_walk` reachability present).
- FR-008: `cli/commands/mission_type.py:632` `_read_mission_mid8` reads `load_meta(meta_path.parent...)` — the product code is correct; the test `tests/specify_cli/test_mid8_direct_routing.py:108` writes `full.json/explicit.json/bare.json` which the reader IGNORES (it reads `<dir>/meta.json`), so 2 of 3 asserts are RED purely from fixture drift.

**Recommendation:** Keep as ONE mission, but the plan MUST fence two lanes: **Lane A (spine)** FR-001/002/003/004/005 — the read-seam re-point; **Lane B (lock-the-fix)** FR-006/007/008 — pure test additions + one fixture re-pin, *no product change*. They share the #1716/#1868 identity theme but have disjoint files and disjoint risk profiles. Do not let Lane B's "trivial" framing leak into Lane A's WP sizing.

---

## 2. Design soundness of the spine (FR-001/002/004)

**The chosen design — re-point gate reads onto `resolve_planning_read_dir(kind=…)` — is CORRECT and the deeper authority problem the spec worries about is ALREADY SOLVED.** `_read_path_resolver.py:1244-1308`:

```
if is_primary_artifact_kind(kind):        # SPEC/PLAN/TASKS/WP/DATA_MODEL/RESEARCH/CHECKLIST/LANE_STATE/PRIMARY_METADATA
    return primary_feature_dir_for_mission(...)   # topology-blind PRIMARY
return candidate_feature_dir_for_mission(...)     # STATUS-partition: coord-aware, KEEP transients
```

The read seam already carries the **same kind partition the write side got** (`_PRIMARY_ARTIFACT_KINDS`, `artifacts.py:85`), queried through the public `is_primary_artifact_kind` predicate (no parallel classifier — C-006 honored). So there is **no deeper read-authority gap**: the resolver is sufficient; the spine is purely *adoption* (the gate commands never called it). This is the right answer per Directive 031 — the per-kind partition IS the bounded-context translation layer between "planning lives on primary" and "status lives on coord."

**API/directionality is sound.** `kind` is an internal compile-time enum threaded by the caller that knows which artifact it is reading; NFR-003 (no new CLI surface) holds. The `_ARTIFACT_TYPE_TO_KIND` map already exists (`mission.py:1106`).

**DESIGN CORRECTION (FR-003):** `ANALYSIS_REPORT` is a **COORD-partition** kind (`artifacts.py:103,109`), NOT primary. So FR-003 is NOT a "read spec.md from primary" fix — record-analysis already writes the report to primary via a `#1989` carve-out (`mission.py:1970-1976` uses `primary_feature_dir_for_mission` for the write while keeping `feature_dir`/`placement_ref` coord-aware for the dirty-tree preflight at `:1951-1957`). FR-003 is really about the **dirty-tree allowlist** correctly classifying bookkeeping residue against the `placement_ref`. The plan must NOT model FR-003 as "route record-analysis reads through `resolve_planning_read_dir(kind=SPEC)`" — that would be wrong (the report's own kind is coord). Re-state FR-003 as: *the allowlist consults the kind partition to decide commit-home, and spec-kitty's own meta/provenance files are residue.* This is a Directive 032 conceptual-alignment flag — the FR's domain terminology ("consistent with the kind partition") is right but its placement under the same "consult `resolve_planning_read_dir`" umbrella as FR-001 is misleading.

---

## 3. Completeness of FR-004 ("ALL gate commands consult the seam")

**FR-004's enumeration is real but the single-chokepoint opportunity is under-exploited.** The enumerated commands (`setup-plan`, `check-prerequisites` tail, `finalize-tasks` verify, `accept`, `record-analysis`) almost all funnel through **`_find_feature_directory`** (`mission.py:1211`): setup_plan (`:2203`), record_analysis (`:1928`), accept-adjacent (`:1859`, `:2931`). That helper returns ONE coord-aware dir, and callers then do `dir / "spec.md"`.

**The clean design is NOT to edit each `dir / "spec.md"` site.** It is to give the gate commands a **kind-aware artifact-path helper** — e.g. `planning_artifact_path(repo_root, slug, kind)` that internally calls `resolve_planning_read_dir(kind=…)` — and have `_find_feature_directory` remain the *identity/existence* resolver while the **artifact read** goes through the per-kind helper. Otherwise the plan risks N per-call-site edits (each `status_feature_dir / "spec.md"` at `acceptance/__init__.py:1179-1184,597`) that re-introduce the kind-blindness the next time someone adds a read. **Recommend the plan name an explicit chokepoint** (one helper, all planning reads through it) and add an architectural ratchet test that no gate command composes `<feature_dir>/spec.md|plan.md|tasks.md` directly. Without that, FR-004's "no command may reconstruct a planning-read path via topology routing" is unenforceable and will silently regress (this is exactly the kind of drift Directive 001 guards).

**One under-specified site:** `acceptance/__init__.py:1176` reads `status_feature_dir / TASKS_FILE` for `_find_unchecked_tasks` and `:597` reads tasks.md in `_missing_artifacts` — TASKS_INDEX is PRIMARY-partition, so both must move. The spec's FR-002 says "each artifact from its kind's canonical surface" which is correct in spirit, but the WP must enumerate that **STATUS_STATE reads (events.jsonl at `:1174`, `:710`) STAY coord** while spec/plan/tasks/research/data-model move to primary. The accept function mixes both partitions on one `status_feature_dir` variable — splitting it cleanly is the WP's core work and the highest-risk edit in the mission.

---

## 4. Constraints check

- **C-001 (build on #2106, no parallel resolver):** CORRECT and already satisfied by design — `resolve_planning_read_dir` exists and is the only seam. Sharpen: add "gate commands ADOPT the existing seam; they MUST NOT add a kind argument to `_find_feature_directory` or branch on topology themselves."
- **C-002 (unification not parity):** CORRECT. The coord planning-read route is removed, not preserved behind a flag. Aligns with the standing "unification not parity" memory. One caution: C-002 says "no fallback to the old route" — but the accept gate's `_status_read_feature_dir` lenient `status_dir if status_dir.exists() else feature_dir` fallback (`acceptance/__init__.py:749-750`) is a STATUS-read leniency that must be PRESERVED for status kinds. C-002 should scope its "no fallback" to planning kinds only, else it collides with the legitimate status leniency.
- **C-003 (preserve KEEP transients #1718 create-window, #1848 coord-deleted):** CORRECT and structurally safe — those transients live on the STATUS-partition arm (`candidate_feature_dir_for_mission`), which planning-kind reads no longer touch. The resolver docstring (`:1273-1276`) confirms the transients ride the STATUS arm. Good.
- **C-004 (forward-only, no migration):** Sound; no concern.

**Missing constraint:** there is no constraint forbidding a gate command from reading a planning artifact via `resolve_handle_to_read_path` / `_find_feature_directory` and then joining `/spec.md`. Add **C-005: planning-artifact file paths are obtained ONLY through the kind-aware helper; direct `<dir>/<planning-file>` joins in gate commands are prohibited (architectural ratchet).** This is what makes FR-004 enforceable (§3).

---

## Risk flags for the plan

1. **Highest-risk edit:** splitting `acceptance/__init__.py`'s single `status_feature_dir` into per-partition reads (`:1174-1187`, `:597`) without breaking the STATUS_STATE/events read. Needs a coord-topology + flattened-topology test matrix per NFR-001/004.
2. **FR-003 mis-modeling** (§2) — do not route the analysis-report read through a SPEC-kind seam.
3. **FR-004 enforceability** (§3) — demand a chokepoint helper + ratchet, not per-site edits.
4. **Lane B framing** — FR-006/007/008 are test-only; size them small but DO require the red-first proof (revert-the-fix → test goes RED) per NFR-002, especially FR-008 where the product is already correct and only the fixture drifted (Directive 041 — re-pin to a production-shaped `meta.json` via the canonical factory, do not soften the assertion).
