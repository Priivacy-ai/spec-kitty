---
work_package_id: WP02
title: Content-identity recipe — swap references.yaml → directive digest, fail-safe
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-005
- FR-007
- NFR-001
- NFR-003
- C-003
tracker_refs: []
planning_base_branch: gk/2758-2759
merge_target_branch: gk/2758-2759
branch_strategy: Planning artifacts for this mission were generated on gk/2758-2759. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into gk/2758-2759 unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
phase: Phase 2 - Recipe
assignee: ''
agent: ''
history:
- timestamp: '2026-07-17T13:20:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
create_intent: []
execution_mode: code_change
mission_id: 01KXR0M1FQTBPSQ8S2GNM6K7XZ
authoritative_surface: src/charter/bundle.py
owned_files:
- src/charter/bundle.py
- tests/charter/test_bundle_content_hash.py
- tests/specify_cli/charter_freshness/test_computer.py
tags: []
wp_code: WP02
---

# Work Package Prompt: WP02 – Content-identity recipe: swap references.yaml → directive digest, fail-safe

## Objectives & Success Criteria

- `BUNDLE_CONTENT_HASH_FILES` = `("governance.yaml", "directives.yaml", "metadata.yaml")` (drop
  `references.yaml`) → a missing/pruned `references.yaml` can no longer force `None`/permanent stale (#2758).
- `compute_bundle_content_hash` appends a **directive-activation digest** =
  `hash_content("directives=" + ",".join(sorted(resolve_synthesis_graph_directives(repo_root))))` before the
  final combine → directive activation moves the hash (#2759).
- The compiler import is **function-local** (NFR-001); the resolver read is wrapped so resolver exceptions →
  `None` (NFR-003/OQ-4). Reader/`promote`/`resynthesize` unchanged (single-recipe propagation, FR-004).

## Context & Constraints

- Read `plan.md` (IC-02, OQ-1/3/4/5) + `data-model.md` (recipe + fail-posture matrix). Ground truth is
  `src/charter/bundle.py:47,133-184`.
- **C-003**: edit ONLY `BUNDLE_CONTENT_HASH_FILES`; do NOT touch `computer._BUNDLE_FILES` (computer.py:137,
  the separate `synced_bundle` signal).
- Preserve the per-file recipe (BOM-strip/CRLF via `hash_content`) for the remaining triad.
- Never-raise contract (bundle.py:160) is absolute — the new resolver read must not break it.

## Subtasks & Detailed Guidance

### T003 — (RED-FIRST) Recipe unit tests
- New/extended `tests/charter/test_bundle_content_hash.py` + flip the landed
  `tests/specify_cli/charter_freshness/test_computer.py::test_synthesized_drg_stale_when_a_bundle_file_is_missing`:
  1. Missing `references.yaml` (present triad + directives) → `compute_bundle_content_hash` returns a real
     hash (NOT `None`); and via the reader, `synthesized_drg` is NOT stale on that account (#2758 flip).
  2. Change the resolved directive set (add/remove an activated directive) → hash changes.
  3. No-op (resolved directive set unchanged) → hash stable.
  4. Drifted activated stem (config references an id absent from the catalog → `UnknownArtifactIdError`) →
     `compute_bundle_content_hash` returns `None` (does NOT raise).
  5. Malformed `config.yaml` (`CharterPackConfigError`) → `None` (does NOT raise).
  6. Existing BOM/CRLF/non-UTF-8 guards remain green for the triad.
  - Commit RED first.
- **Files**: `tests/charter/test_bundle_content_hash.py`, `tests/specify_cli/charter_freshness/test_computer.py`.

### T004 — Implement the recipe change
- **Steps**:
  1. `BUNDLE_CONTENT_HASH_FILES` → drop `references.yaml` (triad only). Update the module docstring/comments
     (the `references.yaml` rationale block) to reflect the new set.
  2. In `compute_bundle_content_hash`, after the per-file digest loop, add the directive digest:
     ```python
     try:
         from charter.compiler import resolve_synthesis_graph_directives  # function-local (NFR-001)
         directives = resolve_synthesis_graph_directives(repo_root)
     except (UnknownArtifactIdError, CharterPackConfigError, ValueError, OSError, UnicodeDecodeError):
         return None  # never-raise (bundle.py:160): a read that can't prove fresh → None → recoverable stale
     digests.append(hash_content("directives=" + ",".join(sorted(directives))))
     ```
     (import the exception types function-locally too; keep the catch scoped to the resolver read, not the
     per-file loop.) Then combine as today.
  3. Run `pytest tests/charter/test_bundle_content_hash.py tests/specify_cli/charter_freshness/test_computer.py -q` → GREEN.
- **Files**: `src/charter/bundle.py`.
- **Notes**: inline rationale comment for the (necessarily broad-ish) resolver catch citing the never-raise
  contract; `ruff`/`mypy --strict` clean, no new suppressions.

## Validation
- `PWHEADLESS=1 pytest tests/charter/test_bundle_content_hash.py tests/specify_cli/charter_freshness/test_computer.py -q`
- `ruff check src/charter/bundle.py && mypy src/charter/bundle.py`
- Confirm no edit to `computer._BUNDLE_FILES` (C-003).

## Dependencies
- WP01 (the shared helper).
