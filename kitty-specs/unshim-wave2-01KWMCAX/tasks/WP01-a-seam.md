---
work_package_id: WP01
title: 'A-seam: next src callers + injection seam'
dependencies: []
requirement_refs:
- FR-001
tracker_refs:
- '#'
- '2'
- '2'
- '9'
- '1'
planning_base_branch: tidy/unshim-wave2
merge_target_branch: tidy/unshim-wave2
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave2 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Sequential DAG
assignee: ''
agent: ''
history:
- at: '2026-07-03T17:18:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/next_cmd.py
- tests/specify_cli/cli/commands/test_selector_resolution.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – A-seam: next src callers + injection seam

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

Spec FR-001 (IC-01): re-point the ONLY 3 src callers of `specify_cli.next` and move the
monkeypatch injection seam + its 2 injector tests to the canonical key in ONE change.
Success = zero `specify_cli.next` references in src/ outside the shim itself; the
injector tests provably consume the injected fake; gates green.

Read FIRST: spec.md rev 2 Stream A census + research.md D2 + occurrence_map.yaml
(`import_paths.src_callers`).

## Subtasks & Detailed Guidance

### Subtask T001 – Re-point the 2 plain src imports
- `implement.py:1285` and `agent/workflow.py:1518`: `from specify_cli.next.runtime_bridge import build_operational_context_for_claim` → `from runtime.next.runtime_bridge import …`. Line numbers are current; re-locate by grep if drifted.

### Subtask T002 – Re-key the injection seam + both injectors, atomically
- `next_cmd.py:52-58` `_runtime_bridge_module()`: drop the legacy `sys.modules.get("specify_cli.next.runtime_bridge")` probe → probe/import `runtime.next.runtime_bridge` (keep the seam — it is a deliberate test seam; simplify the dead branch, do not delete the function). Also update the `:557` comment.
- `tests/specify_cli/cli/commands/test_selector_resolution.py:502,548`: re-key both `patch.dict(sys.modules, ...)` injections to `runtime.next.runtime_bridge`; ALSO update the `ModuleType("specify_cli.next.runtime_bridge")` name args at `:496` and `:542` to the canonical string (no gate catches these — by hand).
- **Consumption proof (AC-1.3)**: run the injector tests and confirm the fake is consumed via its observable side-effect (the `captured` dict / `_fake_query` sentinel, ~:484-497) — paste evidence in the Activity Log. A green exit code alone does NOT satisfy this. Record both sites as ledger rows (these are 2 of the 195).

### Subtask T003 – Gates
- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_selector_resolution.py -q` green;
  `grep -rn "specify_cli\.next" src/ | grep -v "src/specify_cli/next/"` → empty (paste); `spec-kitty next --help` exit 0; ruff diff-scoped; whole-tree mypy 0. Commit.

## Test Strategy
```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_selector_resolution.py tests/next/ -q
python -m mypy src/ 2>&1 | tail -2; ruff check .
```

## Risks & Mitigations
- Seam re-pointed without injectors (or vice versa) → vacuous injection post-deletion. One commit, both sides, consumption proof mandatory.
- **Ledger protocol (FR-002)**: every patch-string site you rewrite gets its proof recorded TWICE: (a) a row in this WP file's Activity Log table `file:line → new target → proof form (assertion file::test | red-first flip) → outcome`, and (b) the orchestrator syncs your table into `occurrence_map.yaml`'s `interception_proof` fields on the planning branch at approval (the lane guard blocks kitty-specs edits on lanes — do NOT edit the map yourself from the lane). A site without a proof row is a review reject; bulk sed is a review reject.

## Review Guidance
- The consumption-proof evidence is the headline; verify the fake's side-effect assertion yourself.
- Diff = 3 src files + 1 test file, import/seam lines only (C-002).

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T17:18:34Z – system – Prompt created.
