---
work_package_id: WP01
title: Retire the inert governance_refs field
dependencies: []
requirement_refs:
- FR-010
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1336791"
shell_pid_created_at: "1784067713.53"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-01, Lane A tidy-first)
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/doctrine/missions/models.py
- src/doctrine/missions/mission_types/software-dev.yaml
- src/doctrine/missions/mission_types/documentation.yaml
- src/doctrine/missions/mission_types/research.yaml
- src/doctrine/missions/mission_types/plan.yaml
- src/specify_cli/cli/commands/mission_type.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read, in order:
[plan.md](../plan.md) §IC-01 + "Cross-cutting notes" (the "Two distinct models — not a collision" note),
[spec.md](../spec.md) FR-010, and the ADR decision "The inert `governance_refs` field is replaced, not
merely dropped" ([ADR 2026-07-14-2](../../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md)).
The ADR/plan are the authority — do not restate them; execute against live code.

## Objective

Remove the dead, dangling per-type `governance_refs` field so the `MissionType` artefact's governance
resolves only through the live path (the resolver seam WP03 builds), with **no danglers** left in the
DRG (FR-010). This is a behaviour-preserving **tidy** — `governance_refs` has no runtime reader today
(only CLI display), so nothing that matters at runtime changes. It is the independent Lane-A root.

## Context

- `MissionType` (the **artefact** model, `src/doctrine/missions/models.py:186`) is `extra="forbid"`.
  Therefore `governance_refs` cannot be removed from the model alone — **all four**
  `mission_types/*.yaml` carry `governance_refs: []` (or refs) and every one must be stripped in the
  same WP, or the next `MissionType` load reds.
- `software-dev.yaml:11-12` additionally carries **dangling** `DIR-010`/`DIR-011` references (real ids
  are `DIRECTIVE_0NN`) — remove them with the field.
- This is a **different model** from `MissionTypeProfile` (edited by WP05 in `charter/`). No `models.py`
  collision — see the plan's cross-cutting note.
- The intent `governance_refs` gestured at (a mission type declaring its governance) is fulfilled
  properly downstream by the load-bearing artefact + resolver — do not try to preserve the field.

## Subtask guidance

- **T001 — model.** In `src/doctrine/missions/models.py`, delete the `governance_refs` field from
  `MissionType`. Keep `extra="forbid"`. Confirm no other field or validator references it.
- **T002 — the four YAMLs.** Strip `governance_refs:` from `mission_types/{software-dev,documentation,
  research,plan}.yaml`. In `software-dev.yaml` also remove the dangling `DIR-010`/`DIR-011` entries
  (`:11-12`). Missing any one file reds every `MissionType` load — grep to prove zero `governance_refs:`
  keys remain under `mission_types/`.
- **T003 — CLI display.** In `src/specify_cli/cli/commands/mission_type.py`, drop the display rows that
  render `governance_refs` (`:1486,1505`). Keep the rest of the command intact.
  **Coordination note:** WP03 must also touch this file (migrate a `resolve_action_sequence` caller at
  `:1477`) — see tasks.md "WP01/WP03 coordination". Do NOT pre-empt that edit here; land only the display
  removal so the operator's chosen coordination path stays open.
- **T004 — comment + DRG guard.** Fix the stale `drg.py:169` comment that describes `governance_refs`.
  If a DRG parity/freshness guard references the field, re-point it. Do **not** run the terminal
  `regenerate-graph --check` here — that is owned once by WP12 (removing danglers may change the graph;
  WP12 runs the single authoritative regenerate after WP01 + WP06/07/08 land).
- **T005 — tests + gates.** Update (do not preserve) the ~3–4 tests that asserted the field:
  `test_mission_type_repository.py:44`, `test_charter_mission_type_commands.py:242,247`, the
  `test_activation_filtered_drg.py` docstring. The tests **move with the behaviour** — they must assert
  the field is gone, not keep it alive. `ruff check` + `mypy` clean on the diff. Run the terminology
  guard (`pytest tests/architectural/test_no_legacy_terminology.py`) before pushing (doctrine/prose CI gate).

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` (per-lane worktree, `lanes` topology) and merges back into
`mission/883-mission-type-governance-profiles`. Lane A is independent — WP01 can land first, in parallel
with the Lane B/D roots.

## Definition of Done

- [ ] `governance_refs` removed from `MissionType` (`extra="forbid"` retained).
- [ ] `grep -rn 'governance_refs' src/doctrine/missions/mission_types/` returns **0**; dangling
      `DIR-010/011` gone from `software-dev.yaml`.
- [ ] `MissionType` loads green for all four types (no `extra="forbid"` reds).
- [ ] CLI `mission_type` display no longer renders governance_refs rows; command still runs.
- [ ] `drg.py:169` comment corrected; any DRG guard re-pointed (terminal regenerate deferred to WP12).
- [ ] The ~3–4 field-asserting tests updated to the new behaviour (not preserved).
- [ ] `ruff` + `mypy` clean; terminology guard green.

## Risks

- **Missing one of the four YAMLs reds every load** — the `extra="forbid"` failure is global. Grep-verify.
- **Clobbering DRG freshness** — do NOT regenerate here; WP12 is the single owner (WP01 + WP06/07/08 both
  touch `graph.yaml`'s inputs).
- **Over-reach into WP03's `mission_type.py:1477` edit** — stay to the display rows only.

## Reviewer guidance (reviewer-renata, opus)

- Grep the diff for any surviving `governance_refs` under `src/doctrine/missions/`.
- Confirm the field-asserting tests were **rewritten** (not deleted-to-green and not preserved).
- Confirm `mission_type.py` diff is display-only (no resolver-caller edit that belongs to WP03).
- Confirm no `regenerate-graph` run leaked into this WP.

## Activity Log

- 2026-07-14T22:12:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1312033 – Assigned agent via action command
- 2026-07-14T22:21:12Z – claude:sonnet:python-pedro:implementer – shell_pid=1312033 – Ready: governance_refs retired from model + 4 yaml + CLI; danglers fixed; tests updated; ruff+mypy+terminology green
- 2026-07-14T22:22:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=1336791 – Started review via action command
- 2026-07-14T22:26:55Z – user – shell_pid=1336791 – Review passed: governance_refs retired from MissionType model (extra=forbid retained) + all 4 mission_types/*.yaml; dangling DIR-010/011 removed from software-dev.yaml; CLI display rows + JSON key dropped; drg.py comment corrected; 3 field-asserting tests REWRITTEN to assert-gone (not deleted-to-green, not preserved). grep governance_refs in src/ = 0; all 4 types load under extra=forbid; resolve_action_sequence caller at mission_type.py:1477 correctly LEFT for WP03; no regenerate-graph leak. ruff+mypy clean; 63 gate tests pass incl. terminology guard. mission_type.py shared-file coordination with WP03 respected (display-only). NOTE: filled mission issue-matrix #883/#461/#901 as in-mission (was unknown, blocking approve gate).
