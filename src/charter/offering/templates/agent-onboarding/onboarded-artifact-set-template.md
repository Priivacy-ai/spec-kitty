# Onboarded Artifact Set: {{ agent_name }}

> Purpose: Record the final doctrine artifacts created or updated during external-agent onboarding.

| Field | Value |
|-------|-------|
| Source agent | {{ agent_name }} |
| Owner | {{ owner }} |
| Date | {{ date }} |
| Dossier | {{ source_agent_dossier_link }} |
| Decomposition table | {{ decomposition_table_link }} |
| Validation status | Not run / Passed / Passed with advisories / Failed |

## Created Artifacts

| Artifact kind | Artifact id | Path | DRG node present? | Notes |
|---------------|-------------|------|-------------------|-------|
| {{ kind }} | {{ artifact_id }} | {{ path }} | Yes / No | {{ notes }} |

## Updated Artifacts

| Artifact kind | Artifact id | Change summary | DRG edge changes |
|---------------|-------------|----------------|------------------|
| {{ kind }} | {{ artifact_id }} | {{ summary }} | {{ edges }} |

## Validation Evidence

| Check | Result | Evidence |
|-------|--------|----------|
| Pack validation | Passed / Failed | {{ command_or_link }} |
| DRG regeneration | Passed / Failed | {{ command_or_link }} |
| Sensitivity scan | Passed / Failed | {{ command_or_link }} |

## Handoff Notes

Summarise remaining risks, deferred decisions, and reviewer instructions.
