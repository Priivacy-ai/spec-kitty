# Contract: `retrospective.yaml` schema v1

**Status**: pinned for this tranche.
**Source of truth**: `specify_cli.retrospective.schema` (Pydantic v2 models).
**Mirrored from**: [../data-model.md](../data-model.md).

This contract is normative. Any change requires a `schema_version` bump and a documented compatibility shim.

---

## Canonical path

```
.kittify/missions/<mission_id>/retrospective.yaml
```

`<mission_id>` is the canonical ULID from the mission's `meta.json`. The display-only `mission_number` MUST NOT appear in the path. (Spec FR-009, C-014.)

---

## Top-level YAML shape

```yaml
schema_version: "1"
mission:
  mission_id: 01KQ6YEGT4YBZ3GZF7X680KQ3V
  mid8: 01KQ6YEG
  mission_slug: mission-retrospective-learning-loop-01KQ6YEG
  mission_type: software-dev
  mission_started_at: 2026-04-27T07:46:18.715532+00:00
  mission_completed_at: 2026-04-27T11:00:00+00:00
mode:
  value: human_in_command
  source_signal:
    kind: charter_override
    evidence: "charter:mode-policy:hic-default"
status: completed              # completed | skipped | failed | pending(*)
started_at: 2026-04-27T10:55:00+00:00
completed_at: 2026-04-27T11:00:00+00:00
actor:
  kind: human
  id: rob@robshouse.net
  profile_id: null
helped: [...]                  # list of Finding (may be empty)
not_helpful: [...]             # list of Finding (may be empty)
gaps: [...]                    # list of Finding (may be empty)
proposals: [...]               # list of Proposal (may be empty)
provenance:
  authored_by: { kind: agent, id: claude-opus-4-7, profile_id: retrospective-facilitator }
  runtime_version: 3.2.0
  written_at: 2026-04-27T11:00:00+00:00
  schema_version: "1"
# Optional, status-conditional:
# skip_reason: "low-value docs fix"           # required iff status == skipped
# failure: { code: writer_io_error, ... }      # required iff status == failed
# successor_mission_id: null                   # set when this record is superseded
```

`status: pending` is **not persistable**. The writer refuses to materialize a pending record. (NFR-002.)

---

## `Finding` shape

```yaml
- id: F-01
  target:
    kind: drg_edge                # see allowed kinds below
    urn: "drg:edge:doctrine_directive_003->action_specify"
  note: "Directive 003 over-fired during research-only steps; surfaced no-op evidence."
  provenance:
    source_mission_id: 01KQ6YEGT4YBZ3GZF7X680KQ3V
    evidence_event_ids:
      - 01KQ6YE...A
      - 01KQ6YE...B
    actor:
      kind: agent
      id: claude-opus-4-7
      profile_id: retrospective-facilitator
    captured_at: 2026-04-27T10:58:00+00:00
```

Allowed `target.kind` values:

```
doctrine_directive | doctrine_tactic | doctrine_procedure
drg_edge | drg_node
glossary_term
prompt_template
test
context_artifact
```

`provenance.evidence_event_ids` MUST contain at least one entry. A mission that produced zero usable events MUST result in an empty `helped`/`not_helpful`/`gaps` list, not in synthetic evidence.

---

## `Proposal` shape (envelope)

```yaml
- id: 01KQ6YE...P1
  kind: add_glossary_term       # see allowed kinds below
  payload:
    # kind-specific; see "Proposal payload schemas" below
  rationale: "Term 'lifecycle terminus hook' was missing in 4/5 missions."
  state:
    status: pending             # pending | accepted | rejected | applied | superseded
    decided_at: null
    decided_by: null
    apply_attempts: []
  provenance:
    source_mission_id: 01KQ6YEGT4YBZ3GZF7X680KQ3V
    source_evidence_event_ids: [01KQ6YE...C]
    authored_by: { kind: agent, id: claude-opus-4-7, profile_id: retrospective-facilitator }
    approved_by: null
```

Allowed `kind` values (closed set; any unlisted future kind defaults to **staged** per Q2-A):

```
synthesize_directive | synthesize_tactic | synthesize_procedure
rewire_edge | add_edge | remove_edge
add_glossary_term | update_glossary_term
flag_not_helpful
```

---

## Proposal payload schemas (per kind)

Pinned minimums. Implementations may add fields; they MUST NOT remove these.

### `synthesize_directive` / `synthesize_tactic` / `synthesize_procedure`

```yaml
payload:
  artifact_id: <directive_or_tactic_or_procedure_id>     # e.g. "DIRECTIVE_NEW_EXAMPLE"
  body: |
    <markdown body>
  body_hash: sha256:...                                  # normalized-body hash for conflict detection (R-006)
  scope:
    actions: [...]                                       # action ids this artifact applies to
    profiles: [...]                                      # profile ids this artifact applies to
```

### `add_edge` / `remove_edge`

```yaml
payload:
  edge:
    from_node: drg:node:<urn>
    to_node: drg:node:<urn>
    kind: <edge_kind>                                    # closed enum from src/doctrine/graph.yaml
```

### `rewire_edge`

```yaml
payload:
  edge_old:
    from_node: drg:node:<a>
    to_node: drg:node:<b>
    kind: <edge_kind>
  edge_new:
    from_node: drg:node:<a>
    to_node: drg:node:<c>
    kind: <edge_kind>
```

`edge_old` and `edge_new` MUST share `from_node` and `kind`. Otherwise this is a `remove_edge` + `add_edge`.

### `add_glossary_term` / `update_glossary_term`

```yaml
payload:
  term_key: lifecycle-terminus-hook
  definition: |
    <markdown definition>
  definition_hash: sha256:...
  related_terms: []
```

### `flag_not_helpful`

```yaml
payload:
  target:
    kind: <Target.kind>                                  # see Finding target kinds
    urn: <urn>
```

`flag_not_helpful` is the only **auto-applicable** kind (Q2-A, FR-020). Auto-application still records a `ProposalApplyAttempt` and writes provenance.

---

## Required vs. optional fields (canonical list)

For an automated reader, the explicit lists:

**Required** at top level:
```
schema_version, mission, mode, status, started_at, actor,
helped, not_helpful, gaps, proposals, provenance
```

**Optional** at top level (status-conditional):
```
completed_at      # required iff status in (completed, skipped, failed)
skip_reason       # required iff status == skipped
failure           # required iff status == failed
successor_mission_id
```

**Required** on every `Finding`:
```
id, target, note, provenance
```

**Required** on every `Proposal`:
```
id, kind, payload, rationale, state, provenance
```

---

## Forward-compatibility rules

- Adding a field at any level is a non-breaking change; readers MUST ignore unknown fields silently.
- Removing or renaming a required field is a breaking change; bump `schema_version` and ship a compatibility shim.
- Adding a new proposal `kind` is a non-breaking change for readers; the synthesizer's auto-apply allowlist remains closed (`{flag_not_helpful}`) by default. (FR-020.)
- Adding a new `target.kind` is a non-breaking change for readers; calibration updates may be needed.

---

## Privacy

`provenance.evidence_event_ids` are opaque references to entries in the mission event log. The schema disallows embedding payload content from those events directly into the retrospective record. Redaction at the event-log layer therefore propagates without the retrospective record needing modification. (CHK019, Open Risk: privacy of evidence references.)
