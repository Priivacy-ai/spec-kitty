# Data Model: Retrospective Learning Default-On Policy

**Mission**: `retrospective-default-policy-01KS049J` (mission_id `01KS049J4V9CSWBKJHTY2FB69H`)
**Date**: 2026-05-19
**Phase**: 1 — Design

This document specifies the domain entities, fields, relationships, validation rules, invariants, and state transitions introduced or extended by this mission. JSON Schemas for wire/file shapes live in [contracts/](./contracts/).

## Entities

### RetrospectivePolicy

The resolved, runtime-effective policy controlling retrospective behavior for a single mission boundary.

| Field | Type | Cardinality | Description |
|---|---|---|---|
| `enabled` | `bool` | required | Whether retrospective generation runs at all. Default `true`. |
| `timing` | `enum{post_completion, before_completion}` | required | When generation runs relative to mission completion. Default `post_completion`. |
| `failure_policy` | `enum{warn, block}` | required | What to do when generation fails. Default `warn`. |
| `write_record` | `bool` | required | Whether the resolved record is persisted to disk. Default `true`. |
| `generate_proposals` | `bool` | required | Whether the generator emits `proposals[]`. Default `true`. |
| `apply_proposals` | `enum{require_human, low_risk_auto}` | required | Whether the runtime may auto-apply low-risk proposals (`flag_not_helpful` is the only currently-defined low-risk class). Default `require_human`. |
| `permissions` | `RetrospectivePermissions` | required | Granular permission flags (see below). |

#### RetrospectivePermissions

| Field | Type | Description |
|---|---|---|
| `write_record` | `bool` | Generator may write to disk. Default `true`. |
| `inspect_mission_artifacts` | `bool` | Generator may read mission artifacts (specs, plans, status). Default `true`. |
| `propose_glossary_changes` | `bool` | Generator may include glossary-mutation proposals. Default `true`. |
| `propose_drg_changes` | `bool` | Generator may include DRG-mutation proposals. Default `true`. |
| `propose_doctrine_changes` | `bool` | Generator may include doctrine-mutation proposals. Default `true`. |
| `apply_low_risk_changes` | `bool` | Runtime may auto-apply a proposal whose `risk_class == low`. Default `false`. |
| `apply_structural_changes` | `bool` | Runtime may auto-apply structural changes. Default `false`. **MUST stay `false` unless explicitly opted in by the operator.** |

#### Resolution rules

- Resolution order: charter frontmatter → `.kittify/config.yaml#retrospective` → built-in defaults.
- Charter MAY delegate to config via `retrospective.precedence: config`. In that case `.kittify/config.yaml` wins for any field present there, and charter fills the rest.
- The resolver returns `(policy, source_map)` where `source_map: dict[str, str]` maps each leaf field of `policy` to one of:
  - `"<charter-frontmatter-path>:retrospective.<key>"`, e.g. `".kittify/charter/charter.md:retrospective.timing"`
  - `".kittify/config.yaml#retrospective.<key>"`
  - `"<default>"`

#### Invariants

- `apply_structural_changes == true` MUST require an explicit user opt-in via config (not the built-in default). Built-in policy never enables structural auto-apply.
- `failure_policy == block` AND `timing == post_completion` is a *valid but unusual* combination: it blocks mission completion based on a post-completion check. The resolver does not reject it but the CLI surfaces a `WARNING` when this combination is encountered.
- `enabled == false` implies `write_record`, `generate_proposals`, `apply_proposals` are all effectively no-ops. The resolver returns the canonical disabled policy regardless of other fields.

### RetrospectiveRecord

The artifact written to `.kittify/missions/<mission_id>/retrospective.yaml` (or the canonical equivalent path — confirm at implementation time).

| Field | Type | Cardinality | Description |
|---|---|---|---|
| `schema_version` | `int` | required | Currently `1`. Bumped on breaking changes. Additive changes do not bump. |
| `mission_id` | `ULID string` | required | Mission identity. Immutable. |
| `mission_slug` | `string` | required | Human handle, includes `mid8` suffix per the 083 identity model. |
| `mission_number` | `int \| null` | required | Display-only. May be `null` if record authored pre-merge. |
| `friendly_name` | `string` | required | From `meta.json`. |
| `mission_type` | `string` | required | E.g. `software-dev`. |
| `target_branch` | `string` | required | From `meta.json`. |
| `created_at` | `RFC 3339 string` | required | When this record was authored. |
| `created_by` | `Actor` | required | Identity attribution (CLI user, agent ID, etc.). |
| `provenance` | `Provenance` | required | How the record was authored (runtime / explicit `create` / `backfill` / `synthesize_fabricate`). |
| `policy_source` | `dict[str,str]` | required | The `source_map` from the resolver, snapshot at authoring time. |
| `findings_status` | `enum{has_findings, ran_no_findings, missing, failed}` | required | Coarse outcome category. (`missing` and `failed` are reserved for the runtime emit path — see invariants.) |
| `helped` | `list[Finding]` | required | What worked. Empty `[]` permitted; combined with `findings_status` to disambiguate empty vs missing. |
| `not_helpful` | `list[Finding]` | required | What didn't work. |
| `gaps` | `list[Finding]` | required | Missing capabilities or coverage. |
| `proposals` | `list[Proposal]` | required | Concrete improvement suggestions. |
| `evidence_refs` | `list[EvidenceRef]` | required | Pointers to source artifacts (file + range or event range). |
| `generator_version` | `string` | required | Version identifier of the generator that produced this record. Lets future tooling reason about field-by-field freshness. |

