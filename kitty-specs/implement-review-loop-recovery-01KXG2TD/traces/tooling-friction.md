# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

## Entries

- 2026-07-14 — GitHub ticket intake through `mission create --from-ticket` required hosted Spec Kitty authentication even though `gh` was authenticated, so canonical ticket context could not be generated.
- 2026-07-14 — The canonical planning prompt passed `--mission` to `agent mission branch-context`, but the installed 3.2.5 command rejected that option.
- 2026-07-14 — Discarding an accidentally main-bound Mission created a retrospective commit on local main and left its scaffold untracked; local main had to be restored to `origin/main` before recreating the PR-bound Mission.
- 2026-07-14 — The PR-bound coordination worktree is registered as healthy but lacks the Mission directory, and workspace repair does not populate it; planning remains on the dedicated fix branch.
- 2026-07-14 — Two open-ended planning subagent attempts stalled without producing artifacts; the orchestrator resumed from verified code-truth findings.
- 2026-07-14 — Several open issue facets were already delivered on the planning base, requiring commit and focused-test reconciliation before scope could be trusted.
- 2026-07-14 — The repository shell did not expose `pytest` directly despite the documented command; validation required the managed `uv run pytest` entry point.
- 2026-07-14 — Post-plan code-truth review found the apparent pre-mutation hook was preceded by lane-deliverable auto-commit, and timeout was erased into `no_coverage`; the first plan had to be structurally revised before tasks.
- 2026-07-14 — `finalize-tasks` committed generated `tasks.md`, WP prompt, and lane metadata but omitted the authoritative `wps.yaml`; it must be committed separately through the planning artifact workflow.
- 2026-07-14 — A read-only post-tasks reviewer accidentally reran mutating finalization, producing timestamp-only metadata churn; the final content was retained while the transient commit was folded during landing cleanup, and no further reviewer mutations were allowed.
- 2026-07-14 — Fresh lane validation required `uv run --extra test`; the global transition interpreter lacked pytest and truthfully reported `no_coverage` while the explicit managed-environment suite passed.
- 2026-07-14 — Runtime claim needed root projections of coordination-owned status and analysis artifacts, but the analysis projection later blocked review handoff. Keeping canonical coordination copies and removing only proven temporary projections unblocked the workflow.
- 2026-07-14 — Exact-entry interruption testing needed a real Git topology plus Linux subreaper ownership: synchronize the actual Typer command inside its pytest gate, kill that command, and explicitly reap its orphaned runner child before asserting authoritative state.
- 2026-07-14 — Windows descendant cleanup requires `taskkill /PID <owned-parent> /T`, followed by `/T /F` for bounded escalation; direct `Popen.terminate()`/`kill()` does not cover descendants.
- 2026-07-14 — Approval refused an unstructured cycle-1 review and unresolved issue matrix. Recovery required parseable review artifacts, a preserved rejection plus explicit override, and terminal evidence for each referenced issue.
- 2026-07-14 — Post-merge architectural review requires Git-subprocess test modules to use `pytest.mark.git_repo`, not `pytest.mark.fast`; corrected in the final implementation commit after rebasing onto current `origin/main`.
- 2026-07-14 — Cross-repo E2E failures reproduce against `origin/main`: contract drift is masked by a missing nested `build` dependency (E2E #327), and the dependent-WP floor scenario cannot run unauthenticated or from a baseline worktree (E2E #326). The SaaS floor scenario needs an operator-configured endpoint or schema-valid exception.
- 2026-07-14 — The architectural surface audit has a planning-base inventory undercount for `_wp04_bite_witness`; recorded as #2638 before treating it as baseline context.
