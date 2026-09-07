---
work_package_id: WP03
title: Gate-Adjacent Residue + Emitter Slice (SHRUNK variant)
dependencies:
- WP01
requirement_refs:
- C-002
- C-003
- C-006
- C-007
- FR-011
- FR-012
- FR-013
- FR-014
- NFR-003
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1TZVN
base_commit: 1ceba9f2259968b99f5bb85cdc56e38c92622489
created_at: '2026-09-06T20:00:45.151568+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Wave 1 - Residue (after WP01)
agent: claude
history:
- at: '2026-09-06T12:40:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_layer_rules.py
- src/specify_cli/team_projection/**
- src/mission_runtime/context.py
- src/mission_runtime/__init__.py
- src/mission_runtime/lifecycle_phase.py
- src/kernel/paths.py
- src/runtime/next/event_emitter.py
- tests/architectural/test_no_retired_subsystems.py
- tests/architectural/test_pyproject_shape.py
- src/charter/offering/missions/models.py
- src/charter/offering/schemas/mission.schema.yaml
- scripts/generate_schemas.py
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_inert_slots_baseline.yaml
- tests/architectural/_baselines.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Gate-Adjacent Residue + Emitter Slice (SHRUNK variant)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

User Stories 3 and 4 (P3/P4). **Gate states at tasks time**: PR #3888 merged (C-002 satisfied); PR #3898 (emitter ADR) open / `Proposed` → this WP ships the **shrunk** variant (decision OD7 `01M1VAHPARWJKB35F6E1VH8ZTW`); PR #3899 carries none of the residue (OD8 `01M1VAHQN3WFC58K0TS9C1DYFQ`). **Update 2026-09-06 16:00Z**: PR #3898 MERGED with the ADR Accepted and PR #3899 MERGED. The ADR execution is minted as **WP05** (depends on this WP) — do NOT execute the ADR here; keep this WP's emitter items exactly as written (docstring correction + FR-011 record), noting in the docstring that the ADR is Accepted and executed by WP05. PR #3899 carried none of the residue (verified), so OD8 holds.

Done means:

- **SC-008 / FR-013**: `tests/architectural/test_layer_rules.py:65-73` no longer excludes the nonexistent `constitution` package; the layer rules gate is green.
- **FR-014**: `src/specify_cli/team_projection/` deleted; `ActionContext` alias deleted from both files; the 13 test-only `__all__` exports demoted (never deleted) with matching re-pins in `tests/architectural/test_no_dead_symbols.py` (out-of-map: WP01 owns that file; you edit it AFTER WP01 landed, with a one-line rationale in the Activity Log).
- **SC-007 shrunk**: `src/runtime/next/event_emitter.py:1-10` docstring corrected to point at the real E3 seam (`src/specify_cli/status/adapters.py:364-366`) and to name the pending ADR; **no code, name, signature, or import changes** anywhere on the emitter surface; `tests/runtime/test_bridge_parity.py` untouched and green; `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) untouched (C-006).
- **FR-011**: `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md` extracted from the dossier §3 with every anchor re-verified at your HEAD.
- Follow-up mint text for the emitter execution drafted in `design-notes/WP03-residue.md`.

## Context & Constraints

- Spec US3, US4, FR-011..014, C-002, C-003, C-006, C-007, SC-006..008. Contract `contracts/residue-and-emitter-shrunk.md` (binding). Data model §2 (gate ledger), §5 (residue table). Research §1 (gate states), §7 (R6).
- **C-007 runtime ledger**: after each deletion run `tests/architectural/test_layer_rules.py::test_runtime_ledger_has_no_stale_entries`; if a subpackage's last live `specify_cli` edge disappears, edit the ledger in the same commit (you own `test_layer_rules.py`).
- Do not touch Mission A's four shared runtime files beyond `event_emitter.py`'s docstring (`event_emitter.py` is not one of the four, but is Mission-A-adjacent — docstring only).
- Sonar/CLAUDE.md rules as usual; terminology guard before doc pushes.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP03 --mission dead-port-disposition-01M1TZVN` (based on WP01's lane).

## Subtasks & Detailed Guidance

### Subtask T011 – Delete the `constitution` exclusion

- **Purpose**: FR-013 / SC-008.
- **Steps**: read `tests/architectural/test_layer_rules.py:55-80`; delete the comment block and the `"constitution",` entry (`:65-73`); confirm no other reference (`grep -n constitution tests/architectural/test_layer_rules.py`); run the file. Record in the Activity Log that PR #3888 is present in the branch (`git log --oneline | grep 3888`).
- **Files**: `tests/architectural/test_layer_rules.py`.
- **Parallel?**: No.

### Subtask T012 – Delete the `team_projection/` tombstone

- **Purpose**: FR-014.
- **Steps**: `ls src/specify_cli/team_projection/` (expect only `__init__.py`); `git rm -r` it; check `pyproject.toml` `[tool.hatch.build.targets.wheel].packages` (WP01 owns `pyproject.toml` — if an entry must go, it is a one-line out-of-map edit with rationale; if WP01 is still open, coordinate); run `tests/architectural/test_no_retired_subsystems.py` (its bans at `:39-40,99-100` assert absence and stay green) and `tests/architectural/test_pyproject_shape.py`.
- **Files**: `src/specify_cli/team_projection/`.
- **Parallel?**: Yes.

### Subtask T013 – Delete the `ActionContext` alias

- **Purpose**: FR-014.
- **Steps**: `src/mission_runtime/context.py:338` (`ActionContext = MissionExecutionContext`) and its `__all__` entry `:342`; `src/mission_runtime/__init__.py:127` listing and the `__getattr__` branch `:139-142`; also the docstring mention at `context.py:22`. `grep -rn "ActionContext\b" src tests docs` → only unrelated `MissionExecutionContext` hits remain. If `test_no_dead_symbols.py` pins `ActionContext`, drop that pin in T014's edit.
- **Files**: `src/mission_runtime/context.py`, `src/mission_runtime/__init__.py`.
- **Parallel?**: Yes.

### Subtask T014 – Demote the 13 test-only `__all__` exports; re-pin

- **Purpose**: FR-014 (demotion, never deletion).
- **Steps**: enumerate the 13 from the current pins in `tests/architectural/test_no_dead_symbols.py` (search for `mission_runtime` and the two named symbols `content_present_at_primary_tip` (`mission_runtime/lifecycle_phase.py`), `get_packs_root_default` (`kernel/paths.py`)); for each: remove from the package `__all__` (and the `__init__.py` re-export if it exists only for the facade), keep the symbol; in-package callers (`mission_runtime/resolution.py:52`, `kernel/env_expand.py:63`) already import by module path — verify; tests importing via the package facade repoint to module paths. Then update the pins in `test_no_dead_symbols.py` (out-of-map, after WP01 landed; rationale line in Activity Log: "OD8 — WP03 re-pins sequenced behind WP01's DSL pin drops").
- **Files**: `src/mission_runtime/__init__.py`, `src/mission_runtime/lifecycle_phase.py`, `src/kernel/paths.py`, `tests/architectural/test_no_dead_symbols.py` (out-of-map), affected tests.
- **Parallel?**: No (after T011–T013).

### Subtask T015 – Emitter docstring; FR-011 record; follow-up mint; PR re-check

- **Purpose**: FR-011, FR-012 (shrunk), SC-007.
- **Steps**: (1) rewrite `src/runtime/next/event_emitter.py:1-10` per `contracts/residue-and-emitter-shrunk.md` §2 — docstring only; `git diff` must show no non-docstring change. (2) Create `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md`: header "Input to PR #3898 — recorded, not executed (C-003)"; copy dossier §3.1/§3.2 and the relevant verification-log lines; re-verify each anchor (`event_emitter.py:23`, `_internal_runtime/events.py:67`, `runtime_bridge_engine.py:80` TYPE_CHECKING import + 16 sites, `runtime_bridge.py:195,:1552,:2739,:1614,:2745,:2149-2150,:2187,:1560-1565`, `test_bridge_parity.py:1131-1152`, `spec_kitty_events` version via `.venv/bin/python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"`) and mark deltas. (3) `design-notes/WP03-residue.md`: the FR-012 follow-up text (contract §4), the PR #3898/#3899 re-check output with timestamps, and the residue placement table as landed. (4) Run `tests/runtime/test_bridge_parity.py` — must be untouched and green.
- **Files**: `event_emitter.py` (docstring), research file, design note.
- **Parallel?**: Yes.

### Subtask T014b – Rider (orchestrator-added 2026-09-06, decision 01M1W4WZEZZM8DM21JN1ZQY9E6): delete the dead `MissionOrchestration` model family

- **Why**: WP01 removed the packs' `states:`/`transitions:` blocks, which were the only name-only producer match for the charter offering's `MissionOrchestration.states/transitions` slots. WP01 therefore recorded 4 rows in `tests/architectural/_inert_slots_baseline.yaml` owned by `mission:dead-port-disposition-01M1TZVN` with disposition `delete-the-declaration` (and raised `_baselines.yaml` `baseline_entries` 47→51). The WP01 reviewer verified that the owner-completion gate (`test_a_baseline_entry_does_not_survive_its_owner`) was deleted upstream in `177e06269` (#3285), so nothing fires automatically — but the rows still promise a deletion this mission must deliver (FR-014 single gate ownership; charter campsite rule). The charter `Mission` pydantic model is a schema-generation-only model: no constructor exists anywhere in `src/`/`tests/` (the `Mission(` hits are `specify_cli.mission.Mission`, a different class), and `tests/doctrine/test_schema_validation.py:17` only checks that `mission.schema.yaml` is a valid schema.
- **Steps** (recipe from the WP01 review; verify every line number, they may have moved after the lane-a merge):
  1. `src/charter/offering/missions/models.py`: delete `MissionStateObject`, `MissionTransition`, `MissionOrchestration`, and the required `Mission.orchestration` field (`:188`). STOP and report (do not force) if a grep finds any live constructor of the charter `Mission` model or any consumer of an `orchestration` key outside this family.
  2. `scripts/generate_schemas.py::_mission_fixups` (`:385-396`): remove the fixup (or reduce to a no-op with no `mission_orchestration` reference) and regenerate `src/charter/offering/schemas/mission.schema.yaml` with the script; `orchestration` must leave the schema's `required:` list and `definitions:`.
  3. `tests/architectural/test_no_dead_symbols.py`: drop the three pins in BOTH categories (`:355-362` and `:1001-1008`).
  4. `tests/architectural/_inert_slots_baseline.yaml`: delete the whole orchestration family — the 4 rows owned by this mission plus the 9 unassigned rows (`from`, `from_state`, `on`×2, `orchestration`×2, `required_artifacts`×2, `states`×2, `transitions`×2, `to`×2; confirm by grep); lower `_baselines.yaml` `baseline_entries` (51→38 expected) and `unassigned_entries` (19→10 expected) to the counts you actually measure, with a `# justification:` line naming this WP.
  5. RED first: add/adjust a pin that fails while the family exists (e.g. the dead-symbol pin removal is only green once the symbols are gone; a schema assertion that `orchestration` is absent from `required:`), commit it before the deletion commit (charter C-011 — the WP01 reviewer noted WP01 folded RED and GREEN into one commit; do not repeat that).
- **Tests**: `tests/doctrine/test_schema_validation.py tests/charter/test_schemas.py tests/charter/test_schemas_additive_fields.py tests/charter/test_schemas_selection.py tests/doctrine/missions tests/architectural/test_no_inert_schema_slots.py tests/architectural/test_ratchet_baselines.py tests/architectural/test_gate_remedy_presence.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_layer_rules.py tests/architectural/test_no_retired_subsystems.py`.
- **Files**: the six added to `owned_files` above. `lanes.json` write_scope was not regenerated; expect `ACTIVE_WP_SCOPE_VIOLATION` *warnings* on commit for these files — they are not blocks.
- **Parallel?**: No (after T014).


## Test Strategy

```bash
.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py -q
.venv/bin/pytest tests/runtime/test_bridge_parity.py tests/mission_runtime -q 2>/dev/null || .venv/bin/pytest tests/runtime/test_bridge_parity.py -q
PWHEADLESS=1 make test-fast
grep -rn "ActionContext\b" src tests docs | grep -v MissionExecutionContext ; echo "expect nothing"
.venv/bin/ruff check $(git diff --name-only --diff-filter=AMR $(git merge-base HEAD missions/coreloop-proto-missions) | grep '\.py$') && .venv/bin/mypy src/mission_runtime src/kernel/paths.py
```

## Risks & Mitigations

- Wheel build breaks on the deleted package → `test_pyproject_shape.py`.
- A demotion deletes instead of demotes → in-package callers listed above must keep working; grep before/after.
- Emitter surface drift → `git diff --stat` on `src/runtime/next/` shows only `event_emitter.py` with docstring-only hunks.

## Review Guidance

- `constitution` gone; layer rules green; #3888 present.
- Residue table fully landed; 13 demotions are demotions; pins consistent.
- Emitter: docstring-only diff; parity oracle untouched; FR-011 record present with re-verified anchors; follow-up text present; PR re-check recorded.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T12:40:00Z – system – Prompt created.
- 2026-09-06T18:53:06Z – unknown – Orchestrator hand-off from WP04 (2026-09-06): WP04 deleted runtime.next.decision::derive_mission_state and ::evaluate_guards but left their two grandfathered rows in tests/architectural/test_no_dead_symbols.py (_WIDENED_SCOPE_GRANDFATHERED_470, ~:3244-3245) because WP03 T014 owns that file's re-pins. Prune those two orphaned rows as part of T014 and mention it in the WP03 design note.
- 2026-09-06T20:46:45Z – claude – shell_pid=45904 – T014 enumeration (analysis U1): test_no_dead_symbols.py carries no pins for the 13 - the facade re-export was itself a src/ importer. 13 = 11 mission_runtime facade names (ArtifactPlacementFragment, BranchRefFragment, IdentityFragment, MissionArtifactContext, StatusSurfaceFragment, WorkspaceFragment, MissionArtifactHome, artifact_home_for, ResolvedSurface, SurfaceLocations, translate_surface) + content_present_at_primary_tip + get_packs_root_default; the census's 14-3 delta (MissionContext name-collision with specify_cli.context, MissionExecutionContext/CheckoutIdentityError docstring hits) reconciles exactly. Re-pin landed on test_mission_runtime_surface.py::_PUBLIC_SURFACE (was declared, never asserted; now wired, 42->31) - out-of-map edit, OD8: sequenced behind WP01's DSL pin drops.
- 2026-09-06T20:46:46Z – claude – shell_pid=45904 – T014 drift: with the facade import gone the dead-symbol gate saw resolution.__all__ still claiming ResolvedSurface/SurfaceLocations/translate_surface with no importer; demoted from resolution.__all__ too (gate fix #2, in-file resolve_context_for_mission precedent) - zero allowlist rows added anywhere.
- 2026-09-06T20:46:48Z – claude – shell_pid=45904 – WP04 hand-off NOT executable on lane-c: lane-c is based on lane-a, WP04's decision.py deletion is on unmerged lane-d, so derive_mission_state/evaluate_guards still exist here and pruning their _WIDENED_SCOPE_GRANDFATHERED_470 rows reds test_no_dead_symbols (verified). Rows left in place (set is non-ratcheted); prune in WP05 once lane-c is rebased over the merged WP04, or at consolidation.
- 2026-09-06T20:46:49Z – claude – shell_pid=45904 – T014b outcome: DELETED. Stop condition checked, not hit (no charter Mission constructor anywhere; only orchestration consumers are the mission schema's own validation fixtures - decision record's 'test_schema_validation.py:17 only checks the schema file' is inaccurate, it validates fixtures, updated in-commit). Schema diff = 62 deletions in mission.schema.yaml only. Baseline family measured 14 rows (recipe said 13: to x2 + required_artifacts x2): BASELINE_SLOTS 51->37, unassigned 19->9 (recipe expected 38/10); MAX_UNASSIGNED_ENTRIES 19->9. Mission pin hash refreshed via _refresh_dead_symbol_hashes. Category-C pins were at :992-999, not :1001-1008.
- 2026-09-06T20:46:50Z – claude – shell_pid=45904 – T011: PR #3888 present as c0054153b. T015: gh re-check 2026-09-06T20:07Z - #3898 MERGED 15:59:54Z ADR Accepted, #3899 MERGED 15:59:58Z (no residue in its 15 files), so the FR-012 follow-up is WP05 (already minted). Docstring-only change proven by AST identity. Design note + FR-011 record delivered at <scratchpad>/wp03-c-planning-artifacts/{WP03-residue.md,emitter-adr-inputs.md} for the operator to copy into kitty-specs (lane gate refuses kitty-specs writes).
- 2026-09-06T21:10:52Z – claude – shell_pid=37499 – Review cycle 1 (full scope) VERDICT: APPROVE. Reproduced: RED 9f8d3a0b3 on 4213e000b = 18 failed/13 passed (note claims 21/10; the 3-node delta is test_symbol_survives_at_defining_module nodes green-on-base by construction; RED holds across all four pin groups); RED bf89e43e8 on f91716551 = 3 failed; HEAD sweep 1319 passed/4 skipped + extras 211 passed/1 skipped (charter schemas, 12 repointed tests, bridge parity, producer conformance); generate_schemas.py --check OK and rewrite zero-diff; _refresh_dead_symbol_hashes rerun zero-diff; event_emitter AST identical with docstring stripped; src/runtime diff = event_emitter.py only; parity oracle + Mission A files untouched; team_projection gone with no importer; ActionContext gone; 13 demoted not deleted, root __all__ 31, _PUBLIC_SURFACE asserted; T014b stop condition not hit (no charter Mission constructor in src; orchestration consumers only the schema fixtures); baseline family 14 rows, BASELINE_SLOTS 37, unassigned 19->9, MAX_UNASSIGNED_ENTRIES shrink-only; ruff check/format + mypy clean, no suppressions. Deviations 1-8 accepted. Deviation 6 verified: pruning the two decision:: rows reds test_no_public_symbol_in_all_is_unimported on lane-c; lane-d also left the rows; prune belongs to the first tree containing WP04 (consolidation, or WP05 after a rebase). test_mission_runtime_surface.py incl. test_package_root_cold_imports is green on base 4213e000b and on HEAD (not baseline-red here). move-task --to approved BLOCKED by issue-matrix gate: 'issue-matrix.md has unresolved entries. Fill in verdicts before approving. Missing rows: #3285' -- reviewer did not add rows; operator to resolve.
