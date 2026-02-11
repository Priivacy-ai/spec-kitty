---
description: Capture a mid-implementation change request and create dependency-safe work packages.
---

# /spec-kitty.change - Mid-Stream Change Command

**Version**: 0.14.0+
**Purpose**: Capture review feedback or implementation pivots as branch-aware, dependency-safe work packages.

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<feature>/tasks/`). Never refer to a folder by name alone.

## Working Directory and Routing

- Run from the project root (planning repository).
- This workflow does not create worktrees.
- Change requests are routed automatically:
  - Feature scope -> `kitty-specs/<feature>/tasks/`
  - Primary branch scope -> `kitty-specs/change-stack/main/`

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Command Surface

### Top-Level Command

```bash
# Direct request
spec-kitty change "use SQLAlchemy instead of raw SQL"

# Preview without creating WPs
spec-kitty change "refactor auth module" --preview

# JSON output for automation
spec-kitty change "add caching layer" --json output.json
```

### Agent Commands (recommended for deterministic flow)

```bash
# Step 1: Preview - validate and classify before writing files
spec-kitty agent change preview "$ARGUMENTS" --json

# Step 2: Apply - create WPs from validated request (with AI-assessed scores)
# --request-text is REQUIRED
# Complexity scores are REQUIRED (assessed by you, the agent)
spec-kitty agent change apply <request-id> \
  --request-text "$ARGUMENTS" \
  --scope-breadth <0-3> \
  --coupling <0-2> \
  --dependency-churn <0-2> \
  --ambiguity <0-2> \
  --integration-risk <0-1> \
  --json

# Stack-first selection - get next doable WP with change priority
spec-kitty agent change next --json

# Reconcile - recompute links and dependency consistency
spec-kitty agent change reconcile --json
```

## Required Execution Flow

1. **Preview and classify first**:
   - Run `spec-kitty agent change preview "$ARGUMENTS" --json`.
   - Parse and retain: `requestId`, `stashScope`, `stashPath`, `validationState`, `requiresClarification`.

2. **Resolve ambiguity before apply**:
   - If `requiresClarification=true` or `validationState` is ambiguous, ask focused clarifying questions.
   - Re-run preview until the request is unambiguous.
   - Do not apply while ambiguity remains.

3. **Assess complexity (YOU do this)**:
   Before calling apply, YOU must assess the change request across 5 dimensions.
   Read the feature's spec.md, plan.md, and existing tasks to understand the scope,
   then score each factor:

   | Factor | Range | Guidance |
   |--------|-------|----------|
   | `--scope-breadth` | 0-3 | 0=single file/function, 1=2-3 targets, 2=multiple modules, 3=cross-cutting/architectural |
   | `--coupling` | 0-2 | 0=isolated, 1=shared interfaces/imports, 2=API contracts/schema/breaking changes |
   | `--dependency-churn` | 0-2 | 0=no dep changes, 1=add/update packages, 2=replace frameworks/major versions |
   | `--ambiguity` | 0-2 | 0=clear and specific, 1=hedging language, 2=vague/broad qualitative goals |
   | `--integration-risk` | 0-1 | 0=localized, 1=touches CI/CD/deploy/infra/auth/external APIs |

   **Thresholds** (computed from total score):
   - 0-3: **simple** -> single change WP
   - 4-6: **complex** -> adaptive packaging (orchestration or targeted multi-WP)
   - 7-10: **high** -> recommend `/spec-kitty.specify`, require explicit `--continue`

4. **Apply with full arguments**:
   - Run:
     ```bash
     spec-kitty agent change apply <request-id> \
       --request-text "$ARGUMENTS" \
       --scope-breadth <N> --coupling <N> --dependency-churn <N> \
       --ambiguity <N> --integration-risk <N> \
       [--continue] --json
     ```
   - If total score >= 7 (high), you MUST recommend `/spec-kitty.specify` first.
     Only add `--continue` when the user explicitly agrees to proceed.
   - Parse and retain: `createdWorkPackages`, `writtenFiles`, `closedReferenceLinks`, `mergeCoordinationJobs`, `consistency`, `rejectedEdges`, `mode`.

5. **Reconcile after apply**:
   - Run `spec-kitty agent change reconcile --feature <feature-slug> --json`.
   - Confirm:
     - `dependencyValidationPassed=true`
     - `issues=[]` (or explicitly reported and actionable)
   - If reconciliation reports issues, stop and report blockers.

6. **Quality-normalize every generated WP** (mandatory):
   - Review every file in `writtenFiles` and ensure each new WP is implementation-ready.
   - Apply the same quality bar used by `/spec-kitty.plan` and `/spec-kitty.tasks`:
     - Clear objective and scope tied to the change request.
     - Dependency-aware implementation command (`spec-kitty implement WP##` or `spec-kitty implement WP## --base WP##`).
     - Concrete implementation guidance (components/files, constraints, edge cases).
     - Explicit acceptance constraints and review expectations.
     - Final testing closure (regression + new change coverage).
     - Frontmatter correctness (`lane: "planned"`, `dependencies`, change metadata, history entry).
   - If generated content is too shallow, enrich the WP prompt before hand-off.
   - Keep all WPs in flat `tasks/` (never lane subdirectories).

