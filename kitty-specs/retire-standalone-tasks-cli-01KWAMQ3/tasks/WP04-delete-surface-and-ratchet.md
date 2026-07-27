---
work_package_id: WP04
title: Delete the standalone surface and shed the ratchet
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: mission/retire-standalone-tasks-cli
merge_target_branch: mission/retire-standalone-tasks-cli
branch_strategy: Planning artifacts for this mission were generated on mission/retire-standalone-tasks-cli. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/retire-standalone-tasks-cli unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 4 - Deletion and ratchet shed
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "872377"
history:
- at: '2026-06-29T22:08:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/scripts/tasks/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- scripts/tasks/**
- .kittify/overrides/scripts/tasks/**
- src/specify_cli/scripts/tasks/**
- tests/cross_cutting/misc/test_tasks_cli_commands.py
- tests/cross_cutting/misc/test_task_helpers.py
- tests/specify_cli/scripts/**
- tests/specify_cli/test_standalone_tasks_cli_canonical.py
- tests/conftest.py
- pyproject.toml
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
- tests/architectural/test_gate_read_literal_ban.py
- tests/architectural/resolution_gate_allowlist.yaml
- tests/architectural/_baselines.yaml
- tests/architectural/surface_resolution_audit/**
- tests/architectural/test_coord_read_residuals_closeout.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Delete the standalone surface and shed the ratchet

## ⚡ Do This First: Load Agent Profile
Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.
- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Atomically remove the standalone tasks CLI surface and everything that still references it, then shed the architectural-ratchet entries the deletion unblocks. After WP01–WP03, only pure scaffolding still touches the surface; this WP deletes it all together so the suite collects and passes at the boundary. This is a behavior-preserving reduction — no product behavior changes (coverage preserved by WP02/WP03 and the real-surface suites).

**Atomicity**: the deletions in T016–T020 must land together. Removing the modules (T016) without removing the `tests/utils.py` sys.path injection / DELETE-class files / allowlist entries in the same change leaves the suite red. Do all edits, then run the full suite once.

## Subtasks

### T016 — Delete the three standalone copies (FR-001/002/003)
```bash
git rm -r scripts/tasks .kittify/overrides/scripts/tasks src/specify_cli/scripts/tasks
```
Confirm `src/specify_cli/scripts/tasks/__init__.py` and the now-empty `src/specify_cli/scripts/` package go too (if `scripts/` has no other members). The wheel must no longer ship `specify_cli.scripts.tasks`.

### T017 — Delete the DELETE-class test scaffolding + empty package tree
```bash
git rm tests/cross_cutting/misc/test_tasks_cli_commands.py \
       tests/cross_cutting/misc/test_task_helpers.py \
       tests/specify_cli/test_standalone_tasks_cli_canonical.py
git rm -r tests/specify_cli/scripts   # test_task_helpers.py, scripts/tasks/test_tasks_cli.py + __init__.py package dirs
```
(`tests/cross_cutting/misc/test_acceptance_support.py` was reconciled in WP03 — do NOT delete it.)

### T018 — Remove the sys.path injection + helpers (now safe)
In `tests/utils.py` remove the `TASKS_DIR`/`sys.path` injection (`:9-13`) and `run_tasks_cli` (`:35-36`). (`write_wp` was already repointed in WP01 — do not touch it.) This is a small, justified **out-of-map edit** to a WP01-owned file; record the one-line rationale ("remove the now-orphaned standalone bootstrap, consumers deleted in T017"). In `tests/conftest.py` delete the `ensure_imports` fixture (`:737-741`) and its `# noqa: F401` after confirming no consumers reference it.

### T019 — pyproject.toml (FR-006)
Remove the now-dangling entries:
- the `scripts/tasks/acceptance_support.py` and `.kittify/overrides/scripts/tasks/acceptance_support.py` ruff per-file-ignores (`pyproject.toml:231-232`);
- the three `specify_cli.scripts.tasks.{acceptance_support,task_helpers,tasks_cli}` mypy/module entries (`:341-343`).
Confirm `uv lock --check` is unaffected (no dependency change).

### T020 — FR-007 ratchet/audit shed
Remove every dead allowlist/audit entry referencing the deleted surface:
- `tests/architectural/test_no_dead_symbols.py`: the `acceptance_support::*` block (13 entries) + `task_helpers::*` block (21 entries) = 34 symbol entries, plus their explanatory comments.
- `tests/architectural/test_no_dead_modules.py`: the 3 `specify_cli.scripts.tasks.*` entries in `_CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS` (`:272-274`) + comment.
- `tests/architectural/test_gate_read_literal_ban.py`: the `…tasks_cli.py::list_command` residual (`:1124`) + comment. **Mandatory** — this gate self-validates that pinned files exist, so a dangling entry FAILS.
- `tests/architectural/resolution_gate_allowlist.yaml`: the `_prepare_merge_metadata` write-site entry (≈`:115`).
- `tests/architectural/surface_resolution_audit/inventory.md` (2 rows) and `write_candidate_classification.yaml` (3 sites): stale rows.
- `tests/architectural/test_coord_read_residuals_closeout.py`: the `#2167`/`scripts/tasks/` comment (comment-only; no assertion).

### T021 — Recompute `_baselines.yaml` to live (C-002)
After T020's edits, set the two informational+enforced baselines to the **live frozenset/file sizes** — do not hand-count (the inline justification comments are stale):
```bash
.venv/bin/python - <<'PY'
import importlib.util
def load(p,n):
    s=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
dds=load("tests/architectural/test_no_dead_symbols.py","dds")
ddm=load("tests/architectural/test_no_dead_modules.py","ddm")
print("category_b_grandfathered_legacy ->", len(dds._CATEGORY_B_GRANDFATHERED_LEGACY))
print("category_3_external_cli_entrypoints ->", len(ddm._CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS))
PY
```
Set `test_no_dead_symbols.category_b_grandfathered_legacy` and `test_no_dead_modules.category_3_external_cli_entrypoints` to those printed values, with a `# justification:` noting the shrink (shrink needs no extra workflow per the burn-down policy). `test_gate_read_literal_ban` / `resolution_gate_allowlist` have no `_baselines.yaml` entry — their shrink is the in-file removal only.

### T022 — Verify green
```bash
grep -rn "specify_cli.scripts.tasks\|from task_helpers\|import acceptance_support\|run_tasks_cli" src/ tests/ && echo "FAIL: residual" || echo "clean"
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/ -p no:cacheprovider -q
PWHEADLESS=1 .venv/bin/python -m pytest tests/ -n auto --dist loadfile -p no:cacheprovider -q
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync/test_orphan_sweep.py -n0 -q
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src/specify_cli
```
All green (pre-existing/unrelated failures reported per the charter rule, not silenced).

## Definition of Done
- All three standalone copies + the 5 DELETE-class test files + the empty `tests/specify_cli/scripts/` tree are gone; the wheel no longer ships `specify_cli.scripts.tasks`.
- `tests/utils.py` sys.path injection + `run_tasks_cli` removed; `conftest.py::ensure_imports` removed; pyproject entries removed.
- Every dead ratchet/audit entry removed; `_baselines.yaml` equals live sizes; `test_ratchet_baselines` + `test_gate_read_literal_ban` + dead-symbol/module gates green.
- `grep specify_cli.scripts.tasks` over `src/` + `tests/` → nothing.
- Full suite + architectural suite + `ruff` + `mypy` green.

## Risks
- **Non-atomic landing** → red suite. Mitigation: make all edits, then run the suite once; do not commit a partial state.
- **Baseline drift vs the in-flight #2159 PR**: `category_b` is also touched by PR #2159 (not yet merged). On THIS branch (off `origin/main`), recompute against the live frozenset here; do not import #2159's numbers.
- **Missed importer** elsewhere → collection error. Mitigation: the T022 grep over `src/`+`tests/` must be clean.

## Reviewer guidance
Confirm: net deletion (no logic added), suite + architectural gates green, baselines equal live frozenset sizes, no dangling allowlist entry at a deleted path, and the `tests/utils.py` out-of-map edit is the documented sys.path/run_tasks_cli removal only. Confirm the `record_merge`/`finalize_merge` dead-symbol follow-up is captured as a tracked issue (plan Out-of-scope) — not folded here.

## Activity Log

- 2026-06-30T00:30:41Z – claude:sonnet:randy-reducer:implementer – shell_pid=827326 – Assigned agent via action command
- 2026-06-30T01:15:01Z – claude:sonnet:randy-reducer:implementer – shell_pid=827326 – FR-001/002/003/006/007: standalone surface deleted (3 copies+scaffolding); ratchet shed; baselines category_3 4->1, category_b 286->237; residual grep clean; architectural 599 passed (1 .worktrees-path artifact, green on merge target); ruff clean. Out-of-map: tests/utils.py sys.path removal + COORD_AUTHORITY_WRITE_FLOOR 13->12 (deletion-driven). commit 789c7526e.
- 2026-06-30T01:15:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=872377 – Started review via action command
