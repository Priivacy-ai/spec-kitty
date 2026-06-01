---
work_package_id: WP09
title: Pack-manager catalog core (kind tables + list_available)
dependencies:
- WP01
- WP10
requirement_refs:
- FR-026
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/charter/pack_manager.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/charter/pack_manager.py
- tests/charter/test_pack_manager_catalog.py
role: implementer
tags: []
---

# WP09 — Pack-manager catalog core (kind tables + list_available)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Re-point `pack_manager` onto the canonical kind/ID vocabulary (WP01), extend `list_available` to include org/project layers with source-layer annotation and `id:`-aware IDs (FR-026, C-008), decouple the layer segment from the kind directory, and thin `activate`/`deactivate` to delegate into the activation engine (WP10). This is the catalog/activation core refactor; it owns all of `pack_manager.py`.

## Context

- Spec FR-026; research R-009 (`YAML_KEY_MAP`/`_KIND_TO_DOCTRINE_DIR` re-declare the kind set), R-011-D (`list_available` discards the `id:` field and returns filename stems; `ctx` ignored "reserved for future org-pack support" — this is that future).
- Data model §1, §6. Contract C4.4 (list scope feeds WP16). C-008 (roots resolved in specify_cli, passed as data).

### Code map

- `src/charter/pack_manager.py:104` `_KIND_TO_DOCTRINE_DIR` (hyphen keys, hardcoded `built-in` segment + suffix), `YAML_KEY_MAP`, `list_available` (~:371-416, built-in only, discards `id:`), `activate` (~:176-258), `deactivate` (~:260-336, `sys.exit` smell at ~:309).
- WP01: `ArtifactKind.from_operator_token`, `ArtifactKind.glob_pattern`, `charter/kind_vocabulary.py` resolver.
- WP10: `charter/activation_engine.py` (`plan_activation`/`commit_plan`).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP01 + WP10.

## Subtasks

### T039 — Derive kind tables from the canonical resolver

**Steps**: Replace the hand-maintained `YAML_KEY_MAP` and `_KIND_TO_DOCTRINE_DIR` with derivations from `ArtifactKind` (+ `mission-type`) via WP01. Kind validation uses `from_operator_token` (structured error on unknown). Keep config YAML key derivation stable (`activated_<plural>` / `mission_type_activations`).

**Validation**: - [ ] no second kind enumeration remains in `pack_manager`; existing kind→key/dir mappings preserved (parity test).

### T040 — `list_available` across layers + id-aware

**Steps**: Change `list_available(ctx, kind, *, layer_roots: list[Path])` (or accept resolved roots as data) to scan built-in + org + project, returning entries annotated by source layer and using the artifact `id:` (via WP01 resolver), not the filename stem. Org/project roots are passed in as data (resolved in specify_cli per C-008) — do not import `specify_cli`.

**Validation**: - [ ] returns org/project artifacts with layer; IDs match the `id:` field.

### T041 — Decouple layer from kind dir

**Steps**: Split `_KIND_TO_DOCTRINE_DIR` into kind→(base dir, glob-from-`ArtifactKind`) and iterate the layer segment ({built-in, org, project}); reuse `ArtifactKind.glob_pattern` instead of re-declaring suffixes. (Templates handled separately by WP18 — leave a clear extension point.)

**Validation**: - [ ] built-in scan unchanged; org/project scan added via the same loop.

### T042 — Thin activate/deactivate delegation

**Steps**: Make `activate`/`deactivate` call `activation_engine.plan_activation(...)` + `commit_plan(...)` (WP10). Replace the `deactivate` `sys.exit(1)` with a typed exception raised by the engine and surfaced by the CLI (WP12). Keep `pack_manager`'s public API stable.

**Validation**: - [ ] activate/deactivate delegate; no `sys.exit` in `pack_manager`; public API stable.

### T043 — Tests

**Steps**: `tests/charter/test_pack_manager_catalog.py` — list_available across layers (built-in/org/project) with a fixture pack; kind-table parity vs the previous mapping; id-aware IDs.

**Validation**: - [ ] green; ruff/mypy clean.

## Definition of Done

- [ ] Kind tables derived from canonical resolver; `list_available` covers org/project with layer + `id:`; layer decoupled from kind dir; activate/deactivate thin. CC-2 + CC-4 pass.

## Risks

- `pack_manager` is central — many callers. Keep the public signatures stable; add new params as keyword-only with safe defaults.
- C-008: roots must be passed as data; do not reach into `specify_cli`.

## Reviewer Guidance (reviewer-renata)

- Confirm no kind set is re-declared (CC-4).
- Confirm `list_available` no longer discards the `id:` field and covers all layers.
- Confirm `charter` still does not import `specify_cli`.
