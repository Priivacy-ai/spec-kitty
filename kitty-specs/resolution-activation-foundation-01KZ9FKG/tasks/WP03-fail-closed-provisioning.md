---
work_package_id: WP03
title: Fail-closed provisioning (fresh-init + migration parity)
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- NFR-004
planning_base_branch: feat/resolution-activation-foundation
merge_target_branch: feat/resolution-activation-foundation
branch_strategy: Planning artifacts for this mission were generated on feat/resolution-activation-foundation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/resolution-activation-foundation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-resolution-activation-foundation-01KZ9FKG
base_commit: db9c1cb939c43dc45bcb2bf92cb79722492ee436
created_at: '2026-08-05T20:17:00.894943+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
history:
- at: '2026-08-05'
  actor: claude
  note: Authored during /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/provisioning/__init__.py
- src/specify_cli/provisioning/default_charter.py
- tests/specify_cli/cli/commands/test_init_provisioning.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/init.py
- src/specify_cli/provisioning/__init__.py
- src/specify_cli/provisioning/default_charter.py
- tests/specify_cli/cli/commands/test_init_provisioning.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: run `/ad-hoc-profile-load python-pedro` (role: implementer). Adopt
its identity, boundaries, and quality discipline before reading further.

## Objective

Make fresh-init projects carry an explicit `mission_type_activations` set **copied** from the provisioned
default charter, so the implicit fallback (removed in WP04) can go away without leaving new projects with
zero mission types. Fail closed if the default charter cannot be provisioned. This WP is the load-bearing
prerequisite for WP04.

Governing: spec FR-009/010/011, NFR-004; contracts C-A3/C-A4/C-A5; data-model Seam 2 (I-8/I-9/I-10);
research D-04/D-07. **Root** (independent of WP01/WP02); **gates WP04**.

## Context

- Today `spec-kitty init` writes NO activation keys; both rc35 migrations
  (`m_3_2_0rc35_default_charter_pack`, `m_3_2_0rc35_activate_builtin_mission_types`) fail-**open** on
  absent config. So removing the fallback without init provisioning = zero mission types for new projects.
- The provisioned surface is `src/charter/packs/default.yaml` (`mission_type_activations: [software-dev,
  documentation, research, plan]`). The migration uses `merge_pack_into_config(..., force=False)`.
- **Operator decision**: keep BOTH rc35 migrations unchanged (no consolidation).

## Subtasks

### T014 — RED acceptance test
Create `tests/specify_cli/cli/commands/test_init_provisioning.py`: (a) a brand-new `init` writes an
explicit, non-empty `mission_type_activations` copied from `default.yaml` (C-A3/SC-003); (b) a broken
install missing `default.yaml` fails closed with an actionable error (C-A4); (c) re-running provisioning
on an already-provisioned config is byte-identical and preserves a custom (non-built-in) entry
(C-A5/NFR-004/I-8). Must fail first.
**Copy-vs-rescan discriminator (post-tasks squad — REQUIRED):** `default.yaml` currently authors exactly
the disk roster `[software-dev, documentation, research, plan]`, so a naive test passes whether the
implementer COPIES or RE-SCANS. Add a discriminating case that fails a re-scan implementation: use a
fixture `default.yaml` whose `mission_type_activations` **differs** from the disk roster (e.g. a subset or
an extra custom id) and assert the provisioned config matches the **fixture**, not the disk roster — OR
provision with `SPEC_KITTY_PACKS_ROOT` pointed at an empty tree and assert copy still succeeds (a re-scan
would resolve empty/raise). This is what enforces D-07/I-10 (copy, not re-scan).

### T015 — Provisioning helper (copy, not re-scan)
Add `src/specify_cli/provisioning/default_charter.py` with a helper that reads `packs/default.yaml`'s
authored `mission_type_activations` and writes it into project `.kittify/config.yaml` **verbatim**
(union with any present custom entries; NO intersection against the built-in catalog; NO re-derivation via
`builtin_mission_type_id_set()` — D-07/I-10, keeps this WP decoupled from the resolver env). Reuse the
existing `merge_pack_into_config` semantics where practical. Fail closed (raise) if `default.yaml` is
missing.

### T016 — Wire into `init.py`
Call the helper during fresh-project init so the activation surface is seeded. **Re-anchor** the insertion
around #3211's `_REVIEW_CYCLE_GITATTRIBUTES_ENTRY` constant + `_ensure_event_log_merge_attributes`
addition (textual only — no semantic interaction). Preserve `SPEC_KITTY_TEMPLATE_ROOT` behavior (C-009).

### T017 [P] — Migration-parity regression
Add/extend a test asserting both rc35 migrations are unchanged in identity and remain idempotent (no edit
to migration files). This guards the operator decision to keep both.

### T018 — Green the tests
`tests/upgrade/*` + the new init-provisioning test green. Run from the primary checkout; if any test
touches a daemon/real port, run it `-n0`.

## Branch Strategy

Planning/base and merge target: `feat/resolution-activation-foundation`. Enter the resolved workspace via
`spec-kitty implement WP03` — the lane is computed from `lanes.json`.

## Definition of Done

- C-A3 fresh-init provisioning green (copied, not re-scanned); C-A4 fail-closed; C-A5/NFR-004 idempotent +
  customization-safe.
- Both rc35 migrations unchanged; T017 regression green.
- `mypy --strict` + `ruff` clean; complexity ≤15; no new suppressions.

## Risks / reviewer guidance

- **Do NOT touch `charter/pack_context.py` or `mission_type_profiles.py`** — those are WP04's owned files;
  removing the fallback is WP04, which depends on this WP.
- Confirm the helper COPIES `default.yaml` (does not re-scan the tree) — this is what keeps IC-05
  independent of the PACKS_ROOT-sensitive resolver (D-07).
- Authored empty `mission_type_activations: []` must NOT trigger provisioning (C-008) — preserve it.
- **FR-011 fail-closed applies to the fresh-init path.** The two rc35 migrations intentionally stay
  fail-**open** on absent config (operator decision: migrations unchanged; absent config = not yet a
  spec-kitty project = nothing to migrate). This is not a miss — the fresh-init provisioning is the new
  fail-closed guarantee; T017 asserts the migrations are untouched.
