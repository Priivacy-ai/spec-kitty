---
work_package_id: WP01
title: Schema + manifest keystone (CharterYaml, manifest v2, shared write helper)
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-001
- C-004
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/charter/charter_yaml_io.py
- tests/charter/test_charter_yaml_model.py
- tests/charter/test_charter_yaml_io.py
execution_mode: code_change
owned_files:
- src/charter/schemas.py
- src/charter/bundle.py
- src/charter/charter_yaml_io.py
- tests/charter/test_bundle_manifest_model.py
- tests/charter/test_charter_yaml_model.py
- tests/charter/test_charter_yaml_io.py
- tests/cli/commands/test_charter_bundle_coverage.py
role: implementer
tags: []
shell_pid_created_at: "1784379527.3"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "278415"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML — do not act on the persona name alone.

## Objective

Author the **keystone** of the charter-bundle inversion: the `CharterYaml` structured model, the `CharterBundleManifest` **v2** (single schema bump), and the **single shared charter.yaml write helper** every other WP consumes. This WP unblocks WP02/WP03/WP06. It ships no behavior change on its own — it defines the target shape and the safe writer.

**Authoritative design** (read before coding): [`data-model.md`](../data-model.md) (charter.yaml shape + Landmine 1 + INV-9), [`contracts/charter-yaml-schema.md`](../contracts/charter-yaml-schema.md), [`contracts/manifest-v2.md`](../contracts/manifest-v2.md). Do NOT re-derive; implement what they specify.

## Context / grounding

- `src/charter/schemas.py:124 GovernanceConfig`, `:166 DirectivesConfig` — reuse as nested sub-models.
- `src/charter/bundle.py:34-52` (`SCHEMA_VERSION`, `BUNDLE_CONTENT_HASH_FILES`, filename constants), `:69-104 CharterBundleManifest` + `_validate:82-88`, `:107-125 CANONICAL_MANIFEST`, `:133 compute_bundle_content_hash`.
- Filename constants are duplicated: `bundle.py:36-51` (Path-form) + `sync.py:43-44` (str-form) — unify into one shared constant (campsite; do NOT re-scatter the new `charter.yaml` name).

## Subtasks

### T001 — `CharterYaml` pydantic model (`schemas.py`)
- Add `CharterYaml` (frozen) with: `schema_version: str` (`"2.0.0"`); `governance: GovernanceConfig`; `directives: DirectivesConfig`; a `catalog` sub-model (mission/template_set/languages[]/references[] — mirror the `references.yaml` body); **FLAT activation root fields** `activated_kinds`, `mission_type_activations`, `activated_directives`, `activated_tactics`, `activated_styleguides`, `activated_toolguides`, `activated_paradigms`, `activated_procedures`, `activated_agent_profiles`, `activated_mission_step_contracts` (each `list[str] | None`, three-state); `overrides` (open mapping, forward-compat); `metadata` (`generated_at`, `bundle_schema_version: int = 2`; NO `charter_hash`).
- ⚠ Activation is **FLAT at root** (paula BLOCKER-1) — matches `packs/default.yaml:5-38` so `pack_context._read_activated_*` reads it unchanged. Do NOT nest under an `activation:` key.
- **Validation**: `tests/charter/test_charter_yaml_model.py` — round-trips governance/directives/catalog + flat activation; rejects a nested `activation:` mapping.

