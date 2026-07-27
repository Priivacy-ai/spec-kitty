---
work_package_id: WP02
title: Brownfield Analysis Tactics
dependencies:
- WP01
requirement_refs:
- FR-003
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:sonnet:curator-carla:implementer"
shell_pid: "82277"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
execution_mode: code_change
owned_files:
- src/doctrine/tactics/shipped/analysis/ammerse-impact-analysis.tactic.yaml
- src/doctrine/tactics/shipped/analysis/analysis-extract-before-interpret.tactic.yaml
- src/doctrine/tactics/shipped/analysis/bounded-context-canvas-fill.tactic.yaml
- src/doctrine/tactics/shipped/analysis/bounded-context-identification.tactic.yaml
- src/doctrine/tactics/shipped/analysis/connascence-analysis.tactic.yaml
- src/doctrine/tactics/shipped/analysis/context-boundary-inference.tactic.yaml
- src/doctrine/tactics/shipped/analysis/context-mapping-classification.tactic.yaml
- src/doctrine/tactics/shipped/analysis/entity-value-object-classification.tactic.yaml
- src/doctrine/tactics/shipped/analysis/premortem-risk-identification.tactic.yaml
- src/doctrine/tactics/shipped/analysis/requirements-validation-workflow.tactic.yaml
- src/doctrine/tactics/shipped/analysis/reverse-speccing.tactic.yaml
- src/doctrine/tactics/shipped/analysis/safe-to-fail-experiment.tactic.yaml
- src/doctrine/tactics/shipped/analysis/strategic-domain-classification.tactic.yaml
- src/doctrine/tactics/shipped/analysis/code-documentation-analysis.tactic.yaml
- src/doctrine/tactics/shipped/analysis/terminology-extraction-mapping.tactic.yaml
- src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-code-documentation-analysis.import.yaml
- src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-terminology-extraction-mapping.import.yaml
authoritative_surface: src/doctrine/tactics/shipped/analysis/
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

This WP owns the `src/doctrine/tactics/shipped/analysis/` directory end-to-end: move 13 existing analysis tactics from the `shipped/` root into `analysis/`, then create 2 new brownfield analysis tactics in the same directory.

**Step 1 — Move existing analysis tactics** (13 files): create `analysis/` if absent, then `git mv` each listed tactic from `shipped/` to `shipped/analysis/`. Do NOT modify YAML content.

**Step 2 — Create new brownfield tactics** (T006, T007): adapt from quickstart project materials.

**Step 3 — Create provenance imports** (T008) and verify (T009).

**Attribution (C-006)**: Each new shipped tactic's `notes` field must contain the line `Adapted from patterns.sddevelopment.be`.

**NFR-003 baseline**: The pre-move count was captured in WP01. After this WP merges, `len(repo.load_all())` must still equal that baseline (moves + new files = baseline + 2).

---

## Context

- Tactic YAML schema: `src/doctrine/schemas/tactic.schema.yaml` — required fields: `schema_version`, `id`, `name`, `purpose`, `steps[]` (each with `title`, `description`)
- Optional but expected: `notes`, `failure_modes`, `references[]`
- Import file format: see `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-input-validation-fail-fast.import.yaml` for the established pattern
- Create `analysis/` if WP01 has not merged yet: `mkdir -p src/doctrine/tactics/shipped/analysis/`

**Tactics to move from root → `analysis/`** (13 files):
```
ammerse-impact-analysis.tactic.yaml
analysis-extract-before-interpret.tactic.yaml
bounded-context-canvas-fill.tactic.yaml
bounded-context-identification.tactic.yaml
connascence-analysis.tactic.yaml
context-boundary-inference.tactic.yaml
context-mapping-classification.tactic.yaml
entity-value-object-classification.tactic.yaml
premortem-risk-identification.tactic.yaml
requirements-validation-workflow.tactic.yaml
reverse-speccing.tactic.yaml
safe-to-fail-experiment.tactic.yaml
strategic-domain-classification.tactic.yaml
```

---

## Subtask T006 — Create `code-documentation-analysis.tactic.yaml`

**Purpose**: Encode the tactic for extracting terminology from codebase and documentation to identify semantic clusters revealing implicit context boundaries.

**File**: `src/doctrine/tactics/shipped/analysis/code-documentation-analysis.tactic.yaml`

**Content to produce** (adapt and generalize — no quickstart-specific paths):

