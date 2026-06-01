---
work_package_id: WP08
title: doctor doctrine health report
dependencies:
- WP05
requirement_refs:
- FR-008
- FR-009
- FR-010
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
- T038
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctor.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/_doctrine_health.py
- tests/specify_cli/test_doctor_doctrine.py
role: implementer
tags: []
---

# WP08 — `doctor doctrine` health report

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Introduce one `DoctrineHealthReport` consumed by both human and `--json` output (no independent assembly), surface invalid-profile diagnostics (FR-008/009), and fix the false-healthy bug so pack health derives from `valid==discovered`, not snapshot presence (FR-010). Keep it ≤2s on built-in + one pack (NFR-001).

## Context

- Spec FR-008/009/010, NFR-001; research R-011-C (human/JSON built independently; org-DRG load duplicated; `_render_doctrine_pack:1843` greens on `snapshot_present`; `_count_pack_artifacts:1803` globs; collisions scraped via regex; long `doctrine_check`).
- Data model §5. Contract C1.4. Depends on WP05 (`skipped_profiles()` is the data source — read it, do not regex `warnings`).

### Code map

- `src/specify_cli/cli/commands/doctor.py` — `doctrine_check` (~:1875-2014), `_render_doctrine_pack` (~:1839, the `:1843` snapshot check + `:1856` green), `_count_pack_artifacts` (~:1797), `_collect_org_layer_data`/`_render_org_layer_section` (~:2156/~:2092 duplicate load), `_build_selection_block` (~:2288), `DoctorFinding` (~:2404, mirror its pattern).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP05.

## Subtasks

### T034 — `DoctrineHealthReport` + `PackHealth`

**Steps**: Create `src/specify_cli/cli/commands/_doctrine_health.py` with `PackHealth{pack_id, layer, discovered_count, valid_count, invalid_profiles: list[SkippedProfile], healthy (derived)}` and `DoctrineHealthReport` aggregating packs + org-DRG state, with `to_dict()` for JSON. `healthy = (valid_count == discovered_count) and not invalid_profiles` (I-H1).

**Validation**: - [ ] `to_dict()` emits stable invalid-profile fields (layer/path/profile_id/error_summary).

### T035 — Build report once; render human from it

**Steps**: Refactor `doctrine_check` into `_build_doctrine_report(repo_root) -> DoctrineHealthReport` (single `DoctrineService`/DRG load; read `repo.skipped_profiles()` from WP05) + `_emit_doctrine_human(report)`. Collapse the duplicated org-DRG load into the report builder.

**Validation**: - [ ] human output shows degraded pack with invalid profiles by layer/path/error; valid profiles still listed.

### T036 — Render JSON from report; FR-010 health

**Steps**: `_emit_doctrine_json(report)` as a passthrough of `report.to_dict()`. Replace the `snapshot_present`/glob-count green logic with the derived `healthy`.

**Validation**: - [ ] `--json` includes `invalid_profiles` with stable fields; a pack with an invalid profile reports `healthy=false` even with valid DRG counts.

### T037 — Split long methods

**Steps**: Extract `_read_project_selections()`/`_read_org_required()` from `_build_selection_block`; retire the collision regex in favor of structured data where feasible (`focused-function-complexity-check`).

**Validation**: - [ ] no method >~60 lines in the doctrine slice; ruff complexity clean.

### T038 — Tests

**Steps**: `tests/specify_cli/test_doctor_doctrine.py` — degraded pack in human + JSON; FR-010 false-healthy fixed; ≤2s budget on built-in + one-pack fixture (NFR-001, assert wall-clock with a generous margin).

**Validation**: - [ ] all green.

## Definition of Done

- [ ] One report drives human + JSON; invalid profiles surfaced; false-healthy fixed; long methods split; ≤2s.
- [ ] CC-2 gates pass.

## Risks

- NFR-001 budget: build the report once (single service/DRG load) — the old double-load is the main cost.
- Don't reintroduce regex scraping; consume `skipped_profiles()` from WP05.

## Reviewer Guidance (reviewer-renata)

- Confirm human and JSON derive from the same `DoctrineHealthReport` (no parallel assembly).
- Confirm `healthy` is `valid==discovered`, not snapshot presence.
- Confirm JSON invalid-profile fields are stable and a passthrough of `SkippedProfile`.
