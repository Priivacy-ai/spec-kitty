---
work_package_id: WP02
title: 'Functional fix: Optional provisioning descriptor + non-error diagnostic'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-007
- FR-011
- NFR-001
- NFR-003
planning_base_branch: issue-1931-ci-rework-test-remainders
merge_target_branch: issue-1931-ci-rework-test-remainders
branch_strategy: Planning artifacts for this mission were generated on issue-1931-ci-rework-test-remainders. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into issue-1931-ci-rework-test-remainders unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Functional fix
history:
- at: '2026-09-08T14:42:18Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/
create_intent:
- tests/upgrade/_fixtures.py
- tests/upgrade/test_upgrade_guard_absent.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/upgrade/assessment.py
- src/specify_cli/skills/installer.py
- src/specify_cli/upgrade/finalize.py
- tests/upgrade/_fixtures.py
- tests/upgrade/test_upgrade_guard_absent.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objective

Make absent-authority provisioning a **non-fatal, deferred no-op decided once at the assessment/compiler layer**, surfaced as a **non-error** `deferred_provisioning` diagnostic, with the installer guard reduced to a pure integrity validator — and **guarantee the finalizer does NOT create the authority** (C-001). (FR-001, FR-002, FR-003, FR-004, FR-007, FR-011, NFR-001, NFR-003.)

## Context — the corrected seam (read research.md Decisions 1–2)

- The guard `ValueError` at `skills/installer.py:428` is **already caught** (`installer.py:665-668`) → `error`-severity diagnostic → poisons `PreparedUpgradeRepairs.complete` (`assessment.py:65`) → `activation_errors` → failed outcome (`finalize.py:59-62`). So "stop raising" is NOT enough.
- There are **two** provisioning authorities. The finalizer applies the RAW `PreparedUpgradeRepairs.provisioning` (built at `assessment.py:120`, applied at `upgrade.py:1035`). A benign guard alone lets that raw `.apply()` emit a `"create"` effect (`assessment.py:100`) — i.e. it performs the #4047 create-from-absent we DEFER. **You must null the Optional descriptor at the assessment layer so there is nothing to apply.**

## Subtasks & Guidance

### T005 — RED-first (adopt a pre-existing witness, signal-bound)
Run `tests/upgrade/test_upgrade_idempotency.py::test_no_migrations_no_op_repeat_is_clean_exit_zero` and confirm it fails RED on the current base. **Capture the RED traceback** and confirm it contains the literal `Managed skill provisioning requires an existing authority` originating in the provisioning/guard path (not an unrelated assertion) — paste it in the Activity Log. Post-fix, the same nodeid must be green with its traceback gone; capture both. (FR-011 — adopt this pre-existing test as the witness; do NOT author a synthetic repro on a different subsystem. A RED that is red for an unrelated reason does NOT satisfy this subtask.)

### T006 — Optional descriptor, nulled on absent authority
Make `PreparedUpgradeRepairs.provisioning` `Optional` (`upgrade/assessment.py:48`). When the authority is absent (`write.before_bytes is None` or `write.absent_parents`), set it to `None` at the single assessment/compiler seam, and ensure `provisioning_effects` emits **no** `create` effect and **no** parent-dir create effects (`assessment.py:87-100,165`). This is the single decision consumed by guard/recheck/effects/finalizer (Decision 1).

### T007 — Non-error diagnostic; completeness preserved (via owned layer, not upgrade.py)
On the absent path emit a **non-error** diagnostic carrying the `deferred_provisioning` signal (see `contracts/deferred-provisioning-diagnostic.md`). `PreparedUpgradeRepairs.complete` must stay `true` (not poisoned); the outcome must not be `failed` solely due to the absent authority.

**Ownership:** populate the diagnostic on the outcome / `result.rendered_json` from **your owned files** (`assessment.py`/`finalize.py`) so it flows out through WP01's generic `_report_upgrade_outcome` render seam and the pass-through JSON payload — do NOT edit `cli/commands/upgrade.py` (WP01-owned). Only if the generic seam is genuinely insufficient, take a single recorded out-of-map edit to `upgrade.py` with a one-line rationale (charter ownership-map leeway; sequential after WP01). The signal MUST NOT land in `errors` or `warnings`.

