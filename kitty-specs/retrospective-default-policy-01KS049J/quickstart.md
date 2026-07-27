# Quickstart: Retrospective Learning Default-On Policy

**Mission**: `retrospective-default-policy-01KS049J`
**Phase**: 1 — Quickstart

This quickstart is for operators of a Spec Kitty project after this mission ships. It assumes the operator has run `spec-kitty upgrade` to pick up the new commands and policy schema.

## The 30-second mental model

| What | Where it lives | Authored by |
|---|---|---|
| **Policy** (whether/when/how-to-fail) | `.kittify/config.yaml#retrospective` or charter frontmatter | Operator (durable config) |
| **Record** (`retrospective.yaml`) | `.kittify/missions/<mission_id>/` | Runtime (default), or `spec-kitty retrospect create` / `backfill` |
| **Summary** (aggregation across records) | stdout / JSON | `spec-kitty retrospect summary` (read-only) |
| **Proposal application** | Doctrine/DRG/glossary mutations gated by human approval | `spec-kitty agent retrospect synthesize` (preview/apply) |

## The default path (you do nothing)

With no `retrospective:` block in `.kittify/config.yaml`, every completed mission produces a `retrospective.yaml` automatically:

```bash
# Normal mission completion
spec-kitty merge --feature my-feature

# After merge, the runtime authored:
#   .kittify/missions/<mission_id>/retrospective.yaml
# and emitted a RetrospectiveCaptured event in the mission's status.events.jsonl.

# Inspect the record
cat .kittify/missions/$(jq -r .mission_id kitty-specs/my-feature-01J6XW9K/meta.json)/retrospective.yaml

# Aggregate across all completed missions
spec-kitty retrospect summary
```

If generation fails (e.g. mission lacks an event log), the runtime emits a `RetrospectiveCaptureFailed` event and prints a one-line warning. Mission completion is NOT blocked. Author later via `spec-kitty retrospect create --mission <handle>`.

## The opt-out path

To turn off all retrospective behavior:

```yaml
# .kittify/config.yaml
retrospective:
  enabled: false
```

No generator runs at any boundary. No warnings. No events.

## The strict path (governed projects)

To require a successful retrospective before mission completion can proceed:

```yaml
# .kittify/config.yaml  OR  charter frontmatter
retrospective:
  enabled: true
  timing: before_completion
  failure_policy: block
```

Mission completion blocks if generation fails. The block message cites the resolved policy source so operators know which file/key drives the gate.

To skip the gate for a single completion:

```bash
spec-kitty merge --feature my-feature --skip-retrospective
```

`--skip-retrospective` requires an explicit permission and logs actor/provenance in the event log.

## Authoring a retrospective on demand

For a single completed mission:

```bash
# Default: errors if record exists
spec-kitty retrospect create --mission my-feature-01J6XW9K

# Replace an existing record
spec-kitty retrospect create --mission my-feature-01J6XW9K --overwrite

# Merge into an existing record (deduplicates by (category, summary))
spec-kitty retrospect create --mission my-feature-01J6XW9K --update

# JSON output for tooling
spec-kitty retrospect create --mission my-feature-01J6XW9K --json
```

`<handle>` accepts `mission_id` (ULID), `mid8` (8-char prefix), or `mission_slug`. The resolver disambiguates by `mission_id`; ambiguous handles produce a `MISSION_AMBIGUOUS_SELECTOR` structured error listing candidates.

## Backfilling historical records

After upgrading from a pre-3.2.0 project, populate retrospectives for old completed missions:

```bash
# Preview (no writes)
spec-kitty retrospect backfill --since 2026-01-01 --dry-run

# Apply
spec-kitty retrospect backfill --since 2026-01-01

# Single mission
spec-kitty retrospect backfill --mission my-old-feature

# Include skipped/failed candidates in the event log (useful for dashboards)
spec-kitty retrospect backfill --since 2026-01-01 --emit-skipped --emit-failures
```

Existing records are never silently overwritten by backfill. Use `retrospect create --overwrite` per mission for that.

## Reviewing and applying proposals

A `retrospective.yaml` may contain `proposals[]` with suggested changes to glossary, DRG, doctrine, etc. Applying them stays human-approved by default:

```bash
# Preview proposals
spec-kitty agent retrospect synthesize --mission my-feature-01J6XW9K --preview

# Apply a specific proposal
spec-kitty agent retrospect synthesize --mission my-feature-01J6XW9K --apply p-001
```

