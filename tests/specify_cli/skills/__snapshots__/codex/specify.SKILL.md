---
name: spec-kitty.specify
description: Create a mission specification
user-invocable: true
---
# /spec-kitty.specify - Create Mission Specification

**Version**: 0.11.0+

## 📍 WORKING DIRECTORY: Stay in the project root checkout

**IMPORTANT**: Specify works in the project root checkout. NO worktrees are created.

```bash
# Run from project root:
cd /path/to/project/root  # Your project root checkout

# All planning artifacts are created in the project root and committed:
# - kitty-specs/<mission_slug>/spec.md → Created in project root
#   (use the mission_slug returned by `mission create`; the numeric NNN- prefix
#    is display-only and is assigned at merge time)
# - Committed to target branch (from create JSON: target_branch/base_branch)
# - NO worktrees created
```

**Worktrees are created later** during `/spec-kitty.implement`, after task finalization computes execution lanes.

## Mission Handle Rule

Before `mission create`, there is no mission handle yet.

- Do **not** pass `--mission` to `spec-kitty agent mission branch-context`.
- Do **not** pass `--mission` to `spec-kitty agent mission create`.
- After `create` succeeds, use `--mission <handle>` for commands that operate on
  the created mission.
- `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of
  the ULID), or `mission_slug`.
- The resolver disambiguates by `mission_id` and returns a structured
  `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

You **MUST** consider this user input before proceeding (if not empty).
## Branch Strategy Confirmation (MANDATORY)

Before discovery, resolve branch intent through the Python helper, not by probing git directly:

```bash
spec-kitty agent mission branch-context --json
```

If the user already told you the intended landing branch, pass it explicitly:

```bash
spec-kitty agent mission branch-context --json --target-branch <intended-branch>
```

Parse the JSON and, in your next reply, explicitly tell the user:

- Current branch at workflow start: `current_branch`
- Default planning/base branch if you create the mission right now: `planning_base_branch`
- Final merge target for completed changes: `merge_target_branch`
- Whether `branch_matches_target` is true or false
- If that is not the intended landing branch, stop and ask which branch should receive this feature before you run `create`

Never talk generically about `main` or "the default branch". Name the actual branch values from the helper JSON. Do not shell out to git for this prompt.

## DO NOT

- Do not mix functional, non-functional, and constraint requirements in one list.
- Do not emit requirements without stable IDs (`FR-###`, `NFR-###`, `C-###`).
- Do not leave requirement status fields empty.
- Do not write non-functional requirements without measurable thresholds.
- Do not proceed to planning with unresolved requirement quality checklist failures.

## Charter Context Bootstrap (required)

Before discovery questions, load charter context for this action:

```bash
spec-kitty charter context --action specify --json
```

- If JSON `mode` is `bootstrap`, treat JSON `text` as the initial governance context and consult referenced docs as needed.
- If JSON `mode` is `compact`, proceed with concise governance context.
- If no charter exists yet, note that and continue. Missing charter is not a
  blocker for `/spec-kitty.specify`.

## Brief Context Detection (check before discovery)

Before starting discovery, check for a pre-existing mission brief:

```bash
ls .kittify/mission-brief.md 2>/dev/null && echo "MISSION_BRIEF_FOUND"
ls .kittify/ticket-context.md 2>/dev/null && echo "TICKET_CONTEXT_FOUND"
```

Check in priority order:
1. `.kittify/mission-brief.md` — general plan intake (written by `spec-kitty intake`)
2. `.kittify/ticket-context.md` — tracker ticket (written by `mission create --from-ticket`)

### If a brief file is found → Enter Brief-Intake Mode

**BRIEF DETECTED: `.kittify/<filename>` (source: `<source_file>`)**

1. **Read the full brief.** Do not skim.

2. **Summarise for the user.** Present a single paragraph: what the brief says the goal is, who it is for, and what the key constraints are. Example: "I found a plan document from Claude Code plan mode. Here's what I understand the goal to be: [summary]. I'll extract the spec from this brief rather than running a full discovery interview."

3. **Extract requirements directly.** Map the brief's content to `FR-###`, `NFR-###`, and `C-###` IDs. Do not ask questions the brief already answers. Specifically extract:
   - Objective → Functional Requirements
   - Constraints and non-goals → Non-Functional Requirements and Constraints
   - Acceptance criteria → FR status and Definition of Done markers
   - Risks and open questions → Assumptions or `[NEEDS CLARIFICATION]` markers (max 3)