### T008 — Guard → pure integrity validator (non-vacuous)
Reduce `_prepare_skill_provisioning` (`installer.py:416-442`) so it raises ONLY on a genuinely malformed/non-canonical descriptor (integrity), not on the benign "nothing to provision" case. Keep `_recheck_skill_provisioning` (`:445-473`) untouched for the create case (that is #4047).

**Non-vacuity (DIRECTIVE_043) — pinned so the guard cannot be gutted to `pass`:** the negative test MUST drive a **present-authority, structurally non-canonical** descriptor that actually reaches `_prepare_skill_provisioning`, and assert the **exact** integrity `ValueError` (message substring) is raised **from that function** — not merely that some exception occurs, and not via an absent-authority shape (which is now benign).

**C-006 guard-reduction regression lock:** add an assertion that a **present-but-degenerate** authority (`before_bytes == b""`, empty/corrupt `config.yaml`) does NOT hard-error / does not produce a fatal exit through the reduced guard (healing it stays out of scope, but the guard reshape must not regress non-fatal behavior for it).

### T009 — Finalizer performs NO create (C-001) + guard-aligned test
Ensure `finalize_upgrade`/`_finalizer_step_provision` (`finalize.py`, `upgrade.py:1035`) does nothing to apply when the descriptor is `None`. Create `tests/upgrade/test_upgrade_guard_absent.py` asserting, on a config-absent project driven through the real `upgrade()`: exit 0; outcome `up_to_date`; the `deferred_provisioning` **content/signal value** present per `contracts/deferred-provisioning-diagnostic.md` (NOT merely a key-exists check) with `errors == []` **and** `warnings == []` (proving the dedicated non-error channel); and **the `.kittify/config.yaml` authority file is NOT created** after the run (INV-1). The adopted witness (T005) must now be green.

### T010 — Shared fixture builder (both variants live here)
Create `tests/upgrade/_fixtures.py` exposing two builders: a **config-absent** project (metadata.yaml only, git-initialized — the legacy shape) and a **real-init-ed** project (via `CliRunner().invoke(app, ["init", ...])`). WP02's guard-aligned test uses the config-absent builder. **Smoke-exercise the real-init-ed builder in at least one WP02 assertion (or a trivial self-test)** so it is not dead-on-arrival for WP03 (which is its only downstream consumer). **Cross-reference:** WP03 T012 imports the config-absent builder; WP03 T013 imports the real-init-ed builder — enumerate both here so any future WP03 need forces a T010 update rather than a WP03 edit to this WP02-owned file. Keep the file import-only for consumers.

## Branch Strategy
- **Planning base**: `issue-1931-ci-rework-test-remainders` · **Merge target**: `issue-1931-ci-rework-test-remainders` · lane per `lanes.json`.

## Definition of Done
- Adopted witness flips RED→green with the captured guard-signal traceback gone (both tracebacks in the Activity Log).
- `test_upgrade_guard_absent.py` green: skip + **no-create** + diagnostic **content** asserted (not presence-only) with `errors == [] and warnings == []`.
- Guard non-vacuity: negative test drives a **present-authority non-canonical** descriptor and asserts the exact integrity `ValueError` **from `_prepare_skill_provisioning`**; a `b""` degenerate authority does NOT hard-error (C-006).
- `deferred_provisioning` populated from owned files (no `upgrade.py` edit, or one recorded out-of-map edit); `complete` not poisoned; no `create`/parent-create effect when absent.
- Real-init-ed builder smoke-exercised in WP02; ruff + mypy clean, no new suppressions; behavior for init-ed projects unchanged (WP03 oracle confirms).

## Reviewer guidance
- Verify the deferral decision lives at the assessment layer (single seam), NOT a guard special-case; confirm the raw `.apply()` cannot create the authority; confirm the guard is non-vacuous; confirm the diagnostic is non-`errors`/non-`warnings`.
