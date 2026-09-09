---
work_package_id: WP01
title: Mission-DSL v1 Retirement (FULL) + transitions Drop
dependencies: []
requirement_refs:
- C-004
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1TZVN
base_commit: 1ceba9f2259968b99f5bb85cdc56e38c92622489
created_at: '2026-09-06T18:33:02.557753+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Wave 0 - DSL retirement (mission bulk)
agent: claude
history:
- at: '2026-09-06T12:40:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/mission_v1/
create_intent:
- tests/specify_cli/mission_v1/test_import_hygiene.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/mission_v1/**
- src/specify_cli/mission.py
- src/specify_cli/review/gate_registry.py
- src/specify_cli/skills/manifest_store.py
- packs/built-in/missions/software-dev/mission.yaml
- packs/built-in/missions/plan/mission.yaml
- packs/built-in/missions/research/mission.yaml
- pyproject.toml
- uv.lock
- CHANGELOG.md
- tests/specify_cli/mission_v1/**
- tests/missions/**
- tests/research/test_research_plan_missions_integration.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_gate_coverage.py
- tests/specify_cli/test_wp_frontmatter_fold.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Mission-DSL v1 Retirement (FULL) + `transitions` Drop

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (`spec-kitty agent tasks status --mission dead-port-disposition-01M1TZVN`). Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Story 1 (P1), the mission's bulk. **Mission-level gate (C-001)**: this WP is claimed only after Mission A has merged into the branch (the orchestrator enforces it; if you find Mission A WPs not `done`, stop and report).

Done means:

- **SC-001**: `tests/specify_cli/mission_v1/test_import_hygiene.py` (new) proves in an isolated subprocess that `import specify_cli.mission_v1.events` leaves `transitions` and `six` out of `sys.modules`. RED on the base, GREEN after, kept permanently.
- **SC-002**: `transitions` is gone from `pyproject.toml` (line 82 today) and `uv.lock` (regenerated with `uv lock`, never hand-edited); `six` remains via `python-dateutil`; `tests/architectural/test_pyproject_shape.py` green; clean-install smoke green.
- **SC-003**: zero `import transitions` / `from transitions import` in `src/` (today: `mission_v1/runner.py:15-16`, `mission_v1/compat.py:23`); ~1,190 LOC retired (FULL: `compat.py` 158, `runner.py` 252, `guards.py` 382, `schema.py` 299, plus ~120 of `__init__.py`'s 154); `events.py` (93 LOC) byte-identical; the two live consumers (`runtime/next/next_invocation_lifecycle.py:332`, `runtime/next/decision.py:200`) pass their tests unchanged.
- **NFR-003 / C-005**: every gate touched moves in this WP: dead-symbol pins at `tests/architectural/test_no_dead_symbols.py:720-727` (3) **and** `:3278` (`mission_v1.schema::strip_v1_keys`, missed by the spec), fold-gate entry `tests/specify_cli/test_wp_frontmatter_fold.py:60`, `_gate_coverage.py:1456` row verified, runtime ledger row `test_layer_rules.py:194` verified to stay.
- **FR-007 / OD3**: the orphan `states:`/`transitions:` blocks are deleted from the three built-in `mission.yaml`s; `MISSION_COMPAT_IGNORED_FIELDS` (`src/specify_cli/mission.py:59-67`, `:260-261`) stays with an updated comment.
- CHANGELOG entry under `## [Unreleased] - 3.2.7rc1`; no version bump.

## Context & Constraints

- Spec US1, FR-001..007, NFR-001..003, C-004, C-005, edge cases. Contract `contracts/dsl-retirement.md` §1–§4, §6 (binding: deletion/retention list, gate checklist, dependency mechanics). Data model §1–§3. Research §1 (gate states), §2 (OD1 FULL, OD3, OD4), §3 drift D-1/D-2, §6 supply-chain.
- **Decisions**: OD1 FULL (`01M1VAHEBB54DDDVCEX2R4BMCJ`); OD3 delete pack blocks (`01M1VAHGZM8HE72QPHEGP6DS24`); OD4 `events.py` stays (`01M1VAHJ9RMMND00NVHHYTHVV7`); OD2 (roadmap) deferred with working assumption "retire" — if the operator has since answered YES (check `plan.md`'s marker / `spec-kitty agent decision verify`), STOP and report.
- **"Both, together, or neither"**: deleting files without breaking the eager block frees nothing; breaking it without deleting leaves dead code. T002+T003 land in one commit.
- Charter/CLAUDE.md rules: Sonar (complexity ≤15; no `# noqa`/`# type: ignore`; no empty except); terminology "Mission"; `make test-fast` + blast radius; pyproject touched ⇒ run `tests/architectural/` in full ONCE before handoff; never `make test-full`; one dependency change per PR — do NOT touch `truststore` (PR #3899).
- Do not touch Mission A's surfaces or `runtime/next/*` (WP04 owns `decision.py`; `next_invocation_lifecycle.py` is untouched — its lazy import keeps working because `events.py` survives).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP01 --mission dead-port-disposition-01M1TZVN`.

## Subtasks & Detailed Guidance

### Subtask T001 – Red-first ratchet

- **Purpose**: FR-004 / SC-001; the permanent negative invariant.
- **Steps**: create `tests/specify_cli/mission_v1/test_import_hygiene.py` per `contracts/dsl-retirement.md` §1: a subprocess (`sys.executable -c …`) imports `specify_cli.mission_v1.events` and prints any `sys.modules` key equal to `transitions`, starting with `transitions.`, or equal to `six`; assert the output is empty. Second test: the loaded `specify_cli.mission_v1*` module set equals exactly `{package, package.events}`. Use a hermetic env (copy `os.environ`, drop `PYTHONPATH` surprises; set `PYTHONPATH=src` explicitly since `pytest.ini`'s `pythonpath` does not propagate to subprocesses). Run it: it must FAIL on the base (paste the failing output into the Activity Log).
- **Files**: `tests/specify_cli/mission_v1/test_import_hygiene.py` (new).
- **Parallel?**: No.

### Subtask T002 – Rewrite `mission_v1/__init__.py`

- **Purpose**: FR-001, FR-003, OD4.
- **Steps**: read `src/specify_cli/mission_v1/__init__.py` fully (154 lines). Replace with: a docstring stating that `mission_v1.events` is the surviving observability module (consumers: `next_invocation_lifecycle.py:332`, `decision.py:200`), that the state-machine DSL was retired in mission `dead-port-disposition-01M1TZVN` (git history has it), and why the package name is kept (OD4); then `from specify_cli.mission_v1.events import emit_event, read_events` and `__all__ = ["emit_event", "read_events"]`. Delete `MissionProtocol`, `load_mission`, `load_mission_by_name`, `StateMachineMission`/`PhaseMission`/`MissionModel` re-exports, the `yaml`/`Path`/`Protocol`/`runtime_checkable` imports. Grep `src` and `tests` for every deleted name before deleting (`grep -rn "load_mission\b\|load_mission_by_name\|MissionProtocol\|StateMachineMission\|PhaseMission\|MissionModel\b" src tests`) — production hits must be zero; test hits are handled in T004.
- **Files**: `src/specify_cli/mission_v1/__init__.py`.
- **Parallel?**: No (same commit as T003).

### Subtask T003 – Delete the DSL modules; re-point docstrings

- **Purpose**: FR-002 (FULL).
- **Steps**: `git rm src/specify_cli/mission_v1/{compat,runner,guards,schema}.py`. Re-point `src/specify_cli/review/gate_registry.py:7,132` docstrings (they cite `mission_v1.guards.GUARD_REGISTRY`/`compile_guards` as a shape precedent) to "the retired `mission_v1/guards.py` (see git history before mission dead-port-disposition-01M1TZVN)". Reword `src/specify_cli/skills/manifest_store.py:27`'s mention of `mission_v1.schema`. `grep -rn "mission_v1\.\(compat\|runner\|guards\|schema\)" src docs packs` → zero code references (docs mentions may be reworded or left as history with a note).
- **Files**: the four deleted modules, `review/gate_registry.py`, `skills/manifest_store.py`.
- **Parallel?**: No.

### Subtask T004 – Rework the test blast radius

- **Purpose**: FR-006.
- **Steps**: `grep -rln "mission_v1" tests` and classify each file: (a) imports ONLY retired modules → delete (`test_mission_v1_runner_unit.py`, `test_mission_v1_compat_unit.py`, `test_mission_v1_guards_unit.py`, `test_mission_v1_schema_unit.py`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`, `tests/missions/test_e2e_mission_v1_integration.py`, `tests/missions/test_mission_loading_integration.py`, `tests/missions/test_mission_guards_integration.py` — confirm names with `ls`); (b) mixed → trim: `tests/specify_cli/mission_v1/test_mission_v1_events_unit.py` keep the events half, delete the runner half (`:228-304`); `tests/research/test_research_plan_missions_integration.py:21` and `tests/missions/test_mission_software_dev_integration.py:21` delete only the `validate_mission_v1` schema-validation halves; (c) touches only `events` → keep. Never delete a file that covers live code.
- **Files**: as classified.
- **Parallel?**: No.

### Subtask T005 – Same-WP gate edits

- **Purpose**: C-005 / NFR-003 (no red or vacuous gate).
- **Steps**: (1) `tests/architectural/test_no_dead_symbols.py:720-727` remove the three `mission_v1` pins; (2) `:3278` remove `specify_cli.mission_v1.schema::strip_v1_keys` (drift D-1); read the gate's docstring for how pins are hashed — if removing a pin requires a baseline-count change, make it; (3) `tests/specify_cli/test_wp_frontmatter_fold.py:60` remove the `("specify_cli.mission_v1.guards", "read_wp_frontmatter")` tuple and fix the module docstring `:4`; (4) `tests/architectural/_gate_coverage.py:1456` — keep the row; run the coverage gate to confirm the trimmed directory satisfies it; (5) `tests/architectural/test_layer_rules.py:194` — the `mission_v1` runtime-ledger row stays (live edge `next_invocation_lifecycle.py:332`); run `test_runtime_ledger_has_no_stale_entries`. Do NOT edit `test_layer_rules.py` (WP03 owns its `constitution` hunk).
- **Files**: the three gate files.
- **Parallel?**: No.

### Subtask T006 – Pack-DSL honesty (OD3)

- **Purpose**: FR-007.
- **Steps**: in `packs/built-in/missions/{software-dev,plan,research}/mission.yaml` delete the `states:` and `transitions:` blocks (and nothing else — diff must be block-only). In `src/specify_cli/mission.py:59-67` update the `MISSION_COMPAT_IGNORED_FIELDS` comment: the keys belonged to the retired DSL v1; tolerance is retained for third-party/override `mission.yaml`s that still carry them. Run `tests/missions`, `tests/research`, and any pack-loading tests (`grep -rln "mission.yaml" tests | head`).
- **Files**: three `mission.yaml`, `src/specify_cli/mission.py`.
- **Parallel?**: Yes.
- **Notes**: `.kittify/overrides/missions/*` in this repo may also carry blocks — those are project overrides, NOT owned; leave them (tolerated) and mention it in the Activity Log.

### Subtask T007 – Dependency drop, CHANGELOG, architectural run

- **Purpose**: FR-005, NFR-002, C-004.
- **Steps**: delete `pyproject.toml:82`; `uv lock`; `git diff uv.lock | grep '^[-+]name = '` must show only `-name = "transitions"`; `six` must remain (grep the lock); in the worktree run `uv sync --frozen --all-extras` into a fresh temporary venv path (`UV_PROJECT_ENVIRONMENT=/tmp/…`) as the clean-install smoke, then `.venv/bin/pytest tests/architectural/test_pyproject_shape.py -q`; CHANGELOG entry under `## [Unreleased] - 3.2.7rc1` (Removed: `transitions` + mission-DSL v1 runtime; `mission_v1.events` remains; ratchet test added); then run `tests/architectural/` in full once.
- **Files**: `pyproject.toml`, `uv.lock`, `CHANGELOG.md`.
- **Parallel?**: No (last).

## Test Strategy

```bash
.venv/bin/pytest tests/specify_cli/mission_v1 tests/missions tests/research tests/specify_cli/next/test_next_invocation_lifecycle_seam.py tests/specify_cli/test_wp_frontmatter_fold.py -q
.venv/bin/pytest tests/architectural -q -p no:cacheprovider      # once, cross-cutting
PWHEADLESS=1 make test-fast
grep -rn "from transitions\|import transitions" src ; echo "expect nothing"
.venv/bin/ruff check $(git diff --name-only --diff-filter=AMR $(git merge-base HEAD missions/coreloop-proto-missions) | grep '\.py$') && .venv/bin/mypy src/specify_cli/mission_v1
```

## Risks & Mitigations

- Deleting a test that covered live code → classification step in T004; the events half stays.
- Vacuous/red gate → T005 + full architectural run.
- Lock conflict with PR #3899 → rebase; one dependency per PR.
- Working assumption OD2 → check the marker before starting.

## Review Guidance

- Ratchet was RED on the base (Activity Log evidence) and is green; no `transitions` import remains; `events.py` byte-identical (`git diff --stat` shows it untouched).
- All four pins + fold-gate entry removed; architectural suite green with no missing-symbol warnings.
- Lock diff limited to `transitions`; `six` present; CHANGELOG entry present; no version bump.
- Pack diffs are block-only.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T12:40:00Z – system – Prompt created.
- 2026-09-06T19:22:56Z – claude – shell_pid=88278 – Claim-time checks: PR #3899 MERGED 2026-09-06T15:59:58Z (truststore already dropped; lock regenerated on top). OD2 resolved by operator: NO roadmap, retire (plan.md:26). Mission A merged (base 1ceba9f22).
- 2026-09-06T19:23:02Z – claude – shell_pid=88278 – T001 RED proof on base: pytest tests/specify_cli/mission_v1/test_import_hygiene.py -> 2 failed. test_events_import_does_not_load_transitions: hot path loaded: six,transitions,transitions.core,transitions.extensions,transitions.extensions.asyncio,transitions.extensions.diagrams,transitions.extensions.factory,transitions.extensions.locking,transitions.extensions.markup,transitions.extensions.nesting,transitions.version. test_events_import_loads_only_the_package_and_events: loaded specify_cli.mission_v1,.compat,.events,.guards,.runner,.schema. GREEN after T002/T003.
- 2026-09-06T19:23:08Z – claude – shell_pid=88278 – Drift beyond research D-1..D-4: (D-5) strip_v1_keys pin is at test_no_dead_symbols.py:3320 not :3278 (removed). (D-6) test_mission_v1_events_unit.py lives in tests/missions/, not tests/specify_cli/mission_v1/ (trimmed in place). (D-7) test_mission_software_dev_integration.py reads the built-in PACK, so its states/transitions-reading classes had to go with the schema half once T006 deleted the blocks; the research/plan test reads the separate src/specify_cli/missions/* copies (still carry DSL blocks, not owned) so only its schema half was trimmed. (D-8) the fold-gate tuple at :60 was the ONLY parametrize case; removing it alone leaves a vacuous gate, so it is re-pointed at the two live read_wp_frontmatter consumers its docstring names (status.bootstrap, dossier.indexer). (D-9) ci_topology_census.json is stale on the BASE in worklist+mapped_dirs and no test consumes it; mission_v1 (120 LOC) now falls below the 500-LOC worklist floor; census NOT regenerated (would fold unrelated churn); _gate_coverage.py:1456 row kept as instructed. (D-10) packs still carry mission:/initial:/guards:/inputs:/outputs: and a 'v1 State Machine Definition' header (block-only rule honoured; residue flagged). .kittify/overrides/missions/{plan,research,software-dev}/mission.yaml carry DSL blocks too: project overrides, not owned, left tolerated.
- 2026-09-06T19:23:11Z – claude – shell_pid=88278 – T007: pyproject transitions line deleted; uv lock -> Removed transitions v0.9.3; lock diff names: -name = transitions only; six remains. Clean-install smoke in a throwaway venv (uv sync --frozen --all-extras): transitions installed False, six True, mission_v1 exports [emit_event, read_events], spec-kitty-cli 3.2.7rc1; throwaway venv deleted. CHANGELOG Removed entry under [Unreleased] - 3.2.7rc1, no version bump. Lane commit 7f70e6f94.
- 2026-09-06T19:34:51Z – claude – shell_pid=88278 – Full tests/architectural run (4 slices, -n 3): 1819 passed; reds: test_golden_count_ban (baseline-red, left red); test_ruff_format_exclude_ratchet x2 + test_ruff_format_enforcement (mine: 7 deleted-file exclude entries + 2 already-formatted-on-base entries removed from pyproject); test_no_inert_schema_slots (mine: pack states:/transitions: keys were the only name-match producer for charter MissionOrchestration.states/transitions; 4 ledger rows added owned by mission:dead-port-disposition-01M1TZVN, delete-the-declaration; baseline_entries 47->51 justified; unassigned stays 19). OPEN ITEM: this binds Mission B to delete the dead orchestration state machine (models.py + mission.schema.yaml, rider for WP03/WP05) or re-own the rows before all WPs complete. Other baseline-red nodes named in the brief (execution_context_parity x6, mission_runtime_surface cold imports, home_pin_census) were NOT red in this run. Second lane commit: gate follow-through.
- 2026-09-06T19:56:22Z – claude – shell_pid=55024 – Independent review (reviewer claude): APPROVED. Reproduced: RED on merge-base scratch worktree (test_import_hygiene 2 failed: six,transitions,transitions.* loaded; compat/guards/runner/schema loaded), GREEN on lane. Static: events.py byte-identical; mission_v1 = __init__+events only; grep mission_v1.{compat,runner,guards,schema} src packs empty; grep transitions imports src empty; uv.lock names diff = -transitions only, six kept via python-dateutil; packs states/transitions removed and every other top-level key equal to base (YAML round-trip); .kittify/overrides untouched; _gate_coverage.py:1456 and test_layer_rules.py:194 untouched; no __init__.py version change; CHANGELOG Removed entry present. Tests: 427 slice (mission_v1+missions+research+lifecycle-seam+fold, -n3 loadfile) 427 passed; gate quartet 96 passed; ruff-format-ratchet+enforcement+inert-slots+dead-symbols+layer-rules+pyproject-shape+terminology 114 passed; ratchet_baselines+gate_remedy_presence 31 passed; contract/doctrine-missions/unit-mission_loader 514 passed; ruff check clean, ruff format --check clean per file, mypy mission_v1 clean. Deviations D-5..D-11 acceptable. D-12: (a) owned non-provisional delete-the-declaration rows are the sanctioned ledger route since MAX_UNASSIGNED_ENTRIES is shrink-only - acceptable; (b) FALSE at HEAD: test_a_baseline_entry_does_not_survive_its_owner and test_every_named_owner_resolves were deleted in 177e06269 (#3285); owner_is_complete/unresolved_by_completed_owners in _inert_slots.py have zero callers, so NO gate fires when Mission B completes - pre-existing base condition, not WP01's; (c) recommend WP03 carry the rider: delete MissionOrchestration/MissionStateObject/MissionTransition + Mission.orchestration field (models.py:68-89,188), adjust scripts/generate_schemas.py _mission_fixups (:385-395), regenerate mission.schema.yaml, drop pins test_no_dead_symbols.py:355-362 and :992-999, delete the 13 orchestration-family baseline rows (4 owned + 9 unassigned: from, from_state, on x2, orchestration x2, required_artifacts x2, states x2, transitions x2, to x2) and lower _baselines.yaml counts 51->38 / 19->10; blast radius tests/doctrine/test_schema_validation.py + the arch gates. Non-blocking: ATDD test landed in the same commit as the implementation (charter asks for a separate preceding commit); design-note D-12 claim about the anti-weasel test needs correcting; docs/adr and docs/reports still cite mission_v1.guards/schema as history (no note added); file an upstream gap for the orphaned anti-weasel helpers.
