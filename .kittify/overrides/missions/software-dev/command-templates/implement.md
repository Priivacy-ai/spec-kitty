---
description: Create an isolated workspace (worktree) for implementing a specific work package.
---

## Constitution Context Bootstrap (required)

Before running workflow implement, load constitution context for this action:

```bash
spec-kitty constitution context --action implement --json
```

Use JSON `text` as governance context. On first load (`mode=bootstrap`), follow referenced docs as needed.

## Agent Profile Adoption and Incremental Context Loading (required)

After claiming a WP, the workflow implement command outputs an **Agent Identity** section
derived from the WP's `agent_profile` frontmatter field. You MUST adopt this profile and
load doctrine context **incrementally** as the work demands it — not all at once.

### Phase 1: Profile Identity (load once, at WP start)

Resolve the assigned profile and internalize its identity, boundaries, and directive scope.
Use the Python API — do NOT read YAML files directly.

```python
from doctrine.agent_profiles import AgentProfileRepository

repo = AgentProfileRepository(project_dir=project_agents_dir)
profile = repo.get("<profile-id>")  # e.g. "python-implementer"

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
    # Apply this directive's constraints to your behavior
```

### Phase 2: Incremental Tactical Context (load per-subtask, discard when done)

As you work through subtasks, load ONLY the doctrine artifacts relevant to your
current activity. When you move to a different activity, discard the previous
tactical context and load the new one. This keeps your context focused and avoids
overloading with irrelevant guidance.

**All doctrine artifacts MUST be loaded through the Python API (repository classes),
never by reading YAML files directly.**

| Activity | What to load | How to load | When to discard |
|----------|-------------|-------------|-----------------|
| Writing tests | Test tactics, styleguides, procedures | `service.tactics.get("tdd-red-green-refactor")`, `service.tactics.get("acceptance-test-first")`, `service.styleguides.get("python-conventions")` | When tests pass and you move to production code |
| Implementing production code | Coding styleguides, relevant design tactics | `service.styleguides.get("python-conventions")`, `service.tactics.get("change-apply-smallest-viable-diff")` | When implementation is complete |
| Refactoring | Refactoring procedure and refactoring tactics | `service.procedures.get("refactoring")`, `service.tactics.get("<specific-refactoring>")` | When refactoring is complete |
| Bug fixing | Test-first bug fix procedure | `service.procedures.get("test-first-bug-fixing")` | When the fix is verified |

**Example flow for a Python implementer working a subtask:**

1. Subtask says "write tests for the new validator" →
   Load: `service.tactics.get("tdd-red-green-refactor")`, `service.styleguides.get("python-conventions")`
2. Tests written and failing for the right reason →
   Discard test tactics. Load: `service.tactics.get("change-apply-smallest-viable-diff")`
3. Implementation done, reviewer feedback says "extract helper" →
   Discard implementation tactics. Load: `service.procedures.get("refactoring")`

**Key rules:**
- Load tactical context **when you need it**, not upfront
- Discard tactical context **when the activity changes** — stale context creates drift
- Profile-level context (identity, boundaries, directives) persists for the entire WP
- Tactical context (tactics, procedures, styleguides) is scoped to the current activity

## ⚠️ CRITICAL: Working Directory Requirement

**After running `spec-kitty implement WP##`, you MUST:**

1. **Run the cd command shown in the output** - e.g., `cd .worktrees/###-mission-WP##/`
2. **ALL file operations happen in this directory** - Read, Write, Edit tools must target files in the workspace
3. **NEVER write deliverable files to the main repository** - This is a critical workflow error

**Why this matters:**

- Each WP has an isolated worktree with its own branch
- Changes in main repository will NOT be seen by reviewers looking at the WP worktree
- Writing to main instead of the workspace causes review failures and merge conflicts

## Deterministic Pre-Read Checks (required)

Before any `Read`/`Edit`/`Write` action, run these checks from your shell:

```bash
pwd
ls -la
test -f kitty-specs/<mission>/tasks/<wp-file>.md && echo "wp prompt exists"
```

If a file/path is uncertain, verify first with `ls` or `test -f` before reading it.

---

**IMPORTANT**: After running the command below, you'll see a LONG work package prompt (~1000+ lines).

**You MUST scroll to the BOTTOM** to see the completion command!

Run this command to get the work package prompt and implementation instructions:

```bash
spec-kitty agent workflow implement $ARGUMENTS --agent <your-name>
```

<details><summary>PowerShell equivalent</summary>

```powershell
spec-kitty agent workflow implement $ARGUMENTS --agent <your-name>
```

</details>

> **Explicit slash-command argument from the caller**: `$ARGUMENTS` above is forwarded directly from
> the slash-command invocation (e.g., `/spec-kitty.implement WP03 --base WP01`).
> Pass it as-is to `spec-kitty agent workflow implement`; do not modify or strip it.
>
> **Agent identity** (required — tracks WHO is working on the WP):
>
> You can provide your identity in two ways:
>
> **Compact form** (all-in-one via `--agent`):
> ```
> --agent <tool>:<model>:<profile>:<role>
> ```
> Example: `--agent opencode:gpt-4:python-implementer:implementer`
>
> Partial compact strings are allowed (missing fields default to `unknown`):
> - `--agent claude` → tool=claude, model/profile/role=unknown
> - `--agent claude:opus` → tool=claude, model=opus, profile/role=unknown
>
> **Explicit flags** (mutually exclusive with `--agent`):
> - `--tool <tool>`: Agent tool name (e.g., `claude`, `opencode`)
> - `--model <model>`: AI model identifier (e.g., `opus`, `gpt-4`)
> - `--profile <profile-id>`: Agent profile (e.g., `python-implementer`, `implementer`)
> - `--role <role>`: Agent role (e.g., `implementer`, `reviewer`)
>
> Example: `spec-kitty agent workflow implement WP03 --base WP01 --tool opencode --model gpt-4 --profile python-implementer --role implementer`

**CRITICAL**: You MUST provide agent identity (`--agent` or explicit flags) to track who is implementing!

If no WP ID is provided, it will automatically find the first work package with `lane: "planned"` and move it to "doing" for you.

---

## Commit Workflow

**BEFORE moving to for_review**, you MUST commit your implementation:

```bash
cd .worktrees/###-mission-WP##/
git add -A
git commit -m "feat(WP##): <describe your implementation>"
```

<details><summary>PowerShell equivalent</summary>

```powershell
Set-Location .worktrees\###-mission-WP##\
git add -A
git commit -m "feat(WP##): <describe your implementation>"
```

</details>

**Then move to review:**

```bash
spec-kitty agent tasks move-task WP## --to for_review --note "Ready for review: <summary>"
```

**Why this matters:**

- `move-task` validates that your worktree has commits beyond main
- Uncommitted changes will block the move to for_review
- This prevents lost work and ensures reviewers see complete implementations

---

**The Python script handles all file updates automatically - no manual editing required!**

**NOTE**: If `/spec-kitty.status` shows your WP in "doing" after you moved it to "for_review", don't panic - a reviewer may have moved it back (changes requested), or there's a sync delay. Focus on your WP.
