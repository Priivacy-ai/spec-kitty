---
work_package_id: WP04
title: Decompose acceptance/__init__.py (+ seam-route)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: feat/coord-authority-trio-degod
merge_target_branch: feat/coord-authority-trio-degod
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-trio-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-trio-degod unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - Decompose
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "365588"
history:
- timestamp: '2026-07-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- src/specify_cli/acceptance/summary_core.py
- src/specify_cli/acceptance/gates_core.py
- tests/specify_cli/acceptance/test_acceptance_cores.py
execution_mode: code_change
mission_id: 01KX7094EYXKC6EJZC9XZCADS3
model: claude-sonnet-5
owned_files:
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/summary_core.py
- src/specify_cli/acceptance/gates_core.py
- tests/specify_cli/acceptance/test_acceptance_cores.py
role: implementer
tags: []
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP04 – Decompose acceptance/__init__.py (+ seam-route)

## Objective
FR-003/FR-005. Extract matrix/gate logic into pure cores; thin executor for the CLI/commit path; route acceptance's leaf calls onto the seam. **Scope = `acceptance/__init__.py` only** (accept.py / #2482 OUT).

## Subtasks
- **T021** Extract `summary_core.py`: `collect_feature_summary:1212`(CC25), `_build_recommended_fix_order:1168`(CC22) + helpers. Pure.
- **T022** Extract `gates_core.py`: `_check_lane_gates:965`(CC19), `_all_work_packages_terminal:536`, `_find_unchecked_tasks:501`, `_check_workflow_run_evidence:1153`. Pure.
- **T023** Reduce `perform_acceptance:1661`/`_commit_acceptance_meta:1468` → thin executor over the cores; S3776 ≤15. If wiring the executor RAISES complexity above the standalone CC (13/15), record it in the tracer and re-split.
- **T024** Route acceptance's leaf resolver calls onto the seam (grep real count). `_status_read_feature_dir:747` is LENIENT (`status_dir if status_dir.exists() else feature_dir`, require_exists=False) — PRESERVE that degrade exactly; do NOT fail-close. ZERO diff to shared seam modules.
- **T025** Re-export shims at the acceptance package (bare import, NOT in `__all__`; KEEP the existing `collect_feature_summary`/`perform_acceptance` exports that `accept.py` imports for real); run acceptance test files (re-verify count) — green.
- **T026** Append `tracers/acceptance.md`; core unit tests in `test_acceptance_cores.py` (`pytestmark=[pytest.mark.unit]`).

## Shared discipline (squad-hardened)
- **Complexity gate**: Sonar S3776 ≤15 is the gate of record; ruff C901 is BLIND. Local pre-flight = `uvx radon cc -s -n B <file>`. Sonar is NOT run on PRs — confirm via manual `gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod`.
- **Shims (FR-009)**: bare `from <cores/executor> import <name>`, NOT in `__all__` (implement.py __all__ stays its 4 names; acceptance keeps only its 2 accept.py-consumed exports). Public shim → allowlist in `test_no_dead_symbols.py` (#2057 rationale), never a silent __all__ add.
- **Read contracts**: the trio is LENIENT (`resolve_handle_to_read_path` require_exists=False) + acceptance existence-degrade. NO fail-closed site in the trio — do not introduce one.
- **C-004 tripwire**: ZERO diff to `mission_runtime/resolution.py` / `missions/_read_path_resolver.py`; missing seam capability → ESCALATE.
- **Markers**: per-file `pytestmark` (unit / integration+git_repo / architectural).
- Verify the real test-file count with a fresh grep before trusting the estimate.
## Branch Strategy
`spec-kitty agent action implement WP04 --agent <name>` (deps WP01; ∥ WP02/WP03).

## Definition of Done
- [ ] Matrix/gate logic in pure cores; executor thin; S3776 ≤15 (radon proxy + Sonar dispatch); characterization + acceptance test files green.
- [ ] `_status_read_feature_dir` lenient degrade preserved; shims bare-import not __all__ (accept.py exports kept); zero seam-module diff; ruff+mypy clean; tracer appended.

## Activity Log

- 2026-07-11T07:02:57Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – Assigned agent via action command
- 2026-07-11T07:44:54Z – claude:sonnet:python-pedro:implementer – shell_pid=243517 – Decomposed acceptance/__init__.py (1737 LOC) into summary_core.py and gates_core.py; collect_feature_summary stays in __init__.py (WP01 characterization suite monkeypatches ~14 collaborators via module-attribute patching) but its own complexity dropped D(25)->B(8). _build_recommended_fix_order D(22)->predicate-table (<=3); _check_lane_gates C(19)->3 guard stages (all <=10). perform_acceptance C(13)/_commit_acceptance_meta C(15) already <=15, untouched. _status_read_feature_dir lenient degrade preserved byte-for-byte; coord-dir routing preserved. Zero diff to mission_runtime/resolution.py or missions/_read_path_resolver.py. 73 characterization + 145 acceptance + 32 new core unit tests green; ruff/mypy clean (same 5 pre-existing findings, relocated, zero new). Tracer updated on planning branch separately.
- 2026-07-11T07:46:29Z – claude:opus:reviewer-renata:reviewer – shell_pid=365588 – Started review via action command
- 2026-07-11T07:56:25Z – user – shell_pid=365588 – PASS: radon drops verified (collect_feature_summary 25->B8; _check_lane_gates 19->A<=5; _build_recommended_fix_order 22->A<=5 predicate-table); normalize_feature_encoding C16 is pre-existing/untouched. Characterization 73 green + acceptance 59+98 + 32 new core tests green. Lenient degrade '_status_read_feature_dir status_dir if status_dir.exists() else feature_dir' byte-identical to base; gates read coord read_feature_dir (#2107 preserved). Monkeypatch trap avoided: collect_feature_summary stays in __init__; moved+patched symbols (_check_lane_gates/_build_recommended_fix_order) imported into __init__ and called bare there, no core-internal bypass. Zero seam-module diff (resolution.py/_read_path_resolver.py); __all__ byte-identical, accept.py exports kept, shims bare-import not in __all__. test_no_dead_symbols WorkPackageState removal is ratchet-MANDATED (stale-entry detector forces it; class gained live caller via summary_core->__init__), not scope creep. mypy: same 5 pre-existing findings relocated, zero new; ruff clean.
