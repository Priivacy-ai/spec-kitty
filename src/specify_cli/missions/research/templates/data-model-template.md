# Data Model (Discovery Draft)

Use this skeleton to capture entities, attributes, and relationships uncovered during research. Update it as the solution space becomes clearer; implementation will refine and extend it.

## Entities

### Entity: <!-- e.g., Customer -->
- **Description**: <!-- Summary -->
- **Attributes**:
  - `field_name` (type) – purpose / constraints
- **Identifiers**: <!-- Primary / alternate keys -->
- **Lifecycle Notes**: <!-- Creation, updates, archival -->

### Entity: <!-- e.g., Account -->
- **Description**:
- **Attributes**:
  - `field_name` (type) – purpose / constraints
- **Identifiers**:
- **Lifecycle Notes**:

## Relationships

| Source | Relation | Target | Cardinality | Notes |
|--------|----------|--------|-------------|-------|
| <!-- e.g., Customer --> | <!-- owns --> | <!-- Account --> | <!-- 1:N --> | <!-- Business rules --> |

## Validation & Governance

- **Data quality requirements**: <!-- e.g., null-handling, accepted ranges -->
- **Compliance considerations**: <!-- PII, retention policies, regional restrictions -->
- **Source of truth**: <!-- Systems or datasets authoritative for each entity -->

> Treat this as a working model. When research uncovers new flows or systems, update the entities and relationships immediately so the implementation team inherits up-to-date context.