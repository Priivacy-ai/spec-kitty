---
work_package_id: WP05
title: '#2139 target_branch reconcile (all readers)'
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "194257"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/test_target_branch_reconcile.py
execution_mode: code_change
owned_files:
- src/specify_cli/context/resolver.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- src/specify_cli/missions/_resolve_planning_branch.py
- src/specify_cli/retrospective/reader.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- tests/specify_cli/test_target_branch_reconcile.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your agent profile via `/ad-hoc-profile-load` for `python-pedro` (implementer). Then read
`kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-008), `plan.md` (IC-05), and `research.md`
(D-03 + census expansion).

## Objective

Finish the `#2139` strangler: route **all ≥9 non-migration** `target_branch` readers onto the existing
single authority `read_target_branch_from_meta` (`core/paths.py:655`), and delete the divergent
`"main"`/`""`/`None` silent defaults so every reader shares one fail-closed behavior. This is a **sibling
reconcile, not a resolver method** — do not add `target_branch` to the `MissionResolver`.

## Whack-a-field warning
The plan's original "4 readers" undercounts. Route **all** non-migration readers or **explicitly triage**
the ones you leave. Three divergent absent-value contracts coexist (`"main"`, `""`, hard `KeyError`) —
reconcile them onto the authority's contract, don't leave a partial fix.

## Subtasks

### T021 — Route the readers onto `read_target_branch_from_meta`
Route these to the authority (which already fail-closes on corruption):
- `context/resolver.py:82` (`get("target_branch", "main")`)
- `retrospective/generator.py:1263` (`or "main"`)
- `cli/commands/agent/mission_branch_context.py:63` (`get("target_branch", "")`)
- `missions/_resolve_planning_branch.py:80`
- `retrospective/reader.py:303`, `retrospective/writer.py:398` (`get("target_branch", "")`)
- `acceptance/__init__.py:1075`, `:1696` (`get("target_branch")` → `None`)
- `cli/commands/agent/tasks_parsing_validation.py:751`
Each should call the authority and stop re-embedding a local default.

### T022 — Delete divergent defaults; triage the KeyError reads
- Remove the `"main"`/`""`/`None` fallbacks at the sites above.
- **Triage** the hard-`KeyError` dataclass-hydration reads (`context/resolver.py:236/269`,
  `context/models.py:83`, `lanes/models.py:200`): these are a *different contract by design*
  (construction-time, must-be-present). Leave them **OUT** with a one-line rationale comment — do NOT
  route them through the optional-read authority. (`context/models.py`/`lanes/models.py` are NOT in this
  WP's owned_files — only annotate the two `context/resolver.py` reads you own; note the model reads as
  OUT in the review.)

### T023 — Characterization test
- New `tests/specify_cli/test_target_branch_reconcile.py`: for a `meta.json` missing `target_branch`, every
  routed reader now exhibits the authority's single behavior (fail-closed / documented default), and none
  silently returns `"main"`/`""`. Assert against realistic meta fixtures.

## Branch Strategy
Planning branch and merge target: `feat/mission-resolver-port-2173`. Lane worktree per `lanes.json`.

## Definition of Done
- All owned readers route through `read_target_branch_from_meta`; no `get("target_branch", "main"/"")` in
  owned files.
- KeyError model reads triaged OUT with rationale.
- Characterization test green; `ruff`/`mypy` clean.

## Risks / reviewer guidance
- Reviewer greps owned files for residual silent defaults.
- Confirm no behavior change where a default was legitimately load-bearing (assert via the test).
- Sonar census on touched files; fold SAFE trivia.

## Activity Log

- 2026-07-08T19:10:14Z – claude:sonnet:python-pedro:implementer – shell_pid=4187596 – Assigned agent via action command
- 2026-07-08T19:46:20Z – claude:sonnet:python-pedro:implementer – shell_pid=4187596 – Verified+finished prior implementer's uncommitted diff: all 9 non-migration target_branch readers routed onto read_target_branch_from_meta (context/resolver.py:82, retrospective/generator.py:1263, mission_branch_context.py:63, missions/_resolve_planning_branch.py:80 [triaged OUT, already fail-closes via PlanningBranchResolutionFailed], retrospective/reader.py:303+writer.py:398 [triaged OUT, persisted-record dataclass hydration not a meta.json reader], acceptance/__init__.py:1075+1696, tasks_parsing_validation.py:751). Triaged OUT per spec: context/resolver.py:236/269 hard-KeyError dataclass hydration reads. Added tests/specify_cli/test_target_branch_reconcile.py (T023, 4 behavioral tests). Fixed 2 real regressions in the uncommitted diff: _read_meta_json's new repo_root param broke tests/context/test_mission_resolver.py (2 call sites updated); mission_branch_context.py's removed _read_feature_meta import broke 3 tests in test_mission_branch_context.py (updated to patch read_target_branch_from_meta). Fixed 2 new mypy no-any-return regressions (str(...) cast, precedent core/paths.py:723). ruff: 0 issues on all touched files. mypy on touched src files: 0 new issues (5 pre-existing acceptance/__init__.py errors remain, unrelated to target_branch, same as HEAD just shifted line numbers). 422 tests green across touched-module suites + new characterization suite.
- 2026-07-08T19:47:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=194257 – Started review via action command
- 2026-07-08T19:53:22Z – user – shell_pid=194257 – Review passed (reviewer-renata): real reconcile, not whack-a-field. 6 readers ROUTED onto read_target_branch_from_meta (context/resolver.py:82 + retrospective/generator.py:1263 with resolve_primary_branch fallback replacing the 'main' literal; mission_branch_context.py:63 with current-branch degradation preserved; acceptance:1075/1696 via thin _target_branch_for_feature adapter returning None; tasks_parsing_validation.py:751 with planning_base_branch precedence kept). No residual get('target_branch','main'/'') in any routed owned file. All 4 triage-OUT decisions verified SOUND & genuinely divergent contracts: (1) resolver.py:236/269 hard-KeyError reads of the internally-hydrated meta dict (always populated) - construction-time hydration, not a meta.json field read; (2) _resolve_planning_branch.py:80 is a pure Mapping->str transform that ALREADY fail-closes via PlanningBranchResolutionFailed (no silent default) and diverges on merge_target_branch alias + type-strict isinstance - routing would drop the alias and break type-strict tests; conforms to FR-008 spirit; (3) reader.py:303 & (4) writer.py:398 deserialize PERSISTED retrospective records (schema-wide '' default, no feature_dir at boundary) - routing to live meta.json would be a semantic regression. Characterization test uses non-main 'trunk-integration' discriminator through real production paths (4 passed) so a stray 'main'/'' fails the assertion; ruff exit 0; mypy casts precedented (core/paths.py:723), sole remaining no-any-return at mission_branch_context.py:357 is PRE-EXISTING on base (unrelated). Anti-pattern checklist: all PASS/N-A.
