# User Journey: Curating External Practice into Governance

| Field | Value |
|---|---|
| **Status** | ACTIVE |
| **Implementation Status** | IMPLEMENTED — reflects current runtime reality as of 2026-03-05 |
| **Date** | 2026-02-17 (updated 2026-03-05) |
| **Primary Contexts** | Governance, Curation, Constitution |
| **Supporting Contexts** | Orchestration, Agent Profiles, Tool Selection |
| **Related Spec / ADR** | Proposed ADR: `2026-02-17-1-explicit-governance-layer-model` (not present in this branch) |

---

## Scenario

A lead developer discovers an external practice (for example, ZOMBIES TDD) and wants
it to become standard behavior for implementation agents in their Spec Kitty project.

The system supports this as a staged pull-based flow:

1. land raw reference material into the doctrine reference zone,
2. extract and author a structured doctrine artifact in the staging area,
3. curate the artifact through an interactive interview,
4. activate it through constitution-level governance selection.

---

## Actors

| # | Actor | Type | Persona | Role in Journey |
|---|-------|------|---------|-----------------|
| 1 | Lead Developer | `human` | [Lead Developer](../../audience/internal/lead-developer.md) | Identifies external practice, drives curation interview, approves adoption |
| 2 | AI Agent | `llm` | [AI Collaboration Agent](../../audience/internal/ai-collaboration-agent.md) | Extracts and authors doctrine artifacts from raw references |
| 3 | Spec-Kitty CLI | `system` | [Spec Kitty CLI Runtime](../../audience/internal/spec-kitty-cli-runtime.md) | Runs the curation interview, promotes artifacts, validates schemas |

---

## Preconditions

1. Project has `src/doctrine/` structure initialized with `_proposed/` and `shipped/` subdirectories per artifact type.
2. Constitution exists and is project authority for governance selection.
3. Schema validation tests are available in `tests/`.
4. Lead developer has identified an external source to curate.

---

## Journey Map

| Phase | Actor(s) | System / Location | Key Events |
|-------|----------|-------------------|------------|
| 0. Land | Lead Developer | `src/doctrine/_reference/<source>/` | Drop raw material (articles, excerpts, import candidates) into reference landing zone |
| 1. Extract | AI Agent | `<type>/_proposed/` | Author structured `.yaml` artifact (directive, tactic, procedure, paradigm, styleguide, or toolguide) from raw reference |
| 2. Classify | AI Agent | `_proposed/` artifact `classification` field | Map external idea to target doctrine concept; record provenance in `.import.yaml` candidate if traceability is needed |
| 3. Adapt | AI Agent ↔ Lead Developer | `_proposed/` artifact fields | Finalise wording, enforcement level, tactic refs, and opposition modeling (`opposed_by`) for Spec Kitty canon |
| 4. Curate | Lead Developer | `spec-kitty doctrine curate` | Interactive interview presents artifacts depth-first; Lead Developer accepts (→ `shipped/`), drops (→ deleted), or skips (→ deferred) |
| 5. Integrate | AI Agent | Constitution + doctrine | Update constitution selections to activate newly shipped artifacts for appropriate agent profiles |
| 6. Validate | Spec-Kitty CLI | CI / `pytest` | Schema and consistency validation confirms artifact structure; failures block activation |
| 7. Operate | AI Agent | Mission runtime | Implementation runs with newly activated governance behavior |

---

## CLI Entry Points

```bash
# Check what is proposed vs shipped
spec-kitty doctrine status

# Run interactive curation interview (resumable)
spec-kitty doctrine curate

# Resume an interrupted session
spec-kitty doctrine curate --resume

# Start fresh (discard previous session decisions)
spec-kitty doctrine curate --fresh

# Filter by artifact type
spec-kitty doctrine curate --type tactics

# Promote a single artifact directly
spec-kitty doctrine promote <artifact-id> --type directives

# Clear session state
spec-kitty doctrine reset
```

---

## Coordination Rules

1. External practices are never adopted directly — they must enter through `_reference/`
   and be extracted into `_proposed/` before curation.
2. Classification and adaptation must be explicit before the artifact is presented in
   the curation interview.
3. Constitution is the only project-level authority for activation; a shipped artifact
   is available but not active until selected.
4. Schema validation must pass before behavior is considered active.
5. Oppositions (`opposed_by`) must be documented when two valid directives or tactics
   conflict — they are not resolved away but made explicit.
6. If adaptation is ambiguous, stop and request developer confirmation.

---

## Responsibilities

### Spec-Kitty CLI (Local Runtime)

