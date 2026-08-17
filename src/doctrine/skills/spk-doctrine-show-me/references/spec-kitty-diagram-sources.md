# Spec Kitty diagram sources

Load only the artifact needed for the visual. Run one include per command:

```bash
spec-kitty charter context --include toolguide:mermaid-diagramming
spec-kitty charter context --include toolguide:plantuml-diagramming
spec-kitty charter context --include directive:USE_C4_MODEL_TECHNIQUES
spec-kitty charter context --include tactic:architecture-diagram-review-checklist
```

The returned artifact is governing context. Toolguide context also reports its
canonical `guide_path`; read that path when it exists in the current checkout.
In the Spec Kitty source repository, the core guides and templates are:

- `packs/built-in/toolguides/MERMAID_DIAGRAMMING.md`
- `packs/built-in/toolguides/PLANTUML_DIAGRAMMING.md`
- `src/doctrine/templates/diagrams/`

Project-installed skills cannot assume those checkout-relative paths exist.
Use this skill's portable `assets/mermaid-theme-common-template.md` or
`assets/mermaid-theme-bluegray-conversation-template.md` as optional visual
baselines. They are bundled snapshots of Spec Kitty's canonical theme examples;
the loaded directive, tactic, and toolguide remain authoritative.
