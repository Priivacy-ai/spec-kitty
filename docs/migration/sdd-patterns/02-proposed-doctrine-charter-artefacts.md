# Proposed Doctrine and Charter Artefacts

_Migration research document — proposed artefact taxonomy and DRG extension strategy_
_Date: 2025-05-25_

## 1. Executive Summary

This document proposes the doctrine artifacts to extract from the penguin-pragmatic-patterns
repository and bundle as a spec-kitty org doctrine pack named `sdd-patterns`. It describes
how each artifact type maps to the spec-kitty taxonomy, how the DRG can be extended, and
how the charter selection mechanism activates these artifacts at runtime.

## 2. Proposed Pack Structure

```
sdd-patterns/
  paradigms/
    sdd-context-over-commandments.paradigm.yaml
    sdd-progressive-disclosure.paradigm.yaml
    sdd-ammerse-evaluation.paradigm.yaml
  directives/
    sdd-001-glossary-tag-sync.directive.yaml
    sdd-002-ieee-citation-format.directive.yaml
    sdd-003-practice-section-completeness.directive.yaml
    sdd-004-uuid-uniqueness.directive.yaml
    sdd-005-tone-alignment.directive.yaml
    sdd-006-no-prescriptive-absolutes.directive.yaml
    sdd-007-ammerse-delta-required.directive.yaml
  tactics/
    sdd-pattern-curation-workflow.tactic.yaml
    sdd-bibliography-entry.tactic.yaml
    sdd-lex-tone-review.tactic.yaml
    sdd-glossary-term-addition.tactic.yaml
    sdd-content-template-selection.tactic.yaml
  styleguides/
    writing/
      sdd-tone-map.styleguide.yaml
      sdd-style-rules.styleguide.yaml
      sdd-practice-structure.styleguide.yaml
    content/
      sdd-concept-structure.styleguide.yaml
      sdd-primer-structure.styleguide.yaml
  toolguides/
    sdd-hugo-site-generator.toolguide.yaml
    sdd-plantuml-diagramming.toolguide.yaml
    sdd-contextive-ide-glossary.toolguide.yaml
    sdd-toml-frontmatter.toolguide.yaml
  procedures/
    sdd-pattern-discovery-to-publication.procedure.yaml
    sdd-lex-analysis-cycle.procedure.yaml
    sdd-glossary-curation.procedure.yaml
  agent_profiles/
    sdd-curator.agent.yaml
    sdd-researcher.agent.yaml
    sdd-lexical.agent.yaml
    sdd-writer-editor.agent.yaml
    sdd-synthesizer.agent.yaml
    sdd-diagrammer.agent.yaml
    sdd-scribe.agent.yaml
  drg/
    010-sdd-content-types.graph.yaml
    020-sdd-curation-workflow.graph.yaml
    030-sdd-quality-gates.graph.yaml
  glossary/
    sdd-patterns-glossary.yaml
  org-charter.yaml
  pack-manifest.yaml
```

## 3. Paradigms

### sdd-context-over-commandments

Source: AGENTS.md + repository README philosophy.
Rejects prescriptive best-practice mandates in favor of contextual guidance.

### sdd-progressive-disclosure

Information is presented gradually, revealing complexity only when necessary.

### sdd-ammerse-evaluation

Every practice is evaluated across 7 dimensions (Agile, Minimal, Maintainable,
Environmental, Reachable, Solvable, Extensible) with delta ratings and rationales.

## 4. Directives

| ID | Title | Enforcement | Source |
|----|-------|-------------|--------|
| sdd-001 | Glossary Tag Sync | required | Content validation pipeline |
| sdd-002 | IEEE Citation Format | advisory | LEX_STYLE_RULES.md |
| sdd-003 | Practice Section Completeness | required | TEMPLATE_PRACTICE.md |
| sdd-004 | UUID Uniqueness | required | Content validation pipeline |
| sdd-005 | Tone Alignment | advisory | LEX_TONE_MAP.md |
| sdd-006 | No Prescriptive Absolutes | advisory | LEX_STYLE_RULES.md |
| sdd-007 | AMMERSE Delta Required | required | Practice template contract |

## 5. Extending the DRG

### Three-Layer DRG Architecture

Spec-kitty's DRG uses three layers:

1. **Shipped (built-in):** `src/doctrine/drg/shipped.json` — immutable core
2. **Org-tier:** `drg/fragment.yaml` inside each configured org pack — additive extensions
3. **Project-tier:** `.kittify/doctrine/graph.yaml` — project-local annotations

The sdd-patterns pack contributes to **Layer 2 (org-tier)** via DRG fragment files.

### Extension Rules

- Each tier is **additive only**
- Org and project tiers **cannot remove or reclassify** shipped nodes
- Resolved at runtime by `charter.drg.merge_three_layers`
- Multiple fragment files merge in alphabetical filename order
- Collisions with built-in nodes produce advisories (not errors)

### DRG Fragments

**010-sdd-content-types.graph.yaml** introduces content type nodes (practice, concept, primer)
and connects them to styleguide artifacts.

**020-sdd-curation-workflow.graph.yaml** maps curation workflow stages to action nodes
(directive -> action scope edges).

**030-sdd-quality-gates.graph.yaml** wires validation directives to review actions.

## 6. Org-Charter Policy

Required directives: sdd-001, sdd-003, sdd-004
Required styleguides: sdd-tone-map, sdd-style-rules
Required paradigms: sdd-context-over-commandments
Default agent profiles: sdd-curator, sdd-researcher, sdd-lexical, sdd-writer-editor

## 7. Artifact Dependency Map

```
sdd-context-over-commandments (paradigm)
  sdd-006-no-prescriptive-absolutes (directive)
    sdd-tone-map (styleguide)
      sdd-005-tone-alignment (directive)
        sdd-lex-tone-review (tactic)
  sdd-ammerse-evaluation (paradigm)
    sdd-007-ammerse-delta-required (directive)
      sdd-practice-structure (styleguide)
  sdd-progressive-disclosure (paradigm)
    sdd-concept-structure (styleguide)

sdd-001-glossary-tag-sync (directive)
  sdd-glossary-term-addition (tactic)
  sdd-glossary-curation (procedure)

sdd-pattern-curation-workflow (tactic)
  sdd-content-template-selection (tactic)
  sdd-bibliography-entry (tactic)
  sdd-pattern-discovery-to-publication (procedure)
```

## 8. References

- spec-kitty glossary/contexts/doctrine.md
- spec-kitty docs/how-to/create-an-org-doctrine-pack.md
- spec-kitty src/charter/drg.py
- spec-kitty glossary/contexts/governance.md
- AGENTS.md
- docs/templates/TEMPLATE_PRACTICE.md
- docs/styleguide/LEX_TONE_MAP.md
- docs/styleguide/LEX_STYLE_RULES.md
