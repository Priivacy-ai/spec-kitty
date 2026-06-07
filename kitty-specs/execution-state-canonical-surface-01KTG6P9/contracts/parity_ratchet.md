# Contract — full-sequence e2e parity ratchet

Extends `tests/architectural/test_execution_context_parity.py` from the status read+write slice to the full command sequence across all execution modes.

## Sequence under test

`next → implement → move-task → review → status`

## Modes (fixtures)

1. **main-checkout CWD** — sequence driven from the repository root.
2. **lane-worktree CWD** — sequence driven from `.worktrees/<mission>-<mid8>-lane-a/`.
3. **direct-to-target** — mission run with no worktree, target branch used directly.

## Assertions

For each adjacent pair of modes, the following must be **identical**:
- resolved WP identity (from `resolve_action_context`)
- lane transitions emitted (event identity / ordering)
- `agent tasks status --json` output

Plus:
- **Mode-correct branch**: direct-to-target resolves the declared target branch; a resolved mainline write without explicit authorization is refused (C-001, FR-012).

## Negative control (non-vacuity — FR-022)

A deliberately reverted surface that re-derives context independently MUST make the ratchet fail. Mirror the existing `test_ratchet_catches_divergence` / `test_write_ratchet_catches_divergence` injection proofs for the full sequence.

## Docstring (FR-023)

The module docstring states the **actual** coverage (full sequence × 3 modes). It must not imply coverage the test lacks.

## CI gate (FR-024)

Required for PRs touching: `mission_runtime/`, `src/specify_cli/status/`, `src/runtime/next/`, `src/specify_cli/cli/commands/agent/`.
