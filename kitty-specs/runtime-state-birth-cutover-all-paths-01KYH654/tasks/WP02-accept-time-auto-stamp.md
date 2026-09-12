---
work_package_id: WP02
title: Auto-stamp cutover at the terminal accept seam
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-006
- NFR-003
planning_base_branch: fix/runtime-state-birth-cutover-all-paths
merge_target_branch: fix/runtime-state-birth-cutover-all-paths
branch_strategy: Planning artifacts for this mission were generated on fix/runtime-state-birth-cutover-all-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/runtime-state-birth-cutover-all-paths unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Stamp
history:
- at: '2026-07-27T07:43:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/accept.py
create_intent:
- tests/specify_cli/cli/test_accept_birth_cutover.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/migration/runtime_state_cutover.py
- tests/specify_cli/cli/test_accept_birth_cutover.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Auto-stamp cutover at the terminal accept seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter first.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Stamp the birth-cutover into the mission branch at the terminal `accept` seam so
the committed corpus is **already cut over before the branch can land by any
path** (closing the GitHub-squash/rebase leak). Reuse the single authority
`cutover_mission` — no forked writer.

**Done when**: a finalized mission stamped at accept, then squash-merged with no
`spec-kitty merge`, has a cut-over corpus on the target branch (per
[data-model.md](../data-model.md)) with no post-merge step. See
[contracts/stamp-seam.md](../contracts/stamp-seam.md) — that contract is binding.

## Context & Constraints

- Reference wiring to mirror: `merge/executor.py::_run_birth_cutover:939` (resolve legs → `cutover_mission` best-effort → commit both partitions). Do the same shape at accept.
- **FR-005 single authority**: call `runtime_state_cutover.cutover_mission(...)`; do not reimplement seeding/flip.
- **R4**: `_flip_phase` writes but does NOT git-commit; this WP must commit both partitions into the branch. **PRIMARY** = `meta.json` (status_phase), **COORD** = `status.events.jsonl` (seed events). No reliance on the background status daemon (it can commit under a stale message — see project memory).
- **Worktree `.git`-redirect hazard** (WP09/#2920): write `status_phase` LAST, only after `verify.ok`, resume-heal; ensure the write lands on the branch's own `meta.json` (read the `_flip_phase` path-normalization contract pinned on this branch, commit `d89e2be8d`).
- Depends on **WP01** (pinned anchor) — do not start seeding logic before WP01 lands.

## Subtasks & Detailed Guidance

### Subtask T005 – Locate the accept seam & confirm runtime finality
- **Purpose**: Find where to stamp such that runtime state is final.
- **Steps**: Read `cli/commands/accept.py` (esp. `_commit_residual_acceptance_artifacts`). Confirm accept runs only when all WPs are approved/done (runtime final — avoids the dual-write vacuity trap, FR-004). Identify the commit point for residual artifacts to hook the stamp into.

### Subtask T006 – Add the accept-time cutover_mission caller
- **Purpose**: The stamp (FR-001/FR-005).
- **Steps**: Resolve PRIMARY `feature_dir` + COORD `status_feature_dir` (topology-aware, as executor does). Call `cutover_mission(feature_dir, status_feature_dir=..., dry_run=False)` best-effort/non-fatal. Record the `CutoverResult`.
- **Files**: `accept.py`; a small shared helper may live in `runtime_state_cutover.py` if it reduces duplication with executor (keep single authority).

### Subtask T007 – Commit both partitions into the branch, resume-heal
- **Purpose**: FR-001/R4 — the stamp must be a committed artifact.
- **Steps**: Commit `meta.json` on PRIMARY and seed events on COORD into what lands. Idempotent resume-heal; `status_phase` written last after `verify.ok`. Respect coord/primary partition (the #2920 `SafeCommitHeadMismatch` fold is the cautionary tale). Coordinate with deferred #2923 rather than re-routing `_flip_phase` through the placement port here.

### Subtask T008 – Fail closed on absent mission_id
- **Purpose**: NFR-003/R6 — never slug-namespace seeds.
- **Steps**: Assert `mission_id` present before stamping; if absent, fail closed (non-zero, no seed written), with a clear message.

### Subtask T009 – Red-first: GitHub-squash simulation test [P]
- **Steps**: New test finalizes a fixture mission, runs the accept stamp, simulates a squash merge (plain git, no `spec-kitty merge`) into a target branch, asserts the corpus is cut over with no post-merge command. Write RED first.
- **Files**: `tests/specify_cli/cli/test_accept_birth_cutover.py` (new).

### Subtask T010 – Red-first: idempotency test [P]
- **Steps**: Re-run the accept stamp on an already-cut-over mission; assert no duplicate/divergent seed events (byte-identical `events.jsonl`) and no error (FR-006).

## Test Strategy

Red-first. `PWHEADLESS=1 uv run pytest tests/specify_cli/cli/test_accept_birth_cutover.py -q`, then `-n0 tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` to confirm the acceptance lock stays green.

## Risks & Mitigations

- **R4** stamp not committed / daemon race → explicit commit in the seam; test asserts committed state post-simulated-merge.
- Worktree `.git` redirect → stamp writes stale meta.json. Mitigation: post-verify write + path-contract adherence; test on a worktree fixture.
- Divergent payload vs merge path → depends on WP01; add a cross-caller determinism assertion.

## Review Guidance

Confirm: single-authority `cutover_mission` reuse (no forked writer); both partitions committed; `status_phase` last & post-verify; fail-closed on absent `mission_id`; squash-simulation test genuinely bypasses `spec-kitty merge`; idempotent.

## Activity Log

- 2026-07-27T07:43:31Z – system – Prompt created.
