# Use the `wps.yaml` Manifest

Learn about the structured work-package manifest format introduced in 3.1.0 and how it fits into the `finalize-tasks` workflow.

## What is `wps.yaml`?

`wps.yaml` is a machine-readable manifest at `kitty-specs/<mission>/wps.yaml`. It is the authoritative structured source of work-package definitions, replacing the previous approach of extracting dependency graphs by parsing prose in `tasks.md`.

## Why It Exists

Before `wps.yaml`, `finalize-tasks` had to parse natural-language task descriptions to extract dependency graphs and file ownership. This was fragile: ambiguous phrasing, markdown formatting changes, or prose rewrites would silently alter the computed lane graph.

`wps.yaml` replaces that unbounded prose-parser with a structured contract: the LLM writes the manifest directly during `/spec-kitty.tasks-outline`, and `finalize-tasks` reads it deterministically.

## Fields

```yaml
# kitty-specs/042-auth-system/wps.yaml
wps:
  - id: WP01
    title: "Set up database schema"
    dependencies: []          # present and empty = no deps; never overwritten
    owned_files:
      - src/models/user.py
      - migrations/0001_initial.py
    requirement_refs:
      - spec.md#auth-schema
    subtasks:
      - "Create User model"
      - "Write migration"
    prompt_file: tasks/WP01.md

  - id: WP02
    title: "Implement login endpoint"
    dependencies: [WP01]
    owned_files:
      - src/views/auth.py
    requirement_refs:
      - spec.md#login-flow
    subtasks:
      - "POST /api/login handler"
      - "JWT token generation"
    prompt_file: tasks/WP02.md
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Work-package identifier (e.g., `WP01`) |
| `title` | Yes | Short human-readable name |
| `dependencies` | No | List of WP IDs this WP depends on. **Key invariant**: once present (even as `[]`), this field is never overwritten by the pipeline. |
| `owned_files` | No | Files this WP exclusively writes. Used for parallelism assignment (see [Parallelism Preservation](../explanation/execution-lanes.md#parallelism-preservation)). |
| `requirement_refs` | No | Anchors in spec artifacts this WP implements |
| `subtasks` | No | Fine-grained checklist items inside the WP |
| `prompt_file` | No | Path to the WP prompt (defaults to `tasks/<id>.md`) |

## How `/spec-kitty.tasks-outline` Produces `wps.yaml`

During the `tasks-outline` workflow step, the agent writes `wps.yaml` directly (not `tasks.md`). The LLM receives the spec and plan and emits a structured manifest. This is the canonical source of WP definitions.

## How `finalize-tasks` Uses It

`finalize-tasks` reads `wps.yaml` and:

1. Validates each entry against the JSON Schema at `src/specify_cli/schemas/wps.schema.json`
2. Computes the lane graph from `dependencies` and `owned_files`
3. Writes `lanes.json` with the computed assignment and a `collapse_report`
4. Regenerates `tasks.md` as a human-readable derived artifact

`tasks.md` is now a **derived view** of `wps.yaml`. Do not hand-edit it; edit `wps.yaml` instead, then re-run `finalize-tasks`.

## Key Invariant: `dependencies` Is Never Overwritten

If a WP's `dependencies` field is present in `wps.yaml` (even as an empty list `[]`), the pipeline treats it as authoritative and never overwrites it. This lets you explicitly declare that a WP has no dependencies even if the file-overlap analysis would suggest otherwise.

## JSON Schema

The schema is at `src/specify_cli/schemas/wps.schema.json`. Validate manually with:

```bash
python -m jsonschema --instance kitty-specs/042-auth-system/wps.yaml \
  src/specify_cli/schemas/wps.schema.json
```

## Backward Compatibility

Missions without a `wps.yaml` continue to work. `finalize-tasks` falls back to the prose parser for those missions. New missions created with spec-kitty 3.1.0+ will always produce a `wps.yaml`.

## See Also

- [Parallelism Preservation](../explanation/execution-lanes.md#parallelism-preservation) — how `owned_files` drives lane assignment
- [Generate Tasks](generate-tasks.md) — the full task generation workflow
- [CLI Reference: spec-kitty tasks](../reference/cli-commands.md#spec-kitty-tasks)
