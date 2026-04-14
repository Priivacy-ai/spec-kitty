---
work_package_id: WP03
title: Inference Warning System
dependencies: []
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
agent: "claude:opus:implementer:implementer"
shell_pid: "59674"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/specify_cli/bulk_edit/
execution_mode: code_change
owned_files:
- src/specify_cli/bulk_edit/inference.py
- tests/specify_cli/bulk_edit/test_inference.py
tags: []
---

# WP03 — Inference Warning System

## Objective

Create the keyword-scanning inference module that detects rename/migration language in spec content and returns a scored result. This module is purely analytical — it reads spec.md and returns a score. The CLI wiring (displaying warnings, handling acknowledgement) is in WP04.

## Context

- **Spec**: FR-009 (inference warning), FR-010 (acknowledgement resolution), NFR-003 (< 20% false positive rate)
- **Plan**: Integration Point 3 — Inference Warning
- **Data model**: Keyword weights table — high (3), medium (2), low (1), threshold >= 4
- **Research**: RQ-3 — Conservative keyword list with scoring threshold, pattern from `ownership/inference.py`
- This module follows the same scoring pattern as `src/specify_cli/ownership/inference.py` (planning_signals / code_signals)

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T006: Create inference.py — Weighted Keyword Scanning

**Purpose**: Implement the keyword scoring engine that analyzes spec.md content for rename/migration language.

**Steps**:

1. Create `src/specify_cli/bulk_edit/inference.py`

2. Define keyword weight tables:
   ```python
   # High-specificity phrases (3 points each) — strong signal for bulk edit
   HIGH_WEIGHT_PHRASES: list[str] = [
       "rename across",
       "bulk edit",
       "codemod",
       "find-and-replace",
       "find and replace",
       "replace everywhere",
       "terminology migration",
       "rename all occurrences",
   ]

   # Medium-specificity keywords (2 points each)
   MEDIUM_WEIGHT_KEYWORDS: list[str] = [
       "rename",
       "migrate",
       "replace all",
       "across the codebase",
       "globally",
       "sed",
       "search and replace",
   ]

   # Low-specificity keywords (1 point each) — common, ambiguous alone
   LOW_WEIGHT_KEYWORDS: list[str] = [
       "update",
       "change",
       "modify",
       "refactor",
   ]

   INFERENCE_THRESHOLD: int = 4
   ```

3. Implement `score_spec_for_bulk_edit(spec_content: str) -> InferenceResult`:
   ```python
   @dataclass(frozen=True)
   class InferenceResult:
       score: int
       threshold: int
       triggered: bool  # score >= threshold
       matched_phrases: list[tuple[str, int]]  # (phrase, weight)
   ```

   Scoring rules:
   - Normalize content to lowercase for matching
   - Match high-weight phrases first (substring match)
   - Match medium-weight keywords (word boundary aware where possible)
   - Match low-weight keywords (word boundary aware)
   - Each unique keyword/phrase counts only once (no double-counting from overlapping phrases)
   - Return `InferenceResult` with score, threshold, triggered flag, and matched items

4. Implement `scan_spec_file(feature_dir: Path) -> InferenceResult`:
   - Read `feature_dir / "spec.md"`
   - If spec.md doesn't exist: return InferenceResult(score=0, threshold=INFERENCE_THRESHOLD, triggered=False, matched_phrases=[])
   - Call `score_spec_for_bulk_edit()` on content
   - Return result

5. Use `from __future__ import annotations` and full type annotations.

**Files**: `src/specify_cli/bulk_edit/inference.py`

**Validation**:
- [ ] Score of 0 for spec with no relevant keywords
- [ ] Score >= 4 for "rename all occurrences of X across the codebase"
- [ ] Score < 4 for "update the configuration file" (low-weight only)
- [ ] High-weight phrases score 3 each
- [ ] No double-counting when phrases overlap (e.g., "rename" inside "rename across")
- [ ] Missing spec.md returns non-triggered result

---

### Subtask T007: Unit Tests for Inference Keyword Scanning

**Purpose**: Verify scoring accuracy and threshold behavior.

**Steps**:

1. Create `tests/specify_cli/bulk_edit/test_inference.py`

2. Test cases for `score_spec_for_bulk_edit`:
   - `test_empty_content_scores_zero`
   - `test_single_high_phrase_scores_3`: "This will use a codemod to migrate" → 3+ (codemod)
   - `test_single_medium_keyword_scores_2`: "Rename the function" → 2 (rename)
   - `test_single_low_keyword_scores_1`: "Update the module" → 1 (update)
   - `test_threshold_reached_with_mixed_weights`: "Rename all occurrences across the codebase" → >= 4
   - `test_threshold_not_reached_with_low_only`: "Update and change the config" → 2 (below threshold)
   - `test_no_double_counting`: "rename across" should count as high (3), not also as medium "rename" (2)
   - `test_case_insensitive`: "BULK EDIT" scores same as "bulk edit"
   - `test_realistic_spec_positive`: Full spec text describing a rename operation → triggered=True
   - `test_realistic_spec_negative`: Full spec text about adding a new feature → triggered=False

3. Test cases for `scan_spec_file`:
   - `test_scan_missing_spec_returns_not_triggered`
   - `test_scan_existing_spec_returns_result`

4. False-positive guard tests:
   - `test_normal_feature_spec_not_triggered`: "Add authentication endpoint with password reset" → triggered=False
   - `test_refactoring_spec_not_triggered`: "Refactor the database layer for better performance" → triggered=False (score=1, below threshold)

**Files**: `tests/specify_cli/bulk_edit/test_inference.py`

**Validation**:
- [ ] All tests pass: `pytest tests/specify_cli/bulk_edit/test_inference.py -v`
- [ ] Coverage >= 90% on `inference.py`

## Definition of Done

- [ ] `inference.py` scores spec content with weighted keywords
- [ ] Threshold of 4 correctly separates bulk-edit specs from normal specs
- [ ] No double-counting on overlapping phrases
- [ ] Case-insensitive matching
- [ ] All tests pass with 90%+ coverage
- [ ] mypy --strict passes

## Risks

- **Medium**: False positives on specs that use "rename" in a different context (e.g., "rename the PR"). Mitigate by keeping threshold at 4 (requires multiple signals) and using phrase-level matching for high-weight items.

## Reviewer Guidance

- Verify the keyword lists are conservative (err on the side of fewer false positives)
- Check that overlapping phrases are handled correctly (no double-counting)
- Test with realistic spec content to validate the threshold
- Confirm the module is pure analysis (no Rich output, no CLI interaction — that's WP04)

## Activity Log

- 2026-04-13T19:07:15Z – claude:opus:implementer:implementer – shell_pid=59674 – Started implementation via action command
- 2026-04-13T19:11:50Z – claude:opus:implementer:implementer – shell_pid=59674 – Ready for review
- 2026-04-13T19:12:26Z – claude:opus:implementer:implementer – shell_pid=59674 – Review passed: clean keyword scoring, word boundary matching, no-double-counting, pure analysis. 15 tests.
- 2026-04-13T19:32:08Z – claude:opus:implementer:implementer – shell_pid=59674 – Done override: Feature merged to main
