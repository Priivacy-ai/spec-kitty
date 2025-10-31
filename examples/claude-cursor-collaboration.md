# Claude & Cursor Collaboration

Blend Anthropic Claude and Cursor to accelerate delivery while maintaining Spec Kitty’s guardrails.

## Objective
- Claude specializes in discovery, planning, and narrative-heavy tasks.
- Cursor executes implementation prompts with tight IDE integration.
- Both agents operate inside `.worktrees/<feature>` and respect the kanban workflow.

## Collaboration Pattern
1. **Discovery & Spec** – Claude runs `/spec-kitty.specify` and writes the spec. Cursor remains idle.
2. **Planning** – Claude executes `/spec-kitty.plan`, updates plan.md, and refreshes agent context via `.kittify/scripts/bash/update-agent-context.sh claude`.
3. **Task Generation** – `/spec-kitty.tasks` creates prompts. Claude reviews each for ambiguity; Cursor prepares to implement.
4. **Parallel Execution**  
   - Claude handles research prompts or explanatory work packages.  
   - Cursor moves implementation prompts to `doing`, codes inside its IDE, and commits changes.
5. **Mutual Review** – Claude reviews Cursor’s prompts in `for_review`; Cursor validates Claude’s narrative outputs for consistency.

## Coordination Tips
- Keep a shared log in `kitty-specs/<feature>/collaboration-notes.md`.
- Use git worktree status (`git worktree list`) to confirm both agents operate in the same branch.
- When switching ownership, run `tasks-move-to-lane.sh` to reset the lane and shell PID metadata.
