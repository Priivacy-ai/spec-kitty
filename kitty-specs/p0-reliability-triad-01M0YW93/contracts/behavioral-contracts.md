# Behavioral Contracts (per WP)

CLI/behavioral contracts (no HTTP surface in this mission).

## C-WP01 — activation write-target contract (#3282)
- GIVEN a pointer-charter project, WHEN `spec-kitty upgrade` provisions default mission-type activations, THEN the activations are written to the resolved effective authority (`charter.yaml`) such that `PackContext.from_config(project).activated_mission_types` is non-empty.
- The dry-run/`--json` "provisioning pending" predicate MUST agree with the resolved write target (no false "not pending" for pointer projects).
- An authored empty activation list is preserved (idempotent, additive).

## C-WP02 — stale-lane remediation contract (#3579)
- WHEN the merge stale-lane halt emits remediation for a planning lane with a `status.json` conflict, THEN the remediation names `spec-kitty agent status materialize --mission <id>` (+ `git add`) as a reachable resolution.
- The remediation MUST NOT instruct hand-editing a tool-generated file and MUST NOT introduce a `status.json` merge driver (T013 arch guard stays green).

## C-WP03 — allocator retry & ancestry contract (#3281)
- WHEN lane allocation is retried over a pre-existing worktree, THEN the idempotent self-heal re-runs planning-commit and dependency-tip merges (no short-circuit on `workspace.exists`).
- WHEN fresh-path allocation's planning-commit merge conflicts, THEN no registered worktree remains (atomic rollback).
- WHEN the claim/dependency gate runs, THEN `claimed` is emitted only if the recorded planning SHA and every approved dependency lane tip are git ancestors of workspace HEAD.
- A retry over an already-correct worktree is a no-op resume (not re-gated).
