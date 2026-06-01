---
work_package_id: WP12
title: Charter activation CLI (wiring + cleanup)
dependencies:
- WP10
- WP11
requirement_refs:
- FR-013
- FR-014
- FR-020
- FR-035
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T053
- T054
- T055
- T056
- T057
- T058
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/charter/activate.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- src/specify_cli/cli/commands/charter/_app.py
- tests/specify_cli/test_charter_activate_cli.py
role: implementer
tags: []
---

# WP12 — Charter activation CLI (wiring + cleanup)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Wire the CLI to the engine + cascade engine: thread the real `--cascade` scope (stop the bool collapse), catch `CharterPackConfigError` fail-closed (FR-035), generalize the inlined `mission-type` block, and clear the FR-020 bookkeeping (normalize the dead sub-app exports, fix the FR-008 comment misattribution).

## Context

- Spec FR-013/014 (CLI), FR-020, FR-035; research R-011-D (`cascade_bool = bool(cascade)` at activate.py:47 discards scope; `kind=="mission-type"` block inlined at :49-73), R-011-E (`charter_activate_app`/`charter_deactivate_app` dead exports; `_app.py:47` FR-008 comment misattribution; `pack_context._config_error` raises `CharterPackConfigError` but no external catcher).
- Contract C3.2/C3.3, C1.5 (FR-035 fail-closed). Data model §9.

### Code map

- `src/specify_cli/cli/commands/charter/activate.py` (`activate_cmd`, `cascade_bool` at :47, mission-type block :49-73, kind check vs `YAML_KEY_MAP` :42), `deactivate.py` (mirror), `_app.py` (:17/:48 register bare `activate_cmd`; :47 FR-008 comment).
- WP10 engine, WP11 cascade (`CascadeScope.parse`), `charter.pack_context.CharterPackConfigError`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP10 + WP11.

## Subtasks

### T053 — Thread `--cascade` scope (FR-014)

**Steps**: Stop `cascade_bool = bool(cascade)`. Parse the option string via `CascadeScope.parse` (WP11) and pass the scope through `pack_manager`→engine→cascade. CLI option stays `str | None`. Render `cascade_activated`/`skipped` per kind (the result shape already supports it).

**Validation**: - [ ] `--cascade agent-profile,tactic` activates only those kinds; `--cascade all` activates all; absent → no cascade + warning (FR-013 via WP11).

### T054 — Fail-closed `CharterPackConfigError` (FR-035)

**Steps**: In `activate.py`/`deactivate.py`, catch `charter.pack_context.CharterPackConfigError` and present its `CHARTER_PACK_CONFIG_INVALID` code + remediation; exit non-zero with no mutation. This gives the previously-dead error type a live external caller.

**Validation**: - [ ] malformed config → fail-closed message; no write; `CharterPackConfigError` is imported/caught here (dead-symbol resolved — see WP15).

### T055 — Generalize the mission-type block

**Steps**: Move the inlined `kind == "mission-type"` step-removal-warning logic behind the engine/plan (warnings returned in `ActivationPlan.warnings`) so the CLI does not special-case it. The CLI just renders warnings for any kind.

**Validation**: - [ ] mission-type warnings still emitted, now via the plan; no `if kind == "mission-type"` in the CLI.

### T056 — Normalize sub-app exports (FR-020)

**Steps**: Pick one registration pattern: either register the sub-apps (`add_typer`) or drop the unused `charter_activate_app`/`charter_deactivate_app` and export the callbacks. Remove the dead export so the dead-symbol gate clears these two (coordinate with WP15).

**Validation**: - [ ] one consistent pattern; `charter_activate_app`/`charter_deactivate_app` no longer dead.

### T057 — Fix FR-008 comment misattribution

**Steps**: In `_app.py:47`, correct the comment: the general `activate` registration is FR-004; FR-008 refers only to the in-flight step-removal warning branch.

**Validation**: - [ ] comment accurate.

### T058 — Tests

**Steps**: `tests/specify_cli/test_charter_activate_cli.py` — cascade scope honored (selected kinds + `all`), no-cascade warning present, fail-closed on malformed config (message + no write), command registration intact.

**Validation**: - [ ] green; black-box CLI tests (DIRECTIVE_036).

## Definition of Done

- [ ] Cascade scope threaded; fail-closed config error; mission-type generalized; sub-app exports normalized; FR-008 comment fixed; tests green. CC-2 pass.

## Risks

- Don't regress the existing mission-type step-removal UX — keep the warnings, just relocate their source.
- The sub-app export normalization must actually remove the dead symbol (verify with the dead-symbol gate; WP15 owns the gate test but this WP removes the cause).

## Reviewer Guidance (reviewer-renata)

- Confirm the scope string is no longer collapsed to bool.
- Confirm `CharterPackConfigError` is caught with an actionable fail-closed message and no mutation.
- Confirm the dead sub-app export is gone (one registration pattern).
