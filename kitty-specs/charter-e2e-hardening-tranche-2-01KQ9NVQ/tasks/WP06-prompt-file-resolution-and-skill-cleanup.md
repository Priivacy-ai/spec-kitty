---
work_package_id: WP06
title: 'Prompt-File Resolution in `next` + Skill Cleanup (#844 / #336)'
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-013
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
agent: claude
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/next/**
- src/doctrine/skills/spec-kitty-runtime-next/**
- tests/next/**
- .claude/commands/spec-kitty.runtime-next.md
- .amazonq/prompts/spec-kitty-runtime-next.md
- .gemini/commands/spec-kitty-runtime-next.md
- .cursor/commands/spec-kitty-runtime-next.md
- .qwen/commands/spec-kitty-runtime-next.md
- .opencode/command/spec-kitty-runtime-next.md
- .windsurf/workflows/spec-kitty-runtime-next.md
- .kilocode/workflows/spec-kitty-runtime-next.md
- .augment/commands/spec-kitty-runtime-next.md
- .roo/commands/spec-kitty-runtime-next.md
- .kiro/prompts/spec-kitty-runtime-next.md
- .agent/workflows/spec-kitty-runtime-next.md
- .github/prompts/spec-kitty-runtime-next.md
- .agents/skills/spec-kitty-runtime-next/SKILL.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

Make `spec-kitty next --json` return strict envelopes per `contracts/next-issue.json`: every issued step carries a non-empty, on-disk-resolvable `prompt_file`; when no prompt is resolvable, the call returns a structured blocked decision. Remove the `prompt_file == null` workaround from the SOURCE skill `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and refresh generated agent copies via the established upgrade migration.

Closes (with strict E2E gate): `#844`. Verifies fix from `#336`/PR `#803` is locked. Satisfies: `FR-006`, `FR-013`, `NFR-006`.

## Context

- **Spec FR-006**: `next --json` never issues a step with `prompt_file: null`/missing/empty/dangling. **FR-013**: skill no longer documents the workaround.
- **Contract**: `contracts/next-issue.json`.
- **Research R4** (`research.md`): file:line refs for `decision.py`, `runtime_bridge.py`, `prompt_builder.py`; current resolution algorithm.
- **Brief**: `start-here.md` "The golden path must enforce runnable prompt files" section.
- **CLAUDE.md "Template Source Location"**: edit SOURCE only; agent copies are generated.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`. Enter via `spec-kitty agent action implement WP06 --agent <name>`.

## Subtasks

### T025 — Ensure `next --json` issued steps carry non-empty resolvable `prompt_file`

**Purpose**: Lock FR-006 in the runtime so the strict E2E (WP08) can require it.

**Steps**:
1. Read research R4 file:line refs for `decision.py`, `runtime_bridge.py`, `prompt_builder.py`.
2. Trace the prompt resolution path for each step kind. Identify any path that could return `prompt_file: null`, missing, empty, or pointing at a non-existent file.
3. Update the resolver: when a prompt cannot be resolved (no template, no fallback), return a structured blocked decision per `contracts/next-issue.json` `definitions.blocked` with `status: "blocked"`, a non-empty `reason`, and an optional `blocker_code` like `"no_prompt_template"`.
4. When a prompt IS resolvable, ensure `step.prompt_file` is non-empty and the path resolves on disk before the JSON envelope is emitted.

**Files**: `src/specify_cli/next/decision.py`, `src/specify_cli/next/runtime_bridge.py`, `src/specify_cli/next/prompt_builder.py`.

### T026 — Add per-step-kind tests for prompt-file presence/resolvability

**Purpose**: Lock the behavior with regression coverage for every public step kind.

**Steps**:
1. In `tests/next/`, add tests for each public step kind:
   - discovery (the original #336 case)
   - research
   - documentation
   - composed mission steps
2. Each test invokes `next --json` via subprocess against a project that should issue that step kind, and asserts:
   - If `status == "issued"`: `step.prompt_file` is non-empty AND `os.path.exists(step.prompt_file)` is True.
   - If `status == "blocked"`: `reason` is non-empty.
   - There is no third state.
3. Add a negative test: simulate a step with no prompt template (e.g., via a fixture) and assert the response is `blocked`, not partial-issued.

**Files**: new test(s) under `tests/next/`.

### T027 — Edit SOURCE skill to remove `prompt_file == null` workaround

**Purpose**: Per CLAUDE.md "Template Source Location", edit only the source file.

**Steps**:
1. Read `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`.
2. Locate the workaround text — typically a paragraph or numbered step that tells the agent "if `prompt_file` is null, do X instead". The exact phrasing is identified in research R4.
3. Delete that section. If surrounding context references it, reword to describe the new contract: `prompt_file` is always non-empty and resolvable, OR the response is `status: "blocked"`.
4. Do **not** edit any of the generated copies under `.claude/`, `.amazonq/`, etc. — those are regenerated by T028.

**File**: `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` only.

### T028 — Run skills sync / upgrade migration; confirm regenerated copies in diff

**Purpose**: Ensure the generated agent copies of the runtime-next skill don't ship the old workaround text.

**Steps**:
1. Read research R7 for the migration name and command.
2. Run the local skills sync command (likely `spec-kitty upgrade` or an equivalent migration runner; confirm in research).
3. Verify the diff: regenerated copies under `.claude/commands/`, `.amazonq/prompts/`, `.gemini/commands/`, `.cursor/commands/`, `.qwen/commands/`, `.opencode/command/`, `.windsurf/workflows/`, `.kilocode/workflows/`, `.augment/commands/`, `.roo/commands/`, `.kiro/prompts/`, `.agent/workflows/`, `.github/prompts/`, `.agents/skills/spec-kitty-runtime-next/SKILL.md` are all updated to reflect the new SOURCE.
4. If the manifest at `.kittify/command-skills-manifest.json` updates, include it in the diff.
5. Do not hand-edit any agent copy. If a copy is out of sync after the migration, file a bug; do not patch by hand.

### T029 — Verify `tests/next/` regression-free

**Steps**:
1. Run `uv run pytest tests/next -q`. Must exit 0.
2. Run `uv run mypy --strict src/specify_cli` and `uv run ruff check src tests`.

## Test Strategy

- **Per-fix regression coverage**: T026 covers all four step kinds (NFR-006).
- **Targeted gate**: `tests/next/`.
- **Skill cleanup verification**: visual diff in T028 — reviewer should see all 14 generated copies updated.

## Definition of Done

- [ ] `next --json` issued steps always carry non-empty resolvable `prompt_file`, or response is structured blocked.
- [ ] T026 tests pass; fail without fixes.
- [ ] SOURCE skill no longer documents `prompt_file == null` workaround.
- [ ] Generated agent copies refreshed via migration; visible in PR diff.
- [ ] No hand-edited agent copies.
- [ ] `mypy --strict` passes; ruff passes.
- [ ] Owned files only (note: agent-copy files are owned by this WP because they are regenerated here).

## Risks

- **Step kind without a prompt template**: research R4 may surface a step kind that legitimately has no prompt today. **Mitigation**: such a step kind must either gain a prompt template or always return `blocked`. Document the choice in the commit message.
- **Migration drift**: if `spec-kitty upgrade` doesn't refresh skills directly, identify the specific migration that does (per research R7). Don't run unrelated migrations.
- **Generated copy ownership conflict**: agent-copy paths are owned by this WP. If another concurrent WP also touches them, coordinate (in practice, only WP06 should touch them in this tranche).

## Reviewer Guidance

- Confirm SOURCE skill diff removes the workaround.
- Confirm all 14 agent copies in the diff reflect the new SOURCE.
- Run `next --json` against a fresh project; confirm `prompt_file` is resolvable or response is `blocked`.
- Review T026 test coverage across step kinds.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent <your-agent-key>
```
