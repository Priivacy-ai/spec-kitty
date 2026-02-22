---
description: Create or update the feature specification from a natural language feature description.
---

# /spec-kitty.specify - Create Feature Specification

**Version**: 0.11.0+

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: Specify works in the planning repository. NO worktrees are created.

```bash
# Run from project root:
cd /path/to/project/root  # Your planning repository

# All planning artifacts are created in the planning repo and committed:
# - kitty-specs/###-feature/spec.md → Created in planning repo
# - Committed to target branch (meta.json → target_branch)
# - NO worktrees created
```

**Worktrees are created later** during `/spec-kitty.implement`, not during planning.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Constitution Context Bootstrap (required)

Before discovery questions, load constitution context for this action:

```bash
spec-kitty constitution context --action specify --json
```

- If JSON `mode` is `bootstrap`, treat JSON `text` as the initial governance context and consult referenced docs as needed.
- If JSON `mode` is `compact`, proceed with concise governance context.

## Discovery Gate (mandatory)

Before running any scripts or writing to disk you **must** conduct a structured discovery interview.

- **Scope proportionality (CRITICAL)**: FIRST, gauge the inherent complexity of the request:
  - **Trivial/Test Features** (hello world, simple pages, proof-of-concept): Ask 1-2 questions maximum, then proceed. Examples: "a simple hello world page", "tic-tac-toe game", "basic contact form"
  - **Simple Features** (small UI additions, minor enhancements): Ask 2-3 questions covering purpose and basic constraints
  - **Complex Features** (new subsystems, integrations): Ask 3-5 questions covering goals, users, constraints, risks
  - **Platform/Critical Features** (authentication, payments, infrastructure): Full discovery with 5+ questions

- **User signals to reduce questioning**: If the user says "just testing", "quick prototype", "skip to next phase", "stop asking questions" - recognize this as a signal to minimize discovery and proceed with reasonable defaults.

- **First response rule**:
  - For TRIVIAL features (hello world, simple test): Ask ONE clarifying question, then if the answer confirms it's simple, proceed directly to spec generation
  - For other features: Ask a single focused discovery question and end with `WAITING_FOR_DISCOVERY_INPUT`

- If the user provides no initial description (empty command), stay in **Interactive Interview Mode**: keep probing with one question at a time.

- **Conversational cadence**: After each user reply, decide if you have ENOUGH context for this feature's complexity level. For trivial features, 1-2 questions is sufficient. Only continue asking if truly necessary for the scope.

Discovery requirements (scale to feature complexity):

1. Maintain a **Discovery Questions** table internally covering questions appropriate to the feature's complexity (1-2 for trivial, up to 5+ for complex). Track columns `#`, `Question`, `Why it matters`, and `Current insight`. Do **not** render this table to the user.
2. For trivial features, reasonable defaults are acceptable. Only probe if truly ambiguous.
3. When you have sufficient context for the feature's scope, paraphrase into an **Intent Summary** and confirm. For trivial features, this can be very brief.
4. If user explicitly asks to skip questions or says "just testing", acknowledge and proceed with minimal discovery.

## Mission Selection

After completing discovery and confirming the Intent Summary, determine the appropriate mission for this feature.

### Available Missions

- **software-dev**: For building software features, APIs, CLI tools, applications
  - Phases: research → design → implement → test → review
  - Best for: code changes, new features, bug fixes, refactoring

- **research**: For investigations, literature reviews, technical analysis
  - Phases: question → methodology → gather → analyze → synthesize → publish
  - Best for: feasibility studies, market research, technology evaluation

### Mission Inference

1. **Analyze the feature description** to identify the primary goal:
   - Building, coding, implementing, creating software → **software-dev**
   - Researching, investigating, analyzing, evaluating → **research**

2. **Check for explicit mission requests** in the user's description:
   - If user mentions "research project", "investigation", "analysis" → use research
   - If user mentions "build", "implement", "create feature" → use software-dev

3. **Confirm with user** (unless explicit):
   > "Based on your description, this sounds like a **[software-dev/research]** project.
   > I'll use the **[mission name]** mission. Does that work for you?"

4. **Handle user response**:
   - If confirmed: proceed with selected mission
   - If user wants different mission: use their choice

5. **Handle --mission flag**: If the user provides `--mission <key>` in their command, skip inference and use the specified mission directly.

Store the final mission selection in your notes and include it in the spec output. Do not pass a `--mission` flag to feature creation.

## Workflow (0.11.0+)

**Planning happens in the planning repository - NO worktree created!**

1. Creates `kitty-specs/###-feature/spec.md` directly in planning repo
2. Automatically commits to target branch
3. No worktree created during specify

**Worktrees created later**: Use `spec-kitty implement WP##` to create a workspace for each work package. Worktrees are created later during implement (e.g., `.worktrees/###-feature-WP##`).

## Location

