---
work_package_id: WP07
title: Charter authority-path flip — the full ADR-recorded chain (FR-011)
dependencies: []
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
created_at: '2026-06-12T18:32:00Z'
subtasks:
- T023
- T024
- T025
- T026
phase: Phase 1 - Independent lanes
assignee: ''
agent: ''
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
