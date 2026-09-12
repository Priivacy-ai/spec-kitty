---
work_package_id: WP01
title: Kernel env-expansion seam
dependencies: []
requirement_refs:
- FR-006
planning_base_branch: fix/operator-config-ergonomics
merge_target_branch: fix/operator-config-ergonomics
branch_strategy: Planning artifacts for this mission were generated on fix/operator-config-ergonomics. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/operator-config-ergonomics unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- '2026-08-16: authored by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/kernel/
create_intent:
- src/kernel/env_expand.py
- tests/kernel/test_env_expand.py
- tests/kernel/test_packs_root_default.py
- tests/doctrine/test_org_pack_delegation.py
- tests/architectural/test_kernel_env_expand_no_upward_import.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/kernel/env_expand.py
- src/kernel/paths.py
- src/doctrine/drg/org_pack_config.py
- tests/kernel/test_env_expand.py
- tests/kernel/test_packs_root_default.py
- tests/doctrine/test_org_pack_delegation.py
- tests/architectural/test_kernel_env_expand_no_upward_import.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile via `/ad-hoc-profile-load` (profile: `python-pedro`, role: implementer). Follow its identity, boundaries, and TDD discipline for the rest of this WP.

## Objective

Create the single kernel-floor `${VAR}` expansion authority (two policies) plus the `${SPEC_KITTY_PACKS_ROOT}` default value, and make the existing org-pack expander delegate to it. This is the foundation every downstream WP consumes (provenance tokens, the `.kitty.env` loader). Contracts: [../contracts/env-expander.md](../contracts/env-expander.md) (C-EXP-1..5). Design: [../design-record.md](../design-record.md) D2; plan PPC-2/PPC-3.

## Branch Strategy

Planning/base branch: `fix/operator-config-ergonomics`; final merge target: `fix/operator-config-ergonomics`. Execution runs in the lane worktree resolved from `lanes.json` (allocated by `finalize-tasks`). Do not branch manually.

## Subtasks

### T001 — `get_packs_root_default()` + state-root primitive (`src/kernel/paths.py`)
- Add `def get_packs_root_default() -> Path: return get_built_in_pack_root().parent`. Rationale: `get_built_in_pack_root()` returns `…/packs/built-in`; the `${SPEC_KITTY_PACKS_ROOT}` token names the PARENT `…/packs`, and the env override rejoins `/built-in` (`paths.py:266`). Injecting the resolver's return would double-join. Export via `__all__`.
- Add a stdlib-safe state-root primitive the pre-import loader (WP02) can consume WITHOUT importing `specify_cli` — e.g. `get_runtime_state_root() -> Path` returning `$SPEC_KITTY_HOME` else the platform state root (`~/.spec-kitty` POSIX / `%LOCALAPPDATA%\spec-kitty` Windows via `platformdirs`, mirroring `specify_cli/paths/windows_paths.py:60-91`). Single `SPEC_KITTY_HOME` read here; keep the existing `get_kittify_home` (`.kittify`) untouched — do NOT collapse the two roots.

### T002 — `src/kernel/env_expand.py` (NEW)
- `expand_env_template(raw: str, *, inject_defaults: bool, environ: Mapping[str,str] | None = None) -> str`: `os.path.expanduser(os.path.expandvars(raw))`, then if `inject_defaults` substitute any surviving `${SPEC_KITTY_*}`/`$SPEC_KITTY_*` token from the injector registry; else a surviving token raises `UnresolvedEnvTokenError`.
- `UnresolvedEnvTokenError(ValueError)`. Migrate the ASCII token detector + empty-token check from `doctrine/drg/org_pack_config.py:71-106` here (single detector). Stdlib + `kernel.paths` only.

### T003 — Default-injection registry
- `_DEFAULT_INJECTORS: dict[str, Callable[[], str]] = {"SPEC_KITTY_PACKS_ROOT": lambda: str(get_packs_root_default())}`. Keep the mapping in `env_expand.py`; `CONFIG_HOME`/locator defaults are the caller's concern (WP02), not here.

### T004 — `org_pack_config` delegation (fail-loud EXACTLY preserved)
- Delegate the pure transform in `_expand_path_template` (`org_pack_config.py:82-90`) to a **NON-RAISING** expansion — i.e. call `expand_env_template(raw, inject_defaults=False)` in a mode that returns the string with surviving tokens intact for the caller to detect (do NOT let the kernel raise `UnresolvedEnvTokenError` here). The caller MUST keep BOTH of its existing guards: `_unresolved_env_token` (unset-token → `OrgPackEnvVarUnsetError`, `:93-106,253-262`) AND `_empty_expanded_env_token` (set-but-BLANK var → empty, no surviving token, `:100-106`). Net: the org-pack exception TYPE (`OrgPackEnvVarUnsetError`) and the set-but-blank fail-loud are byte-preserved; the kernel primitive only shares the `expanduser(expandvars(...))` + token-detector, not the raise policy for this caller.
- If `expand_env_template` cannot both fail-loud (for provenance callers via a raising mode) and stay non-raising here, expose the shared token-detector separately so `org_pack_config` reconstructs its exact errors. Document the chosen shape in the module docstring.

### T005 — Tests (C-EXP-1..5)
- `test_env_expand.py`: C-EXP-1 (default-inject unset → `get_packs_root_default()/built-in/...`, no literal token), C-EXP-2 (`inject_defaults=False` unset → raises), C-EXP-4 handled in `test_org_pack_delegation.py` (unset `local_path` token still raises the existing error).
- `test_packs_root_default.py`: C-EXP-3 (`get_packs_root_default() == get_built_in_pack_root().parent`; token + `/built-in` round-trips, no double-join).
- `test_kernel_env_expand_no_upward_import.py`: C-EXP-5 (assert `kernel.env_expand` imports nothing from `specify_cli`/`doctrine`; extend/mirror `test_kernel_no_doctrine_import`).

## Definition of Done
- All C-EXP-1..5 green; `org_pack_config` behavior unchanged (existing org-pack tests stay green).
- `ruff`/`mypy` clean; complexity ≤15; no new dependency.
- RED-first: write the failing C-EXP tests before the implementation.

## Reviewer guidance
- Verify `.parent` arithmetic and that unset `${SPEC_KITTY_PACKS_ROOT}` resolves via the same authority (not a hardcoded path).
- Verify the fail-loud vs default-inject split is one primitive with a boolean, not two expanders.
- Verify kernel gains no upward import (arch test present + green).
