---
work_package_id: WP06
title: Append-promotion primitive (activation_engine)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
phase: Phase 2 - Promotion
shell_pid: "3497995"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/activation_engine.py
create_intent:
- tests/charter/test_append_promotion_primitive.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/charter/activation_engine.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP06
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP06 – Append-promotion primitive (activation_engine)

## Objective
A NEW append primitive in `src/charter/activation_engine.py` that promotes an **arbitrary `{kind: [ids]}` set** into `config.activated_*`. Shared by three consumers: the migration + interview (WP07) and the org-union (WP04) — WP04 needs non-root kinds (tactics/styleguides/toolguides/…), so this is deliberately NOT roots-only. Stays in `charter` (layer rule); maps ids via WP01's `resolve_artifact_urn`.

## Context (three traps the squad pinned — read before coding)
- **C-002 write path (do it right):** `commit_plan` (`:352-387`) is THE single config-write chokepoint and writes exactly ONE `yaml_key` per call. The FR-021 default-pack materialization is a **`plan_activation`** behaviour (`:251-259`), NOT a `commit_plan` behaviour — they are orthogonal. So the primitive builds its own `ActivationPlan(yaml_key, new_list=current+ids)` per kind and calls **`commit_plan` once per yaml_key**. It MUST NOT reuse `plan_activation`'s absent-key branch, and MUST NOT call `save`/`_save_config` directly (that would be a sibling writer → C-002 breach).
- **LAND-BLOCKER — absent-key semantics (`PackContext.from_config` is three-state).** An ABSENT `activated_<kind>` key means **"all built-ins active"** (`pack_context.py:123-129,274-281`). If a first-run promotion writes a bare `activated_directives: [5 stems]` into a previously-absent key, runtime resolution flips from *all built-ins* to *only those 5 (+closure)* — dropping ~19 built-ins, violating the spec `built_in_only` Edge Case + NFR-004/C-005. **Required behaviour:** on an absent key, promotion must PRESERVE the all-built-ins-active semantics (union the built-in set for that kind, THEN append the promoted ids) — never write a bare restrictive set. This is the intended reading of the spec's amended absent-key clarification; pin it with a first-run regression (T022). (The dogfood repo masks this — its keys are present with 25 entries — so it will not surface without a dedicated test.)
- **Circular-import trap.** `activation_engine.py` deliberately has ZERO charter-internal imports (`:50-54`). `YAML_KEY_MAP` lives in `pack_manager.py:120`, and `pack_manager` imports `activation_engine` at module top (`:66`). Importing `YAML_KEY_MAP` from `pack_manager` creates a cycle. Take `yaml_key` **as data**, or derive it via `doctrine.artifact_kinds` the way `pack_manager._yaml_key_for_token` does (`:101-111`).

## Subtasks
- **T021** Add a primitive taking an arbitrary `{kind: [ids]}` set and promoting it into `config.activated_*` APPEND-only via `commit_plan` (one call per yaml_key), mapping ids via WP01. On an absent key, preserve all-built-ins-active (union built-ins then append) — do NOT write a bare restrictive set and do NOT trigger `plan_activation`'s default-pack branch. No `pack_manager.YAML_KEY_MAP` import (avoid the cycle).
- **T022** Tests: (a) promoting a directive+paradigm+styleguide set appends exactly those, idempotent, via `commit_plan` only; (b) **first-run parity** — promoting into an absent key leaves the built-ins for that kind still active (no ~19-directive drop; `PackContext.from_config` resolves identically to the absent-key case for the un-promoted built-ins); (c) no `specify_cli` import (layer rule).

## Branch Strategy
`spec-kitty agent action implement WP06 --agent <name>` (deps WP01; ∥ WP02).

## Definition of Done
- [ ] Arbitrary-kind append primitive in `charter`; writes via `commit_plan` only (no direct `save`, no `plan_activation` default-pack branch); absent-key preserves all-built-ins-active; no circular import.
- [ ] First-run parity test + arbitrary-kind + idempotency tests green; ruff/mypy clean; complexity ≤15; layer rule green.

## Activity Log

- 2026-07-10T15:59:03Z – claude:sonnet:python-pedro:implementer – shell_pid=3466812 – Assigned agent via action command
- 2026-07-10T16:14:24Z – claude:sonnet:python-pedro:implementer – shell_pid=3466812 – New promote_activations() append-only primitive in src/charter/activation_engine.py, accepting an arbitrary {yaml_key: [config-stem ids]} mapping (not roots-only — supports non-root kinds like tactics/styleguides/toolguides for WP04's org-union). Writes exclusively via one commit_plan() call per yaml_key (built on a new private pure planner _plan_promotion, distinct from plan_activation, so the FR-021 default-pack branch is never triggered and save/_save_config is never called directly - C-002 respected). Absent-key parity: when a yaml_key is absent, default_ids (caller-supplied, e.g. discovered built-in ids) are unioned into the plan BEFORE the promoted ids are appended, so PackContext.from_config's three-state absent-key contract (absent == all-built-ins-active) is preserved instead of flipped to a restrictive explicit list - pinned by test_promote_into_absent_key_preserves_all_builtins_active and test_promote_into_absent_key_never_writes_bare_restrictive_list, both exercising real PackContext.from_config resolution. No circular import: yaml_key is taken as data from the caller (mirrors plan_activation/plan_deactivation's existing yaml_key parameter) rather than re-deriving it from pack_manager.YAML_KEY_MAP, so activation_engine.py keeps zero charter-internal imports; pinned by a new AST-based layer-rule test (no specify_cli/charter/pack_manager import). 8 new tests in tests/charter/test_append_promotion_primitive.py all green; full tests/charter/ suite (1473 tests) green; tests/architectural/test_layer_rules.py green; ruff + mypy clean on both changed files; complexity well under 15 (two small functions, no nested branching).
- 2026-07-10T16:14:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=3497995 – Started review via action command
- 2026-07-10T16:20:20Z – user – shell_pid=3497995 – All 3 squad traps verified closed against real diff (commit d14cde3be), not the summary. C-002: promote_activations builds pure _plan_promotion then calls commit_plan once per yaml_key (activation_engine.py:465-471); no direct save/_save_config, plan_activation absent-key branch not reused; test_promote_arbitrary_kinds_writes_via_commit_plan_only counts exactly one write/key. Absent-key LAND-BLOCKER: _plan_promotion:435 unions caller default_ids THEN appends; test_promote_into_absent_key_preserves_all_builtins_active is NON-VACUOUS - asserts through REAL PackContext.from_config (frozenset d1,d2,d3,d4), and since _read_list_key returns the literal present-key set, a bare [d4] write would resolve to frozenset(d4) and fail. default_ids caller-supplied (correct C-008, keeps built-in discovery out of the charter layer); docstring documents a key absent from default_ids writes a bare set, so WP04/WP07 MUST pass the real built-in set or the guard is inert - that caller obligation is documented, out of WP06 scope. Cycle guard: module imports only stdlib (zero charter-internal), yaml_key as data; AST test guards specify_cli AND charter AND pack_manager roots (stronger than claimed). Scope: WP06 commit touches only the 2 owned files (other lane files are merged-in WP01 dep). Idempotency+dedup genuinely tested. Gates green: 8/8 promotion tests, 16/16 layer_rules, ruff+mypy clean, C901<=15. No production caller yet - intended foundation primitive for dependents WP04/WP07, not dead code.
