---
work_package_id: WP01
title: Atomic template_set cutover (Concern A)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-011
- NFR-001
- NFR-003
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent:
- tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py
execution_mode: code_change
owned_files:
- src/doctrine/missions/models.py
- src/doctrine/missions/mission_type_repository.py
- src/doctrine/missions/mission_step_repository.py
- src/doctrine/missions/step_projection.py
- src/charter/mission_type_profiles.py
- src/specify_cli/cli/commands/mission_type.py
- tests/doctrine/missions/test_softwaredev_roundtrip.py
- tests/doctrine/missions/test_mission_type_repository.py
- tests/doctrine/missions/test_step_schema.py
- tests/doctrine/missions/test_step_projection.py
- tests/runtime/test_runtime_seam.py
- tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py
role: implementer
tags: []
shell_pid: "2433070"
shell_pid_created_at: "1784286334.2"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

Retire the persisted `MissionType.template_set` field and source the template-set projection from the step authority **at the consumption boundary** — a single **atomic** change (C-009) that is byte-for-byte behavior-preserving for the four built-in types. This is Concern A; it lands first so Concerns B/C are built on the clean surface.

**Anchor convention**: line numbers are *indicative* — resolve by symbol name.

## Context

`template_set` today is a persisted, YAML-authorable dict field on the frozen `MissionType` model, overlaid by `_inject_projected_fields` from `project_template_set(steps)` with a raw-YAML fallback. The only behavioral consumer is `resolve_configured_template` (`resolver.py:395`), which reads the lazy `ResolvedMissionType.template_set` `@cached_property` whose thunk (`_resolve_template_set_slot`, `mission_type_profiles.py:744`) reads the model field. Retiring the field = drop the overlay + repoint the thunk to compute from steps. Proven behavior-preserving (software-dev steps already carry refs → identical projection; no `mission_types/*.yaml` authors `template_set` → the fallback is dead code).

### FROZEN INVARIANTS (do not violate)
- **C-009 atomic**: T001–T006 land together on one tree. `MissionType` is `frozen, extra="forbid"` — removing the field while any `.template_set` read or the overlay remains throws `AttributeError`/`ValidationError`. Do NOT split across WPs.
- **C-007**: leave the `action_sequence` overlay (`_inject_projected_fields:199`) and its retained test (`test_softwaredev_roundtrip.py:125-129`) untouched. `action_sequence` symmetry is deferred to #2751.
- **C-006**: do NOT rename `ResolvedMissionType.template_set` (the resolved property name stays).
- **C-002 scalar fence**: `mission_type_profiles.py` also holds the OUT-of-scope scalar `MissionTypeProfile.template_set` (`:145`, display `:1001-1004`) — a DIFFERENT domain object. Edit ONLY the in-scope dict slot `_resolve_template_set_slot:744`. **No blind grep-replace on `template_set` in this file.**
- **C-001 fail-closed**: the `resolve_configured_template` null-guard and typeless rejection stay; do NOT relax them.

## Subtasks

### T001 — Remove the `MissionType.template_set` field
- In `src/doctrine/missions/models.py`, delete the `template_set: dict[str, str] | None` field from `MissionType` and its docstring lines. Keep `action_sequence`.
- `grep -rn "\.template_set" src/` and confirm no remaining read targets the *model* field (distinguish from `ResolvedMissionType.template_set` (keep), the charter scalar (fenced), and `step.template` (survives)).

### T002 — Drop the `template_set` overlay (keep `action_sequence`)
- In `mission_type_repository.py:_inject_projected_fields`, delete the **entire** `payload["template_set"] = (...)` assignment (`:200-202`). **Keep** `payload["action_sequence"] = projected_sequence or raw.get("action_sequence")` (`:199`).
- The pack-authored-`template_set` loud-fail is now automatic: `payload = dict(raw)` (`:198`) preserves any authored key and `extra="forbid"` rejects it. (Proof lands in T007.)

