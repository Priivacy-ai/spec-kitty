---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
scripts:
  sh: scripts/bash/setup-plan.sh --json
  ps: scripts/powershell/setup-plan.ps1 -Json
agent_scripts:
  sh: scripts/bash/update-agent-context.sh __AGENT__
  ps: scripts/powershell/update-agent-context.ps1 -AgentType __AGENT__
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Planning Interrogation (mandatory)

Before executing any scripts or generating artifacts you must interrogate the specification and stakeholders.

- **First response rule**: On your very first reply after `/speckitty.plan`, ask a single architecture-focused question (e.g., “What baseline technical stack are you assuming?”) and end the message with `WAITING_FOR_PLANNING_INPUT`. Do nothing else yet.
- If the user has not provided plan context, keep interrogating with one question at a time to surface architecture, constraints, and risks before running any automation.

- **Conversational cadence**: After each user reply, decide which planning dimension is still unclear. Ask exactly one follow-up question referencing that dimension (e.g., “Great. For integrations…”) and end with `WAITING_FOR_PLANNING_INPUT`. Do not bundle questions or progress while unknowns remain.
- **Scope proportionality**: Calibrate planning depth to the feature’s complexity and risk profile. Lightweight enhancements may only need a brief checklist, whereas platform-level builds demand exhaustive architectural and operational interrogation before committing to a plan.

Planning requirements you must still satisfy:

1. Maintain a **Planning Questions** table internally with at least five targeted questions covering: architectural drivers, non-functional requirements, integration points, deployment/operational constraints, data and compliance considerations, risks/unknowns. Track columns `#`, `Question`, `Why it matters`, and `Current insight` (prefill `—` when unknown). Do **not** render this table to the user; it is solely for your internal coverage tracking.
2. Inspect prior conversation for explicit answers. Treat hand-wavy phrases ("we want it scalable") as unanswered until quantified.
3. Continue the ask → wait → update loop until every row has a concrete answer. Never show the internal table in the conversation; summarize progress conversationally. End with `WAITING_FOR_PLANNING_INPUT` if additional confirmation is needed.
4. After you have concrete answers for every question, summarise them into an **Engineering Alignment** note and confirm with the user before moving on.
5. Continue to pause and seek clarification whenever new uncertainties surface during later phases.

## Outline

1. **Check planning discovery status**:
   - If any planning questions remain unanswered or the user has not confirmed the **Engineering Alignment** summary, stay in the one-question cadence, capture the user’s response, update your internal table, and end with `WAITING_FOR_PLANNING_INPUT`. Do **not** surface the table. Do **not** run `{SCRIPT}` yet.
   - Once every planning question has a concrete answer and the alignment summary is confirmed by the user, continue.

2. **Setup**: Run `{SCRIPT}` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH.

3. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

4. **Execute plan workflow**: Follow the structure in IMPL_PLAN template, using the validated planning answers as ground truth:
   - Update Technical Context with explicit statements from the user or discovery research; mark `[NEEDS CLARIFICATION: …]` only when the user deliberately postpones a decision
   - Fill Constitution Check section from constitution and challenge any conflicts directly with the user
   - Evaluate gates (ERROR if violations unjustified or questions remain unanswered)
   - Phase 0: Generate research.md (commission research to resolve every outstanding clarification)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md based on confirmed intent
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design, asking the user to resolve new gaps before proceeding

5. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
   - Run `{AGENT_SCRIPT}`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
