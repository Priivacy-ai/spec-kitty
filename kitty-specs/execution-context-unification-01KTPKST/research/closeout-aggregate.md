# Closeout Aggregate — execution-context-unification-01KTPKST

**Aggregator:** closeout-synthesis · **Date:** 2026-06-10
**Branch:** `fixups/code-engine-stabilization` (12 WPs merged + rebased onto upstream/main, flattened topology)
**Inputs synthesized:** `closeout-reviewer-renata.md` (spec→code fidelity), `closeout-architect-alphonso.md` (architecture / C-005), `closeout-reducer-randy.md` (dead-code / duplication / NFR-005), `closeout-debugger-debby.md` (runtime / behavioral risk), plus `research/findings.md` (F-001..F-009) and `mission-review-report.md`.

---

## 1. Overall verdict — RELEASABLE (ship with follow-ups)

All four independent deep-dives converged on the same release call: **PASS / SHIP-WITH-FOLLOWUPS**. No reviewer found a blocking issue.

- **renata:** PASS (releasable) — 2 minor non-blocking findings + 1 doc nit.
- **alphonso:** PASS — 2 documented-scope deviations, both defensible; no surviving parallel mechanism.
- **randy:** PASS on de-duplication / export hygiene; FAIL only on the *literal* NFR-005 "net subtraction" narrative (a documentation correction, not a code defect).
- **debby:** SHIP-WITH-FOLLOWUPS — structural fix is runtime-sound for BOTH topologies (not flattened-only).

**Release-readiness:** The mission delivers its core thesis — one resolved `MissionExecutionContext` (doc-09 fragment composite) assembled by one builder, status routed through the existing facade, a real git-op guard, and a collapsed daemon reaper. The C-005 binding test (no surviving parallel mechanism) holds across all four lenses. The parity ratchet is fully green (21 passed, 0 xfail), proving CWD-invariance + flattened topology end-to-end, and coordination topology is independently exercised on disk (12 passed in the coord facade/resolver suites). **There is exactly ONE real code change to make (privatize `legacy_record_path`); everything else is follow-up tickets or narrative/retro corrections — none gate the release.**

---

## 2. Consolidated findings (de-duplicated)

### (a) Real code fixes needed — 1

