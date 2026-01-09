---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with planning, verify you are in the correct working directory:

**What to validate**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- You're in the feature worktree directory or main repo

**Note**: The CLI commands will automatically detect your feature context.

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Planning Interrogation (mandatory)

Before executing any scripts or generating artifacts you must interrogate the specification and stakeholders.

- **Scope proportionality (CRITICAL)**: FIRST, assess the feature's complexity from the spec:
  - **Trivial/Test Features** (hello world, simple static pages, basic demos): Ask 1-2 questions maximum about tech stack preference, then proceed with sensible defaults
  - **Simple Features** (small components, minor API additions): Ask 2-3 questions about tech choices and constraints
  - **Complex Features** (new subsystems, multi-component features): Ask 3-5 questions covering architecture, NFRs, integrations
  - **Platform/Critical Features** (core infrastructure, security, payments): Full interrogation with 5+ questions

- **User signals to reduce questioning**: If the user says "use defaults", "just make it simple", "skip to implementation", "vanilla HTML/CSS/JS" - recognize these as signals to minimize planning questions and use standard approaches.

- **Batch Q&A approach**:
  - Determine the appropriate number of questions based on feature complexity (1-2 for trivial, 2-3 for simple, 3-5 for complex, 5+ for critical)
  - Present ALL planning questions together in a numbered list format
  - For TRIVIAL features: If tech stack is already clear, skip questions entirely and use reasonable defaults
  - For other features: Present all planning questions at once and end with `WAITING_FOR_PLANNING_INPUT`

- If the user has not provided plan context, present the full set of planning questions in one batch.

- **Question presentation format**:
  ```
  I have [N] planning questions:
  
  Q1: [First question]
  Q2: [Second question]
  Q3: [Third question]
  ...
  
  Please answer all questions (you can respond with Q1: answer, Q2: answer, etc.)
  ```

Planning requirements (scale to complexity):

1. Maintain a **Planning Questions** table internally covering questions appropriate to the feature's complexity (1-2 for trivial, up to 5+ for platform-level). Track columns `#`, `Question`, `Why it matters`, and `Current insight`. Do **not** render this table to the user.
2. For trivial features, standard practices are acceptable (vanilla HTML, simple file structure, no build tools). Only probe if the user's request suggests otherwise.
3. Present all questions in a single batch rather than one at a time. Wait for user to answer all questions before proceeding.
4. After receiving all answers, summarize into an **Engineering Alignment** note and confirm.
5. If user explicitly asks to skip questions or use defaults, acknowledge and proceed with best practices for that feature type.

## Outline

1. **Check planning discovery status**:
   - If this is your first message and the user provided context, assess the complexity level
   - For TRIVIAL features with clear tech stack: Skip questions entirely and proceed with reasonable defaults
   - For all other cases: Generate and present ALL planning questions at once in a numbered batch format
   - Stay in question mode, capture the user's responses to all questions, update your internal table, and end with `WAITING_FOR_PLANNING_INPUT`. Do **not** surface the table. Do **not** run the setup command yet.
   - Once ALL planning questions have been answered and the alignment summary is confirmed by the user, continue.

2. **Setup**: Run `spec-kitty agent feature setup-plan --json` from the worktree root and parse JSON for:
   - `result`: "success" or error message
   - `plan_file`: Absolute path to the created plan.md
   - `feature_dir`: Absolute path to the feature directory

3. **Load context**: 
   - Read the spec file at `<feature_dir>/spec.md`
   - Read `.kittify/memory/constitution.md` for constitution compliance
   - Load the plan template (already copied to `plan_file` by the setup command)

4. **Execute plan workflow**: Follow the structure in the plan template (loaded from `plan_file`), using the validated planning answers as ground truth:
   - Update Technical Context with explicit statements from the user or discovery research; mark `[NEEDS CLARIFICATION: …]` only when the user deliberately postpones a decision
   - Fill Constitution Check section from constitution and challenge any conflicts directly with the user
   - Evaluate gates (ERROR if violations unjustified or questions remain unanswered)
   - Phase 0: Generate research.md (commission research to resolve every outstanding clarification)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md based on confirmed intent
   - Phase 1: Update agent context by running `spec-kitty agent context update --json`
   - Re-evaluate Constitution Check post-design, asking the user to resolve new gaps before proceeding

5. **STOP and report**: This command ends after Phase 1 planning. Report:
   - Current feature branch name
   - Path to `plan_file` (the plan.md)
   - Generated artifacts (research.md, data-model.md, contracts/, etc.)

   **⚠️ CRITICAL: DO NOT proceed to task generation!** The user must explicitly run `/spec-kitty.tasks` to generate work packages. Your job is COMPLETE after reporting the planning artifacts.

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
   - Run `spec-kitty agent context update --json` (or specify agent with `--agent-type <name>`)
   - The command automatically detects the current agent in use
   - Updates the appropriate agent-specific context file (CLAUDE.md, GEMINI.md, etc.)
   - Adds only new technology from current plan
   - Preserves manual additions between `<!-- MANUAL ADDITIONS -->` markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications

---

## ⛔ MANDATORY STOP POINT

**This command is COMPLETE after generating planning artifacts.**

After reporting:
- `plan.md` path
- `research.md` path (if generated)
- `data-model.md` path (if generated)
- `contracts/` contents (if generated)
- Agent context file updated

**YOU MUST STOP HERE.**

Do NOT:
- ❌ Generate `tasks.md`
- ❌ Create work package (WP) files
- ❌ Create `tasks/` subdirectories
- ❌ Proceed to implementation

The user will run `/spec-kitty.tasks` when they are ready to generate work packages.

**Next suggested command**: `/spec-kitty.tasks` (user must invoke this explicitly)
