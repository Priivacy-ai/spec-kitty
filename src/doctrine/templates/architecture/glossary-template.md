# Glossary Template

A structured glossary for capturing ubiquitous language terms within a
bounded context. Compatible with [Contextive](../../toolguides/shipped/CONTEXTIVE.md)
glossary file format.

Use the [glossary-curation-interview](../../tactics/shipped/glossary-curation-interview.tactic.yaml)
tactic for the curation process and the
[kitty-glossary-writing](../../styleguides/shipped/writing/kitty-glossary-writing.styleguide.yaml)
styleguide for writing conventions.

---

## Markdown Glossary Table

For documentation and canvas integration:

| Term | Definition | Examples | Context boundary notes |
|---|---|---|---|
| _e.g. Policy_ | _A set of actuarial rules applied to premium calculation._ | _"The policy determines the base rate for this risk class."_ | _Different from Billing's 'Policy' (payment terms)._ |
| _e.g. Cargo_ | _A unit of transportation that needs moving and delivery._ | _"Multiple customers are involved with a cargo."_ | |
| | | | |

---

## Contextive Glossary File (YAML)

For IDE-integrated ubiquitous language enforcement. Place this file at
`.contextive/definitions.yml` (or per-module as
`<module>/<module>.glossary.yml`).

```yaml
contexts:
  - name: __CONTEXT_NAME__
    domainVisionStatement: >
      __One to three sentences describing the context's purpose.__
    terms:
      - name: __Term__
        definition: >
          __Clear, concise definition as used within this context.__
        examples:
          - "__A real sentence a domain expert might say using this term.__"
        aliases:
          - __alternative_name__
        meta:
          "Status:": "Candidate / Canonical / Deprecated"

      - name: __AnotherTerm__
        definition: >
          __Definition.__
        examples:
          - "__Usage example.__"
```

### Field Reference

| Field | Required | Description |
|---|---|---|
| `name` | Yes | The term in natural language (e.g. "Leg Magnitude Policy") |
| `definition` | No (but strongly recommended) | What the term means in this context |
| `examples` | No | Real sentences a domain expert would say |
| `aliases` | No | Alternative names or abbreviations |
| `meta` | No | Key-value metadata (ownership, status, links) |

### Multi-Context Repository Layout

```
repo-root/
  billing-module/
    billing.glossary.yml         # Billing context terms
  shipping-module/
    shipping.glossary.yml        # Shipping context terms
  .contextive/
    definitions.yml              # Shared / cross-cutting terms
```

### Term Lifecycle

| Status | Meaning |
|---|---|
| **Candidate** | Proposed during curation; awaiting HiC approval |
| **Canonical** | Approved by HiC; enforced in code and docs |
| **Deprecated** | Superseded; retained with deprecation notice and pointer to replacement |

---

## Cross-Reference Checklist

- [ ] Every term in the Bounded Context Canvas "Ubiquitous Language" section has a corresponding entry here
- [ ] Terms with different meanings in other contexts are flagged in the "Context boundary notes" column
- [ ] Deprecated terms have a deprecation notice and point to their replacement
- [ ] The Contextive YAML file is committed to the repository and the IDE extension is configured

---

## Traceability

- Tactic: [glossary-curation-interview](../../tactics/shipped/glossary-curation-interview.tactic.yaml)
- Styleguide: [kitty-glossary-writing](../../styleguides/shipped/writing/kitty-glossary-writing.styleguide.yaml)
- Canvas: [bounded-context-canvas-template](../architecture/bounded-context-canvas-template.md)
- Toolguide: [Contextive](../../toolguides/shipped/CONTEXTIVE.md)
