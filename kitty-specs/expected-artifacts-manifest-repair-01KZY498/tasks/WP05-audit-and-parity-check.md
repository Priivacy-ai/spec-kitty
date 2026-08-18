---
work_package_id: WP05
title: Post-reconciliation audit + cross-cutting parity check
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-expected-artifacts-manifest-repair-01KZY498-lane-d
base_commit: 1eea815bd045a1326f92e553410b71d146a95c4a
created_at: '2026-08-14T05:09:23.719757+00:00'
subtasks:
- T020
- T021
- T022
phase: Phase 3 - Audit + cross-cutting checks (depends on WP01, WP02, WP03)
assignee: ''
agent: claude
history:
- timestamp: '2026-08-14T00:00:00Z'
  agent: claude
  action: Prompt generated via manual /spec-kitty.tasks-outline + /spec-kitty.tasks-packages equivalent (tasks-authoring agent)
agent_profile: implementer-ivan
authoritative_surface: tests/dossier/test_manifest_guard_parity.py
create_intent:
- tests/dossier/test_manifest_guard_parity.py
execution_mode: code_change
model: ''
owned_files:
- tests/dossier/test_manifest_guard_parity.py
- tests/doctrine/missions/test_repository.py
- tests/runtime/test_bridge_cores.py
- tests/integration/test_research_runtime_walk.py
- tests/integration/test_documentation_runtime_walk.py
- tests/charter/test_resolved_mission_type_context.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – Post-reconciliation audit + cross-cutting parity check

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Run the checks that genuinely require all four manifests' **final** content to
exist first: the guard-vs-comment parity cross-check across `research`/
`documentation`/`software-dev` (AS7/SC-001), the `manifest_version` stability
cross-check across all four files (SC-006), and the `manifest_version` rationale
comment presence check across those same four files (FR-013's cross-file
verification). Also audit five files named by FR-015 for any assertion that still
depends on pre-reconciliation manifest content. This is **Implementation Concern
IC-05** from `plan.md` — the only IC with a genuine content dependency on other
WPs (not merely a scheduling convenience).

## Context

**Why this WP genuinely depends on WP01, WP02, WP03** (not a C-011 exception):
AS7, SC-006, and FR-013's cross-file check all read across all four manifests'
**final** content — they cannot be meaningfully written or run until WP02's three
edits and WP03's new file both exist. This WP's own red-first tests (in the new
`test_manifest_guard_parity.py`) still land before this WP's own
audit/correction commit, the same C-011 discipline as every other WP — the
dependency is on *content*, not on skipping red-first.

**Why this WP does NOT depend on WP04**: `plan.md`'s IC-05 sequencing note is
explicit — WP04's override-mirror deprecation is unrelated to the guard-parity/
manifest-version/rationale-comment checks this WP runs. Do not add a dependency
on WP04 here; if `tracer-approach.md`'s "Chokepoints & execution sequencing" addendum recommends running WP04 before
this WP for `test_manifest.py`-adjacent reasons, that is an execution-order
recommendation, not a content dependency — this WP's `owned_files` do not include
`test_manifest.py` at all (see below).

**This WP does NOT touch `tests/dossier/test_manifest.py`** — per `plan.md`'s
explicit design, IC-05's cross-cutting checks land in a **separate new file**,
`tests/dossier/test_manifest_guard_parity.py`, specifically so this WP never needs
to touch the other four WPs' sections in that shared file. This is the one WP in
this mission with **zero** out-of-map-edit exposure to the `test_manifest.py`
chokepoint.

### ⚠️ Chokepoint note: `tests/runtime/test_bridge_cores.py`