Structural changes (doctrine, DRG, glossary) always require explicit `--apply`. Low-risk proposals (`flag_not_helpful`) may auto-apply when policy explicitly enables it:

```yaml
# .kittify/config.yaml — enable auto-apply for low-risk only
retrospective:
  apply_proposals: low_risk_auto
  permissions:
    apply_low_risk_changes: true
```

## Migration from env vars (deprecated)

If your shell or CI sets `SPEC_KITTY_RETROSPECTIVE=1` or `SPEC_KITTY_MODE=autonomous`:

| Old env var | New durable config |
|---|---|
| `SPEC_KITTY_RETROSPECTIVE=1` | `retrospective.enabled: true` (this is the default — usually you can just unset the env var) |
| `SPEC_KITTY_RETROSPECTIVE=0` | `retrospective.enabled: false` |
| `SPEC_KITTY_MODE=autonomous` | `retrospective.timing: before_completion` AND `retrospective.failure_policy: block` |

Env vars still work this release cycle but emit a one-time deprecation warning per process. Durable config wins when both are present. Suppress the warning in CI with `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1` once you've migrated.

## What the new commands DON'T do

- `spec-kitty retrospect summary` — read-only aggregation. Does NOT author or mutate any record.
- `spec-kitty agent retrospect synthesize` — preview/apply proposals from an *existing* record. Does NOT author records. If invoked on a mission with no record, errors with a pointer at `retrospect create`. The legacy "fabricate empty record" path is preserved behind `--fabricate-empty` but is no longer the default.
- The runtime — does NOT mutate doctrine, DRG, or glossary automatically. Generation produces a record with proposals; application is a separate human-approved step.

## Verifying your install

```bash
# Confirm CLI exposes the new commands
spec-kitty retrospect --help              # should list create, backfill, summary
spec-kitty retrospect create --help       # should show --overwrite, --update, --json

# Confirm policy resolution
spec-kitty agent retrospect policy --json   # shows resolved policy + source map (if surfaced)
```

If `spec-kitty retrospect` reports "No such command", run `spec-kitty upgrade` and re-check.

## Common errors

| Symptom | Likely cause | Fix |
|---|---|---|
| `RETROSPECTIVE_RECORD_EXISTS` | Existing record on disk; called `create` without flag | Pass `--overwrite` or `--update` |
| `MISSION_NOT_COMPLETED` | Some WPs still in non-terminal lanes | Complete mission first, or accept open WPs as known |
| `MISSION_AMBIGUOUS_SELECTOR` | Handle resolves to multiple missions | Use `mission_id` (ULID) or `mid8` instead of slug |
| Mission completion blocks with `RETROSPECTIVE_GATE_BLOCKED` | Policy is `before_completion + block` and generation failed | Inspect `RetrospectiveCaptureFailed` event in `status.events.jsonl` for `remediation_hint`; address and retry |
| Deprecation warning keeps firing | Env var set in shell/CI | Unset env var; rely on `.kittify/config.yaml` |
| `cannot import name 'normalize_event_id' from 'spec_kitty_events'` during pytest collection (locally only) | Local PEP 420 namespace-package corruption from a partial pip uninstall — NOT a wheel bug | `uv sync --reinstall-package spec-kitty-events` per [CONTRIBUTING.md](../../CONTRIBUTING.md) |

## Test-runner commands

For contributors validating this mission's behavior:

```bash
uv run pytest tests/retrospective/ -q                                                          # unit
uv run pytest tests/integration/retrospective/ -q                                              # integration
uv run pytest tests/next/test_retrospective_terminus_wiring.py -q                              # wiring
uv run pytest tests/agent/test_orchestrator_commands_integration.py::TestAcceptMission -q      # accept-mission regression
uv run ruff check src tests                                                                    # lint
```

## See also

- [spec.md](./spec.md) — full mission spec
- [plan.md](./plan.md) — implementation plan
- [research.md](./research.md) — decision rationale
- [data-model.md](./data-model.md) — entity shapes
- [contracts/](./contracts/) — JSON schemas + CLI/event contracts
- `docs/how-to/use-retrospective-learning.md` (will be updated by FR-018) — operator how-to
- `docs/explanation/retrospective-learning-loop.md` (will be updated by FR-018) — conceptual explanation
