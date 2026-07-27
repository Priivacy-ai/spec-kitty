---
work_package_id: WP02
title: Decompose workflow.py (+ seam-route +
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: feat/coord-authority-trio-degod
merge_target_branch: feat/coord-authority-trio-degod
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-trio-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-trio-degod unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Decompose
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "551407"
history:
- timestamp: '2026-07-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/specify_cli/cli/commands/agent/test_workflow_cores.py
execution_mode: code_change
mission_id: 01KX7094EYXKC6EJZC9XZCADS3
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_cores.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/specify_cli/cli/commands/agent/test_workflow_cores.py
role: implementer
tags: []
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP02 – Decompose workflow.py (+ seam-route + #2508)

## Objective
FR-001/FR-005/FR-010. #2508 red-first FIRST (against untouched code), then split `implement`(CC78 @1379)/`review`(CC72 @2432)/`_resolve_review_context`(CC37 @2085) into Typer-shell + request dataclass + pure cores + executor; route workflow's leaf resolver calls onto the seam. workflow.py has no `__all__` — keep it that way.

## Subtasks (ORDER MATTERS — #2508 red-first is FIRST)
- **T006** #2508 (FR-010) RED-FIRST: write a repro that drives the REAL command entry (`agent action implement`/`review` on a coord-topology mission → `_commit_workflow_change` → observe the `safe_commit` fallback misfire) and FAILS on untouched `workflow.py`. THEN fix `_load_coord_branch_meta:276`/`_commit_workflow_change:571` to anchor the identity read on primary (sibling `_canonical_status_feature_dir:303` was already fixed; this one wasn't). Do this BEFORE any extraction so red is proven against pre-mission code.
- **T007** Extract pure cores → `workflow_cores.py`: review-context builder, review-feedback resolution (`_resolve_review_feedback_*`), decision mapping, renderers (`_render_*`), status-error classifier (`_is_missing_canonical_status_error:1030`). No I/O.
- **T008** Extract executor → `workflow_executor.py`: `_commit_workflow_change` (post-fix), `_ensure_workspace_materialized:1318`.
- **T009** Reduce `implement`(CC78) → Typer-shell (~150-200 LOC Annotated params) + request dataclass over cores; S3776 ≤15; re-run `tests/characterization/` GREEN before proceeding.
- **T010** Reduce `review`(CC72) → shell over cores; S3776 ≤15; characterization green.
- **T011** Reduce `_resolve_review_context`(CC37) → cores; S3776 ≤15; characterization green.
- **T012** Route workflow's leaf resolver calls onto the seam wrappers (grep the real count first). Keep every read LENIENT (`resolve_handle_to_read_path` require_exists=False) — do NOT introduce fail-close. ZERO diff to the shared seam modules.
- **T013** Re-export shims at `workflow.py` (bare `from workflow_cores/executor import <name>`, NOT in `__all__`) for moved monkeypatch targets (`safe_commit`, `_find_mission_slug`, `resolve_workspace_for_wp`, …); run the workflow test files (re-verify count) — green.
- **T014** Append `tracers/workflow.md` (extraction decisions, S3776 before→after via radon, surprises); core unit tests in `test_workflow_cores.py` (`pytestmark=[pytest.mark.unit]`). DoD: re-verify the `top_level_implement` delegation call site (workflow.py:1601, 6 keyword params) is intact after WP03.

## Shared discipline (squad-hardened)
- **Complexity gate**: Sonar S3776 ≤15 is the gate of record; ruff C901 is BLIND. Local pre-flight = `uvx radon cc -s -n B <file>` (reproduces the cited CC numbers). Actual Sonar is NOT run on PRs — confirm via manual `gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod` (the branch-review script lacks a --branch flag — WP05 tracks that gap).
- **Shims (FR-009)**: add re-export shims as bare `from <cores/executor> import <name>` — do NOT add shimmed names to `__all__` (workflow.py has none; keep it that way; implement.py __all__ stays its 4 names; acceptance keeps only its 2 accept.py-consumed exports). A public shim needs an allowlist entry in `test_no_dead_symbols.py` with the #2057 rationale, never a silent __all__ add.
- **Read contracts (corrected)**: the trio uses the LENIENT projection (`resolve_handle_to_read_path`, `require_exists=False`) + acceptance-specific existence-degrade. There is NO `require_exists=True` fail-closed site in the trio — do NOT introduce one. Keep every currently-lenient read lenient.
- **C-004 tripwire**: ZERO diff to the shared seam modules `mission_runtime/resolution.py` / `missions/_read_path_resolver.py`; a missing seam capability is ESCALATED, not patched in place.
- **Markers**: every new test file needs its own `pytestmark` (unit for pure-core tests; integration+git_repo for CliRunner/git tests; architectural for arch tests).
- Verify the real monkeypatch/test-file count with a fresh grep before relying on the planning-time figure.
## Branch Strategy
`spec-kitty agent action implement WP02 --agent <name>` (deps WP01; ∥ WP03/WP04).

## Definition of Done
- [ ] #2508 red-first repro FAILS on untouched code (real command entry), passes after fix; implement/review/_resolve_review_context each S3776 ≤15 (radon proxy + Sonar dispatch).
- [ ] Characterization + workflow test files green; seam-routed & LENIENT-preserved; shims bare-import not __all__; zero seam-module diff; ruff+mypy clean; tracer appended.

## Activity Log

- 2026-07-11T07:02:40Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – Assigned agent via action command
- 2026-07-11T08:30:05Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – WP02 done: implement 78->11 CC, review 72->7 CC, _resolve_review_context 37->8 CC (radon proxy), all executor/cores functions <=14. #2508 red-first proven (tests/regression/test_issue_2508.py) and fixed via PRIMARY_METADATA seam anchor. implement/review/_resolve_review_context stay in workflow.py as thin shells (deliberate, monkeypatch-safety). New workflow_cores.py + workflow_executor.py with _wf() lazy accessor pattern. Bare shims, no __all__, zero seam-module diff. Characterization + regression + workflow tests green; broad sweep 4999 passed / 2 pre-existing unrelated failures. ruff+mypy clean.
- 2026-07-11T08:33:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=551407 – Started review via action command
- 2026-07-11T08:42:12Z – user – shell_pid=551407 – verified: radon implement 78->11 / review 72->7 / _resolve_review_context 37->8, all <=15 (max CC 14, no new fn >15); #2508 red-first PROVEN via real CLI entry (agent action implement WP01 CliRunner) -> reverting PRIMARY_METADATA anchor makes test FAIL, fix anchors identity read on primary at workflow_executor.py:143-146; delegation call site workflow.py:992 top_level_implement 6 kwargs intact + implement.py zero-diff; seam LENIENT preserved (_canonical_status_feature_dir routes resolve_handle_to_read_path, no require_exists=True added) + zero diff to resolution.py/_read_path_resolver.py; cores pure, bare shims, no __all__; monkeypatch symbols resolve; characterization 73/73, workflow suite 102/102, cores 42/42 green