7. **Report and hand-off**:
   - Report:
     - `requestId`
     - stash scope/path
     - complexity assessment (your scores and the resulting classification)
     - created WP IDs and prompt paths
     - dependency and reconciliation status
     - merge coordination jobs (if any)
   - Suggest next commands:
     - `spec-kitty agent change next --json`
     - `spec-kitty agent workflow implement <WP##> --agent <your-agent-name>`

## Work Package Quality Standard (same as /plan and /tasks)

When a change request creates new WPs, apply these standards before considering the output complete:

- **Context grounding first**:
  - Read `kitty-specs/<feature>/spec.md`, `kitty-specs/<feature>/plan.md`, and `kitty-specs/<feature>/tasks.md`.
  - Ensure each new change WP is consistent with existing architecture and sequencing.

- **Sizing and depth**:
  - Target the same practical density used by `/spec-kitty.tasks`: focused, implementable guidance rather than vague summaries.
  - For manually expanded or split change WPs, use the same sizing logic:
    - target 3-7 subtasks (or equivalent guidance depth)
    - hard max ~10 subtasks / ~700 lines before splitting

- **Dependency correctness**:
  - Dependencies in frontmatter must match both `tasks.md` intent and implementation base requirements.
  - Closed WPs must remain link-only references, never reopened.

- **Review readiness**:
  - A reviewer should be able to validate completion using only the WP prompt, supporting artifacts, and code changes.
  - Include clear done conditions and testing expectations.

## Fail-Fast Rules

- Do not apply ambiguous requests.
- Do not bypass complexity warnings silently.
- Do not write outside the resolved change stash.
- Do not create lane-based subdirectories under `tasks/`.
- Do not treat generated WPs as final if they fail the quality standard above.

## Examples

**Simple change on feature branch:**
```bash
spec-kitty agent change preview "replace manual JSON parsing with pydantic models" --json
spec-kitty agent change apply <request-id> \
  --request-text "replace manual JSON parsing with pydantic models" \
  --scope-breadth 1 --coupling 0 --dependency-churn 1 --ambiguity 0 --integration-risk 0 \
  --json
spec-kitty agent change reconcile --json
```

**Complex change requiring explicit continue:**
```bash
spec-kitty agent change preview "restructure the entire auth flow and replace session model" --json
# Total score: scope=3 + coupling=2 + churn=2 + ambiguity=1 + risk=1 = 9 (HIGH)
# Recommend /spec-kitty.specify. If user says continue:
spec-kitty agent change apply <request-id> \
  --request-text "restructure the entire auth flow and replace session model" \
  --scope-breadth 3 --coupling 2 --dependency-churn 2 --ambiguity 1 --integration-risk 1 \
  --continue --json
```
