# Structure Templates

Structural mapping templates that enable agents and humans to orient themselves in a
repository.

## Available Templates

| Template | Purpose |
|----------|---------|
| `REPO_MAP.md` | Repository topology: folder purposes, key files, primary languages, build system, test frameworks |
| `SURFACES.md` | Entry points, external integrations, public interfaces, observability endpoints |

Templates use `{{PLACEHOLDER}}` markers (e.g., `{{DATE}}`, `{{TREE_SNIPPET}}`) that
are populated by agents or users during project-specific generation. The `spec-kitty
init` bootstrap process offers to generate these files from the shipped templates.
