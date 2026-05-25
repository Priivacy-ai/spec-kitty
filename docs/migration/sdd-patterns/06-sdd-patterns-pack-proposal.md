# Proposed SDD-Patterns Spec-Kitty Pack

_Migration research document — how to create an sdd-patterns spec-kitty pack_
_Date: 2025-05-25_

## 1. Executive Summary

This document proposes a concrete plan for creating an `sdd-patterns` spec-kitty org
doctrine pack. It covers the pack identity, distribution strategy, artifact inventory,
build pipeline, and integration steps for consumer projects.

## 2. Pack Identity

| Field | Value |
|-------|-------|
| **Pack ID** | `sdd-patterns` |
| **Pack Name** | SDD Pragmatic Patterns Doctrine Pack |
| **Organization** | SDD Development |
| **Schema Version** | `1.0` |
| **Target spec-kitty** | `2.x` |
| **Repository** | `sddevelopment-be/sdd-patterns-doctrine-pack` (proposed) |
| **License** | Same as penguin-pragmatic-patterns |

## 3. Distribution Strategy

### Option A: Git Remote (Recommended)

```yaml
# Consumer project .kittify/config.yaml
doctrine:
  org:
    packs:
      - name: sdd-patterns
        source: git
        url: https://github.com/sddevelopment-be/sdd-patterns-doctrine-pack.git
        ref: v1.0.0
```

**Advantages:**
- Versioned via git tags
- No infrastructure required beyond GitHub
- Familiar for consumers already using git
- Supports pinning to specific versions

### Option B: Embedded in penguin-pragmatic-patterns

```yaml
# Consumer project .kittify/config.yaml
doctrine:
  org:
    packs:
      - name: sdd-patterns
        source: local_path
        path: ../penguin-pragmatic-patterns/.kittify/doctrine-pack
```

**Advantages:**
- No separate repository needed
- Pack evolves with the content it governs
- Simpler for single-project use

**Recommended approach:** Start with Option B (embedded) for development and validation,
then extract to Option A (separate repo) for distribution to other projects.

## 4. Pack Directory Layout

```
sdd-patterns/
├── paradigms/
│   ├── shipped/
│   │   ├── context-over-commandments.paradigm.yaml
│   │   ├── progressive-disclosure.paradigm.yaml
│   │   └── ammerse-evaluation.paradigm.yaml
│   └── README.md
├── directives/
│   ├── shipped/
│   │   ├── 001-glossary-tag-sync.directive.yaml
│   │   ├── 002-ieee-citation-format.directive.yaml
│   │   ├── 003-practice-section-completeness.directive.yaml
│   │   ├── 004-uuid-uniqueness.directive.yaml
│   │   ├── 005-tone-alignment.directive.yaml
│   │   ├── 006-no-prescriptive-absolutes.directive.yaml
│   │   └── 007-ammerse-delta-required.directive.yaml
│   └── README.md
├── tactics/
│   ├── shipped/
│   │   ├── pattern-curation-workflow.tactic.yaml
│   │   ├── bibliography-entry.tactic.yaml
│   │   ├── lex-tone-review.tactic.yaml
│   │   ├── glossary-term-addition.tactic.yaml
│   │   └── content-template-selection.tactic.yaml
│   └── README.md
├── styleguides/
│   ├── shipped/
│   │   ├── writing/
│   │   │   ├── tone-map.styleguide.yaml
│   │   │   ├── style-rules.styleguide.yaml
│   │   │   └── practice-structure.styleguide.yaml
│   │   └── content/
│   │       ├── concept-structure.styleguide.yaml
│   │       └── primer-structure.styleguide.yaml
│   └── README.md
├── toolguides/
│   ├── shipped/
│   │   ├── hugo-site-generator.toolguide.yaml
│   │   ├── plantuml-diagramming.toolguide.yaml
│   │   ├── contextive-ide-glossary.toolguide.yaml
│   │   └── toml-frontmatter.toolguide.yaml
│   └── README.md
├── procedures/
│   ├── shipped/
│   │   ├── pattern-discovery-to-publication.procedure.yaml
│   │   ├── lex-analysis-cycle.procedure.yaml
│   │   └── glossary-curation.procedure.yaml
│   └── README.md
├── agent_profiles/
│   ├── shipped/
│   │   ├── curator.agent.yaml
│   │   ├── researcher.agent.yaml
│   │   ├── lexical.agent.yaml
│   │   ├── writer-editor.agent.yaml
│   │   ├── synthesizer.agent.yaml
│   │   ├── diagrammer.agent.yaml
│   │   └── scribe.agent.yaml
│   └── README.md
├── drg/
│   ├── 010-sdd-content-types.graph.yaml
│   ├── 020-sdd-curation-workflow.graph.yaml
│   └── 030-sdd-quality-gates.graph.yaml
├── glossary/
│   └── sdd-patterns-glossary.yaml
├── org-charter.yaml
└── pack-manifest.yaml
```

