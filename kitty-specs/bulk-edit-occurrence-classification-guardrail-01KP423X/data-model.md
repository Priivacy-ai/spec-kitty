# Data Model: Bulk Edit Occurrence Classification Guardrail

**Date**: 2026-04-13
**Mission**: bulk-edit-occurrence-classification-guardrail-01KP423X

## Entities

### 1. Mission Metadata — `change_mode` field

**Location**: `kitty-specs/<mission>/meta.json`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `change_mode` | `str \| None` | No | `None` (absent) | Declares the mission's edit sensitivity. `"bulk_edit"` triggers the occurrence classification guardrail. |

**Constraints**:
- When present, must be one of: `"bulk_edit"` (only defined value in v1)
- When absent or `null`: mission is not occurrence-sensitive — no guardrail applies
- Backward compatible: existing missions without this field are unaffected

### 2. Occurrence Map — `occurrence_map.yaml`

**Location**: `kitty-specs/<mission>/occurrence_map.yaml`

**Purpose**: Machine-readable classification of target tokens by occurrence category with per-category change actions. Created during planning, before implementation begins.

#### Schema

```yaml
# Required: What is being changed
target:
  term: "constitution"              # The primary token being changed
  replacement: "charter"            # What it becomes (if applicable)
  operation: "rename"               # Operation type: rename | remove | deprecate

# Required: Where the token appears and what to do in each context
categories:
  code_symbols:                     # Python/TS/JS class, function, variable names
    action: rename                  # rename | manual_review | do_not_change | rename_if_user_visible
    notes: ""                       # Optional: additional context for implementers

  import_paths:                     # from X import Y, import X
    action: rename
    notes: ""

  filesystem_paths:                 # Path literals in code, config path references
    action: manual_review
    notes: "Review each path individually — some are on-disk locations"

  serialized_keys:                  # Dict keys, YAML keys, JSON field names, API fields
    action: do_not_change
    notes: "Changing serialized keys breaks existing data"

  cli_commands:                     # CLI command names, subcommand names, flags
    action: do_not_change
    notes: "CLI surface is a public API — requires deprecation cycle"

  user_facing_strings:              # Log messages, error messages, docstrings, comments, docs
    action: rename_if_user_visible
    notes: "Rename in user-visible docs; preserve in internal logs if they serve as search keys"

  tests_fixtures:                   # Test assertions, fixture data, snapshot files
    action: rename
    notes: "Tests should reflect the new terminology"

  logs_telemetry:                   # Telemetry labels, metric names, structured log keys
    action: do_not_change
    notes: "Changing telemetry labels breaks dashboards and alerts"

# Optional: Specific files or patterns that are exceptions to the category rules
exceptions:
  - path: "src/specify_cli/migrations/*.py"
    reason: "Migration files are historical records — never modify"
    action: do_not_change

  - path: "CHANGELOG.md"
    reason: "Historical changelog entries should not be rewritten"
    action: do_not_change

# Optional: Approval/review status
status:
  reviewed_by: "claude"             # Who reviewed the classification
  reviewed_at: "2026-04-13T18:00:00+00:00"  # When
  accepted: true                    # Whether the classification has been accepted
```

#### Validation Rules

| Rule | Check | Error if violated |
|------|-------|-------------------|
| `target` section exists | Key present and non-empty | "Occurrence map missing 'target' section" |
| `target.term` is non-empty string | Type + length check | "Target term must be specified" |
| `target.operation` is valid | In `{rename, remove, deprecate}` | "Invalid target operation" |
| `categories` section exists | Key present and non-empty | "Occurrence map missing 'categories' section" |
| At least 1 category defined | Length >= 1 | "At least one occurrence category must be defined" |
| Every category has `action` | Each entry has `action` key | "Category '{name}' missing 'action' field" |
| Every `action` is valid | In `{rename, manual_review, do_not_change, rename_if_user_visible}` | "Invalid action '{action}' for category '{name}'" |
| No unknown top-level keys | Warn on keys outside `{target, categories, exceptions, status}` | Warning only (forward-compatible) |

#### Admissibility Criteria (for review gate)

The occurrence map is **admissible** (sufficient to unblock implementation/review) when:
1. All validation rules pass (structurally complete)
2. The `target.term` is specific (not a placeholder like "TODO" or "TBD")
3. At least 3 categories are classified (a real bulk edit touches multiple contexts)

### 3. Inference Keywords

**Location**: Compiled into `src/specify_cli/bulk_edit/inference.py`

| Weight | Keywords |
|--------|----------|
| 3 (high) | `rename across`, `bulk edit`, `codemod`, `find-and-replace`, `replace everywhere`, `terminology migration`, `rename all occurrences` |
| 2 (medium) | `rename`, `migrate`, `replace all`, `across the codebase`, `globally`, `sed`, `search and replace` |
| 1 (low) | `update`, `change`, `modify`, `refactor` |

**Threshold**: Score >= 4 triggers inference warning.

### 4. Doctrine Directive

**Location**: `src/doctrine/directives/shipped/035-bulk-edit-occurrence-classification.directive.yaml`

| Field | Value |
|-------|-------|
| `id` | `DIRECTIVE_035` |
| `title` | Bulk Edit Occurrence Classification |
| `intent` | Codebase-wide renames and terminology migrations must classify string occurrences by semantic context before edits begin |
| `enforcement` | `required` |
| `scope` | Missions marked `change_mode: bulk_edit` |
| `tactic_refs` | `occurrence-classification-workflow` |

## State Transitions

### Implement Gate Decision Flow

```
implement WP## invoked
  ↓
load_meta(feature_dir)
  ↓
change_mode == "bulk_edit"?
  ├─ No → check inference warning (advisory)
  │        ↓
  │        spec contains rename/migration keywords?
  │        ├─ No → PASS (proceed to implement)
  │        └─ Yes → emit warning, require acknowledgement
  │                 ├─ Acknowledged → PASS
  │                 └─ Not acknowledged → BLOCK
  └─ Yes → check occurrence_map.yaml
           ↓
           file exists?
           ├─ No → BLOCK ("Occurrence map required for bulk_edit missions")
           └─ Yes → validate structure
                    ↓
                    structurally complete?
                    ├─ No → BLOCK ("Occurrence map incomplete: {specific errors}")
                    └─ Yes → admissible?
                             ├─ No → BLOCK ("Occurrence map not admissible: {reasons}")
                             └─ Yes → PASS (proceed to implement)
```

### Review Gate Decision Flow

```
review WP## invoked
  ↓
load_meta(feature_dir)
  ↓
change_mode == "bulk_edit"?
  ├─ No → PASS (standard review, no occurrence check)
  └─ Yes → check occurrence_map.yaml
           ↓
           file exists AND structurally complete AND admissible?
           ├─ No → REJECT ("Review cannot proceed: occurrence map missing or incomplete")
           └─ Yes → PASS (review proceeds with occurrence map as governing artifact)
```

## Relationships

```
meta.json
  └── change_mode: "bulk_edit" ─── triggers ──→ occurrence_map.yaml requirement
                                                  │
                                                  ├── gates ──→ implement action
                                                  ├── gates ──→ review action
                                                  └── referenced by ──→ doctrine directive

spec.md
  └── content keywords ─── triggers ──→ inference warning (advisory)
                                          │
                                          └── gates (soft) ──→ implement action
```
