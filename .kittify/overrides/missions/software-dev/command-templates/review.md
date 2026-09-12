---
description: Perform structured code review and kanban transitions for completed task prompt files
---

## Governance Bootstrap (required)

The prompt produced by `spec-kitty agent action review` already carries this
project's governance payload — Terminology Canon, Code Review Checklist,
Regression Vigilance, and any mission-declared action-critical sections. Trust
that prompt; the older bootstrap flow through a standalone `spec-kitty
constitution` subcommand has been retired. If you need to resolve context
ahead of claiming a WP for review, use:

```bash
spec-kitty agent context resolve --action review --mission <handle> --json
```

## Agent Profile Adoption and Incremental Context Loading (required)

After claiming a WP for review, adopt your assigned profile and load doctrine context
**incrementally** as the review demands it — not all at once.

### Phase 1: Profile Identity (load once, at review start)

Resolve the assigned profile and internalize its identity, boundaries, and directive scope.
Use the `/ad-hoc-profile-load` skill, or the sanctioned `DoctrineService` entry point below
— do NOT read YAML files directly and do NOT construct `AgentProfileRepository` or
`DoctrineService` yourself (five architectural gates ban that construction outside
`charter.activation.doctrine_service_builder`).

```python
from charter.activation.doctrine_service_builder import build_activation_aware_doctrine_service

service = build_activation_aware_doctrine_service(project_root)
profile = service.agent_profiles.get("<profile-id>")  # e.g. "reviewer-renata"

# Internalize identity
profile.initialization_declaration  # Your persona startup statement
profile.specialization.primary_focus  # What you actively do
profile.specialization.avoidance_boundary  # What you must NOT do
profile.collaboration.handoff_to  # Roles to defer to when out of scope

# Load only the directives this profile references
for ref in profile.directive_references:
    directive = service.directives.get(f"DIRECTIVE_{ref.code}")
```

### Phase 2: Incremental Tactical Context (load per review concern, discard when done)

As you review different aspects of the WP, load ONLY the doctrine artifacts relevant
to your current review concern, through the same `service` from Phase 1. Discard when
you move to a different concern.

**All doctrine artifacts MUST be loaded through `service` (the `DoctrineService`
returned by `build_activation_aware_doctrine_service`), never by reading YAML
files directly.**

| Review concern | What to load | How to load |
|----------------|-------------|-------------|
| Test quality | Test tactics, styleguides | `service.tactics.get("tdd-red-green-refactor")`, `service.tactics.get("acceptance-test-first")` |
| Code structure | Design tactics, styleguides | `service.styleguides.get("python-conventions")`, `service.tactics.get("change-apply-smallest-viable-diff")` |
| Architecture fit | Architecture tactics | `service.tactics.get("aggregate-boundary-design")`, `service.tactics.get("bounded-context-identification")` |
| Review checklist | Review tactics | `service.tactics.get("code-review-incremental")`, `service.tactics.get("atomic-design-review-checklist")` |

**Key rules:**
- Load tactical context **when you need it for a specific review concern**, not upfront
- Discard tactical context **when moving to the next concern** — stale context creates drift
- Profile-level context (identity, boundaries, directives) persists for the entire review
- Tactical context (tactics, procedures, styleguides) is scoped to the current concern

**IMPORTANT**: After running the command below, you'll see a LONG work package prompt (~1000+ lines).

**You MUST scroll to the BOTTOM** to see the completion commands!

Run this command to get the work package prompt and review instructions:

```bash
spec-kitty agent action review $ARGUMENTS --agent <your-name>
```

**CRITICAL**: You MUST provide agent identity (`--agent` or explicit flags) to track who is reviewing!

> **Explicit slash-command argument from the caller**: `$ARGUMENTS` above is forwarded directly from
> the slash-command invocation (e.g., `/spec-kitty.review WP03`).
> Pass it as-is; do not modify or strip it.
> Note: only explicit WP IDs are supported here — auto-detection is not available via slash commands.
> Do not interpret it as a prompt path or file reference; it is a WP selector only.
>
> **In repos with multiple missions, always pass `--mission <handle>` too.** The
> `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the
> ULID), or `mission_slug`. The resolver disambiguates by `mission_id` and returns a
> structured `MISSION_AMBIGUOUS_SELECTOR` error on ambiguity — there is no silent fallback.
>
> **Agent identity** (required — tracks WHO is reviewing the WP):
>
> **Compact form** (all-in-one via `--agent`):
> `--agent <tool>:<model>:<profile>:<role>` (e.g., `--agent claude:opus:reviewer-renata:reviewer`)
>
> **Explicit flags** (mutually exclusive with `--agent`):
> - `--tool <tool>`: Agent tool name (e.g., `claude`, `opencode`)
> - `--model <model>`: AI model identifier (e.g., `opus`, `gpt-4`)
> - `--profile <profile-id>`: Agent profile (e.g., `reviewer-renata`, `architect-alphonso`)
> - `--role <role>`: Agent role (e.g., `reviewer`, `implementer`)

If no WP ID is provided, it will automatically find the first work package with `lane: "for_review"` and move it to "doing" for you.

## Dependency checks (required)

- dependency_check: If the WP frontmatter lists `dependencies`, confirm each dependency WP is merged to main before you review this WP.
- dependent_check: Identify any WPs that list this WP as a dependency and note their current lanes.
- rebase_warning: If you request changes AND any dependents exist, warn those agents to rebase and provide a concrete command (example: `cd .worktrees/<mission-slug>-<mid8>-lane-<id> && git rebase <base-branch>`).
- verify_instruction: Confirm dependency declarations match actual code coupling (imports, shared modules, API contracts).

**After reviewing, scroll to the bottom and run ONE of these commands**:

- ✅ Approve: `spec-kitty agent tasks move-task WP## --to approved --mission <handle> --note "Review passed: <summary>"`
- ❌ Reject: Write feedback to the temp file path shown in the prompt, then run `spec-kitty agent tasks move-task WP## --to planned --mission <handle> --review-feedback-file <temp-file-path>`

**The prompt will provide a unique temp file path for feedback - use that exact path to avoid conflicts with other agents!**

**The Python script handles all file updates automatically - no manual editing required!**
