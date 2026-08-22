---
work_package_id: WP04
title: 'Fold #2901 — WP-frontmatter tolerant reader (residual)'
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: rc3-canonical-mission-type-reader-01M0GGWM
merge_target_branch: rc3-canonical-mission-type-reader-01M0GGWM
branch_strategy: Planning artifacts for this mission were generated on rc3-canonical-mission-type-reader-01M0GGWM. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-canonical-mission-type-reader-01M0GGWM unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
phase: Phase 2 - Convergence
history:
- at: '2026-08-22T04:16:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/audit/
create_intent:
- tests/specify_cli/test_wp_frontmatter_fold.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/audit/classifiers/wp_files.py
- src/specify_cli/mission_v1/guards.py
- tests/specify_cli/test_wp_frontmatter_fold.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Fold #2901 — WP-frontmatter tolerant reader (residual)

## Objectives & Success Criteria

- Route the residual divergent WP-frontmatter classification site(s) through the
  **already-landed** tolerant reader `status/wp_metadata.py`
  (`read_wp_frontmatter` / `read_authored_wp_frontmatter_lenient`) — FR-008.
- Pin the already-routed consumers (`bootstrap.py`, `dossier/indexer.py`,
  `sync/history_import/scan.py`) with a parity assertion so the #2884 B3
  "incomplete import reported as success" defect stays closed (AC-6).

## Context & Constraints

- **Verify-first (this fold is mostly landed).** `status/wp_metadata.py` exists
  and three consumers already route through it — do NOT rebuild. Load
  `../research.md` §FR-008.
- **Independent** of the mission-type seam (WP-frontmatter domain).
- **Same-file cross-mission coordination**: in `audit/classifiers/wp_files.py`,
  own **only** the WP-frontmatter reader (`:58` raw `FrontmatterManager().read()`);
  **M6** owns the `_TERMINAL_LANES` constant (`:16`). Different symbols.
- **Out of scope**: `review/prompt_metadata.py` reads *review-prompt* frontmatter,
  not WP frontmatter — do not touch.

## Branch Strategy

- **Merge target branch**: `rc3-canonical-mission-type-reader-01M0GGWM`

## Subtasks & Detailed Guidance

### Subtask T021 – Route audit/classifiers/wp_files.py
- **Steps**: Replace the raw `FrontmatterManager().read()` classification at
  `wp_files.py:58` with the tolerant reader's classification so absent /
  unparseable / schema-invalid frontmatter is handled identically to the landed
  consumers. Preserve the existing finding taxonomy (`UNKNOWN_SHAPE`, legacy-key,
  missing-evidence). Touch only the reader; leave `_TERMINAL_LANES` for M6.

### Subtask T022 [P] – Evaluate mission_v1/guards.py
- **Steps**: `guards.py` uses its own `_read_lane_from_frontmatter` (catches
  `json.JSONDecodeError, OSError`). Determine whether it duplicates the tolerant
  classification; route it if so, else document why it is exempt (guards must
  never raise — a different tolerance contract).

### Subtask T023 [P] – Landed-consumer parity pin
- **Steps**: `tests/specify_cli/test_wp_frontmatter_fold.py` — assert
  `bootstrap.py`, `dossier/indexer.py`, `sync/history_import/scan.py`, and the
  newly-routed `wp_files.py` produce the same skip/classify outcome for a
  malformed/wrong-shape WP `.md` fixture (the #2884 B3 pin: skipped-but-reported,
  never silently counted as success).

## Test Strategy

- `pytest tests/specify_cli/test_wp_frontmatter_fold.py -q`

## Risks & Mitigations

- Scope creep into review-prompt frontmatter — explicitly out of scope.
- Verify-first: three consumers already landed; do not re-route them, only pin.

## Review Guidance

- `wp_files.py` routes through the tolerant reader without changing its finding
  taxonomy; `_TERMINAL_LANES` untouched; guards decision documented; B3 pin present.

## Activity Log

- 2026-08-22T04:16:17Z – system – Prompt created.