4. **Ask gap-filling questions only.** Scale to brief quality:

   | Brief quality | Discovery questions |
   |---------------|---------------------|
   | Comprehensive (objective + constraints + approach + ACs) | 0–1 gap-filling questions |
   | Good (objective + constraints, no ACs) | 2–3 questions |
   | Partial (goal statement only) | 4–5 questions |
   | Empty / missing | Proceed to normal Discovery Gate below |

5. **Show the extracted requirement set.** Present the full FR/NFR/C table to the user: "I extracted X functional requirements and Y non-functional requirements. Does this look right?" Wait for one round of confirmation. The user may correct or supplement before you write the spec.

6. **Write spec.md normally.** Apply the same quality checklist and readiness gate as standard specify. Brief-intake mode does NOT lower the quality bar — spec.md must still pass all validation items.

7. **After spec.md is committed, delete all brief files** (each only if present):
   ```bash
   rm -f .kittify/mission-brief.md
   rm -f .kittify/brief-source.yaml
   rm -f .kittify/ticket-context.md
   rm -f .kittify/pending-origin.yaml
   ```

**What brief-intake mode does NOT do:**
- Does not copy brief prose verbatim into spec.md — it extracts and structures requirements
- Does not skip the quality checklist
- Does not skip the readiness gate
- Does not require the brief to be in any particular format — Markdown prose is fine

### If no brief file is found → Proceed with normal Discovery Gate

No change to current behaviour. Continue to the Discovery Gate section below.

## Discovery Gate (mandatory)

Before running any scripts or writing to disk you **must** conduct a structured discovery interview.

- **Scope proportionality (CRITICAL)**: FIRST, gauge the inherent complexity of the request:
  - **Trivial/Test Features** (hello world, simple pages, proof-of-concept): Ask 1-2 questions maximum, then proceed. Examples: "a simple hello world page", "tic-tac-toe game", "basic contact form"
  - **Simple Features** (small UI additions, minor enhancements): Ask 2-3 questions covering purpose and basic constraints
  - **Complex Features** (new subsystems, integrations): Ask 3-5 questions covering goals, users, constraints, risks
  - **Platform/Critical Features** (authentication, payments, infrastructure): Full discovery with 5+ questions

- **Scenario-first discovery**: For any non-trivial feature, prefer concrete
  workflow questions over abstract opinion prompts. Ask for the primary actor,
  trigger, happy-path outcome, and the most common exception or branch.

- **Terminology discipline**: If the request introduces business or domain
  terms that may drift, ask which term is canonical and which synonyms should
  be avoided. When relevant, carry those choices into the optional Domain
  Language section of the spec instead of leaving them implicit.

- **Rule probing**: For workflows with approvals, validations, state changes,
  or compliance implications, ask what must always be true and which
  transitions or checks cannot be skipped.

- **User signals to reduce questioning**: If the user says "just testing", "quick prototype", "skip to next phase", "stop asking questions" - recognize this as a signal to minimize discovery and proceed with reasonable defaults.

- **First response rule**:
  - For TRIVIAL features (hello world, simple test): Ask ONE clarifying question, then if the answer confirms it's simple, proceed directly to spec generation
  - For other features: Ask a single focused discovery question anchored in the primary user scenario and end with `WAITING_FOR_DISCOVERY_INPUT`

- If the user provides no initial description (empty command), stay in **Interactive Interview Mode**: keep probing with one question at a time.

- **Conversational cadence**: After each user reply, decide if you have ENOUGH context for this feature's complexity level. For trivial features, 1-2 questions is sufficient. Only continue asking if truly necessary for the scope.

Discovery requirements (scale to feature complexity):

1. Maintain a **Discovery Questions** table internally covering questions appropriate to the feature's complexity (1-2 for trivial, up to 5+ for complex). Track columns `#`, `Question`, `Why it matters`, and `Current insight`. Do **not** render this table to the user.
2. For trivial features, reasonable defaults are acceptable. Only probe if truly ambiguous.
3. When you have sufficient context for the feature's scope, paraphrase into an **Intent Summary** and confirm. For trivial features, this can be very brief. For non-trivial features, include the primary actor, trigger/success outcome, key constraint, and any explicit assumptions or deferred decisions.
4. Before leaving the interview loop, do a short playback of the primary scenario, the main exception or edge case, and any rule that must always hold.
5. If user explicitly asks to skip questions or says "just testing", acknowledge and proceed with minimal discovery.

## Bulk-Edit Detection (mandatory check)

Before finalizing the Intent Summary, ask yourself one question:

> Does fulfilling this request require changing the **same existing string**
> (identifier, path, key, label, or term) in more than one file?

Typical shapes: "rename X to Y", "the Blue feature is now the Red feature",
"change the terminology from X to Y", "move package A to package B", "replace
ACME with GlobalCorp everywhere in docs and UI".

