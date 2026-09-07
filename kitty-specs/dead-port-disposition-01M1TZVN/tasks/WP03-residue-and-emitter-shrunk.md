---
work_package_id: WP03
title: Gate-Adjacent Residue + Emitter Slice (SHRUNK variant)
dependencies:
- WP01
requirement_refs:
- C-002
- C-003
- C-006
- C-007
- FR-011
- FR-012
- FR-013
- FR-014
- NFR-003
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Wave 1 - Residue (after WP01)
history:
- at: '2026-09-06T12:40:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_layer_rules.py
- src/specify_cli/team_projection/**
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
- src/mission_runtime/lifecycle_phase.py
- src/kernel/paths.py
- src/runtime/next/event_emitter.py
- tests/architectural/test_no_retired_subsystems.py
- tests/architectural/test_pyproject_shape.py
role: implementer
agent: claude
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Gate-Adjacent Residue + Emitter Slice (SHRUNK variant)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Stories 3 and 4 (P3/P4). **Gate states at tasks time**: PR #3888 merged (C-002 satisfied); PR #3898 (emitter ADR) open / `Proposed` → this WP ships the **shrunk** variant (decision OD7 `01M1VAHPARWJKB35F6E1VH8ZTW`); PR #3899 carries none of the residue (OD8 `01M1VAHQN3WFC58K0TS9C1DYFQ`). **Update 2026-09-06 16:00Z**: PR #3898 MERGED with the ADR Accepted and PR #3899 MERGED. The ADR execution is minted as **WP05** (depends on this WP) — do NOT execute the ADR here; keep this WP's emitter items exactly as written (docstring correction + FR-011 record), noting in the docstring that the ADR is Accepted and executed by WP05. PR #3899 carried none of the residue (verified), so OD8 holds.

Done means:

- **SC-008 / FR-013**: `tests/architectural/test_layer_rules.py:65-73` no longer excludes the nonexistent `constitution` package; the layer rules gate is green.
- **FR-014**: `src/specify_cli/team_projection/` deleted; `ActionContext` alias deleted from both files; the 13 test-only `__all__` exports demoted (never deleted) with matching re-pins in `tests/architectural/test_no_dead_symbols.py` (out-of-map: WP01 owns that file; you edit it AFTER WP01 landed, with a one-line rationale in the Activity Log).
- **SC-007 shrunk**: `src/runtime/next/event_emitter.py:1-10` docstring corrected to point at the real E3 seam (`src/specify_cli/status/adapters.py:364-366`) and to name the pending ADR; **no code, name, signature, or import changes** anywhere on the emitter surface; `tests/runtime/test_bridge_parity.py` untouched and green; `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) untouched (C-006).
- **FR-011**: `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md` extracted from the dossier §3 with every anchor re-verified at your HEAD.
- Follow-up mint text for the emitter execution drafted in `design-notes/WP03-residue.md`.

## Context & Constraints

- Spec US3, US4, FR-011..014, C-002, C-003, C-006, C-007, SC-006..008. Contract `contracts/residue-and-emitter-shrunk.md` (binding). Data model §2 (gate ledger), §5 (residue table). Research §1 (gate states), §7 (R6).
- **C-007 runtime ledger**: after each deletion run `tests/architectural/test_layer_rules.py::test_runtime_ledger_has_no_stale_entries`; if a subpackage's last live `specify_cli` edge disappears, edit the ledger in the same commit (you own `test_layer_rules.py`).
- Do not touch Mission A's four shared runtime files beyond `event_emitter.py`'s docstring (`event_emitter.py` is not one of the four, but is Mission-A-adjacent — docstring only).
- Sonar/CLAUDE.md rules as usual; terminology guard before doc pushes.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP03 --mission dead-port-disposition-01M1TZVN` (based on WP01's lane).

## Subtasks & Detailed Guidance

### Subtask T011 – Delete the `constitution` exclusion

- **Purpose**: FR-013 / SC-008.
- **Steps**: read `tests/architectural/test_layer_rules.py:55-80`; delete the comment block and the `"constitution",` entry (`:65-73`); confirm no other reference (`grep -n constitution tests/architectural/test_layer_rules.py`); run the file. Record in the Activity Log that PR #3888 is present in the branch (`git log --oneline | grep 3888`).
- **Files**: `tests/architectural/test_layer_rules.py`.
- **Parallel?**: No.

### Subtask T012 – Delete the `team_projection/` tombstone

- **Purpose**: FR-014.
- **Steps**: `ls src/specify_cli/team_projection/` (expect only `__init__.py`); `git rm -r` it; check `pyproject.toml` `[tool.hatch.build.targets.wheel].packages` (WP01 owns `pyproject.toml` — if an entry must go, it is a one-line out-of-map edit with rationale; if WP01 is still open, coordinate); run `tests/architectural/test_no_retired_subsystems.py` (its bans at `:39-40,99-100` assert absence and stay green) and `tests/architectural/test_pyproject_shape.py`.
- **Files**: `src/specify_cli/team_projection/`.
- **Parallel?**: Yes.

### Subtask T013 – Delete the `ActionContext` alias

- **Purpose**: FR-014.
- **Steps**: `src/mission_runtime/context.py:338` (`ActionContext = MissionExecutionContext`) and its `__all__` entry `:342`; `src/mission_runtime/__init__.py:127` listing and the `__getattr__` branch `:139-142`; also the docstring mention at `context.py:22`. `grep -rn "ActionContext\b" src tests docs` → only unrelated `MissionExecutionContext` hits remain. If `test_no_dead_symbols.py` pins `ActionContext`, drop that pin in T014's edit.
- **Files**: `src/mission_runtime/context.py`, `src/mission_runtime/__init__.py`.
- **Parallel?**: Yes.

### Subtask T014 – Demote the 13 test-only `__all__` exports; re-pin

- **Purpose**: FR-014 (demotion, never deletion).
- **Steps**: enumerate the 13 from the current pins in `tests/architectural/test_no_dead_symbols.py` (search for `mission_runtime` and the two named symbols `content_present_at_primary_tip` (`mission_runtime/lifecycle_phase.py`), `get_packs_root_default` (`kernel/paths.py`)); for each: remove from the package `__all__` (and the `__init__.py` re-export if it exists only for the facade), keep the symbol; in-package callers (`mission_runtime/resolution.py:52`, `kernel/env_expand.py:63`) already import by module path — verify; tests importing via the package facade repoint to module paths. Then update the pins in `test_no_dead_symbols.py` (out-of-map, after WP01 landed; rationale line in Activity Log: "OD8 — WP03 re-pins sequenced behind WP01's DSL pin drops").
- **Files**: `src/mission_runtime/__init__.py`, `src/mission_runtime/lifecycle_phase.py`, `src/kernel/paths.py`, `tests/architectural/test_no_dead_symbols.py` (out-of-map), affected tests.
- **Parallel?**: No (after T011–T013).

### Subtask T015 – Emitter docstring; FR-011 record; follow-up mint; PR re-check

- **Purpose**: FR-011, FR-012 (shrunk), SC-007.
- **Steps**: (1) rewrite `src/runtime/next/event_emitter.py:1-10` per `contracts/residue-and-emitter-shrunk.md` §2 — docstring only; `git diff` must show no non-docstring change. (2) Create `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md`: header "Input to PR #3898 — recorded, not executed (C-003)"; copy dossier §3.1/§3.2 and the relevant verification-log lines; re-verify each anchor (`event_emitter.py:23`, `_internal_runtime/events.py:67`, `runtime_bridge_engine.py:80` TYPE_CHECKING import + 16 sites, `runtime_bridge.py:195,:1552,:2739,:1614,:2745,:2149-2150,:2187,:1560-1565`, `test_bridge_parity.py:1131-1152`, `spec_kitty_events` version via `.venv/bin/python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"`) and mark deltas. (3) `design-notes/WP03-residue.md`: the FR-012 follow-up text (contract §4), the PR #3898/#3899 re-check output with timestamps, and the residue placement table as landed. (4) Run `tests/runtime/test_bridge_parity.py` — must be untouched and green.
- **Files**: `event_emitter.py` (docstring), research file, design note.
- **Parallel?**: Yes.

## Test Strategy

```bash
.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py -q
.venv/bin/pytest tests/runtime/test_bridge_parity.py tests/mission_runtime -q 2>/dev/null || .venv/bin/pytest tests/runtime/test_bridge_parity.py -q
PWHEADLESS=1 make test-fast
grep -rn "ActionContext\b" src tests docs | grep -v MissionExecutionContext ; echo "expect nothing"
.venv/bin/ruff check $(git diff --name-only --diff-filter=AMR $(git merge-base HEAD missions/coreloop-proto-missions) | grep '\.py$') && .venv/bin/mypy src/mission_runtime src/kernel/paths.py
```

## Risks & Mitigations

- Wheel build breaks on the deleted package → `test_pyproject_shape.py`.
- A demotion deletes instead of demotes → in-package callers listed above must keep working; grep before/after.
- Emitter surface drift → `git diff --stat` on `src/runtime/next/` shows only `event_emitter.py` with docstring-only hunks.

## Review Guidance

- `constitution` gone; layer rules green; #3888 present.
- Residue table fully landed; 13 demotions are demotions; pins consistent.
- Emitter: docstring-only diff; parity oracle untouched; FR-011 record present with re-verified anchors; follow-up text present; PR re-check recorded.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T12:40:00Z – system – Prompt created.
