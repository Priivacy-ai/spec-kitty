---
work_package_id: WP01
title: Characterization-first safety net
dependencies: []
requirement_refs:
- FR-006
- FR-008
tracker_refs: []
planning_base_branch: feat/coord-authority-trio-degod
merge_target_branch: feat/coord-authority-trio-degod
branch_strategy: Planning artifacts for this mission were generated on feat/coord-authority-trio-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/coord-authority-trio-degod unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Gate
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "233268"
history:
- timestamp: '2026-07-11T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/characterization/
create_intent:
- tests/characterization/_normalize.py
- tests/characterization/test_trio_pure_cores.py
- tests/characterization/test_trio_json_envelope.py
- tests/characterization/test_trio_transitions.py
execution_mode: code_change
mission_id: 01KX7094EYXKC6EJZC9XZCADS3
model: claude-sonnet-5
owned_files:
- tests/characterization/**
role: implementer
tags: []
wp_code: WP01
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP01 – Characterization-first safety net (GATES EVERYTHING)

## Objective
FR-008. Pin the trio's CURRENT behaviour BEFORE any structure moves — the ONLY defence against a false-green refactor. Authored against untouched `main`-state trio; must pass now. WP02/03/04 depend on this.

## Context (squad LAND-BLOCKER — pin the actual monsters, not just easy helpers)
The hazardous targets are the functions being SPLIT (not moved verbatim): `_resolve_review_context`(CC37), `collect_feature_summary`(CC25), `_build_recommended_fix_order`(CC22), `_check_lane_gates`(CC19). These are pure/deterministic TODAY → pin them DIRECTLY with a branch-coverage matrix (every terminal/blocked/for_review/approved combo into gates; every rejection/rewind/resume path into review-context). The CLI-envelope (T003) + reducer (T004) layers only prove the scenarios you pick — internal branches never hit by chosen scenarios can silently change (false-green). Direct pure-core pinning is the strong net.
Not-deterministic outputs (git SHAs, timestamps, worktree ids, paths) MUST be normalized (`_normalize.py`).

## Subtasks
- **T001** Scaffold `tests/characterization/` + `_normalize.py` (normalize SHA/ISO-ts/abs-path/pid/worktree-id → stable tokens). Each file gets its own `pytestmark`.
- **T002** DIRECT in→out pure-core characterization (`test_trio_pure_cores.py`, `pytestmark=[pytest.mark.unit]`) of the CC19-37 split targets + the already-clean helpers, WITH a branch-coverage matrix exercising every branch of `_check_lane_gates`/`collect_feature_summary`/`_resolve_review_context`.
- **T003** JSON-envelope characterization (`test_trio_json_envelope.py`, `pytestmark=[pytest.mark.integration, pytest.mark.git_repo]`) for ALL 4 surfaces: `agent action implement`, `agent action review`, `spec-kitty implement`, `spec-kitty accept` in `--json` via CliRunner; assert the normalized envelope; coord-topology AND flat fixtures.
- **T004** Status-reducer transition characterization (`test_trio_transitions.py`, `pytestmark=[pytest.mark.unit]`) over the `next`/decision loop incl. rejection/rewind/resume; explicitly pin the not-exists DEGRADE path of the lenient status reads (status_dir absent → falls back to feature_dir, does NOT raise).
- **T005** Prove GREEN on pre-refactor code. Write the WP01 DoD reviewer checklist enumerating exactly which behaviours are pinned per surface (lenient degrade, rejection/rewind/resume, the #2508 pre-fix path) so review can't rubber-stamp a shallow suite.

## Shared discipline (squad-hardened)
- **Complexity gate**: Sonar S3776 ≤15 is the gate of record; ruff C901 is BLIND. Local pre-flight = `uvx radon cc -s -n B <file>` (reproduces the cited CC numbers). Actual Sonar is NOT run on PRs — confirm via manual `gh workflow run ci-quality.yml --ref feat/coord-authority-trio-degod` (the branch-review script lacks a --branch flag — WP05 tracks that gap).
- **Shims (FR-009)**: add re-export shims as bare `from <cores/executor> import <name>` — do NOT add shimmed names to `__all__` (workflow.py has none; keep it that way; implement.py __all__ stays its 4 names; acceptance keeps only its 2 accept.py-consumed exports). A public shim needs an allowlist entry in `test_no_dead_symbols.py` with the #2057 rationale, never a silent __all__ add.
- **Read contracts (corrected)**: the trio uses the LENIENT projection (`resolve_handle_to_read_path`, `require_exists=False`) + acceptance-specific existence-degrade. There is NO `require_exists=True` fail-closed site in the trio — do NOT introduce one. Keep every currently-lenient read lenient.
- **C-004 tripwire**: ZERO diff to the shared seam modules `mission_runtime/resolution.py` / `missions/_read_path_resolver.py`; a missing seam capability is ESCALATED, not patched in place.
- **Markers**: every new test file needs its own `pytestmark` (unit for pure-core tests; integration+git_repo for CliRunner/git tests; architectural for arch tests).
- Verify the real monkeypatch/test-file count with a fresh grep before relying on the planning-time figure.
## Branch Strategy
Planning/base = merge target = `feat/coord-authority-trio-degod`. `spec-kitty agent action implement WP01 --agent <name>` (no deps).

## Definition of Done
- [ ] Suite green on pre-refactor code; the CC19-37 split targets pinned DIRECTLY with a branch-coverage matrix; lenient not-exists degrade pinned.
- [ ] All 4 CLI surfaces covered (coord + flat); per-file markers correct; reviewer checklist of pinned behaviours present; ruff+mypy clean.

## Activity Log

- 2026-07-11T05:59:22Z – claude:sonnet:python-pedro:implementer – shell_pid=128230 – Assigned agent via action command
- 2026-07-11T06:54:09Z – claude:sonnet:python-pedro:implementer – shell_pid=128230 – T001-T005 done: 73 tests green (57 pure-core + 8 transitions + 8 CLI-envelope) across 4 new files under tests/characterization/. Pins CC19-37 targets (_check_lane_gates, _resolve_review_context, _build_recommended_fix_order, collect_feature_summary) with direct branch-coverage matrices via mocked collaborators (no real git/subprocess in unit files). Pins the lenient not-exists DEGRADE contract of acceptance._status_read_feature_dir vs the non-degrading workflow._canonical_status_feature_dir. Pins rejection/rewind/resume via _resolve_review_feedback_context/_has_prior_rejection using the real status package + canonical review-cycle writer. JSON-envelope suite covers all 4 CLI surfaces (accept --json --diagnose, implement --recover --json, agent action implement, agent action review) on flat AND coord-topology fixtures via real git repos + CliRunner. GAP filed (not silently worked around): agent action implement/review have no --json flag today (pinned as normalized TEXT instead); a coord-materialized agent action review with no prior implement claim crashes with a raw FileNotFoundError (pinned as the current, deterministic behaviour, flagged for a follow-up defect). ruff+mypy clean on new files; zero src/ changes; confirmed GREEN on pre-refactor code.
- 2026-07-11T06:55:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=233268 – Started review via action command
- 2026-07-11T07:01:46Z – user – shell_pid=233268 – PASS. Diff = ONLY tests/characterization/** (4 files, 2080 LOC); zero src/ + zero frozen-seam (resolution.py/_read_path_resolver.py) diff. 73/73 green via uv run on pre-refactor code. CC19-37 split targets pinned DIRECTLY with real branch matrices asserting OUTPUT (not vacuous wiring): _build_recommended_fix_order (each trigger->exact string + fixed source order), _check_lane_gates CC19 (corrupt/missing/mismatch/off-branch/detached/planning-only/missing-matrix/mutate-vs-diagnose/evidence/verdict), _resolve_review_context CC37 (default/repo-root/lanes-manifest/workspace-ctx/dependency/well-known base_ref discovery + partial-fill), collect_feature_summary CC25 (strict metadata gate incl #2369 terminal exemption + coord-vs-primary routing + fix-order kwarg wiring). Lenient not-exists degrade pinned BOTH sides (acceptance degrades to feature_dir no-raise; workflow returns nonexistent path no-fallback). Normalization targeted not payload-to-constant. Gaps verified real: implement/review have no --json typer option; coord-review-without-claim raw FileNotFoundError pinned as current behaviour, both flagged for tickets. Markers correct; marker arch gates 4/4 green; ruff clean; mypy clean on new files. Filled issue-matrix verdicts to in-mission (WP01 pins pre-refactor behaviour; #s owned by WP02-05, terminal before mission done).
