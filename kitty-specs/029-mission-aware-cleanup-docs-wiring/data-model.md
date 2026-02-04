# Data Model: Mission-Aware Cleanup & Docs Wiring

## Entities

### Script Source of Truth
- **Purpose**: Defines the authoritative script entrypoints used by tests and packaged templates.
- **Key Attributes**:
  - `path_root`: `src/specify_cli/scripts/`
  - `entrypoints`: validate-encoding, debug-dashboard-scan, tasks_cli, tasks helpers
- **Relationships**: Referenced by tests and template packaging logic.

### Documentation State
- **Purpose**: Persisted metadata in `meta.json` for documentation mission features.
- **Key Attributes**:
  - `iteration_mode`
  - `divio_types_selected`
  - `generators_configured`
  - `target_audience`
  - `last_audit_date`
  - `coverage_percentage`
- **Relationships**: Updated by gap analysis; validated during acceptance/validation.

### Gap Analysis Report
- **Purpose**: Audit artifact of documentation coverage and missing areas.
- **Key Attributes**:
  - `framework_detected`
  - `coverage_matrix`
  - `gaps_prioritized`
  - `generated_at` (ISO 8601 timestamp)
- **Relationships**: Generated during plan/research; required for acceptance validation.

### Mission Type
- **Purpose**: Governs mission-aware behavior in CLI flows.
- **Key Attributes**:
  - `name` (software-dev, documentation)
  - `artifacts_required`
  - `validation_rules`
- **Relationships**: Gates when documentation tooling executes.
