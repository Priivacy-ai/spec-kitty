# Research: Recover Missing Lane Workspaces

## Question

Does #2626 remain reproducible on the current planning base, and which existing authority owns each observed failure without inventing a shared cross-command resolver?

## Evidence Summary

The exact recoverable arm—relative stale record, missing worktree directory, matching lane branch still present—appears substantially repaired on the planning base. Focused existing coverage across workspace-husk preparation, move-task placement/authority staging, and mark-status is green (54 tests). That does not close the Mission: full `agent action review` still claims and commits `for_review → in_review` before it prepares the workspace, while review also resolves workspace state twice. A later preparation failure can therefore leave status/WP evidence changed after the command fails.

The three reported entry points have distinct owners:

| Entry point | Existing owner | Workspace need | Allowed stale-record outcome |
|---|---|---|---|
| `mark-status` | TASKS_INDEX commit routing in `tasks_mark_status.py` | None for lane execution | Clean success with no event/lane delta; stale lane metadata is a negative control. |
| `move-task` | WORK_PACKAGE_TASK/status routing in `tasks_move_task.py` | Conditional for deliverable/pre-review checks | Clean success only when its required checks and commits complete; otherwise truthful non-zero/structured refusal. |
| `agent action review` | review claim transaction plus workspace preparation in `workflow.py` / `workflow_executor.py` | Required | Matching existing branch may be reattached/recreated; unavailable or divergent authority must refuse before claim mutation. |

## Decisions

### D1 — One fixture contract, distinct implementation seams

Use one real persisted-context fixture and one six-surface observation contract across entry points. Do not build a shared stale-workspace implementation seam unless the RED witness proves a shared owner. This preserves FR-007 and avoids absorbing #2160.

### D2 — Resolve and establish readiness before mutation where required

Each command path that already requires an execution workspace obtains one reconciled `ResolvedWorkspace` result before durable mutation. Review passes that same value through readiness/materialization and execution; lifecycle helpers do not recompose a competing branch/path from `lanes.json`. `mark-status` remains workspace-free and proves stale lane metadata is irrelevant to TASKS_INDEX routing.

### D3 — Recovery classification

A missing worktree may be reattached/recreated only when the canonical lane branch exists and agrees with the current assignment. If branch authority is absent or divergent, refuse before event/WP mutation and name the missing workspace plus supported recovery. This is narrower than falling back to the primary checkout and does not relax `safe_commit`.

### D4 — Executable consistency proof

The witness snapshots:

1. CLI exit/result and stdout/JSON envelope;
2. `status.events.jsonl` bytes and reduced/materialized lane;
3. WP/tasks bytes;
4. primary, coordination, and lane ref HEADs plus each new commit's path set;
5. lock files and missing-path existence;
6. porcelain for every relevant checkout.

The acceptance witness allows no production monkeypatching. Fixture construction may use canonical serializers, environment isolation, and cache clearing; the registered Typer command, root discovery, placement, lifecycle, commit/status, and Git subprocess paths all remain real.

## Candidate REDs

- **Review ordering**: `workflow.py` claims review before `_prepare_review_workspace`; preparation failure can occur after durable mutation.
- **Double resolution / path disagreement**: persisted context wins in `workspace/context.py`, but lifecycle sync can independently compose a path from lanes metadata.
- **Raw missing-cwd probe**: `lanes/lifecycle_sync.py` can run a Git probe with a missing worktree as `cwd` when both branch and worktree are absent.
- **Move-task commit truth**: durable status can precede WP commit; commit failure becomes a warning while final output remains success. This is in scope only if the production-shaped stale fixture triggers it.

## Existing Partial Coverage

- `tests/integration/test_lane_lifecycle_sync.py`: missing worktree with branch present; does not cover branch plus worktree absent.
- `tests/specify_cli/cli/commands/test_workspace_husk_resolution_1833.py`: helper-level preparation outcomes; bypasses full review ordering and persisted-context lookup.
- `tests/agent/test_workflow_review_lane_gate.py`: status rollback on sync refusal; does not prove restoration/cleanliness of the PRIMARY WP file.
- Move-task placement/authority and mark-status suites cover healthy canonical routing but not one full stale-context CLI matrix.

## Scope Boundaries

#2160 and #2367 are reference-only and already owned elsewhere. Exclude merge VCS locks, upgrade-worktree coherence, registry/doctor redesign, path-security variants, generic commit-warning redesign, `safe_commit` relaxation, and release work unless the exact witness proves unavoidable same-seam ownership.

## Open Risks for Planning

- The recoverable historical arm may be GREEN while only the stricter unavailable/divergent branch arm is RED; results must be reported separately.
- Cross-placement compensation is risky. Prefer readiness before mutation over adding rollback when possible.
- The real CLI fixture is more expensive than helper tests; isolate reusable setup and keep per-entry-point expectations explicit.
