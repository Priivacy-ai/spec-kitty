# Agent Knowledge Decomposition: {{ agent_name }}

> Purpose: Map source-agent knowledge fragments to doctrine artifact candidates before authoring YAML.

| Field | Value |
|-------|-------|
| Source agent | {{ agent_name }} |
| Owner | {{ owner }} |
| Date | {{ date }} |
| Dossier | {{ source_agent_dossier_link }} |
| Status | Draft / Reviewed / Accepted |

## Decomposition Table

| Source fragment | Artifact kind | Proposed id | Target path | Overlap assessment | Existing artifact (if any) | Decision | Rationale |
|-----------------|---------------|-------------|-------------|--------------------|----------------------------|----------|-----------|
| {{ fragment }} | directive / tactic / procedure / paradigm / styleguide / toolguide / template / agent_profile | {{ id }} | {{ path }} | None / Partial / Strong | {{ artifact_id_or_none }} | New / Augment / Defer | {{ rationale }} |

## Candidate DRG Edges

| Source artifact | Target artifact | Relation | Rationale |
|-----------------|-----------------|----------|-----------|
| {{ source_id }} | {{ target_id }} | requires / suggests / applies / enhances / overrides / specializes_from | {{ rationale }} |

## Open Decisions

| Decision | Owner | Due | Current default |
|----------|-------|-----|-----------------|
| {{ decision }} | {{ owner }} | {{ date }} | {{ default }} |
