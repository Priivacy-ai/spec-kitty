---
work_package_id: WP05
title: Recovery-command repoint — phantom 'agent worktree repair' to 'doctor workspaces --fix'
dependencies: []
requirement_refs:
- FR-007
tracker_refs:
- '#1890'
- '#2119'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
- T055
phase: Phase 1 - Recovery text (line-disjoint, fully parallel)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1692844"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_coordination_doctor.py
create_intent:
- tests/architectural/test_no_phantom_worktree_repair.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_coordination_doctor.py
- src/specify_cli/coordination/surface_resolver.py
- src/doctrine/skills/spec-kitty-mission-system/SKILL.md
- tests/architectural/test_no_phantom_worktree_repair.py
- tests/coordination/test_surface_resolver_coord_empty_warning.py
- tests/specify_cli/coordination/test_surface_resolver.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 — Recovery-command repoint (#1890)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface:
src/specify_cli/cli/commands/_coordination_doctor.py`.

---

## Objective

**Remove the phantom `spec-kitty agent worktree repair` recovery string from every site and
replace it with the REAL `spec-kitty doctor workspaces --fix`** (which exists). The phantom
command was deleted post-#2135 but the recovery guidance still points users at it — a dead end.
Enforce with a **count-agnostic** repo-wide grep-guard so the phantom string can never survive
or re-appear, regardless of how many sites exist.

## The 8 phantom sites (live-verified on `e36547461`, post-#2135 — count-agnostic guard regardless)

| Site | Anchor |
|------|--------|
| `cli/commands/_coordination_doctor.py` | `:220`, `:293`, `:338`, `:345` (×4) |
| `coordination/surface_resolver.py` | `:109`, `:119`, `:782` (×3) |
| SOURCE doctrine `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` | `:509` (×1) |

`cli/commands/doctor.py` now has **ZERO** (#2135 relocated its former 5 phantom strings into
`_coordination_doctor.py`, where a duplicate collapsed to 4). The `SKILL.md` site is the **SOURCE**
doctrine under `src/doctrine/`, NOT a generated `.agents/` copy — edit the source only.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-007** + **SC-005** (count-agnostic grep-guard fails closed).
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C4**.
- [research.md](../research.md) brownfield deprecations note.

**Negative scope:**
- Do NOT edit generated `.agents/` / `.claude/` copies of `SKILL.md` — only the SOURCE under
  `src/doctrine/`.
- Do NOT pin the grep-guard to a hardcoded count (it must fail closed on ANY surviving phantom).
- Do NOT change the surrounding diagnostic logic — only the recovery STRING.

## Branch Strategy

- **Strategy**: no dependencies — fully parallel with all other WPs (line-disjoint).
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP05 OWNS `cli/commands/_coordination_doctor.py`, `coordination/surface_resolver.py`, and the
> SOURCE `SKILL.md`. No other WP touches these (WP04 owns `coordination/teardown.py`, a different
> file — no glob overlap with `surface_resolver.py`).

## Subtasks & Detailed Guidance

### Subtask T051 — Count-agnostic repo-wide grep-guard (red-first)

- **Purpose**: Fail closed on ANY surviving `agent worktree repair`.
- **Files**: new `tests/architectural/test_no_phantom_worktree_repair.py`.
- **Steps (red-first)**:
  1. Walk **`src/` only** (product code + SOURCE doctrine under `src/doctrine/` — the 8 sites WP05
     owns) and assert the literal `agent worktree repair` appears **zero** times. **Scope explicitly
     to `src/` — do NOT sweep `docs/`, `architecture/`, `kitty-specs/`, or `tests/`.** Those trees
     carry the phantom string in HISTORICAL engineering notes (`docs/engineering_notes/**`, 7 files),
     an immutable ADR snapshot (`architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md`),
     mission planning prose, and the two test-side assertions re-pinned by T055 — none of which WP05
     owns or should rewrite. A tree-wide guard would force WP05 to edit unowned files (ownership
     violation) and corrupt the historical record. (Live census on HEAD: 8 in `src/`, 7 in `docs/`,
     1 in `architecture/`, 2 in `tests/` — only the 8 `src/` sites are in scope.)
  2. Assert RED on current code (8 surviving `src/` sites). After T052–T055, GREEN.
  3. Phrase the guard count-agnostically — it greps `src/` and fails on any match; it does NOT
     assert "exactly N sites".
- **Notes**: model on the existing architectural grep-guards in `tests/architectural/`. The two
  test-side assertions (`tests/coordination/...` and `tests/specify_cli/coordination/...`) are
  re-pinned by T055, not by this `src/`-scoped guard.

### Subtask T052 — Repoint `_coordination_doctor.py` (×4)

- **Purpose**: Replace the 4 phantom strings.
- **Files**: `cli/commands/_coordination_doctor.py:220`, `:293`, `:338`, `:345`.
- **Steps**:
  1. Replace each `spec-kitty agent worktree repair --mission <slug>` with
     `spec-kitty doctor workspaces --fix` (preserve any `--mission <slug>` scoping ONLY if
     `doctor workspaces --fix` accepts it — verify the real command's flags via
     `spec-kitty doctor workspaces --help`; if it does not take `--mission`, drop the suffix).
  2. Keep the surrounding f-string / message structure; only the command text changes.
- **Notes**: if a phantom string is duplicated verbatim, consider hoisting it to a module
  constant per Sonar S1192 (≥3 occurrences) — but the recovery text is now the REAL command.

### Subtask T053 — Repoint `surface_resolver.py` (×3)

- **Purpose**: Replace the 3 phantom strings (one is a runtime message at `:119`, two are
  comments at `:109`/`:782`).
- **Files**: `coordination/surface_resolver.py:109`, `:119`, `:782`.
- **Steps**:
  1. `:119` (runtime message) — replace the phantom with `spec-kitty doctor workspaces --fix`.
  2. `:109`, `:782` (comments describing the recovery paths) — correct the prose to name the real
     command.
- **Notes**: `surface_resolver.py` is a loopback/control-plane module — no transport changes here,
  just the recovery STRING.

### Subtask T054 — Repoint SOURCE `SKILL.md`

- **Purpose**: Fix the doctrine source.
- **Files**: `src/doctrine/skills/spec-kitty-mission-system/SKILL.md:509`.
- **Steps**:
  1. The line currently reads: "do **not** use `agent worktree repair`" — replace the phantom
     reference with `spec-kitty doctor workspaces --fix` guidance.
  2. This is the SOURCE; generated `.agents/` copies propagate via `spec-kitty upgrade` (do NOT
     edit them here).
  3. Run the terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`) since
     this is doctrine prose.
- **Notes**: per CLAUDE.md, edit SOURCE templates under `src/doctrine/`, never agent copies.

### Subtask T055 — RE-PIN the two test-side phantom assertions (DIR-041 — update, not delete)

- **Purpose**: Two EXISTING tests assert the phantom `spec-kitty agent worktree repair` string in
  the recovery guidance. After T052–T053 repoint the production strings to
  `doctor workspaces --fix`, these assertions go STALE (they still expect the phantom command).
  Re-pin them to the REAL command so they assert the corrected recovery guidance — never delete or
  weaken them.
- **Files** (live-verified anchors on HEAD):
  - `tests/coordination/test_surface_resolver_coord_empty_warning.py:127` — asserts
    `"spec-kitty agent worktree repair" in message` (the coord-empty warning's recovery path (b)).
  - `tests/specify_cli/coordination/test_surface_resolver.py:276` — asserts
    `"spec-kitty agent worktree repair" in err.next_step` (the `CoordinationBranchDeleted.next_step`).
- **Steps (DIR-041 — re-pin valid+current tests to the new contract)**:
  1. `:127` — re-pin the recovery-path-(b) assertion to require `"doctor workspaces --fix"` in the
     warning message (the real command), keeping the recovery-path-(a) "flatten /
     `coordination_branch`" assertion intact. The test still verifies "both recovery paths named" —
     only path (b)'s command text changes.
  2. `:276` — re-pin `err.next_step` to assert `"doctor workspaces --fix"` (the real command),
     keeping the `error_code` / `coordination_branch` assertions intact.
  3. Do NOT delete or skip either test; they remain valid contracts on the recovery guidance — only
     the asserted command string is corrected.
- **Notes**: these two assertions are exactly why the T051 grep-guard would have broken if left
  tree-wide — they are dormant false-greens that must be re-pinned IN STEP with the production
  repoint. After T052/T053/T055, `surface_resolver.py`'s production message AND both test
  assertions all name the real command.

## Test Strategy

- `pytest tests/architectural/test_no_phantom_worktree_repair.py tests/architectural/test_no_legacy_terminology.py -q` — RED first (8 `src/` sites), GREEN after.
- `pytest tests/coordination/test_surface_resolver_coord_empty_warning.py tests/specify_cli/coordination/test_surface_resolver.py -q` — the two re-pinned assertions (T055) GREEN against the corrected recovery strings.
- `ruff check src/specify_cli/cli/commands/_coordination_doctor.py src/specify_cli/coordination/surface_resolver.py` + `mypy --strict` — zero issues, no suppressions.

## Definition of Done

- [ ] All 8 phantom `agent worktree repair` sites in `src/` replaced with `doctor workspaces --fix`
  (4 + 3 + 1 SOURCE `SKILL.md`).
- [ ] `cli/commands/doctor.py` confirmed ZERO (no regression introduced there).
- [ ] Count-agnostic grep-guard test passes, **scoped to `src/`** (fails closed on any surviving
  phantom in product + SOURCE doctrine); it does NOT sweep `docs/`/`architecture/`/`kitty-specs/`/
  `tests/` (historical/immutable/unowned).
- [ ] **T055: the two test-side assertions RE-PINNED** (DIR-041) —
  `test_surface_resolver_coord_empty_warning.py:127` and `test_surface_resolver.py:276` now assert
  `doctor workspaces --fix`; neither deleted/weakened.
- [ ] Only the SOURCE `SKILL.md` edited (no `.agents/` copies); terminology guard green.
- [ ] ruff + `mypy --strict` clean; no suppressions.

## Risks & Mitigations

- **`doctor workspaces --fix` flag mismatch:** mitigated by verifying the real command's flags via
  `--help` before keeping a `--mission` suffix (T052 step 1).
- **Editing a generated copy by mistake:** mitigated by the negative scope (SOURCE only); the
  grep-guard still passes because the source is fixed and copies regenerate.
- **Sonar S1192 (repeated literal):** if the real command string appears ≥3 times in one module,
  hoist to a constant.

## Review Guidance

- Confirm every replacement names the REAL `doctor workspaces --fix` and the grep-guard is
  count-agnostic **and scoped to `src/`** (not the whole tree — docs/architecture/kitty-specs/tests
  carry the phantom in historical/immutable/unowned prose).
- Confirm T055 re-pinned BOTH test assertions (`:127`, `:276`) to `doctor workspaces --fix` (DIR-041
  — updated, not deleted).
- Confirm only the SOURCE `SKILL.md` was edited, not a generated `.agents/` copy.
- Confirm `doctor.py` was not touched (it is already zero post-#2135).

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-007/#1890.
</content>
- 2026-06-25T21:00:11Z – claude:sonnet:python-pedro:implementer – shell_pid=1653982 – Assigned agent via action command
- 2026-06-25T21:11:51Z – user – shell_pid=1653982 – Moved to claimed
- 2026-06-25T21:11:57Z – user – shell_pid=1653982 – Moved to in_progress
- 2026-06-25T21:12:34Z – claude:sonnet:python-pedro:implementer – shell_pid=1653982 – Ready: 8+ phantom sites repointed (5 in doctor.py + 3 in surface_resolver.py + 1 in SKILL.md), src/-scoped grep-guard added, 2 tests re-pinned (T055); ruff/mypy clean, 254 tests pass
- 2026-06-25T21:14:20Z – claude:sonnet:python-pedro:implementer – shell_pid=1653982 – Code on lane-e (9222a80fe): 8 phantom sites repointed + src-scoped grep-guard + 2 tests re-pinned
- 2026-06-25T21:14:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=1692844 – Started review via action command
- 2026-06-25T21:24:35Z – user – shell_pid=1692844 – renata APPROVE: phantom gone from src/ (mutation-probed grep-guard), 2 re-pins honest, doctor workspaces --fix correct
