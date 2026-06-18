---
work_package_id: WP04
title: Charter freshness residue downgrade + unlink consolidation
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-002
tracker_refs:
- '#2009'
planning_base_branch: feat/governed-state-surface-coherence
merge_target_branch: feat/governed-state-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/governed-state-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/governed-state-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4177659"
history:
- 2026-06-18 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/freshness/
create_intent:
- tests/specify_cli/charter_runtime/test_freshness_residue.py
- tests/specify_cli/charter/test_graph_unlink_helper.py
- src/charter/synthesizer/graph_residue.py
- tests/specify_cli/charter/test_freshness_hash_unification.py
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/freshness/computer.py
- src/specify_cli/cli/commands/charter/_fresh_doctrine.py
- src/charter/synthesizer/project_drg.py
- src/charter/synthesizer/graph_residue.py
- src/charter/hasher.py
- tests/specify_cli/charter_freshness/test_computer.py
- tests/specify_cli/charter_runtime/test_freshness_residue.py
- tests/specify_cli/charter/test_graph_unlink_helper.py
- tests/specify_cli/charter/test_freshness_hash_unification.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and binding context. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md` — **FR-006, FR-007, FR-009, NFR-002, C-003**.
2. `kitty-specs/governed-state-surface-coherence-01KVCGQC/research.md` — Goal B table (C2-f structural + the two unlink sites) + **decision D-2**.

## Objective

Make the charter-freshness false-positive **structurally unreachable**, and collapse a duplicated producer.

1. **FR-006 (C2-f, structural):** `computer.py:345-357` returns a terminal `invalid` sub-state when `built_in_only=true` ∧ a project `graph.yaml` is present. `runner.py:60` `_PASS_STATES` excludes `invalid`, so preflight/implement is **blocked** — and it self-heals only reactively on the next `synthesize` (auto-refresh skips dirty trees). The manifest is the **declared authority** (#083): a `graph.yaml` it disowns is *residue*, not a contradiction. So the reader should authoritatively report `built_in_only` and emit a **non-blocking "stale graph residue" diagnostic** instead of the blocking `invalid`. This makes the blocking branch unreachable for the residue condition (structural, not reactive — do NOT "fix" by auto-running synthesize).
2. **FR-007:** the two parallel `graph.yaml` unlink sites — `src/charter/synthesizer/project_drg.py::apply_post_condition` (:343) and `cli/commands/charter/_fresh_doctrine.py` (:119) — consolidate into ONE shared helper any `built_in_only`-writer calls.
3. **FR-009 (C2-e):** `charter sync --json` reportedly returns `noop`-despite-stale (then `--force` works). **Reproduce LIVE first** (live-evidence rule — NFR-002). If reproduced, fix the stored-hash drift. If NOT reproducible, record a `verified-non-reproducible` verdict with captured evidence — do NOT change code on a hunch.
4. **FR-008b (C2-d hash pin, moved here from WP03):** pin that `sync`/`status`/`computer` agree on the content hash via the one `charter.hasher.hash_content` path — co-located here because the C2-e fix (FR-009) targets the same `is_stale`/hash seam. Test the REAL surfaces, not the primitive (T035).

## Subtasks

### T030 — Failing-first test: residue blocks preflight today (TDD, FR-006)

**Steps:**
1. Create `tests/specify_cli/charter_runtime/test_freshness_residue.py`.
2. Build a topology-true fixture: a synthesis manifest declaring `built_in_only=true` AND a stray `.kittify/doctrine/graph.yaml` present.
3. Assert current behavior: `compute_freshness(.).synthesized_drg.state == "invalid"` and `run_charter_preflight(., auto_refresh=False).passed is False` — RED (this is the bug).

**Validation:** test RED, demonstrating the blocking `invalid`.

### T031 — Downgrade to read-time residue (FR-006) — incl. existing-test update + genuine-`invalid` guard

> ⚠️ **BLOCKER (squad-pedro+debbie):** existing tests in `tests/specify_cli/charter_freshness/test_computer.py` assert `state=="invalid"` for EXACTLY the residue case you are downgrading — `test_synthesized_drg_invalid_on_conflict_state` (~:238) and the `[invalid]` parametrization of `test_states_are_among_documented_vocabulary` (~:309). They go RED after the fix. This file is now in your `owned_files` — you MUST update them as part of the change (not an out-of-scope edit).

**Steps:**
1. In `computer.py` (the `_compute_synthesized_drg` region ~:324-357), replace the terminal `invalid` return for the `built_in_only ∧ graph_exists` branch with a `built_in_only` sub-state that ALSO carries a non-blocking diagnostic (e.g. a `detail`/`diagnostic` field "stale graph residue: graph.yaml present but manifest declares built_in_only; ignored").
2. `_PASS_STATES` (`runner.py:60`) already includes `built_in_only` — reporting `built_in_only` is sufficient; **do NOT add `invalid` to `_PASS_STATES`**.
3. **Preserve the genuine-`invalid` path.** A genuine inconsistency NOT covered by a `built_in_only` manifest declaration must STILL return `invalid`. Note the OTHER live `invalid` producer at `computer.py:276` (`_compute_charter_source`: "charter.md exists but cannot be hashed") — that one is out of scope and MUST stay `invalid`. Scope the downgrade to the `_compute_synthesized_drg` residue branch ONLY.
4. **Update the existing tests** (`test_computer.py`): change `test_synthesized_drg_invalid_on_conflict_state` and the `[invalid]` vocabulary parametrization to reflect the new residue contract (manifest-disowned `built_in_only ∧ graph` → `built_in_only` + residue diagnostic). If the `invalid` vocabulary smoke-entry no longer has a reachable `_compute_synthesized_drg` producer, re-point it at a genuine producer (e.g. the `:276` charter-unhashable case) rather than deleting the vocabulary coverage.
5. **Complexity:** the ≤15 budget is the **ruff `C901` (mccabe)** local gate — which currently PASSES on `computer.py`; swapping a `return invalid` for `return built_in_only(detail=…)` does not add branches, so no refactor is forced. Sonar `S3776=22` on `_compute_synthesized_drg` is a **separate Sonar-UI hotspot** — call it out in the PR body (like WP05's S2083), do NOT chase a refactor to satisfy it unless ruff C901 actually trips.

**Validation:**
- T030 flips to PASS — preflight passes reporting `built_in_only` + the residue diagnostic.
- **Genuine-`invalid` guard (F5):** add/keep a test asserting a genuine inconsistency (e.g. the `:276` charter-unhashable case, or a synthesized-DRG inconsistency with NO `built_in_only` declaration) STILL returns `invalid` and STILL fails `_PASS_STATES`. This must be GREEN after the fix (guards against over-downgrading).
- `test_computer.py` updated tests green; ruff C901 still passes.

### T032 — One shared unlink helper (FR-007)

> ⚠️ **Helper home is MANDATED, not discretionary (squad-paula+debbie):** put `unlink_stale_project_graph(doctrine_dir: Path) -> None` in a NEW small module **`src/charter/synthesizer/graph_residue.py`** (declared in this WP's `owned_files`/`create_intent`). This is the only import-safe home: `_fresh_doctrine.py` already does deferred `from charter.synthesizer.* import …` (no new cycle), and `project_drg.py` is in the same package. **NEVER** place it in `specify_cli` — `src/charter/synthesizer` already has a deferred `import specify_cli`, so a back-import would tighten toward a cycle.

**Steps:**
1. Create `src/charter/synthesizer/graph_residue.py` with `unlink_stale_project_graph(doctrine_dir)` doing the plain `(doctrine_dir / "graph.yaml").unlink(missing_ok=True)`. Reuse the existing `_GRAPH_FILENAME` constant from `project_drg.py` (import it) — do **NOT** mint a third copy (it is already duplicated in `project_drg.py:47` and `write_pipeline.py:61`).
2. Replace ONLY the bare unlink expression at `project_drg.py:343` and `_fresh_doctrine.py:119` with a call to the helper. **The two sites are asymmetric:** `project_drg.py:343` sits INSIDE `apply_post_condition`'s guarded `write_text(tmp) → unlink(graph) → guard.replace(tmp, manifest)` atomic sequence — the helper call MUST stay **in place** within that sequence (replace only the `.unlink` line, keep the `graph_path` local and the `guard.replace` ordering exactly). `_fresh_doctrine.py:119` is a standalone unlink.
3. Add `tests/specify_cli/charter/test_graph_unlink_helper.py` exercising the helper (idempotent, missing-ok).

**Validation:** both sites call the one helper; `apply_post_condition`'s atomic `unlink→guard.replace` ordering is UNCHANGED (hard check, not a footnote); no third `_GRAPH_FILENAME` copy; existing synthesizer/fresh-doctrine tests still green.

### T035 — Pin C2-d: hash unification, testing the REAL surfaces (FR-008b, moved from WP03; F1)

> ⚠️ **Anti-tautology (squad-renata F1):** the pin must exercise the ACTUAL surface functions, NOT call `charter.hasher.hash_content` N times (that is `assert x == x`, green-from-start, proves nothing). The regression risk it guards is a surface *stopping* routing through `hash_content` (e.g. a reintroduced local `hashlib.sha256`).

**Steps:**
1. Create `tests/specify_cli/charter/test_freshness_hash_unification.py`.
2. Build a real charter bundle. Invoke the REAL surface functions — `_collect_charter_sync_status`/`sync` via `is_stale`, and `computer._charter_hash_of` — and assert the emitted `current_hash`/`stored_hash` values are byte-equal AND carry the `sha256:` prefix.
3. **Negative guard:** mutate the bundle content and assert all three surfaces' hashes change identically (proves they read the same content via the same normalization).
4. This test imports `computer.py` (owned here) and `sync.py`/`_status_collectors.py` (read-only — no edits).

**Validation:** test green; it FAILS if any surface stops routing through `hash_content`. Reject if it only calls `hash_content` directly (tautological).

### T033 — Live-repro C2-e; fix-or-document (FR-009, NFR-002)

**Steps:**
1. Attempt a live repro: construct a stale charter bundle where `charter sync --json` reports `noop` (`is_stale` False) while freshness/status independently report stale — i.e. a stored-hash drift between the bundle `metadata.yaml` `charter_hash` and `compute_freshness`'s view.
2. If REPRODUCED: fix so `sync`'s staleness decision agrees with the unified `hash_content` path (couple to WP03's hash-unification pin); add a regression test.
3. If NOT reproducible after a genuine attempt: record a `verified-non-reproducible` verdict — but it MUST carry hard evidence (squad-renata F2), not a bare "could not reproduce": (a) the exact fixture construction steps (the stored-hash-drift bundle); (b) the actual captured `charter sync --json` output (pasted JSON showing `noop`); (c) the independent `compute_freshness`/`status` output for the same bundle showing they agree (no drift); (d) a one-line structural argument why the drift cannot occur given the unified `hash_content` path (T035). A prose-only "could not reproduce" is a REJECT.

**Validation:** either a regression test for the fixed drift, OR a `verified-non-reproducible` verdict with captured command output (a–d above).

### T034 — Quality gate

**Steps:**
1. Run the preflight/freshness/synthesizer test suites.
2. `ruff` + `mypy` on `computer.py`, `_fresh_doctrine.py`, `project_drg.py`, and the new helper module; complexity ≤15; zero new suppressions.

**Validation:** all green; ruff+mypy clean.

## Branch Strategy

Planning branch `feat/governed-state-surface-coherence`; merge target `main` (PR). Depends on **WP01** (green CI base only — no code interaction). Independent of WP02/WP03/WP05 (disjoint owned_files). Worktree per `lanes.json`.

## Definition of Done

- [ ] Residue (`built_in_only ∧ graph.yaml`) reports `built_in_only` + non-blocking diagnostic; preflight PASSES (SC-003); the blocking `invalid` branch is unreachable for this case (structural, not reactive).
- [ ] **Existing `test_computer.py` `invalid` assertions updated** to the residue contract (blocker fix); the `invalid` vocabulary stays covered by a genuine producer.
- [ ] **Genuine `invalid` guard (F5):** a real inconsistency (e.g. `computer.py:276` charter-unhashable) STILL returns `invalid` and fails `_PASS_STATES` — GREEN after the fix.
- [ ] ONE `unlink_stale_project_graph` helper in `src/charter/synthesizer/graph_residue.py`; both former sites call it; `apply_post_condition` atomic `unlink→guard.replace` ordering preserved; no third `_GRAPH_FILENAME` (FR-007).
- [ ] **C2-d hash pin (T035)** tests the REAL surfaces (not `hash_content` directly) with a negative guard (FR-008b, F1).
- [ ] C2-e reproduced+fixed OR `verified-non-reproducible` with captured `sync --json`+freshness output (FR-009, NFR-002, F2).
- [ ] complexity ≤15 = ruff C901 (passes); S3776 on `_compute_synthesized_drg` noted as a PR-body Sonar hotspot, not refactored.
- [ ] ruff + mypy clean, zero new suppressions.
- [ ] **#2009 issue-matrix row set to `in-mission`** (terminal only on the later-merged of WP03/WP04 — squad-paula); #2009 carries a tracker comment naming mission `01KVCGQC` (SC-007).

## Reviewer Guidance

Confirm: the residue downgrade is at the READER (manifest-authority), NOT a "self-heal" that runs synthesize (C-003 — structural, not reactive); `_PASS_STATES` was NOT widened to include `invalid`; the genuine-`invalid` guard test is present and green (the downgrade didn't over-fire); the unlink helper lives in `src/charter/synthesizer/graph_residue.py` (never `specify_cli`) and `apply_post_condition`'s atomic ordering is byte-unchanged; the hash pin (T035) exercises real surface functions with a mutate-and-diverge negative guard (reject if it only calls `hash_content`); C2-e carries captured command output if non-reproducible (reject prose-only). Grep for any new `sync`/mutator call in the status/freshness read path — none allowed.

## Activity Log

- 2026-06-18T06:20:41Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – Assigned agent via action command
- 2026-06-18T06:45:09Z – claude:sonnet:python-pedro:implementer – shell_pid=4098966 – FR-006 residue downgrade (built_in_only + non-blocking diagnostic, invalid unreachable for residue; _PASS_STATES not widened); FR-007 graph_residue.unlink_stale_project_graph helper consolidates both sites (atomic ordering preserved, _GRAPH_FILENAME reused); FR-008b hash-unification pin on real surfaces w/ negative guard; FR-009 C2-e LIVE-REPRODUCED (CRLF+BOM noop-despite-stale) and FIXED in hash_content; F5 genuine-invalid guard green. 34 new/touched tests pass; ruff+mypy clean (package-mode).
- 2026-06-18T06:46:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=4177659 – Started review via action command
- 2026-06-18T06:54:53Z – user – shell_pid=4177659 – WP04 APPROVED. FR-006 residue downgrade at reader (built_in_only + non-blocking detail + remediation=None; terminal invalid removed for residue; C-003 no self-heal); T030 verified RED pre-fix / GREEN post-fix; _PASS_STATES NOT widened (runner.py untouched). test_computer.py faithful; [invalid] vocab re-pointed to genuine _compute_charter_source (untouched). F5 genuine-invalid guard real+GREEN. FR-007 unlink_stale_project_graph in src/charter/synthesizer/graph_residue.py (no specify_cli cycle), reuses _GRAPH_FILENAME; atomic unlink->guard.replace ordering byte-unchanged at project_drg.py; _fresh_doctrine rewired. FR-008b hash pin on REAL surfaces + mutate-diverge negative guard (non-tautological). C2-e SHARED-HASHER-SEAM SAFETY: NORMAL CONTENT (no BOM, LF-only) HASHES UNCHANGED = YES (verified old-vs-new; only BOM/CRLF changes + converges to plain-LF); NO mass-restale. test_c2e_no_noop_despite_stale real (crlf/bom/bom_crlf). No new read-path mutator (NFR-006). ruff clean incl C901<=15; mypy clean package-mode. Sole suite failure test_cli.py::test_hard_error_exits_two confirmed PRE-EXISTING (fails identically on mission base). #2009 stays in-mission (SC-007 orchestrator).
