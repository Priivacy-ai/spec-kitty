---
description: Create an implementation plan
---
# /spec-kitty.plan - Create Implementation Plan

**Version**: 0.11.0+

## 📍 WORKING DIRECTORY: Stay in the project root checkout

**IMPORTANT**: Plan works in the project root checkout. NO worktrees created.

```bash
# Run from project root (same directory as /spec-kitty.specify):
# You should already be here if you just ran /spec-kitty.specify

# Creates:
# - kitty-specs/<mission_slug>/plan.md → In project root checkout
#   (the NNN- prefix in the directory listing is display-only metadata)
# - Commits to target branch
# - NO worktrees created
```

**Do NOT cd anywhere**. Stay in the project root checkout root.

## Mission Handle Rule

`/spec-kitty.plan` operates on an existing mission, so use `--mission <handle>`
when the CLI needs a mission selector.

- `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of
  the ULID), or `mission_slug`.
- Prefer `mission_id` or `mid8` when the repo has multiple similarly named
  missions.
- The resolver disambiguates by `mission_id` and returns a structured
  `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Branch Strategy Confirmation (MANDATORY)

Before asking planning questions or generating artifacts, you must make the branch contract explicit.

- Never describe the landing branch vaguely. Always name the actual branch value.
- If the user says the feature should land somewhere else, stop and resolve that before writing `plan.md`.
- You must repeat the branch contract twice during this command:
  1. immediately after parsing `setup-plan --json`
  2. again in the final report before suggesting `/spec-kitty.tasks`

## Charter Context Bootstrap (required)

Before planning interrogation, load charter context for this action:

```bash
spec-kitty charter context --action plan --json
```

- If JSON `mode` is `bootstrap`, apply JSON `text` as first-run governance context and follow referenced docs as needed.
- If JSON `mode` is `compact`, continue with condensed governance context.

## Location Check (0.11.0+)

This command runs in the **project root checkout**, not in a worktree.

- Resolve branch context from deterministic JSON output, not from `meta.json` inspection:
  - Run `spec-kitty agent mission setup-plan --mission <mission-slug> --json`
  - Use `current_branch`, `target_branch` / `base_branch`, and `planning_base_branch` / `merge_target_branch` (plus uppercase aliases) from that payload
  - Use `branch_matches_target` from that payload to detect branch mismatch; do not probe branch state manually inside the prompt
- Planning artifacts live in `kitty-specs/<mission_slug>/` (the `NNN-` prefix is display-only metadata)
- The plan template is committed to the target branch after generation

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<mission>/tasks/`). Never refer to a folder by name alone.

## Agent Context Files (do not mutate)

This command does **not** update agent-specific context files.

- Do **not** search for or mutate `CLAUDE.md`, `AGENTS.md`, or similar
  agent-specific files as part of `/spec-kitty.plan`.
- Do **not** hunt for updater scripts or imaginary `spec-kitty agent context update`
  commands. No supported context-update command exists in this release.
- Planning outputs are the mission planning artifacts only:
  - `plan.md`
  - `research.md`
  - `data-model.md`
  - `contracts/`
  - `quickstart.md`
  - `occurrence_map.yaml` when bulk-edit planning applies

## Planning Interrogation (mandatory)

Before executing any scripts or generating artifacts you must interrogate the specification and stakeholders.

- **Scope proportionality (CRITICAL)**: FIRST, assess the feature's complexity from the spec:
  - **Trivial/Test Features** (hello world, simple static pages, basic demos): Ask 1-2 questions maximum about tech stack preference, then proceed with sensible defaults
  - **Simple Features** (small components, minor API additions): Ask 2-3 questions about tech choices and constraints
  - **Complex Features** (new subsystems, multi-component features): Ask 3-5 questions covering architecture, NFRs, integrations
  - **Platform/Critical Features** (core infrastructure, security, payments): Full interrogation with 5+ questions

- **Scenario-to-design handoff**: For non-trivial features, anchor planning
  questions in the concrete user flows from the spec rather than generic
  architecture preferences.

- **Domain rule follow-through**: When the spec implies approvals, lifecycle
  states, irreversible operations, or business-critical validations, ask 1-2
  targeted questions about invariants, transitions, atomicity, and externally
  visible events or integrations. Skip this for trivial features.

- **User signals to reduce questioning**: If the user says "use defaults", "just make it simple", "skip to implementation", "vanilla HTML/CSS/JS" - recognize these as signals to minimize planning questions and use standard approaches.

- **First response rule**:
  - For TRIVIAL features: Ask ONE tech stack question, then if answer is simple (e.g., "vanilla HTML"), proceed directly to plan generation
  - For other features: Ask a single architecture question tied to the riskiest scenario, rule, or lifecycle constraint and end with `WAITING_FOR_PLANNING_INPUT`

- If the user has not provided plan context, keep interrogating with one question at a time.

- **Conversational cadence**: After each reply, assess if you have SUFFICIENT context for this feature's scope. For trivial features, knowing the basic stack is enough. Only continue if critical unknowns remain.

Planning requirements (scale to complexity):

1. Maintain a **Planning Questions** table internally covering questions appropriate to the feature's complexity (1-2 for trivial, up to 5+ for platform-level). Track columns `#`, `Question`, `Why it matters`, and `Current insight`. Do **not** render this table to the user.
2. For trivial features, standard practices are acceptable (vanilla HTML, simple file structure, no build tools). Only probe if the user's request suggests otherwise.
3. When you have sufficient context for the scope, summarize into an **Engineering Alignment** note and confirm. Include invariant, state-transition, or event assumptions when they materially affect the design.
4. If user explicitly asks to skip questions or use defaults, acknowledge and proceed with best practices for that feature type.

