# Data Model: TeamSpace Mission-State Repair

## Audit Report (JSON)

Output of `spec-kitty doctor mission-state --audit --json`:

```json
{
  "total_missions": <int>,
  "missions_with_teamspace_blockers": <int>,
  "teamspace_blockers": <int>,
  "blocker_counts_by_code": {
    "<blocker_code>": <int>
  },
  "unexpected_errors": [<string>]
}
```

Acceptance gate: `missions_with_teamspace_blockers == 0` and `teamspace_blockers == 0`.

## Repair Manifest (written by --fix)

Location: `.kittify/migrations/mission-state/<timestamp>-repair.json` (or similar)

Required fields (per start-here.md WP03 acceptance):
- `repo_head`: git commit SHA at repair time
- `checksums`: map of affected file paths → SHA256
- `row_transformations`: count of rows modified
- `quarantine_count`: count of quarantined rows
- `quarantine_list`: list of quarantined row identifiers (if any)
- `validation_results`: summary of post-repair validation

## Dry-Run Output (JSON)

Output of `spec-kitty doctor mission-state --teamspace-dry-run --json`:

```json
{
  "envelopes_synthesized": <int>,
  "envelope_validation_errors": [],
  "side_logs_skipped": <int>,
  "status_transitions_synthesized": <int>
}
```

Acceptance gate: `envelope_validation_errors` is empty; `side_logs_skipped >= 0`; no runtime log appears as a status transition.

## Invariants

- Repair is deterministic: same repo HEAD → same checksums → same output in any clone.
- Valid canonical IDs are never rewritten.
- Legacy shape fields (`feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, `work_package_id`) are removed from TeamSpace-bound rows after repair.
- Quarantine is explicit: any row that cannot be repaired is listed, never silently dropped.
