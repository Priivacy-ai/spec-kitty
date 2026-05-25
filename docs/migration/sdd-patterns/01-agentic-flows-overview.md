# Agentic Flows and Approaches: SDD Pragmatic Patterns

_Migration research document — prepared for spec-kitty doctrine bundle extraction_
_Date: 2025-05-25_

## 1. Executive Summary

The penguin-pragmatic-patterns repository implements a multi-agent orchestration framework
with 13 specialized agent profiles, a 6-layer governance stack, 12 extended directives, and
a mature content-curation pipeline. This document maps each agentic component to its
spec-kitty doctrine equivalent to support extraction into a reusable doctrine pack.

## 2. Governance Stack (Context Layers)

The AGENTS.md defines a strict initialization order that all agents must follow:

| Layer | Priority | Location | Spec-Kitty Equivalent |
|-------|----------|----------|----------------------|
| Bootstrap Protocol | Root | `.github/agents/guidelines/bootstrap.md` | Paradigm (worldview framing) |
| General Guidelines | Highest | `.github/agents/guidelines/general_guidelines.md` | Directive (constraint rules) |
| Operational Guidelines | High | `.github/agents/guidelines/operational_guidelines.md` | Directive + Styleguide |
| Project Vision Reference | Medium | `docs/VISION.md` | Charter Selection (project-level) |
| Project Specific Guidelines | Medium-Low | `docs/specific_guidelines.md` | Charter Selection (narrow scope) |
| Command Aliases Reference | Medium-Low | `.github/agents/aliases.md` | Tactic (execution patterns) |

### Initialization Contract

Agents MUST load layers in order. If any layer is missing or conflicting, the agent pauses
execution until synchronization. After loading:

1. Run `/validate-alignment`
2. Announce readiness with integrity confirmation

This maps directly to spec-kitty's **Charter-Mediated Selection** pattern, where the charter
is the sole authority that decides which doctrine artifacts apply to a given mission run.

### Conflict Resolution

- **Priority order:** Operational > Strategic > Command convenience
- **Halt + flag** when a command conflicts with tone/ethics
- **Never silently override** rules

This corresponds to spec-kitty's **Precedence Rule** governance term:
`CLI override > step metadata > mission config > global default`.

## 3. Agent Profiles

The repository defines 13 specialized agent roles in `.github/agents/`:

| Agent | File | Role | Spec-Kitty Artifact Kind |
|-------|------|------|-------------------------|
| Bootstrap Bill | `bootstrap-bill.agent.md` | Repo structure mapping, topology discovery | Agent Profile |
| Curator | `curator.agent.md` | Content curation, pattern sourcing, coherence | Agent Profile |
| Diagrammer | `diagrammer.agent.md` | PlantUML diagram generation | Agent Profile + Toolguide |
| Frontend | `frontend.agent.md` | UI/UX, theme customization | Agent Profile |
| Lexical | `lexical.agent.md` | Terminology management, tone/style analysis | Agent Profile + Styleguide |
| Researcher | `researcher.agent.md` | Reference management, bibliography expansion | Agent Profile |
| Scribe | `scribe.agent.md` | Documentation writing, bootstrap artifacts | Agent Profile |
| Synthesizer | `synthesizer.agent.md` | Cross-pattern coherence, content synthesis | Agent Profile |
| Writer-Editor | `writer-editor.agent.md` | Content editing, quality polishing | Agent Profile + Styleguide |
| Architect | `architect.agent.md` | ADRs, system design | Agent Profile |
| Backend Dev | `backend-dev.agent.md` | Backend development tasks | Agent Profile |
| Build Automation | `build-automation.agent.md` | CI/CD and build pipeline tasks | Agent Profile + Toolguide |
| Manager | `manager.agent.md` | Project planning and coordination | Agent Profile |

### Profile Extraction Notes

Each agent profile contains:
- **Context sources** — which files to read for context
- **Purpose** — role summary
- **Key responsibilities** — operational scope
- **Tools/capabilities** — allowed operations
- **Communication style** — tone and format constraints

These map directly to spec-kitty's `*.agent.yaml` schema, which declares:
`id`, `role`, `title`, `identity`, and `governance_scope`.

## 4. Extended Directives

The repository maintains 12 externalized directive files in `.github/agents/directives/`:

| Code | Directive | Purpose | Spec-Kitty Mapping |
|------|-----------|---------|-------------------|
| 001 | CLI & Shell Tooling | Tool usage rubric (fd/rg/ast-grep/jq/yq/fzf) | Toolguide |
| 002 | Context Notes | Profile precedence & shorthand caution | Directive |
| 003 | Repository Quick Reference | Directory roles & Hugo version requirement | Toolguide |
| 004 | Documentation & Context Files | Canonical structural & workflow references | Directive |
| 005 | Agent Profiles | Role specialization catalog | Agent Profile registry |
| 006 | Version Governance | Versioned layer table & update rules | Directive |
| 007 | Agent Declaration | Mandatory operational authority affirmation | Directive (procedural) |
| 008 | Artifact Templates | Template locations & usage rules | Template Set |
| 009 | Role Capabilities | Allowed operational verbs & conflict prevention | Directive |
| 010 | Mode Protocol | Standardized mode transitions & misuse indicators | Procedure |
| 011 | Risk & Escalation | Markers, triggers, remediation procedure | Directive |
| 012 | Common Operating Procedures | Centralized behavioral norms | Directive (cross-cutting) |