### T003 — `step_projection.py` (sole owner): ordering + shared helper
- Order the projected steps by `sequence_index` at the source (mirror `project_action_sequence`, which already sorts) so `project_template_set` and the downstream graph pass are deterministic. Do **NOT** key-sort the output dict (would reorder software-dev's `{spec, plan}`).
- Promote the private `_step_template_ref` (`:111`) into a public `iter_template_refs(steps) -> list[tuple[MissionStep, MissionStepTemplateRef]]` (sequence_index-ordered), and rewire `project_template_set` to build its dict from it. **WP06 will consume the same helper** — one traversal of `step.template`, not two.

### T004 — Shared cache + re-point the slot
- In `mission_step_repository.py`, memoise `resolve_all_for_mission_type` keyed by `(mission_type, pack_context)` (the filesystem walk lives here; `default()` only singletons the repo object). Add a `.cache_clear()` test seam. The cache must be **shared** — after the cutover both the retained `action_sequence` overlay and the new `template_set` slot resolve steps per resolution.
- In `mission_type_profiles.py:_resolve_template_set_slot` (`:744`), replace the `mission.template_set` read with `project_template_set(<steps resolved via the cached repo>, pack_context=None)`. Preserve `pack_context=None` (builtin-only parity). **Never** touch the scalar `:145/:1001`.

### T005 — Migrate CLI reads + add CLI test
- In `cli/commands/mission_type.py`, migrate the `--json` read (`:1491`) and the human panel (`:1509-1511`) from `mt.template_set` to the resolved context; `dict()`-wrap the returned `MappingProxyType` before `json.dumps` (else `TypeError`). Mirror the existing `action_sequence` resolved-context pattern (`:1477`).
- Add `tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py` covering the `--json` and panel output for software-dev (currently untested — this path breaks silently otherwise).

### T006 — Test migration (retire-only-template_set-method)
- From `TestMissionTypeRepositoryLiveProjection` (class `test_softwaredev_roundtrip.py:115`), retire **only** `test_default_resolves_software_dev_template_set` (`:131-135`). **KEEP** `test_default_resolves_software_dev_action_sequence` (`:125-129`, C-007-retained).
- Grep-migrate **every** `.template_set` read on a `MissionType` instance → `project_template_set(steps)`/`ResolvedMissionType`: `test_mission_type_repository.py:47` (easy to miss — outside the enumerated ranges), `:89-105`, `:181-197`; `test_step_schema.py:197-211`; `test_step_projection.py:255/318`. Distinguish from surviving `step.template` reads.
- **KEEP** `TestSoftwareDevProjectionParity` (`test_softwaredev_roundtrip.py:68-112`) — the enduring regression net (NFR-001).
- Optional campsite: freshen the stale `tests/runtime/test_runtime_seam.py:18-24` docstring (describes the old "read `mission.template_set` off the model" architecture).

### T007 — Concern-A proofs (red-first)
- **software-dev parity**: resolved filenames byte-identical; `mission_type show --json` `template_set` key order == `sequence_index` order (update the CLI-test baseline to the canonical order — this is a determinism fix, not a regression).
- **repo constructs**: `MissionTypeRepository.default().get("software-dev")` returns non-None and projects `{spec, plan}`.
- **pack-fails-loud** (SC-002): a `MissionType` payload / mission_type YAML authoring `template_set:` raises `ValidationError` (regression test).
- **one-walk shared-cache** (NFR-003): a call-count/spy test asserting N template resolutions for one type trigger **exactly one** `mission-steps/` resolution, shared across the two consumers.

## Branch Strategy
Planning/base branch: `feat/mission-step-creatability`. Final merge target: `feat/mission-step-creatability`. Execution worktree is allocated per the computed lane from `lanes.json`; base on the current `feat/mission-step-creatability` HEAD (NOT origin/main). Implement via `spec-kitty agent action implement WP01 --agent <tool>:<model>:python-pedro:implementer`.

## Definition of Done
- Field removed; overlay dropped (action_sequence overlay intact); slot computes from cached steps; CLI migrated + tested; test migration complete (parity guard kept).
- All 4 proofs (T007) green; `ruff` + `mypy --strict` clean, zero new suppressions; complexity ≤15; ≥3× literals hoisted.
- `spec-kitty doctrine regenerate-graph --check` unchanged (WP01 mints no edges — behavior-preserving), `tests/architectural/` green.

## Risks & Reviewer Guidance
- **Atomicity**: verify no intermediate state has a dangling `.template_set` model read. Reviewer: grep the diff for any surviving `mt.template_set`/`mission.template_set` model read.
- **Scalar leak (C-002)**: reviewer confirms `mission_type_profiles.py` edits touch only `:744`, never `:145/:1001`; the diff references no `resolution.template_set`.
- **Cache correctness (NFR-003)**: reviewer confirms the cache is on `resolve_all_for_mission_type` keyed `(mission_type, pack_context)` and shared — not slot-local, not merely `default()`.
- **Determinism**: reviewer confirms steps ordered by `sequence_index`, dict NOT key-sorted, software-dev `--json` order is `{spec, plan}`.

## Activity Log

- 2026-07-17T10:16:20Z – claude:sonnet:python-pedro:implementer – shell_pid=2326337 – Assigned agent via action command
- 2026-07-17T11:04:30Z – claude:sonnet:python-pedro:implementer – shell_pid=2326337 – WP01 atomic template_set cutover complete (commit ff7d410bd). Retired MissionType.template_set field + overlay; slot now computes project_template_set(steps) from a shared, cross-instance resolve_all_for_mission_type cache (NFR-003 one-walk proof green); CLI --json+panel migrated to resolved context with dict()-wrapped MappingProxyType + new test_mission_type_template_set_cli.py; test migration complete (parity guard TestSoftwareDevProjectionParity kept). T007 proofs: (1) software-dev filename+canonical {spec,plan} key-order parity green; (2) default().get(software-dev) constructs+projects {spec,plan}; (3) pack/YAML-authored template_set: raises ValidationError (SC-002); (4) one-walk shared-cache spy green. Gates FOREGROUND: diff-scoped ruff exit-0 (All checks passed); mypy --strict src exit-0 (Success: no issues found in 14 source files); tests/architectural 1016 passed/4 skipped; tests/charter+tests/doctrine 4290 passed; tests/runtime+cli 32 passed; regenerate-graph --check FRESH (WP01 mints no edges). Scope note: 2 non-owned test files edited (test_resolved_mission_type_context.py lazy-cache spy re-point for FR-002; test_mission_step_resolver.py NFR-003 cache proof) — rationale-backed, no cross-WP overlap.
- 2026-07-17T11:05:36Z – claude:opus:reviewer-renata:reviewer – shell_pid=2433070 – Started review via action command
- 2026-07-17T11:14:03Z – user – shell_pid=2433070 – Review passed (reviewer-renata): C-009 atomicity verified (field removal + overlay drop + slot re-point + CLI migration all on one tree; zero surviving MissionType.template_set model reads in src/). C-002 scalar fence held (mission_type_profiles.py diff touches ONLY _resolve_template_set_slot; scalar MissionTypeProfile.template_set and resolution.template_set untouched). C-006 resolved property not renamed. C-007 action_sequence overlay+test kept. C-005 parity guard retained. 4 T007 proofs all genuine (real CLI/repo/YAML-loader paths): --json {spec,plan} order parity; default().get constructs+projects; YAML template_set: raises ValidationError; NFR-003 spy proves cross-instance one-walk shared cache keyed (builtin_root,mission_type,pack_context). iter_template_refs public+consumed; dead-symbol gate green. Gates verified locally: 159 WP tests pass, dead-symbol 24 pass, regenerate-graph --check FRESH, ruff+mypy --strict clean. Seeded mission issue-matrix (in-mission for mission-scope issues; deferred-with-followup w/ handles for out-of-scope #2751/#2725/#2726) to unblock per-WP approval; terminal verdicts due at mission done.
