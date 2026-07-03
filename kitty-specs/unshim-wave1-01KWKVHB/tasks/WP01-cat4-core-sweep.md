---
work_package_id: WP01
title: Category_4 core sweep (7 shims minus tasks_support)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs:
- '#2289'
planning_base_branch: tidy/unshim-wave1
merge_target_branch: tidy/unshim-wave1
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave1 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Sequential deletion lane
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2199056"
history:
- at: '2026-07-03T12:00:28Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/acceptance_matrix.py
- src/specify_cli/core/identity_aliases.py
- src/specify_cli/doc_generators.py
- src/specify_cli/doc_state.py
- src/specify_cli/gap_analysis.py
- src/specify_cli/state_contract.py
- src/specify_cli/workspace_context.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
- pyproject.toml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Category_4 core sweep (7 shims minus tasks_support)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-001/FR-002/FR-003 (IC-01): delete the 7 non-tasks_support category_4
backcompat shims, re-anchor their ~14 test sites to the spec's VERIFIED canonical
homes, and drain every gate/config row atomically (C-006: the stale-allowlist guard
at `test_no_dead_modules.py:590` hard-fails any tip where a deleted module's
allowlist row survives). Success = the 7 files gone, `_CATEGORY_4_BACKCOMPAT_SHIMS`
has exactly 1 row left (`tasks_support`), `_baselines.yaml category_4: 1`, the
`doc_state`/`gap_analysis` mypy overrides gone, full architectural + touched-test
sweep green, whole-tree mypy still 0.

## Context & Constraints

Read FIRST: `kitty-specs/unshim-wave1-01KWKVHB/spec.md` (rev 2) — the
**Squad-Verified Census** table is the ONLY re-anchor authority (C-005; the #2289
issue body has 4 wrong canonical-home cells — do not consult it for paths):

| Delete | Canonical home (re-anchor target) |
|---|---|
| `src/specify_cli/acceptance_matrix.py` | `specify_cli.acceptance.matrix` |
| `src/specify_cli/core/identity_aliases.py` | `specify_cli.identity.aliases` |
| `src/specify_cli/doc_generators.py` | `specify_cli.doc_analysis.doc_generators` |
| `src/specify_cli/doc_state.py` | `specify_cli.doc_analysis.doc_state` |
| `src/specify_cli/gap_analysis.py` | `specify_cli.doc_analysis.gap_analysis` |
| `src/specify_cli/state_contract.py` | `specify_cli.state.contract` |
| `src/specify_cli/workspace_context.py` | `specify_cli.workspace.context` |

- Three shims (`identity_aliases`, `state_contract`, `workspace_context`) have ZERO
  importers anywhere → pure deletes, no re-anchor.
- ~12 string-literal path refs to `workspace_context.py` in historical
  mission-fixture `owned_files` lists: LEAVE AS-IS (spec edge-case disposition).
- `doc_state` has dynamic `import specify_cli.doc_state as mod` sites → re-anchor the
  module object, not just symbols.
- C-002: deletion-only — no behavior changes, no refactors of canonical homes.
- research.md D5: `identity_aliases::with_tracked_mission_slug_aliases` at
  `test_no_dead_symbols.py:176` is BOTH the category_4 symbol row AND a
  `_CATEGORY_B` member — removing it is the −1 that WP03's −12 completes to reach
  category_b 237→224. Do NOT touch `category_b_grandfathered_legacy` in
  `_baselines.yaml` in this WP (it only reaches 224 after WP03).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/unshim-wave1
- **Merge target branch**: tidy/unshim-wave1

## Subtasks & Detailed Guidance

### Subtask T001 – Delete the 3 zero-importer shims + drain their rows

- **Steps**:
  1. `git rm` `core/identity_aliases.py`, `state_contract.py`, `workspace_context.py`.
  2. Remove their 3 rows from `_CATEGORY_4_BACKCOMPAT_SHIMS`
     (`test_no_dead_modules.py:276-287` region).
  3. Remove the `identity_aliases::with_tracked_mission_slug_aliases` symbol row
     (`test_no_dead_symbols.py:176`).
  4. Run the two gate files — green proves the drain matched the deletion exactly.
- **Files**: the 3 shims + 2 gate files.

### Subtask T002 – acceptance_matrix

- **Steps**: `git rm acceptance_matrix.py`; re-anchor its 2–3 test import sites to
  `specify_cli.acceptance.matrix`; remove its `_CATEGORY_4` row; run the re-anchored
  test files.

