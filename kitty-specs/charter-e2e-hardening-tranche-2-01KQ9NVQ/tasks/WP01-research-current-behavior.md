---
work_package_id: WP01
title: Research Current Behavior
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-013
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
  note: Initial WP creation
agent_profile: researcher-robbie
authoritative_surface: kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/research.md
execution_mode: planning_artifact
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/research.md
role: researcher
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile. The profile defines your identity, governance scope, and boundaries for this WP.

Run `/ad-hoc-profile-load researcher-robbie` (or your equivalent skill) to apply the profile, then return here and continue reading.

## Objective

Replace every "To verify" hypothesis in `research.md` (R1..R7) with concrete file:line citations and a confirmed Decision/Rationale/Alternatives entry. Output is the updated `research.md` — the single source of truth for product-fix WPs that follow.

## Context

- **Spec**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/spec.md` (FRs 001–014, NFRs 001–006, Cs 001–006).
- **Plan**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/plan.md` Phase 0 lists the seven research questions.
- **Research**: `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/research.md` is your edit target.
- **Brief**: `/Users/robert/spec-kitty-dev/spec-kitty-20260428-103627-oSca5Q/start-here.md` enumerates issues #839–#844 and #336 with the implementation surface for each.
- **Branch**: `fix/charter-e2e-827-tranche-2`. Worktree path/branch for this lane is set by `finalize-tasks`.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks` from `lanes.json`. Use `spec-kitty agent action implement WP01 --agent <name>` to enter the workspace.

## Subtasks

### T001 — Investigate #840 init metadata stamping (R6)

**Purpose**: Document where `spec-kitty init` writes `.kittify/metadata.yaml`, which schema fields it stamps today, and where the canonical schema constants live.

**Steps**:
1. Locate the init code path. Likely roots: `src/specify_cli/init/`, `src/specify_cli/cli/init.py`, or wherever `spec-kitty init` is wired in the typer app.
2. Read the metadata writer: identify whether `spec_kitty.schema_version` and `spec_kitty.schema_capabilities` are written and, if not, why.
3. Find the canonical source of those constants — most likely under `src/specify_cli/upgrade/migrations/` (the migration that stamps them on legacy projects).
4. Note current upgrade-version test names in `tests/specify_cli/` so WP02 keeps them green.

**Files to read** (verify actual paths):
- `src/specify_cli/cli/...` (init command wiring)
- `src/specify_cli/init/...`
- `src/specify_cli/upgrade/migrations/...`
- Existing `tests/specify_cli/test_init*.py`

**Capture in research.md R6**: file:line refs for the writer; the canonical constants module:line; the set of `schema_capabilities` values.

### T002 — Investigate #841 charter generate ↔ bundle validate (R1)

**Purpose**: Document why `charter generate` and `charter bundle validate` disagree about where the generated charter lives, and pick a fix direction.

**Steps**:
1. Locate `charter generate` and `charter bundle validate` CLI command implementations. Likely under `src/charter/` (this repo has `src/charter/generator.py`, `src/charter/bundle.py`, `src/charter/compiler.py`) plus CLI shims under `src/specify_cli/charter/` or `src/specify_cli/cli/`.
2. Read both commands: identify the path `generate` writes to, and the path/source `bundle validate` reads from.
3. Identify the tracked-vs-working-tree mismatch (`git ls-files` vs filesystem).
4. Confirm the **default decision direction**: `charter generate --json` emits a `next_step.action == "git_add"` instruction in the JSON envelope when the generated file is not yet tracked.
5. If the codebase makes that direction infeasible, pick the alternative ("loosen `bundle validate` to accept the generated path") and update the research entry.

**Files to read**:
- `src/charter/generator.py`
- `src/charter/bundle.py`
- `src/charter/compiler.py`
- `src/charter/_doctrine_paths.py`
- charter CLI shim under `src/specify_cli/`

**Capture in research.md R1**: file:line refs for both commands; tracking expectations; chosen direction with rationale.

### T003 — Investigate #839 charter synthesize fixture pipeline (R2)

**Purpose**: Document why `charter synthesize --adapter fixture --json` does not produce `.kittify/doctrine/` artifacts today and why the E2E falls back to `--dry-run-evidence`.

**Steps**:
1. Read `src/charter/synthesizer/`:
   - `fixture_adapter.py` — the fixture adapter contract
   - `orchestrator.py` — top-level synthesis orchestration
   - `synthesize_pipeline.py` and `write_pipeline.py` — write path
   - `evidence.py`, `manifest.py`, `provenance.py` — artifact shapes
2. Find the `--dry-run-evidence` code path; trace why it produces artifacts but `--json` does not.
3. Identify the gap: missing wire-through, error short-circuit, or unimplemented fixture write.
4. Document the canonical artifact set the fixture should produce (manifest, provenance, doctrine units).

**Files to read**:
- `src/charter/synthesizer/fixture_adapter.py`
- `src/charter/synthesizer/orchestrator.py`
- `src/charter/synthesizer/synthesize_pipeline.py`
- `src/charter/synthesizer/write_pipeline.py`
- `src/charter/_doctrine_paths.py`
- existing `tests/doctrine_synthesizer/`

**Capture in research.md R2**: file:line refs for the gap; canonical artifact set; recommended fix scope (small change or refactor).

### T004 — Investigate #842 `--json` stdout discipline (R3)

**Purpose**: Document which CLI commands leak SaaS sync / auth / background diagnostics into `--json` stdout, and where in the codebase those leaks originate.

**Steps**:
1. Identify the SaaS sync / auth diagnostic emission sites. Likely under `src/specify_cli/auth/`, `src/specify_cli/events/`, or a shared sync client.
2. For each `--json` path the strict E2E exercises (`charter generate`, `charter bundle validate`, `charter synthesize`, `next`), trace whether diagnostics are printed to stdout or stderr.
3. Identify whether the leak is in shared output plumbing or per-command.

**Files to read**:
- `src/specify_cli/auth/...`
- `src/specify_cli/events/...`
- shared CLI base / typer app under `src/specify_cli/cli/`
- per-command modules

**Capture in research.md R3**: file:line refs for emission sites; layer (shared vs per-command); recommended routing destination (stderr vs envelope).

### T005 — Investigate #844/#336 prompt resolution in `next` (R4)

**Purpose**: Document how `next --json` resolves a step's `prompt_file`, and confirm `#336`'s fix from PR `#803` is locked.