```yaml
schema_version: "1.0"
id: code-documentation-analysis
name: Code and Documentation Analysis for Boundary Discovery
purpose: >
  Extract domain terminology from codebase and documentation to identify semantic
  clusters that reveal implicit context boundaries. Use when analyzing an existing
  (brownfield) system to discover bounded context candidates before refactoring or
  extending it. Not applicable when starting greenfield with no existing codebase.
steps:
  - title: Identify source materials
    description: >
      Locate the codebase (source files, module names, class and function names)
      and documentation (README, ADRs, specs, comments). Both sources are required;
      code alone reveals structure, documentation reveals intent.
  - title: Extract terminology from code
    description: >
      Collect domain terms from all code artifacts: class names, method names,
      module/package names, variable names in public interfaces, and domain-specific
      constants. Exclude generic infrastructure terms (handler, manager, util, helper).
      Use grep/rg or an AST parser to enumerate identifiers at scale.
  - title: Extract terminology from documentation
    description: >
      Collect domain terms from documentation artifacts: noun phrases used to describe
      system capabilities, terms defined in glossaries or READMEs, entities and events
      named in ADRs and specs. Prefer terms that recur across multiple documents.
  - title: Identify semantic clusters
    description: >
      Group collected terms by semantic affinity. Terms that co-occur frequently in code
      and documentation, or that are defined together in a module, belong to the same
      cluster. Each cluster is a candidate bounded context boundary.
  - title: Produce glossary candidates
    description: >
      For each cluster, list its canonical terms, suspected synonyms, and any
      conflicts (same term used with different meanings). Output as a structured
      list for review with domain experts. Flag terms that appear in multiple clusters
      as boundary indicators requiring disambiguation.
failure_modes:
  - "Collecting only code terms and ignoring documentation — code reveals structure but not intent; both are needed."
  - "Including infrastructure terms (Handler, Manager, Util) that obscure domain semantics."
  - "Stopping at single-word terms — noun phrases often carry more domain specificity than individual nouns."
notes: >
  Adapted from patterns.sddevelopment.be.
  This tactic is a prerequisite for bounded context identification and context mapping.
  Feed its output into the `bounded-context-identification` and `context-mapping-classification`
  tactics for the next analysis step.
references:
  - name: Bounded Context Identification
    type: tactic
    id: bounded-context-identification
    when: After clusters are identified, use this tactic to formalize the boundary candidates
  - name: Terminology Extraction and Mapping
    type: tactic
    id: terminology-extraction-mapping
    when: Run alongside or after this tactic to build the formal glossary from extracted terms
```

**Validation**: Content is domain-language focused; no quickstart project paths appear; `notes` has attribution line.

---

## Subtask T007 — Create `terminology-extraction-mapping.tactic.yaml`

**Purpose**: Encode the tactic for systematically extracting domain terms from multiple sources and mapping their relationships to build a maintainable glossary.

**File**: `src/doctrine/tactics/shipped/analysis/terminology-extraction-mapping.tactic.yaml`

**Content to produce**:

```yaml
schema_version: "1.0"
id: terminology-extraction-mapping
name: Terminology Extraction and Mapping
purpose: >
  Systematically extract domain terms from multiple sources (code, docs, transcripts,
  specs) and map their relationships to build a comprehensive, maintainable glossary.
  Use when a project lacks a shared vocabulary, when terminology drift is causing
  communication failures, or as a follow-up to code-documentation-analysis.
steps:
  - title: Identify source materials
    description: >
      Enumerate all sources that carry domain terminology: source code (class/method
      names), documentation (READMEs, ADRs, specs), stakeholder transcripts or
      meeting notes, and existing glossaries (even informal ones). Rank sources by
      authority — specs and ADRs typically outrank code comments.
  - title: Extract candidate terms
    description: >
      From each source, collect noun phrases that name concepts, entities, events,
      roles, or relationships in the problem domain. Assign each term its source and
      the context in which it appeared. Prefer complete noun phrases over single words.
  - title: Map relationships and conflicts
    description: >
      For each pair of terms with overlapping meaning, classify the relationship:
      synonym (same concept, different word), hypernym/hyponym (general/specific),
      homonym (same word, different meaning in different contexts), or conflict
      (contradictory definitions). Homonyms and conflicts are boundary indicators.
  - title: Assign ownership by bounded context
    description: >
      For each term, identify which bounded context owns its canonical definition.
      Cross-context uses of the same term must be explicitly translated at the
      context boundary — do not assume shared meaning.
  - title: Publish and validate
    description: >
      Present the draft glossary to domain experts and implementers for validation.
      Unresolvable conflicts must be escalated as open questions. The validated
      glossary becomes the authoritative source for the project ubiquitous language.
failure_modes:
  - "Treating synonyms as interchangeable without documenting the canonical term — creates drift."
  - "Ignoring conflicts between bounded contexts — they indicate missing ACL or translation layers."
  - "Building the glossary bottom-up from code alone — misses the intent expressed in documentation."
notes: >
  Adapted from patterns.sddevelopment.be.
references:
  - name: Code and Documentation Analysis
    type: tactic
    id: code-documentation-analysis
    when: Use as the upstream term-extraction step before mapping relationships
  - name: Language-Driven Design
    type: tactic
    id: language-driven-design
    when: Apply after the glossary is validated to enforce the ubiquitous language in code
```

