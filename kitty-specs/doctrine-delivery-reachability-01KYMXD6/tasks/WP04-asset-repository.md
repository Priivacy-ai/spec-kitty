---
work_package_id: WP04
title: Asset repository and service wiring
dependencies:
- WP03
requirement_refs:
- C-001
- C-002
- C-006
- FR-003
- FR-004
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Assets
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/assets/
create_intent:
- src/doctrine/assets/repository.py
- tests/doctrine/assets/test_repository.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/assets/**
- src/doctrine/service.py
- tests/doctrine/assets/**
- tests/doctrine/test_service.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP04 — Asset repository and service wiring

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`** — the *resolved* definition. **Do not
read the raw `*.agent.yaml`**.

---

## Objective

An asset identifier resolves to a filesystem path, across built-in / organisation / project tiers,
**fail-closed**. Today `ResolveTransitiveRefsResult.assets` holds bare ids and no production code
reads them; the one shipped asset is reached only by a hard-coded repo path in a test.

## Context

The kind exists (delivered by `doctrine-template-asset-kinds-01KX2YQ7`): `AssetManifest`
(`src/doctrine/assets/models.py:27`, frozen, `extra="forbid"`, fields `id/mime/path/title`), the glob
`*.asset.yaml`, DRG node kind, pack validation. What is missing is the **repository and path
resolution**.

The one shipped asset: `src/doctrine/assets/built-in/docs_structural_lint.py` with sidecar
`docs_structural_lint.py.asset.yaml` (`id: common-docs-structural-lint`, `path:
built-in/docs_structural_lint.py`).

Read [`contracts/asset-resolution.md`](../contracts/asset-resolution.md) A-1 through A-6 and the
top-three traps.

### The three traps (each costs a day)

1. **Anchor asymmetry.** `_built_in_dir("assets")` returns `<root>/assets/built-in`, and blob paths
   anchor at its **parent** — `path: built-in/docs_structural_lint.py` proves it. `_org_dirs` and
   `_project_dir` return `<root>/assets`, anchoring at the directory itself. A single shared anchor
   rule produces `.../assets/built-in/built-in/...`.
2. **Non-recursive overlay glob.** `BaseDoctrineRepository._project_scan` (`src/doctrine/base.py:140`)
   uses `glob`, not `rglob`. An org-pack manifest at the ADR-mandated `assets/<pack>/x.asset.yaml` is
   never discovered. Override it — the `StyleguideRepository` is the precedent. The override must
   return `list[Path]`, not `Iterable[Path]` — the base declares `list[Path]` and widening it is a
   Liskov violation mypy flags, which NFR-002 forbids silencing.
3. **Containment lives in the wrong layer.** The only containment helper today is in
   `specify_cli.doctrine.pack_validator`, which `doctrine` may **not** import (C-001). Call
   `doctrine.drg.org_pack_config.resolve_relative_path_within_root` directly. "Just joining the paths"
   ships a `..`/symlink escape the validator would have caught.

## Subtasks

### T019 — `AssetRepository` with recursive overlay discovery
1. Create `src/doctrine/assets/repository.py`, subclassing `BaseDoctrineRepository[AssetManifest]`
   with `_schema = AssetManifest`, `_glob = "*.asset.yaml"`.
2. Override `_project_scan` to `rglob` (returning `list[Path]`).
3. Export from `src/doctrine/assets/__init__.py`.

### T020 — Per-identifier source-path tracking [P]
1. The base class records only a layer *label* in `_provenance`, never the file. Track the source
   file per id, modelled on `AgentProfileRepository._source_paths`.

### T021 — `resolve_path` with fail-closed containment
1. `resolve_path(asset_id) -> Path`. Missing id raises a typed error naming the id.
2. Containment enforced via `org_pack_config.resolve_relative_path_within_root`; traversal/symlink
   escapes raise a typed error (NFR-006).

### T022 — Anchor asymmetry
1. Built-in blob paths anchor at the parent of `assets/built-in`; org/project anchor at the dir.
2. Test the built-in case explicitly — it is the one that silently doubles the path.

### T023 — Convert `service.py` `_PROJECT_KIND_DIRS` to the hoisted authority
1. WP03 hoisted the canonical mapping into `artifact_kinds.py`. Consume it here; delete
   `service.py:19`'s copy.
2. The project-tier asset directory now comes from the single authority (contract A-5).

### T024 — `DoctrineService.assets` property
1. Add the `assets` property mirroring `glossary_packs` (`service.py:140`).
2. The `charter/resolver.py` `__getattr__` delegation surfaces it for free — no charter change here.

### T025 — Repository tests
1. Tier precedence: built-in / org / project, more-specific wins, shadowed tier reported.
2. rglob discovery of a nested org manifest.
3. Containment negatives (traversal, symlink).
4. Missing id raises the typed error.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP03 — the hoisted
kind mapping must exist. `spec-kitty implement WP04` resolves the workspace.

**File-ownership note**: WP03 touched `service.py`'s kind mapping and left the canonical form; you own
`service.py` for the asset property and the `_PROJECT_KIND_DIRS` removal. WP05 owns the CLI surface;
you own the repository and service.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/doctrine/assets/test_repository.py tests/doctrine/test_service.py tests/doctrine/test_template_asset_e2e.py -q
```

Baseline: `test_template_asset_e2e.py` green (part of the 50-passed asset baseline).

## Definition of Done

- [ ] `AssetRepository` resolves across three tiers, recursively, fail-closed
- [ ] Built-in anchor asymmetry handled and tested
- [ ] `resolve_path` returns a path, never a bare id; escapes refused with a typed error
- [ ] `service.py` consumes the hoisted mapping; no local `_PROJECT_KIND_DIRS` copy remains
- [ ] `DoctrineService.assets` resolves the shipped asset
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean, **no `# type: ignore` on the `_project_scan` override**

## Risks

| Risk | Mitigation |
|---|---|
| Path doubling on the built-in tier | T022 tests it explicitly |
| Org assets never discovered | rglob override, `list[Path]` return |
| Symlink/`..` escape | containment via `org_pack_config`, not path-join |
| Liskov `# type: ignore` temptation | return `list[Path]`; NFR-002 forbids the suppression |

## Reviewer guidance

1. Resolve the shipped `common-docs-structural-lint` and confirm the path exists.
2. Place an org manifest one dir deep; confirm discovery.
3. Craft a manifest whose `path` escapes the root; confirm refusal.
4. `grep -n "_PROJECT_KIND_DIRS" src/doctrine/service.py` — should be gone.
