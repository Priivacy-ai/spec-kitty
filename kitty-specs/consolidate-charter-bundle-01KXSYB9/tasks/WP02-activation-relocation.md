---
work_package_id: WP02
title: Activation relocation (charter.yaml owns activation; config keeps a pointer)
dependencies:
- WP01
requirement_refs:
- FR-012
- FR-013
- FR-014
- FR-015
- C-005
tracker_refs:
- '#2773'
- '#2519'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_pack_context_charter_yaml.py
- tests/charter/test_activation_engine_charter_yaml.py
execution_mode: code_change
owned_files:
- src/charter/activation_engine.py
- src/charter/pack_manager.py
- src/charter/pack_context.py
- src/specify_cli/cli/commands/charter/interview.py
- src/specify_cli/doctrine/org_charter.py
- tests/charter/test_pack_context_charter_yaml.py
- tests/charter/test_activation_engine_charter_yaml.py
role: implementer
tags: []
shell_pid: "383053"
shell_pid_created_at: "1784382220.72"
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective

Relocate the project **activation state** (flat `activated_*` / `activated_kinds` / `mission_type_activations`) out of `.kittify/config.yaml` INTO `charter.yaml`, and re-point the activation engine + reader. `config.yaml` keeps only non-doctrine config + a one-line `charter:` **pointer**. This is a **behavior-preserving relocation** — the activation-parity + DRG-filter behavior must stay byte-identical.

**Authoritative**: [`data-model.md`](../data-model.md) (config entity + INV-2/4/5/8/9), [`contracts/active-doctrine-resolution.md`](../contracts/active-doctrine-resolution.md), [`contracts/charter-yaml-schema.md`](../contracts/charter-yaml-schema.md) G3/G7. Consumes WP01's `CharterYaml` + shared write helper.

## Context / grounding
- `src/charter/pack_context.py:150 from_config`, `:218 _load_config`, `:239-288 _read_activated_*` — the single read seam; consumers auto-follow via the `PackContext` instance.
- `src/charter/activation_engine.py:359 commit_plan` — the REAL write primitive (data-source-agnostic; writes whatever mapping/path handed). Carries config.yaml-specific error strings (`:183`).
- `src/charter/pack_manager.py:703-753 merge_defaults` (absent-key seed) + `_save_config` (ruamel round-trip).
- `src/charter/packs/default.yaml:5-38` — flat activation shape (the fallback/seed).

## Subtasks

### T006 — `from_config` resolves charter.yaml via the config pointer + reads flat activation
- `_load_config` reads `config.yaml`; add resolution of the `charter:` pointer → load `charter.yaml`; read the FLAT activation keys from charter.yaml (not config).
- `org_packs` / pack roots STAY in `config.yaml` → `from_config` is a **two-file read** (G7).
- Preserve the **three-state** contract exactly (`_read_activated_*`): absent → default-pack fallback (`load_default_pack_activation_ids`), `[]` → `frozenset()` fail-closed, populated → exact. NEVER convert absent→`[]` (SC-008).