---

## Subtask T008 — Create provenance import files

**Purpose**: Record the source and adaptation notes for both tactics in the established `_reference/` format.

**Files to create** (use the existing `tactic-input-validation-fail-fast.import.yaml` as a template):

`src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-code-documentation-analysis.import.yaml`:

```yaml
id: "imp-quickstart-code-documentation-analysis"
source:
  title: "Tactic: Code and Documentation Analysis for Boundary Discovery"
  type: "tactic"
  publisher: "quickstart_agent-augmented-development"
  accessed_on: "2026-04-26"
classification:
  target_concepts:
    - "tactic"
  rationale: >
    Systematic extraction of domain terminology from code and documentation to
    identify implicit bounded context boundaries. Brownfield analysis prerequisite.
adaptation:
  summary: >
    Converted from markdown to spec-kitty tactic YAML schema. Steps generalized
    to remove project-specific tooling references. Failure modes added from
    practitioner experience. Cross-references added to bounded-context-identification
    and terminology-extraction-mapping.
  notes:
    - "Source references patterns.sddevelopment.be — preserved as attribution in notes field."
    - "All local file paths removed from shipped YAML."
external_references:
  - title: "Bounded Context Linguistic Discovery (patterns.sddevelopment.be)"
    url: "https://patterns.sddevelopment.be"
    extraction_action: none
status: "adopted"
resulting_artifacts:
  - "src/doctrine/tactics/shipped/analysis/code-documentation-analysis.tactic.yaml"
```

Create an equivalent file for `terminology-extraction-mapping` with appropriate IDs and descriptions.

---

## Subtask T009 — Verify both tactics load and validate

**Steps**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.tactics.repository import TacticRepository
r = TacticRepository()
all_tactics = r.load_all()
assert 'code-documentation-analysis' in all_tactics, 'code-documentation-analysis not found'
assert 'terminology-extraction-mapping' in all_tactics, 'terminology-extraction-mapping not found'
print('Both tactics load successfully')
"
pytest -m doctrine -q
```

**Validation checklist**:
- [ ] Both YAML files exist in `src/doctrine/tactics/shipped/analysis/`
- [ ] Both tactic IDs resolve in the repository
- [ ] `notes` field contains `Adapted from patterns.sddevelopment.be` in each
- [ ] No local filesystem paths appear in shipped YAML content
- [ ] `pytest -m doctrine -q` is green

---

## Branch Strategy

No dependencies — this WP can start immediately. Merges into `feature/doctrine-enrichment-bdd-profiles`.

```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Definition of Done

- Two new YAML tactics exist in `shipped/analysis/`
- Two provenance import files exist in `_reference/`
- Both tactics load via the repository
- Attribution line present in each tactic's `notes`
- Doctrine test suite green

## Reviewer Guidance

- Verify no quickstart project paths appear in shipped YAML
- Verify each tactic's `id` matches its filename stem
- Verify `notes` attribution line is present
- Confirm `failure_modes` are domain-relevant, not implementation-specific

## Activity Log

- 2026-04-26T12:13:50Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Started implementation via action command
- 2026-04-26T12:25:54Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – 13 analysis tactics moved + terminology-extraction-mapping created + 2 provenance imports; 1121 doctrine tests green
- 2026-04-26T12:26:23Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Review passed: 13 analysis tactics renamed (100% similarity), code-documentation-analysis moved from root (pre-existing), terminology-extraction-mapping created new. Both new tactic IDs load correctly. 2 provenance import files created. Doctrine tests green (1121 pass).
- 2026-04-26T13:10:17Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
