# CLI Contract: `spec-kitty retrospect *`

**Mission**: `retrospective-default-policy-01KS049J`
**Phase**: 1 — Contracts

This contract specifies the user-facing surfaces this mission adds to or changes on the `spec-kitty retrospect` and `spec-kitty agent retrospect` namespaces. JSON output shapes are stable contracts.

## `spec-kitty retrospect create`

Author a retrospective for one completed mission.

### Usage

```
spec-kitty retrospect create --mission <handle> [--overwrite | --update] [--json]
```

| Flag | Type | Description |
|---|---|---|
| `--mission <handle>` | required | `mission_id` (ULID), `mid8`, or `mission_slug`. Resolver disambiguates by `mission_id`; ambiguous handles return `MISSION_AMBIGUOUS_SELECTOR`. |
| `--overwrite` | optional | Replace an existing record. Mutually exclusive with `--update`. |
| `--update` | optional | Merge into an existing record per the merge semantics in [data-model.md](../data-model.md#merge-semantics-retrospect-create---update). Mutually exclusive with `--overwrite`. |
| `--json` | optional | Emit a JSON contract (below). When absent, emit a Rich human-readable summary. |

### Exit codes

- `0` — record authored (or merged) successfully.
- `1` — error (record already exists without `--overwrite`/`--update`, mission not completed, missing artifacts, validation failure, etc.).
- `2` — invalid invocation (bad flags, ambiguous mission handle).

### JSON output (success)

```json
{
  "result": "success",
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "mission_slug": "my-feature-01J6XW9K",
  "record_path": "/abs/path/.kittify/missions/<mission_id>/retrospective.yaml",
  "findings_status": "has_findings",
  "counts": {"helped": 4, "not_helpful": 2, "gaps": 1, "proposals": 3, "evidence_refs": 10},
  "provenance_kind": "explicit_create",
  "policy_source": {"enabled": "<default>", "timing": "<default>", "failure_policy": "<default>"},
  "next_step": "Run `spec-kitty agent retrospect synthesize --mission <handle> --preview` to review proposals."
}
```

### JSON output (error: record already exists)

```json
{
  "result": "blocked",
  "code": "RETROSPECTIVE_RECORD_EXISTS",
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "mission_slug": "my-feature-01J6XW9K",
  "record_path": "/abs/path/.kittify/missions/<mission_id>/retrospective.yaml",
  "blocked_reason": "A retrospective record already exists for this mission. Pass --overwrite to replace it or --update to merge.",
  "exit_code": 1
}
```

### JSON output (error: mission not completed)

```json
{
  "result": "blocked",
  "code": "MISSION_NOT_COMPLETED",
  "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
  "mission_slug": "my-feature-01J6XW9K",
  "blocked_reason": "Mission has WPs in non-terminal lanes: WP02 (in_progress), WP04 (for_review). Complete the mission before authoring a retrospective.",
  "open_wps": [{"wp_id": "WP02", "lane": "in_progress"}, {"wp_id": "WP04", "lane": "for_review"}],
  "exit_code": 1
}
```

### Side effects

- On success: writes the YAML record at `record_path`; appends a `RetrospectiveCaptured` event to `kitty-specs/<mission_slug>/status.events.jsonl` (or the canonical event log path the runtime uses).
- On `--update`: appends to `provenance_history[]` in the record, replaces top-level `provenance` and `policy_source`.
- Auto-commit policy: if `.kittify/config.yaml#agents.auto_commit: true` (the project default), the record + event log change are committed with a structured message. Otherwise the operator commits.

---

## `spec-kitty retrospect backfill`

Author records for historical missions.

### Usage

```
spec-kitty retrospect backfill [--since <ISO-date>] [--until <ISO-date>] [--mission <handle>]
                               [--dry-run] [--emit-skipped] [--emit-failures] [--json]
```

| Flag | Type | Description |
|---|---|---|
| `--since <ISO-date>` | optional | Only consider missions whose completion timestamp ≥ this date. Default: 30 days ago. |
| `--until <ISO-date>` | optional | Only consider missions whose completion timestamp ≤ this date. Default: now. |
| `--mission <handle>` | optional | Restrict to a single mission. Skips other missions in scope. |
| `--dry-run` | optional | Report what would be authored without writing. |
| `--emit-skipped` | optional | Append a `RetrospectiveCaptured` event with provenance noting the skip. Default: skips are CLI-output only. |
| `--emit-failures` | optional | Append `RetrospectiveCaptureFailed` events for failed candidates. Default: failures are CLI-output only. |
| `--json` | optional | Emit JSON contract (below). |

### Exit codes

- `0` — all candidates processed cleanly (some may have been skipped or failed; aggregate report in stdout).
- `1` — fatal error (e.g. malformed `.kittify/config.yaml`, missing critical infrastructure). Per-mission failures are NOT fatal.
- `2` — invalid invocation.

### JSON output

```json
{
  "result": "success",
  "window": {"since": "2026-01-01", "until": "2026-05-19"},
  "scanned": 47,
  "created": 12,
  "skipped": [
    {"mission_id": "...", "mission_slug": "...", "reason": "already_exists", "record_path": "..."},
    {"mission_id": "...", "mission_slug": "...", "reason": "not_completed"},
    {"mission_id": "...", "mission_slug": "...", "reason": "out_of_window"}
  ],
  "failed": [
    {"mission_id": "...", "mission_slug": "...", "failure_category": "missing_artifacts", "missing": ["status.events.jsonl"], "remediation_hint": "Mission lacks an event log; rebuild via `spec-kitty migrate normalize-lifecycle --mission <handle>`."}
  ],
  "next_actions": [
    "Run `spec-kitty agent retrospect synthesize --mission <handle> --preview` on newly authored records.",
    "Inspect the 1 failed mission listed above."
  ]
}
```

### Side effects

- Per successful candidate: writes record; emits `RetrospectiveCaptured` event.
- Per skipped/failed candidate: CLI output only unless `--emit-skipped` / `--emit-failures` are passed.
- Auto-commit policy: identical to `create` if `--dry-run` is absent.

---

## `spec-kitty retrospect summary`

**No semantic change in this mission.** This contract clarifies the read-only invariant.

### Contract

- `summary` MUST NOT author, mutate, or write any retrospective record.
- `summary` MUST distinguish four record states in its output: `has_findings`, `ran_no_findings`, `missing` (no record on disk), `failed` (most recent `RetrospectiveCaptureFailed` not followed by a `RetrospectiveCaptured`).
- JSON output shape per the existing `retrospect summary` contract, with two added fields: `policy_source` (snapshot from the most recent attribution event) and `findings_status` (per record).

---

## `spec-kitty agent retrospect synthesize`

Tighten the fabrication fallback.

### Default behavior (changed)

When invoked on a mission with no `retrospective.yaml`:

```
{
  "result": "blocked",
  "code": "RETROSPECTIVE_RECORD_MISSING",
  "mission_id": "...",
  "mission_slug": "...",
  "blocked_reason": "No retrospective record found for this mission. Author one with: spec-kitty retrospect create --mission <handle>",
  "exit_code": 1
}
```

### Compatibility flag (preserved)

When invoked with `--fabricate-empty` on a mission with no `retrospective.yaml`, the legacy fabrication path runs and authors a `findings_status: ran_no_findings` record with `provenance.kind = "synthesize_fabricate"`. The action is logged in the event log with actor attribution.

### All other modes (unchanged)

`--preview`, `--apply <proposal_id>`, default proposal listing — identical wire contract to today. The only change is the default-path error and the new `--fabricate-empty` flag.

---

## Env-var deprecation contract (FR-015, NFR-006)

- `SPEC_KITTY_RETROSPECTIVE` and `SPEC_KITTY_MODE` continue to be honored as test/dev overrides.
- First use per process emits a single `DeprecationWarning` AND a single Rich stderr notice (controlled by `SPEC_KITTY_NO_DEPRECATION_WARNINGS=1`).
- Durable policy always wins when both env and config/charter are present. The deprecation warning still emits in that case.
- The warning text MUST cite the durable replacement key path (`retrospective.enabled` or `retrospective.timing`+`retrospective.failure_policy`) AND link to `docs/how-to/use-retrospective-learning.md`.

## Cross-references

- Schemas: [retrospective-policy.schema.json](./retrospective-policy.schema.json), [retrospective-record.schema.json](./retrospective-record.schema.json)
- Event contracts: [retrospective-events.contract.md](./retrospective-events.contract.md)
- Operator quickstart: [../quickstart.md](../quickstart.md)