This WP's `owned_files` includes `tests/runtime/test_bridge_cores.py` for FR-015's
audit (read-only unless a pinned assertion is actually found). **Open PR #3395**
("fix(requirements): scope spec.md requirement extraction to declared ids, not
prose citations") also modifies this same file (confirmed via `gh pr list`
file-overlap check at planning time). If PR #3395 merges before this WP executes,
rebase this WP's own touch (if any correction is needed) against the merged state
before editing. If this WP's audit finds no correction needed here (the expected
outcome — `test_bridge_cores.py` tests the guard tables directly, which this
mission's C-001 constraint keeps untouched, so it should already be
content-agnostic to this mission's manifest edits), this chokepoint is moot for
this WP's own diff, but the orchestrator should still confirm PR #3395's merge
state before finalizing this mission's PR to avoid a stale-rebase surprise.

## Subtask T020: Red-first tests — cross-cutting checks in new `test_manifest_guard_parity.py`

**Purpose**: Land the three cross-cutting tests before running the audit that
depends on them existing as the acceptance bar.

**Steps**:
1. Create `tests/dossier/test_manifest_guard_parity.py` (new file). Add a module
   docstring stating its purpose: cross-cutting checks that read across all four
   `expected-artifacts.yaml` files' final content, kept separate from
   `tests/dossier/test_manifest.py` specifically so this file never needs to touch
   that file's per-IC-owned sections (per `plan.md`'s Implementation Concern Map,
   "Test file ownership" note).
2. Add `test_all_required_by_step_keys_match_guard_or_carry_comment` (AS7): for
   each of the `research`/`documentation`/`software-dev` manifests, load the raw
   YAML via `ruamel.yaml`'s round-trip loader (`ruamel.yaml.YAML()`, producing a
   `CommentedMap`), iterate every `required_by_step` key, and assert each key
   either (a) corresponds to a real branch in `runtime_bridge_cores.py`'s guard
   tables (cross-check by reading the guard-table source directly — build a small
   allow-list of step-id → guard-function-name mappings inline in the test, sourced
   from `plan.md`'s Test Strategy table and this WP's own re-verification) or (b)
   carries an inline YAML comment near that key documenting the specific
   non-filesystem-expressible check it corresponds to (use `CommentedMap`'s
   `.ca.items` comment-attachment API — the same mechanism T022 below uses for the
   `manifest_version` comment check). Zero unexplained divergences is the pass
   condition. **Additionally**, for the `software-dev` manifest's `tasks_packages`
   and `tasks_finalize` entries specifically, assert the literal `path_pattern`
   string value is exactly `"tasks/WP*.md"` (not merely that the `tasks_packages`/
   `tasks_finalize` step keys are present with *some* pattern) — this is a
   dedicated, narrower check on top of the step-key-presence check above, so a
   future regression to the broader `tasks/*.md` pattern (which the guard's
   `tasks_dir.glob("WP*.md")` call does not actually check, per FR-007/AS5) is
   caught structurally rather than only by manual review.
3. Add `test_manifest_version_unchanged_on_all_four_files` (SC-006): for each of
   the four `packs/built-in/missions/{research,documentation,software-dev,plan}/expected-artifacts.yaml`
   files, assert `manifest_version == "1"` (a straightforward content check, or a
   `grep`-equivalent regex over the raw text — either is acceptable; prefer
   loading via `ManifestRegistry.load_manifest()` for consistency with the rest of
   this test suite).