## 5. Artifact Specifications

### 5.1 Example: Paradigm

```yaml
# paradigms/shipped/context-over-commandments.paradigm.yaml
schema_version: "1.0"
id: sdd-context-over-commandments
title: Context Over Commandments
description: |
  Knowledge artifacts present contextual guidance rather than prescriptive
  rules. Each pattern acknowledges trade-offs, limitations, and situations
  where it should not be applied. The reader's context determines
  applicability, not the pattern author.

  This paradigm influences all content creation: practices must include
  "when NOT to use" sections, concepts must include comparisons, and all
  artifacts must use hedging language ("consider", "can", "may") over
  prescriptive language ("must", "should", "always").
action_scope:
  - specify
  - implement
  - review
```

### 5.2 Example: Directive

```yaml
# directives/shipped/001-glossary-tag-sync.directive.yaml
schema_version: "1.0"
id: sdd-001-glossary-tag-sync
title: Glossary Tag Synchronization
severity: high
description: |
  All tags used in content frontmatter must reference terms that exist in
  the glossary registry (data/glossary.toml). Content that introduces new
  tags must also add corresponding glossary entries with proper domain
  classification, description, aliases, and references.
action_scope:
  - implement
  - review
enforcement: required
checks:
  - "Every tag in content frontmatter exists as a glossary term name or alias"
  - "New glossary entries have non-empty description fields"
  - "New glossary entries have domain classification"
```

### 5.3 Example: Styleguide

```yaml
# styleguides/shipped/writing/tone-map.styleguide.yaml
schema_version: "1.0"
id: sdd-tone-map
title: SDD Patterns Tone Map
description: |
  Defines the voice characteristics and compliance targets for all SDD
  Patterns content. Content is scored against these targets during the
  LEX analysis review cycle.
action_scope:
  - implement
  - review
rules:
  - id: calm
    description: "No urgency language, no absolutism"
    target_compliance: 0.94
  - id: clear
    description: "Concrete examples, minimal unexplained jargon"
    target_compliance: 0.91
  - id: sincere
    description: "Acknowledge limitations openly"
    target_compliance: 0.96
  - id: humble
    description: "Acknowledge reader knows their context better"
    target_compliance: 0.93
  - id: collaborative
    description: "Inclusive 'we' framing, peer stance"
    target_compliance: 0.90
  - id: practical
    description: "Actionable steps with mitigations"
    target_compliance: 0.92
  - id: balanced
    description: "Acknowledge trade-offs and negative deltas"
    target_compliance: 0.95
```

### 5.4 Example: Agent Profile

```yaml
# agent_profiles/shipped/curator.agent.yaml
schema_version: "1.0"
id: sdd-curator
role: curator
title: SDD Patterns Curator
identity: |
  The Curator agent evaluates whether new patterns align with the
  repository philosophy (context over commandments), assigns categories,
  and ensures conceptual coherence across the pattern collection.

  The Curator does not author content but reviews proposals, validates
  fit, and maintains the collection's thematic integrity.
governance_scope:
  - sdd-001-glossary-tag-sync
  - sdd-003-practice-section-completeness
  - sdd-007-ammerse-delta-required
  - sdd-context-over-commandments
capabilities:
  - pattern_sourcing
  - category_assignment
  - coherence_review
  - cross_reference_validation
```

### 5.5 Example: DRG Fragment

```yaml
# drg/010-sdd-content-types.graph.yaml
schema_version: "1.0"
pack_id: sdd-patterns
description: |
  Introduces SDD content type nodes and connects them to the styleguide
  artifacts that govern their structure.

nodes:
  - urn: "sdd:content-type:practice"
    kind: concept
    label: "Practice Pattern"
  - urn: "sdd:content-type:concept"
    kind: concept
    label: "Concept Definition"
  - urn: "sdd:content-type:primer"
    kind: concept
    label: "Primer Guide"

edges:
  - source: "sdd:content-type:practice"
    target: "urn:styleguide:sdd-practice-structure"
    relation: requires
  - source: "sdd:content-type:practice"
    target: "urn:directive:sdd-007-ammerse-delta-required"
    relation: requires
  - source: "sdd:content-type:concept"
    target: "urn:styleguide:sdd-concept-structure"
    relation: requires
  - source: "sdd:content-type:primer"
    target: "urn:styleguide:sdd-primer-structure"
    relation: requires
  - source: "urn:directive:sdd-001-glossary-tag-sync"
    target: "urn:action:software-dev/implement"
    relation: scope
  - source: "urn:directive:sdd-005-tone-alignment"
    target: "urn:action:software-dev/review"
    relation: scope
```