### Subtask T003 – doc_analysis trio

- **Steps**:
  1. `git rm` `doc_generators.py`, `doc_state.py`, `gap_analysis.py`.
  2. Re-anchor their ~9 sites (1–2 + 3–6 + 1–2 files) to `specify_cli.doc_analysis.*`;
     handle the `doc_state` dynamic module-object imports.
  3. Remove their 3 `_CATEGORY_4` rows.
  4. `pyproject.toml`: delete the `specify_cli.doc_state` and
     `specify_cli.gap_analysis` entries from the transitional-quarantine
     `[[tool.mypy.overrides]]` list (lines ~314/322; leave `tasks_support` — WP02's).
  5. Run the re-anchored test files + `python -m mypy src/` (must stay 0).

### Subtask T004 – Baseline + WP gate sweep

- **Steps**:
  1. `_baselines.yaml`: `category_4_backcompat_shims: 8` → `1`.
  2. Full sweep: `PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider`
     green; `ruff check .` clean on touched files; whole-tree mypy 0; the NFR-002
     grep (quickstart.md) restricted to the 7 deleted names returns empty in `src/`
     — paste the grep command + its empty output into the Activity Log.
  3. Commit with a message naming the 7 modules + the drain rows.

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py -q
PWHEADLESS=1 pytest <each re-anchored test file> -q
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
python -m mypy src/ 2>&1 | tail -2
ruff check .
```

## Risks & Mitigations

- **Missed re-anchor** → a canonical home flags as newly-dead or an import error
  surfaces; the per-file test runs catch it before the sweep.
- **Over-drain** (removing a row whose module still exists) → same guard, opposite
  direction; the gate is bidirectional.
- **Scope creep into canonical homes** → C-002; the diff shows deletions + import-line
  edits + gate rows ONLY.

## Review Guidance

- Diff shape: 7 file deletions, ~14 import-line edits, gate-row removals, 2 pyproject
  lines, 1 baseline line. Nothing else.
- Spot re-derive 3 re-anchors against the spec table (not the issue body).
- Verify `category_b` baseline was NOT touched (it moves only in WP03).
- Confirm the two removed `[[tool.mypy.overrides]]` entries are `doc_state` +
  `gap_analysis` ONLY — `tasks_support` must remain (it is WP02's; stripping it here
  silently gaps WP02's drain).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T12:00:28Z – system – Prompt created.
- 2026-07-03T12:18:09Z – claude:opus:python-pedro:implementer – shell_pid=2170569 – Assigned agent via action command
- 2026-07-03T12:35:00Z – claude:opus:python-pedro:implementer – shell_pid=2170569 – WP01 complete: deleted 7 category_4 shims + re-anchored 9 test import sites to verified canonical homes (spec rev 2 census, C-005) + atomic C-006 drain (7 gate rows + identity_aliases symbol row + baseline category_4 8->1 + doc_state/gap_analysis mypy overrides). Gates: architectural sweep 641 passed/4 skipped GREEN; gate files+ratchet 14 passed; re-anchored files 153 passed/1 skipped/1 pre-existing env fail (test_sphinx_generation_end_to_end - sphinx absent from venv, fails identically on unmodified base, out of scope); mypy 0 issues (1063 files); diff-scoped ruff exit 0; NFR-002 grep empty. category_b baseline + tasks_support untouched (WP02/WP03). --force used: move-task validator misattributed WP02's subtasks T005-T007 as WP01 unchecked; T001-T004 (WP01's real subtasks) all done; rationale in Activity Log.
- 2026-07-03T12:35:53Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2199056 – Started review via action command
- 2026-07-03T12:54:22Z – user – shell_pid=2199056 – Review passed: 7 shims deleted (acceptance_matrix, core.identity_aliases, doc_generators, doc_state, gap_analysis, state_contract, workspace_context); 9 import sites re-anchored to spec.md rev-2 census paths; atomic gate drain (7 category_4 rows + 1 symbol row + category_4 baseline 8→1 + doc_state/gap_analysis mypy overrides). Reviewer verified: NFR-002 grep empty; mypy 0/1063 (primary venv); test_no_dead_modules+symbols 11 passed; re-anchored files 153 passed/1 pre-existing sphinx env fail; arch sweep 641 passed/4 skipped; category_b 237 untouched; tasks_support override retained. --force: T005-T007 misattribution tooling gap (WP02 subtasks); issue-matrix schema migrated to canonical format (pre-existing planning artifact drift, not WP01 code issue).
