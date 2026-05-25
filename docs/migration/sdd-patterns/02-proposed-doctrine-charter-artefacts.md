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
├── paradigms/
│   ├── sdd-context-over-commandments.paradigm.yaml
│   ├── sdd-progressive-disclosure.paradigm.yaml
│   └── sdd-ammerse-evaluation.paradigm.yaml
├── directives/
│   ├── sdd-001-glossary-tag-sync.directive.yaml
│   ├── sdd-002-ieee-citation-format.directive.yaml
│   ├── sdd-003-practice-section-completeness.directive.yaml
│   ├── sdd-004-uuid-uniqueness.directive.yaml
│   ├── sdd-005-tone-alignment.directive.yaml
│   ├── sdd-006-no-prescriptive-absolutes.directive.yaml
│   └── sdd-007-ammerse-delta-required.directive.yaml
├── tactics/
│   ├── sdd-pattern-curation-workflow.tactic.yaml
│   ├── sdd-bibliography-entry.tactic.yaml
│   ├── sdd-lex-tone-review.tactic.yaml
│   ├── sdd-glossary-term-addition.tactic.yaml
│   └── sdd-content-template-selection.tactic.yaml
├── styleguides/
│   ├── writing/
│   │   ├── sdd-tone-map.styleguide.yaml
│   │   ├── sdd-style-rules.styleguide.yaml
│   │   └── sdd-practice-structure.styleguide.yaml
│   └── content/
│       ├── sdd-concept-structure.styleguide.yaml
│       └── sdd-primer-structure.styleguide.yaml
├── toolguides/
│   ├── sdd-hugo-site-generator.toolguide.yaml
│   ├── sdd-plantuml-diagramming.toolguide.yaml
│   ├── sdd-contextive-ide-glossary.toolguide.yaml
│   └── sdd-toml-frontmatter.toolguide.yaml
├── procedures/
│   ├── sdd-pattern-discovery-to-publication.procedure.yaml
│   ├── sdd-lex-analysis-cycle.procedure.yaml
│   └── sdd-glossary-curation.procedure.yaml
├── agent_profiles/
│   ├── sdd-curator.agent.yaml
│   ├── sdd-researcher.agent.yaml
│   ├── sdd-lexical.agent.yaml
│   ├── sdd-writer-editor.agent.yaml
│   ├── sdd-synthesizer.agent.yaml
│   ├── sdd-diagrammer.agent.yaml
│   └── sdd-scribe.agent.yaml
├── templates/
│   └── sets/
│       ├── sdd-practice-template.set.yaml
│       ├── sdd-concept-template.set.yaml
│       └── sdd-primer-template.set.yaml
├── drg/
│   ├── 010-sdd-content-types.graph.yaml
│   ├── 020-sdd-curation-workflow.graph.yaml
│   └── 030-sdd-quality-gates.graph.yaml
├── glossary/
│   └── sdd-patterns-glossary.yaml
├── org-charter.yaml
└── pack-manifest.yaml
```

## 3. Artifact Detail

### 3.1 Paradigms

Paradigms are worldview-level framings. Three paradigms capture the SDD Patterns philosophy:

#### sdd-context-over-commandments

**Source:** `AGENTS.md` Section 1 + repository README philosophy
**Definition:** Rejects prescriptive "best practice" mandates in favor of contextual guidance.
Patterns provide judgment-building frameworks rather than rules to follow blindly.

```yaml
schema_version: "1.0"
id: sdd-context-over-commandments
title: Context Over Commandments
description: |
  Knowledge artifacts present contextual guidance rather than prescriptive rules.
  Each pattern acknowledges trade-offs, limitations, and situations where it should
  not be applied. The reader's context determines applicability, not the pattern author.
action_scope:
  - specify
  - implement
  - review
