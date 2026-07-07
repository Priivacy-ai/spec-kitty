# Work Packages: Session-scoped test reaper + /tmp prompt namespacing + workspace-context tombstone

**Mission**: `session-reaper-and-tmp-leak-hygiene-01KWWAE7` | **Issues**: #1842 (subsumes #1634) | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Subtask Format: `[Txxx] Description (WP)`

## Path Conventions
Repo-root-relative. Three cohesive WPs: WP02 (runtime `/tmp` namespacing) owns the shared temp-namespace constant that WP01 (test-side reaper) imports; WP03 (runtime workspace-context tombstone) is independent.

| Subtask | Description | WP | Requirement |
| --- | --- | --- | --- |
| T001 | Shared temp-namespace constant/module (single source of truth for the `/tmp` prompt prefix) | WP02 | FR-003 |
| T002 | Route `prompt_builder.py` (`spec-kitty-next-*`) through the shared namespace | WP02 | FR-003 |
| T003 | Route `decision.py` (both `spec-kitty-composed-*` `mkstemp` sites) through the shared namespace | WP02 | FR-003 |
| T004 | Route `workflow.py` (`spec-kitty-implement\|review-*`) through the shared namespace | WP02 | FR-003 |
| T005 | Drift-proof test: a writer's output path falls under the reaper's swept root; namespacing green | WP02 | FR-003, FR-006 |
| T006 | `pytest_sessionstart` narrow name-pattern snapshot (NOT deep rglob) in root `tests/conftest.py` | WP01 | FR-001, C-001 |
| T007 | `pytest_sessionfinish` controller-gated snapshot-delta reaper: `test-feature-*` dirs+branches + git-unregistered `.worktrees/` husks | WP01 | FR-001, NFR-001/002 |
| T008 | Reaper `/tmp` sweep: current-run `spec-kitty-{next,implement,review,composed}-*` (via the shared constant) + `spec-kitty-test-homes/<run_uid>/` (N1) | WP01 | FR-002 |
| T009 | Retire `.gitignore:143-144` masks; add reap-then-assert pollution assertion | WP01 | FR-004 |
| T010 | Reaper unit tests: seed→reap; pre-existing NOT touched (both directions); pollution reds on seeded leak | WP01 | FR-006, SC-002/003 |
| T011 | Verify the cancel seam + worktree-persists-through-cancel; pin `emit_status_transition`/`tasks_transition_core` | WP03 | FR-005 |
| T012 | Cancel-transition hook: gate on all-lane-WPs-terminal (mirror `doctor.py`), map WP→lane `workspace_name`, `delete_context` | WP03 | FR-005 |
| T013 | Merge-completion tombstone hook AFTER `executor.py`'s worktree removal (~:749) | WP03 | FR-005 |
| T014 | Remove the 14 committed `059-*`/`060-*` `.kittify/workspaces/*.json` orphans | WP03 | FR-005 |
| T015 | LC-6 regression: a merged/cancelled mission leaves no orphan context JSON; merge/cancel semantics preserved | WP03 | FR-005, FR-006, SC-004 |

---

## Work Package WP02: /tmp prompt-writer namespacing (Priority: P1)
**Prompt**: `/tasks/WP02-tmp-prompt-namespacing.md`
**Goal**: The three flat-`/tmp` prompt writers write under one shared, per-repo/per-run-namespaced, sweepable temp-root (single-source-of-truth constant), stopping the unbounded `spec-kitty-next-*`/`spec-kitty-composed-*` accumulation.
### Included Subtasks
- [x] T001 Shared temp-namespace constant (WP02)
- [x] T002 prompt_builder.py through the namespace (WP02)
- [x] T003 decision.py (both sites) through the namespace (WP02)
- [x] T004 workflow.py through the namespace (WP02)
- [x] T005 Drift-proof test + green (WP02)
### Dependencies
None. (Owns the shared constant that WP01 imports.)
### Risks & Mitigations
- Consumers read the returned path — preserve the return contract; don't break the runtime `next` loop.

## Work Package WP01: Session reaper + mask retirement + pollution assertion (Priority: P1)
**Prompt**: `/tasks/WP01-session-reaper.md`
**Goal**: A controller-gated `pytest_sessionfinish` snapshot-delta reaper that self-heals all test-created REPO_ROOT + `/tmp` residue (importing WP02's shared constant for the prompt prefix), retires the `.gitignore` masks, and makes a leak regression visible via reap-then-assert.
### Included Subtasks
- [ ] T006 sessionstart narrow snapshot (WP01)
- [ ] T007 sessionfinish reaper: dirs/branches/worktrees (WP01)
- [ ] T008 reaper /tmp sweep (shared constant + test-homes) (WP01)
- [ ] T009 retire .gitignore masks + pollution assertion (WP01)
- [ ] T010 reaper unit tests (seed/preserve/pollution) (WP01)
### Dependencies
WP02 (imports the shared temp-namespace constant for the `/tmp` sweep).
### Risks & Mitigations
- Worker races → controller gate (`workerinput is None`). Deleting pre-existing → snapshot-delta. `prune`-blind husks → explicit `rmtree` of the delta. Slow/false-red → narrow name-pattern snapshot, not deep `rglob`.

## Work Package WP03: LC-6 workspace-context tombstone (Priority: P2)
**Prompt**: `/tasks/WP03-workspace-context-tombstone.md`
**Goal**: Tombstone `.kittify/workspaces/*.json` on merge-completion (after worktree removal) + cancel (targeted `delete_context` via the transition hub, gated on all-lane-terminal), and remove the 14 committed orphans.
### Included Subtasks
- [x] T011 Verify cancel seam + worktree persistence (WP03)
- [x] T012 Cancel-transition tombstone hook (WP03)
- [x] T013 Merge-completion tombstone hook (after worktree removal) (WP03)
- [x] T014 Remove the 14 committed orphans (WP03)
- [x] T015 LC-6 regression + semantics preserved (WP03)
### Dependencies
None.
### Risks & Mitigations
- Ordering (pre-removal cleanup finds a live worktree → no-op) → hook after removal. Cancel no-op trap → targeted `delete_context`. Preserve merge/cancel semantics (C-004).
