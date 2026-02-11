---
description: Capture a mid-implementation change request and create dependency-safe work packages.
---

# /spec-kitty.change - Mid-Stream Change Command

**Version**: 0.14.0+
**Purpose**: Capture review feedback or implementation pivots as branch-aware, dependency-safe work packages.

## When to Use

Use `/spec-kitty.change` when you need to:
- Capture review feedback as actionable work packages during implementation
- Handle implementation pivots ("use this library instead")
- Add late-stage requirements without disrupting ongoing work
- Create small fixes on `main` with complexity guidance

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

### Agent Subcommands

For programmatic use by AI agents:

```bash
# Step 1: Preview - validate and classify before writing files
spec-kitty agent change preview "your change request" --json

# Step 2: Apply - create work packages (with AI-assessed complexity scores)
spec-kitty agent change apply <request-id> \
  --request-text "your change request" \
  --scope-breadth <0-3> --coupling <0-2> --dependency-churn <0-2> \
  --ambiguity <0-2> --integration-risk <0-1> \
  --json

# Stack-first selection - get next doable WP with change priority
spec-kitty agent change next --json

# Reconcile - recompute links and merge coordination jobs
spec-kitty agent change reconcile --json
```

## Workflow

1. **Preview**: Validates the request, routes to correct branch stash, checks ambiguity
2. **Assess complexity**: The AI agent scores 5 factors based on request context
3. **Decide**: If total score >= 7 (high), recommends `/spec-kitty.specify` with continue-or-stop choice
4. **Apply**: Creates change work packages with dependencies, documentation links, and testing tasks
5. **Implement**: Change-stack items take priority in `/spec-kitty.implement` selection

## Branch Stash Routing

- **Feature branch**: Routes to feature stash (`kitty-specs/<feature>/tasks/`)
- **Main/primary branch**: Routes to embedded main stash (`kitty-specs/change-stack/main/`)
- Detection covers `main`, `master`, and other primary branch patterns

## Complexity Assessment

The AI agent assesses complexity across 5 dimensions and passes scores to the apply command:

| Factor | Range | Guidance |
|--------|-------|----------|
| Scope breadth | 0-3 | 0=single target, 1=2-3 targets, 2=multiple modules, 3=cross-cutting |
| Coupling | 0-2 | 0=isolated, 1=shared interfaces, 2=API contracts/schema changes |
| Dependency churn | 0-2 | 0=none, 1=add/update packages, 2=replace frameworks |
| Ambiguity | 0-2 | 0=clear, 1=hedging language, 2=vague goals |
| Integration risk | 0-1 | 0=localized, 1=CI/CD/deploy/infra |

**Thresholds** (total score):
- 0-3: simple (single change WP)
- 4-6: complex (adaptive packaging)
- 7-10: high (recommend `/spec-kitty.specify`, require `--continue`)

## Key Behaviors

- **Fail-fast**: Ambiguous requests are rejected before any files are created
- **Append-only**: Never rewrites existing WP bodies
- **Link-only for closed WPs**: References closed WPs without reopening them
- **Stack-first ordering**: Ready change WPs execute before normal backlog
- **Testing closure**: Every generated change WP includes a final testing task

## User Input

```text
$ARGUMENTS
```

## Examples

**Simple change on feature branch:**
```bash
spec-kitty agent change preview "replace manual JSON parsing with pydantic models" --json
spec-kitty agent change apply <request-id> \
  --request-text "replace manual JSON parsing with pydantic models" \
  --scope-breadth 1 --coupling 0 --dependency-churn 1 --ambiguity 0 --integration-risk 0 \
  --json
```

**Complex change with preview:**
```bash
spec-kitty agent change preview "restructure the entire auth flow" --json
# Agent assesses: scope=3, coupling=2, churn=1, ambiguity=0, risk=1 -> total=7 (HIGH)
# Recommends /spec-kitty.specify. If user confirms continue:
spec-kitty agent change apply <request-id> \
  --request-text "restructure the entire auth flow" \
  --scope-breadth 3 --coupling 2 --dependency-churn 1 --ambiguity 0 --integration-risk 1 \
  --continue --json
```
