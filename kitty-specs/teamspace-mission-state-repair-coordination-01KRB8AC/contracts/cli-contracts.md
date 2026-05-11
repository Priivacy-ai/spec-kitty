# CLI Contracts: TeamSpace Mission-State Repair

## Contract 1: Baseline audit must produce machine-readable JSON

**Command**: `spec-kitty doctor mission-state --audit --json`
**Must**: Exit 0 (or non-zero only if unexpected non-repairable errors exist).
**Must produce**: JSON with keys `total_missions`, `missions_with_teamspace_blockers`, `teamspace_blockers`, `blocker_counts_by_code`.
**Must NOT**: Mutate any files.

## Contract 2: Repair must be deterministic and idempotent

**Command**: `spec-kitty doctor mission-state --fix`
**Must**: Write a manifest to `.kittify/migrations/mission-state/`.
**Must**: Produce identical output when run again on the same repo state (idempotency).
**Must**: Remove legacy fields (`feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, `work_package_id`) from TeamSpace-bound rows.
**Must NOT**: Rewrite existing valid canonical IDs.
**Must NOT**: Use random IDs or wall-clock timestamps in deterministic outputs.
**Must NOT**: Run if relevant git paths are dirty (unless `--allow-dirty` is passed).

## Contract 3: Post-repair audit must show zero TeamSpace blockers

**Command**: `spec-kitty doctor mission-state --audit --json` (post-fix)
**Must**: Return `missions_with_teamspace_blockers == 0`.
**Must**: Return `teamspace_blockers == 0`.

## Contract 4: Dry-run must pass envelope validation

**Command**: `spec-kitty doctor mission-state --teamspace-dry-run --json`
**Must**: Synthesize envelopes without network I/O.
**Must**: Return `envelope_validation_errors == []`.
**Must**: Report runtime side logs as `side_logs_skipped`, not as status transitions.
**Must**: Validate envelopes against `spec-kitty-events==5.0.0`.

## Contract 5: Repair PR body requirements

Each repair PR **must** include:
- Baseline audit summary (from `before.audit.json`)
- Post-repair audit summary (from `after.audit.json`)
- Dry-run command and result (from `dry-run.json`)
- Manifest path under `.kittify/migrations/mission-state/`
- Links to `spec-kitty#979` and `spec-kitty#920`