4. Add `test_manifest_version_rationale_comment_present` (FR-013): for each of the
   same four files, load the raw YAML via `ruamel.yaml`'s round-trip loader and
   inspect `.ca.items` to find a comment attached at/near the `manifest_version:
   "1"` key whose text contains a recognizable Decision-2 rationale marker (e.g.
   references `manifest_version` being a sync-namespace identity key rather than a
   content-freshness counter) — a content check on the comment itself, not merely
   on the version value (this is the row `plan.md`'s Test Strategy table names
   explicitly as distinct from SC-006's value-only check).

**Files**: `tests/dossier/test_manifest_guard_parity.py` (new, ~120-180 lines).
**Validation**: All three tests should be **GREEN once WP01/WP02/WP03 have
landed** (this WP runs after them, so its own red-first bar is: was this test RED
if you reverted WP02/WP03's content edits or WP01's `extra="forbid"` addition?
Confirm this via a local revert-and-rerun check, not merely by writing the
assertions and having them pass against already-correct content — the ATDD bar is
about proving the test *would* catch a regression, which for a cross-cutting
check authored after the fact means demonstrating it fails against the
pre-WP02/WP03 manifest content, e.g. by temporarily checking out `packs/built-in/missions/software-dev/expected-artifacts.yaml`
at its pre-WP02 state in a scratch copy and confirming the parity test fails
against it).

## Subtask T021: Audit — five FR-015 files for pre-reconciliation content dependencies

**Purpose**: Confirm (or correct) that `tests/doctrine/missions/test_repository.py`,
`tests/runtime/test_bridge_cores.py`, `tests/integration/test_research_runtime_walk.py`,
`tests/integration/test_documentation_runtime_walk.py`, and
`tests/charter/test_resolved_mission_type_context.py` do not pin
pre-reconciliation manifest content.

**Steps**:
1. **`tests/doctrine/missions/test_repository.py`**: read `TestGetExpectedArtifacts`
   (lines ~378-394). Confirmed at planning time — both tests use synthetic
   `tmp_path` fixtures with hand-written YAML, not the real built-in manifest
   content. Expected outcome: **no correction needed**. Re-confirm this holds by
   running the class and reading its assertions once more before marking this
   file audited-clean.
2. **`tests/runtime/test_bridge_cores.py`**: read the guard-table tests
   (confirmed at planning time to include `test_research_gathering_both_conditions_independently_appended`,
   the `documentation` step-message tests around lines 479-488, and the
   `tasks_outline`/`tasks_packages`/`tasks_finalize` tests around lines 233-406).
   These test `runtime_bridge_cores.py`'s guard functions **directly** (not via
   the manifest), and this mission's C-001 constraint keeps that file untouched.
   Expected outcome: **no correction needed** — these are the guard-truth-source
   tests this mission reconciles the manifest *against*, not tests of the
   manifest itself. See the chokepoint note in Context above re: PR #3395 sharing
   this file for an unrelated reason.
3. **`tests/integration/test_research_runtime_walk.py`** and
   **`tests/integration/test_documentation_runtime_walk.py`**: read the fixture
   setup around the lines confirmed at planning time (research: `source-register.csv`
   write at line ~431; documentation: the `gap-analysis.md`/`audit-report.md`/
   `release.md` writes at lines ~121-130 and the `(step, artifact)` pairs at
   lines ~571-575). These integration walks exercise the guard chain end-to-end
   with real filesystem fixtures matching the **guard's** requirements (which this
   mission does not change), not the manifest's. Expected outcome: **no
   correction needed** — but confirm directly by reading both files in full before
   concluding.
4. **`tests/charter/test_resolved_mission_type_context.py`**: this is the
   **confirmed real consumer** (spec.md's "Non-Gate Consumer Notes"). Read
   `test_doctrine_slots_and_populated_step_contracts` (lines ~154-169) — its three
   `bundle.expected_artifacts` assertions check `is not None`, `isinstance(...,
   dict)`, and `["mission_type"] == "software-dev"` only — none of these assert on
   the *specific step content* WP02 changes (FR-006/FR-007/FR-008). Expected
   outcome: **no correction needed**, but this is the one file where "must still
   pass" is a real, load-bearing claim (not just an audit formality) — actually run
   this test against WP02's final `software-dev` content and confirm it passes,
   don't just read the assertions and assume.
5. For any of the five files where the audit **does** find a pinned
   pre-reconciliation assertion (budget review time for this possibility — see
   Risks below), correct it in this same WP's implementation commit, and record
   what was found and corrected in this WP's PR-body evidence (do not silently
   fix without noting the finding, matching this mission's own pattern of
   surfacing discoveries rather than absorbing them quietly).

