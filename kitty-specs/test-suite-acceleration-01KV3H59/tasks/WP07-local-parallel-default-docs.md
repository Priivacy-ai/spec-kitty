---
work_package_id: WP07
title: Local parallel default and contributor docs
dependencies:
- WP04
- WP05
requirement_refs:
- FR-001
- FR-011
- NFR-001
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
phase: Phase 5 - Documentation
agent: claude
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/development/
create_intent:
- docs/development/testing-parallel.md
execution_mode: code_change
model: ''
owned_files:
- docs/development/testing-parallel.md
- CLAUDE.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Local parallel default and contributor docs

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Make safe local multi-process runs the documented default — but only after the preconditions are proven green.

**Done when**: the local parallel command and the serial daemon-pass caveat are documented in `CLAUDE.md` and a dedicated docs page; the documented command runs the suite green locally (≥2× faster on ≥4 cores, NFR-001) with the real home untouched.

## Context & Constraints

- **Depends on WP04** (HOME isolation) AND **WP05** (charter flip proven green under `-n auto`). Do NOT publish the local default before both are green — otherwise developers running it would have corrupted their real `~/.spec-kitty` (the exact hazard WP04 fixes).
- Evidence: `architecture/test-suite-acceleration-plan.md` (B1, C-LOCAL); `quickstart.md`.
- The `/spec-kitty.plan` step deliberately did NOT touch `CLAUDE.md`; THIS implementation WP is the right place to update it.

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T028 – Document the local parallel command + caveat

- **Purpose**: Give contributors one correct command.
- **Steps**:
  1. In `CLAUDE.md` (Commands section), document:
     ```bash
     PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
     ```
     and the **serial daemon pass** for port/daemon tests:
     ```bash
     PWHEADLESS=1 pytest tests/sync/test_orphan_sweep.py -n0 -q
     ```
  2. State the rules: always `--dist loadfile` (never bare `--dist load`); real-port/daemon tests run serially; the run never touches the real `~/.spec-kitty` (WP04).
- **Files**: `CLAUDE.md`.

### Subtask T029 – Testing-parallel docs page + config guidance

- **Purpose**: A discoverable explanation.
- **Steps**:
  1. Create `docs/development/testing-parallel.md` covering: why `loadfile`, the per-worker home isolation, the serial pass, the volume env gates (`SPEC_KITTY_ULID_VOLUME_FULL`), and how to run the stability ratchet locally.
  2. Cross-link it from the docs index / contributor guide as appropriate (record any out-of-map index edit with rationale).
- **Files**: `docs/development/testing-parallel.md`.

### Subtask T030 – Wire quickstart validation helper

- **Purpose**: Make the mission’s validation reproducible.
- **Steps**:
  1. Fold the `quickstart.md` validation steps (collection-equivalence diff, 3× ratchet, parallel-vs-serial timing) into the testing-parallel docs page as a copy-pasteable block.
  2. Reference the WP02 ratchet entrypoint so contributors run the same gate CI uses.
- **Files**: `docs/development/testing-parallel.md`.

## Test Strategy

- Run the documented command end-to-end locally; confirm green and ≥2× vs the serial baseline (capture both numbers).
- Confirm `~/.spec-kitty` is untouched after the run.

## Risks & Mitigations

- **Risk**: publishing before WP04/WP05 are green corrupts real state. **Mitigation**: hard dependencies; verify both green first.
- **Risk**: docs drift from the actual flags. **Mitigation**: copy flags verbatim from the proven CI step.

## Review Guidance

- Confirm the command matches the proven CI invocation and includes the serial-pass caveat.
- Reviewer profile suggestion: curator-carla or reviewer-renata.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
