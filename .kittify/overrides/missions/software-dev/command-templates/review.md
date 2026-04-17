---
description: Perform structured code review and kanban transitions for completed task prompt files
---

## Constitution Context Bootstrap (required)

Before running workflow review, load constitution context for this action:

```bash
spec-kitty constitution context --action review --json
```

Use JSON `text` as governance context. On first load (`mode=bootstrap`), follow referenced docs as needed.

## Agent Profile Adoption and Incremental Context Loading (required)

After claiming a WP for review, adopt your assigned profile and load doctrine context
**incrementally** as the review demands it — not all at once.

### Phase 1: Profile Identity (load once, at review start)

Resolve the assigned profile and internalize its identity, boundaries, and directive scope.
Use the Python API — do NOT read YAML files directly.

```python
from doctrine.agent_profiles import AgentProfileRepository

repo = AgentProfileRepository(project_dir=project_agents_dir)
profile = repo.get("<profile-id>")  # e.g. "reviewer"

# Internalize identity
profile.initialization_declaration  # Your persona startup statement
profile.specialization.primary_focus  # What you actively do
profile.specialization.avoidance_boundary  # What you must NOT do
profile.collaboration.handoff_to  # Roles to defer to when out of scope

# Load only the directives this profile references
from doctrine.service import DoctrineService

service = DoctrineService(shipped_root, project_root)
for ref in profile.directive_references:
    directive = service.directives.get(f"DIRECTIVE_{ref.code}")
```

### Phase 2: Incremental Tactical Context (load per review concern, discard when done)

As you review different aspects of the WP, load ONLY the doctrine artifacts relevant
to your current review concern. Discard when you move to a different concern.

**All doctrine artifacts MUST be loaded through the Python API (repository classes),
never by reading YAML files directly.**

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
spec-kitty agent workflow review $ARGUMENTS --agent <your-name>
```

**CRITICAL**: You MUST provide agent identity (`--agent` or explicit flags) to track who is reviewing!

> **Explicit slash-command argument from the caller**: `$ARGUMENTS` above is forwarded directly from
> the slash-command invocation (e.g., `/spec-kitty.review WP03`).
> Pass it as-is; do not modify or strip it.
> Note: only explicit WP IDs are supported here — auto-detection is not available via slash commands.
> Do not interpret it as a prompt path or file reference; it is a WP selector only.
>
> **Agent identity** (required — tracks WHO is reviewing the WP):
>
> **Compact form** (all-in-one via `--agent`):
> `--agent <tool>:<model>:<profile>:<role>` (e.g., `--agent claude:opus:reviewer:reviewer`)
>
> **Explicit flags** (mutually exclusive with `--agent`):
> - `--tool <tool>`: Agent tool name (e.g., `claude`, `opencode`)
> - `--model <model>`: AI model identifier (e.g., `opus`, `gpt-4`)
> - `--profile <profile-id>`: Agent profile (e.g., `reviewer`, `architect`)
> - `--role <role>`: Agent role (e.g., `reviewer`, `implementer`)

If no WP ID is provided, it will automatically find the first work package with `lane: "for_review"` and move it to "doing" for you.

## Dependency checks (required)

- dependency_check: If the WP frontmatter lists `dependencies`, confirm each dependency WP is merged to main before you review this WP.
- dependent_check: Identify any WPs that list this WP as a dependency and note their current lanes.
- rebase_warning: If you request changes AND any dependents exist, warn those agents to rebase and provide a concrete command (example: `cd .worktrees/FEATURE-WP02 && git rebase FEATURE-WP01`).
- verify_instruction: Confirm dependency declarations match actual code coupling (imports, shared modules, API contracts).

**After reviewing, scroll to the bottom and run ONE of these commands**:

- ✅ Approve: `spec-kitty agent tasks move-task WP## --to done --note "Review passed: <summary>"`
- ❌ Reject: Write feedback to the temp file path shown in the prompt, then run `spec-kitty agent tasks move-task WP## --to planned --review-feedback-file <temp-file-path>`

**The prompt will provide a unique temp file path for feedback - use that exact path to avoid conflicts with other agents!**

**The Python script handles all file updates automatically - no manual editing required!**
