---
work_package_id: WP01
title: 'Green main: repair the un-masked architectural gate'
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
- NFR-003
- NFR-004
tracker_refs:
- '#2025'
planning_base_branch: feat/governed-state-surface-coherence
merge_target_branch: feat/governed-state-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/governed-state-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/governed-state-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4087631"
history:
- 2026-06-18 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/specify_cli/missions/test_read_path_resolver_validation.py
- tests/architectural/test_no_worktree_name_guess.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any edits, load the implementer profile and binding context. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md` — **FR-011, FR-012, FR-013, NFR-003** and **C-007** (Goal D = WP01, the green base).
2. `kitty-specs/governed-state-surface-coherence-01KVCGQC/research.md` — Goal D table + **D-4** (D1's test file is owned here, not by IC-A) and the env-sensitivity note.
3. The memory lesson behind this WP: a gate-un-mask cannot self-validate — see plan.md "Goal D" framing.

## Objective

The architectural CI shard `integration-tests-core-misc (architectural)` is **RED on `main`** (CI run 27736269610, sha `9f98d89fe`). The canonical-seams mission (#2024) shipped FR-007 (un-mask the gate) which only takes effect *post-merge*, so its own CI couldn't catch the offenders the merge introduced/exposed. **Green it here so WP02–WP05 land on a green base.** This WP is **guard-mechanism only** — do NOT change what any guard asserts; only fix the offending markers/baselines and remove a test that never belonged on `main`.

> ⚠️ **Env-sensitivity (NFR-003):** some of these failures manifest only under **CI conditions** (Python 3.12 + installed package + `-n auto --dist loadfile`) and pass on local Python 3.11 editable. **Local green is necessary but NOT sufficient.** The DoD requires the shard green on CI.

## Subtasks

### T001 — D1: fix markers on `test_read_path_resolver_validation.py`

**Purpose:** the file (added by canonical-seams) invokes `git` via `subprocess` but carries `pytest.mark.fast` and lacks `git_repo` — failing `test_pytest_marker_correctness` Rule 1 (git_repo presence) and Rule 2 (fast excludes subprocess).

**Steps:**
1. Open `tests/specify_cli/missions/test_read_path_resolver_validation.py`; find the `pytestmark = [...]` list.
2. Remove `pytest.mark.fast`; add `pytest.mark.git_repo`. Choose the correct category marker (`integration`) since it spawns git subprocesses. Final e.g. `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`.
3. Confirm the file still collects and runs: `pytest tests/specify_cli/missions/test_read_path_resolver_validation.py -q`.

**Validation:**
- `pytest tests/architectural/test_pytest_marker_correctness.py::test_subprocess_git_users_must_carry_git_repo_marker tests/architectural/test_pytest_marker_correctness.py::test_fast_marker_must_not_apply_to_subprocess_users -q` → green.

### T002 — D2: remove the mission-diff-scoped test

**Purpose:** `tests/architectural/test_no_worktree_name_guess.py::test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils` pins the **canonical-seams one-time diff** (it asserts only `status/aggregate.py` changed under `status/` and `task_utils/` is untouched). That is a *mission-scoped* assertion, not a durable invariant — it has no business on `main`, where any later `status/` work trips it.

**Steps:**
1. Read the test body and its docstring to confirm it is the NFR-001-consolidation diff guard (references `status/emit.py`, `status/lifecycle_events.py`, etc.).
2. **Remove the test function** (and any now-unused helper/fixture exclusive to it). Do NOT remove the durable name-guess tests in the same file (`test_no_worktree_or_branch_name_guess_outside_seam`, the allow-list/baseline tests) — those stay.
3. If the test references a module-level constant used only by it, remove that too; otherwise leave shared machinery intact.

**Validation:**
- `pytest tests/architectural/test_no_worktree_name_guess.py -q` no longer collects `test_nfr001_consolidation_does_not_bleed_into_status_or_task_utils`.
- **Durable-test survival (F10):** `pytest tests/architectural/test_no_worktree_name_guess.py --collect-only -q` count drops by **exactly** the removed test(s) — no more. The durable tests (`test_no_worktree_or_branch_name_guess_outside_seam`, the allow-list/baseline tests) still collect. This guards against silent over-removal.

### T003 — D3: reconcile the re-keyed ratchet baselines to the current main tree

**Purpose:** the FR-008-era re-keyed (AST/qualname + token-line composite) ratchet allow-lists/baselines drifted against the exact `main` tree, so `test_allow_list_entries_are_real_and_benign`, `test_name_compose_offenders_match_pinned_baseline`, and `test_shortid_allow_list_entries_are_real` go stale/red under CI.

**Steps:**
1. Run each failing test and read its assertion message — they tell you which composite keys are stale (no longer match a live offender) or which offenders are unaccounted.
2. For **stale allow-list entries** (key no longer matches a live site): re-verify the cited site, then update the composite key to the current qualname/token-line, or drop the entry if the offender is gone. Do NOT blindly delete — confirm the site.
3. For **unaccounted name-compose offenders** (a real `{... mission_slug}`/name-compose outside the seam): these are REAL — route through the canonical seam if trivially in-scope, OR add a justified allow-list entry with a one-line rationale proving it is not a wrong-compose. Prefer the smallest correct change; do NOT mass-add entries.
4. **DO NOT touch** `test_no_write_side_rederivation.py::_ALLOW_LIST` line `:295` (status_transition.py) — that is the deliberate #1716-blocked pin (C-007 of the canonical-seams mission); it is out of scope here.

> ⚠️ **Anti-fake teeth (squad-renata F3):** "green" is trivially achievable by deleting drifted entries / loosening the baseline. That is NOT reconciliation. For EACH changed allow-list/baseline entry, the handoff note MUST cite the live source site (`file:line` + the offending token) the new composite key matches — the reviewer greps that site to confirm it exists and is benign/in-seam. A net **reduction** in entries MUST be accompanied by proof (git log / grep showing the site is genuinely gone), not merely de-listed.

**Validation:**
- All three ratchet tests green locally AND (DoD) under CI conditions.
- Handoff note carries the per-entry `file:line` justification for every changed/removed entry (F3).

### T004 — verify GREEN under real CI conditions (NFR-003)

**Purpose:** local py3.11 editable is not representative; the gate runs py3.12 + installed + parallel. (This WP exists *because* a gate un-mask can't self-validate — do not let it self-certify on local.)

**Steps:**
1. Run the architectural shard the way CI does: `pytest tests/adversarial tests/architectural tests/architecture tests/lint -m 'not windows_ci and (git_repo or integration or architectural)' -q -n auto --dist loadfile`.
2. **A py3.12 interpreter IS available** at `python3.12` (pyenv shim) — run the same command under `python3.12 -m pytest …` to approximate CI's interpreter locally. This is a REQUIRED step (not conditional).
3. **The binding verification is the CI run** (squad-renata F4): T004 is NOT complete until a CI run of `integration-tests-core-misc (architectural)` on the **pushed** WP01 branch is observed GREEN. A local run (any interpreter) is necessary but explicitly INSUFFICIENT. Record the local command output AND the CI run id/URL + `conclusion=success` in the handoff.

**Validation:**
- Local `python3.12 -m pytest …` green; AND a real CI run id for the architectural shard shows `conclusion=success`. The DoD "CI-condition verified" checkbox may ONLY be checked against a real CI run id — never a local-only run.

## Branch Strategy

Planning branch: `feat/governed-state-surface-coherence`. Final merge target: `main` (via PR). Execution worktrees are allocated per computed lane from `lanes.json`; this WP is the lane root (no dependencies).

## Definition of Done

- [ ] T001–T004 complete; the architectural shard is GREEN — verified by a **real CI run id** (`conclusion=success`), not a local-only run (NFR-003, F4).
- [ ] The marker fix uses `integration` + `git_repo` (not `fast`).
- [ ] The mission-diff-scoped `test_nfr001_…` is removed; durable tests retained (collect-count drops by exactly the removed test — F10).
- [ ] Ratchet baselines reconciled with per-entry `file:line` justification; removals proven; `:295` untouched (F3).
- [ ] ruff + mypy clean on touched files; zero new suppressions (NFR-004).
- [ ] Issue-matrix row for #2025 set to a verdict; #2025 carries a tracker comment naming mission `01KVCGQC` (SC-007).
- [ ] Handoff note records the CI run id + GREEN conclusion + per-entry ratchet justifications.

## Reviewer Guidance

Confirm: no guard's *assertion* changed (only markers/baselines/test-removal); the removed test was genuinely mission-diff-scoped (not a durable invariant); ratchet entries each have a rationale and `:295` is untouched; and the GREEN evidence is from CI conditions, not just local py3.11.

## Activity Log

- 2026-06-18T05:49:56Z – claude:sonnet:python-pedro:implementer – shell_pid=4053594 – Assigned agent via action command
- 2026-06-18T06:10:16Z – claude:sonnet:python-pedro:implementer – shell_pid=4053594 – Markers fixed (integration+git_repo); test_nfr001 removed (durable tests retained, collect-count 12->11 verified); ratchets reconciled by making composite_key interpreter-stable (PEP701 f-string token drift, NFR-003) — no baseline entry added/removed/edited, live sites recovery.py:135/vcs detection.py:161/lifecycle_sync.py:135/executor.py:469; :295 untouched; local py3.12 architectural shard GREEN (461 passed) — CI run id pending PR push.
- 2026-06-18T06:11:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=4087631 – Started review via action command
- 2026-06-18T06:19:01Z – user – shell_pid=4087631 – Review passed (reviewer-renata). T001: marker fixed to integration+git_repo — file genuinely spawns git subprocesses (git init/config); fast correctly removed (Rule 2). T002: exactly one test removed (test_nfr001_…, a cross-mission diff guard pinning mission/mission-identity-seam-and-1908-panel — never a durable invariant); collect-count 12->11, zero durable tests lost; helpers + import subprocess removed with no dangling refs. T003 ratchet-key mechanism PRESERVES DETECTION (verified): offender flagging is the untouched AST scanner; composite key only governs exemption lookup. Keys byte-identical on py3.11 AND py3.12 for all cited sites (recovery.py:135, vcs/detection.py:161, lifecycle_sync.py:135, doctor.py:3074/3166, executor.py:469). Confirmed real CI break: pre-fix py3.12 leaked PEP701 interpolation tokens ('pattern = { mission_slug }') vs committed py3.11 baseline ('pattern ='); fix restores py3.11 form = restoration of pinned semantics, NOT a loosening. No baseline entry added/removed/edited; :295 pin untouched. Ratchet teeth intact (drift-proof, new-offender-flagged-RED, distinct-keys self-tests all pass). ruff+mypy clean on all 3 touched files, zero new suppressions. py3.12-failure disposition: PRE-EXISTING + OUT-OF-SCOPE — test_pytest_marker_convention::test_support_helper_tree_is_exempt is UNTOUCHED by WP01, fails identically on py3.11 (not interpreter-specific), path-sensitive: passes from main checkout, fails from .worktrees/ because _iter_candidate_test_files() skips path parts starting with '.' (the .worktrees ancestor zeroes the candidate set, tripping assert-candidates). CI runs on a normal checkout so it passes there. Scope: _ratchet_keys.py edit outside owned_files (non-blocking ACTIVE_WP_SCOPE_VIOLATION) ACCEPTED — only correct seam (re-pinning to py3.12 would break py3.11). CONDITION (orchestrator action, not lane): NFR-003 binding CI run id for integration-tests-core-misc(architectural) pending mission-PR push.