```

#### sdd-progressive-disclosure

**Source:** `data/glossary.toml` term "Progressive Disclosure"
**Definition:** Information is presented gradually, revealing complexity only when necessary.

#### sdd-ammerse-evaluation

**Source:** Practice template AMMERSE frontmatter
**Definition:** Every practice is evaluated across 7 dimensions (Agile, Minimal, Maintainable,
Environmental, Reachable, Solvable, Extensible) with delta ratings and rationales.

### 3.2 Directives

Directives encode required or advisory expectations:

| ID | Title | Enforcement | Source |
|----|-------|-------------|--------|
| sdd-001 | Glossary Tag Sync | required | Content validation pipeline |
| sdd-002 | IEEE Citation Format | advisory | LEX_STYLE_RULES.md |
| sdd-003 | Practice Section Completeness | required | TEMPLATE_PRACTICE.md |
| sdd-004 | UUID Uniqueness | required | Content validation pipeline |
| sdd-005 | Tone Alignment | advisory | LEX_TONE_MAP.md |
| sdd-006 | No Prescriptive Absolutes | advisory | LEX_STYLE_RULES.md |
| sdd-007 | AMMERSE Delta Required | required | Practice template contract |

### 3.3 Tactics

Tactics define how work is performed:

#### sdd-pattern-curation-workflow

The end-to-end flow from pattern discovery to publication.

**Steps:**
1. Source pattern concept from experience, literature, or discussion
2. Select appropriate template (practice/concept/primer)
3. Generate UUID and assign metadata
4. Author content following template structure
5. Verify glossary tag synchronization
6. Create branch and PR
7. Run validation gates (front matter, tags, UUID, sections, images)
8. Deploy preview to GitHub Pages
9. Review cycle with tone/style validation
10. Merge to production

#### sdd-bibliography-entry

**Steps:**
1. Validate source credibility (author credentials, publication reputation)
2. Create `bibliography.toml` entry with UUID key
3. Populate all metadata fields (title, authors, publisher, year, link, levels, tags)
4. Run book page generation script
5. Link from pattern `further_exploration` frontmatter

#### sdd-lex-tone-review

**Steps:**
1. Run LEX analysis against tone map characteristics
2. Score each voice characteristic (calm, clear, sincere, humble, collaborative, practical, balanced)
3. Flag deviations below 85% compliance threshold
4. Generate LEX_DELTAS report with before/after suggestions
5. Prioritize fixes by severity (high/medium/low)

### 3.4 Styleguides

The LEX framework translates directly into styleguide artifacts:

#### sdd-tone-map.styleguide.yaml

**Rules:**
- Calm (94%): No urgency language, no absolutism
- Clear (91%): Concrete examples, minimal unexplained jargon
- Sincere (96%): Acknowledge limitations
- Humble (93%): "You know your context better than we do"
- Collaborative (90%): Inclusive "we" framing
- Practical (92%): Actionable steps with mitigations
- Balanced (95%): Acknowledge trade-offs and negative deltas

#### sdd-style-rules.styleguide.yaml

**Rules:**
- Active voice preferred
- Use "consider", "can", "may" over "must", "should"
- Include "when NOT to use" clarifications
- Max 3-4 sentences per topic paragraph
- Bulleted workflows for step-by-step processes
- Clear heading hierarchy (H2/H3 for scannability)

### 3.5 Toolguides

| Toolguide | Scope | Key Constraints |
|-----------|-------|----------------|
| Hugo Site Generator | Build system | v0.152.2 extended; Dart Sass for SCSS |
| PlantUML Diagramming | Visualization | Consistent theme; accessibility colors |
| Contextive IDE Glossary | IDE integration | Auto-generated from glossary.toml |
| TOML Frontmatter | Content metadata | Required fields vary by content type |

### 3.6 Procedures

#### sdd-pattern-discovery-to-publication

A compound procedure that orchestrates the full lifecycle:

```
[Discovery] → [Research] → [Template Selection] → [Authoring]
    → [Metadata Assignment] → [Glossary Sync] → [Validation]
    → [Preview Deploy] → [Review Cycle] → [Publication]
