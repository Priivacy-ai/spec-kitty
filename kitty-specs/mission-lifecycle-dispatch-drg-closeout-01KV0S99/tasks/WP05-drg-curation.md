---
work_package_id: WP05
title: 'DRG curation: stale-ref repair + orphan triage + deterministic regen + #1863 closure'
dependencies: []
requirement_refs:
- C-003
- FR-008
- FR-009
- NFR-002
- NFR-003
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2835611"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/styleguides/built-in/**
- src/doctrine/graph.yaml
- src/doctrine/tactics/built-in/**
- src/doctrine/toolguides/built-in/**
- src/doctrine/procedures/built-in/**
- tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – DRG curation

## ⚡ Do This First: Load Agent Profile

Load your assigned implementer profile (recommended `python-pedro`) via the profile-load skill —
governed context, not a bare name — before reading further.

## Objectives & Success Criteria

Repair the stale java-implementer reference, triage orphans without destroying valid doctrine,
regenerate deterministically, pin the reduced count, and close #1863.

- `java-conventions.styleguide.yaml` references a REAL profile (`java-jenny`), no phantom
  `agent_profile:java-implementer` node after regen; same-class stale refs swept + repaired.
- Orphan count reduced by **wiring real inbound edges**; remaining orphaned-but-valid artifacts
  **documented** with per-orphan rationale (+ follow-up ticket if non-empty). **No bulk-delete.**
- `graph.yaml` regenerated deterministically (already no-op-stable); reduced orphan count pinned.

## Context & Constraints

- Read: `plan.md` (IC-08, IC-09, IC-10), `contracts/drg-curation.md` (binding), `research.md`
  (Workstream C, **D-C2 the no-bulk-delete correction**), `spec.md` (FR-008/FR-009 reworded), quickstart §C.
- **CRITICAL (D-C2 / C-003):** an orphan that is a valid, deliberately-authored doctrine artifact
  (Fowler refactoring tactics, mutation-testing toolguides, ZOMBIES TDD, REASONS/skill-authoring
  styleguides, etc.) is unreferenced, NOT a defect. Do **NOT** delete it to shrink a metric. Wire a
  real inbound edge if a natural referent exists, else document it as an accepted residual. Prune
  only genuinely-retired artifacts, each individually justified — never bulk.
- **Sweep predicate (precise):** a `references:` path whose pattern matches a doctrine kind AND whose
  target file is **absent on disk** (the extractor mints a phantom node for exactly these). Do not
  repaint live references.
- Regen via `spec-kitty doctrine regenerate-graph`; emit is ALREADY deterministic (sorted nodes/edges,
  `generated_at="STATIC"`) — pin it, do not re-architect it (NFR-003).
- **Ownership:** do NOT touch `src/doctrine/skills/spec-kitty.advise/**` (WP04 owns it).

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T018 – ATDD: orphan-count regression test first
- Add a test (in `test_doctrine_regenerate_graph.py` or a sibling) that loads `graph.yaml`, computes
  orphans (no inbound/outbound edge), and asserts the count `<=` the documented residual. Confirm the
  existing freshness `--check` and byte-identical-twice tests stay green.

### T019 – Stale-reference repair
- Repaint `src/doctrine/styleguides/built-in/java-conventions.styleguide.yaml` `references`:
  `java-implementer.agent.yaml` → `java-jenny.agent.yaml` (real, exists, specializes_from
  implementer-ivan). Sweep all `references:` across doctrine for the same-class predicate (pattern
  matches kind AND target file absent); repair to a real target or prune the *reference* (never the
  target artifact). Record a one-line rationale per fix.

### T020 – Orphan triage: wire where natural
- For each genuinely-orphaned valid artifact, wire a real inbound edge when a natural referent exists
  (e.g. cite a refactoring tactic from the refactoring procedure / a coding directive). Add the edge
  via the SOURCE doctrine YAML `references`/relation, not by hand-editing graph.yaml.

### T021 – Document residual + follow-up
- List remaining orphaned-but-valid artifacts with a per-orphan rationale (in-mission doc, e.g. a
  `drg-orphan-residual.md` under the mission dir or a section in research.md). If the residual set is
  non-empty, file a curation follow-up ticket before #1863 closes (C-003).

### T022 – Deterministic regen
- Run `spec-kitty doctrine regenerate-graph`; confirm `--check` exits 0 and regenerating twice is
  byte-identical. The phantom `java-implementer` node must be gone.

### T023 – #1863 closure
- Prepare the issue-matrix #1863 row for a terminal verdict at accept (orchestrator finalizes at the
  merge gate). Ensure the residual is documented (never silently accepted).

## Test Strategy

- `pytest tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` (incl. new orphan-count
  test) green. Run the terminology guard (doctrine prose). Diff-scoped ruff/mypy on any touched
  `.py`. Paste commands + exit codes into handoff.

## Definition of Done

- Stale ref(s) repaired; orphans wired-or-documented (zero bulk-deletes of valid doctrine); residual
  documented (+ follow-up if non-empty); graph regen deterministic + orphan-count test green; #1863
  closure readiness recorded.

## Risks

- **Content destruction** — bulk-deleting valid orphans (prohibited). Repainting a live reference by
  mis-applying the sweep. Hand-editing graph.yaml instead of regenerating. Re-architecting the
  already-deterministic emit.

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Verify NO valid doctrine artifact was deleted to shrink the count
  (wire-or-document only), the sweep matched only pattern+absent refs, regen is deterministic, and the
  residual is documented with rationale.

## Activity Log

- 2026-06-13T16:57:35Z – claude:opus:python-pedro:implementer – shell_pid=2767258 – Assigned agent via action command
- 2026-06-13T17:10:50Z – user – shell_pid=2767258 – WP05 transition to claimed (implementation complete, see prior for_review note)
- 2026-06-13T17:10:51Z – user – shell_pid=2767258 – WP05 transition to in_progress (implementation complete, see prior for_review note)
- 2026-06-13T17:12:54Z – claude:opus:python-pedro:implementer – shell_pid=2767258 – Ready: orphans 26->14. Wired 12 (9 Fowler refactoring tactics via refactoring.procedure references + mutation-testing-workflow tactic + python/typescript mutation toolguides). 14 valid residual orphans DOCUMENTED with per-orphan rationale (content at /tmp/drg-orphan-residual.md; lane-branch kitty-specs guard blocks committing it on the lane - orchestrator/reviewer must place drg-orphan-residual.md on coordination branch feat/mission-lifecycle-dispatch-drg-closeout; follow-up curation ticket REQUIRED per C-003). java-implementer phantom node removed; 5 stale styleguide refs repaired. regenerate-graph --check exit 0, twice byte-identical. 5/5 graph tests + terminology guard + 122 DRG tests green. ruff+mypy clean. ZERO valid artifacts deleted (D-C2). NOTE: forced due to lane status desync (#1589) - canonical planning-branch status was in_progress.
- 2026-06-13T17:14:55Z – claude:opus:python-pedro:implementer – shell_pid=2767258 – Ready: orphans 26→14 (12 wired, 0 deleted), java-implementer→java-jenny +4 same-class refs, deterministic regen --check exit 0, residual doc on planning branch; curation follow-up ticket due at #1863 close (C-003)
- 2026-06-13T17:15:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=2835611 – Started review via action command
- 2026-06-13T17:21:56Z – user – shell_pid=2835611 – Review PASS (renata): no-bulk-delete confirmed, 12 genuine wirings, deterministic regen, residual doc complete
