---
name: ad-hoc-profile-load
description: >-
  Load an agent profile on demand to adopt a specific role for the current
  session. Applies the profile's identity, governance scope, boundaries, and
  initialization declaration without requiring a running mission.
  Triggers: "act as the architect", "load the reviewer profile",
  "switch to implementer", "use the researcher persona",
  "start a session as planner", "adopt the curator role",
  "initialize profile", "assume the designer identity".
  Does NOT handle: mission advancement (use runtime-next), charter
  interview/generation (use charter-doctrine), or profile creation
  (use spec-kitty agent profile create).
argument-hint: "<profile-id>"
---

# ad-hoc-profile-load

Load an agent profile interactively to adopt a specific role for the current
session. This skill is for ad-hoc use outside the mission runtime loop — when
a user wants an agent to behave as a particular role without starting a formal
mission.

---

## When to Use This Skill

Use this when the user asks you to:

- Act as a specific agent role (architect, reviewer, implementer, etc.)
- Load a profile for an interactive session
- Adopt role-scoped boundaries and governance context
- Switch roles mid-conversation

Do NOT use this when:

- A mission is running and `spec-kitty next` is driving the loop — the
  runtime assigns profiles automatically via DDR-011 matching
- The user wants to create a new profile — use `spec-kitty agent profile create`
- The user wants to modify an existing profile — edit the YAML directly

---

## Step 1: Resolve the Profile

If the user names a profile directly, load it. If they describe a role or
task, resolve the best match.

**By explicit ID:**

```bash
spec-kitty agent profile show <profile-id>
```

```python
from doctrine.agent_profiles import AgentProfileRepository

repo = AgentProfileRepository(project_dir=project_agents_dir)
profile = repo.resolve_profile("architect")
```

**By task context (when the user describes what they want to do):**

```python
from doctrine.agent_profiles.profile import TaskContext

context = TaskContext(
    languages=["python"],
    frameworks=["fastapi", "<project-test-runner>"],
    file_patterns=["src/**/*.py"],
    domain_keywords=["architecture", "design"],
)

profile = repo.find_best_match(context)
```

**Discovery (when the user is unsure which profile to use):**

```bash
spec-kitty agent profile list
spec-kitty agent profile hierarchy
```

---

## Step 2: Apply the Profile

Once resolved, adopt the profile by internalizing three things:

### Identity

Read `initialization_declaration` — this is your startup persona statement.
Acknowledge it at the beginning of the session.

```python
print(profile.initialization_declaration)
# "I am Architect Alphonso. I design scalable, maintainable system
#  architectures using established design patterns and principles..."
```

### Boundaries

Read `specialization` — this defines your scope:

- `primary_focus` — what you actively do
- `secondary_awareness` — what you consider but don't own
- `avoidance_boundary` — what you must not do

Before taking any action, check whether it falls within your boundaries.
If the user asks you to do something in the avoidance boundary, acknowledge
the request and explain which role would handle it instead (using
`collaboration.handoff_to`).

### Governance Scope

The profile's `context_sources` declares which doctrine layers and specific
directives are relevant to this role. Load only those:

```python
from doctrine.service import DoctrineService

service = DoctrineService(shipped_root, project_root)

# Load directives referenced by this profile
for ref in profile.directive_references:
    directive = service.directives.get(f"DIRECTIVE_{ref.code}")
    # Apply this directive's constraints to your behavior
```

Do NOT load the full doctrine catalog. The profile scopes what matters.

---

## Step 3: Scope Governance Context

After adopting the profile, load charter context scoped to the action
the user wants to perform:

```bash
spec-kitty charter context --action implement --json
```

If the user hasn't named an action, infer it from the profile's
`canonical_verbs`:

| Profile | Canonical verbs | Default action |
|---|---|---|
| architect | design, evaluate, decide, model, specify | specify |
| planner | plan, prioritize, decompose, schedule | plan |
| implementer | implement, fix, refactor, test, debug | implement |
| reviewer | review, approve, reject, assess | review |
| researcher | research, investigate, evaluate, synthesize | specify |
| curator | curate, validate, update, reconcile | review |
| designer | design, prototype, sketch, iterate | specify |

---

## Step 4: Maintain Role Throughout the Session

### Respect Handoffs

When work falls outside your boundaries, name the appropriate role:

```
"This requires implementation work. That's in Implementer Ivan's scope —
I can hand off my architectural notes for them to execute."
```

The profile's `collaboration` section defines:
- `handoff_to` — roles you delegate work to
- `handoff_from` — roles that delegate to you
- `works_with` — roles you collaborate with in parallel

### Pull Doctrine On Demand

When you need guidance mid-session, pull specific tactics or directives
relevant to your current task — don't reload the full context:

```python
# Need guidance on a design decision?
tactic = service.tactics.get("adr-drafting-workflow")

# Need to check a quality gate?
directive = service.directives.get("DIRECTIVE_030")
```

### Mode Selection

The profile's `mode_defaults` lists the working modes this role supports.
If the user's request maps to a specific mode, acknowledge it:

```python
for mode in profile.mode_defaults:
    # mode.mode → "analysis", "design", "review", etc.
    # mode.description → what this mode is for
    # mode.use_case → when to activate it
    pass
```

---

## Step 5: Tool Context Persistence (Optional)

To persist the profile for the current tool so it loads automatically on
next session:

```bash
spec-kitty agent profile init <profile-id>
```

This writes a `spec-kitty.profile-context.md` file to the active tool's
command directory (e.g., `.claude/commands/`, `.cursor/commands/`). The
profile context is then available to the agent on every invocation until
replaced.

---

## Quick Reference

```bash
# List profiles
spec-kitty agent profile list

# Inspect a profile
spec-kitty agent profile show architect

# View hierarchy
spec-kitty agent profile hierarchy

# Persist to tool context
spec-kitty agent profile init architect
```

```python
from doctrine.agent_profiles import AgentProfileRepository
from doctrine.service import DoctrineService

# Load profile
repo = AgentProfileRepository()
profile = repo.resolve_profile("architect")

# Read identity
profile.initialization_declaration
profile.specialization.primary_focus
profile.specialization.avoidance_boundary

# Load scoped doctrine
service = DoctrineService(shipped_root, project_root)
for ref in profile.directive_references:
    service.directives.get(f"DIRECTIVE_{ref.code}")

# Check boundaries before acting
if task_type in profile.specialization.avoidance_boundary:
    suggest_handoff(profile.collaboration.handoff_to)
```