### Load Pattern

Directives are loaded on-demand via:
```
/require-directive 001
/require-directive 006
```

This maps to spec-kitty's **Context-Scoped Selection** where artifacts activate only for a
specific mission_type × action pair, rather than being always-on globally.

## 5. Reasoning Modes

Three runtime modes govern agent cognition:

| Mode | Command | Purpose | Spec-Kitty Mapping |
|------|---------|---------|-------------------|
| Analysis | `/analysis-mode` (default) | Analytical reasoning, fact-based | Paradigm |
| Creative | `/creative-mode` | Narrative, metaphor, brainstorming | Paradigm |
| Meta | `/meta-mode` | Self-reflection, process analysis | Procedure |

Mode transitions must be annotated: `[mode: creative → analysis]`.

These map to spec-kitty **Paradigms** — worldview-level framings that influence how work is
approached but are not executable step recipes themselves.

## 6. Content Curation Workflow

The pattern publication pipeline follows a defined lifecycle:

```
Concept → Issue/Discussion → Template Selection → Content Authoring
    → Metadata Assignment → Glossary Sync → Branch/PR → Review
    → Preview Deploy → Production Merge → Netlify Publication
```

### Workflow Stages

| Stage | Description | Agents Involved | Spec-Kitty Phase |
|-------|-------------|-----------------|------------------|
| **Discovery** | Pattern idea sourced from experience, literature, or discussion | Researcher, Curator | specify |
| **Research** | Source validation, reference gathering, bibliography entry | Researcher | specify/plan |
| **Drafting** | Content authoring using template (practice/concept/primer) | Writer-Editor, Scribe | implement |
| **Metadata** | UUID generation, tag assignment, AMMERSE evaluation | Lexical, Curator | implement |
| **Glossary Sync** | Verify tags exist in `data/glossary.toml` | Lexical | implement |
| **Diagrams** | PlantUML visualization where applicable | Diagrammer | implement |
| **Review** | PR review cycle, style validation, structure check | Writer-Editor, Synthesizer | review |
| **Preview** | GitHub Pages deploy from `develop` branch | Build Automation | review |
| **Publication** | Merge to `main`, Netlify deploy | Manager | accept/merge |

### Validation Gates

- TOML front matter syntax validation
- Tag existence checks against glossary
- UUID uniqueness verification
- Required section presence (Problem/Intent/Solution/Consequences for practices)
- Image reference validation
- Tone/style compliance via LEX framework

## 7. Writing Style System (LEX Framework)

The LEX framework is a comprehensive style governance system:

### LEX_TONE_MAP (Voice Characteristics)

| Characteristic | Compliance | Description |
|---------------|------------|-------------|
| Calm | 94% | No urgency, no absolutism |
| Clear | 91% | Concrete examples, minimal unexplained jargon |
| Sincere | 96% | Acknowledges limitations |
| Humble | 93% | "You know your context better than we do" |
| Collaborative | 90% | Inclusive "we" framing |
| Practical | 92% | Actionable steps with mitigations |
| Balanced | 95% | Acknowledges trade-offs and negative deltas |

### LEX_STYLE_RULES

- Prefer active voice over passive
- Use "consider", "can", "may" over "must", "should"
- Include "when NOT to use" clarifications
- Acknowledge limitations explicitly
- Avoid prescriptive absolutes
- Max 3-4 sentences per topic paragraph
- IEEE citation format for references

### Spec-Kitty Mapping

The LEX framework maps to:
- **Styleguide artifacts** — `kitty-glossary-writing.styleguide.yaml` equivalent
- **Directive artifacts** — for mandatory style rules
- **Template Sets** — for structural requirements (AMMERSE evaluation, section ordering)

## 8. Template System

### Content Templates

| Template | Location | Content Type | Key Sections |
|----------|----------|-------------|-------------|
| Practice | `docs/templates/TEMPLATE_PRACTICE.md` | Problem-solution patterns | Problem/Intent/Solution/Forces/Rationale/Consequences |
| Concept | `docs/templates/TEMPLATE_CONCEPT.md` | Definitional content | Definition/Components/Background/Comparisons/Examples |
| Pattern | `docs/templates/TEMPLATE_pattern.md` | Streamlined patterns | Context/Problem/Intent/Forces/Solution/Rationale |
| Agent | `docs/templates/TEMPLATE_SPECIALIST_AGENT.agent.md` | Agent role definition | Context/Purpose/Responsibilities/Tools/Style |
| Primer | `docs/templates/primers/TEMPLATE_PROGRAMMING_PRIMER.md` | Programming language guides | Philosophy/Syntax/Tooling/Testing/Application |

