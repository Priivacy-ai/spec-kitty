# Phase 1 Data Model: Template Mapping Resolution

This mission changes in-memory configuration projection and lookup only. It introduces no database, persistent state machine, or external schema migration.

## Entities and Value Objects

### Doctrine MissionType

Canonical authored entity loaded from a doctrine mission-type artifact.

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | Stable mission-type identifier, such as `software-dev` |
| `template_set` | `dict[str, str] | None` | Artifact-kind-to-filename mapping; null declares no built-in content templates |

For the shipped software-development artifact the exact value is:

```yaml
template_set:
  spec: spec-template.md
  plan: plan-template.md
```

Documentation, research, and plan mission types currently declare null. Filesystem presence does not make any entity available; charter activation does.

### ResolvedMissionType

Charter-mediated, runtime-consumable view of one activated doctrine mission type.

| Field | Type | Rules |
|---|---|---|
| `mission_type_id` | `str` | Identifies the activated doctrine source |
| `template_set` | `Mapping[str, str] | None` | Complete deterministic projection of the doctrine value, resolved lazily/cached consistently with other context fields |

Invariants:

1. The resolved mapping equals the doctrine mapping key-for-key and value-for-value.
2. Explicit null remains null.
3. No profile-level default string contributes data.
4. Repeated resolution of the same activated type/configuration yields identical ordered content.
5. Consumers cannot mutate canonical repository state through the resolved view.

### ArtifactKind

A semantic key requested by a content-template reader.

Current in-scope values are `spec` and `plan`. The selector accepts a string-shaped key so doctrine remains extensible, but absence is an explicit outcome rather than an invitation to infer another mission type.

### MappedTemplateFilename

A filename selected from `ResolvedMissionType.template_set`, for example `spec-template.md`. It is not a path and does not encode an override tier.

Validation rules:

- Mapping exists.
- Requested key exists.
- Filename is non-empty and acceptable to the existing resolver's safety rules.

### ResolvedTemplateFile

The effective path/content selected when the existing five-tier resolver searches for `MappedTemplateFilename` under the active mission type and project/user/package context.

## Relationships

```text
activated Doctrine MissionType
        │ exact lazy projection
        ▼
ResolvedMissionType.template_set
        │ lookup by ArtifactKind
        ▼
MappedTemplateFilename
        │ existing five-tier file resolution
        ▼
ResolvedTemplateFile
```

## Resolution Outcomes

| Condition | Outcome |
|---|---|
| Activated type has requested mapping entry and file resolves | Return effective template file using existing precedence |
| Activated type has `template_set: null` | Unavailable/actionable failure naming mission type and artifact kind |
| Mapping omits requested artifact kind | Unavailable/actionable failure naming mission type and artifact kind |
| Mapping contains filename but no permitted tier resolves it | Actionable unresolved-template failure naming mission type and artifact kind |
| Mission type exists on disk but is not activated | It is unavailable to runtime consumers |
| Legacy/meta-less mission reaches reader | Preserve the separately owned compatibility boundary; do not add new inference in this mission |

## State Transitions

None. Resolution is a pure configuration-read operation. Mission lifecycle events and git coordination state are unaffected by this data model.