```

Each stage maps to a spec-kitty mission action and can be delegated to specific agent
profiles.

### 3.7 Agent Profiles

Seven agent profiles are extracted as doctrine-level agents (the remaining 6 are
infrastructure/tooling agents that stay project-local):

| Profile | Governance Scope | Key Directives |
|---------|-----------------|----------------|
| sdd-curator | sdd-001, sdd-003, sdd-007 | Content curation and coherence |
| sdd-researcher | sdd-002, sdd-004 | Reference sourcing and bibliography |
| sdd-lexical | sdd-001, sdd-005, sdd-006 | Terminology and tone governance |
| sdd-writer-editor | sdd-003, sdd-005, sdd-006 | Content editing and polish |
| sdd-synthesizer | sdd-005, sdd-006 | Cross-pattern coherence |
| sdd-diagrammer | (toolguide scope) | PlantUML visualization |
| sdd-scribe | sdd-003, sdd-005 | Documentation bootstrap |

## 4. Extending the DRG

### 4.1 Three-Layer DRG Architecture

Spec-kitty's DRG uses three layers:

1. **Shipped (built-in):** `src/doctrine/drg/shipped.json` — immutable core
2. **Org-tier:** `drg/fragment.yaml` inside each configured org pack — additive extensions
3. **Project-tier:** `.kittify/doctrine/graph.yaml` — project-local annotations

The sdd-patterns pack contributes to **Layer 2 (org-tier)** via DRG fragment files.

### 4.2 DRG Fragment Strategy

Three fragment files partition the extension cleanly:

#### 010-sdd-content-types.graph.yaml

Introduces nodes for the SDD content taxonomy:

```yaml
nodes:
  - urn: "content-type:practice"
    kind: concept
    label: "Practice (SDD Pattern)"
  - urn: "content-type:concept"
    kind: concept
    label: "Concept (SDD Definition)"
  - urn: "content-type:primer"
    kind: concept
    label: "Primer (SDD Language Guide)"

edges:
  - source: "content-type:practice"
    target: "urn:styleguide:sdd-practice-structure"
    relation: requires
  - source: "content-type:concept"
    target: "urn:styleguide:sdd-concept-structure"
    relation: requires
  - source: "content-type:primer"
    target: "urn:styleguide:sdd-primer-structure"
    relation: requires
```

#### 020-sdd-curation-workflow.graph.yaml

Maps the curation workflow stages to action nodes:

```yaml
edges:
  - source: "urn:directive:sdd-001-glossary-tag-sync"
    target: "urn:action:implement"
    relation: scope
  - source: "urn:directive:sdd-005-tone-alignment"
    target: "urn:action:review"
    relation: scope
  - source: "urn:directive:sdd-003-practice-section-completeness"
    target: "urn:action:implement"
    relation: scope
  - source: "urn:procedure:sdd-pattern-discovery-to-publication"
    target: "urn:action:specify"
    relation: scope
```

#### 030-sdd-quality-gates.graph.yaml

Wires validation directives to review actions:

```yaml
edges:
  - source: "urn:directive:sdd-004-uuid-uniqueness"
    target: "urn:action:review"
    relation: scope
  - source: "urn:directive:sdd-007-ammerse-delta-required"
    target: "urn:action:review"
    relation: scope
  - source: "urn:styleguide:sdd-tone-map"
    target: "urn:action:review"
    relation: scope
```

### 4.3 Extension Rules

Per spec-kitty's glossary definition of **Three-layer DRG**:

- Each tier is **additive only**
- Org and project tiers **cannot remove or reclassify** shipped nodes
- Resolved at runtime by `charter.drg.merge_three_layers`
- Multiple fragment files merge in **alphabetical filename order** (hence `010-`, `020-`, `030-` prefixes)
- Collisions with built-in nodes produce advisories (not errors)

### 4.4 Activation Registry

The org-charter.yaml declares which artifacts activate in which contexts:

```yaml
activation_registry:
  # Global selections (always active)
  - context: {mission_type: "generic", action: "generic"}
    pack: sdd-patterns
    artifact: sdd-tone-map

  # Content-type specific activations
  - context: {mission_type: "documentation", action: "implement"}
    pack: sdd-patterns
    artifact: sdd-practice-structure

  - context: {mission_type: "documentation", action: "review"}
    pack: sdd-patterns
    artifact: sdd-005-tone-alignment

  - context: {mission_type: "research", action: "specify"}
    pack: sdd-patterns
    artifact: sdd-pattern-discovery-to-publication
```

## 5. Org-Charter Policy

The `org-charter.yaml` file declares organization-level governance:

```yaml
schema_version: "1.0"
org_name: "SDD Development"
pack_id: sdd-patterns

