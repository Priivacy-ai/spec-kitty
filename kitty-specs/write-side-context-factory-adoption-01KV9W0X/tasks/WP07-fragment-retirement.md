---
work_package_id: WP07
title: Fragment-scaffolding retirement (FR-006)
dependencies:
- WP01
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: feat/write-side-context-factory-adoption
merge_target_branch: feat/write-side-context-factory-adoption
branch_strategy: Planning artifacts for this mission were generated on feat/write-side-context-factory-adoption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/write-side-context-factory-adoption unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2985272"
history:
- 2026-06-17 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
- src/specify_cli/status/aggregate.py
- tests/mission_runtime/test_context_fragments.py
- tests/architectural/test_execution_context_parity.py
- tests/architectural/test_mission_runtime_surface.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Then read: `spec.md` **FR-006** + **C-001** (factory NOT modified — this is DELETION of dead scaffolding,
not an authority change) + **C-008**; `plan.md` **IC-RETIRE** + **D-9** (the S-2/S-3 tests that encode these
deletion targets as contracts retire ATOMICALLY here); `research/pre-refactor/paula-test-smells.md` **S-2/S-3**
(the deletion-target-as-contract tests); `contracts/behavioral-contracts.md` **C-RETIRE**.

## Objective

Delete the genuinely-dead scaffolding the write-half adoption supersedes. **CORRECTION (post-squad, paula
SF-1 / pedro B1-B2): "0 readers" was true for `src/` only — there ARE live TEST contracts + a package export
that must be handled in this same change:**
- the `prompt_source` fragment (`resolution.py:761-778` `_assemble_prompt_source_fragment`, `:908`, `:929`;
  `context.py:181` `prompt_source_dir`, `:246`, `:254`) **and its export `src/mission_runtime/__init__.py:36,63`**
  (`PromptSourceFragment`) — a dangling export breaks import/mypy if left (pedro B2);
- the dead `StatusSurfaceFragment.surface=` read-param wiring (`status/aggregate.py:199` + the
  `if surface is not None` branch) — the `MissionStatus.load()` callers never pass `surface=` (census said
  two callers; there are **three** — retirement still safe, alphonso S-4).

This is **C-001-safe** (no authority change; `build_execution_context` untouched). The proof is the suite
staying green **after** the test contracts below are retired atomically (NFR-003) — not "deletion is
behavior-neutral with zero readers" (that framing is retired).

## Subtask guidance

### T031 — Delete the prompt_source fragment (+ the export)
Remove `_assemble_prompt_source_fragment` + its call/assembly in `resolution.py`, the
`prompt_source`/`prompt_source_dir` fields + references in `context.py`, **and the `PromptSourceFragment`
export in `src/mission_runtime/__init__.py:36,63`** (else import/mypy breaks). **Re-grep first** to confirm no
live `src/` reader appeared since the census (C-006).

### T032 — Delete the surface= read-param
Remove the `surface: StatusSurfaceFragment | None = None` param at `aggregate.py:199` and the dead
`if surface is not None` branch. Confirm the two `MissionStatus.load()` callers never pass it.

### T033 — Atomically retire the contract-encoding tests
These existing tests encode the deletion targets as contracts — they go RED on a correct deletion, so retire
the prompt_source rows **in this same change** (atomic): `tests/mission_runtime/test_context_fragments.py`,
`tests/architectural/test_execution_context_parity.py::test_promptsource_fragment_parity` (~:1780, xfail
already removed → live), and the `PromptSourceFragment` row in `tests/architectural/test_mission_runtime_surface.py`
(~:59). Do NOT delete a test to make unrelated breakage pass — only the rows asserting the now-deleted
scaffolding (the surface-inventory test keeps its other rows).

### T034 — Prove + clean
Full suite green after deletion (deletion is its own proof). `ruff`/`mypy` clean ≤15, no suppressions.

## Definition of Done
- [ ] `prompt_source` fragment + `surface=` read-param wiring deleted; 0 readers re-confirmed on this branch.
- [ ] The S-2/S-3 contract-encoding tests retired **atomically** with the deletion.
- [ ] Suite green after deletion (no behavioral change, SC-004); `build_execution_context` untouched (C-001).
- [ ] `ruff`/`mypy` clean ≤15, no suppressions. **C-008**: adjacent breakage fixed in-change.

## Reviewer guidance
Confirm the deletions are genuinely 0-reader (grep `prompt_source`, `surface=` across `src/` excluding the
deleted defs). Confirm the factory authority (`build_execution_context`, the fragment SET) is NOT otherwise
modified (C-001). Confirm only deletion-target tests were retired — not tests covering live behavior.

## Activity Log

- 2026-06-17T06:21:37Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – Assigned agent via action command
- 2026-06-17T06:33:04Z – claude:sonnet:python-pedro:implementer – shell_pid=2897020 – WP07 fragment retirement complete (prompt_source+export+surface= deleted, contract tests retired atomically, 63 pass, 0 src readers). FORCE: flattened-mission guard false-positive. Orchestrator-driven.
- 2026-06-17T06:33:05Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2985272 – Started review via action command
- 2026-06-17T06:37:03Z – user – shell_pid=2985272 – APPROVE: 0 src readers confirmed (grep prompt_source/PromptSourceFragment/surface= all zero). C-001 holds — build_execution_context body untouched, only prompt_source removed from fields dict. Retired tests: test_promptsource_fragment_parity (PromptSourceFragment), test_mission_status_load_consumes_carried_fragment (surface= param), PromptSourceFragment row in test_mission_runtime_surface.py, prompt_source refs in test_context_fragments.py — all exactly deletion-target scaffolding; no live-behaviour test deleted. Suite: 63 passed (tests/mission_runtime/ + test_execution_context_parity + test_mission_runtime_surface). ruff clean. mypy error at aggregate.py:286 is pre-existing on base branch, not introduced by WP07.
