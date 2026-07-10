---
work_package_id: WP02
title: IC-01 derivation source switch (both paths)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T026
phase: Phase 2 - Derivation
shell_pid: "3536553"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/compiler.py
create_intent:
- tests/charter/test_config_sourced_derivation.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- src/charter/compiler.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- src/specify_cli/cli/commands/charter/generate.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP02
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP02 – IC-01 derivation source switch (both paths)

## Objective
Repoint the compiled-reference-set + graph derivation from `answers.selected_*` to `config.activated_*` (via the WP01 resolver), in BOTH derivation paths the squad found:
1. `src/charter/compiler.py` — `compile_charter`/`_build_references` (`:84-149`) reads `interview.selected_paradigms/directives/tactics` → the references.yaml roots.
2. `src/specify_cli/cli/commands/charter/_synthesis.py` (`:41-70`) — builds interview_snapshot/drg_snapshot from `answers.selected_*` → the project graph layer.
Plus `generate.py` (`:294-300`) which calls `compile_charter`.

## Context
- **CRITICAL (squad LAND-BLOCKER — direct roots, not just directives+paradigms).** `_build_references_from_service` (`compiler.py:428-535`) sources directives via directive-DRG closure and paradigms via a direct YAML scan, but tactics/styleguides/toolguides/procedures come **exclusively** from directive-closure. Two of the three #2524 baseline danglers — `aggregate-design-rules` (styleguide) and `contextive` (toolguide) — are activated **directly** in `config.activated_styleguides`/`activated_toolguides` and are reachable from **no** directive (graph-BFS confirmed). So sourcing only `{directives, paradigms}` roots leaves them dangling and makes WP03's shrink-to-empty impossible. **You MUST add a direct-root path** that reads `config.activated_styleguides`/`activated_toolguides` (and, for the WP04 org-union, the remaining directly-activatable kinds: tactics, procedures, agent_profiles) as additional roots into `_build_references_from_service`, analogous to the existing paradigm direct-load — union them with the closure result. This same capability is what WP04's org-required non-root kinds depend on.
- **CRITICAL (squad — close the actual silent-drop seam, not just swap the source).** Today `_sanitize_catalog_selection` (`compiler.py:292-324`, called at `:109-132` before `_build_references`) appends an unrecognized stem to `missing`, emits an info diagnostic, and **drops it — the compile continues.** That IS the C-006 silent-drop vector. Routing config through it upstream leaves the drop intact. Route config-sourced stems through WP01's **raising** `resolve_artifact_urn` **in place of / bypassing** the lenient sanitizer for the config path, so an unresolvable stem raises.
- Paradigms remain selection-only (NOT DRG-reachable). Layer rule: config-read + mapping lives in `charter`; `_synthesis.py`/`generate.py` (specify_cli) orchestrate. Scope `selected_*` edits **by module**, not by token grep — `governance.yaml doctrine.selected_*` (ledger C) shares the token and must NOT be swept.

## Subtasks
- **T005** `compiler._build_references_from_service`: source directive + paradigm roots from config.activated_* (via WP01 `resolve_artifact_urn`), not `interview.selected_*`; route config stems through the raising resolver, **not** the lenient `_sanitize_catalog_selection` drop.
- **T006** compiler charter.md render (`:814-921`): source displayed selections from config.
- **T007** `_synthesis.py`: build interview_snapshot/drg_snapshot roots from config.activated_*.
- **T008** `generate.py`: wire the compile path to the config-sourced derivation (interview object no longer the activation source).
- **T009** Tests: compiler + synthesis emit the config-sourced set; assert an unresolvable config stem RAISES (no silent drop).
- **T026** Direct-root inclusion: `_build_references_from_service` reads `config.activated_styleguides`/`activated_toolguides` (and the remaining directly-activatable kinds) as additional roots unioned with the closure, so directly-activated non-directive-reachable artefacts (`aggregate-design-rules`, `contextive`) resolve. Test: a directly-activated styleguide with no directive edge resolves in the compiled set.

