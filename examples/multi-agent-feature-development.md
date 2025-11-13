# Multi-Agent Feature Development

This scenario demonstrates how a lead architect can orchestrate a multi-agent team to deliver a complex feature with Spec Kitty.

## Context
- Feature: `001-cross-platform-chat-upgrade`
- Agents: Claude (spec/plan), Gemini (data modeling), Cursor (implementation), Human reviewer
- Goal: Deliver a cross-platform chat upgrade (web + mobile) with improved reliability in two weeks

## Playbook
1. **Specify the feature**  
   Lead runs `/spec-kitty.specify` with the stakeholder brief. Discovery gates confirm scope, users, and success metrics.

2. **Plan and research**  
   Claude executes `/spec-kitty.plan` to capture architecture; Gemini runs `/spec-kitty.research` to gather literature benchmarks.

3. **Generate work packages**  
   `/spec-kitty.tasks` produces eight prompts across API, UI, and infrastructure. `[P]` flags highlight parallel-safe work such as documentation updates and telemetry instrumentation.

4. **Assign agents**  
   - Claude handles plan updates and reviews.  
   - Gemini owns data-model.md updates and research prompts.  
   - Cursor implements the chat service changes.  
   - Human reviewer tracks `tasks/for_review/`.

5. **Run the kanban workflow**
   Each agent moves prompts using `.kittify/scripts/bash/tasks-move-to-lane.sh` and logs progress. The dashboard shows lane health in real time.

6. **Review completed work**
   Human reviewer processes `for_review` prompts via `/spec-kitty.review`, providing feedback or approving work to move to `done`.

7. **Acceptance & merge**
   Once all work packages are in `done/`:
   ```text
   /spec-kitty.accept  # Validates feature readiness, records metadata
   /spec-kitty.merge --push  # Merges to main, cleans up worktree
   ```

## Outcome
- Web and mobile chat surfaces upgraded with consistent reliability guarantees
- Zero merge conflicts (agents respected prompt file boundaries)
- Dashboard snapshot exported for the sprint report
