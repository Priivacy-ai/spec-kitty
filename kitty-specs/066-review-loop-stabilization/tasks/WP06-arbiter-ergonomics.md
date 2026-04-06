---
work_package_id: WP06
title: Arbiter Ergonomics
dependencies: []
requirement_refs:
- C-005
- FR-014
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-066-review-loop-stabilization
base_commit: 4dbb05e1ae46b17dad6ae64402cfb2861107f268
created_at: '2026-04-06T16:42:36.857956+00:00'
subtasks:
- T030
- T031
- T032
- T033
- T034
- T035
shell_pid: "51659"
agent: "claude:opus-4-6:reviewer:reviewer"
history:
- timestamp: '2026-04-06T16:32:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/arbiter.py
execution_mode: code_change
owned_files:
- src/specify_cli/review/arbiter.py
- tests/review/test_arbiter.py
---

# WP06: Arbiter Ergonomics

## Objective

Add a structured arbiter checklist and rationale model for false-positive review rejections. Arbiter override decisions should use a standard category set, be persisted in the review history, and be visible in subsequent review cycles.

**Issues**: [#441](https://github.com/Priivacy-ai/spec-kitty/issues/441)
**Dependencies**: None (uses review-cycle artifacts if WP01 has landed, gracefully degrades if not)

## Context

### Current Problem

Arbiter overrides are mechanically easy (just `--force`) but cognitively expensive. Operators must quickly decide whether a rejection should be overruled. Common causes: pre-existing test failures, wrong feature/WP context, findings outside WP scope, hallucinated/stale context, and environmental failures. Currently, `--force` sets `review_ref` to `"force-override"` — no structured rationale, no audit trail.

### Target Behavior

When an arbiter overrides a rejection (detected as a forward `--force` move from `planned` after a rejection event), the system presents a 5-question checklist, derives a category, records the decision, and persists it in the review-cycle artifact's frontmatter. The `review_ref` in the event log points to the same `review-cycle://` artifact — no new pointer scheme.

### Override Detection Logic

An arbiter override is detected when ALL of these are true:
1. `--force` flag is set
2. Current lane is `planned`
3. Target lane is forward (`for_review`, `claimed`, or `approved`)
4. The latest event for this WP was a `for_review` → `planned` transition with a `review_ref` (i.e., a rejection)

This prevents false triggers on normal claim/re-claim workflows.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktree: allocated per lane (independent lane)

## Subtask Details

### T030: Create arbiter.py with dataclasses

**Purpose**: Define the arbiter decision model.

**Steps**:
1. Create `src/specify_cli/review/arbiter.py`
2. Define the category enum:
   ```python
   from enum import StrEnum

   class ArbiterCategory(StrEnum):
       PRE_EXISTING_FAILURE = "pre_existing_failure"
       WRONG_CONTEXT = "wrong_context"
       CROSS_SCOPE = "cross_scope"
       INFRA_ENVIRONMENTAL = "infra_environmental"
       CUSTOM = "custom"
   ```

3. Define the checklist dataclass:
   ```python
   @dataclass(frozen=True)
   class ArbiterChecklist:
       is_pre_existing: bool       # Q1: Is the failure pre-existing on the base branch?
       is_correct_context: bool    # Q2: Is the reviewer talking about the correct feature/WP?
       is_in_scope: bool           # Q3: Is the finding within this WP's scope?
       is_environmental: bool      # Q4: Is the failure environmental/infra?
       should_follow_on: bool      # Q5: Should this become a follow-on issue instead?

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> ArbiterChecklist: ...
   ```

4. Define the decision dataclass:
   ```python
   @dataclass(frozen=True)
   class ArbiterDecision:
       arbiter: str                # who made the decision
       category: ArbiterCategory
       explanation: str            # mandatory for all categories, especially CUSTOM
       checklist: ArbiterChecklist
       decided_at: str             # ISO 8601 UTC

       def to_dict(self) -> dict[str, Any]: ...
       @classmethod
       def from_dict(cls, data: dict[str, Any]) -> ArbiterDecision: ...
   ```

5. Export all three from `src/specify_cli/review/__init__.py`

### T031: Implement prompt_arbiter_checklist()

**Purpose**: Present the checklist and derive the category.

**Steps**:
1. Implement the function:
   ```python
   def prompt_arbiter_checklist(
       wp_id: str,
       arbiter_name: str,
       console: Console,
   ) -> ArbiterDecision:
       """Present the arbiter checklist and return a structured decision."""
   ```

2. **Checklist questions** (present via rich console):
   ```
   Arbiter Override Checklist for {wp_id}

   Answer each question to classify this override:

   Q1. Is this failure pre-existing on the base branch? [y/N]
   Q2. Is the reviewer talking about the correct feature/WP? [Y/n]
   Q3. Is the finding within this WP's scope? [Y/n]
   Q4. Is the failure environmental or infrastructure-related? [y/N]
   Q5. Should this become a follow-on issue instead of blocking this WP? [y/N]
   ```

3. **Category derivation** from checklist responses:
   ```python
   def _derive_category(checklist: ArbiterChecklist) -> ArbiterCategory:
       if checklist.is_pre_existing:
           return ArbiterCategory.PRE_EXISTING_FAILURE
       if not checklist.is_correct_context:
           return ArbiterCategory.WRONG_CONTEXT
       if not checklist.is_in_scope:
           return ArbiterCategory.CROSS_SCOPE
       if checklist.is_environmental:
           return ArbiterCategory.INFRA_ENVIRONMENTAL
       return ArbiterCategory.CUSTOM
   ```

4. **Explanation prompt**: Always ask for explanation. For CUSTOM, it is mandatory (reject empty). For other categories, provide a default based on the category name but allow override.

5. **Non-interactive mode**: For CI/automated contexts, accept category and explanation directly via function parameters (skip the interactive checklist). This is needed because agents calling move-task with `--force` may not have interactive input.

   ```python
   def create_arbiter_decision(
       arbiter_name: str,
       category: str | ArbiterCategory,
       explanation: str,
       checklist: ArbiterChecklist | None = None,
   ) -> ArbiterDecision:
       """Non-interactive arbiter decision creation."""
   ```

### T032: Implement override detection in move-task

**Purpose**: Detect when a `--force` move is an arbiter override vs. a normal force operation.

**Steps**:
1. In `tasks.py` move_task() function, add detection logic (before the existing force-override path):
   ```python
   def _is_arbiter_override(
       feature_dir: Path,
       wp_id: str,
       old_lane: str,
       target_lane: str,
       force: bool,
   ) -> bool:
       """Detect if this is an arbiter override of a rejection."""
       if not force:
           return False
       if old_lane != "planned":
           return False
       if target_lane not in ("for_review", "claimed", "approved"):
           return False

       # Check if latest event was a rejection
       from specify_cli.status.store import read_events
       events = read_events(feature_dir)
       wp_events = [e for e in events if e.wp_id == wp_id]
       if not wp_events:
           return False
       latest = wp_events[-1]
       return (
           latest.from_lane == Lane.FOR_REVIEW
           and latest.to_lane == Lane.PLANNED
           and latest.review_ref is not None
       )
   ```

2. When detected, prompt for arbiter decision before proceeding:
   ```python
   if _is_arbiter_override(feature_dir, wp_id, old_lane, target_lane, force):
       # Get the review-cycle artifact that the rejection created
       review_ref = latest_event.review_ref

       # Create arbiter decision (non-interactive for agent context)
       # The agent should provide --note with the category and explanation
       decision = create_arbiter_decision(
           arbiter_name=agent or "operator",
           category=_parse_arbiter_category_from_note(note),
           explanation=note or "Override without explanation",
       )
       # ... persist and proceed
   ```

3. **--note flag reuse**: The existing `--note` flag on move-task carries the arbiter's explanation. The category can be parsed from a structured format in the note: `"[pre_existing_failure] Test was already failing"`

4. If `--note` is missing on an arbiter override, warn but proceed (don't block — the whole point is operator efficiency).

### T033: Persist ArbiterDecision in review-cycle artifact

**Purpose**: Store the arbiter decision as a frontmatter extension on the review-cycle artifact.

**Steps**:
1. When an arbiter override is detected and a ReviewCycleArtifact exists:
   - Load the review-cycle artifact that the rejection created (resolve from `review_ref` pointer)
   - Add `arbiter_override` section to frontmatter:
     ```yaml
     arbiter_override:
       arbiter: "robert"
       category: "pre_existing_failure"
       explanation: "Test test_legacy_import_path has been failing since commit abc123"
       checklist:
         is_pre_existing: true
         is_correct_context: true
         is_in_scope: true
         is_environmental: false
         should_follow_on: false
       decided_at: "2026-04-06T14:00:00Z"
     ```
   - Rewrite the artifact file with updated frontmatter (preserve body)
   - Commit the updated artifact

2. If WP01 hasn't landed yet (no review-cycle artifact exists), write the arbiter decision to a standalone file:
   `kitty-specs/<mission>/tasks/<WP-slug>/arbiter-override-{N}.json`
   This is a graceful degradation path.

3. Set `review_ref` in the emitted event to the existing `review-cycle://` pointer (NOT a new scheme):
   ```python
   emit_review_ref = review_ref  # reuse the rejection's pointer
   ```

### T034: Make arbiter decisions visible

**Purpose**: Surface arbiter override history in status displays.

**Steps**:
1. In `agent tasks status` output (the kanban display), when showing review cycles for a WP:
   - Check if any review-cycle artifact has an `arbiter_override` section in frontmatter
   - If yes, show: `Cycle {N}: rejected → overridden ({category})`
   - Use rich formatting: `[yellow]overridden[/yellow]` for visibility

2. This is informational only — no new CLI commands needed. The existing `agent tasks status` command reads from the event log and can also peek at review-cycle artifacts.

### T035: Write tests

**Test file**: `tests/review/test_arbiter.py`

**Required test cases**:
1. `test_arbiter_category_enum_values` — all 5 categories have correct string values
2. `test_checklist_to_dict_round_trip` — create, to_dict, from_dict, compare
3. `test_decision_to_dict_round_trip` — full decision round-trip
4. `test_derive_category_pre_existing` — is_pre_existing=True → PRE_EXISTING_FAILURE
5. `test_derive_category_wrong_context` — is_correct_context=False → WRONG_CONTEXT
6. `test_derive_category_cross_scope` — is_in_scope=False → CROSS_SCOPE
7. `test_derive_category_environmental` — is_environmental=True → INFRA_ENVIRONMENTAL
8. `test_derive_category_custom` — all normal, falls through → CUSTOM
9. `test_is_arbiter_override_after_rejection` — rejection event + forward force → True
10. `test_is_arbiter_override_normal_claim` — no rejection event + force → False
11. `test_is_arbiter_override_no_force` — rejection event + no force → False
12. `test_persist_decision_in_artifact` — decision appears in artifact frontmatter
13. `test_persist_decision_standalone_fallback` — no artifact → standalone JSON created
14. `test_parse_category_from_note` — "[pre_existing_failure] explanation" parsed correctly

**Coverage target**: 90%+ for `src/specify_cli/review/arbiter.py`

## Definition of Done

- [ ] ArbiterCategory, ArbiterChecklist, ArbiterDecision pass mypy --strict
- [ ] Override detection correctly identifies forward --force after rejection
- [ ] Override detection does NOT trigger on normal claim/re-claim
- [ ] ArbiterDecision persisted in review-cycle artifact frontmatter
- [ ] Standalone fallback works when WP01 hasn't landed
- [ ] Agent tasks status shows override history
- [ ] No new pointer scheme (reuses review-cycle://)
- [ ] 90%+ test coverage on arbiter.py
- [ ] All existing tests pass

## Reviewer Guidance

- Verify override detection requires ALL four conditions (force + planned + forward target + rejection event)
- Check that the note parsing is lenient — missing categories default to CUSTOM, missing explanation defaults to a generic message
- Verify standalone fallback (arbiter-override-{N}.json) is only used when review-cycle artifacts don't exist
- Confirm no `arbiter-override://` pointer scheme exists anywhere

## Activity Log

- 2026-04-06T16:42:37Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48129 – Started implementation via action command
- 2026-04-06T16:49:35Z – claude:sonnet-4-6:implementer:implementer – shell_pid=48129 – Arbiter checklist model, override detection, persistence, kanban visibility — 21 tests passing
- 2026-04-06T16:49:52Z – claude:opus-4-6:reviewer:reviewer – shell_pid=51659 – Started review via action command
