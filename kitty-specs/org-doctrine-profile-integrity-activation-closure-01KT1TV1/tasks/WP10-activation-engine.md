---
work_package_id: WP10
title: Activation engine (plan/commit seam)
dependencies:
- WP01
requirement_refs:
- FR-011
- FR-012
- FR-021
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/activation_engine.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/charter/activation_engine.py
- tests/charter/test_activation_engine.py
role: implementer
tags: []
---

# WP10 — Activation engine (plan/commit seam)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Introduce a pure `plan_activation` → `commit_plan` seam so artifact-ID validation provably precedes the single config write (FR-011/012, NFR-003), with actionable unknown-ID errors and backward compatibility for projects with no activation restrictions (FR-021). This new module is consumed by `pack_manager` (WP09) and the CLI (WP12).

## Context

- Spec FR-011/012/021, NFR-003; research R-004, R-011-D (validation interleaved with default-pack materialization + write; `merge_defaults` writes backup before load).
- Data model §6 (`ActivationPlan`, state transitions). Contract C3.1.

### Code map

- `src/charter/pack_manager.py` (WP09 thins `activate`/`deactivate` to call this engine).
- `src/charter/kind_vocabulary.py` (WP01 ID resolver — `resolve_artifact_urn` raises on unknown ID).
- Existing `activate` body (~pack_manager.py:176-258) is the logic to refactor into the engine.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01. (WP09 depends on this.)

## Subtasks

### T044 — `ActivationPlan` + `plan_activation` (validate before mutate)

**Steps**: Create `src/charter/activation_engine.py`. Define `ActivationPlan{yaml_key, new_list, warnings, cascade_targets}`. Implement `plan_activation(ctx, kind, artifact_id, *, cascade_scope=None, layer_roots=...) -> ActivationPlan` that:
- validates the kind (via WP01) and the artifact ID exists for that kind (via the WP01 ID resolver) **before** computing any state (FR-011);
- computes the post-state list in memory (including any default-pack materialization as part of the plan, not applied);
- raises a structured error on unknown ID (no plan returned).

**Validation**: - [ ] `plan_activation` raises before producing a plan on unknown ID; pure (no writes).

### T045 — `commit_plan` single write

**Steps**: `commit_plan(config_path, plan) -> ActivationResult` performs the single `_save_config` write applying `plan.new_list`. Default materialization lives in the plan; a failing plan never stages a half-materialized list. Mirror for deactivation (`plan_deactivation`/reuse).

**Validation**: - [ ] exactly one write per commit; nothing written when no plan.

### T046 — Unknown-ID error + backward compat (FR-021)

**Steps**: Unknown-ID error message names kind + missing id + recovery path (`charter list --show-available` / `doctor doctrine`). Ensure projects with no explicit activation restrictions behave exactly as before PR #1535 (FR-021) — add a guard/test.

**Validation**: - [ ] actionable message; no-restriction projects unchanged.

### T047 — Tests

**Steps**: `tests/charter/test_activation_engine.py` — byte-compare config before/after a failing `plan_activation` (NFR-003); unknown-ID raises with recovery text; happy-path plan→commit writes once; backward-compat path.

**Validation**: - [ ] green; ruff/mypy clean.

## Definition of Done

- [ ] Pure plan/commit seam; validation precedes write; non-mutating failure proven; FR-021 preserved. CC-2 pass.

## Risks

- Keep the engine pure (no I/O in `plan_activation` except read for validation). The single write is only in `commit_plan`.
- Coordinate the `ActivationResult` shape with the existing CLI rendering (already `dict[str,list]` for cascade) so WP12 needs no shape change.

## Reviewer Guidance (reviewer-renata)

- Confirm the byte-compare non-mutation test exists and passes (NFR-003).
- Confirm no write path exists in `plan_activation`.
- Confirm unknown-ID error names kind+id+recovery.