**If yes or uncertain**: load the `spec-kitty-bulk-edit-classification` skill
and follow it. You will set `change_mode: bulk_edit` in `meta.json` after
`mission create` and produce an `occurrence_map.yaml` during plan. The user
does not need to know these field names — the skill teaches you the workflow.

**If clearly no** (a new feature with new identifiers, a bug fix that doesn't
rename anything, a refactor inside one file): proceed normally.

When in doubt, treat as bulk edit. The false-positive cost is drafting one map
the user approves in a pass; the false-negative cost is the silent cross-file
breakage that DIRECTIVE_035 exists to prevent.

## Mission Selection

After completing discovery and confirming the Intent Summary, determine the appropriate mission type for this mission run.

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

Store the final mission selection in your notes and include it in the spec output. Do not pass a `--mission-type` flag to mission creation unless the user explicitly overrides the default.

## Workflow (0.11.0+)

**Planning happens in the project root checkout - NO worktree created!**

1. Creates `kitty-specs/<mission_slug>/spec.md` directly in project root (the optional `NNN-` prefix is display-only metadata assigned at merge time)
2. Automatically commits to target branch
3. No worktree created during specify

**Worktrees created later**: After `/spec-kitty.tasks` finishes, run: `spec-kitty next --agent <agent> --mission <handle>`. The `--mission` handle can be the mission's `mission_id` (ULID), `mid8` (first 8 chars), or `mission_slug`; the resolver disambiguates by `mission_id` and returns a structured error on ambiguity (no silent fallback). Your agent will call `spec-kitty agent action implement WP## --agent <name>` for each WP. Each lane gets exactly one worktree, for example `.worktrees/<human-slug>-<mid8>-lane-a/` (e.g. `.worktrees/my-feature-01J6XW9K-lane-a/`).

## Location

- Work in: **Project root checkout** (not a worktree)
- Creates: `kitty-specs/<mission_slug>/spec.md` (the `NNN-` prefix is display-only and assigned at merge time)
- Commits to: target branch (from `create --json` → `target_branch`)

## Outline

### 0. Generate a Friendly Feature Title

- Summarize the agreed intent into a short, descriptive title (aim for ≤7 words; avoid filler like "feature" or "thing").
- Read that title back during the Intent Summary and revise it if the user requests changes.
- Use the confirmed title to derive the kebab-case feature slug for the create command.

The text the user typed after `/spec-kitty.specify` in the triggering message **is** the initial feature description. Capture it verbatim, but treat it only as a starting point for discovery—not the final truth. Your job is to interrogate the request, surface gaps, and co-create a complete specification with the user.

Given that feature description, do this:

- **Generation Mode (arguments provided)**: Use the provided text as a starting point, validate it through discovery, and fill gaps with explicit questions or clearly documented assumptions (limit `[NEEDS CLARIFICATION: …]` to at most three critical decisions the user has postponed).
- **Interactive Interview Mode (no arguments)**: Use the discovery interview to elicit all necessary context, synthesize the working feature description, and confirm it with the user before you generate any specification artifacts.

1. **Check discovery status**:
   - If this is your first message or discovery questions remain unanswered, stay in the one-question loop, capture the user's response, update your internal table, and end with `WAITING_FOR_DISCOVERY_INPUT`. Do **not** surface the table; keep it internal. Do **not** call the creation command yet.
   - Only proceed once every discovery question has an explicit answer and the user has acknowledged the Intent Summary.
   - Empty invocation rule: stay in interview mode until you can restate the agreed-upon feature description. Do **not** call the creation command while the description is missing or provisional.

2. When discovery is complete and the intent summary, **title**, and **mission type** are confirmed, run the mission creation command from repo root:

   ```bash
   spec-kitty agent mission create "<slug>" --json
   ```

   Where `<slug>` is a kebab-case version of the friendly title (e.g., "Checkout Upsell Flow" → "checkout-upsell-flow").

   The command returns JSON with:
   - `result`: "success" or error message
   - `mission_id`: Canonical ULID machine identity (e.g., `01J6XW9KQT7M0YB3N4R5CQZ2EX`). Immutable.
   - `mission_slug`: Human-readable mission slug (e.g., `checkout-upsell-flow`)
   - `mission_number`: **Display-only** numeric prefix, `null` pre-merge. Assigned at merge time. **Never** use this as a selector or identity.
   - `mission_type`: Mission type key (for example `software-dev`)
   - `slug`: Unnumbered mission slug (e.g., `checkout-upsell-flow`)
   - `feature_dir`: Absolute path to the feature directory inside the main repo
   - `current_branch`: the branch you started from
   - `target_branch` / `base_branch`: deterministic branch contract for downstream commands
   - `planning_base_branch` / `merge_target_branch`: explicit landing-branch aliases
   - `branch_strategy_summary`: human-readable summary of the branch contract

   Parse these values for use in subsequent steps. All file paths are absolute.

   **IMPORTANT**: You must only ever run this command once. The JSON is provided in the terminal output - always refer to it to get the actual paths you're looking for.
   Immediately restate the branch contract to the user after parsing the JSON:
   - Current branch at start
   - Intended planning/base branch
   - Final merge target for later changes
   - Whether that matches the user's intended landing branch
