---
work_package_id: WP02
title: Pre-import .kitty.env loader + config pointer
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- NFR-001
- NFR-005
planning_base_branch: fix/operator-config-ergonomics
merge_target_branch: fix/operator-config-ergonomics
branch_strategy: Planning artifacts for this mission were generated on fix/operator-config-ergonomics. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/operator-config-ergonomics unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history:
- '2026-08-16: authored by /spec-kitty.tasks'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/bootstrap/
create_intent:
- src/specify_cli/bootstrap/__init__.py
- src/specify_cli/bootstrap/env_file.py
- tests/specify_cli/bootstrap/test_env_file_loader.py
- tests/architectural/test_bootstrap_import_purity.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/bootstrap/__init__.py
- src/specify_cli/bootstrap/env_file.py
- src/specify_cli/__init__.py
- pyproject.toml
- tests/specify_cli/bootstrap/test_env_file_loader.py
- tests/architectural/test_bootstrap_import_purity.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load` before anything else.

## Objective

Seed a two-tier `.kitty.env` into `os.environ` BEFORE any spec-kitty module is imported, so the ~88 scattered `os.environ.get` reads (incl. import-time ones) work unchanged. Add the single `config.yaml` `env_file` pointer. Contracts: [../contracts/kitty-env-loader.md](../contracts/kitty-env-loader.md) (C-LDR-1..7). Plan PPC-3/PPC-5. Deps: **WP01** (uses `kernel.env_expand` + the state-root primitive).

## Branch Strategy
Base + merge target: `fix/operator-config-ergonomics`. Lane worktree from `lanes.json`.

## Subtasks

### T006 — `bootstrap/env_file.py` (NEW): parser + two-tier merge
- Hand-rolled `KEY=VALUE` parser (stdlib only): strip `export `, strip surrounding quotes, full-line `#` comments, `KEY` matches `[A-Za-z_][A-Za-z0-9_]*` else skip+debug-log; values literal (no in-value interpolation).
- Tiers: home = `kernel.paths.get_runtime_state_root() / ".kitty.env"`; per-repo = `<repo_root>/.kittify/.kitty.env` (ancestor-walk for `.kittify`/`.git`). **Merge `{**home, **repo}` first, THEN one `os.environ.setdefault` pass** so precedence is real-env > per-repo > home. (A naive per-tier `setdefault` inverts repo/home — do NOT do that.)

### T007 — `config.yaml` `env_file` pointer (`FR-005`)
- Read ONLY the `env_file` key from `.kittify/config.yaml` at bootstrap (no full model load; do not choke the ~30 config readers). Resolve its one `${SPEC_KITTY_HOME}` expansion via `kernel.env_expand.expand_env_template(..., inject_defaults=True)` with the state-root default. Default when the key/file is absent: `<state-root>/.kitty.env`. The key must live OUTSIDE any `extra="forbid"` pydantic block (`doctrine/org_charter.py:112/136`) — verify which model owns the section.

### T008 — Fail policy (`FR-004a`)
- Absent `.kitty.env` → warn-and-continue (exit 0; init/CI). Present-but-unreadable `env_file` → fail loud (non-zero, name the file — it gates auth). Malformed line → skip + debug log. A `SPEC_KITTY_HOME=` line inside `.kitty.env` (locator recursion) → ignore + warning.

### T009 — Wire the shim (`src/specify_cli/__init__.py`)
- Call `bootstrap.env_file.load_operator_env_file()` as the FIRST statements of the module (before the `SPEC_KITTY_TEST_MODE` read at `:36` and before completion). Import must stay stdlib + `kernel` + `core.env` only. Bump `pyproject.toml` version + add the `__init__.py`-change CHANGELOG note is deferred to WP06's CHANGELOG (single-PR); the version bump lives here (C-007).

### T010 — Tests (C-LDR-1..7 + import purity)
- `test_env_file_loader.py`: precedence (real>repo>home), pre-import (`SPEC_KITTY_SYNC_MINIMAL_IMPORT` set only in file → `sync/__init__.py:455` branch active), fail policy (absent/unreadable/malformed), locator recursion, single-pointer resolution, cross-platform (parametrize POSIX/Windows state root).
- `test_bootstrap_import_purity.py`: assert `specify_cli.bootstrap.env_file`'s transitive import set contains no module with an import-time `os.environ` read (allow only stdlib + `kernel` + `core.env`).

## Definition of Done
- **RED-first**: write the failing C-LDR-1..7 + import-purity tests before implementing.
- C-LDR-1..7 green; import-purity arch test green.
- **NFR-001 (measured)**: a test asserts the loader's added startup overhead is within the noise floor of the existing completion benchmark (name the benchmark it runs; delta vs a no-`.kitty.env` baseline, not an absolute ms). If no completion benchmark exists to extend, add a micro-benchmark test and cite the budget source.
- `ruff`/`mypy` clean; no new dependency (no `python-dotenv`).

## Reviewer guidance
- The merge-then-setdefault order is the load-bearing correctness point — verify per-repo beats home AND real-env beats both.
- Verify the shim truly runs before `__init__.py:36` (not in `main()`), proven by the `SYNC_MINIMAL_IMPORT` test.
- Verify the home default is the STATE root (`.spec-kitty`), not `.kittify`, and reuses WP01's kernel primitive (no 4th resolver).
