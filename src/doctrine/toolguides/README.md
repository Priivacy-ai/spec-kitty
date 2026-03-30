# Toolguides

`toolguides` document how agents and contributors should use specific tools in
the project environment.

Shipped toolguide artifacts live in:

- `src/doctrine/toolguides/shipped/*.toolguide.yaml`
- `src/doctrine/toolguides/shipped/*.md`

Use toolguides for operational syntax and platform nuances, for example:

- PowerShell command and parameter conventions
- Git usage conventions for this repo
- CI/tool invocation patterns

The file `src/doctrine/toolguides/shipped/POWERSHELL_SYNTAX.md` is a canonical example
of a toolguide reference.

## Diagramming Toolguides

Toolguides for diagram-as-code tools used in Spec Kitty projects:

- `src/doctrine/toolguides/shipped/plantuml-diagramming.toolguide.yaml` -- PlantUML reference guide
- `src/doctrine/toolguides/shipped/mermaid-diagramming.toolguide.yaml` -- Mermaid reference guide

See `src/doctrine/templates/diagrams/README.md` for the corresponding diagram
template library.