1. Present proposed artifacts in depth-first order (directives first, then referenced tactics and styleguides).
2. Persist curation session state to `.kittify/curation/state.json` (resumable across sessions).
3. Move accepted artifacts from `_proposed/` to `shipped/` via `promote_artifact()`.
4. Validate artifacts against schemas in CI.
5. Expose failures as actionable QA errors.

### AI Agent (LLM Context)

1. Analyze source practice in `_reference/` and extract applicable doctrine concepts.
2. Author structured `.yaml` artifacts in `_proposed/` with correct schema fields.
3. Propose `opposed_by` entries where legitimate tensions exist with existing doctrine.
4. Update constitution selections after artifacts are shipped.
5. Use the `doctrine-curation-interview` procedure as the authoritative guide for the curation workflow.

### Lead Developer (Human Authority)

1. Approve/reject each artifact during `spec-kitty doctrine curate`.
2. Decide activation scope via constitution selections.
3. Confirm final adoption into project standards.

---

## Scope: Implemented

### In Scope

1. Staged curation flow: `_reference/` → `_proposed/` → `shipped/`.
2. Mapping to any doctrine concept: Paradigm, Directive, Tactic, Procedure, Styleguide, Toolguide.
3. Interactive interview with depth-first artifact ordering, skip/defer, resumable session.
4. Constitution update for selected profiles and available tools.
5. Schema validation pass/fail gate.
6. Opposition modeling via `opposed_by` field.

### Out of Scope (Deferred)

- Automatic harvesting from web/catalogs.
- Bulk multi-candidate ranking/prioritization.
- Organization-wide multi-repo rollout orchestration.

---

## Required Event Set

| # | Event | Emitted By | Phase |
|---|-------|-----------|-------|
| 1 | `ReferenceMaterialLanded` | Human / Agent | 0 |
| 2 | `DoctrinArtifactAuthored` | AI Agent | 1–3 |
| 3 | `CurationDecisionRecorded` | CLI (session state) | 4 |
| 4 | `ArtifactPromoted` | CLI (`promote_artifact`) | 4 |
| 5 | `ConstitutionSelectionsUpdated` | AI Agent | 5 |
| 6 | `GovernanceValidationPassed` | CLI | 6 |
| 7 | `BehaviorActivatedForImplementation` | AI Agent | 7 |

---

## Acceptance Scenarios

1. **ZOMBIES TDD adopted as implementation behavior**
   Given a lead developer provides a ZOMBIES TDD source in `_reference/`,
   when an agent extracts it into `_proposed/`, and the lead developer accepts it
   during `spec-kitty doctrine curate`,
   then the artifact is promoted to `shipped/`,
   and constitution selections activate the behavior for implementation profiles.

2. **Invalid artifact blocked by schema gate**
   Given a malformed doctrine artifact in `_proposed/`,
   when validation runs in CI,
   then activation is blocked and actionable validation errors are reported.

3. **Constitution authority enforced**
   Given doctrine artifacts exist in `shipped/` but constitution selections are not updated,
   when implementation runs,
   then the new behavior is not considered active for project execution.

4. **Interrupted session resumed**
   Given a curation session was started and quit mid-way,
   when `spec-kitty doctrine curate` is invoked again,
   then only the remaining pending artifacts are presented; previously accepted/dropped decisions are preserved.

5. **Opposition documented for conflicting directives**
   Given two directives with conflicting enforcement under the same conditions,
   when an agent authors both artifacts,
   then `opposed_by` is set on each pointing to the other with an explicit `reason`,
   and both remain valid and shipped.

---

## Design Decisions

| Decision | Rationale | ADR |
|----------|-----------|-----|
| Three-stage pipeline (`_reference/` → `_proposed/` → `shipped/`) | Separates raw intake, structured authoring, and canonisation; each stage has clear entry/exit criteria | pending (`2026-02-17-1` proposed) |
| Curation is candidate-first | Preserves provenance and explicit adaptation | pending (`2026-02-17-1` proposed) |
| Constitution is activation authority | Keeps per-project governance explicit and auditable | pending (`2026-02-17-1` proposed) |
| Schema validation is required pre-activation | Provides early QA guardrail for governance changes | pending (`2026-02-17-1` proposed) |
| Business logic in `doctrine.curation.workflow` | Decouples orchestration from CLI I/O; enables testability without a terminal | architecture vision (2026-03-05) |
| Oppositions are documented, not resolved | Legitimate tensions between valid principles must be explicit so agents can reason about them contextually | architecture vision (2026-03-05) |

---

## Product Alignment

This journey operationalizes the governance-layer model by showing how external practices
become project behavior through a staged curation pipeline and constitution selection,
rather than ad hoc mission prompt edits. The `spec-kitty doctrine curate` command is the
canonical interactive entry point; `doctrine.curation.workflow` is the business logic
backbone that powers it.
