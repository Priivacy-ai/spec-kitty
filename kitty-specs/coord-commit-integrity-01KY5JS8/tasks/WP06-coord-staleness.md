---
work_package_id: WP06
title: Coord staleness signal + safe resync
dependencies: []
requirement_refs:
- FR-008
- FR-009
planning_base_branch: remediation/coord-trust-2841
merge_target_branch: remediation/coord-trust-2841
branch_strategy: Planning artifacts for this mission were generated on remediation/coord-trust-2841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/coord-trust-2841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-coord-commit-integrity-01KY5JS8
base_commit: cd9ac00a4958de49fab50b6a8ce21b41f8abdcc0
created_at: '2026-07-22T21:00:28.475988+00:00'
subtasks:
- T014
history:
- at: '2026-07-22T19:33:57Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/coordination/test_coord_staleness.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/_coordination_doctor.py
- tests/coordination/test_coord_staleness.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

(Or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml`.) Adopt its directives/tactics; state which you applied.

## Objective

Surface coord-vs-target staleness non-blockingly and offer a safe fast-forward only when unambiguously safe
(Gap-1, the only irreducible residual). Read `research.md` (Decision E context + Gap-1), `contracts/gate-and-doctor-contracts.md`
(Coord staleness), C-003/C-005. **File is `src/specify_cli/cli/commands/_coordination_doctor.py`** (NOT
`coordination/` — the plan's earlier path was wrong).

## Branch Strategy

Planning base + merge target **`remediation/coord-trust-2841`** (coord). Lane e (parallel). Worktree per lane.

## Subtasks

### T014 — FR-008 staleness detector + doctor mode; FR-009 safe fast-forward

- **FR-008**: add `_coord_branch_stale_vs_target_finding()` comparing the coord branch tip vs `target_branch`
  (reuse the `merge-base --is-ancestor` plumbing `_is_ancestor`/`_coord_worktree_stale_finding:~338` already
  use): strict-ancestor → stale-fast-forwardable (non-blocking); diverged → warn/fail-loud. Surface via a new
  `spec-kitty doctor coordination --check-staleness` mode + a non-blocking WARN woven into `finalize-tasks`
  The finalize entry point is `tasks.py:~1007 finalize_tasks` (pedro) — in NO WP's owned_files, so this is a
  DECLARED, rationale-recorded out-of-map one-liner (locality, DIRECTIVE_024): it calls the detector, must not
  block, reviewed as such (not a silent drive-by).
- **FR-009**: `doctor coordination --fix` fast-forwards the coord branch ONLY when it is a strict ancestor of
  target AND the coord worktree is clean; otherwise fail loud with a unified diff and mutate nothing.
- **C-003 (binding):** keep `--fix` MINIMIZED — it does the Gap-1 fast-forward only. Do NOT grow it into a
  general "repair arbitrary drifted content" command.
- **Campsite:** extract `_fast_forward_finding(...)`/`_is_ff_candidate(...)` from the near-dup
  `_coord_worktree_stale_finding:~312-359` (C-005 warn-first falls out for free — the predicate returns a
  finding, never mutates); hoist the 7× function-local `import subprocess`; extract `_resolve_coord_short(meta)`.

`tests/coordination/test_coord_staleness.py`: (a) strict-ancestor → `--check-staleness` reports stale + `--fix`
fast-forwards (clean worktree); (b) diverged → `--fix` fails loud with a diff, mutates nothing; (c) dirty
worktree → `--fix` fails loud. **(renata) On (b)/(c) assert `git rev-parse <coord_branch>` is byte-identical
before and after the failed `--fix` (proves zero mutation), in addition to the non-zero exit + diff. Add (d):
run `finalize-tasks` on a stale-coord mission and assert both that the staleness WARN is surfaced AND that
`finalize-tasks` still exits 0 (non-blocking).** Use the real-git coord fixture.

## Definition of Done

- [ ] `doctor coordination --check-staleness` reports coord-vs-target staleness non-blockingly; `finalize-tasks` prints a non-blocking WARN.
- [ ] `--fix` fast-forwards ONLY when strict-ancestor AND coord worktree clean; else fails loud with a unified diff, mutating nothing.
- [ ] `--fix` stays minimized (no general repair); C-005 warn-first, never silent mutation.
- [ ] Campsite: `_fast_forward_finding`/`_is_ff_candidate`/`_resolve_coord_short` extracted; subprocess import hoisted.
- [ ] `uv run --extra test ruff check` + `mypy` clean; complexity ≤15 (`run_coordination_health`/`_check_coordination_worktree_health` stay <15 via sub-helpers); `uv run --extra test pytest tests/coordination -q` green.

## Reviewer guidance

Verify `--fix` never mutates on divergence/dirty (fails loud with diff — the data-loss-sensitive decision);
`--fix` stays minimized (C-003 — no general repair); the staleness compares coord vs TARGET (not coord-worktree
vs its own coord branch, which the existing `_coord_worktree_stale_finding` already does).

## Risks

- Growing `--fix` into a general repair command (C-003 forbids).
- Auto-mutating on divergence/dirty (C-005 forbids — fail loud with diff).