### Supporting Templates

| Category | Templates | Purpose |
|----------|-----------|--------|
| LEX | `LEX_DELTAS.md`, `LEX_REPORT.md`, `LEX_STYLE_RULES.md` | Style governance |
| Architecture | `adr.md`, `design_vision.md`, `functional_requirements.md`, `roadmap.md`, `technical_design.md` | System design |
| Structure | `REPO_MAP.md`, `SURFACES.md`, `CONTEXT_LINKS.md`, `WORKFLOWS.md` | Bootstrap artifacts |
| Automation | `NEW_SPECIALIST.agent.md`, `PERSONA.md` | Agent and persona creation |

### Spec-Kitty Mapping

Templates map to **Template Sets** in the doctrine model. Each set shapes output artifacts
and interaction contracts. The practice template's AMMERSE evaluation system is a unique
element not present in current spec-kitty templates and represents a contribution opportunity.

## 9. Research and Reference Management

### Bibliography System

- **Source:** `data/bibliography.toml` (41.7KB, comprehensive)
- **Fields per entry:** `id` (UUID), `title`, `authors`, `publisher`, `year`, `link`,
  `image`, `levels`, `tags`, `description`
- **Auto-generation:** `src/scripts/ops/generate_books.sh` creates Hugo content pages
- **Citation format:** IEEE convention

### Reference Workflow

1. **Source Discovery** — Researcher agent scans for relevant materials
2. **Entry Creation** — Add to `data/bibliography.toml` with UUID
3. **Page Generation** — Run generation script for Hugo pages
4. **Cross-Linking** — `further_exploration` frontmatter links patterns to sources

### Spec-Kitty Mapping

The bibliography system has no direct equivalent in spec-kitty. It could be modeled as:
- A **Toolguide** for reference management practices
- A **data artifact** in the doctrine pack (new artifact kind)
- Or maintained as a project-level asset outside doctrine scope

## 10. Glossary System

### Current Implementation

- **Format:** TOML (`data/glossary.toml`, ~99KB, ~150+ entries)
- **Domains:** software, communication, productivity, psychology, management, etc.
- **Fields:** `name`, `abbreviation`, `domain`, `description`, `aliases`, `references`
- **IDE Integration:** Contextive glossaries in `.contextive/*.glossary.yml`

### Spec-Kitty Glossary Comparison

| Feature | SDD Patterns | Spec-Kitty |
|---------|-------------|------------|
| Format | TOML | YAML |
| Status tracking | No | Yes (candidate/canonical/deprecated) |
| Scoping | Domain-based | Layered (core/team/audience/mission) |
| Strictness | Not enforced | 3 modes (off/medium/max) |
| DRG integration | No | Yes (glossary nodes in DRG) |
| IDE integration | Contextive | Glossary semantic pipeline |
| Cross-references | Implicit via aliases | Explicit `see_also` fields |
| Confidence scores | No | Yes (0.0-1.0) |

## 11. Integrity and Safety Protocols

### Integrity Symbols

| Symbol | Meaning | When Used |
|--------|---------|----------|
| ❗️ | Critical error / misalignment detected | Command conflicts with tone/ethics |
| ⚠️ | Low confidence / assumption-based reasoning | Uncertain output |
| ✅ | Alignment confirmed | Post-validation check |

### Safety Mechanisms

1. **Validation on long tasks** — `/validate-alignment` after major mode shifts
2. **Tone comparison** — Compare against Operational + Strategic references
3. **No autonomous actions** — Require explicit approval for web/file actions
4. **Announce high-impact steps** — Before irreversible operations
5. **Recovery protocol** — Reload layers, confirm versions, re-validate on state loss

### Spec-Kitty Mapping

These map to:
- **Clarification Burst Policy** — limiting interruptions, prioritizing highest-impact conflicts
- **Glossary Strictness Policy** — governance rule for how semantic conflicts are treated
- **Human-in-Charge (HiC)** — explicit approval model for consequential actions

## 12. References

- [AGENTS.md](/AGENTS.md) — Primary agent governance document
- [docs/VISION.md](/docs/VISION.md) — Project vision template
- [docs/specific_guidelines.md](/docs/specific_guidelines.md) — Repository-specific constraints
- [spec-kitty glossary/contexts/doctrine.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/glossary/contexts/doctrine.md) — Doctrine domain glossary
- [spec-kitty glossary/contexts/governance.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/glossary/contexts/governance.md) — Governance domain glossary
- [spec-kitty docs/how-to/create-an-org-doctrine-pack.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/docs/how-to/create-an-org-doctrine-pack.md) — Org pack creation guide
