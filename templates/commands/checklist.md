---
description: Generate a custom checklist for the current feature based on user requirements.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Execution Steps

1. **Setup**: Run `{SCRIPT}` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS list.
   - All file paths must be absolute.

2. **Clarify intent (dynamic)**: Derive up to THREE initial contextual clarifying questions (no pre-baked catalog). They MUST:
   - Be generated from the user's phrasing + extracted signals from spec/plan/tasks
   - Only ask about information that materially changes checklist content
   - Be skipped individually if already unambiguous in `$ARGUMENTS`
   - Prefer precision over breadth

   Generation algorithm:
   1. Extract signals: feature domain keywords (e.g., auth, latency, UX, API), risk indicators ("critical", "must", "compliance"), stakeholder hints ("QA", "review", "security team"), and explicit deliverables ("a11y", "rollback", "contracts").
   2. Cluster signals into candidate focus areas (max 4) ranked by relevance.
   3. Identify probable audience & timing (author, reviewer, QA, release) if not explicit.
   4. Detect missing dimensions: scope breadth, depth/rigor, risk emphasis, exclusion boundaries, measurable acceptance criteria.
   5. Formulate questions chosen from these archetypes:
      - Scope refinement (e.g., "Should this include integration touchpoints with X and Y or stay limited to local module correctness?")
      - Risk prioritization (e.g., "Which of these potential risk areas should receive mandatory gating checks?")
      - Depth calibration (e.g., "Is this a lightweight pre-commit sanity list or a formal release gate?")
      - Audience framing (e.g., "Will this be used by the author only or peers during PR review?")
      - Boundary exclusion (e.g., "Should we explicitly exclude performance tuning items this round?")
      - Scenario class gap (e.g., "No recovery flows detected—are rollback / partial failure paths in scope?")

   Question formatting rules:
   - If presenting options, generate a compact table with columns: Option | Candidate | Why It Matters
   - Limit to A–E options maximum; omit table if a free-form answer is clearer
   - Never ask the user to restate what they already said
   - Avoid speculative categories (no hallucination). If uncertain, ask explicitly: "Confirm whether X belongs in scope."

   Defaults when interaction impossible:
   - Depth: Standard
   - Audience: Reviewer (PR) if code-related; Author otherwise
   - Focus: Top 2 relevance clusters

   Output the questions (label Q1/Q2/Q3). After answers: if ≥2 scenario classes (Alternate / Exception / Recovery / Non-Functional domain) remain unclear, you MAY ask up to TWO more targeted follow‑ups (Q4/Q5) with a one-line justification each (e.g., "Unresolved recovery path risk"). Do not exceed five total questions. Skip escalation if user explicitly declines more.

3. **Understand user request**: Combine `$ARGUMENTS` + clarifying answers:
   - Derive checklist theme (e.g., security, review, deploy, ux)
   - Consolidate explicit must-have items mentioned by user
   - Map focus selections to category scaffolding
   - Infer any missing context from spec/plan/tasks (do NOT hallucinate)

4. **Load feature context**: Read from FEATURE_DIR:
   - spec.md: Feature requirements and scope
   - plan.md (if exists): Technical details, dependencies
   - tasks.md (if exists): Implementation tasks
   - Use context to enrich or validate checklist items (omit irrelevant categories)

