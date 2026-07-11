---
work_package_id: WP05
title: Seam-only arch gate + closeout
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-004
- FR-007
tracker_refs: []
planning_base_branch: feat/coord-authority-trio-degod
merge_target_branch: feat/coord-authority-trio-degod
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-trio-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-trio-degod unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 3 - Gate + closeout
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "926514"
history:
- timestamp: '2026-07-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_trio_seam_only.py
execution_mode: code_change
mission_id: 01KX7094EYXKC6EJZC9XZCADS3
model: claude-sonnet-5
owned_files:
- tests/architectural/test_single_mission_surface_resolver.py
- tests/architectural/test_trio_seam_only.py
role: implementer
tags: []
wp_code: WP05
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP05 – Seam-only arch gate + closeout

## Objective
FR-004/FR-007/SC-002. Pin trio seam-only consumption + cores-pure (no-I/O), verify the read contracts survived, run the full closeout gate.

## Subtasks
- **T027** Extend `test_single_mission_surface_resolver.py` (do NOT weaken it for non-trio callers) + add `test_trio_seam_only.py` (`pytestmark=[pytest.mark.architectural]`): AST import-scan that workflow.py/implement.py/acceptance + their cores/executors import ONLY the seam wrappers, never other leaf primitives. Non-vacuous: a planted leaf-primitive import in the trio FAILS the test.
- **T028** FR-007 arch test in `test_trio_seam_only.py`: the extracted pure cores perform NO I/O — use the repo's AST `FUNCTIONAL_FS_BYPASS` vs `DIAGNOSTIC_PAYLOAD` classification pattern (see the sibling resolver test), banning `open`, `Path.read_text/write_text/read_bytes/write_bytes`, `subprocess.*`, `os.system`, `sqlite3`, network. Non-vacuous self-check: plant a REAL I/O call in a fake core → the test catches it (not just a planted import).
- **T029** Closeout gate: `uv run pytest tests/ -q` + `tests/characterization/` + `tests/architectural/` green; ruff + mypy zero; `uvx radon cc -s -n B` on the trio's touched functions ≤ (B = CC≤10, comfortably under S3776 15) + a manual Sonar confirmation (`gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod`); `rg "noqa: C901"` across the trio → zero; verify FR-009 shims keep all trio tests green. FILE a follow-up: `scripts/ci/sonarcloud_branch_review.sh` needs a `--branch` flag (currently reads default branch only).
- **T030** Verify the 3 read contracts intact — grep that no lenient site was flipped to fail-close and no fail-close was introduced in the trio. Assess the 3 tracer files; note residuals for the retrospective.

## Shared discipline (squad-hardened)
- **Complexity gate**: Sonar S3776 ≤15 is the gate of record; ruff C901 is BLIND. Local pre-flight = `uvx radon cc -s -n B <file>`. Sonar is NOT run on PRs — confirm via manual `gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod`.
- **Shims (FR-009)**: bare `from <cores/executor> import <name>`, NOT in `__all__` (implement.py __all__ stays its 4 names; acceptance keeps only its 2 accept.py-consumed exports). Public shim → allowlist in `test_no_dead_symbols.py` (#2057 rationale), never a silent __all__ add.
- **Read contracts**: the trio is LENIENT (`resolve_handle_to_read_path` require_exists=False) + acceptance existence-degrade. NO fail-closed site in the trio — do not introduce one.
- **C-004 tripwire**: ZERO diff to `mission_runtime/resolution.py` / `missions/_read_path_resolver.py`; missing seam capability → ESCALATE.
- **Markers**: per-file `pytestmark` (unit / integration+git_repo / architectural).
- Verify the real test-file count with a fresh grep before trusting the estimate.
## Branch Strategy
`spec-kitty agent action implement WP05 --agent <name>` (deps WP02, WP03, WP04).

## Definition of Done
- [ ] Trio seam-only arch pin + cores-no-I/O AST pin, both non-vacuous (plant-and-catch); 3 read contracts verified unflipped.
- [ ] Full suite + characterization + arch + ruff + mypy + radon ≤ ceiling + manual Sonar confirmation green; zero trio noqa:C901; Sonar-script --branch gap filed; tracers assessed.

## Activity Log

- 2026-07-11T08:43:34Z – claude:sonnet:python-pedro:implementer – shell_pid=564964 – Assigned agent via action command
- 2026-07-11T09:56:23Z – claude:sonnet:python-pedro:implementer – shell_pid=564964 – closeout: arch gates + WP01 char fixes; local arch 47 passed
- 2026-07-11T09:56:55Z – claude:opus:reviewer-renata:reviewer – shell_pid=828716 – Started review via action command
- 2026-07-11T10:09:38Z – user – shell_pid=828716 – Moved to planned
- 2026-07-11T10:10:29Z – claude:sonnet:python-pedro:implementer – shell_pid=854187 – Started implementation via action command
- 2026-07-11T11:05:21Z – claude:sonnet:python-pedro:implementer – shell_pid=854187 – cycle-1: reconciled untrusted_path_audit inventory (4 new workflow_cores/executor sinks + 2 re-anchored ghost rows); tests/architectural/ 869 passed 0-failed; arch gates unchanged (non-vacuous)
- 2026-07-11T11:05:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=926514 – Started review via action command
