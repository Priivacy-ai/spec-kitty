---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with planning, verify you are in the correct working directory by running the shared pre-flight validation:

```python
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Planning Interrogation (mandatory)

Before executing any scripts or generating artifacts you must interrogate the specification and stakeholders.

- **Scope proportionality (CRITICAL)**: FIRST, assess the feature's complexity from the spec:
  - **Trivial/Test Features** (hello world, simple static pages, basic demos): Ask 1-2 questions maximum about tech stack preference, then proceed with sensible defaults
  - **Simple Features** (small components, minor API additions): Ask 2-3 questions about tech choices and constraints
  - **Complex Features** (new subsystems, multi-component features): Ask 3-5 questions covering architecture, NFRs, integrations
  - **Platform/Critical Features** (core infrastructure, security, payments): Full interrogation with 5+ questions

- **User signals to reduce questioning**: If the user says "use defaults", "just make it simple", "skip to implementation", "vanilla HTML/CSS/JS" - recognize these as signals to minimize planning questions and use standard approaches.

- **First response rule**:
  - For TRIVIAL features: Ask ONE tech stack question, then if answer is simple (e.g., "vanilla HTML"), proceed directly to plan generation
  - For other features: Ask a single architecture question and end with `WAITING_FOR_PLANNING_INPUT`

- If the user has not provided plan context, keep interrogating with one question at a time.

- **Conversational cadence**: After each reply, assess if you have SUFFICIENT context for this feature's scope. For trivial features, knowing the basic stack is enough. Only continue if critical unknowns remain.

Planning requirements (scale to complexity):

1. Maintain a **Planning Questions** table internally covering questions appropriate to the feature's complexity (1-2 for trivial, up to 5+ for platform-level). Track columns `#`, `Question`, `Why it matters`, and `Current insight`. Do **not** render this table to the user.
2. For trivial features, standard practices are acceptable (vanilla HTML, simple file structure, no build tools). Only probe if the user's request suggests otherwise.
3. When you have sufficient context for the scope, summarize into an **Engineering Alignment** note and confirm.
4. If user explicitly asks to skip questions or use defaults, acknowledge and proceed with best practices for that feature type.

## Outline

1. **Check planning discovery status**:
   - If any planning questions remain unanswered or the user has not confirmed the **Engineering Alignment** summary, stay in the one-question cadence, capture the user’s response, update your internal table, and end with `WAITING_FOR_PLANNING_INPUT`. Do **not** surface the table. Do **not** run `{SCRIPT}` yet.
   - Once every planning question has a concrete answer and the alignment summary is confirmed by the user, continue.

2. **Setup**: Run `{SCRIPT}` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH.

3. **Load context**: Read FEATURE_SPEC and `.kittify/memory/constitution.md` if it exists. If the constitution file is missing, skip Constitution Check and note that it is absent. Load IMPL_PLAN template (already copied).

4. **Execute plan workflow**: Follow the structure in IMPL_PLAN template, using the validated planning answers as ground truth:
   - Update Technical Context with explicit statements from the user or discovery research; mark `[NEEDS CLARIFICATION: …]` only when the user deliberately postpones a decision
   - If a constitution exists, fill Constitution Check section from it and challenge any conflicts directly with the user. If no constitution exists, mark the section as skipped.
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