5. **Generate checklist**:
   - Create `FEATURE_DIR/checklists/` directory if it doesn't exist
   - Generate unique checklist filename:
     * Use short, descriptive name based on checklist type
     * Format: `[type].md` (e.g., `ux.md`, `test.md`, `security.md`, `deploy.md`)
     * If file exists, append to existing file (e.g., use the same UX checklist)
   - Number items sequentially starting from CHK001
   - Group items by category/section ONLY using this controlled set:
       - Primary Flows
       - Alternate Flows
       - Exception / Error Flows
       - Recovery & Resilience
       - Non-Functional Domains (sub‑grouped or prefixed: Performance, Reliability, Security & Privacy, Accessibility, Observability, Scalability, Data Lifecycle)
       - Traceability & Coverage
       - Ambiguities & Conflicts
       - Assumptions & Dependencies
   - Do NOT invent ad-hoc categories; merge sparse categories (<2 items) into the closest higher-signal category.
   - Add traceability refs when possible (order: spec section, acceptance criterion). If no ID system exists, create an item: `Establish requirement & acceptance criteria ID scheme before proceeding`.
   - Optional brief rationale ONLY if it clarifies requirement intent or risk; never include implementation strategy, code pointers, or test plan details.
   - Each `/checklist` run creates a NEW file (never overwrites existing checklists)
   - **CRITICAL**: Focus on requirements & scenario coverage quality (NOT implementation). Enforce clarity, completeness, measurability, domain & cross-cutting obligations; surface ambiguities / assumptions / conflicts / dependencies. NEVER include implementation details (tests, code symbols, algorithms, deployment steps).
   - Soft cap: If raw candidate items > 40, prioritize by risk/impact, consolidate minor edge cases, and add one consolidation item: `Consolidate remaining low-impact scenarios (see source docs) after priority review`.
   - Minimum traceability coverage: ≥80% of items MUST include at least one traceability reference (spec section OR acceptance criterion). If impossible (missing structure), add corrective item: `Establish requirement & acceptance criteria ID scheme before proceeding` then proceed.

   **Scenario Modeling & Traceability (MANDATORY)**:
   - Classify scenarios into: Primary, Alternate, Exception/Error, Recovery/Resilience, Non-Functional (performance, reliability, security/privacy, accessibility, observability, scalability, data lifecycle) where applicable.
   - At least one item per present scenario class; if a class is intentionally absent add: `Confirm intentional absence of <Scenario Class> scenarios`.
   - Each item MUST include ≥1 of: scenario class tag, spec ref `[Spec §X.Y]`, acceptance criterion `[AC-##]`, or marker `(Assumption)/(Dependency)/(Ambiguity)/(Conflict)` (track coverage ratio for ≥80% traceability rule).
   - Surface & cluster (
     - Ambiguities (vague terms: "fast", "robust", "secure")
     - Conflicts (contradictory statements)
     - Assumptions (unvalidated premises)
     - Dependencies (external systems, feature flags, migrations, upstream APIs)
   ) — create one resolution item per cluster.
   - Include resilience/rollback coverage when state mutation or migrations occur (partial write, degraded mode, backward compatibility, rollback preconditions).
   - BANNED: references to specific tests ("unit test", "integration test"), code symbols, frameworks, algorithmic prescriptions, deployment steps. Rephrase any such user input into requirement clarity or coverage validation.
   - If a major scenario lacks acceptance criteria, add an item to define measurable criteria.

   **Context Curation (High-Signal Tokens Only)**:
   - Load only necessary portions of `spec.md`, `plan.md`, `tasks.md` relevant to active focus areas (avoid full-file dumping where sections are irrelevant).
   - Prefer summarizing long sections into concise scenario/requirement bullets before generating items (compaction principle).
   - If source docs are large, generate interim summary items (e.g., `Confirm summary of §4 data retention rules is complete`) instead of embedding raw text.
   - Use progressive disclosure: add follow-on retrieval only if a gap is detected (missing scenario class, unclear constraint).
   - Treat context budget as finite: do not restate already-tagged requirements verbatim across multiple items.
   - Merge near-duplicates when: same scenario class + same spec section + overlapping acceptance intent. Keep higher-risk phrasing; add note if consolidation occurred.
   - Do not repeat identical spec or acceptance refs in >3 items unless covering distinct scenario classes.
   - If >5 low-impact edge cases (minor parameter permutations), cluster into a single aggregated item.
   - If user arguments are sparse, prioritize clarifying questions over speculative item generation.

6. **Structure Reference**: Generate the checklist exactly following the canonical template in `templates/checklist-template.md`. Treat that file as the single source of truth for:
   - Title + meta section placement
   - Category headings
   - Checklist line formatting and ID sequencing
   - Prohibited content (implementation details)

   If (and only if) the canonical file is missing/unreadable, fall back to: H1 title, purpose/created meta lines, then one or more `##` category sections containing `- [ ] CHK### <imperative requirement-quality item>` lines with globally incrementing IDs starting at CHK001. No trailing explanatory footer.

7. **Report**: Output full path to created checklist, item count, and remind user that each run creates a new file. Summarize:
   - Focus areas selected
   - Depth level
   - Actor/timing
   - Any explicit user-specified must-have items incorporated

**Important**: Each `/checklist` command invocation creates a checklist file using short, descriptive names unless file already exists. This allows:

- Multiple checklists of different types (e.g., `ux.md`, `test.md`, `security.md`)
- Simple, memorable filenames that indicate checklist purpose
- Easy identification and navigation in the `checklists/` folder

To avoid clutter, use descriptive types and clean up obsolete checklists when done.

## Example Checklist Types

**Specification Review:** `spec-review.md`

- Requirement completeness and clarity
- User scenarios and edge cases coverage
- Acceptance criteria definition
- Domain-specific considerations

**Requirements Quality:** `requirements.md`

- Testable and measurable outcomes
- Stakeholder alignment verification
- Assumptions and constraints documentation
- Success metrics definition

**UX/Accessibility Scenarios:** `ux.md` or `a11y.md`

- User journey completeness
- Accessibility requirement coverage
- Responsive design considerations
- Internationalization needs

**Security Requirements:** `security.md`

- Threat model coverage
- Authentication/authorization requirements
- Data protection requirements
- Compliance and regulatory needs

**API/Integration Scenarios:** `api.md`

- Contract completeness
- Error handling scenarios
- Backward compatibility considerations
- Integration touchpoint coverage

Principle reminder: Checklist items validate requirements/scenario coverage quality—not implementation. If in doubt, transform any implementation phrasing into a requirement clarity or coverage validation item.
