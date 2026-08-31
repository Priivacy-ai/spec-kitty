---
work_package_id: WP03
title: 'US1: empty-charter governance scoping + default charter asset (#3064)'
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-010
planning_base_branch: feat/charter-delivery-finish-context-degod
merge_target_branch: feat/charter-delivery-finish-context-degod
branch_strategy: Planning artifacts for this mission were generated on feat/charter-delivery-finish-context-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-delivery-finish-context-degod unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
history:
- at: '2026-07-30'
  actor: planner-priti
  note: WP authored from plan IC-02b/IC-03 + post-plan squad governance-leak finding.
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- src/doctrine/assets/built-in/charter_scaffold_minimal.yml
- src/doctrine/assets/built-in/charter_scaffold_minimal.yml.asset.yaml
- tests/charter/test_empty_charter_governance_agreement.py
- tests/doctrine/test_charter_scaffold_asset.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/charter/compact.py
- src/doctrine/assets/built-in/charter_scaffold_minimal.yml
- src/doctrine/assets/built-in/charter_scaffold_minimal.yml.asset.yaml
- tests/charter/test_empty_charter_governance_agreement.py
- tests/doctrine/test_charter_scaffold_asset.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```
Apply the resolved initialization/boundaries/directives/tactics; confirm which in one line, then proceed.

## Objective

Close the governance-context half of issue **#3064**: under an empty charter the dispatch governance block currently leaks the **full built-in `DIR-###` canon** (proven below), which would reach the generic agent. Scope the empty-charter governance block so it emits no doctrine. Also ship the **minimal charter scaffold asset** users can copy instead of authoring a charter. Depends on **WP02** (the `empty_charter_fallback` signal).

Design authority: [`../spec.md`](../spec.md) (FR-010, FR-005), [`../contracts/empty-charter-fallback.md`](../contracts/empty-charter-fallback.md), [`../research.md`](../research.md) (Decisions 4, 6).

## Critical context (verified against code — the leak is real)

- `_render_compact_governance` → `render_compact_view` (`src/charter/compact.py:216-230`) **merges `resolver_directives`** from `_resolve_governance_summary(repo_root)` into the `Directive IDs:` block, **independent of the profile**.
- Under an empty charter, `resolve_project_governance` → `_resolve_directives_selection` (`src/charter/resolver.py:233-260`) has empty `selected_directives`, so it returns `fallback = sorted(doctrine_catalog.directives)` — **all built-in directives** (`catalog_fallback`). Hence a generic-agent dispatch would emit every `DIR-###`.
- **Bounded fix only**: suppress the resolver-directive merge on the empty-charter/generic-agent path. Do NOT globally change `_resolve_directives_selection` (broad blast radius across every compact-context consumer). Prefer a flag on the fallback path (e.g. `render_compact_view` consulting the composite empty-charter predicate, or a `suppress_project_resolver` param threaded from the fallback). Keep the change inside `compact.py` where possible; a minimal `build_charter_context` param passthrough is an acceptable declared out-of-map coupled edit to `context.py` (owned by WP06) if unavoidable — record the rationale.
- Asset precedent: `src/doctrine/assets/built-in/docs_structural_lint.py.asset.yaml` sidecar has `id`, `mime`, `path`, `title`; `AssetManifest` is frozen/extra-forbid; `path` carries the leading `built-in/` segment. Resolve via `spec-kitty doctrine asset path <id>` (resolve/copy-only, no install). Do NOT reuse `src/charter/packs/default.yaml` (it activates ALL built-ins — the inverse of a minimal starter).

## Subtasks

### T012 — Red-first governance-agreement test
Create `tests/charter/test_empty_charter_governance_agreement.py`: resolve `build_charter_context` for a dispatch under a wholly-empty charter (compose with WP02's fallback) and assert the governance `Directive IDs:` block is **empty** (or exactly `generic-agent`'s own cited directives) and no specialist marker is present. This test is **RED** today (the leak). Use a realistic empty `.kittify` fixture.

### T013 — Empty-charter governance scoping
Implement the bounded suppression so the empty-charter/generic-agent governance block does not merge the project catalog-fallback directives. Keep the change scoped to the fallback path; verify no other compact-context consumer changes behaviour (run the existing `tests/charter/test_*compact*`/`test_reference_block.py` etc.). Complexity ≤ 15.

### T014 — Ship the minimal charter scaffold asset
Add `src/doctrine/assets/built-in/charter_scaffold_minimal.yml` (a minimal, valid, activatable curated starter charter) and its sidecar `charter_scaffold_minimal.yml.asset.yaml`:
```yaml
id: common-charter-scaffold-minimal
mime: application/yaml
path: built-in/charter_scaffold_minimal.yml
title: Minimal charter scaffold
```
Add a one-line comment in each file cross-referencing `src/charter/packs/default.yaml` (activate-all) so a later agent does not conflate them.

### T015 — Asset mime guard + resolvability test
Create `tests/doctrine/test_charter_scaffold_asset.py`: assert the sidecar passes `pack_validator._check_asset_mime`, and that `spec-kitty doctrine asset path common-charter-scaffold-minimal` resolves to the shipped file (exit 0). Frame the mime test as a guard (py3.11 already maps `.yml`→`application/yaml`).

### T016 — Asset activatability test
In the same test file, activate the scaffold in a temp repo and assert the resulting charter validates (non-empty, activatable) and **no pre-existing user charter is modified** (User Customization Preservation). This is FR-005's real done-line (not just resolvability).

## Branch strategy
Planning base `feat/charter-delivery-finish-context-degod`; merge target `main` (PR). Depends on WP02 — enter via `spec-kitty agent action implement WP03 --agent claude` (implement gate enforces WP02 approved/done first).

## Definition of Done
- [ ] T012 red-first agreement test committed before T013 (RED → GREEN).
- [ ] Empty-charter dispatch `Directive IDs:` block empty; no other compact consumer perturbed.
- [ ] Scaffold asset resolves, passes mime guard, and **activates to a valid charter** without touching a user charter.
- [ ] Asset id is `common-charter-scaffold-minimal` (not "default-charter"); cross-ref comment present.
- [ ] ruff + mypy --strict clean.

## Risks
- Over-broad suppression changing directive resolution for other consumers (keep it bounded to the fallback; run the compact-context test suite).
- Asset naming collision with `packs/default.yaml` (distinct id + cross-ref).

## Reviewer guidance
Confirm RED→GREEN on T012; verify `_resolve_directives_selection` is NOT globally changed; run `tests/charter/` compact/reference suites to confirm no collateral; verify the activatability test really activates + asserts user-charter untouched.
