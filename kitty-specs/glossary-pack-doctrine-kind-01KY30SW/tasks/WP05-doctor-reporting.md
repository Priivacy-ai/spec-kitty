---
work_package_id: WP05
title: Doctor reporting + performance
dependencies:
- WP02
- WP04
requirement_refs:
- FR-012
- NFR-005
planning_base_branch: research/glossary-doctrine-artefact
merge_target_branch: research/glossary-doctrine-artefact
branch_strategy: Planning artifacts for this mission were generated on research/glossary-doctrine-artefact. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/glossary-doctrine-artefact unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/doctrine/test_doctrine_health_glossary_pack.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/cli/commands/_doctrine_health.py
- src/specify_cli/cli/commands/_doctrine_collect.py
- src/specify_cli/cli/commands/_profile_health_render.py
- tests/doctrine/test_doctrine_health_glossary_pack.py
role: implementer
tags: []
tracker_refs: []
shell_pid: "1753368"
shell_pid_created_at: "1784675787.05"
---

# WP05 — Doctor reporting + performance

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load python-pedro` and adopt it fully. **Boundary**: doctor health is ratified in
`plan.md` IC-06 and `contracts/pack-schema.md §5`. Implement the reporting; do not change the pack
schema or activation.

## Objective

Surface glossary-pack health in `spec-kitty doctor doctrine --json`: counts of loaded packs and their
health, with an **invalid member pack reported unhealthy** (never silently healthy). Keep doctor under
2 s. `src/specify_cli/cli/commands/_doctrine_health.py` is profile-centric today, so this is real new code, not a derived freebie.

## Context

- **Requirements owned**: FR-012 (doctor reporting), NFR-005 (doctor < 2 s), SC-001 (loaded+healthy /
  invalid→unhealthy).
- `src/specify_cli/cli/commands/_doctrine_health.py` currently derives `PackHealth` from `AgentProfileRepository` provenance — add a
  glossary-pack dimension alongside it, sourced from `DoctrineService.glossary_packs` (WP02) with the
  built-in pack active (WP04).

## Subtasks

### T024 — Doctor health test (RED-FIRST) · FR-012, SC-001

- File: `tests/doctrine/test_doctrine_health_glossary_pack.py`.
- **Valid**: with the built-in `spec-kitty-core` pack loaded, `doctor doctrine --json` reports it as a
  loaded, **healthy** glossary-pack node with its term count.
- **Invalid**: with a **synthetic** malformed pack (e.g. a term missing `definition`, or a duplicate
  surface) in a temp doctrine root, the aggregate glossary-pack health is reported **unhealthy** — not
  silently healthy. RED first (no reporting exists yet).

### T025 — Implement glossary-pack health across the MODEL→COLLECT→RENDER seam · FR-012, SC-001

**Squad F1/M1/M2 — doctor health is a three-layer seam; touching only the MODEL layer ships a
`--json` payload that never surfaces glossary-pack health.** Do ALL of:

- **MODEL** — `src/specify_cli/cli/commands/_doctrine_health.py`: add the glossary-pack health type
  (counts + health), mirroring the profile `PackHealth` shape. An invalid member pack degrades the
  aggregate `healthy`. Reuse the load-diagnostics pattern (skipped/invalid surfaced, not swallowed).
- **COLLECT** — `src/specify_cli/cli/commands/_doctrine_collect.py`: this is where the
  `doctor doctrine --json` payload is actually assembled (`_collect_profile_health`,
  `_attach_pack_health`, `build_pack_health_by_layer`). Extend it to source glossary-pack health from
  `DoctrineService.glossary_packs` and attach it to the report. **Without this edit the JSON stays
  silent** even though the MODEL type exists.
- **RENDER / serialisation** — `_emit_doctrine_json` (`_profile_health_render.py`) is a passthrough of
  `DoctrineHealthReport.to_dict()`. **Nest** the glossary-pack health *inside* the report's `to_dict()`
  / `healthy` so the JSON emits it with NO change to the render passthrough or `doctor.py`. Only if a
  sibling top-level `glossary_packs` key is genuinely required, edit `_profile_health_render.py`
  (it is in this WP's `owned_files`) — but prefer nesting.

### T026 — Doctor performance assertion · NFR-005

- Add an assertion (in the same test file or a focused perf test) that `doctor doctrine --json`
  completes in **< 2 s** on this repository with the built-in pack loaded. Use a wall-clock budget with
  a sane margin; do not make it flaky (single generous threshold, not a tight micro-benchmark).

## Branch Strategy

Planning base `research/glossary-doctrine-artefact`; per-lane worktree; merge back unless redirected.
Depends on WP02 (repository) and WP04 (default-on so the pack is active in the health scan).

## Definition of Done

- [ ] T024 doctor health test RED-first (valid + invalid synthetic fixture) → GREEN.
- [ ] Glossary-pack counts + health in `doctor doctrine --json`; invalid pack → unhealthy.
- [ ] Doctor `< 2 s` assertion green and non-flaky.
- [ ] `ruff` + `mypy --strict` clean; complexity ≤ 15; ≥ 90% coverage.
- [ ] `pytest tests/doctrine/test_doctrine_health_glossary_pack.py -q` green.

## Risks & Reviewer Guidance

- **Risk**: invalid pack silently healthy (the exact anti-pattern SC-001 forbids) — reviewer confirms
  the synthetic-invalid fixture drives the aggregate unhealthy.
- **Risk**: a flaky perf assertion — reviewer confirms a generous single threshold, not a tight
  micro-benchmark.
- **Reviewer**: confirm the health dimension sources from `DoctrineService.glossary_packs`, not a
  re-implemented loader.

## Activity Log

- 2026-07-21T22:48:46Z – claude:sonnet:python-pedro:implementer – shell_pid=1714356 – Assigned agent via action command
- 2026-07-21T23:14:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1714356 – WP05 complete; glossary-pack health surfaced through MODEL→COLLECT→RENDER (nested, no render passthrough change); invalid pack→unhealthy via synthetic fixture; <2s perf assertion; target test green with PYTHONPATH pinned
- 2026-07-21T23:16:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=1753368 – Started review via action command
