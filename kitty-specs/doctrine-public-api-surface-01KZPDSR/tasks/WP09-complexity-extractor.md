---
work_package_id: WP09
title: 'Complexity refactor: extractor.py (isolated)'
dependencies:
- WP01
requirement_refs:
- FR-010
- NFR-003
planning_base_branch: feat/doctrine-public-api-surface
merge_target_branch: feat/doctrine-public-api-surface
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-public-api-surface. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-public-api-surface unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
phase: Phase 4 - Debt
history:
- timestamp: '2026-08-10T18:39:50Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/extractor.py
create_intent: []
execution_mode: code_change
mission_id: 01KZPDSR40YTNZ9HPWV3V9V3YA
owned_files:
- src/doctrine/drg/migration/extractor.py
role: implementer
tags: []
tracker_refs: []
wp_code: WP09
---

# Work Package Prompt: WP09 — Complexity refactor: extractor.py

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and apply its initialization, boundaries, directives, and
tactics. **Also load the semantic-compression / disciplined-refactoring doctrine** (`/spec-kitty`
→ `spk-doctrine-semantic-compression`) — it governs HOW this behavior-preserving refactor is done
(C-007-mission). State which you applied.

## Objective

Reduce `src/doctrine/drg/migration/extractor.py`'s S3776 functions — `:545` (cognitive complexity
**183**, >12× the ≤15 ceiling) and `:933` (16) — to ≤ 15, strictly behavior-preserving (FR-010,
NFR-003). This is the mission's highest-risk slice: isolated in its own WP, sequenced last,
independently revertable.

## Context & Constraints

- **Behavior lock:** WP01 captured the golden `regenerate-graph` output. After every extraction,
  `spec-kitty doctrine regenerate-graph --check` must stay exit-0 (byte-identical). Do NOT proceed
  without WP01's golden.
- **No complexity-shuffling:** cognitive complexity ≤15 is gameable by extracting no-op helpers
  that relocate rather than reduce load. Every extracted helper must (a) have a clear single
  responsibility and (b) carry its own focused unit test (charter Sonar expectation: "every new
  branch/helper needs tests in the same PR").
- NFR-005: no suppressions, no Sonar-UI triage.
- **Preserve charter-re-exported symbols (post-tasks squad):** `charter.drg` imports
  `FIELDS_WITHHELD_FROM_GRAPH_OUTPUT`, `graph_document_to_dict`, `model_to_graph_dict` from
  `doctrine.drg.migration.extractor`. Do NOT rename/inline these (or any module-level public
  symbol) — WP03's facade identity test would break. Refactor *inside* function bodies only.

## Subtasks

### T042 — Refactor `extractor.py:545` (cc 183 → ≤ 15)
- Decompose the god-function into deterministic, single-responsibility helpers (separate
  lookup/build/emit phases; flatten nested conditionals). Each helper gets a focused test with
  stable inputs/outputs. Re-run `regenerate-graph --check` after each extraction.

### T043 — Refactor `extractor.py:933` + any remaining extractor S3776 functions
- Same discipline. Confirm ruff `C901` / Sonar `S3776` report ≤ 15 for every function in the file.

### T044 — Verify byte-identity + complexity
- `regenerate-graph --check` exit 0; `ruff check src/doctrine/drg/migration/extractor.py` clean;
  every touched function ≤ 15; helper tests green.

## Branch Strategy

Base + merge target `feat/doctrine-public-api-surface`; worktree per lane. Implement via
`spec-kitty agent action implement WP09 --agent <name>` (after WP01). Independently revertable —
if the refactor risks the golden, revert this WP alone without touching the boundary work.

## Definition of Done

- [ ] `extractor.py` S3776 functions ≤ 15; no suppressions.
- [ ] Every extracted helper has a focused test; helpers reduce real load (reviewer-judged).
- [ ] `regenerate-graph --check` byte-identical.

## Risks & Reviewer Guidance

- **Risk**: complexity-shuffling into untested no-op helpers. Reviewer: read the extracted helpers
  — do they carry real responsibility and tests, or just relocate branches?
- **Reviewer**: confirm the golden round-trip is green (behavior preserved), not just the number.
