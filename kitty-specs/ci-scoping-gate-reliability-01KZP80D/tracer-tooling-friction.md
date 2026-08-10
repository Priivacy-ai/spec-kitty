# Tracer: Tooling Friction — ci-scoping-gate-reliability

Every place the tooling fought us (feeds the tooling-gap backlog). Append during implement.

## Planning phase (2026-08-10)

- **The bug itself is a tooling gap:** CI silently skips corpus suites on data-only PRs (no signal that
  a whole class of tests never ran) — a false-green the path-filter design did not guard. #3008.
- **The two-gate structure was non-discoverable without a code trace:** the trigger-allowlist omission
  (Gate 0) is separate from the dorny-group gap (Gate 1); a naive "add a dorny group" fix would look
  right but be inert. Required a squad to surface.
- **Arch-invariant gates run only in CI's integration-core-misc job**, not the fast local suites — a
  path-filter/census regression passes local runs and only fails at CI. Must run `tests/architectural/`
  before pushing.
