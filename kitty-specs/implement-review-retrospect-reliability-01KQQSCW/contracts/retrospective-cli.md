# Contract: Completed-Mission Retrospective Missing-Record Path

## Scope

This contract covers #965.

## Command Surface

Existing:

- `spec-kitty agent retrospect synthesize --mission <mission> --json`

Allowed addition:

- `spec-kitty agent retrospect capture --mission <mission> --json`
- or `spec-kitty agent retrospect init --mission <mission> --json`

## Required JSON Outcomes

Every JSON response for missing-record handling must be parseable and include:

- `command`.
- `mission_id` or resolvable mission identity when available.
- `mission_slug` when available.
- `status`.
- `outcome`.
- `next_action` when operator action is required.

Outcome values:

- `retrospective_record_created`.
- `retrospective_synthesized`.
- `insufficient_mission_artifacts`.
- `mission_not_found`.

## Behavior

### Missing Mission

Return a structured JSON outcome with `outcome="mission_not_found"` and no Python traceback.

### Completed Mission With Missing Record and Sufficient Artifacts

Either:

- synthesize initializes the record and continues, returning `retrospective_record_created` and/or `retrospective_synthesized`; or
- capture/init creates the record and synthesize reports the command to run.

### Completed Mission With Missing Record and Insufficient Artifacts

Return `outcome="insufficient_mission_artifacts"` with the missing artifact list and a human-actionable `next_action`.

### Existing Record

Preserve existing synthesize behavior and proposal application semantics.

## Regression Coverage

- Missing `retrospective.yaml` no longer emits only `record_not_found`.
- JSON output parses for all required outcomes.
- Missing mission is distinct from missing retrospective record.
- Created records go through `retrospective.writer.write_record`.
