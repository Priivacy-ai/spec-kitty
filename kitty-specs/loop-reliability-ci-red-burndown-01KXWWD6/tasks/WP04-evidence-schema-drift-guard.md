---
work_package_id: WP04
title: Fix the schema-drift crash in dry-run evidence (#2807, clears 3 reds)
dependencies: []
requirement_refs:
- FR-004
- NFR-001
tracker_refs:
- '#2807'
planning_base_branch: fix/loop-reliability-ci-red-burndown
merge_target_branch: fix/loop-reliability-ci-red-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/loop-reliability-ci-red-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/loop-reliability-ci-red-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/evidence/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/evidence/orchestrator.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2442998"
shell_pid_created_at: "1784458197.41"
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`. Load the YAML.

## Objective
One `isinstance` guard fixes a schema-drift crash that reds THREE charter tests at once
(`test_phase3_dry_run_evidence_smoke`, the orchestrator dry-run test, AND the e2e `test_charter_epic_golden_path`).

**Authoritative grounding**: [`research.md` §3](../research.md), [`data-model.md` LM-2, LM-9, LM-10](../data-model.md).

## Context / grounding (verified on main)
- Crash: `load_url_list_from_config` in `src/charter/evidence/orchestrator.py` does
  `charter_cfg = config.get("charter") or {}` then `charter_cfg.get("synthesis_inputs")` → **`'str' object has no
  attribute 'get'`**, because post-#2773 `.kittify/config.yaml`'s `charter:` key holds a **path string**
  (`.kittify/charter/charter.yaml`), not a dict. `synthesis_inputs`/`url_list` has no live config home now.
- Sole caller of `load_url_list_from_config` is the synthesize path (`_synthesis.py`); it does NOT feed
  `charter status --json`, so the guard cannot regress that surface. The dict-shaped unit test still passes.

## Subtasks
### T007 — Guard the shape (do NOT re-wire url_list)
Add `if not isinstance(charter_cfg, dict): charter_cfg = {}` after the `config.get("charter")` read in
`load_url_list_from_config` (returns `()` — correct, the feature has no config home) + fix the stale docstring.
**Resolve by symbol (LM-10). Do NOT re-plumb url_list into charter.yaml — that is scope expansion, its own
deferred issue (LM-2, C-005).**

### T008 — Verify all 3 reds green (run the FULL e2e — LM-9)
- `PWHEADLESS=1 uv run --extra test pytest tests/charter/test_phase3_integration.py tests/charter/evidence/test_orchestrator.py -q`.
- **Run the FULL `test_charter_epic_golden_path`** — it dies AT synthesize today, so post-synthesize assertions
  are unverified; prove the whole test greens (not just that the crash cleared). `PWHEADLESS=1 uv run --extra test
  pytest tests/e2e/test_charter_epic_golden_path.py -q`.
- **ESCALATION BOUNDARY (this WP owns ONLY `orchestrator.py`):** if the guard clears the crash but the full e2e
  then fails on a *post-synthesize* assertion for a cause **unrelated** to the guard, that is a NEW, separate
  defect — STOP and escalate. Do NOT infer green from crash-clearance, and do NOT scope-expand into e2e/charter
  code you don't own to force it green. The mission's sanctioned valve is the issue-matrix `#2807`
  xfail-with-tracking-ref (issue stays open for the new defect); flag it to the orchestrator rather than
  silently editing unowned files.
- ruff + mypy --strict on `orchestrator.py` → clean.

## Definition of Done
The `isinstance` guard landed; all three tests (incl. the FULL e2e) green; `charter status --json` unregressed;
url_list re-wire NOT done (deferred); ruff + mypy clean.

## Reviewer guidance
Confirm the guard returns `()` and doesn't re-plumb url_list; confirm the FULL e2e was run to green (not inferred);
confirm `charter status --json` is unaffected.

## Activity Log

- 2026-07-19T10:45:08Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Assigned agent via action command
- 2026-07-19T10:49:38Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Ready for review: isinstance guard in load_url_list_from_config fixes 'str' object has no attribute 'get' crash post-#2773 config schema drift. All 3 gates green: phase3_integration+orchestrator unit tests (18 passed/1 skipped), FULL e2e test_charter_epic_golden_path (1 passed, no escalation boundary hit), ruff+mypy --strict clean. charter status --json spot-checked unaffected.
- 2026-07-19T10:49:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=2442998 – Started review via action command
