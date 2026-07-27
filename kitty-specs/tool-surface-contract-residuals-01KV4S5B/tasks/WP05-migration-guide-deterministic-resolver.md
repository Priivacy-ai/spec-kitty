---
work_package_id: WP05
title: Migration guide & deterministic project-root resolver (#1944/#1965)
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
tracker_refs:
- '1944'
- '1965'
planning_base_branch: feat/tool-surface-contract-residuals
merge_target_branch: feat/tool-surface-contract-residuals
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract-residuals. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract-residuals unless the human explicitly redirects the landing branch.
created_at: '2026-06-15T05:20:00+00:00'
subtasks:
- T018
- T019
- T020
- T021
agent: "claude:opus:python-pedro:implementer"
shell_pid: "3967469"
history:
- date: '2026-06-15'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent:
- tests/specify_cli/core/test_paths.py
- docs/how-to/tool-surface-upgrade-and-repair.md
execution_mode: code_change
owned_files:
- src/specify_cli/core/paths.py
- tests/specify_cli/core/test_paths.py
- tests/specify_cli/cli/commands/test_doctor_skills.py
- docs/how-to/**
- docs/development/3-2-page-inventory.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile via `/ad-hoc-profile-load` (profile: **python-pedro**, role: implementer). Then return here.

## Objective

Close #1965 + #1944: make `SPECIFY_REPO_ROOT` authoritative so `test_doctor_skills_json_error_schema_stable` is deterministic (FR-007), and ship the user-facing Tool-vs-Agent upgrade/repair guide (FR-006). DIRECTIVE_037 Living Documentation Sync + `formalized-constraint-testing` (don't weaken the frozen error-envelope schema) + DIRECTIVE_034 test-first.

## Context

- `core/paths.py::locate_project_root` line ~79 only honors `SPECIFY_REPO_ROOT` when the target **also** has `.kittify/`. The doctor-skills error-schema test points the env var at a `.kittify`-less temp dir → the guard fails → Tier-2 walk-up finds the real checkout → leaks ambient `~/.claude` state → flaky test.
- **C-003 scope**: real `.kittify/` projects hit the same `get_main_repo_root(env_path)` branch either way → no behavior change for them. Only an explicitly-set, existing, non-`.kittify` path changes from silently-ignored to honored.
- The 3-way `locate_project_root` split (`project_resolver.py`, `__init__.py`) is **out of scope** — deferred to **#1971**; just note it.

## Subtasks (ATDD — tests first)

### T018 — RED tests (fix the resolver, do NOT weaken the schema)
- `tests/specify_cli/core/test_paths.py`: (a) set `SPECIFY_REPO_ROOT` to an existing `.kittify`-less temp dir; assert `locate_project_root()` returns it (not the ambient checkout) — **determinism must come from the `paths.py` resolver fix, not from test-local `monkeypatch` isolation** (that would leave #1965's root cause unfixed). (b) C-003 regression guard: a real `.kittify/` project resolves to the **same** root with and without `SPECIFY_REPO_ROOT` set.
- `test_doctor_skills_json_error_schema_stable`: make it deterministic with an ambient `~/.claude` present, from any cwd. **The asserted schema (keys/values) must be byte-identical before vs after** — the *only* permitted change is the environment setup (env-var/cwd). Loosening an exact-match to `in`, or dropping a required key, to dodge the ambient state is a rejection (it destroys the frozen-envelope contract this test exists to pin).

### T019 — Fix `paths.py`
Make `SPECIFY_REPO_ROOT` authoritative: when set and `env_path.exists()`, return `get_main_repo_root(env_path)` regardless of `.kittify/` presence (drop the `(env_path / KITTIFY_DIR).is_dir()` precondition at line 79). **Keep the `env_path.exists()` guard** (non-existent paths still fall through). Update the docstring to match (the env var is already declared "highest priority").

### T020 — User-facing migration/repair guide
Write a `docs/how-to/` guide covering: the Tool vs Agent vs Tool Surface terminology; how an upgrading or fresh-clone user repairs missing generated surfaces via `spec-kitty doctor tool-surfaces --fix`. Add it to the docs TOC and `docs/development/3-2-page-inventory.yaml`. It must be **lint-clean** against the docs-contract lint (WP04's gate).

### T021 — Note the split + verify (enumerated, not prose)
- Document (code comment + PR body) that `project_resolver.py` + `__init__.py` retain the simpler resolver and full consolidation is deferred to **#1971**.
- **Enumerate each of the 4 `project_resolver` callers** with a one-line evidence statement that it does NOT rely on env-var/worktree authority for correctness here — `cli/helpers.py`, `cli/commands/lint.py`, `compat/planner.py`, `core/__init__`. A checkable list, not "confirmed they're fine."
- Run: the new paths tests, the doctor-skills test (deterministic now), the docs-contract lint on the new guide, ruff + mypy --strict clean.

## Branch Strategy

Planning/merge branch: **`feat/tool-surface-contract-residuals`** (PR → `main`). Lane worktree from `lanes.json`. `safe-commit --to-branch feat/tool-surface-contract-residuals`; status transitions from primary CWD.

## Definition of Done

- `SPECIFY_REPO_ROOT` authoritative when the path exists; real `.kittify/` projects unaffected (C-003 regression test green).
- `test_doctor_skills_json_error_schema_stable` deterministic (passes with ambient `~/.claude`), frozen schema assertion intact.
- User-facing guide present under `docs/`, TOC/inventory-discoverable, docs-lint-clean.
- #1971 split noted; ruff + mypy --strict clean; #1944 + #1965 acceptance criteria met.

## Risks

- The `paths.py` change must not alter resolution for real `.kittify/` projects (keep `env_path.exists()`; the C-003 regression test guards this).
- Do not attempt the full 3-way consolidation here (that's #1971) — scope creep + import-cycle risk.

## Reviewer Guidance

Recommended reviewer: **reviewer-renata** (standard) + **architect-alphonso sign-off** on the `locate_project_root` boundary (confirm the `paths.py` change is C-003-safe and the deferred #1971 split is documented, not silently widened). Resolves **#1944** + **#1965** → terminal issue-matrix verdicts (`fixed`).

## Activity Log

- 2026-06-15T06:05:10Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – Assigned agent via action command
- 2026-06-15T06:21:36Z – claude:opus:python-pedro:implementer – shell_pid=3887319 – WP05 done. #1965: paths.py::locate_project_root now honours SPECIFY_REPO_ROOT whenever env_path.exists() (dropped the .kittify-precondition at old line 79; kept exists() guard). Determinism PROVEN from the resolver, not monkeypatch: direct probe shows OLD code returns the ambient checkout, NEW returns the explicit env root (tests/specify_cli/core/test_paths.py::test_env_root_authoritative_without_kittify). C-003 regression test green (test_c003_real_kittify_resolves_same_with_and_without_env). doctor.py UNTOUCHED so the not_in_project error envelope is byte-identical; test_doctor_skills_not_in_project_envelope_frozen pins it exactly, test_doctor_skills_json_error_schema_stable pins the full success schema via the env-authoritative path. #1944: docs/how-to/tool-surface-upgrade-and-repair.md (Tool vs Agent vs Tool Surface + doctor tool-surfaces --fix), added to toc.yml + 3-2-page-inventory.yaml; docs-lint-clean (0 findings) + SEO + terminology guard pass. 4 project_resolver callers enumerated in project_resolver.py docstring + below; #1971 split deferred+noted. ruff clean; mypy --strict clean on changed lines (2 pre-existing get_feature_target_branch Any-returns are baseline, out of scope). NOTE: editable install points at primary checkout; run tests with PYTHONPATH=src to exercise worktree code.
- 2026-06-15T06:22:48Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=3940282 – Started review via action command
- 2026-06-15T06:28:17Z – user – shell_pid=3940282 – Moved to planned
- 2026-06-15T06:29:00Z – claude:opus:python-pedro:implementer – shell_pid=3967469 – Started implementation via action command
- 2026-06-15T06:31:00Z – user – shell_pid=3967469 – cycle 2 implementation starting
- 2026-06-15T06:31:04Z – user – shell_pid=3967469 – cycle 2: committing 4-caller evidence block
