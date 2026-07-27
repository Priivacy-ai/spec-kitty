---
work_package_id: WP11
title: task_helpers shadow-module retirement (FR-007)
dependencies:
- WP08
requirement_refs:
- FR-007
- NFR-004
tracker_refs: []
planning_base_branch: feat/single-authority-topology-cleanup
merge_target_branch: feat/single-authority-topology-cleanup
branch_strategy: Planning artifacts for this mission were generated on feat/single-authority-topology-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-authority-topology-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T022
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "1447751"
history:
- Created by /spec-kitty.tasks 2026-06-23
agent_profile: python-pedro
authoritative_surface: src/specify_cli/scripts/tasks/
create_intent:
- tests/specify_cli/scripts/test_task_helpers.py
execution_mode: code_change
owned_files:
- src/specify_cli/scripts/tasks/task_helpers.py
- tests/specify_cli/scripts/test_task_helpers.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt its
directives/tactics (or `/ad-hoc-profile-load python-pedro`). State which you applied.

## Objective
**FR-007** — reduce `src/specify_cli/scripts/tasks/task_helpers.py` (~490 LOC, 20
defs, 17 overlapping with `task_utils/support.py`) to a **thin re-export** of the
canonical `task_utils/support.py`, eliminating the duplicated independent
implementations. Honor the `acceptance_support` compat contract (the public names
that importers rely on must remain importable). Largest single-file LOC reduction.

## Context
- `task_helpers.py` re-implements (not delegates) 18 identically-named functions
  (`load_meta`, `run_git`, `split_frontmatter`, …) that already exist in
  `task_utils/support.py`. After WP09 converts `support.load_meta` to the
  canonical reader, re-exporting it gives task_helpers the canonical behavior free.
- The module is on the dead-module allowlist — keep it importable as a shim, or
  update the allowlist if the import surface changes.

## Subtasks
### T022 — Retire to a thin re-export
Replace the 17 duplicated bodies with `from specify_cli.task_utils.support import (…)`
re-exports (preserve every public name in `__all__` / the `acceptance_support`
contract). Keep any genuinely task_helpers-specific function that has NO support.py
twin (verify by name + signature). Update/keep the dead-module allowlist entry.
Update `test_task_helpers.py` to assert the re-export surface (each public name
resolves to the support.py implementation) rather than re-testing duplicated logic.

## Campsite (#1970)
Remove dead imports; fix lint/type debt; if the allowlist entry is now stale,
update it with rationale.

## Test approach (doctrine standard)

> **Test approach (doctrine standard — DIRECTIVE_034/036/041, #2071 CTn).** Assert the **observable contract** — returned value, resolved surface/ref, persisted JSONL/`meta.json`, CLI `--json` payload, or gate verdict — **never** the internal call graph or "collaborator X was invoked" (CT4/D036). Build mission fixtures by delegating to the **production creation seam** (`create_mission_core` / the existing `_stored_topology` helper), not a hand-rolled `meta.json` writer that rots (CT3); use **production-shaped data** — a real 26-char ULID + 8-char mid8, never a short placeholder (testing-principles). Any architectural guard/ratchet anchors keys on `_ratchet_keys.composite_key` (qualname + token-line) or an AST node — **never `file.py:NNN`** — and reuses `audit.py`/`_ratchet_keys.py` (CT1); resolve symbols by AST, never by grepping a string that collides with a surviving flag (NFR-003). Any xfail/skip is a **RED-by-design ATDD pin that names the WP that drains it** and is removed (not re-keyed) when the fix lands — never a defect mask (CT2). Prove behavior-neutrality via the **differential cell over the `(topology × transient)` matrix** PLUS at least one **absolute** assertion (see below) — never a brittle golden count of sites/LOC/refs (CT5); prefer a **tightening ratchet** (count only drops, keyed by symbol-set) over a fixed `== N`. **Pair every "allow / passes / absorbs / ignores-residue" assertion with its negative control** ("still-blocks / still-raises / wrong-topology-differs") — one-sided gate tests let the over-allow mutant survive. When a touched test goes red, classify it (stale→re-point preserving setup / fakeable→delete / valid→fix the product) and establish causation by **code-path coupling, not git-blame** (D041).

### WP11-specific test-DoD
- **Behavioral result-equality, not identity.** Replace identity assertions (`task_helpers.load_meta is support.load_meta`) with **behavioral result-equality** for the hot helpers (`load_meta`, `run_git`, `split_frontmatter`): call each with a representative input and assert the result `==` the canonical `support.py` result. Identity can pass while behavior silently diverges through a wrapper.
- **Public-surface set-equality guard.** Add a guard asserting **set-equality** of the re-exported names against the required `acceptance_support` compat set — NOT `len(__all__) == N` (CT5; a count passes even if a name was swapped).

## Definition of Done
- task_helpers.py is a thin re-export; the 17 duplicate bodies gone; every
  `acceptance_support` public name still importable; tests assert the re-export via
  **behavioral result-equality** (not `is`-identity) for the hot helpers and a
  **set-equality** public-surface guard (not `len(__all__)`).
  `ruff`/`mypy` clean; full `tests/` green. Net LOC down ~300-450.

## Branch Strategy
`feat/single-authority-topology-cleanup`. Lane D (after WP08). Worktree from `lanes.json`.

## Reviewer guidance
Confirm every previously-public name still imports (compat contract). Confirm no
behavior change for importers. Reject if a task_helpers-only function was dropped.

## Activity Log

- 2026-06-23T07:55:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Assigned agent via action command
- 2026-06-23T08:04:54Z – claude:sonnet:python-pedro:implementer – shell_pid=1366956 – Ready: task_helpers → thin re-export; acceptance_support compat names preserved + tested
- 2026-06-23T08:06:18Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=1447751 – Started review via action command
- 2026-06-23T08:14:47Z – user – shell_pid=1447751 – Review passed: thin re-export confirmed (88 LOC from 481); all 22 acceptance_support names present in __all__ verified against each importer (tasks_cli.py, tests/utils.py, test_task_helpers.py, test_tasks_cli_commands.py, test_acceptance_support.py); behavioral result-equality tests green with real inputs; public-surface guard is set-equality not count; path_has_changes retained with positive+negative controls; dead-modules Cat-3 allowlist intact; ruff+mypy clean; 1 pre-existing failing test on base branch.
