# Contract: Tracker Bind (Post-Cutover)

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06

## Bind Payload

The `project_identity` dict sent during tracker bind operations:

```json
{
  "uuid": "project-uuid",
  "slug": "project-slug",
  "node_id": "node-uuid",
  "repo_slug": "repo-slug",
  "build_id": "build-uuid"
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `uuid` | string (UUID) | Project identity |
| `slug` | string | Project slug |
| `node_id` | string (UUID) | Causal emitter identity (Lamport ordering) |
| `repo_slug` | string | Repository slug |
| `build_id` | string (UUID) | Checkout/worktree identity |

## Change from Current

Added: `build_id` (previously absent from tracker bind payload).

All other fields unchanged.
