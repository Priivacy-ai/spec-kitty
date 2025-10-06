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
   
   **Context Loading Strategy**:
   - Load only necessary portions relevant to active focus areas (avoid full-file dumping)
   - Prefer summarizing long sections into concise scenario/requirement bullets
   - Use progressive disclosure: add follow-on retrieval only if gaps detected
   - If source docs are large, generate interim summary items instead of embedding raw text

5. **Generate checklist**:
   - Create `FEATURE_DIR/checklists/` directory if it doesn't exist
   - Generate unique checklist filename:
     - Use short, descriptive name based on checklist type
     - Format: `[type].md` (e.g., `ux.md`, `test.md`, `security.md`, `deploy.md`)
     - If file exists, append to existing file (e.g., use the same UX checklist)
   - Number items sequentially starting from CHK001
   - Each `/checklist` run creates a NEW file (never overwrites existing checklists)

   **Category Structure** - Group items ONLY using this controlled set:
   - Primary Flows
   - Alternate Flows
   - Exception / Error Flows
   - Recovery & Resilience
   - Non-Functional Domains (sub‑grouped or prefixed: Performance, Reliability, Security & Privacy, Accessibility, Observability, Scalability, Data Lifecycle)
   - Traceability & Coverage
   - Ambiguities & Conflicts
   - Assumptions & Dependencies
   
   Do NOT invent ad-hoc categories; merge sparse categories (<2 items) into the closest higher-signal category.

   **Scenario Classification & Coverage**:
   - Classify scenarios into: Primary, Alternate, Exception/Error, Recovery/Resilience, Non-Functional
   - At least one item per present scenario class; if intentionally absent add: `Confirm intentional absence of <Scenario Class> scenarios`
   - Include resilience/rollback coverage when state mutation or migrations occur (partial write, degraded mode, backward compatibility, rollback preconditions)
   - If a major scenario lacks acceptance criteria, add an item to define measurable criteria

   **Traceability Requirements**:
   - MINIMUM: ≥80% of items MUST include at least one traceability reference
   - Each item should include ≥1 of: scenario class tag, spec ref `[Spec §X.Y]`, acceptance criterion `[AC-##]`, or marker `(Assumption)/(Dependency)/(Ambiguity)/(Conflict)`
   - If no ID system exists, create an item: `Establish requirement & acceptance criteria ID scheme before proceeding`

   **Surface & Resolve Issues**:
   - Cluster and create one resolution item per cluster for:
     - Ambiguities (vague terms: "fast", "robust", "secure")
     - Conflicts (contradictory statements)
     - Assumptions (unvalidated premises)
     - Dependencies (external systems, feature flags, migrations, upstream APIs)

   **Content Consolidation**:
   - Soft cap: If raw candidate items > 40, prioritize by risk/impact and add: `Consolidate remaining low-impact scenarios (see source docs) after priority review`
   - Merge near-duplicates when: same scenario class + same spec section + overlapping acceptance intent
   - If >5 low-impact edge cases, cluster into a single aggregated item
   - Do not repeat identical spec or acceptance refs in >3 items unless covering distinct scenario classes
   - Treat context budget as finite: do not restate already-tagged requirements verbatim across multiple items

   **🚫 PROHIBITED CONTENT** (Requirements Focus ONLY):
   - Focus on requirements & scenario coverage quality, NOT implementation
   - NEVER include: specific tests ("unit test", "integration test"), code symbols, frameworks, algorithmic prescriptions, deployment steps, test plan details, implementation strategy
   - Rephrase any such user input into requirement clarity or coverage validation
   - Optional brief rationale ONLY if it clarifies requirement intent or risk

6. **Structure Reference**: Generate the checklist following the canonical template in `templates/checklist-template.md` for title, meta section, category headings, and ID formatting. If template is unavailable, use: H1 title, purpose/created meta lines, `##` category sections containing `- [ ] CHK### <requirement item>` lines with globally incrementing IDs starting at CHK001.

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