## Bulk-Edit Check (if applicable)

If this mission is marked `change_mode: bulk_edit` in `meta.json` — or if the
spec describes renaming the same string (identifier, path, key, label, term)
across many files — load the `spec-kitty-bulk-edit-classification` skill and
follow it. You will produce `kitty-specs/<mission>/occurrence_map.yaml`
alongside the other planning artifacts. Every one of the 8 standard categories
(code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands,
user_facing_strings, tests_fixtures, logs_telemetry) must have an explicit
action. Without that artifact, the `implement` command will refuse to start
the first WP.

If the mission is not a bulk edit, skip this step.

## Outline

1. **Check planning discovery status**:
   - If any planning questions remain unanswered or the user has not confirmed the **Engineering Alignment** summary, stay in the one-question cadence, capture the user's response, update your internal table, and end with `WAITING_FOR_PLANNING_INPUT`. Do **not** surface the table. Do **not** run the setup command yet.
   - Once every planning question has a concrete answer and the alignment summary is confirmed by the user, continue.

2. **Resolve mission context deterministically** (CRITICAL - prevents wrong mission selection):
   - Prefer an explicit mission slug from user direction or from the current directory path (`kitty-specs/<mission-slug>/...`)
   - If you do not yet have an explicit mission slug, run `spec-kitty agent mission setup-plan --json` once without `--mission`
   - If that call succeeds, treat its JSON as the canonical setup payload and skip step 3
   - If that call returns an ambiguity error with `available_missions`, stop and resolve one explicit mission slug before continuing

3. **Setup**: If step 2 did not already return a successful setup payload, run `spec-kitty agent mission setup-plan --mission <mission-slug> --json` from the repository root and parse JSON for:
   - `result`: "success" or error message
   - `mission_slug`: Resolved feature slug
   - `spec_file`: Absolute path to resolved spec.md
   - `plan_file`: Absolute path to the created plan.md
   - `feature_dir`: Absolute path to the feature directory
   - `current_branch`: branch checked out when planning started
   - `target_branch` / `base_branch` (deterministic branch contract for downstream commands)
   - `planning_base_branch` / `merge_target_branch`: explicit aliases for planning and merge intent
   - `branch_strategy_summary`: canonical sentence describing the branch strategy

   Before proceeding, explicitly state to the user:
   - Current branch at plan start
   - Intended planning/base branch
   - Final merge target for completed changes
   - Whether `branch_matches_target` says the current branch matches that intended target

   **Example**:
   ```bash
   # Resolve the active mission handle, then pass it to setup-plan.
   # The --mission flag accepts mission_id (ULID), mid8 (first 8 chars), or mission_slug.
   # The resolver disambiguates by mission_id; ambiguous handles become structured errors.
   spec-kitty agent context resolve --mission <handle> --json
   spec-kitty agent mission setup-plan --mission <handle> --json
   ```

   **Error handling**: If the command fails with "Cannot detect mission", "Multiple missions found", or `MISSION_AMBIGUOUS_SELECTOR`, pass an unambiguous handle — the `mission_id` or its 8-char prefix `mid8` always disambiguates.

4. **Load context**: Read `spec_file` from setup-plan JSON output and `.kittify/charter/charter.md` if it exists. If the charter file is missing, skip Charter Check and note that it is absent. Load IMPL_PLAN template (already copied).

5. **Execute plan workflow**: Follow the structure in IMPL_PLAN template, using the validated planning answers as ground truth:
   - Update Technical Context with explicit statements from the user or discovery research; mark `[NEEDS CLARIFICATION: …]` only when the user deliberately postpones a decision
   - If a charter exists, fill Charter Check section from it and challenge any conflicts directly with the user. If no charter exists, mark the section as skipped.
   - Evaluate gates (ERROR if violations unjustified or questions remain unanswered)
   - Phase 0: Generate research.md (commission research to resolve every outstanding clarification, prioritizing unresolved domain rules, lifecycle questions, and event/integration behavior before generic tech comparisons)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md based on confirmed intent; when applicable, capture entities/value objects, invariants, state transitions, and externally visible events in the design artifacts
   - Re-evaluate Charter Check post-design, asking the user to resolve new gaps before proceeding

6. **STOP and report**: This command ends after Phase 1 planning. Report branch, IMPL_PLAN path, and generated artifacts.

   **⚠️ CRITICAL: DO NOT proceed to task generation!** The user must explicitly run `/spec-kitty.tasks` to generate work packages. Your job is COMPLETE after reporting the planning artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each unresolved rule, invariant, lifecycle edge, or event/integration ambiguity → domain research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each unresolved domain rule:
     Task: "Clarify invariant, state transition, or event behavior for {feature context}"
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
   - Invariants or atomicity boundaries if applicable
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - For each externally visible event, webhook, or integration callback → contract or payload shape when applicable
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

**Output**: data-model.md, /contracts/*, quickstart.md

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

**YOU MUST STOP HERE.**

Do NOT:
- ❌ Generate `tasks.md`
- ❌ Create work package (WP) files
- ❌ Create `tasks/` subdirectories
- ❌ Proceed to implementation

The user will run `/spec-kitty.tasks` when they are ready to generate work packages.

**Next suggested command**: `/spec-kitty.tasks` (user must invoke this explicitly)
