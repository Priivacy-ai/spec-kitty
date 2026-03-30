# PlantUML Diagram Templates

PlantUML diagram templates for standalone diagram files, workshop visuals,
and diagrams requiring the stickies/causal DSL.

These templates are the PlantUML counterparts to the Mermaid templates in
`../examples/`. They originate from the reference PlantUML set in the
quickstart agent-augmented development and penguin-pragmatic-patterns
publication corpora.

## Structure

- `themes/` -- Documentation templates for the three PlantUML themes.
- `examples/` -- Ready-to-copy diagram templates by modeling intent.

## Themes

| Theme | File | Use Case |
|---|---|---|
| Common | `plantuml-theme-common-template.md` | Neutral baseline. ADRs, technical designs. |
| Bluegray Conversation | `plantuml-theme-bluegray-conversation-template.md` | Sequence and interaction diagrams. |
| Stickies | `plantuml-theme-stickies-template.md` | Workshop visuals, causal maps, event storming. |

## Examples

| Template | Modeling Intent |
|---|---|
| `causal-map-plantuml-template.md` | Cause-effect feedback loops with sticky macros |
| `content-map-plantuml-template.md` | Content inventory and governance relationships |
| `frontend-architecture-plantuml-template.md` | Component-level front-end overview |
| `repo-content-graph-plantuml-template.md` | Artifacts-to-audiences mapping |
| `request-lifecycle-plantuml-template.md` | Request flow sequence diagram |
| `structure-meta-model-plantuml-template.md` | C4-based conceptual meta model |
| `system-map-plantuml-template.md` | High-level system context map |
| `event-storming-plantuml-template.md` | DDD event storming board |

## Notes

1. Theme templates in `themes/` document how to use the `.puml` theme source
   files. The actual theme files should be included via `!include` with
   relative paths in your diagram source.
2. All example templates use `{{placeholder}}` double-brace convention for
   fill-in values.
3. For full PlantUML usage guidance, see the
   [PlantUML Diagramming Toolguide](../../../toolguides/shipped/PLANTUML_DIAGRAMMING.md).