### T007 — `commit_plan` writes activation into charter.yaml
- Re-point `commit_plan` to write the flat activation keys into `charter.yaml` (via WP01's shared write helper — mutate the `activation` section, preserve others). It is data-source-agnostic, so this is mostly path/target + **re-wording the `config.yaml`-specific diagnostics/error strings** (`:183`) to name charter.yaml.

### T008 — `merge_defaults` / `_save_config` + the other two activation writers via the shared helper
- Route `merge_defaults` (absent-key seed) and its save through WP01's shared write helper so it preserves governance/catalog/metadata (INV-9). It still only fills ABSENT keys.
- ⚠ **BLOCKER (paula) — two more activation writers write into config.yaml and MUST re-point to charter.yaml, or interview/org-required activations silently stop taking effect (a split-brain the parity guard won't catch):**
  - `src/specify_cli/cli/commands/charter/interview.py:97,111` `_append_promote_selections` (promotes interview selections via `promote_activations`) → write the charter.yaml `activation` section (via the shared helper).
  - `src/specify_cli/doctrine/org_charter.py:421-429` `_promote_org_required_to_config` (unions org-required ids) → write charter.yaml `activation`.
  - Both use the data-source-agnostic `promote_activations`/`commit_plan` — the fix is re-pointing the path/target they pass (config.yaml → charter.yaml) + the save callback. C-002 OK (specify_cli may import the charter helper).

### T009 — config.yaml pointer + fail-loud
- On migrated projects `config.yaml` carries `charter: .kittify/charter/charter.yaml`. Resolve it; **fail loud** (re-homed #2530 / clear error) when the pointer names a missing/unreadable file (INV-5). Distinguish "pointer present, charter.yaml missing" (raise) from "no project config at all" (default-pack fallback — `_load_config` absent→`{}` branch).

### T010 — Tests
- `tests/charter/test_pack_context_charter_yaml.py`: from_config reads activation from charter.yaml via pointer; two-file read; three-state fidelity; dangling pointer raises; absent-config → default.
- `tests/charter/test_activation_engine_charter_yaml.py`: commit_plan writes charter.yaml activation, preserving other sections.
- **MUST stay GREEN** (behavior-preserving — reference, verify at aggregate; owned by WP04): `tests/doctrine/test_activation_parity_guard.py` and the pack_context/activation_engine suites.

## Known coupling (tidy-first, one PR)
The parity check (`consistency_check.py:199`) reads config activation directly and is re-pointed in **WP04**. Between this WP and WP04 the parity guard may read a now-empty config → transiently red *within the branch*. That is expected in the tidy-first sequence; the aggregate PR is green (NFR-005). Do NOT try to "fix" parity here (that file is WP04's — no overlap). If the pre-review gate flags the parity test, note the coupling and let WP04 close it.

## ATDD (red-first)
Red-first through `PackContext.from_config`: assert it reads `activated_directives` from `charter.yaml` (via pointer) and that `config.yaml` no longer needs `activated_*` — RED until T006.

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP01); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- Activation read+write on charter.yaml; config keeps the pointer; three-state + fail-closed + default-pack fallback preserved; two-file read.
- ruff + mypy --strict clean; complexity ≤15. Owned tests green; parity/DRG-filter behavior preserved.

## Reviewer guidance
- Verify NO activation is read from `config.yaml` post-WP; verify absent-key is NOT converted to `[]`; verify dangling pointer fails loud; verify `commit_plan` writes via the shared helper (section preservation).

## Activity Log

- 2026-07-18T13:10:49Z – claude:sonnet:python-pedro:implementer – shell_pid=296320 – Assigned agent via action command
- 2026-07-18T13:41:51Z – claude:sonnet:python-pedro:implementer – shell_pid=296320 – Activation relocated to charter.yaml (flat root keys) via config.yaml charter: pointer. Two-branch design (pointer absent=legacy config.yaml read/write unchanged; pointer present=charter.yaml via WP01 shared helper) preserves all existing tests byte-for-byte. Writes for activate/deactivate/merge_defaults/interview-promotion/org-required-promotion all route through resolve_activation_write_target + update_charter_yaml_section (INV-9 section preservation verified in tests). Gates: ruff clean, mypy --strict clean on changed src (2 pre-existing unrelated errors noted, not introduced), 163 tests green across owned+reference+consumer suites including test_activation_parity_guard.py (no red from the WP02/WP04 coupling window). Two pre-existing unrelated failures observed and left untouched: dead-symbol gate flags WP01/WP03/WP07-owned unconsumed symbols, and test_dead_subapp_exports_removed in activate.py (unrelated __all__ drift, file untouched by this diff).
- 2026-07-18T13:43:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=383053 – Started review via action command
- 2026-07-18T13:50:40Z – user – shell_pid=383053 – APPROVED. Dual-branch (pointer-conditional) is a CORRECT TRANSITIONAL migration-compat design, not a permanent split-brain: INV-5 fail-loud is honored (present-but-dangling pointer RAISES; the config.yaml path is reachable ONLY when the pointer is genuinely ABSENT = un-migrated), and that absent-branch is behavior-preserving (reads/writes where a pre-relocation project stored activation). Canonical charter.yaml is used the instant a pointer exists. All 5 writers re-pointed via WP01 shared helper (update_charter_yaml_section, section-preserving); C-002 clean (no specify_cli import in src/charter/); three-state fidelity byte-identical (absent->default, []->frozenset, populated->exact; never absent->[]); INV-2 held (test_migrated_project_ignores_stale_activated_keys). Gates GREEN: ruff clean; mypy only the 2 pre-declared pre-existing errors (org_charter:306 + interview decorator, zero-diff, last touched 161d5c0b6); 40 owned+parity tests + 255 consumer tests pass (parity guard green, no WP02/WP04 transient red). MISSION-LEVEL HAND-OFF (not a WP02 defect): no production code writes the charter: pointer yet — spec-kitty init writes NO pointer and scaffolds no charter.yaml, so NEW projects currently fall to the config.yaml branch permanently. WP07 migration mints the pointer for EXISTING projects; an explicit owner (WP07 or a #2519 init-scaffold follow-up) MUST ensure new-project init also mints it, else the transitional absent-branch silently becomes permanent for new projects and can never be retired. Anti-pattern checklist: all 8 PASS.
