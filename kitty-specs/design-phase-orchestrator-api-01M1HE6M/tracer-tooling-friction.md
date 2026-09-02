# Tracer: Tooling Friction — design-phase-orchestrator-api-01M1HE6M

Seeded at plan phase (2026-09-02). Appended during implementation; assessed at close.

## Plan phase

None yet. `spec-kitty plan --mission design-phase-orchestrator-api-01M1HE6M --json` ran
cleanly, non-interactively, and returned the expected scaffold-state envelope
(`plan_file`, `feature_dir`, `spec_file`, `planning_base_branch` all correctly resolved
to the feature branch given this mission's `single_branch` topology). No blocking issue
reading the spec (983 lines, read in full), the operator ruling, the charter, or
`AGENTS.md`.

One minor observation, not friction exactly: the task instructions asked to "confirm"
`CLAUDE.md`'s Shared Package Boundary guidance (`src/runtime/next/_internal_runtime/` as
canonical runtime home) against the actual tree and against where the FR-014 functions'
real dependencies live. That confirmation surfaced a genuine nuance CLAUDE.md's one-line
summary doesn't capture: `_internal_runtime/` is a closed set of internalized-package
DAG-engine re-exports, not a general extension point, while the TOP LEVEL of
`src/runtime/next/` (`decision.py`, `runtime_bridge.py`) is where CLI-domain-importing
next-invocation orchestration code already lives. This is recorded as a design decision
(`tracer-design-decisions.md` #1), not filed as friction — CLAUDE.md's guidance was
correct at the level it was written, just not granular enough to answer "which exact
file inside `src/runtime/next/`," which is precisely the kind of question a plan phase
exists to resolve rather than escalate.