## 6. Org-Charter Configuration

```yaml
# org-charter.yaml
schema_version: "1.0"
org_name: "SDD Development"
pack_id: sdd-patterns

# Required for all consumer projects
required_paradigms:
  - sdd-context-over-commandments

required_directives:
  - sdd-001-glossary-tag-sync
  - sdd-003-practice-section-completeness
  - sdd-004-uuid-uniqueness

required_styleguides:
  - sdd-tone-map
  - sdd-style-rules

# Suggested (consumer can opt out)
suggested_directives:
  - sdd-002-ieee-citation-format
  - sdd-005-tone-alignment
  - sdd-006-no-prescriptive-absolutes
  - sdd-007-ammerse-delta-required

suggested_styleguides:
  - sdd-practice-structure
  - sdd-concept-structure
  - sdd-primer-structure

# Default agent profile selections
default_agent_profiles:
  - sdd-curator
  - sdd-researcher
  - sdd-lexical
  - sdd-writer-editor

# Activation registry for context-scoped selections
activation_registry:
  # Always active
  - context: {mission_type: "generic", action: "generic"}
    artifact: sdd-tone-map
    kind: styleguide

  # Documentation missions — implement action
  - context: {mission_type: "documentation", action: "implement"}
    artifact: sdd-practice-structure
    kind: styleguide
  - context: {mission_type: "documentation", action: "implement"}
    artifact: sdd-001-glossary-tag-sync
    kind: directive

  # Documentation missions — review action
  - context: {mission_type: "documentation", action: "review"}
    artifact: sdd-005-tone-alignment
    kind: directive
  - context: {mission_type: "documentation", action: "review"}
    artifact: sdd-007-ammerse-delta-required
    kind: directive

  # Research missions — specify action
  - context: {mission_type: "research", action: "specify"}
    artifact: sdd-pattern-discovery-to-publication
    kind: procedure

# Charter interview defaults
interview_defaults:
  content_types:
    - practice
    - concept
    - primer
  citation_format: ieee
  tone_strictness: standard
  glossary_strictness: medium
```

## 7. Build Pipeline

### Step 1: Artifact Authoring

Convert existing Markdown governance files to YAML:

```bash
# Working directory: penguin-pragmatic-patterns

# Create pack directory
mkdir -p .kittify/doctrine-pack/{paradigms,directives,tactics,styleguides,toolguides,procedures,agent_profiles,drg,glossary}/shipped

# Convert agent profiles
for agent in .github/agents/*.agent.md; do
  # Manual conversion: read MD, write YAML following agent profile schema
  echo "Convert: $agent"
done

# Convert directives
for directive in .github/agents/directives/*.md; do
  echo "Convert: $directive"
done

# Convert guidelines to styleguides/directives
for guideline in .github/agents/guidelines/*.md; do
  echo "Convert: $guideline"
done
```

### Step 2: Glossary Conversion

```bash
# Convert TOML glossary to kittified YAML
# (use docs/migration/05-sdd-patterns-glossary-kittified.yaml as starting point)
cp docs/migration/05-sdd-patterns-glossary-kittified.yaml \
   .kittify/doctrine-pack/glossary/sdd-patterns-glossary.yaml
```

### Step 3: DRG Fragment Creation

```bash
# Create DRG fragments in drg/ directory
# (follow examples from section 5.5)
```

### Step 4: Pack Validation

```bash
# Once spec-kitty supports pack validation:
spec-kitty doctrine pack validate .kittify/doctrine-pack/

# Or manual validation:
# - Check all YAML files parse correctly
# - Verify all IDs are unique within the pack
# - Verify all DRG edges reference valid nodes
# - Verify all agent profile governance_scope references exist
```

### Step 5: Pack Assembly

```bash
# Once spec-kitty supports pack assembly:
spec-kitty doctrine pack assemble .kittify/doctrine-pack/ --output sdd-patterns-v1.0.0

# Generates pack-manifest.yaml with:
# - Pack version
# - Build timestamp
# - Artifact inventory
# - DRG integrity hash
```

### Step 6: Distribution