## Branch Strategy
`spec-kitty agent action implement WP02 --agent <name>` (deps WP01).

## Definition of Done
- [ ] Both derivation paths read config; directly-activated styleguides/toolguides (+ direct kinds) resolve via the new direct-root path; ruff+mypy clean; layer rule green.
- [ ] Unresolvable config stem RAISES (silent-drop seam closed); unit tests prove config-sourced roots; the committed-artefact regen is WP03.

## Activity Log

- 2026-07-10T15:58:54Z – claude:sonnet:python-pedro:implementer – shell_pid=3466812 – Assigned agent via action command
- 2026-07-10T16:30:55Z – claude:sonnet:python-pedro:implementer – shell_pid=3466812 – Both derivation paths (compiler.py references.yaml + _synthesis.py project-graph) now read config.activated_* via WP01 resolve_artifact_urn; generate.py wires PackContext explicitly. T026 direct-root path added for tactics/styleguides/toolguides/procedures/agent_profiles, unioned with directive closure -- verified against this repo's real .kittify/config.yaml that the #2524 baseline danglers (aggregate-design-rules, contextive, domain-driven-design) now resolve (test_dangling_baseline_is_shrink_only fails as expected; shrinking it is WP03's T012). Unresolvable config stem raises UnknownArtifactIdError (reject-not-drop), closing the C-006 seam _sanitize_catalog_selection left open. New tests/charter/test_config_sourced_derivation.py (13 tests) green; ruff+mypy clean on all 4 changed/created files (1 pre-existing unrelated mypy untyped-decorator note on generate.py:204, confirmed present before this change). Full tests/charter/ suite: 1472 passed, 6 failed -- all 6 are the expected, in-scope consequence of retiring answers.selected_* as an activation source (FR-001/FR-002): test_compiler.py x4 + test_generator.py x1 + test_charter_context_spdd_reasons.py x1 assert interview-driven selections/diagnostics that this WP intentionally repoints to config; none are owned_files for WP02 so left unfixed per instructions.
- 2026-07-10T16:32:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=3536553 – Started review via action command
- 2026-07-10T16:42:22Z – user – shell_pid=3536553 – PASS. Both derivation paths switched to config.activated_* via WP01 resolve_artifact_urn: compiler.py compile_charter/_build_references_from_service (references.yaml) + _synthesis.py interview_snapshot/drg_snapshot + generate.py passes PackContext.from_config explicitly. interview.selected_* inert on activation path (only retained in _user_profile_reference, correct-by-design: that doc renders answers.yaml as the interview record). LAND-BLOCKER 1 (T026 direct roots) CLOSED: _direct_root_urns unions styleguides/toolguides/tactics/procedures/agent_profiles into _resolve_transitive_reference_graph start_urns; tests prove real #2524 danglers aggregate-design-rules + contextive resolve with NO directive edge, plus additive-union test. LAND-BLOCKER 2 (silent-drop seam) CLOSED: config stems route through raising resolve_artifact_urn, bypassing lenient _sanitize_catalog_selection (now only used for available_tools); 3 tests prove unresolvable config stem RAISES UnknownArtifactIdError. Gates: 13/13 new tests pass, ruff clean, mypy clean (generate.py:204 untyped-decorator pre-existing typer limitation), layer_rules 16/16, charter imports no specify_cli, C901 complexity <=15. _render_kind_references collapse + agent_profile branch + ConfigActivatedRoots justified by T026, tested; WP02 commit touches only its 4 files. The 6 charter-suite failures (test_compiler.py x4, test_generator.py x1, test_charter_context_spdd_reasons.py x1) are genuinely STALE-BY-DESIGN answers-sourced assertions (spot-checked 3) that FR-001/FR-002 intentionally retired; NOT owned by WP02; re-pin assigned to WP03. 1472 passed full-suite.
