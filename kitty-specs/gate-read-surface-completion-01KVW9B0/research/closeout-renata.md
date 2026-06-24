# Closeout Adversarial Review — Reviewer Renata

**Mission:** gate-read-surface-completion-01KVW9B0 (#1716 closeout; closes #2107/#2085/#2102)
**Branch:** feat/gate-read-surface-completion @ HEAD `8cf711428` (src squashed into `7271cd65c`)
**Base:** ea7dc75c5 (upstream/main) · **PR:** #2113 (draft) · 11/11 WPs approved
**Mode:** read-only closeout audit. No PR/status mutation.
**Directives applied:** 001 (boundaries), 024 (locality), 030 (test/typecheck gate), 032 (terminology), 041 (tests-as-scaffold — primary lens).

---

## 1. Per-WP dropped-hunk audit (the headline lens)

Method: `git diff <lane-tip>..HEAD -- <WP owned src>`, then grep for **removals of the WP's own product additions**. Because the final src is squashed into one commit, the lane tips reference a pre-squash topology; the test is "is each lane-tip's approved product change byte-present on HEAD, with no later removal of its additions". Every product symbol grepped live on HEAD.

| WP | Owned src | Approved product change | Fully present on HEAD? | Evidence |
|----|-----------|-------------------------|------------------------|----------|
| WP00 | core/paths.py, core/git_ops.py | meta.json anchor `candidate_*`→`primary_feature_dir_for_mission` | **YES** | `paths.py:624`, `git_ops.py:376`; zero `candidate_feature_dir_for_mission` remaining in either file (bug fully removed) |
| WP01 | mission.py | `_planning_read_dir` chokepoint + `_kind_for_artifact` | **YES** | `mission.py:1136` def; 5 live call sites (1358,1410,2309,2311 + record_analysis seam); lane-b→HEAD shows only additive layering, no removal of WP01 additions |
| WP02 | mission.py (setup_plan) | `spec_read_dir`/`plan_read_dir` via chokepoint | **YES** | `mission.py:2309/2311`; lane-c→HEAD delta is a single comment-line edit (the "RESTORED after lane-d dropped" annotation), no product removal. **The documented WP02 drop (lane-d merge `32eb6df89`) was caught by the FR-010 ratchet and is restored on HEAD.** |
| WP03 | acceptance/__init__.py | `_planning_read_dir` + planning-read split off `status_feature_dir` | **YES** | `acceptance:1241` call; lane-d→HEAD net diff on acceptance = **empty** (byte-identical) |
| WP04 | tasks.py (+ mission.py record_analysis) | `map_requirements` tasks read → WORK_PACKAGE_TASK seam; record_analysis double-resolution collapse | **YES** | `tasks.py:3710`, `mission.py:2047`; lane-e→HEAD net on tasks.py = **empty**; record_analysis re-point present, not removed |
| WP05/06/07/08/09/10 | artifacts.py, ratchet, guards, fixtures, behavioral net | self-bookkeeping allowlist, literal-ban ratchet, guards | **YES** | `is_self_bookkeeping_path` live at `mission.py:918`; ratchet/guards/behavioral all green (65/65) |

**Verdict: NO FURTHER DROPPED HUNK.** WP02 was the only loss; it is restored and ratchet-fenced. Every approved WP product change is byte-present on feat.

---

## 2. Fakeable / vacuous assertions (directive 041)

Spot-checked the highest-risk surfaces — the behavioral net, the ratchet, the AST dedup guards.

- **`test_gate_read_two_surface_behavioral.py` — SOUND.** `test_accept_gate_reads_primary_planning_and_coord_status` drives the **real** pre-existing entry point `collect_feature_summary` (not the seam) and asserts both partitions on one fixture. `test_record_analysis_allowlist_and_g5_dirt` drives `_enforce_analysis_report_write_preflight` with a genuine G-5 "real dirt" arm (`pytest.raises(typer.Exit)` on a stale primary spec.md). `test_write_twin_*` drives `get_feature_target_branch`/`resolve_target_branch`. Production-shaped ULID/mid8/composed-dir fixture (no bare-slug false-green).
- **NIT (not blocking):** `test_two_surface_seam_across_commands` asserts `resolve_planning_read_dir(...)` directly for setup_plan/map_requirements/finalize_tasks rather than their command entry points. The docstring is **honest** that the per-WP suites carry the command-entry red-first repros (verified those suites green). The `test_planning_seam_red_when_routed_to_coord` mutation monkeypatches `is_primary_artifact_kind` (seam internal) rather than the `candidate` regression — but it pairs a real `candidate_feature_dir_for_mission` control (line 296) proving the husk divergence is live. Coverage is adequate; flagged only for transparency.
- **Ratchet `test_gate_read_literal_ban.py` — SOUND, not fakeable.** Content/AST-anchored (function-name + resolver-call), self-tests the scanner against synthetic flag/pass snippets (lines 488-539), and `test_enumerated_surface_set_is_pinned_and_live` (line 423) guards against vacuity by pinning live `@app.command` surfaces. No line-number keys.

**No fakeable/vacuous assertion rises to a blocker.**

---

## 3. Dead code / unwired helpers

All new helpers grepped to live callers:
- `mission.py::_planning_read_dir` → 5 live sites (1358,1410,2309,2311; record_analysis uses the seam directly).
- `acceptance::_planning_read_dir` → `collect_feature_summary:1241`; `_accept_planning_artifact_kinds` consumed by it.
- `is_self_bookkeeping_path` → preflight `mission.py:918`; `_SELF_BOOKKEEPING_FILENAMES/SUFFIXES` consumed at `artifacts.py:302/304`.

**No dead code.**
**NIT:** `record_analysis` (`mission.py:2047`) calls `resolve_planning_read_dir` directly instead of the `_planning_read_dir` wrapper used at the other 5 sites. Functionally identical (same seam, same SPEC kind, same primary dir; ratchet ALLOWs it) but slightly off the "ONE chokepoint" narrative. Cosmetic only.

---

## 4. Regressions (incl. C-002)

- **C-002 (status reads must stay on coord surface): CLEAN.** In `acceptance`, only the 6 planning artifact reads moved to `planning_read_dir`; the STATUS reads — `status_feature_dir / EVENTS_FILENAME` (1234), `_check_lane_gates` (1181), `_collect_snapshot_wps` (1191) — still consume `status_feature_dir`. No status read leaked to primary. The accept gate has an explicit invariant guard (`_planning_read_dir` raises `AcceptanceError` if any planning kind ever crosses the partition).
- **Partition membership verified live:** 8 planning kinds primary=True, 3 status kinds (STATUS_STATE/ACCEPTANCE_MATRIX/ANALYSIS_REPORT) primary=False — exactly as the tests assert. setup_plan's plan.md (FINALIZED_EXECUTION_PLAN) correctly resolves primary.
- **Locality (024): CLEAN.** Net src diff = exactly the 7 declared files, 0 out-of-scope.
- **Gates (030): GREEN.** ruff + mypy clean on all changed src (no suppressions). 65/65 mission tests + 85/85 broader acceptance+mission_runtime regression green.
- **Terminology (032): CLEAN.** "Mission"/read-surface/write-surface canon throughout; no `feature*`-as-domain drift in new code.
- The mission self-reported & fixed 3 arch-gate failures in-mission (surface contract + inventory drift), adjudicated mission-introduced via base-compare. Confirmed consistent.

---

## CLOSEOUT VERDICT: **SHIP**

The implement-review loop missed nothing material. The one real data-loss (WP02 setup_plan drop during lane-d integration) was caught by the FR-010 ratchet and is fully restored on feat. No further dropped hunk, no dead code, no C-002 regression, no fakeable assertion blocker. Gates green, locality clean.

**Non-blocking NITs (optional follow-up, do NOT gate the PR):**
1. `record_analysis` calls the seam directly rather than the `_planning_read_dir` wrapper (cosmetic consistency).
2. `test_two_surface_seam_across_commands` asserts the seam for 3 of 4 commands rather than their entry points (per-WP suites cover the entry-point red-first; documented honestly).