### T002 — `CharterBundleManifest` v2 + `content_hash_files` (`bundle.py`)
- `SCHEMA_VERSION "1.0.0" → "2.0.0"`.
- `BUNDLE_CONTENT_HASH_FILES → ("charter.yaml",)`.
- Add a **NEW distinct field** `content_hash_files: list[Path]` to `CharterBundleManifest`, set to `[charter.yaml]` in `CANONICAL_MANIFEST`. **Do NOT put `charter.yaml` in `derived_files`.** `derived_files = []`, `derivation_sources = {}`, `tracked_files = [charter.md, charter.yaml]`, `gitignore_required_entries = []`.
- ⚠ **Landmine 1**: `_validate`'s `tracked ∩ derived = ∅` rule stays **UNTOUCHED** — charter.yaml is only in `tracked`. Do NOT relax it.
- Point `compute_bundle_content_hash` at `content_hash_files` (keep the per-file BOM-strip/CRLF recipe — NFR-001/#2732).
- **`first_missing_bundle_file` (`bundle.py:187`, #2758) — disposition (post-tasks squad)**: KEEP it. Once `BUNDLE_CONTENT_HASH_FILES = ("charter.yaml",)` it **auto-narrows** to a `charter.yaml` existence check — i.e. it becomes the desired fail-loud "charter.yaml missing" guard (C-003). Its caller (`_synthesis.py`) is re-messaged by WP03; its test assertion is updated by WP04. Do NOT delete it (it is NOT in `computer.py` — WP06 does not own it).
- **Validation**: `tests/charter/test_bundle_manifest_model.py` + `tests/cli/commands/test_charter_bundle_coverage.py` — manifest v2 constructs + validates; `derived_files == []`; `content_hash_files == [charter.yaml]`.

### T003 — Shared write helper (`src/charter/charter_yaml_io.py`, NEW — INV-9)
- Implement `load → mutate-owned-section → round-trip-save` for charter.yaml using **ruamel round-trip** (comment/format preserving). API shape: a function/class that loads charter.yaml, lets a caller mutate ONE named section (`governance` | `directives` | `catalog` | `activation` | `metadata` | `overrides`), and saves while preserving all other sections **byte-for-byte**.
- This is the ONLY writer path WP02 (activation), WP03 (catalog/metadata), and merge_defaults use. It structurally prevents the internal clobber (Landmine 3).
- Keep it in `src/charter/` (C-002: no `specify_cli` import).
- **Validation**: `tests/charter/test_charter_yaml_io.py` — writing `activation` preserves `governance`/`catalog` byte-for-byte, and vice versa.

### T004 — Unify the charter-filename constant (campsite, S1192)
- Introduce ONE shared `CHARTER_YAML` filename constant (Path + a str accessor if needed) in a single canonical home (e.g. alongside the existing bundle constants). Consumers in WP01–WP07 import it. Reconcile the existing duplicated `bundle.py:36-51` / `sync.py:43-44` sets so the new name is single-sourced (do NOT add a second copy).

### T005 — Tests
- Ensure the three test files above run green: `PWHEADLESS=1 pytest tests/charter/test_charter_yaml_model.py tests/charter/test_charter_yaml_io.py tests/charter/test_bundle_manifest_model.py tests/cli/commands/test_charter_bundle_coverage.py -q`.

## ATDD (red-first)
Write the failing test through the pre-existing entry point first: construct `CharterBundleManifest` v2 and assert `_validate` passes with `charter.yaml` tracked-not-derived (RED until T002), and a round-trip write preserves a sibling section (RED until T003).

## Branch Strategy
Planning artifacts were generated on `feat/consolidate-charter-bundle`. This WP branches from that base (per `lanes.json`); completed changes merge back into `feat/consolidate-charter-bundle` (then to `main` via PR — the operator merges). Execution worktree is allocated per computed lane.

## Definition of Done
- `CharterYaml` model with flat activation; manifest v2 with distinct `content_hash_files`, `derived_files=[]`, `_validate` untouched; shared write helper preserving non-owned sections; single filename constant.
- ruff + mypy --strict clean (zero new suppressions); complexity ≤15.
- All owned tests green. No behavior change shipped (pure foundation).

## Reviewer guidance
- Verify `_validate`'s disjointness rule was NOT relaxed and `charter.yaml ∉ derived_files`.
- Verify activation fields are FLAT (not nested).
- Verify the write helper is byte-preserving on non-owned sections (the anti-#2772-internal-clobber guarantee).
- Verify the filename constant is single-sourced (no re-scatter).

## Activity Log

- 2026-07-18T09:30:50Z – claude:sonnet:python-pedro:implementer – shell_pid=59383 – Assigned agent via action command
- 2026-07-18T09:32:20Z – user – Moved to planned
- 2026-07-18T12:43:31Z – claude:sonnet:python-pedro:implementer – shell_pid=240750 – Assigned agent via action command
- 2026-07-18T12:57:09Z – claude:sonnet:python-pedro:implementer – shell_pid=240750 – CharterYaml pydantic model (flat activation) + CharterBundleManifest v2 (content_hash_files=[charter.yaml], derived_files=[], _validate untouched) + shared charter.yaml write helper (charter_yaml_io.py, byte-preserving ruamel round-trip). ruff clean, mypy --strict clean, 67/67 owned tests green.
- 2026-07-18T12:58:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=278415 – Started review via action command
- 2026-07-18T13:08:02Z – user – shell_pid=278415 – Review passed (renata): landmines verified, gates green 67/67, scope clean; 28 out-of-scope hash-narrowing failures noted for downstream.
