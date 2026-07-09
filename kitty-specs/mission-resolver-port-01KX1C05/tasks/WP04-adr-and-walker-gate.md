---
work_package_id: WP04
title: ADR + AST call-site gate (bind by construction)
dependencies:
- WP03
requirement_refs:
- FR-006
- FR-007
- NFR-002
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "994733"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: architect-alphonso
authoritative_surface: tests/architectural/test_mission_resolver_walker_gate.py
create_intent:
- docs/adr/3.x/2026-07-08-1-mission-resolver-port.md
- tests/architectural/test_mission_resolver_walker_gate.py
execution_mode: code_change
owned_files:
- docs/adr/3.x/2026-07-08-1-mission-resolver-port.md
- tests/architectural/test_mission_resolver_walker_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your agent profile via `/ad-hoc-profile-load` for `architect-alphonso` (implementer). Then read
`kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-006/FR-007), `plan.md` (IC-04),
`contracts/mission-resolver.md` (G-1…G-3), and `research.md` (D-06, D-08, D-Q2).

## Objective

Bind the trunk **by construction**: write the ADR recording the decisions, and add a new AST call-site
gate naming `FsMissionResolver` as the single sanctioned `kitty-specs/` walker. Model it on the existing
`tests/architectural/test_protection_resolver_call_sites.py`.

## Subtasks

### T018 — ADR
- New `docs/adr/3.x/2026-07-08-1-mission-resolver-port.md`. Record:
  - Decision: one `MissionResolver` trunk; Protocol in `mission_runtime`, adapters in `specify_cli.context`;
    per-seam default-param DI (`x or Default()`); one adapter per port; **no shared DI container**; **no
    port on the frozen context**.
  - Corollaries: resolver = handle→mission resolution only (not the `target_branch` field reader, not the
    `merge/ordering` aggregate); the blind-primitive non-fold rule restated (C-007); **no new layer-ledger
    edge** (the ledger-dodge and why — #2173 drains this ledger); no process cache; fail-closed-loud.
  - Follow the ADR template under `docs/adr/`; freshen the docs page-inventory via the generator if the
    freshness gate trips (do not hand-edit the inventory).

### T019 — New AST gate
- New `tests/architectural/test_mission_resolver_walker_gate.py`:
  - **G-1**: no `src/` code performs a raw `iterdir()`/`glob()`/`scandir()` enumeration of `kitty-specs/`
    except `FsMissionResolver` and a **token-keyed allowlist**.
  - **G-2**: allowlist keyed on module/symbol tokens, never line numbers.
  - **G-3**: the gate derives its scan scope from `src/` (cannot go blind to an unscanned root).
  - **Seed the allowlist with the full ~16-walker census** so the gate is green on introduction — incl.
    the anti-fold set (`status/identity_audit.py`, `merge/ordering.py`, `core/paths.py:816/835`), the
    advisory/enumeration walkers (`charter_activate.py`, `doctrine/template_catalog.py`,
    `retrospective/summary.py`, `cli/commands/materialize.py`, `cli/commands/retrospect.py`,
    `_coordination_doctor.py`, `_identity_audit.py` (note: `cli/commands/_identity_audit.py` is a distinct
    file from `status/identity_audit.py` — both are walkers), `agent/mission_feature_resolution.py`,
    `git/sparse_checkout.py`, `release/changelog.py`, `_read_path_resolver.py:1409`) and migration-only
    walkers. **Discriminate** enumeration-of-all-missions from single-mission-dir access.
  - **Scan-root discrimination (squad):** key the gate on walks of the **`kitty-specs/`** tree
    specifically. `doctrine/template_catalog.py:138` walks the **doctrine missions tree** and
    `charter/neutrality/lint.py` walks a charter tree — NOT `kitty-specs/`. Do NOT list them (category
    mismatch that inflates the census); a scan-root-keyed gate never matches them anyway. Verify the live
    walker set with a census grep before finalizing the count.
  - Add a free-function-caller note (or a companion assertion) so new `resolve_mission` call sites can't
    silently multiply without notice.

### T020 — Verify green-on-introduction + anti-mutant
- Confirm the gate passes with the seeded allowlist, and add a negative test: a planted raw `iterdir()` of
  `kitty-specs/` outside the allowlist makes the gate fail (proves it bites).

## Branch Strategy
Planning branch and merge target: `feat/mission-resolver-port-2173`. Lane worktree per `lanes.json`.

## Definition of Done
- ADR committed under `docs/adr/3.x/`; docs freshness green.
- New gate passes with the full census allowlist and fails on a planted violation.
- `ruff`/`mypy` clean.

## Risks / reviewer guidance
- Allowlist must be **token-keyed** (F5) and derive scope from `src/` (F1 blind-spot avoidance).
- Reviewer plants a raw walker to confirm the gate bites, and confirms the census count matches the live
  walker set (run the census grep).

## Activity Log

- 2026-07-08T21:15:16Z – claude:sonnet:architect-alphonso:implementer – shell_pid=931732 – Assigned agent via action command
- 2026-07-08T21:53:35Z – claude:sonnet:architect-alphonso:implementer – shell_pid=931732 – ADR + AST walker gate (5 tests incl anti-mutant); allowlist from live census; FULL arch green (exit 0); ruff clean
- 2026-07-08T21:53:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=994733 – Started review via action command
