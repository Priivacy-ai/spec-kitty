# Contract — Pack-validator advisory rules

**Backed by**: FR-010 .. FR-014, R-9

## Detection precedence

Given a pack artifact (tactic / styleguide / paradigm / procedure / agent-profile) with `id == X`:

1. **Both `overrides: Y` and `enhances: Z` declared** → `intent_conflict` ERROR. Message: `"overrides and enhances are mutually exclusive on <kind> <id>"`. No further checks for this artifact.

2. **`overrides: Y` declared, Y not a built-in `<kind>` ID** → `unknown_target` ERROR. Message: `"<kind> <id> declares overrides: <Y>, but no built-in <kind> with that id exists"`.

3. **`enhances: Z` declared, Z not a built-in `<kind>` ID** → `unknown_target` ERROR. Message: `"<kind> <id> declares enhances: <Z>, but no built-in <kind> with that id exists"`.

4. **Either field declared and target valid** → advisory suppressed for this artifact. DRG auto-emits the corresponding edge.

5. **Neither field declared, ID matches a built-in `<kind>`** → `same_id_collision` ADVISORY (reworded). Message: `"artifact id '<id>' will field-merge into the built-in <kind> — declare 'enhances: <id>' to suppress this advisory, or 'overrides: <id>' to declare a full replacement"`.

6. **Neither field declared, ID does NOT match a built-in `<kind>`** → no advisory (pack-only artifact, normal case).

## DRG edge auto-emission (FR-014)

When `enhances: tactic-y` is set on pack tactic `tactic-x`, the following
edge is auto-emitted into the pack's DRG fragment:

```yaml
# pydantic_model: doctrine.drg.models.DRGEdge
# expect: valid
source: tactic:tactic-x
target: tactic:tactic-y
relation: enhances
reason: "declared via tactic.enhances field"
```

When `overrides: tactic-y` is set on pack tactic `tactic-x`:

```yaml
# pydantic_model: doctrine.drg.models.DRGEdge
# expect: valid
source: tactic:tactic-x
target: tactic:tactic-y
relation: overrides
reason: "declared via tactic.overrides field"
```

Same pattern for the other four artifact kinds, using the appropriate URN prefix (`styleguide:`, `paradigm:`, `procedure:`, `agent_profile:`).

## CLI JSON shape

`spec-kitty doctrine pack validate --json` extends the existing `ValidationIssue` list:

```json
{
  "ok": false,
  "issues": [
    {
      "severity": "error",
      "category": "intent_conflict",
      "artifact_type": "tactics",
      "artifact_id": "context-boundary-inference",
      "file": "/path/to/pack/tactics/context-boundary-inference.tactic.yaml",
      "message": "overrides and enhances are mutually exclusive on tactic context-boundary-inference"
    },
    {
      "severity": "error",
      "category": "unknown_target",
      "artifact_type": "tactics",
      "artifact_id": "team-topology-tactic",
      "file": "...",
      "message": "tactic team-topology-tactic declares enhances: foo-bar-tactic, but no built-in tactic with that id exists"
    },
    {
      "severity": "advisory",
      "category": "same_id_collision",
      "artifact_type": "tactics",
      "artifact_id": "secure-design-checklist",
      "file": "...",
      "message": "artifact id 'secure-design-checklist' will field-merge into the built-in tactic — declare 'enhances: secure-design-checklist' to suppress this advisory, or 'overrides: secure-design-checklist' to declare a full replacement"
    }
  ]
}
```

## Exit code

`ok: false` (at least one ERROR) → exit non-zero. ADVISORY-only output → exit zero.