3. **Stay in the main repository**: No worktree is created during specify.

4. Read the files created by `create`:
   - `<feature_dir>/spec.md` (already created, may be empty/template-filled)
   - `<feature_dir>/meta.json` (already created with feature identity metadata)

   **Do NOT try to read a template file.** The spec structure is defined in this prompt (see sections below). The `create` command scaffolds an initial `spec.md` — read it, then update it following the structure in this prompt.

5. Update `<feature_dir>/meta.json` only when needed:
   - **Never** modify identity fields from `create` (`mission_id`, `slug`, `mission_slug`, `created_at`, `target_branch`). `mission_id` is the canonical ULID and is immutable. `mission_number` is display-only and is `null` pre-merge — do not set it by hand.
   - Keep `target_branch` aligned to the value from `create --json` output. Never hardcode `main`.
   - Ensure `friendly_name` matches the confirmed title.
   - Ensure `mission_type` is correct.
   - Optionally add/update `source_description`.
   - Ensure `vcs` exists (`"git"` default).

   Example `meta.json` schema (identity fields that must be present explicitly):
   ```json
   {
     "mission_id": "01J6XW9KQT7M0YB3N4R5CQZ2EX",
     "mission_number": null,
     "slug": "my-feature",
     "mission_slug": "my-feature",
     "friendly_name": "My Mission",
     "mission_type": "software-dev",
     "target_branch": "main",
     "vcs": "git",
     "created_at": "2026-01-01T00:00:00+00:00"
   }
   ```

   `mission_number` becomes a concrete integer only at merge time, assigned as
   `max(existing_numbers)+1` inside the merge-state lock. Selectors disambiguate
   by `mission_id` (or its 8-char prefix `mid8`), never by `mission_number`.

   **Do not regenerate timestamps or directory paths via shell commands.**

6. Generate the specification content by following this flow:
    - Use the discovery answers as your authoritative source of truth (do **not** rely on the raw invocation text)
    - For empty invocations, treat the synthesized interview summary as the canonical feature description
    - Identify: actors, actions, data, constraints, motivations, success metrics
    - Prefer concrete scenario walkthrough facts (actor, trigger, success outcome, exception path) over abstract restatements
    - For any remaining ambiguity:
      - Ask the user a focused follow-up question immediately and halt work until they answer
      - Only use `[NEEDS CLARIFICATION: …]` when the user explicitly defers the decision
      - Record any interim assumption in the Assumptions section
      - Prioritize clarifications by impact: scope > outcomes > risks/security > user experience > technical details
    - Fill User Scenarios & Testing section (ERROR if no clear user flow can be determined)
    - If terminology precision matters, fill the optional Domain Language section with canonical terms and ambiguous synonyms to avoid
    - Generate separated requirement tables: Functional (`FR-###`), Non-Functional (`NFR-###`), and Constraints (`C-###`)
    - Ensure each requirement entry has a status value and testable wording
    - Capture rules or invariants that shape acceptance scenarios, edge cases, permissions, or lifecycle boundaries
    - Define Success Criteria (measurable, technology-agnostic outcomes)
    - Identify Key Entities (if data involved)

7. Update the existing `<feature_dir>/spec.md` using the template structure, replacing placeholders with concrete details derived from the feature description while preserving section order and headings.

8. **Specification Quality Validation**: After writing the initial spec, validate it against quality criteria:

   a. **Create Spec Quality Checklist**: Generate a checklist file at `feature_dir/checklists/requirements.md` using the checklist template structure with these validation items:

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
      - [ ] Requirement types are separated (Functional / Non-Functional / Constraints)
      - [ ] IDs are unique across FR-###, NFR-###, and C-### entries
      - [ ] All requirement rows include a non-empty Status value
      - [ ] Non-functional requirements include measurable thresholds
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

      - Items marked incomplete require spec updates before `/spec-kitty.plan`
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

9. Report completion with feature directory, spec file path, checklist results, and readiness for the next phase (`/spec-kitty.plan`).

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