- Work in: **Planning repository** (not a worktree)
- Creates: `kitty-specs/###-feature/spec.md`
- Commits to: target branch (`meta.json` → `target_branch`)

## Outline

### 0. Generate a Friendly Feature Title

- Summarize the agreed intent into a short, descriptive title (aim for ≤7 words; avoid filler like "feature" or "thing").
- Read that title back during the Intent Summary and revise it if the user requests changes.
- Use the confirmed title to derive the kebab-case feature slug for the create-feature command.

The text the user typed after `/spec-kitty.specify` in the triggering message **is** the initial feature description. Capture it verbatim, but treat it only as a starting point for discovery—not the final truth. Your job is to interrogate the request, surface gaps, and co-create a complete specification with the user.

Given that feature description, do this:

- **Generation Mode (arguments provided)**: Use the provided text as a starting point, validate it through discovery, and fill gaps with explicit questions or clearly documented assumptions (limit `[NEEDS CLARIFICATION: …]` to at most three critical decisions the user has postponed).
- **Interactive Interview Mode (no arguments)**: Use the discovery interview to elicit all necessary context, synthesize the working feature description, and confirm it with the user before you generate any specification artifacts.

1. **Check discovery status**:
   - If this is your first message or discovery questions remain unanswered, stay in the one-question loop, capture the user's response, update your internal table, and end with `WAITING_FOR_DISCOVERY_INPUT`. Do **not** surface the table; keep it internal. Do **not** call the creation command yet.
   - Only proceed once every discovery question has an explicit answer and the user has acknowledged the Intent Summary.
   - Empty invocation rule: stay in interview mode until you can restate the agreed-upon feature description. Do **not** call the creation command while the description is missing or provisional.

2. When discovery is complete and the intent summary, **title**, and **mission** are confirmed, run the feature creation command from repo root:

   ```bash
   spec-kitty agent feature create-feature "<slug>" --json
   ```

   Where `<slug>` is a kebab-case version of the friendly title (e.g., "Checkout Upsell Flow" → "checkout-upsell-flow").

   The command returns JSON with:
   - `result`: "success" or error message
   - `feature`: Feature number and slug (e.g., "014-checkout-upsell-flow")
   - `feature_dir`: Absolute path to the feature directory inside the main repo

   Parse these values for use in subsequent steps. All file paths are absolute.

   **IMPORTANT**: You must only ever run this command once. The JSON is provided in the terminal output - always refer to it to get the actual paths you're looking for.
3. **Stay in the main repository**: No worktree is created during specify.

4. The spec template is bundled in this project at `.kittify/missions/software-dev/templates/spec-template.md`. The template defines required sections for software development features.

5. Create meta.json in the feature directory with:
   ```json
   {
     "feature_number": "<number>",
     "slug": "<full-slug>",
     "friendly_name": "<Friendly Title>",
     "mission": "<selected-mission>",
     "source_description": "$ARGUMENTS",
     "created_at": "<ISO timestamp>",
     "target_branch": "main",
     "vcs": "git"
   }
   ```

   **CRITICAL**: Always set these fields explicitly:
   - `target_branch`: Set to "main" by default (user can change to "2.x" for dual-branch features)
   - `vcs`: Set to "git" by default (enables VCS locking and prevents jj fallback)

6. Generate the specification content by following this flow:
    - Use the discovery answers as your authoritative source of truth (do **not** rely on raw `$ARGUMENTS`)
    - For empty invocations, treat the synthesized interview summary as the canonical feature description
    - Identify: actors, actions, data, constraints, motivations, success metrics
    - For any remaining ambiguity:
      * Ask the user a focused follow-up question immediately and halt work until they answer
      * Only use `[NEEDS CLARIFICATION: …]` when the user explicitly defers the decision
      * Record any interim assumption in the Assumptions section
      * Prioritize clarifications by impact: scope > outcomes > risks/security > user experience > technical details
    - Fill User Scenarios & Testing section (ERROR if no clear user flow can be determined)
    - Generate Functional Requirements (each requirement must be testable)
    - Define Success Criteria (measurable, technology-agnostic outcomes)
    - Identify Key Entities (if data involved)

7. Write the specification to `<feature_dir>/spec.md` using the template structure, replacing placeholders with concrete details derived from the feature description while preserving section order and headings.

