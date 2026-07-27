---
work_package_id: WP04
title: CI wiring + live corpus-only-PR verification
dependencies:
- WP03
requirement_refs:
- FR-008
- NFR-001
planning_base_branch: fix/runtime-state-birth-cutover-all-paths
merge_target_branch: fix/runtime-state-birth-cutover-all-paths
branch_strategy: Planning artifacts for this mission were generated on fix/runtime-state-birth-cutover-all-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/runtime-state-birth-cutover-all-paths unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 3 - Enforcement
history:
- at: '2026-07-27T07:43:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/release-readiness.yml
create_intent:
- docs/development/cutover-guard.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- .github/workflows/release-readiness.yml
- docs/development/cutover-guard.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – CI wiring + live corpus-only-PR verification

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter first.

- **Profile**: `implementer-ivan` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Wire the WP03 guard into CI so it **actually fires on a corpus-only PR** and is a
**required, non-skippable** status check. This is the load-bearing fix for the
observed leak (risk R1): today `kitty-specs/**` triggers no test workflow and the
dogfood test is push-only, so a corpus-only mission PR runs nothing.

**Done when**: a scratch PR touching only `kitty-specs/**` shows the guard job
running and able to fail; the job is a required check; measured under 30s.

## Context & Constraints

- Read [contracts/pre-merge-guard.md](../contracts/pre-merge-guard.md) "Wiring guarantees" and [research.md](../research.md) (R1). Depends on **WP03** (the guard CLI must exist).
- Candidate host: `.github/workflows/release-readiness.yml` (already `on: pull_request`, fail-closed, with `pr:deferred`/`pr:skip-ci` skip-guards). Confirm it is the best host; if it has a `paths:` filter that excludes `kitty-specs/**`, add `kitty-specs/**`.
- **GitHub footgun**: a required check whose job is `if:`-skipped reports neutral/"skipped" and does NOT block. The guard job must actually EXECUTE and exit non-zero on failure — model it on an unconditional job (e.g. `deferral-consistency-check`), not one behind the `dorny/paths-filter` `changes` gate.
- C-001/C-004: pre-merge only; no push to origin/main; assume no spec-kitty run at GitHub-merge time — the guard just inspects the committed PR corpus by invoking the WP03 CLI.

## Subtasks & Detailed Guidance

### Subtask T016 – Host the guard on pull_request; add kitty-specs/** paths
- **Steps**: Add a job that runs `spec-kitty <cutover_guard>` (from WP03) against the PR's changed corpus. Ensure the host workflow's `on.pull_request.paths` includes `kitty-specs/**` (or host in a workflow with no `paths` filter). Install the package (`pip install -e .`) so the CLI resolves.

### Subtask T017 – Outside the src changes filter; not silently skippable
- **Steps**: Ensure the job is NOT gated behind the src `changes`/`dorny` filter. Confirm it runs for a diff that touches only `kitty-specs/**`.

### Subtask T018 – Register as a required check; document contract
- **Steps**: Document how to register the job as a required status check in branch protection (the operator applies the setting). Write `docs/development/cutover-guard.md` covering: what the guard does, how it triggers, the remedy command, and the required-check registration contract (including the skipped-required-check footgun).

### Subtask T019 – Live-verify corpus-only PR + measure <30s
- **Steps**: Open a scratch PR whose diff is ONLY a `kitty-specs/**` file; confirm the guard job appears, executes, and can fail (do NOT trust path-filter reading — the #2968 lesson). Record the measured wall-time to confirm NFR-002 (<30s). Close the scratch PR. Report evidence (run URL / logs) in the Activity Log.

## Test Strategy

CI-behavioral: the live scratch-PR check is the acceptance evidence. No unit test for YAML; the guard's unit tests live in WP03.

## Risks & Mitigations

- **R1** guard silently doesn't run → the whole enforcement fails. Mitigation: the live corpus-only-PR check is mandatory evidence, not optional.
- Required-check skipped-passes-silently → ensure the job executes unconditionally on corpus PRs.
- Package not installed in the job → add the editable install step.

## Review Guidance

Confirm: `kitty-specs/**` in trigger paths; job unconditional (not behind src filter); live scratch-PR evidence attached; <30s measured; docs cover required-check registration + footgun.

## Activity Log

- 2026-07-27T07:43:31Z – system – Prompt created.
