---
work_package_id: WP08
title: Language tier-3 fallback migration (charter.md prose → catalog.languages)
dependencies:
- WP03
requirement_refs:
- FR-009
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/language_scope.py
- tests/charter/test_language_scope.py
role: implementer
tags: []
shell_pid: "490282"
shell_pid_created_at: "1784385324.63"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Migrate the **one behavioral** `charter.md`-prose read — the doctrine language-scoping tier-3 fallback — off prose to the structured `catalog.languages`, so `charter.md` is behaviorally inert (no decision reads it). Independent P2.

**Authoritative**: [`plan.md`](../plan.md) IC-08; the empirical trace flagged this as the sole behavioral prose read.

## Context / grounding
- `language_scope.py:44 _read_compiled_languages` (reads **references.yaml** `languages` — tier-1, authoritative), `:77-105` precedence, `:101-103 infer_repo_languages` tier-3 (reads `charter.md` free-text — the fallback). Result feeds `active_languages` → `applies_to_languages_match` (`shared/scoping.py:62-69`), a real gate.

## ⚠ Both tiers repoint (paula MINOR-5)
This WP repoints **BOTH** reads, not just tier-3: `_read_compiled_languages:44` currently reads `references.yaml`, which WP07 deletes — so tier-1 breaks unless re-pointed to `charter.yaml.catalog.languages`.

## Subtasks
### T032 — tier-1 `_read_compiled_languages` → catalog.languages
- Re-point `_read_compiled_languages:44` from `references.yaml` to `charter.yaml`'s `catalog.languages` (this is the authoritative tier-1 source post-inversion).
### T033 — tier-3 fallback → catalog.languages (drop the charter.md prose read)
- Replace the tier-3 `charter.md` free-text read (`infer_repo_languages:101-103`) with the structured `catalog.languages` (or drop tier-3 if tier-1 always covers it). No `charter.md` prose read remains. Keep the tier-1/tier-2 precedence semantics unchanged.
### T034 — Tests
- `tests/charter/test_language_scope.py`: language scoping resolves from `catalog.languages`; assert NO `charter.md` read feeds `applies_to_languages_match`.

## ATDD (red-first)
Red-first: assert `infer_repo_languages` resolves languages without reading `charter.md` (RED until T032).

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP03 — needs `catalog.languages`); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- No `charter.md` prose read in language scoping; tier-1 precedence preserved; ruff + mypy --strict clean; complexity ≤15; owned test green.

## Reviewer guidance
- Verify `charter.md` is no longer read for language resolution (INV-3 completeness); verify tier-1 precedence unchanged.

## Activity Log

- 2026-07-18T14:18:21Z – claude:sonnet:python-pedro:implementer – shell_pid=453423 – Assigned agent via action command
- 2026-07-18T14:35:07Z – claude:sonnet:python-pedro:implementer – shell_pid=453423 – language scoping tier-1+tier-3 read charter.yaml catalog.languages; no charter.md prose read. Gates foreground (orchestrator-run): ruff clean, mypy --strict clean, 43 passed. (Implementer backgrounded its gate run + stalled; finished by orchestrator.)
- 2026-07-18T14:35:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=490282 – Started review via action command
- 2026-07-18T14:38:28Z – user – shell_pid=490282 – FR-009/INV-3 met: no charter.md prose read remains in language_scope.py (only docstring mentions); tier-1 now reads charter.yaml catalog.languages via CHARTER_YAML+load_charter_yaml, tier-2 interview precedence + graceful None/empty preserved. extract_declared_languages still live (compiler.py, interview_mapping.py, tier-2). Leeway edit tests/charter/test_context.py assessed: genuinely unowned (WP05 owns context.py + test_context_display_charter_md.py, not test_context.py), mechanical fixture repoint references.yaml->charter.yaml catalog.languages, minimal. Gates green: ruff clean, mypy --strict clean, 43 passed (4 CharterCatalogMissWarning pre-existing noise), C901<=15.
