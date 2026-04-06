# Doctrine Skills

Shipped skills that teach agents how to operate Spec Kitty correctly.

## Scope and Boundary

Skills are the **product-operation layer**: they answer "how do I use Spec
Kitty?" They are not the canonical source for mission behavior or team-
specific workflow — that role belongs to doctrine mission composition (step
contracts, procedures, action indices, mission definitions).

Two tracks exist and should remain distinct:

1. **Skills** — how an external agent correctly uses Spec Kitty itself:
   runtime-next control loop, charter/doctrine access, review workflow,
   setup/repair, glossary context, git workflow, orchestrator API.

2. **Doctrine mission composition** — how a team does product work: which
   steps a mission follows, what procedures each step delegates to, which
   directives and tactics scope each action.

Skills may *consume* doctrine outputs (e.g., calling `DoctrineService` to
load a tactic, reading an action index to scope context). Skills should
**not** become a second source of truth for mission behavior.

> "Skills answer: how do I operate Spec Kitty correctly? Doctrine mission
> composition answers: how should this team do product work? The compiler
> is what should bridge those without expanding the visible slash-command
> surface." — internal design review, PR #305

## Context Loading Pattern

Skills should teach agents to load doctrine **iteratively**:

1. At init: resolve agent profile, load initialization declaration.
2. At each step boundary: call `build_charter_context(action, depth=1)`.
3. When stuck or need guidance: pull specific tactic/directive by ID.
4. Never: load the full doctrine catalog into prompt context upfront.

## Inventory

| Skill | Purpose |
|---|---|
| `spec-kitty-runtime-next` | Drive the `next --agent` control loop with doctrine-aware context loading |
| `spec-kitty-charter-doctrine` | Charter lifecycle + `DoctrineService` programmatic access |
| `spec-kitty-mission-system` | Mission types, step contracts, procedures, action indices, template resolution |
| `ad-hoc-profile-load` | Load an agent profile on demand for interactive sessions outside the mission loop |
| `spec-kitty-runtime-review` | Review workflow surface: claim, review, approve/reject |
| `spec-kitty-implement-review` | Implement-review orchestration loop across WPs |
| `spec-kitty-setup-doctor` | Installation diagnostics and repair |
| `spec-kitty-git-workflow` | Git operations, worktree lifecycle, safe-commit pattern |
| `spec-kitty-glossary-context` | Terminology curation and semantic integrity |
| `spec-kitty-orchestrator-api-operator` | External automation via orchestrator-api |

## Source Location

These files in `src/doctrine/skills/` are the **source of truth**. Agent
copies (`.claude/skills/`, `.agents/skills/`, etc.) are generated during
`spec-kitty upgrade` and should not be edited directly.

## Related

- Issue #327: Doctrine mission compiler proposal
- PR #305 / #348: Doctrine artifact domain, agent profiles, charter bootstrap
- `src/doctrine/missions/`: Mission type definitions with action indices
- `src/doctrine/agent_profiles/`: Agent profile repository and shipped profiles
