---
description: Create or update the research specification from a natural language research question.
---

# /spec-kitty.specify - Create Research Specification

**Version**: 0.11.0+

## 📍 WORKING DIRECTORY: Stay in planning repository

**IMPORTANT**: Specify works in the planning repository. NO worktrees are created.

```bash
# Run from project root:
cd /path/to/project/root  # Your planning repository

# All planning artifacts are created in the planning repo and committed:
# - kitty-specs/###-feature/spec.md → Created in planning repo
# - Committed to target branch (from create-feature JSON: target_branch/base_branch)
# - NO worktrees created
```

**Worktrees are created later** during `/spec-kitty.implement`, not during planning.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Branch Strategy Confirmation (MANDATORY)

Before discovery, resolve branch intent through the Python helper:

```bash
spec-kitty agent feature branch-context --json
```

If the user already named the intended landing branch, pass `--target-branch <branch>` and use that JSON as the branch contract. In your next reply, explicitly state `current_branch`, `planning_base_branch`, and `merge_target_branch`. If the branch contract does not match the user's intention, stop and resolve that before `create-feature`.

## Discovery Gate (mandatory)

Before running any scripts or writing to disk you **must** conduct a structured discovery interview.

### Research-Specific Discovery Questions

For research missions, focus on:

1. **Research Question**: What is the primary question you want to answer?
2. **Research Type**: Literature review, empirical study, case study, competitive analysis?
3. **Scope**: What's in scope and out of scope for this research?
4. **Deliverables**: What outputs do you expect? (Report, analysis, recommendations, data)
5. **Audience**: Who will consume this research? (Technical, business, academic)

### Scope Proportionality (CRITICAL)

- **Simple Research** (quick analysis, single-source review): Ask 2-3 questions, then proceed
- **Standard Research** (multi-source analysis, comparative study): Ask 3-5 questions
- **Complex Research** (systematic review, multi-method study): Full discovery with 5+ questions

### Discovery Requirements

1. Maintain a **Discovery Questions** table internally. Do **not** render to user.
2. When you have sufficient context, paraphrase into an **Intent Summary** and confirm.
3. If user explicitly asks to skip questions, acknowledge and proceed with minimal discovery.

## Research Deliverables Location (CRITICAL)

**IMPORTANT**: Research missions have TWO types of artifacts:

| Type | Location | Purpose |
|------|----------|---------|
| **Planning Artifacts** | `kitty-specs/###/research/` | Evidence/sources for PLANNING this sprint |
| **Research Deliverables** | `deliverables_path` | Actual research OUTPUT (your work product) |

### Determining deliverables_path

During discovery, you MUST ask:

> "Where should I store the research outputs (reports, analysis, findings)?
>
> Recommended: `docs/research/<feature-name>/`
>
> Other options:
> - `research-outputs/<feature-name>/`
> - `docs/<feature-name>/`
> - Custom path (must NOT be inside `kitty-specs/`)"

**Default**: If user doesn't specify, use `docs/research/<feature-slug>/`

**Validation Rules**:
- Must NOT be inside `kitty-specs/` (reserved for planning artifacts)
- Must NOT be just `research/` at root (ambiguous)
- Should include feature name/slug for clarity

## Workflow (0.11.0+)

**Planning happens in the planning repository - NO worktree created!**

1. Creates `kitty-specs/###-feature/spec.md` directly in planning repo
2. Creates `kitty-specs/###-feature/meta.json` with `deliverables_path`
3. Automatically commits to target branch
4. No worktree created during specify

**Worktrees created later**: Use `spec-kitty implement WP##` to create a workspace for each work package.

## Location

- Work in: **Planning repository** (not a worktree)
- Creates: `kitty-specs/###-feature/spec.md`
- Commits to: target branch (from `create-feature --json` → `target_branch`)

## Outline

### 0. Generate a Research Title

- Summarize the research question into a short, descriptive title (≤7 words)
- Use the confirmed title to derive the kebab-case feature slug

### 1. Discovery Phase

- Conduct discovery interview (scaled to complexity)
- Determine deliverables_path (ask user or use default)
- Confirm Intent Summary with user

### 2. Create Feature

When discovery is complete, run:

```bash
spec-kitty agent feature create-feature "<slug>" --json
```

Parse the JSON output for `feature`, `feature_dir`, `spec_file`, and `meta_file`.

### 3. Update existing meta.json with deliverables_path

`create-feature` already created `meta.json`. Read it first, then update only needed fields:

- `mission`: set to `"research"`
- `deliverables_path`: set to the confirmed path
- `friendly_name`: confirmed research title
- optional `source_description`

Preserve existing identity and timing fields (`feature_number`, `slug`, `created_at`, `target_branch`).
Do **not** recreate the file or regenerate timestamps via shell commands.

### 4. Load Research Spec Template

The spec template is bundled with spec-kitty and will be used automatically. The research mission uses a specialized template optimized for research projects.

### 5. Generate Research Specification

Fill in:
- **Research Question**: Primary and sub-questions
- **Methodology**: Approach, data sources, analysis framework
- **Scope**: What's included/excluded
- **Success Criteria**: How we know the research is complete

### 6. Write Specification

Update the existing `<feature_dir>/spec.md`

### 7. Validation

Validate spec against quality criteria:
- Research question is clear and answerable
- Methodology is appropriate for the question
- Deliverables are defined
- Success criteria are measurable

### 8. Report Completion

Report:
- Feature directory path
- Spec file path
- Deliverables path (from meta.json)
- Readiness for `/spec-kitty.plan`

## Research-Specific Guidelines

### Focus On

- **WHAT**: The research question and expected outcomes
- **WHY**: The purpose and value of this research
- **SCOPE**: Clear boundaries on what's in/out

### Avoid

- Implementation details (how data will be collected)
- Technology choices (which tools to use)
- Timeline commitments (handled in planning)

### Research Question Quality

Good research questions are:
- **Specific**: Focused on a particular topic
- **Answerable**: Can be investigated with available resources
- **Relevant**: Addresses a real need or gap
- **Bounded**: Has clear scope limits

### Success Criteria for Research

Research success criteria should be:
- **Completion-based**: "All identified sources reviewed"
- **Quality-based**: "Findings validated by domain expert"
- **Outcome-based**: "Recommendations are actionable"

NOT implementation-focused like:
- "Database populated with 1000 records"
- "Analysis script runs without errors"
