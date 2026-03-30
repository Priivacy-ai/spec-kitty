# Mermaid Diagram Templates

Mermaid diagram templates for inline Markdown diagrams. Mermaid is the default
for diagrams embedded in documentation because it renders natively on GitHub,
GitLab, and VS Code without external tooling.

These templates are the Mermaid equivalents of the PlantUML templates in
`../plantuml/`. They originate from the reference PlantUML set in the
quickstart agent-augmented development publication corpus, translated to
Mermaid syntax.

## Structure

- `themes/` -- Copy-paste `%%{init}%%` theme snippets for consistent styling.
- `examples/` -- Ready-to-copy diagram templates by modeling intent.

## Themes

| Theme | File | Use Case |
|---|---|---|
| Common | `mermaid-theme-common-template.md` | Neutral baseline. ADRs, architecture, domain maps. |
| Bluegray Conversation | `mermaid-theme-bluegray-conversation-template.md` | Sequence and interaction diagrams. |

## Examples

| Template | Modeling Intent |
|---|---|
| `causal-map-mermaid-template.md` | Cause-effect feedback loops |
| `content-map-mermaid-template.md` | Content inventory and governance relationships |
| `frontend-architecture-mermaid-template.md` | Component-level front-end overview |
| `repo-content-graph-mermaid-template.md` | Artifacts-to-audiences mapping |
| `request-lifecycle-sequence-mermaid-template.md` | Request flow sequence diagram |
| `structure-meta-model-mermaid-template.md` | Conceptual meta model |
| `system-map-mermaid-template.md` | High-level system context map |

## Notes

1. Mermaid does not support `!include` files. Theme snippets in `themes/` are
   copy-paste `%%{init}%%` blocks.
2. All example templates use `{{placeholder}}` double-brace convention for
   fill-in values.
3. For full Mermaid usage guidance, see the
   [Mermaid Diagramming Toolguide](../../../toolguides/shipped/MERMAID_DIAGRAMMING.md).