#### Sub-types

**Actor**:
```
{ "kind": "human" | "agent" | "runtime", "id": str, "display": str? }
```

**Provenance**:
```
{
  "kind": "runtime_post_completion" | "runtime_strict_gate" | "explicit_create" | "backfill" | "synthesize_fabricate",
  "command": str | null,
  "invoked_at": rfc3339,
  "policy_resolved_from": dict[str,str]   # snapshot of source_map
}
```

**Finding**:
```
{
  "id": str,                     # short stable id within the record, e.g. "h-001"
  "category": str,               # taxonomy: "process" | "tooling" | "spec_quality" | "review_loop" | "design" | "implementation" | "doc" | "other"
  "summary": str,                # one-line plain text
  "details": str | null,         # markdown allowed
  "evidence_refs": list[str]     # ids of EvidenceRef entries
}
```

**Proposal**:
```
{
  "id": str,                     # short stable id within the record, e.g. "p-001"
  "category": str,               # "glossary" | "drg" | "doctrine" | "tooling" | "process" | "other"
  "risk_class": "low" | "structural",
  "summary": str,
  "details": str | null,
  "evidence_refs": list[str],
  "suggested_action": str,       # human-readable; structured action payloads land via synthesize
  "auto_applicable": bool        # True only for risk_class=low AND policy.apply_low_risk_changes
}
```

**EvidenceRef**:
```
{
  "id": str,                     # short stable id, e.g. "e-001"
  "kind": "file" | "event_range" | "external",
  "path": str | null,            # for file: relative path; for event_range: kitty-specs/<slug>/status.events.jsonl
  "range": str | null,           # for file: "L120-L145"; for event_range: "lamport 23..58" or "event_id A..B"
  "url": str | null              # for external: link to external system
}
```

#### Invariants

- `findings_status == "has_findings"` MUST imply at least one of `helped`, `not_helpful`, `gaps`, `proposals` is non-empty.
- `findings_status == "ran_no_findings"` MUST imply all four lists are empty AND the record is still considered a successful run.
- `findings_status == "missing"` and `"failed"` MUST NOT be persisted in a `retrospective.yaml`. They are reserved for **event-payload** representations of "no record on disk" and "generation failed" states. A YAML file with `findings_status: missing` is a corrupt record.
- Every `Finding.evidence_refs[*]` and `Proposal.evidence_refs[*]` MUST resolve to an `id` that exists in the top-level `evidence_refs[]` list.
- `policy_source` is a snapshot — once written, it is not mutated. Re-running the generator on the same mission produces a new record (under `--overwrite`) or a merged record (under `--update`) with a new `policy_source` snapshot.

#### Merge semantics (`retrospect create --update`)

- `helped`, `not_helpful`, `gaps`, `proposals`: deduplicate by `(category, summary)` (case-insensitive summary compare). New entries append; existing entries retain their `id`.
- `evidence_refs`: deduplicate by `(kind, path, range, url)`. New entries append with newly minted `id`s.
- `policy_source`: replaced wholesale with the latest resolution snapshot. The previous snapshot is recorded in `provenance.prior_policy_resolved_from` if it changed.
- `provenance`: replaced with a new `provenance` whose `kind` reflects the update action; an array `provenance_history[]` accumulates prior entries.
- `findings_status` recomputes from final-state lists.

### Event payloads

Two retrospective lifecycle events join the canonical event log. If `spec_kitty_events` already exposes one of these (R-3 in [research.md](./research.md)), reuse it with additive `policy_source` attribution.

#### RetrospectiveCaptured

Fired when generation succeeds and the record is on disk.

```
{
  "type": "RetrospectiveCaptured",
  "schema_version": 1,
  "mission_id": ULID,
  "mission_slug": str,
  "wp_id": null,
  "actor": Actor,
  "at": rfc3339,
  "event_id": ULID,
  "lamport": int,
  "findings_status": "has_findings" | "ran_no_findings",
  "record_path": str,
  "generator_version": str,
  "policy_source": dict[str,str],
  "provenance_kind": "runtime_post_completion" | "runtime_strict_gate" | "explicit_create" | "backfill"
}
```

#### RetrospectiveCaptureFailed

Fired when generation is attempted under default-policy (`warn`) and fails. **Does NOT fire** when policy is `enabled: false` (no attempt is made) or when policy is `block` and the failure aborts completion (the completion-block event itself carries the failure context).

