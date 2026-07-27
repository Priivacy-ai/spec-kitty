---
work_package_id: WP03
title: IC-01 consequence - regenerate committed artefacts + baseline shrink
dependencies:
- WP02
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: epic/2519-charter-authoring-lifecycle
merge_target_branch: epic/2519-charter-authoring-lifecycle
branch_strategy: Planning artifacts for this mission were generated on epic/2519-charter-authoring-lifecycle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into epic/2519-charter-authoring-lifecycle unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T027
- T028
phase: Phase 2 - Derivation
shell_pid: "3656705"
history:
- timestamp: '2026-07-10T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: .kittify/charter/
create_intent:
- tests/charter/test_activate_resolves_no_answers_edit.py
execution_mode: code_change
mission_id: 01KX5SJ9P0HXTVWZDJ121JBP60
owned_files:
- .kittify/charter/references.yaml
- src/doctrine/graph.yaml
- tests/architectural/test_charter_references_resolve.py
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:opus:reviewer-renata:reviewer"
model: claude-sonnet-5
wp_code: WP03
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned profile:
```
/ad-hoc-profile-load python-pedro
```
Do not touch code until the profile is loaded and acknowledged.
# WP03 – Regenerate committed artefacts + baseline shrink

## Objective
Config-sourcing is a SUPERSET (adds the 8 config paradigms + direct styleguides/toolguides that the answers path produced zero of), so the committed `references.yaml` + `graph.yaml` change content and MUST be regenerated + re-committed, the shrink-only dangler baseline shrunk to empty, and the #2524 regression pinned (spec C-008, FR-004, SC-001).

## Context
- After WP02, regenerate via the canonical commands (`charter generate`/`synthesize` + `generate_graph`), don't hand-edit.
- `test_dangling_baseline_is_shrink_only` (`test_charter_references_resolve.py:247-260`) asserts the 3 baseline tokens (domain-driven-design, aggregate-design-rules, contextive) STILL dangle. **Shrink-to-empty depends on WP02's T026 direct-root fix** — `domain-driven-design` resolves via the paradigm root switch, but `aggregate-design-rules`/`contextive` resolve ONLY if WP02 reads config-activated styleguides/toolguides directly (they are reachable from no directive). If WP02 T026 landed, shrink to `{}`; if it did not, this WP is blocked (do NOT hand-edit references.yaml to fake resolution). The dangler-test helper `_compiled_reference_id_suffixes()` (`:170-190`) drives `compile_charter(interview=…)` — its call shape changes with the source switch; update it.
- **SPDD flip guard (squad D1).** `generate.py:314` runs `sync_charter` right after compile; the compiler's `## Governance Activation` render (`compiler.py:872-885`) feeds `governance.yaml doctrine.selected_*`, which the SPDD gate keys on (`spdd_reasons/activation.py:132-141`, e.g. `DIRECTIVE_038`). A config-sourced superset can spuriously flip SPDD auto-activation — pin a regression that it does not.

