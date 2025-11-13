# Claude & Cursor Collaboration

Blend Anthropic Claude and Cursor to accelerate delivery while maintaining Spec Kitty's guardrails.

## Objective
- Claude specializes in discovery, planning, and narrative-heavy tasks.
- Cursor executes implementation prompts with tight IDE integration.
- Both agents operate inside `.worktrees/<feature>` and respect the kanban workflow.

## Collaboration Pattern

### 0. Project Setup (One-time in main repo)
```bash
cd my-project
claude
```
```text
/spec-kitty.constitution

Create principles focused on code quality, testing standards,
and consistent documentation across all features.
```

### 1. Discovery & Spec (Claude)
Claude runs `/spec-kitty.specify` and writes the spec. Cursor remains idle.

```text
/spec-kitty.specify

Build a user authentication system with email/password login,
password reset, and session management.
```

**Result:** Creates `.worktrees/001-auth-system/` and feature branch

### 2. Switch to Feature Worktree (Claude)
```bash
cd .worktrees/001-auth-system
claude  # Restart Claude in the feature worktree
```

### 3. Planning (Claude)
Claude executes `/spec-kitty.plan` and updates plan.md.

```text
/spec-kitty.plan

Use Python FastAPI for backend, PostgreSQL for database,
JWT tokens for sessions, bcrypt for password hashing.
```

### 4. Task Generation (Claude)
```text
/spec-kitty.tasks
```

**Result:** Creates work packages in `tasks/planned/` - Claude reviews each for ambiguity

### 5. Parallel Execution (Both Agents)
- **Claude** handles research prompts (`/spec-kitty.research`) or explanatory work packages
- **Cursor** moves implementation prompts to `doing` via:
  ```bash
  .kittify/scripts/bash/tasks-move-to-lane.sh 001-auth-system WP01 doing
  ```
  Then codes inside its IDE and commits changes

### 6. Mutual Review (Both Agents)
- **Claude** runs `/spec-kitty.review` on Cursor's completed work in `for_review/`
- **Cursor** validates Claude's narrative outputs for technical consistency

### 7. Acceptance & Merge (Either Agent)
```text
/spec-kitty.accept
/spec-kitty.merge --push
```

## Coordination Tips
- Keep a shared log in `kitty-specs/<feature>/collaboration-notes.md`
- Use git worktree status (`git worktree list`) to confirm both agents operate in the same branch
- When switching ownership, run `.kittify/scripts/bash/tasks-move-to-lane.sh` to update lane and shell PID metadata
- Monitor the dashboard to see which agent is working on which task in real-time

## Agent Strengths
- **Claude:** Specification writing, planning, research, documentation, complex problem-solving
- **Cursor:** Code implementation, refactoring, debugging, IDE-integrated workflows
