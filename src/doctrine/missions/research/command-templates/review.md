---
description: Perform structured research review with citation validation.
---

## Research Review Overview

Research WPs produce deliverables in a **worktree**, which merge to main like code.

### Two Types of Artifacts

| Type | Location | Review Focus |
|------|----------|--------------|
| **Research Deliverables** | `{{deliverables_path}}` (in worktree) | PRIMARY - Your main review target |
| **Planning Artifacts** | `kitty-specs/{{feature_slug}}/research/` (in main) | SECONDARY - Citation validation only |

### Review Checklist

- [ ] Research deliverables exist in `{{deliverables_path}}/`
- [ ] Findings address the WP objectives
- [ ] Citations/sources are properly documented
- [ ] Deliverables are committed to worktree branch
- [ ] Quality meets research standards

---

## Understanding Research Dependencies

**For research missions, `dependencies: []` is often NORMAL.**

Research phases typically work like this:
- **Investigation phase**: WPs run in parallel, no inter-dependencies
- **Synthesis phase**: WPs depend on investigation WPs
- **Final/Validation phase**: Depends on synthesis

Empty dependencies means this WP CAN start immediately - it's **not an error**.

**To see dependency relationships:**
```bash
spec-kitty agent tasks list-dependents WP##

# Output shows both:
#   Depends on: (upstream - what blocks this WP)
#   Depended on by: (downstream - what this WP blocks)
```

**Why this matters for review:**
- If a WP has dependents and you request changes, those downstream WPs may need updates
- The review workflow will warn you about incomplete dependents

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check (CRITICAL for AI Agents)

Before proceeding with review, verify you are in the correct working directory by running the shared pre-flight validation:

```python
```

**What this validates**:
- Current branch follows the feature pattern like `001-feature-name`
- You're not attempting to run from `main` or any release branch
- The validator prints clear navigation instructions if you're outside the feature worktree

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Citation Validation (Research Mission Specific)

Before reviewing research tasks, validate all citations and sources:

```python
from pathlib import Path
from specify_cli.validators.research import validate_citations, validate_source_register

# Validate evidence log
evidence_log = FEATURE_DIR / "research" / "evidence-log.csv"
if evidence_log.exists():
    result = validate_citations(evidence_log)
    if result.has_errors:
        print(result.format_report())
        print("\nERROR: Citation validation failed. Fix errors before proceeding.")
        exit(1)
    elif result.warning_count > 0:
        print(result.format_report())
        print("\nWarnings found - consider addressing for better citation quality.")

# Validate source register
source_register = FEATURE_DIR / "research" / "source-register.csv"
if source_register.exists():
    result = validate_source_register(source_register)
    if result.has_errors:
        print(result.format_report())
        print("\nERROR: Source register validation failed.")
        exit(1)
```

**Validation Requirements**:
- All sources must be documented with unique `source_id` entries.
- Citations must be present in both CSVs (format warnings are advisory).
- Confidence levels should be filled for evidence entries.
- Research review cannot proceed if validation reports blocking errors.

## Outline

1. Run `{SCRIPT}` from repo root; capture `FEATURE_DIR`, `AVAILABLE_DOCS`, and `tasks.md` path.

2. Determine the review target:
   - If user input specifies a filename, validate it exists under `tasks/` (flat structure, check `lane: "for_review"` in frontmatter).
   - Otherwise, select the oldest file in `tasks/` (lexical order is sufficient because filenames retain task ordering).
   - Abort with instructional message if no files are waiting for review.

3. Load context for the selected task:
   - Read the prompt file frontmatter (lane MUST be `for_review`); note `task_id`, `phase`, `agent`, `shell_pid`.
   - Read the body sections (Objective, Context, Implementation Guidance, etc.).
   - Consult supporting documents as referenced: constitution, plan, spec, data-model, research, quickstart, code changes.
   - Review the associated code in the repository (diffs, tests, docs) to validate the implementation.

4. Conduct the review:
   - Verify implementation against the prompt’s Definition of Done and Review Guidance.
   - Run required tests or commands; capture results.
   - Document findings explicitly: bugs, regressions, missing tests, risks, or validation notes.

5. Decide outcome:
  - **Needs changes**:
     * Append a new entry in the prompt’s **Activity Log** detailing feedback (include timestamp, reviewer agent, shell PID).
     * Update frontmatter `lane` back to `planned`, clear `assignee` if necessary, keep history entry.
     * Add/revise a `## Review Feedback` section (create if missing) summarizing action items.
     * Run `spec-kitty agent tasks move-task <FEATURE> <TASK_ID> planned --note "Returned for changes"` (use the PowerShell equivalent on Windows) so the move and history update are staged consistently.
  - **Approved**:
     * Append Activity Log entry capturing approval details (capture shell PID via `echo $$` or helper script).
     * Update frontmatter: set `lane=done`, set reviewer metadata (`agent`, `shell_pid`), optional `assignee` for approver.
     * Use helper script to mark the task complete in `tasks.md` (see Step 6).
     * Run `spec-kitty agent tasks move-task <FEATURE> <TASK_ID> done --note "Approved for release"` (PowerShell variant available) to transition the prompt into `tasks/`.

6. Update `tasks.md` automatically:
   - Run `spec-kitty agent tasks mark-status --task-id <TASK_ID> --status done` (POSIX) or `spec-kitty agent tasks mark-status --task-id <TASK_ID> --status done` (PowerShell) from repo root.
   - Confirm the task entry now shows `[X]` and includes a reference to the prompt file in its notes.

7. Produce a review report summarizing:
   - Task ID and filename reviewed.
  - Approval status and key findings.
   - Tests executed and their results.
   - Follow-up actions (if any) for other team members.
   - Reminder to push changes or notify teammates as per project conventions.

Context for review: {ARGS}

All review feedback must live inside the prompt file, ensuring future implementers understand historical decisions before revisiting the task.

## Citation Validation (Research Mission Specific)

Before reviewing research tasks, validate all citations and sources:

```python
from pathlib import Path
from specify_cli.validators.research import validate_citations, validate_source_register

# Validate evidence log
evidence_log = FEATURE_DIR / "research" / "evidence-log.csv"
if evidence_log.exists():
    result = validate_citations(evidence_log)
    if result.has_errors:
        print(result.format_report())
        print("\nERROR: Citation validation failed. Fix errors before proceeding.")
        exit(1)
    elif result.warning_count > 0:
        print(result.format_report())
        print("\nWarnings found - consider addressing for better citation quality.")

# Validate source register
source_register = FEATURE_DIR / "research" / "source-register.csv"
if source_register.exists():
    result = validate_source_register(source_register)
    if result.has_errors:
        print(result.format_report())
        print("\nERROR: Source register validation failed.")
        exit(1)
```

**Validation Requirements**:
- All sources must be documented with unique `source_id` entries.
- Citations must be present in both CSVs (format warnings are advisory).
- Confidence levels should be filled for evidence entries.
- Research review cannot proceed if validation reports blocking errors.