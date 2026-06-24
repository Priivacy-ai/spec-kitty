# Live dogfooding repro — finalize-tasks commit-surface misresolution

On this very mission (coord-topology: `coordination_branch` set, `target_branch=feat/gate-read-surface-completion`),
with planning artifacts (spec.md/plan.md) correctly committed to **feat** by spec-commit/setup-plan,
the gate command `finalize-tasks` REFUSED to commit:

> error: Git commit failed: Refusing to commit planning artifacts to the protected branch 'main'.

i.e. finalize-tasks resolved its planning-commit surface to the **repo primary `main`** (protected),
NOT the mission's `target_branch` (`feat/...`) where the other planning artifacts live. This is the
**write-side twin** of the FR-001/FR-002 read divergence — a gate command misresolving the surface vs
the write commands. Strengthens the mission's red-first basis (the WRITE path of finalize-tasks, beyond
the READ path the spec enumerates). Candidate: add finalize-tasks commit-surface to the FR-004/FR-009 site map.
Worked around by flattening (removing coordination_branch) to proceed with tasks finalization.

## Update: flatten did NOT help; it is the COMMIT-surface, not topology

Removing `coordination_branch` (flatten) did not change the refusal — `finalize-tasks`
resolves its planning-commit branch to the repo primary `main` **regardless of topology
or current branch** (I am standing on `feat`, where spec-commit/setup-plan committed
fine). So this is a **write-side residual on finalize-tasks's COMMIT path** that #2106
did not re-point: the #2106 FR-008 protected-primary guard then correctly refuses (main
is protected), but the resolution to `main` is the bug — it should be the mission's
`target_branch` (`feat`). debbie's site map listed finalize-tasks as "primary-anchored
READ = OK"; its COMMIT/WRITE is NOT ok. **Add finalize-tasks commit-surface to the
FR-004/FR-009 site map.** Workaround for THIS mission: manual `git commit` of the
finalize-tasks output to `feat` (all artifacts generated correctly on disk; only the
commit was refused). Implement phase likely hits the same class → run flattened with
manual status-surface handling (per [[project_flat_mission_implement_loop_friction]]).