| ID | Summary | Severity | Raised by | Recommended action + owner/effort |
|----|---------|----------|-----------|-----------------------------------|
| **A1** | `legacy_record_path` in `retrospective/writer.py` is importable public surface (no `__all__`) but referenced only intra-module (sites `:80`, `:530`) + one back-compat control test. The one genuine F-009 finding. | LOW (export hygiene; no correctness impact) | **All four** (renata F1, alphonso, randy #1, debby #3) — unanimous | Rename `legacy_record_path` → `_legacy_record_path` (def + 2 call sites) and update the single test import (`tests/retrospective/test_record_committable_1771.py:22,71`). ~5 edits, behavior-preserving, no `__all__` to touch. Owner: randy / F-009 fan-out. Effort: trivial (~10 min). |

### (b) Follow-up tickets to file — 4

| ID | Summary | Severity | Raised by | Recommended action + owner/effort |
|----|---------|----------|-----------|-----------------------------------|
| **B1 (F-006)** | `record-analysis` derives verdict / issue_counts by counting `CRITICAL`/`HIGH`/`MEDIUM`/`LOW` **substrings** in report prose. "no CRITICAL, no HIGH" scores as having those issues → spurious `blocked` → spurious implement-gating. Recurring foot-gun for **every** future mission's analyze step. Worked-around (author prose to dodge counts), not fixed. | **MEDIUM** (operator-facing false-blocked; recurring) | debby (#1, rates it the one item with real operator impact), renata (dogfood ledger) | File upstream tooling ticket: parse the structured findings-table severity column (or accept a structured `--findings` input). Owner: tooling/upstream. Effort: small-medium. **Highest-value follow-up.** |
| **B2 (F-002)** | `safe-commit` directory-args ergonomics gap (worked-around tooling item). Non-mission-FR. | LOW | renata (dogfood ledger) | File upstream tooling follow-up per the dogfood ledger's own recommendation. Owner: tooling/upstream. Effort: small. |
| **B3** | Latent SC-4 drift seam #1: `status/aggregate.py::MissionStatus.load` hand-rolls the coord candidate path itself (`CoordinationWorkspace.worktree_path` + `_compose_mission_dir`) instead of delegating to `candidate_feature_dir_for_mission`. Equivalent today, so they agree — but a **second composition site** that silently diverges if the worktree-naming convention changes. | LOW (no current divergence) | debby (#2) | Follow-up: have `MissionStatus.load` consume `candidate_feature_dir_for_mission` (or a shared compose helper) → truly one composition site. Owner: runtime. Effort: small. |
| **B4** | Latent drift seam #2 (architectural smell, not split-brain): `status_transition._identity_for_request` / `_canonical_primary_feature_dir` re-invoke `resolve_status_surface` / `candidate_feature_dir_for_mission` directly rather than **receiving** the carried `StatusSurfaceFragment` off the resolved context. FR-003 met in *authority* (one resolver) but not in *threading* (fragment recomputed, not passed). No divergence risk — both arms hit the one resolver. | LOW | alphonso (F3) | Follow-up: thread the context/fragment into the transactional emit path so the carried fragment is read, not recomputed. Owner: runtime. Effort: small-medium. Low priority. |

> **Note on B3 vs B4:** these are two *distinct* "not-fully-threaded onto the carried fragment" seams at different sites — B3 is `MissionStatus.load` (coord path composition), B4 is the `status_transition` emit path (status-surface resolution). Both are latent-drift, both LOW, both currently correct because they consume the single authority. They could be folded into one "thread the resolved context everywhere" follow-up.

### (c) Doc / retro / narrative corrections — 3

| ID | Summary | Raised by | Recommended action |
|----|---------|-----------|--------------------|
| **C1 (FR-013)** | FR-013 was stated as "delete 5 dead `coordination/status_service.py` symbols." Reality: **2/5 deleted** (`append_event_log_batch`, `read_wp_lane_actor`); the other 3 (`EventLogWriteTarget`, `StatusContractError`, `StatusReadSource`) are **live internals** post-#1614 rebase (drive `EventLogReadContract`/`EventLogWriteContract`, which have live callers) — correctly NOT deleted, instead **de-exported from `__all__`** (good hygiene). The "5 dead" premise was a stale pre-rebase research assumption. | alphonso (F1), randy, renata (FR-013) — unanimous | Record in retro/issue-matrix: "FR-013 delivered 2/5 deletions; other 3 retained-because-live + de-exported." Re-classify, do NOT re-delete (re-deleting breaks the build). No code change. |
| **C2 (NFR-005)** | NFR-005 framing ("collapses ~500–650 LOC; changed-path LOC trends down") is **empirically false as written**: production diff is **net +1609 LOC** (src `*.py`: +2151 / −542). Targeted duplication WAS removed (~−180: parser −120, status_service −23, orphan_sweep −16, dashboard/lifecycle −12, feature_dir_resolver −10) but dwarfed by genuine NEW doc-09 fragment machinery (~+650: context.py +200, resolution.py +293, _read_path_resolver.py +159). Sound structural trade (duplication → one model), but additive, not subtractive. | **randy** (the sole FAIL-flag, on the *narrative* only) | Correct NFR-005 status in retro/issue-matrix: "targeted duplication removed; net LOC +1609 due to new fragment VOs — NOT net subtraction." Don't leave "net subtraction achieved" standing as met. No code change. |
| **C3 (F-003)** | findings.md marks F-003 🟢 FIXED with acceptance check "`context resolve --action tasks` returns the same `current_branch`/`branch_matches_target` as `setup-plan`." Empirically `context resolve` does NOT surface those keys at all (its schema is `ExecutionContext.to_dict()`, which never carried branch-match fields). The F-003 **root concern** (target_branch single-source) IS fixed and parity holds; only the *stated acceptance-check wording* compares fields one surface intentionally omits. | renata (Finding 2) | Correct the F-003 acceptance-check wording to assert `target_branch` parity (the actual contract), OR optionally add branch-match fields to `context resolve` (follow-up, not blocking). No correctness impact. |

### (d) Confirmed non-issues (false-positives) — 3

| ID | Summary | Raised / adjudicated by | Disposition |
|----|---------|--------------------------|-------------|
| **D1** | `ReapResult` (`sync/owner.py:497`) flagged dead by the scanner. | renata (F3), randy (REFUTE), debby — unanimous | **KEEP PUBLIC.** Live structural return type of `reap_orphan_daemons` (the single spawn-wired reaper); in `__all__` (`:707`); consumed by `tests/sync/test_daemon_singleton_reaper_consolidation.py`. Documented "public-API-consumed-structurally" scanner false-positive class. No action. |
| **D2** | `canonical_executable_scope` (`sync/owner.py:512`) flagged dead. | renata (F3), randy, debby — unanimous | **KEEP** (live identity-scoping helper, called at `owner.py:629` inside the reaper; in `__all__` `:709`). De-export from `__all__` is **optional**, not required (randy #4, debby #5) — no external caller, low value. No action required. |
| **D3** | `_auth_doctor.py:236` BLE001 lint flag. | renata (F3), randy, debby — unanimous | **OUT OF SCOPE.** Pre-existing (commit `38abeebf`, #1297); not a mission-touched file; whole-repo lint scan artifact. Confirm: not this mission's debt. No action. |

---

## 3. Cross-agent agreements vs disagreements

### Where all four converged
- **Release call:** unanimous PASS / ship-with-followups; zero blockers.
- **C-005 (no surviving parallel mechanism):** independently verified by renata, alphonso, randy, and debby across every cluster — read-path resolver, status surface, worktree parser, daemon kill/reaper, liveness probe all collapsed to one. The strongest signal in the whole closeout.
- **`legacy_record_path` privatization (A1):** all four flagged it as the single real code finding.
- **FR-013 = 2/5 not 5/5 (C1):** renata, alphonso, randy all reached the identical conclusion (3 retained-because-live + de-exported); the "5 dead" was a stale pre-#1614 premise. No disagreement.
- **ReapResult / canonical_executable_scope / BLE001 false-positives (D1–D3):** unanimous.

### Divergence (reconciled)
- **NFR-005 "net subtraction":** the only point where verdicts differ in *form*. renata's FR table marks NFR-001/005 ✅ ("net subtraction"); **randy explicitly refutes this as empirically false** (net +1609 LOC) and downgrades NFR-005 to FAIL-on-narrative. **Reconciliation:** randy is correct on the metric — the production diff is additive. This is NOT a code defect or a duplication survivor (the *anti-duplication* thesis is fully delivered, which is what NFR-005 actually protects); it is a **narrative/retro correction (C2)**. renata's ✅ reflects the achieved *structural* goal (duplication collapsed); randy's FAIL reflects the literal LOC *wording*. Both are right about different things — record NFR-005 as "duplication collapsed; net LOC up due to new fragment VOs."
- **SC-7 "exactly one reaper":** alphonso (F2) and randy both note a literal `rg` for reaper-shaped function names finds >1 (discovery/diagnostic wrappers), so SC-7's *wording* isn't satisfiable by name-count — but the load-bearing invariant (one kill path, one spawn-wired reaper, one liveness probe) holds. Not a disagreement; a shared wording-vs-intent note. Optionally tighten SC-7 wording in future to "one kill path + one spawn-wired reaper."
- **F-006 severity:** debby rates it **MEDIUM** (recurring operator-facing false-blocked gate); renata lists it as a routine dogfood-ledger follow-up. **Reconciliation:** adopt debby's MEDIUM — it silently mis-gates every future mission's analyze step, so it is the highest-value follow-up to file.

---

## 4. Prioritized punch-list (for the operator)

> Do NOT open a PR — operator controls that.

**MUST CHANGE (code) — 1 item, do before/with release:**
1. **A1 — Privatize `legacy_record_path` → `_legacy_record_path`** in `src/specify_cli/retrospective/writer.py` (def + 2 intra-module sites + 1 test import). The only real code change. ~5 edits, behavior-preserving, ~10 min. Route through the existing F-009 fan-out.

**FOLLOW-UP TICKETS (file, don't block release) — priority order:**
2. **B1 (F-006) — MEDIUM, highest value.** File upstream: `record-analysis` must parse the structured findings-severity column instead of counting substrings. Recurring false-`blocked` gate affecting every future mission.
3. **B2 (F-002) — LOW.** File upstream tooling follow-up: `safe-commit` directory-args ergonomics.
4. **B3 + B4 — LOW, latent-drift (can fold into one ticket).** Thread the resolved context/carried fragment into (B3) `MissionStatus.load` coord-path composition and (B4) the `status_transition` emit path, so each has exactly one composition/resolution site. Currently correct (both consume the single authority); purely defensive against future convention drift.
5. **Optional / no-action:** de-export `canonical_executable_scope` from `owner.__all__` (D2 — low value); document that deleted-venv daemon orphans rely on PID-death not scope-reaping (debby #4, acceptable trade).

**NARRATIVE / RETRO CORRECTIONS (no code) — land in retro + issue-matrix:**
6. **C1 — FR-013:** record "2/5 deleted; 3 retained-because-live + de-exported." Do NOT re-delete.
7. **C2 — NFR-005:** record "targeted duplication removed; net LOC +1609 (new fragment VOs) — not net subtraction." Don't leave the subtraction claim as satisfied.
8. **C3 — F-003:** correct the acceptance-check wording to assert `target_branch` parity (or optionally add branch-match fields to `context resolve`).

**CONFIRMED NON-ISSUES (no action):**
- D1 `ReapResult` (keep — live public reaper return type).
- D2 `canonical_executable_scope` (keep — live; de-export optional only).
- D3 `_auth_doctor.py:236` BLE001 (pre-existing, out of mission scope).
