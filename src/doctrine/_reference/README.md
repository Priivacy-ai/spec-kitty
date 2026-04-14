# Doctrine Reference Landing Zone

This directory is a landing zone for **raw, unformatted reference material** — articles,
documentation excerpts, style guides, books, or any other external source that contains
ideas worth formalising into doctrine.

## Intent

Drop raw sources here when you identify something worth extracting into a doctrine entity
(directive, tactic, procedure, styleguide, toolguide, or paradigm). Structure is not
required at intake time.

Once a reference has been fully converted into one or more doctrine artifacts under
`src/doctrine/<type>/shipped/`, the raw reference file **should be removed** from this
directory. The traceability between source and artifact is captured in the resulting
`.import.yaml` candidate file, not in this landing zone.

## Lifecycle

```
_reference/<source>/   ← drop raw material here (unformatted, any format)
        ↓  (extract and formalise as a shipped YAML + graph.yaml edges)
<type>/shipped/        ← canonised, live doctrine
```

## What belongs here

- Markdown excerpts from architecture docs, READMEs, or contributing guides
- `.import.yaml` candidate files tracking external source provenance
- `manifest.yaml` files grouping candidates by source
- Any raw notes or references that have not yet been converted

## What does NOT belong here

- Structured doctrine artifacts (`.directive.yaml`, `.tactic.yaml`, etc.) — those go
  directly into `<type>/shipped/`
- Converted references whose artifacts already exist under `<type>/shipped/`