```bash
# Extract to separate repository for distribution
git init sdd-patterns-doctrine-pack
cp -r .kittify/doctrine-pack/* sdd-patterns-doctrine-pack/
cd sdd-patterns-doctrine-pack
git add .
git commit -m "Initial sdd-patterns doctrine pack v1.0.0"
git tag -a v1.0.0 -m "SDD Patterns Doctrine Pack v1.0.0"
git remote add origin https://github.com/sddevelopment-be/sdd-patterns-doctrine-pack.git
git push -u origin main --tags
```

## 8. Consumer Integration

### For new projects

```bash
# Initialize spec-kitty with sdd-patterns pack
spec-kitty init --ai claude

# Add pack to config
spec-kitty doctrine pack add sdd-patterns \
  --source git \
  --url https://github.com/sddevelopment-be/sdd-patterns-doctrine-pack.git \
  --ref v1.0.0

# Run charter interview (inherits sdd-patterns defaults)
spec-kitty charter interview

# Verify
spec-kitty doctor doctrine
```

### For existing projects

```bash
# Add pack
spec-kitty doctrine pack add sdd-patterns \
  --source git \
  --url https://github.com/sddevelopment-be/sdd-patterns-doctrine-pack.git

# Re-run charter to pick up new selections
spec-kitty charter update

# Verify DRG merge
spec-kitty doctor drg
```

## 9. Maintenance Strategy

### Versioning

- **Pack version** follows semver independently from penguin-pragmatic-patterns
- **Major** bumps for breaking schema changes (artifact removal, field renames)
- **Minor** bumps for new artifacts, new DRG edges, new agent profiles
- **Patch** bumps for content corrections, typo fixes, description updates

### Sync with Source Repository

```
penguin-pragmatic-patterns/           sdd-patterns-doctrine-pack/
├── .github/agents/*.agent.md    →    ├── agent_profiles/shipped/*.agent.yaml
├── .github/agents/directives/   →    ├── directives/shipped/*.directive.yaml
├── .github/agents/guidelines/   →    ├── styleguides/shipped/*.styleguide.yaml
├── docs/styleguide/LEX_*.md     →    ├── styleguides/shipped/writing/*.yaml
├── docs/templates/TEMPLATE_*    →    ├── (template set references)
├── data/glossary.toml           →    └── glossary/sdd-patterns-glossary.yaml
```

Changes to source Markdown files should trigger a review of corresponding YAML artifacts.
This is a manual process until bidirectional sync tooling exists.

### Upstream Collaboration

When spec-kitty adds glossary pack support:
1. Register `sdd-patterns-glossary.yaml` as a glossary pack
2. Enable glossary strictness enforcement for SDD terms
3. Integrate with DRG glossary nodes via `drg_builder.py`

When spec-kitty adds `doctrine pack` CLI:
1. Replace manual build steps with CLI commands
2. Integrate into CI pipeline for automated validation
3. Publish pack artifacts as GitHub releases

## 10. Migration Checklist

- [ ] Convert 13 agent profiles from Markdown to `*.agent.yaml`
- [ ] Convert 12 extended directives from Markdown to `*.directive.yaml`
- [ ] Convert 4 guidelines from Markdown to `*.styleguide.yaml` / `*.directive.yaml`
- [ ] Create 3 paradigm artifacts from repository philosophy
- [ ] Create 5 tactic artifacts from workflow patterns
- [ ] Create 5 styleguide artifacts from LEX framework
- [ ] Create 4 toolguide artifacts from tooling conventions
- [ ] Create 3 procedure artifacts from compound workflows
- [ ] Create 3 DRG fragment files
- [ ] Convert TOML glossary to kittified YAML (partial — high-value terms)
- [ ] Create org-charter.yaml with selections and activation registry
- [ ] Generate or create pack-manifest.yaml
- [ ] Validate all YAML artifacts parse correctly
- [ ] Validate DRG edge references
- [ ] Validate agent profile governance_scope references
- [ ] Test pack loading in a spec-kitty project
- [ ] Tag v1.0.0 and publish

## 11. References

- [spec-kitty docs/how-to/create-an-org-doctrine-pack.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/docs/how-to/create-an-org-doctrine-pack.md)
- [spec-kitty glossary/contexts/doctrine.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/glossary/contexts/doctrine.md)
- [spec-kitty src/charter/drg.py](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/charter/drg.py)
- [spec-kitty src/charter/bundle.py](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/charter/bundle.py)
- [spec-kitty src/doctrine/schemas/](https://github.com/Priivacy-ai/spec-kitty/tree/main/src/doctrine/schemas/)
- [AGENTS.md](/AGENTS.md) — Current agentic framework
- [data/glossary.toml](/data/glossary.toml) — Current glossary
- [docs/styleguide/LEX_TONE_MAP.md](/docs/styleguide/LEX_TONE_MAP.md) — Tone characteristics
