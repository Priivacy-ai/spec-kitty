# Contract: `spec-kitty glossary validate` Command

## CLI Interface

```
spec-kitty glossary validate <path> [--json]
```

### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | `Path` | yes | File path to a single `.yaml` seed file, or directory path to validate all `*.yaml` files under it |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | `bool` | `false` | Output validation results as JSON instead of rich table |

### Behavior

**File path**: Validates the single seed file. Reports errors or success.

**Directory path**: Discovers all `*.yaml` files in the directory. For each file:
1. Validates the filename maps to a known `GlossaryScope` (warns on unknown filenames)
2. Validates the file contents against the `GlossarySeedFile` schema
3. Reports per-file errors

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All files valid |
| 1 | One or more validation errors found |

### Human Output (default)

```
Validating .kittify/glossaries/spec_kitty_core.yaml...

  ✗ term[3] 'Sonar quality gate' → surface: surface must be normalized
    (lowercase, trimmed): got 'Sonar quality gate', expected 'sonar quality gate'

  ✗ term[7] → definition: definition must not be empty

2 error(s) in .kittify/glossaries/spec_kitty_core.yaml

Validating .kittify/glossaries/team_domain.yaml...
  ✓ Valid (12 terms)

Summary: 1 of 2 files failed validation.
```

### JSON Output (`--json`)

```json
{
  "files": [
    {
      "path": ".kittify/glossaries/spec_kitty_core.yaml",
      "valid": false,
      "term_count": 15,
      "errors": [
        {
          "term_index": 3,
          "term_surface": "Sonar quality gate",
          "field": "surface",
          "message": "surface must be normalized (lowercase, trimmed): got 'Sonar quality gate', expected 'sonar quality gate'"
        },
        {
          "term_index": 7,
          "term_surface": null,
          "field": "definition",
          "message": "definition must not be empty"
        }
      ]
    },
    {
      "path": ".kittify/glossaries/team_domain.yaml",
      "valid": true,
      "term_count": 12,
      "errors": []
    }
  ],
  "total_files": 2,
  "valid_files": 1,
  "invalid_files": 1
}
```

## Dashboard API Changes

### `/api/glossary-health` Response

Adds optional `validation_errors` field to existing `GlossaryHealthResponse`:

```json
{
  "total_terms": 0,
  "active_count": 0,
  "draft_count": 0,
  "deprecated_count": 0,
  "high_severity_drift_count": 0,
  "orphaned_term_count": 0,
  "entity_pages_generated": false,
  "entity_pages_path": null,
  "last_conflict_at": null,
  "validation_errors": [
    {
      "file": ".kittify/glossaries/spec_kitty_core.yaml",
      "term_index": 3,
      "term_surface": "Sonar quality gate",
      "field": "surface",
      "message": "surface must be normalized (lowercase, trimmed)"
    }
  ]
}
```

When no validation errors exist, `validation_errors` is `null` (not present in response for backward compatibility with existing consumers that don't expect the field).

### `/api/glossary-terms` Response

**Valid state** (unchanged): Returns bare array `[...]`

**Validation error state**: Returns bare empty array `[]` (same as current behavior) with errors logged server-side. Dashboard HTML will check the health endpoint for `validation_errors` to display error state.
