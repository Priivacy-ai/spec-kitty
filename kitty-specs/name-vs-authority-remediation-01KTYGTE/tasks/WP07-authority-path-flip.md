---
work_package_id: WP07
title: Charter authority-path flip — the full ADR-recorded chain (FR-011)
dependencies: []
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: feat/name-vs-authority-remediation-01KTYGTE
merge_target_branch: feat/name-vs-authority-remediation-01KTYGTE
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC (mission retargeted to feat/name-vs-authority-remediation-01KTYGTE on 2026-06-12 — PR #1895 branch frozen for review). During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/name-vs-authority-remediation-01KTYGTE unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T023
- T024
- T025
- T026
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1551027"
history:
- at: '2026-06-12T18:32:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/charter/context_renderers/
execution_mode: code_change
model: ''
owned_files:
- src/charter/context_renderers/authority_paths.py
- src/doctrine/missions/mission-steps/software-dev/implement/prompt.md
- src/doctrine/missions/mission-steps/software-dev/review/prompt.md
- tests/charter/**
- tests/specify_cli/regression/**
- .kittify/charter/charter.md
- architecture/3.x/adr/2026-06-11-1-*.md
- .claude/commands/**
- .github/prompts/**
- .gemini/commands/**
- .cursor/commands/**
- .qwen/commands/**
- .opencode/command/**
- .windsurf/workflows/**
- .kilocode/workflows/**
- .augment/commands/**
- .roo/commands/**
- .amazonq/prompts/**
- .kiro/prompts/**
- .agent/workflows/**
- .agents/skills/**
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Authority-path flip (complete chain, ONE WP)

## ⚡ Do This First: Load Agent Profile
Load the assigned profile via `spec-kitty agent profile show <profile-id> --all` (pick the best implementer match if none assigned) and operate within its boundaries before reading further.

---
## Objectives & Success Criteria
Execute the procedure recorded in the ADR's deferral section (`architecture/3.x/adr/2026-06-11-1-...md`) — verified ZERO-DRIFT in `research/research-fold-cluster.md` §2. ALL links land together or none:
- **T023:** flip `authority_paths.py` default `architecture/2.x/adr/` → `architecture/3.x/adr/` (+docstrings); update BOTH source prompts (`mission-steps/software-dev/{implement,review}/prompt.md`); update `.kittify/charter/charter.md:317` annotation (2.x historical note moves accordingly).
- **T024:** update the 2 governance-contract tests + the 3 `tests/charter/` assertions to the 3.x path.
- **T025:** regenerate the agent command copies via the documented flow, then `PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v` and COMMIT the regenerated twelve-agent parity baselines WITH the template change (one atomic commit for the whole chain is acceptable).
- **T026:** append (append-only!) an "executed" addendum to the ADR's deferral section, dated, referencing this WP; `python -m pytest tests/architectural/ -q` FULLY green.

## Context & Constraints (read before coding)
- Design (absolute): `kitty-specs/name-vs-authority-remediation-01KTYGTE/{spec.md, plan.md, data-model.md, contracts/authority-seams.md}` + the mission `research/` — **`research-authority-seams.md` is NORMATIVE** for seam APIs/site lists/decision table; `research-p0-rootcauses.md` for defect mechanics; `research-fold-cluster.md` for ready deltas.
- NFR-003 binding: fail-closed over fallback — never introduce a silent name-derived fallback.
- ATDD: pinning/contract tests FIRST where the WP names them. New code: ruff + mypy zero issues, zero suppressions. No existing passing test modified (NFR-001; pin-of-defective-behavior exceptions justified per case).
- C-002: in `coordination/status_transition.py` and `cli/commands/merge.py`, touch ONLY the ranges this WP names — upstream coord-merge-stabilization owns adjacent ranges.
- move-task/mark-status: run from the PRIMARY checkout with the FULL mission slug (`name-vs-authority-remediation-01KTYGTE`). No kitty-specs commits on the lane.

## Definition of Done
All 7 chain links flipped together; parity suite green with new baselines; full architectural green; ADR records execution; no 2.x-pointing authority default remains.

## Review Guidance
reviewer-renata. The review IS the chain-completeness check: grep for any surviving `2.x/adr` authority default; verify baselines changed WITH templates (not independently); ADR addendum append-only.

## Activity Log
- 2026-06-12T18:32:00Z – system – Prompt created.
- 2026-06-12T19:23:17Z – claude:sonnet:python-pedro:implementer – shell_pid=1470114 – Assigned agent via action command
- 2026-06-12T19:33:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1470114 – WP07 complete — all 7 chain links flipped atomically. Chain-link checklist: [1-DONE] authority_paths.py DEFAULT flipped 2.x→3.x + docstrings updated. [2-DONE] implement/prompt.md + review/prompt.md updated. [3-DONE] parity baselines regenerated (26 files, 13 agents × implement+review, no unrelated churn). [4-DONE] 2 governance-contract tests updated (test_template_governance_payload_contract.py + test_wp_prompt_governance_contract.py incl. self-sufficiency regex). [5-DONE] 3 tests/charter/ assertions updated (test_context_authority_paths.py, test_sync_authority_paths.py, test_schemas_additive_fields.py). [6-DONE] .kittify/charter/charter.md:317 annotation updated to 3.x. [7-DONE] ADR deferral section append-only EXECUTED addendum added dated 2026-06-12. pytest tests/architectural/: 350 passed, 0 failed.
- 2026-06-12T19:34:24Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1551027 – Started review via action command
- 2026-06-12T19:41:09Z – user – shell_pid=1551027 – Review passed: all 7 chain links verified present and correct; parity baselines contain only 2.x->3.x path change (no unrelated churn); no agent dirs hand-edited; ADR append-only (zero deleted lines); DEFAULT_AUTHORITY_PATHS live-imports as 3.x only; self-sufficiency regex [23].x acceptable while adr_path_present on line 663 pins the actual contract to 3.x specifically; 350 architectural + 1585 charter/regression tests pass; terminology guard clean; C-002 clean.
