---
work_package_id: WP04
title: Generate ↔ Bundle Validate Agreement (#841)
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "58076"
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/charter/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/charter/generator.py
- src/charter/bundle.py
- src/charter/compiler.py
- tests/charter/test_generate*.py
- tests/charter/test_bundle*.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

Make `charter generate` and `charter bundle validate` agree about where the generated charter lives so the operator path is direct, with no undocumented `git add` choreography. Default direction (per research): `charter generate --json` emits a `next_step.action == "git_add"` instruction in its JSON envelope when the generated file is not yet tracked, and the E2E follows that instruction verbatim.

Closes (with strict E2E gate): `#841`. Satisfies: `FR-002`, `NFR-006`.

## Context

- **Spec FR-002**: generate→bundle-validate sequence works without undocumented `git add`, OR generate emits an explicit instruction.
- **Contract**: `contracts/charter-bundle-validate.json` — see `definitions.generate_tracking_instruction`.
- **Research R1** (`research.md`): file:line refs for both commands; chosen direction.
- **Brief**: `start-here.md` "Generate and bundle validate must agree" section.
- **Existing files**: `src/charter/generator.py`, `src/charter/bundle.py`, `src/charter/compiler.py`.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`. Enter via `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks

### T016 — Implement #841 fix per research direction

**Purpose**: Make generate ↔ bundle-validate agree so the operator path is documented and direct.

**Steps**:
1. Read research R1 for confirmed direction.
2. **Default direction**: Add a `next_step` field to `charter generate --json` output. When the generated file is not yet tracked in git, emit:
   ```json
   {
     "result": "success",
     "...": "...",
     "next_step": {
       "action": "git_add",
       "paths": ["charter.md"],
       "reason": "bundle validate requires charter.md to be tracked"
     }
   }
   ```
3. When already tracked or no tracking is needed, emit `"action": "no_action_required"` (or omit `next_step`; document the chosen convention and stick to it).
4. **Alternative direction**: if research surfaces that `bundle validate` should accept the generated path directly, implement that and update `contracts/charter-bundle-validate.json` accordingly.
5. **If both sides need changes**: stop and escalate to a WP04a/WP04b split before continuing (per plan risk register).

**Files**: `src/charter/generator.py` (or wherever charter generate CLI lives), `src/charter/bundle.py` (or wherever bundle validate lives).

### T017 — Add/update tests covering generate→bundle-validate operator path

**Purpose**: Lock the agreed flow with a fresh-git-project regression test.

**Steps**:
1. In `tests/charter/`, add or extend a test that:
   - Initializes a temp git project with `spec-kitty init` (depends on WP02 if running in sequence; otherwise stamp metadata via existing helper).
   - Runs `charter generate --json`, parses stdout strictly.
   - If `next_step.action == "git_add"`, runs `git add` for the listed paths.
   - Runs `charter bundle validate --json` and asserts `result == "success"`.
2. Add a separate test that asserts the JSON envelope from `charter generate --json` itself contains the expected `next_step` shape when applicable.

### T018 — Verify `tests/charter/` regression-free

**Steps**:
1. Run `uv run pytest tests/charter -q`. Must exit 0.
2. Run `uv run mypy --strict src/charter` and `uv run ruff check src tests`.

### T019 — Cross-check operator path against quickstart.md Step 2

**Purpose**: Keep planning artifacts and code aligned (DIRECTIVE_010 specification fidelity).

**Steps**:
1. Compare the implemented behavior to `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/quickstart.md` Step 2.
2. If the chosen direction in T016 differs from the default described there, update quickstart.md to match. Update only this one file in `kitty-specs/...`; do not touch spec.md or plan.md (escalate any spec drift instead).

## Test Strategy

- **Per-fix regression coverage**: T017 (NFR-006).
- **Targeted gate**: `tests/charter/`.
- **Cross-artifact alignment**: T019.

## Definition of Done

- [ ] `charter generate --json` and `charter bundle validate --json` agree.
- [ ] Direction picked (default or alternative) with rationale recorded in commit message.
- [ ] T017 tests pass; fail without fixes.
- [ ] `tests/charter/` regression-free.
- [ ] `mypy --strict src/charter` passes; ruff passes.
- [ ] quickstart.md Step 2 reflects implemented behavior.
- [ ] Owned files only (plus optional quickstart.md update).

## Risks

- **Both sides need changes**: split into WP04a/WP04b before lanes lock (already in plan risk register).
- **JSON envelope drift breaks consumers**: SaaS / dashboard / event clients may parse the output. Audit `git grep "charter generate"` callers before adding fields.
- **Backward compat**: existing tracked-charter callers must still pass. Don't make `next_step` mandatory in consumers.

## Reviewer Guidance

- Confirm chosen direction in commit message and code matches research R1.
- Confirm operator path is direct (no out-of-band knowledge needed beyond the JSON envelope).
- Confirm quickstart.md Step 2 still matches.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent <your-agent-key>
```

## Activity Log

- 2026-04-28T10:34:25Z – claude:sonnet:implementer-ivan:implementer – shell_pid=52562 – Started implementation via action command
- 2026-04-28T10:40:00Z – claude:sonnet:implementer-ivan:implementer – shell_pid=52562 – Default direction: charter generate emits next_step.git_add when charter.md is untracked; tests cover fresh-project flow; bundle validate invariant unchanged
- 2026-04-28T10:40:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=58076 – Started review via action command
- 2026-04-28T10:42:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=58076 – Review passed: next_step git_add/no_action_required envelope correctly added to charter generate --json (charter.py:1257-1290), reuses imported _is_git_tracked from charter_bundle (no duplication), bundle validate untouched, 3 next_step tests pass, full tests/charter suite 663 passed, contract definitions.generate_tracking_instruction shape matches, quickstart Step 2 aligned, owned-files scope respected