8. **Specification Quality Validation**: After writing the initial spec, validate it against quality criteria:

   a. **Create Spec Quality Checklist**: Generate a checklist file at `FEATURE_DIR/checklists/requirements.md` using the checklist template structure with these validation items:
   
      ```markdown
      # Specification Quality Checklist: [FEATURE NAME]
      
      **Purpose**: Validate specification completeness and quality before proceeding to planning
      **Created**: [DATE]
      **Feature**: [Link to spec.md]
      
      ## Content Quality
      
      - [ ] No implementation details (languages, frameworks, APIs)
      - [ ] Focused on user value and business needs
      - [ ] Written for non-technical stakeholders
      - [ ] All mandatory sections completed
      
      ## Requirement Completeness
      
      - [ ] No [NEEDS CLARIFICATION] markers remain
      - [ ] Requirements are testable and unambiguous
      - [ ] Success criteria are measurable
      - [ ] Success criteria are technology-agnostic (no implementation details)
      - [ ] All acceptance scenarios are defined
      - [ ] Edge cases are identified
      - [ ] Scope is clearly bounded
      - [ ] Dependencies and assumptions identified
      
      ## Feature Readiness
      
      - [ ] All functional requirements have clear acceptance criteria
      - [ ] User scenarios cover primary flows
      - [ ] Feature meets measurable outcomes defined in Success Criteria
      - [ ] No implementation details leak into specification
      
      ## Notes
      
      - Items marked incomplete require spec updates before `/spec-kitty.clarify` or `/spec-kitty.plan`
      ```
   
   b. **Run Validation Check**: Review the spec against each checklist item:
      - For each item, determine if it passes or fails
      - Document specific issues found (quote relevant spec sections)
   
   c. **Handle Validation Results**:
      
      - **If all items pass**: Mark checklist complete and proceed to step 6
      
      - **If items fail (excluding [NEEDS CLARIFICATION])**:
        1. List the failing items and specific issues
        2. Update the spec to address each issue
        3. Re-run validation until all items pass (max 3 iterations)
        4. If still failing after 3 iterations, document remaining issues in checklist notes and warn user
      
      - **If [NEEDS CLARIFICATION] markers remain**:
        1. Extract all [NEEDS CLARIFICATION: ...] markers from the spec
        2. Re-confirm with the user whether each outstanding decision truly needs to stay unresolved. Do not assume away critical gaps.
        3. For each clarification the user has explicitly deferred, present options using plain text—no tables:
        
           ```
           Question [N]: [Topic]
           Context: [Quote relevant spec section]
           Need: [Specific question from NEEDS CLARIFICATION marker]
           Options: (A) [First answer — implications] · (B) [Second answer — implications] · (C) [Third answer — implications] · (D) Custom (describe your own answer)
           Reply with a letter or a custom answer.
           ```
        
        4. Number questions sequentially (Q1, Q2, Q3 - max 3 total)
        5. Present all questions together before waiting for responses
        6. Wait for user to respond with their choices for all questions (e.g., "Q1: A, Q2: Custom - [details], Q3: B")
        7. Update the spec by replacing each [NEEDS CLARIFICATION] marker with the user's selected or provided answer
        9. Re-run validation after all clarifications are resolved
   
   d. **Update Checklist**: After each validation iteration, update the checklist file with current pass/fail status

9. Report completion with feature directory, spec file path, checklist results, and readiness for the next phase (`/spec-kitty.clarify` or `/spec-kitty.plan`).

**NOTE:** The script creates and checks out the new branch and initializes the spec file before writing.

## General Guidelines

## Quick Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement (no tech stack, APIs, code structure).
- Written for business stakeholders, not developers.
- DO NOT create any checklists that are embedded in the spec. That will be a separate command.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation

When creating this spec from a user prompt:

1. **Make informed guesses**: Use context, industry standards, and common patterns to fill gaps
2. **Document assumptions**: Record reasonable defaults in the Assumptions section
3. **Limit clarifications**: Maximum 3 [NEEDS CLARIFICATION] markers - use only for critical decisions that:
   - Significantly impact feature scope or user experience
   - Have multiple reasonable interpretations with different implications
   - Lack any reasonable default
4. **Prioritize clarifications**: scope > security/privacy > user experience > technical details
5. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
6. **Common areas needing clarification** (only if no reasonable default exists):
   - Feature scope and boundaries (include/exclude specific use cases)
   - User types and permissions (if multiple conflicting interpretations possible)
   - Security/compliance requirements (when legally/financially significant)
   
**Examples of reasonable defaults** (don't ask about these):

- Data retention: Industry-standard practices for the domain
- Performance targets: Standard web/mobile app expectations unless specified
- Error handling: User-friendly messages with appropriate fallbacks
- Authentication method: Standard session-based or OAuth2 for web apps
- Integration patterns: RESTful APIs unless specified otherwise

### Success Criteria Guidelines

Success criteria must be:

1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No mention of frameworks, languages, databases, or tools
3. **User-focused**: Describe outcomes from user/business perspective, not system internals
4. **Verifiable**: Can be tested/validated without knowing implementation details

**Good examples**:

- "Users can complete checkout in under 3 minutes"
- "System supports 10,000 concurrent users"
- "95% of searches return results in under 1 second"
- "Task completion rate improves by 40%"

**Bad examples** (implementation-focused):

- "API response time is under 200ms" (too technical, use "Users see results instantly")
- "Database can handle 1000 TPS" (implementation detail, use user-facing metric)
- "React components render efficiently" (framework-specific)
- "Redis cache hit rate above 80%" (technology-specific)