**Steps**:
1. Read `src/specify_cli/next/decision.py`, `runtime_bridge.py`, `prompt_builder.py`.
2. Trace prompt resolution for: discovery step, research step, documentation step, composed mission steps.
3. Identify any code path that could still return `prompt_file: null`, missing, empty, or pointing at a non-existent file.
4. Read the `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` source skill — find the `prompt_file == null` workaround text WP06 will remove.
5. Inspect `git log` for PR `#803`'s changes to confirm fix shape.

**Files to read**:
- `src/specify_cli/next/` (full directory)
- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`
- mission runtime YAML prompt-template definitions (likely under `src/specify_cli/missions/`)
- PR #803 diff via `git log` if accessible

**Capture in research.md R4**: file:line refs; current resolution algorithm; locations where structured blocked decision should be returned; current workaround text in SKILL.md.

### T006 — Investigate #843 profile-invocation lifecycle write path (R5)

**Purpose**: Document where `.kittify/events/profile-invocations/` is populated, which step kinds are covered today, and why composed actions are skipped.

**Steps**:
1. Read `src/specify_cli/mission_step_contracts/executor.py`.
2. Read `src/specify_cli/invocation/`:
   - `executor.py`, `writer.py`, `record.py`, `propagator.py`, `router.py`
3. Trace the lifecycle write path for: WP-bound implement/review actions vs composed actions issued by `next`.
4. Identify the canonical record schema (action identity field name, outcome vocabulary).
5. Locate existing trail-record assertions in `tests/integration/test_documentation_runtime_walk.py`, `tests/integration/test_research_runtime_walk.py` and reuse the pattern.

**Files to read**:
- `src/specify_cli/mission_step_contracts/executor.py`
- `src/specify_cli/invocation/` (full directory)
- `tests/integration/test_documentation_runtime_walk.py`
- `tests/integration/test_research_runtime_walk.py`
- `tests/specify_cli/mission_step_contracts/`

**Capture in research.md R5**: file:line refs; record schema; outcome vocabulary; recommended fix location (executor extension vs new writer call site).

### T007 — Finalize research.md with file/line refs and skill-refresh path (R7)

**Purpose**: Confirm the skill copy refresh path so WP06 T028 can run the right migration, then commit `research.md` with all "To verify" blocks replaced.

**Steps**:
1. Identify the migration that refreshes generated skill copies. Likely under `src/specify_cli/upgrade/migrations/` — search for `runtime-next` or `skills-sync`.
2. Confirm the canonical agent directory list (CLAUDE.md "Supported AI Agents" already enumerates them).
3. Read `.kittify/command-skills-manifest.json` to confirm which agents reference each skill package.
4. Update `research.md` R7 with the migration name, the `get_agent_dirs_for_project()` helper location, and the local command WP06 should run after editing the source skill.
5. Walk back through R1..R6 and mark each "To verify" block as Confirmed with file:line refs.
6. If any decision direction needs to change from the default in `plan.md` / `research.md`, escalate via a PR comment in research.md and stop the WP — do not proceed past escalation without operator approval.

**Files to read**:
- `src/specify_cli/upgrade/migrations/`
- `.kittify/command-skills-manifest.json`
- `CLAUDE.md` "Template Source Location" section

**Capture in research.md R7**: migration name and path; `get_agent_dirs_for_project()` reference; the local command(s) WP06 will run.

## Test Strategy

This is a research-only WP. **No new code, no test changes.** The deliverable is `research.md`.

Reviewer verification: open `research.md`, confirm every R1..R7 block contains concrete file:line citations and a Decision entry. No "To verify" or "Hypothesis" markers should remain unresolved.

## Definition of Done

- [ ] All seven R1..R7 blocks updated with confirmed file:line refs.
- [ ] Default decision directions confirmed or explicit deviation escalated.
- [ ] Skill-refresh migration identified by name and path.
- [ ] No "To verify" markers remaining on R1..R7.
- [ ] `kitty-specs/charter-e2e-hardening-tranche-2-01KQ9NVQ/research.md` is the only file modified.

## Risks

- **Deviation discovered**: research finds a decision direction that requires splitting a downstream WP (e.g., #841 needs both sides changed). **Action**: stop and escalate by adding a clearly marked `## OPERATOR ESCALATION` block at the top of research.md before continuing.
- **Hidden coupling**: a fix area touches more files than the plan listed. **Action**: record the additional files in research.md and recommend `owned_files` updates for the affected WP.
- **PR #803 not visible**: if `git log` does not include PR #803's commits on this branch, document what was inferred from current code instead.

## Reviewer Guidance

Reviewer should verify:
1. Every R1..R7 entry cites concrete file:line refs.
2. The canonical schema constants for #840 are identified (not just "somewhere in upgrade migrations").
3. The fix direction for #841 is binary and committed (not "either could work").
4. The skill-refresh migration is named explicitly.
5. No deviation escalation is left unresolved without operator approval.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent <your-agent-key>
```