**Files**: the five files named above (audited; each corrected **only if** a
pinned assertion is actually found — expected outcome for all five is
audit-clean, per planning-time verification, but this WP must independently
re-verify, not merely cite the plan's expectation).
**Validation**: `pytest tests/doctrine/missions/test_repository.py tests/runtime/test_bridge_cores.py tests/integration/test_research_runtime_walk.py tests/integration/test_documentation_runtime_walk.py tests/charter/test_resolved_mission_type_context.py -q`
passes with zero failures against WP01/WP02/WP03's final content.

## Subtask T022: Full-surface validation run + SC-002 confirmation

**Purpose**: Confirm the mission's full validation surface passes with zero new
failures relative to WP01's T001 baseline (SC-002), now that all content-bearing
WPs (WP01-WP03) have landed.

**Steps**:
1. Run the exact NFR-003 scoped surface:
   ```bash
   uv run python -m pytest tests/dossier/ tests/doctrine/missions/ tests/runtime/ \
     tests/charter/test_resolved_mission_type_context.py -q --tb=short
   ```
2. Compare the pass/fail counts against WP01's T001 baseline capture. Confirm zero
   new failures beyond the pre-existing baseline (SC-002).
3. Run `mypy --strict` and `ruff check .` against every file this mission changed
   across all WPs (not just this WP's own files) and confirm zero new issues
   (SC-007) — this is the mission-level confirmation, not just this WP's own
   NFR-002 check.
4. Confirm `grep manifest_version packs/built-in/missions/*/expected-artifacts.yaml`
   shows `"1"` for all four files (SC-006, a final direct-command confirmation
   alongside T020's pytest-based check).

**Files**: None changed — validation-only step.
**Validation**: The recorded counts from this step become the mission's
pre-merge evidence (PR body / `reviews/` trail), alongside WP01's baseline.

## Definition of Done

- [ ] `test_manifest_guard_parity.py` exists with all three cross-cutting tests,
      committed before this WP's own audit/correction commit (C-011).
- [ ] All five FR-015 files are confirmed clean (or corrected, with the finding
      recorded) against WP02/WP03's final content.
- [ ] `test_resolved_mission_type_context.py`'s three `bundle.expected_artifacts`
      assertions for `software-dev` are confirmed passing against WP02's final
      content (not merely audited by inspection).
- [ ] The mission's full NFR-003 scoped test surface passes with zero new
      failures relative to WP01's T001 baseline (SC-002).
- [ ] `mypy --strict` / `ruff check .` report zero new issues mission-wide
      (SC-007).
- [ ] `manifest_version` confirmed `"1"` on all four files (SC-006).

## Risks

- **The FR-015 audit could find more than the one confirmed pinned test**
  (`test_resolved_mission_type_context.py`, which is itself confirmed
  *unaffected* by content, just a real consumer) — budget review time for that
  possibility rather than assuming the audit is a formality (per `plan.md`'s
  IC-05 risk note).
- **Chokepoint**: `test_bridge_cores.py` overlap with open PR #3395 — see Context
  above.
- **The AS7 parity test's guard-table cross-check is itself a maintenance
  surface**: if `runtime_bridge_cores.py`'s guard tables change in a future,
  unrelated mission, this test's inline allow-list could drift stale. This is a
  known limitation, not a defect to fix here — `spec.md`'s "Edge Cases" section
  already names a general structural parity gate as a future follow-up, not
  required by this mission's acceptance bar.

## Reviewer Guidance

- Confirm T020's three tests were genuinely proven to fail against
  pre-reconciliation content (per T020's validation note), not merely written
  against already-correct content and never shown to catch a regression.
- Confirm the FR-015 audit's conclusions are stated explicitly in the PR body
  (clean vs. corrected, per file) rather than silently assumed.
- Confirm the full NFR-003 surface and mypy/ruff mission-wide checks were
  actually run and their results recorded, not merely claimed.

Implementation command: `spec-kitty agent action implement WP05 --agent claude`
