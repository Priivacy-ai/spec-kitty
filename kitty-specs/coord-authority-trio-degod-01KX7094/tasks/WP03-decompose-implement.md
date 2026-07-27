---
work_package_id: WP03
title: Decompose implement.py (+ seam-route)
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: feat/coord-authority-trio-degod
merge_target_branch: feat/coord-authority-trio-degod
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-trio-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-trio-degod unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Decompose
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "429674"
history:
- timestamp: '2026-07-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/implement.py
create_intent:
- src/specify_cli/cli/commands/implement_cores.py
- tests/specify_cli/cli/commands/test_implement_cores.py
execution_mode: code_change
mission_id: 01KX7094EYXKC6EJZC9XZCADS3
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/implement_cores.py
- tests/specify_cli/cli/commands/test_implement_cores.py
role: implementer
tags: []
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP03 – Decompose implement.py (+ seam-route)

## Objective
FR-002/FR-005. Split the two `# noqa: C901` bodies (`_ensure_planning_artifacts_committed_git:756` CC22, `implement:1105` CC60) into staging cores + git executor + shell; remove both noqa; route implement's leaf calls onto the seam. Preserve the `top_level_implement` entry signature (WP02 delegates to it, 6 keyword params at workflow.py:1601).

## Subtasks
- **T015** Extract pure cores → `implement_cores.py`: git-porcelain/diff family (`_feature_dir_status_entries:288`, `_files_changed_vs_ref:483`, `_exclude_coord_owned:571`, `_is_vcs_lock_only_meta_diff:595`, `_drop_vcs_lock_only_meta:641`) + placement family (`_resolve_placement_ref:678`, `_resolve_claim_commit_target:708`, `_placement_coord_filter:733`). git injected as a port (no direct I/O in cores).
- **T016** Split `_ensure_planning_artifacts_committed_git` → staging-decision core + git executor; remove its `# noqa: C901`.
- **T017** Reduce `implement:1105` → Typer-shell over cores + `_run_recover_mode:1008`; remove its `# noqa: C901`; S3776 ≤15; characterization green.
- **T018** Route implement's leaf resolver calls onto the seam wrappers (grep real count); keep lenient; ZERO diff to shared seam modules.
- **T019** Re-export shims at `implement.py` (bare import, NOT in `__all__` — its `__all__` stays the existing 4 names); run implement test files (re-verify count) — green; confirm `top_level_implement` 6-keyword signature UNCHANGED.
- **T020** Append `tracers/implement.md`; core unit tests in `test_implement_cores.py` (`pytestmark=[pytest.mark.unit]`).

## Shared discipline (squad-hardened)
- **Complexity gate**: Sonar S3776 ≤15 is the gate of record; ruff C901 is BLIND. Local pre-flight = `uvx radon cc -s -n B <file>`. Sonar is NOT run on PRs — confirm via manual `gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod`.
- **Shims (FR-009)**: bare `from <cores/executor> import <name>`, NOT in `__all__` (implement.py __all__ stays its 4 names; acceptance keeps only its 2 accept.py-consumed exports). Public shim → allowlist in `test_no_dead_symbols.py` (#2057 rationale), never a silent __all__ add.
- **Read contracts**: the trio is LENIENT (`resolve_handle_to_read_path` require_exists=False) + acceptance existence-degrade. NO fail-closed site in the trio — do not introduce one.
- **C-004 tripwire**: ZERO diff to `mission_runtime/resolution.py` / `missions/_read_path_resolver.py`; missing seam capability → ESCALATE.
- **Markers**: per-file `pytestmark` (unit / integration+git_repo / architectural).
- Verify the real test-file count with a fresh grep before trusting the estimate.
## Branch Strategy
`spec-kitty agent action implement WP03 --agent <name>` (deps WP01; ∥ WP02/WP04).

## Definition of Done
- [ ] Both noqa:C901 removed; implement/_ensure_planning_artifacts_committed_git S3776 ≤15 (radon proxy + Sonar dispatch); characterization + implement test files green.
- [ ] Seam-routed lenient; `top_level_implement` signature preserved; shims bare-import not __all__; zero seam-module diff; ruff+mypy clean; tracer appended.

## Activity Log

- 2026-07-11T07:02:48Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – Assigned agent via action command
- 2026-07-11T07:58:00Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – Decomposed implement.py (1639->1538 LOC) into implement_cores.py (461 LOC, pure decision cores + GitPort protocol) + implement.py shell/executor. Radon before->after: implement F(60)->C(14), _ensure_planning_artifacts_committed_git D(22)->B(8); both noqa:C901 removed, all functions now <=15 (Sonar S3776 gate). top_level_implement's 6-kwarg signature verified unchanged (workflow.py zero-diff). Zero diff to mission_runtime/resolution.py and missions/_read_path_resolver.py. Shims: bare re-export from implement_cores.py, __all__ stays its original 4 names. 44 new core unit tests (test_implement_cores.py, fake GitPort, no subprocess/real git) + all 207 existing implement/agent/characterization tests green + write-side-rederivation ratchet re-pinned (line 88->99, pure shim-import line drift) + one monkeypatch target updated to follow _placement_coord_filter's move to implement_cores.py. Pre-existing, out-of-scope: 3 tests/architectural failures all trace to WP01's tests/characterization/test_trio_json_envelope.py missing a CI-gate marker (zero diff from WP03).
- 2026-07-11T07:58:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=429674 – Started review via action command
- 2026-07-11T08:04:39Z – user – shell_pid=429674 – verified: both noqa:C901 gone + radon drops (implement F60->C14, ensure_planning B8) under S3776/ruff-15 gate; top_level_implement 6-kwarg signature byte-identical to base; characterization 73/73 + implement/cores 128/128 green; git injected as GitPort port; zero seam diff, all=4 names, shims reachable for monkeypatch
