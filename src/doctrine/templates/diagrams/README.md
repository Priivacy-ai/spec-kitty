# Mermaid Diagram Templates

Mermaid-first diagram templates aligned with Spec Kitty documentation
conventions.

These templates are the Mermaid equivalent of the reference PlantUML set from
the Doctrine diagramming collection in the quickstart agent-augmented
development publication corpus.

## Structure

- `themes/` reusable style snippets and class conventions.
- `examples/` ready-to-copy diagram templates by modeling intent.

## Theme Templates

- [mermaid-theme-common-template.md](themes/mermaid-theme-common-template.md)
- [mermaid-theme-bluegray-conversation-template.md](themes/mermaid-theme-bluegray-conversation-template.md)

## Example Templates (Planned)

Planned templates to add:

- `causal-map-mermaid-template.md`
- `content-map-mermaid-template.md`
- `frontend-architecture-mermaid-template.md`
- `repo-content-graph-mermaid-template.md`
- `request-lifecycle-sequence-mermaid-template.md`
- `structure-meta-model-mermaid-template.md`
- `system-map-mermaid-template.md`

## C4 and 2.x Cross-Reference

| Diagram Template | C4 Template Alignment | 2.x Architecture Alignment |
|---|---|---|
| System Map | [C4 Context](../architecture/c4-context-mermaid-template.md) | [`architecture/2.x/01_context/README.md`](../../../../architecture/2.x/01_context/README.md) |
| Frontend Architecture | [C4 Containers](../architecture/c4-container-mermaid-template.md), [C4 Components](../architecture/c4-component-mermaid-template.md) | [`architecture/2.x/02_containers/README.md`](../../../../architecture/2.x/02_containers/README.md), [`architecture/2.x/03_components/README.md`](../../../../architecture/2.x/03_components/README.md) |
| Request Lifecycle | [C4 Components](../architecture/c4-component-mermaid-template.md) | [`architecture/2.x/README.md#usage-flow-high-level-user-journey`](../../../../architecture/2.x/README.md#usage-flow-high-level-user-journey), [`architecture/2.x/02_containers/runtime-execution-domain.md`](../../../../architecture/2.x/02_containers/runtime-execution-domain.md) |
| Structure Meta Model | [C4 Context](../architecture/c4-context-mermaid-template.md) | [`architecture/2.x/README.md#domain-breakdown`](../../../../architecture/2.x/README.md#domain-breakdown) |
| Causal Map | [C4 Context](../architecture/c4-context-mermaid-template.md) | [`architecture/2.x/README.md#domain-breakdown`](../../../../architecture/2.x/README.md#domain-breakdown) |
| Content Map | [C4 Context](../architecture/c4-context-mermaid-template.md) | [`architecture/README.md`](../../../../architecture/README.md) |
| Repo Content Graph | [C4 Context](../architecture/c4-context-mermaid-template.md) | [`architecture/README.md`](../../../../architecture/README.md) |

## Notes

1. Mermaid does not support PlantUML-style include files in markdown contexts.
   Theme files in this directory are copy/paste snippets.
2. Keep architecture docs Mermaid-first. PlantUML references are input lineage
   only.
