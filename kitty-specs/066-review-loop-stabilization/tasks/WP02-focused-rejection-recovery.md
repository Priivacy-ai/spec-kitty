---
work_package_id: WP02
title: Focused Rejection Recovery
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-007
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "64375"
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/fix_prompt.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/fix_prompt.py
- tests/review/test_fix_prompt.py
- tests/integration/test_rejection_cycle.py
---

# WP02: Focused Rejection Recovery

## Objective

Generate focused fix-mode prompts (~40 lines) from persisted review-cycle artifacts instead of replaying the full WP implement prompt (~400-500 lines) when a WP is rejected. This is the core token-saving value proposition of mission 066.

**Issues**: [#430](https://github.com/Priivacy-ai/spec-kitty/issues/430), integration side of [#433](https://github.com/Priivacy-ai/spec-kitty/issues/433)
**Depends on**: WP01 (ReviewCycleArtifact read API)

## Context

### Current Behavior

When a WP is rejected and re-claimed, `agent action implement` in `workflow.py` (lines 526-662) regenerates the full WP prompt with review feedback appended. The implementing agent sees the entire original context (400-700 lines), concludes "everything looks done," and moves to `for_review` without making changes. This was observed during Feature 064 WP01 cycle 2.

### Target Behavior

When a WP has prior review-cycle artifacts (from WP01), the implement path generates a focused fix-mode prompt containing:
- Verbatim review findings (from artifact body)
- Affected file paths with line ranges (from artifact frontmatter)
- Current code read from disk (the code to fix)
- Reproduction command (from artifact frontmatter)
- Commit and status-transition instructions

### Integration Points

This WP modifies `workflow.py` in the implement action path (lines 526-662), which is separate from the review prompt section (lines 1190-1310) modified by WP03-WP05.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: same lane as WP01 (sequential dependency)

## Subtask Details

### T007: Create fix_prompt.py with generate_fix_prompt()

**Purpose**: Domain logic for producing a focused fix-mode prompt from a review-cycle artifact.

**Steps**:
1. Create `src/specify_cli/review/fix_prompt.py`
2. Implement the main function:
   ```python
   def generate_fix_prompt(
       artifact: ReviewCycleArtifact,
       worktree_path: Path,
       wp_prompt_path: Path,
       mission_slug: str,
       wp_id: str,
   ) -> str:
       """Generate a focused fix-mode prompt from a review-cycle artifact.

       Returns the prompt text as a string.
       """
   ```
3. The function should:
   - Read each affected file from disk at `worktree_path / artifact.affected_files[i].path`
   - Extract relevant code snippets using line ranges if provided
   - Compose the prompt from template sections (see T008)
   - Return the complete prompt string
4. Export from `src/specify_cli/review/__init__.py`

**Files**: `src/specify_cli/review/fix_prompt.py` (new)

### T008: Implement fix-prompt template rendering

**Purpose**: Define the structure and content of fix-mode prompts.

**Steps**:
1. The fix-prompt should contain these sections in order:

   ```markdown
   # Fix Mode: {wp_id} — Cycle {cycle_number}

   ## Review Findings

   {artifact.body — verbatim reviewer feedback}

   ## Affected Files

   {for each affected_file:}
   ### {file.path} (lines {file.line_range})

   ```{language}
   {current file content from disk, focused on line_range if provided}
   ```

   ## Reproduction

   ```bash
   {artifact.reproduction_command}
   ```

   ## Instructions

   1. Read the review findings above carefully
   2. Fix ONLY the issues described — do not refactor or improve unrelated code
   3. Run the reproduction command to verify your fix
   4. Commit your changes
   5. Move this WP back to for_review:
      spec-kitty agent tasks move-task {wp_id} --to for_review --mission {mission_slug}
   ```

2. Language detection for code blocks: derive from file extension (`.py` → `python`, `.ts` → `typescript`, etc.)
3. If `line_range` is provided, show the relevant lines plus 5 lines of context above and below
4. If `line_range` is None, show the full file (truncated to 100 lines max with a note)

**Validation**: Prompt should be < 25% of original WP prompt size for single-file findings (NFR-001).

### T009: Add fix-mode detection in workflow.py

**Purpose**: Detect whether a WP has prior review-cycle artifacts and should enter fix mode.

**Steps**:
1. In `workflow.py`, in the implement action path (around lines 526-662), add detection logic:
   ```python
   def _has_prior_rejection(feature_dir: Path, wp_slug: str) -> bool:
       """Check if WP has review-cycle artifacts from a prior rejection."""
       sub_artifact_dir = feature_dir / "tasks" / wp_slug
       if not sub_artifact_dir.exists():
           return False
       return bool(list(sub_artifact_dir.glob("review-cycle-*.md")))
   ```
2. Also check the event log: the latest event for this WP should have `from_lane=for_review` and `to_lane=planned` (rejection transition) with a `review_ref`
3. Both conditions must be true: artifacts exist AND the last transition was a rejection
4. This prevents false positives if artifacts exist from a previous implementation cycle that was already resolved

**Edge cases**:
- WP was rejected, fixed, approved, then re-implemented for a different reason → no fix mode (last event is not a rejection)
- WP was rejected multiple times → use the latest review-cycle artifact

### T010: Implement mode switching

**Purpose**: Wire fix-mode detection into the implement action to switch between full-prompt and fix-prompt output.

**Steps**:
1. In the implement action (workflow.py), after resolving the WP and workspace:
   ```python
   if _has_prior_rejection(feature_dir, wp_slug):
       latest_artifact = ReviewCycleArtifact.latest(sub_artifact_dir)
       if latest_artifact:
           prompt = generate_fix_prompt(
               artifact=latest_artifact,
               worktree_path=workspace_path,
               wp_prompt_path=wp_file,
               mission_slug=mission_slug,
               wp_id=normalized_wp_id,
           )
           # Output fix-mode prompt instead of full WP prompt
           console.print(prompt)
           return
   # Fall through to existing full-prompt logic
   ```

2. Log the mode switch: `console.print("[bold]Fix mode[/bold]: generating focused prompt from review-cycle-{N}")` using rich
3. Include a reference to the artifact path so the agent can read the full feedback if needed:
   `Canonical feedback: {artifact_path}`

**Critical**: The fix-prompt completely replaces the full WP prompt — it is NOT appended to it.

### T011: Write tests

**Purpose**: Comprehensive test coverage for fix-prompt generation and mode switching.

**Test files**: `tests/review/test_fix_prompt.py`, `tests/integration/test_rejection_cycle.py`

**Unit tests** (test_fix_prompt.py):
1. `test_generate_fix_prompt_single_file` — one affected file, verify prompt contains findings + code
2. `test_generate_fix_prompt_multiple_files` — three affected files, all appear in output
3. `test_generate_fix_prompt_with_line_range` — verify code snippet is focused on line range
4. `test_generate_fix_prompt_without_line_range` — full file shown (truncated)
5. `test_fix_prompt_size_vs_original` — verify fix prompt < 25% of a typical 491-line WP prompt for single-file finding
6. `test_generate_fix_prompt_missing_file` — affected file doesn't exist on disk, handled gracefully
7. `test_fix_prompt_includes_reproduction_command` — reproduction_command appears in output

**Integration tests** (test_rejection_cycle.py):
8. `test_has_prior_rejection_no_artifacts` — returns False for clean WP
9. `test_has_prior_rejection_with_artifacts_and_event` — returns True after rejection
10. `test_mode_switch_produces_fix_prompt` — end-to-end: create artifact + rejection event → implement outputs fix prompt
11. `test_mode_switch_falls_through_on_resolved` — artifact exists but last event is not rejection → full prompt

**Coverage target**: 90%+ for `src/specify_cli/review/fix_prompt.py`

## Definition of Done

- [ ] generate_fix_prompt() produces focused prompts from ReviewCycleArtifact
- [ ] Fix-prompt size < 25% of original for single-file findings
- [ ] Fix-mode detection correctly identifies rejected WPs with artifacts
- [ ] Mode switching replaces full prompt (not appends to it)
- [ ] Fall-through to full prompt works when no rejection exists
- [ ] 90%+ test coverage on review/fix_prompt.py
- [ ] All existing tests pass

## Reviewer Guidance

- Verify that the fix prompt is truly self-contained — an agent should not need to read the original WP prompt
- Check that mode detection requires BOTH artifacts AND a rejection event (prevents false positives)
- Verify prompt sizing on a realistic 491-line WP prompt (from issue #430)
- Confirm rich formatting is used for console output (not raw print)

## Activity Log

- 2026-04-06T16:50:40Z – claude:sonnet-4-6:implementer:implementer – shell_pid=51949 – Started implementation via action command
- 2026-04-06T16:56:25Z – claude:sonnet-4-6:implementer:implementer – shell_pid=51949 – Ready for review: focused fix-mode prompt generation from review artifacts, 28/28 tests passing, 95% coverage on fix_prompt.py
- 2026-04-06T16:56:47Z – claude:opus-4-6:reviewer:reviewer – shell_pid=64375 – Started review via action command
- 2026-04-06T16:59:45Z – claude:opus-4-6:reviewer:reviewer – shell_pid=64375 – Review passed: generate_fix_prompt() correctly produces focused prompts from ReviewCycleArtifact. 95% coverage on fix_prompt.py (28/28 tests pass). Fix-mode detection requires BOTH artifacts AND rejection event. Mode switching replaces full prompt via early return. Fall-through works. NFR-001 size constraint verified.