```
{
  "type": "RetrospectiveCaptureFailed",
  "schema_version": 1,
  "mission_id": ULID,
  "mission_slug": str,
  "wp_id": null,
  "actor": Actor,
  "at": rfc3339,
  "event_id": ULID,
  "lamport": int,
  "failure_category": "missing_artifacts" | "generator_exception" | "schema_validation_error" | "io_error" | "other",
  "failure_message": str,
  "remediation_hint": str | null,
  "policy_source": dict[str,str]
}
```

#### Invariants

- For a single mission, the cardinality of `RetrospectiveCaptured` events is ≥ 0. The most recent `RetrospectiveCaptured` is the canonical authoring action; prior ones represent overwrites/updates and stay in the log for audit.
- `RetrospectiveCaptureFailed` is followed eventually by either a successful `RetrospectiveCaptured` (when an operator runs `retrospect create` after fixing the underlying cause) or another `RetrospectiveCaptureFailed`. A `Failed` event does NOT block subsequent attempts.
- Both events are reducer-safe: the existing `specify_cli.status.reducer` does not classify them as state transitions; they are descriptive lifecycle events with no `from_lane`/`to_lane`. Per FR-021, existing reductions remain byte-identical.

### Policy source map

The `source_map` returned by the resolver is a flat `dict[str, str]` keyed by dotted policy paths (`enabled`, `timing`, `failure_policy`, `permissions.write_record`, etc.). Each value points at one of:

- A specific source file + key (`.kittify/config.yaml#retrospective.timing`)
- The literal sentinel `"<default>"` when the field used the built-in default
- The literal sentinel `"<env:SPEC_KITTY_RETROSPECTIVE>"` when an env var supplied the value during the deprecation cycle (FR-015 demotes env vars but does not yet remove them)

The map is serialized into `RetrospectiveRecord.policy_source` and the event payloads.

## State transitions

### Mission completion under default policy

```
mission has all WPs done/approved
  → runtime calls generator(mission, policy)
    → on success:  write retrospective.yaml; emit RetrospectiveCaptured; emit MissionCompleted
    → on failure:  emit RetrospectiveCaptureFailed (warn);     emit MissionCompleted
  → done
```

### Mission completion under strict policy

```
mission ready to complete + policy = before_completion + block
  → runtime calls generator(mission, policy)
    → on success:  write retrospective.yaml; emit RetrospectiveCaptured; emit MissionCompleted
    → on failure:  emit RetrospectiveCaptureFailed;  do NOT emit MissionCompleted; surface structured block reason citing policy_source
    → operator may pass --skip-retrospective (logged with actor/provenance) to bypass; bypass requires explicit permission
```

### `retrospect create` (operator-invoked)

```
record exists?
  → no    : generator runs; writes record; emits RetrospectiveCaptured(provenance=explicit_create)
  → yes   :
    → --overwrite : generator runs; replaces record; emits RetrospectiveCaptured(provenance=explicit_create)
    → --update    : generator runs; merges into existing record per merge semantics; emits RetrospectiveCaptured(provenance=explicit_create, with provenance_history)
    → neither     : error with actionable message; no events emitted
```

### `retrospect backfill` (operator-invoked)

```
for each mission in scope:
  → completed AND on/after --since?
    → no  : skip (do not emit)
    → yes :
      → record exists? skip with reason=already_exists (do not emit unless --emit-skipped passed)
      → generator runs:
        → success : write record; emit RetrospectiveCaptured(provenance=backfill)
        → failure : record failure in CLI JSON output; emit RetrospectiveCaptureFailed only if --emit-failures passed
```

## Relationships

```
RetrospectivePolicy  -----(snapshot via source_map)-----> RetrospectiveRecord.policy_source
                                                         ↓
RetrospectiveRecord  -----(referenced by)-----> RetrospectiveCaptured.record_path
                          (or absence implies)-> RetrospectiveCaptureFailed.failure_message
                                                         ↓
RetrospectiveRecord.proposals[]  ----(consumed by)----> agent retrospect synthesize (preview/apply)
```

## Validation rules

| Rule | Where enforced | Reference |
|---|---|---|
| `RetrospectivePolicy` schema | Resolver (Pydantic or dataclass validator) | FR-001 |
| Defaults applied | Resolver | FR-002 |
| Source map well-formed | Resolver | NFR-007 |
| `apply_structural_changes` opt-in only | Resolver + writer (refuses to write a record with structural auto-applied proposals unless opted in) | C-005 |
| `RetrospectiveRecord` schema | Writer (validates before persisting) | FR-007 |
| Empty findings explicit | Writer + reader | FR-007 |
| Event payload schema | Emitter | NFR-007 |
| Merge semantics deterministic | `retrospect create --update` path | R-6 |

## Out-of-scope additions

- No new mission-identity fields. C-007 preserves the 083+ identity model unchanged.
- No new fields on existing `WPStatusChanged`, `MissionCompleted`, etc. The new retrospective events are siblings, not extensions of existing ones.
- No charter-schema additions beyond the optional `retrospective:` frontmatter block (which existed informally; this mission formalizes it).