required_directives:
  - sdd-001-glossary-tag-sync
  - sdd-003-practice-section-completeness
  - sdd-004-uuid-uniqueness

required_styleguides:
  - sdd-tone-map
  - sdd-style-rules

required_paradigms:
  - sdd-context-over-commandments

suggested_directives:
  - sdd-002-ieee-citation-format
  - sdd-005-tone-alignment
  - sdd-006-no-prescriptive-absolutes
  - sdd-007-ammerse-delta-required

default_agent_profiles:
  - sdd-curator
  - sdd-researcher
  - sdd-lexical
  - sdd-writer-editor
```

## 6. Interrelation with Existing Spec-Kitty Elements

### 6.1 Charter Selection Integration

When a project configures the sdd-patterns pack in `.kittify/config.yaml`:

```yaml
doctrine:
  org:
    packs:
      - name: sdd-patterns
        source: git
        url: https://github.com/sddevelopment-be/sdd-patterns-doctrine-pack.git
```

The charter compiler:
1. Loads `org-charter.yaml` from the pack
2. Unions `required_*` entries into project `selected_*` non-destructively
3. Registers activation entries in the project's activation registry
4. Loads DRG fragments via `load_org_drg()`
5. Merges via `merge_three_layers()` (shipped + sdd-patterns org + project)

### 6.2 Mission-Type Profile Alignment

The sdd-patterns pack aligns with spec-kitty's mission types:

| SDD Activity | Spec-Kitty Mission Type | Primary Artifacts |
|-------------|------------------------|-------------------|
| Pattern research | `research` | Researcher profile, bibliography tactic |
| Pattern drafting | `documentation` | Writer-Editor profile, practice styleguide |
| Glossary curation | `documentation` | Lexical profile, glossary tactic |
| Pattern review | (cross-cutting) | Tone-map styleguide, tone-alignment directive |
| Site publishing | `software-dev` | Hugo toolguide, build-automation profile |

### 6.3 Glossary Layer Integration

The sdd-patterns glossary enters as a `team_domain` scope in spec-kitty's scoped glossary
model:

```yaml
scope: team_domain
terms:
  - surface: "AMMERSE"
    definition: "A 7-dimension evaluation framework..."
    status: canonical
    confidence: 0.95
  - surface: "Practice"
    definition: "A contextual problem-solution pattern..."
    status: canonical
    confidence: 1.0
```

## 7. Artifact Dependency Map

```
sdd-context-over-commandments (paradigm)
├── sdd-006-no-prescriptive-absolutes (directive)
│   └── sdd-tone-map (styleguide)
│       └── sdd-005-tone-alignment (directive)
│           └── sdd-lex-tone-review (tactic)
├── sdd-ammerse-evaluation (paradigm)
│   └── sdd-007-ammerse-delta-required (directive)
│       └── sdd-practice-structure (styleguide)
└── sdd-progressive-disclosure (paradigm)
    └── sdd-concept-structure (styleguide)

sdd-001-glossary-tag-sync (directive)
├── sdd-glossary-term-addition (tactic)
└── sdd-glossary-curation (procedure)

sdd-pattern-curation-workflow (tactic)
├── sdd-content-template-selection (tactic)
├── sdd-bibliography-entry (tactic)
└── sdd-pattern-discovery-to-publication (procedure)
```

## 8. References

- [spec-kitty glossary/contexts/doctrine.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/glossary/contexts/doctrine.md)
- [spec-kitty docs/how-to/create-an-org-doctrine-pack.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/docs/how-to/create-an-org-doctrine-pack.md)
- [spec-kitty src/charter/drg.py](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/charter/drg.py)
- [spec-kitty glossary/contexts/governance.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/glossary/contexts/governance.md)
- [AGENTS.md](/AGENTS.md)
- [docs/templates/TEMPLATE_PRACTICE.md](/docs/templates/TEMPLATE_PRACTICE.md)
- [docs/styleguide/LEX_TONE_MAP.md](/docs/styleguide/LEX_TONE_MAP.md)
- [docs/styleguide/LEX_STYLE_RULES.md](/docs/styleguide/LEX_STYLE_RULES.md)
