---
work_package_id: WP05
title: Asset operator surface and the wheel proof
dependencies:
- WP03
- WP04
requirement_refs:
- C-002
- C-006
- FR-005
- FR-008
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 2 - Assets
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_doctrine_asset.py
create_intent:
- src/specify_cli/cli/commands/_doctrine_asset.py
- tests/specify_cli/cli/commands/test_doctrine_asset.py
- tests/docs/test_asset_resolution_wheel.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_doctrine_asset.py
- tests/specify_cli/cli/commands/test_doctrine_asset.py
- tests/docs/test_asset_resolution_wheel.py
- tests/docs/test_docs_structural_lint.py
- docs/api/cli-commands.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP05 — Asset operator surface and the wheel proof

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

An operator resolves a shipped asset from a **clean installation**, and this repository's own consumer
stops reaching the asset through a hard-coded repo path.

## Context

`SC-003` is the load-bearing criterion, and it is falsifiable **only from a built wheel in a clean
environment**. In-repo, `resolve_doctrine_root()` (`src/charter/catalog.py:153`) falls back to the dev
layout, so an in-repo test always passes and proves nothing. The wheel already contains the asset
(verified: `doctrine/assets/built-in/docs_structural_lint.py` and its sidecar are in
`spec_kitty_cli-*.whl`) — so this is an addressing fix, not a packaging one.

The hard-coded path to retire: `tests/docs/test_docs_structural_lint.py:50-53` reaches through
`_REPO_ROOT`. Repointing it through the resolver is FR-008's proof-by-first-user.

Read [`contracts/asset-resolution.md`](../contracts/asset-resolution.md) operator section A-7 to A-9.

## Subtasks

### T026 — `doctrine asset list` / `path` commands
1. Create `src/specify_cli/cli/commands/_doctrine_asset.py` with a Typer subapp:
   - `asset list [--json]` — all resolvable assets and their tiers
   - `asset path <asset-id> [--json]` — a resolvable path; unknown id exits non-zero naming the id
2. (Optional, in scope) `asset install <id> --to <dir>` — operator-invoked only. **No auto-install**
   (C-002).

### T027 — Register the asset subapp
1. WP03 left a one-line registration hook in `doctrine.py`. Wire the subapp there. If WP03's hook is
   absent, add the single import — record the one-line out-of-map edit with a rationale.

### T028 — Clean-environment wheel harness (SC-003)
1. `tests/docs/test_asset_resolution_wheel.py`: build the wheel, install into a temp venv, resolve
   `common-docs-structural-lint` with the **repository root absent** from resolution inputs.
2. This is the only place SC-003 can actually fail. Model the build/venv steps on any existing
   packaging test; keep it opt-in/marked if it is slow, and `log()` that it ran.

### T029 — Repoint the shipped-asset consumer
1. `tests/docs/test_docs_structural_lint.py:50-53` stops using `_REPO_ROOT`; it resolves the asset
   through `DoctrineService.assets` / `resolve_path`.
2. This is FR-008 — the fix proven by its first user.

### T030 — CLI reference entries
1. Add the two new visible Typer paths to `docs/api/cli-commands.md`, or the freshness gate
   (`scripts/docs/check_cli_reference_freshness.py`) emits `REF-MISSING`.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP03 (CLI kind map,
subapp hook) and WP04 (the repository). `spec-kitty implement WP05` resolves the workspace.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/test_doctrine_asset.py tests/docs/test_docs_structural_lint.py -q
# and the slow wheel proof, on its own:
PWHEADLESS=1 pytest tests/docs/test_asset_resolution_wheel.py -q
pytest tests/docs/test_check_cli_reference_freshness.py -q
```

## Definition of Done

- [ ] `doctrine asset path <id>` prints a resolvable path, exits 0; unknown id exits non-zero naming it
- [ ] The wheel harness resolves the shipped asset with the repo root absent — SC-003 can actually fail
- [ ] `test_docs_structural_lint.py` no longer reaches through `_REPO_ROOT` (FR-008)
- [ ] Both new paths are in `docs/api/cli-commands.md`; the freshness gate passes
- [ ] No file is installed into a consumer repo (C-002); NFR-001 respected
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| In-repo test passes vacuously | T028 is a wheel-in-clean-venv harness, the only falsifiable form |
| New Typer path trips REF-MISSING | T030 |
| Accidentally adding auto-install | C-002 — resolution and explicit invocation only |

## Reviewer guidance

1. Build the wheel yourself, install it into `/tmp`, run `doctrine asset path common-docs-structural-lint`
   from a directory outside the repo. It must resolve.
2. Confirm `test_docs_structural_lint.py` has no `_REPO_ROOT` reference.
3. Confirm nothing writes into a consumer project on upgrade.
