---
work_package_id: WP04
title: cross-grain doctrine-integrity gate + non-vacuity twin
dependencies:
- WP02
requirement_refs:
- C-002
- C-003
- FR-002
- FR-003
- NFR-002
tracker_refs:
- '2651'
planning_base_branch: feat/2651-resolver-seam-completion
merge_target_branch: feat/2651-resolver-seam-completion
branch_strategy: Planning artifacts for this mission were generated on feat/2651-resolver-seam-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/2651-resolver-seam-completion unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2998792"
shell_pid_created_at: "1784131809.91"
history:
- at: '2026-07-15T12:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-04/IC-05/IC-11, gate lane — parallel tail after WP02)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/test_cross_grain_integrity.py
create_intent:
- tests/doctrine/drg/test_cross_grain_integrity.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/drg/test_cross_grain_integrity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [plan.md](../plan.md) §IC-04/§IC-05/§IC-11,
[research.md](../research.md) §R2/R3 (the enforcement-home + vacuity decisions), and
[ADR 2026-07-14-2](../../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md)
Enduring-verification (FR-013's home is a doctrine-module + integration test with a non-vacuity twin).
Depends on WP02's `src/charter/action_grain.py`. Always `uv run`.

## Objective

Build the **load-bearing** FR-013 enforcer: a doctrine-integrity gate over the unioned (type ⊕ action)
governance on **real** content, with a **non-vacuity twin**. This is the ADR-decided home (the resolver's
lazy raise in WP03 is only a fast-fail). It **reuses WP02's `aggregate_action_grain`** — it must NOT
re-implement the union (C-002).

## Context

- Shipped doctrine is authored **disjoint on purpose** (`plan/actions/plan/index.yaml`: "kept disjoint (FR-013)").
  Empirically verified: **zero cross-grain collisions across all 4 types**. So this gate is **forward-looking
  regression protection** for future org/pack-authored grains — "catches no existing defect" is correct-by-design.
- `load_action_index` returns empty on missing/corrupt YAML — a green gate over an accidentally-empty grain would
  be **vacuous**; assert the loaded grain **non-empty**.
- **CRITICAL (post-task squad):** all 4 types HAVE `actions/` dirs; `plan`'s action indexes are intentionally
  **empty-content** (`plan/actions/plan/index.yaml` lists all `[]`, by design) — its aggregated grain is
  legitimately empty. The non-empty assertion MUST key on a **content-bearing allow-list
  `{software-dev, research, documentation}`**, NEVER on `actions/`-dir presence. Grain-line counts today:
  software-dev 20, research 14, documentation 18, **plan 0**. Asserting non-empty for `plan` **red-mains the
  gate on the disjoint shipped tree** (violates SC-002).

### T012 — Doctrine-integrity gate
- Add `tests/doctrine/drg/test_cross_grain_integrity.py` (natural home next to `test_shipped_graph_valid.py`).
- For every shipped mission type: load the type-grain (`governance-profile.yaml selected_*`) and the action-grain
  via **WP02's `aggregate_action_grain`** (real `load_action_index` file I/O); assert the union raises **no**
  `CrossGrainDoubleDeclarationError` (disjoint) and that the action grain loaded is **non-empty for the three
  content-bearing types** (`{software-dev, research, documentation}`; `plan` is legitimately empty — see the
  CRITICAL note above). Fold in WP02's IC-11 dup-scan helper as the assertion — **do not ship a second scanner**.

### T013 — Non-vacuity twin
- Add a test that writes a **purpose-authored temp-tree** with a deliberate type∩action URN collision (a
  `governance-profile.yaml` + an `actions/<a>/index.yaml` sharing one URN), loads it through the **same**
  `load_action_index` file seam + `aggregate_action_grain`, and asserts the gate **fails**
  (`CrossGrainDoubleDeclarationError`). This proves T012 is not vacuously green. If you use a transitional
  parity scaffold anywhere, it MUST be deleted before landing (C-003; WP03 adds the reappearance guard).

## Branch Strategy

Base = WP02's tip; final merge target `feat/2651-resolver-seam-completion`. Parallel tail after WP02; no source contention (new test file, imports WP02's module).

## Definition of Done

- `test_cross_grain_integrity.py` passes on the shipped tree (disjoint, non-empty) and its twin **fails** on the deliberate collision.
- The gate imports WP02's `aggregate_action_grain` (single union authority) — no re-implementation.
- `ruff` + `mypy --strict` clean; no surviving `parity_scaffold` artifact.

## Risks / Reviewer guidance

- **Risk:** vacuous green (grain silently empty) — the non-empty assertion + the twin guard against it.
- **Reviewer:** confirm the twin actually fails without T012's fix and that the gate reuses WP02's union (grep for a duplicate `load_action_index` loop → reject).

## Activity Log

- 2026-07-15T15:59:50Z – claude:sonnet:python-pedro:implementer – shell_pid=2975764 – Assigned agent via action command
- 2026-07-15T16:10:20Z – claude:sonnet:python-pedro:implementer – shell_pid=2975764 – WP04 done: integrity gate + non-vacuity twin (allow-list, reuses WP02 scanner); 7 tests, twin proven to fire, ruff/mypy clean (f9f412b84)
- 2026-07-15T16:10:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=2998792 – Started review via action command
- 2026-07-15T16:16:28Z – user – shell_pid=2998792 – Review PASS (reviewer-renata:opus): single scanner (C-002), content-bearing allow-list, non-vacuity twin proven non-tautological, 7 tests, ruff/mypy exit 0
- 2026-07-15T17:11:17Z – user – shell_pid=2998792 – Done override: Mission merged to feat/2651-resolver-seam-completion (298d0d4)
