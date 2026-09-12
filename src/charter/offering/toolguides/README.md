# Toolguides

`toolguides` document how agents and contributors should use specific tools in
the project environment.

Shipped toolguide artifacts live in:

- `packs/built-in/toolguides/*.toolguide.yaml`
- `packs/built-in/toolguides/*.md`

Use toolguides for operational syntax and platform nuances, for example:

- PowerShell command and parameter conventions
- Git usage conventions for this repo
- CI/tool invocation patterns

The file `packs/built-in/toolguides/POWERSHELL_SYNTAX.md` is a canonical example
of a toolguide reference.

## Diagramming Toolguides

Toolguides for diagram-as-code tools used in Spec Kitty projects:

- `packs/built-in/toolguides/plantuml-diagramming.toolguide.yaml` -- PlantUML reference guide
- `packs/built-in/toolguides/mermaid-diagramming.toolguide.yaml` -- Mermaid reference guide

See `src/charter/offering/templates/diagrams/README.md` for the corresponding diagram
template library.