## Subtasks
- **T010** Regenerate `.kittify/charter/references.yaml` from config; confirm it now includes the config paradigms + direct styleguides/toolguides.
- **T011** Regenerate `src/doctrine/graph.yaml`; the `generate_graph` freshness gate stays green.
- **T012** Shrink `test_dangling_baseline_is_shrink_only` to empty (baseline set → {}); fix the dangler-test helper's `compile_charter` call shape for the config source.
- **T013** New regression test: `charter activate <kind> <id>` → the artefact resolves in the compiled set with NO `answers.yaml` edit (the #2524 class), and `test_no_new_charter_reference_danglers` stays green. Add its **symmetric twin** (T027 below) OR keep both in this test: activate-resolves AND deactivate-drops.
- **T027** Deactivate-drops regression (spec Acceptance Scenario 2, uncovered): `charter deactivate <kind> <id>` → the artefact no longer resolves in the compiled set, NO `answers.yaml` edit, no dangling reference remains. Plus the SPDD-no-flip assertion: config-sourcing does not flip `governance.yaml doctrine.selected_*` / SPDD auto-activation on the dogfood charter.
- **T028 (stale-test re-pin — rationale-backed OUT-OF-MAP edit).** WP02's source switch made 6 existing charter tests fail because they assert the RETIRED answers-sourced behaviour: `tests/charter/test_compiler.py` (×4), `tests/charter/test_generator.py` (×1), `tests/charter/test_charter_context_spdd_reasons.py` (×1). No WP owns these files, and they are a direct consequence of the WP02/WP03 source switch this WP completes — so re-pin them HERE. Per the test-remediation framework: JUDGE each test — if it asserts a genuine invariant, re-pin it to the config-sourced expectation (edit the assertion/fixture to feed `config.activated_*`, not `interview.selected_*`); if it only exercised the now-dead answers path, delete it with a one-line rationale. Do NOT weaken assertions to pass. Record a one-line rationale per edited file in the commit. (This is an accepted out-of-map edit: the no-overlap guard holds — WP04/WP05 do not touch these test files.)

## Branch Strategy
`spec-kitty agent action implement WP03 --agent <name>` (deps WP02).

## Definition of Done
- [ ] references.yaml + graph.yaml regenerated + committed; freshness gate green.
- [ ] Shrink-only baseline empty (contingent on WP02 T026); dangler + activate-resolves + deactivate-drops + SPDD-no-flip regressions green.
- [ ] The 6 stale answers-sourced charter tests re-pinned to config-sourced (or deleted with rationale); `uv run pytest tests/charter/ -q` green.

## Activity Log

- 2026-07-10T17:34:53Z – claude – T010: references.yaml regenerated via canonical compile_charter/_write_references_yaml (repo_root pinned to lane worktree -- find_repo_root() redirects worktree cwd to primary, a landmine flagged in the PR). Superset-only diff (+8 config paradigms, direct-root styleguides/toolguides/tactics/procedures/agent-profiles), zero removals, charter.md untouched (byte-identical). T011: graph.yaml already fresh from WP02, regenerate --check green, no diff. T012: PRE_EXISTING_DANGLING_BASELINE shrunk to {} -- domain-driven-design/aggregate-design-rules/contextive all resolve now. T013/T027: new tests/charter/test_activate_resolves_no_answers_edit.py pins activate-resolves + deactivate-drops (#2524 class, no answers.yaml edit either way) + SPDD-no-flip on the dogfood charter. T028: judged the 6 WP02-broken tests -- 3 deleted (retired answers-sourced paths with equivalent/stronger coverage elsewhere, or now-dead Lynn Cole alias flagged as a follow-up gap), 3 re-pinned to config-sourced PackContext-driven equivalents. Evidence: tests/architectural/test_charter_references_resolve.py 4/4 green baseline-empty; full tests/charter/ -q 1480 passed; ruff clean on all changed files. Full tests/architectural/ sweep: 845 passed/1 pre-existing failure (test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported on charter.compiler::ConfigActivatedRoots) reproduced identically with this WP's diff stashed out -- a WP02 dead-symbol regression outside WP03 owned_files, reported not fixed. Also flagging for reviewer: running 'spec-kitty charter generate --force' from inside a lane worktree writes to the PRIMARY repo checkout instead (find_repo_root() intentionally redirects worktrees to main for mission-bookkeeping reasons but this breaks charter generation); worked around via explicit repo_root injection, did not hand-edit YAML.
- 2026-07-10T17:36:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=3656705 – Started review via action command
- 2026-07-10T17:46:14Z – user – shell_pid=3656705 – PASS. references.yaml is a clean SUPERSET (1097 additions, only generated_at timestamp changed, ZERO content removals) and byte-identical to an independent canonical re-derivation via compile_charter+_write_references_yaml — canonically produced, not hand-crafted. Baseline shrunk to frozenset(); 4/4 test_charter_references_resolve pass non-vacuously (the 3 real danglers domain-driven-design/aggregate-design-rules/contextive now resolve). New test_activate_resolves_no_answers_edit drives the actual charter activate/deactivate CLI + compile_charter (config.yaml-only mutation, target absent-before proves observability) and SPDD-no-flip asserts is_spdd_reasons_active stays True post config-sourced compile. T028 per-file verdicts all sound: DELETE preserves_explicit_empty_selections (retired answers-empty path; replaced by STRONGER config-wins tests test_compiled_paradigms_come_from_config_not_interview + test_no_pack_context_defaults_to_all_builtins_active — both verified present); DELETE unknown_directive_in_diagnostics (interview path retired; replaced by STRONGER fail-closed test_unresolvable_config_directive_stem_raises); DELETE lynn_cole_verbatim (verified genuinely dead-effect — compile_charter reads config_roots for activation and discards the alias's interview mutation; flagged as follow-up gap in commit+in-file NOTE); RE-PIN missing_shipped_graph STRENGTHENED (keeps original transitive-tactic-does-not-resolve assertion AND adds direct-config-activated-tactic-surfaces); RE-PIN build_charter_draft_defaults (source flip interview-default->config absent-key all-builtins; assertion strengthened to exact catalog equality); RE-PIN spdd round-trip (source interview->PackContext, full is_spdd_reasons_active endpoint preserved). No assertions weakened to pass. Scope clean: references.yaml + 5 test files, ZERO src/ changes. Gates: test_charter_references_resolve 4 passed; T028+new charter tests 74 passed; ruff clean. Pre-existing charter.compiler::ConfigActivatedRoots dead-symbol failure confirmed WP02-origin (commit 79c7921e7), WP03 touches no src/ — genuinely pre-existing, WP05-assigned, not a WP03 blocker. Carry-forward (non-blocking): Lynn Cole alias is now dead code and untested post-deletion; the flagged follow-up should become a tracked ticket.
