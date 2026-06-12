# Quickstart — validating 01KTYGTE

- FR-001: fixture repo with spec committed ONLY on the coord branch → `setup-plan` passes the committed-spec gate.
- FR-002: run `spec-kitty accept` twice (incl. --no-commit mode) on an unchanged accepted mission → second run converges, no git_dirty trip.
- FR-003/FR-008: query an unresolvable handle / a declared-coord-with-deleted-branch mission → structured errors with next_step (no stub, no crash, no silent primary fallback).
- FR-004: run the two pinning tests (flattened-#1889 fixture; fully-planned-#1885 fixture) → green.
- FR-005/006/007: `python -m pytest tests/architectural/test_topology_resolution_boundary.py -q` green AND rogue-injection proofs documented in the WP notes.
- FR-010: `spec-kitty doctrine validate` on the three artifacts; doctrine suite green.
- FR-011: both governance-contract tests + 3 charter assertions + twelve-agent parity green with regenerated baselines; ADR shows "executed" addendum.
- FR-012: `spec-kitty doctrine regenerate-graph --check` fresh; graph has the +~27 suggests edges; toolguide schema accepts references.
