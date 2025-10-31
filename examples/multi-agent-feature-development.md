# Multi-Agent Feature Development

This scenario demonstrates how a lead architect can orchestrate a multi-agent team to deliver a complex feature with Spec Kitty.

## Context
- Feature: `001-systematic-recognizer-enhancement`
- Agents: Claude (spec/plan), Gemini (data modeling), Cursor (implementation), Human reviewer
- Goal: Upgrade recognizer confidence scoring across 55 detectors in two weeks

## Playbook
1. **Specify the feature**  
   Lead runs `/spec-kitty.specify` with the stakeholder brief. Discovery gates confirm scope, users, and success metrics.

2. **Plan and research**  
   Claude executes `/spec-kitty.plan` to capture architecture; Gemini runs `/spec-kitty.research` to gather literature benchmarks.

3. **Generate work packages**  
   `/spec-kitty.tasks` produces eight prompts. `[P]` flags highlight parallel-safe work like synthetic dataset generation.

4. **Assign agents**  
   - Claude handles plan updates and reviews.  
   - Gemini owns data-model.md updates and research prompts.  
   - Cursor implements core recognizer changes.  
   - Human reviewer tracks `tasks/for_review/`.

5. **Run the kanban workflow**  
   Each agent moves prompts using `.kittify/scripts/bash/tasks-move-to-lane.sh` and logs progress. The dashboard shows lane health in real time.

6. **Review & merge**  
   Human reviewer processes `for_review` prompts, uses `/spec-kitty.merge` once all packages land in `done`.

## Outcome
- 55 recognizers updated with deterministic scoring
- Zero merge conflicts (agents respected prompt file boundaries)
- Dashboard snapshot exported for the sprint report
