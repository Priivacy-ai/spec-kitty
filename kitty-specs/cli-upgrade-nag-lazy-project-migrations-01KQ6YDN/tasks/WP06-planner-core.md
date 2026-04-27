---
work_package_id: WP06
title: Compatibility planner core (Plan, Decision, decide, plan)
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-001
- FR-008
- FR-009
- FR-010
- FR-022
- FR-023
- FR-024
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/planner.py
- src/specify_cli/compat/messages.py
- src/specify_cli/compat/_init_exports.py
- tests/specify_cli/compat/test_planner.py
- tests/specify_cli/compat/test_messages.py
priority: P0
tags: []
---

# WP06 — Compatibility planner core

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP06 --agent <name>` from `lanes.json`. This WP depends on WP01–WP05; the lane scheduler will not start it until those are merged or available in the lane base.

## Objective

The integration WP. Implement the compatibility planner that subsumes "is this command safe?" and "should we nag?" into a single `Plan` value. After this WP, `from specify_cli.compat import plan, Plan, Decision` is the **single authority** for compatibility decisions across the CLI.

## Context

- Spec: FR-001, FR-008, FR-009, FR-010, FR-022, FR-023, FR-024 (the planner is the single authority).
- Plan: §"Engineering Alignment" Q1-A and §"Implementation phasing" step 2.
- Data model: [`data-model.md`](../data-model.md) — entities (§1.1–1.12), state machine (§2), validation rules (§4), public API (§5).
- Contracts: [`contracts/compat-planner.json`](../contracts/compat-planner.json) — JSON output shape that `plan.rendered_json` must match.
- Security checklist: CHK019 (YAML safe-load), CHK020 (256 KB cap), CHK021 (schema_version int range), CHK028 / CHK029 (output sanitisation), CHK051 (fail-closed planner).

## Subtasks

### T021 — Dataclasses (Plan, Decision, CliStatus, ProjectStatus, MigrationStep, Fr023Case, Invocation)

**Steps**:
1. In `src/specify_cli/compat/planner.py`, declare every dataclass / enum from [`data-model.md`](../data-model.md) §1.1–1.4, §1.6–1.9, §1.12. Use `frozen=True` dataclasses; use `enum.StrEnum` for string enums where possible (Python 3.11+).
2. `Invocation.from_argv(argv: list[str] | None = None) -> Invocation` classmethod parses argv into `command_path`, `raw_args`, `is_help`, `is_version`, `flag_no_nag`, plus environment-derived `env_ci` and `stdout_is_tty`. The argv parsing is "best effort" — it doesn't need to fully replicate typer; it splits up to the first flag and treats the rest as raw_args.
3. Re-export `Safety`, `LatestVersionResult`, `LatestVersionProvider`, `NagCacheRecord`, `InstallMethod`, `UpgradeHint` from their respective WPs (transparent re-export).

**Files**: `src/specify_cli/compat/planner.py`.

**Validation**: every dataclass round-trips via `dataclasses.asdict`; `Invocation.from_argv(["spec-kitty","upgrade","--dry-run"])` returns sensible values.

### T022 — `messages.py` catalog with sanitisation

**Steps**:
1. In `src/specify_cli/compat/messages.py`:
   - `MESSAGES: dict[Fr023Case, MessageTemplate]` — each template has a human format string and a JSON case label. The format strings are **literal strings** with named placeholders (e.g. `{installed} is available; you have {latest}.`).
   - `render_human(case: Fr023Case, *, plan: "Plan") -> str` — fills in placeholders from the Plan; sanitises every placeholder value against the regex from data-model §4.
   - `render_json(plan: "Plan") -> dict[str, Any]` — builds a JSON dict that validates against `contracts/compat-planner.json`. Use stdlib jsonschema or hand-write the assertions; either is fine.
2. Sanitisation: any string field that flows from external input (latest version from PyPI, installed version, project root path, install method command/note) is checked against its regex before substitution. If it fails, substitute the literal `"<unavailable>"` (do NOT raise).
3. Output stability: `render_json` always emits the same set of keys for a given `Decision`; missing-but-typed fields are explicitly `None`/`null`. This lets golden-file tests pin shape.

**Files**: `src/specify_cli/compat/messages.py`, `tests/specify_cli/compat/test_messages.py`.

**Validation**: each `Fr023Case` has a non-empty human render; each plan validates against the JSON schema.

### T023 — `decide()` table

**Steps**:
1. In `compat/planner.py`, implement `decide(project: ProjectStatus, safety: Safety, cli: CliStatus, invocation: Invocation) -> tuple[Decision, Fr023Case]`:
   - Pure function. No I/O.
   - Implements the table in [`data-model.md`](../data-model.md) §2 row-by-row, in order.
   - Returns `(Decision, Fr023Case)` together so callers don't have to map twice.
2. Edge: when project is `NO_PROJECT` and the command is `--cli` or unflagged `upgrade`, return `(ALLOW, NONE)` (or `(ALLOW_WITH_NAG, CLI_UPDATE_AVAILABLE)` if outdated). The user wants CLI guidance, not a project block.
3. Edge: when both `--cli` and `--project` flags are present (invocation.raw_args contains both), return `(BLOCK_INCOMPATIBLE_FLAGS, NONE)`. The `--cli`/`--project` detection is a simple substring check on raw_args; the actual flag parsing happens later in WP09's typer command.

**Files**: `src/specify_cli/compat/planner.py` (extend).

**Validation**: table tests over every (state × safety × outdated × invocation kind) combination.

### T024 — `plan(...)` entry point + YAML hardening

**Steps**:
1. In `compat/planner.py`:
   - `def plan(invocation: Invocation, *, latest_version_provider: LatestVersionProvider | None = None, nag_cache: NagCache | None = None, config: UpgradeConfig | None = None, now: datetime | None = None, project_root_resolver=None) -> Plan`.
   - Defaults: `latest_version_provider = NoNetworkProvider() if invocation.suppresses_network() else PyPIProvider()`; `nag_cache = NagCache.default()`; `config = UpgradeConfig.load()`; `now = datetime.now(tz=timezone.utc)`; `project_root_resolver = locate_project_root` (existing helper in `core.project_resolver`).
   - Steps follow data-model §2 pseudocode: build CliStatus, scan project, classify safety, build install method + hint, decide, list pending migrations (only when blocked), build Fr023Case, render messages, return `Plan`.
2. **YAML hardening** — `scan_project(cwd, project_root_resolver)`:
   - Resolve project root; if None → `ProjectStatus(state=NO_PROJECT, ...)`.
   - Stat `metadata.yaml`; if absent → `state=UNINITIALIZED`.
   - Refuse to read if file size > 262_144 bytes (CHK020) → `state=CORRUPT, metadata_error="oversized"`.
   - Read with the existing safe loader (`migration.schema_version.get_project_schema_version` or its hardened equivalent).
   - Validate `schema_version` is `int` in `[0, 1000]`; else `state=CORRUPT`.
   - Map result onto `ProjectState`.
3. **Fail-closed** (CHK051): if any unexpected exception arises in `plan()` itself, catch it, return a `Plan` with `decision=BLOCK_PROJECT_CORRUPT` and a metadata_error of `"planner_error"`. This guarantees the gate never silently allows an unsafe command due to a planner bug.
4. **Pending migrations**: when `decision == BLOCK_PROJECT_MIGRATION`, query `upgrade.registry` for migrations from `project.schema_version` to `MAX_SUPPORTED_SCHEMA`. Convert each to a `MigrationStep`. `files_modified` is `None` unless the migration exposes a way to compute it (most don't yet — leave `None`).

**Files**: `src/specify_cli/compat/planner.py` (extend).

**Validation**: Each FR-023 case is reachable from the public `plan()` entry with appropriate fixtures.

### T025 — Wire `compat/__init__.py` public API

**Steps**:
1. Replace the empty `compat/__init__.py` (created by WP01) with the public API per data-model §5:
   ```python
   from .planner import (
       Plan, Decision, Safety, Fr023Case, plan,
       CliStatus, ProjectStatus, MigrationStep, Invocation,
   )
   from .safety import classify, register_safety, SAFETY_REGISTRY
   from .provider import (
       LatestVersionProvider, LatestVersionResult,
       PyPIProvider, NoNetworkProvider, FakeLatestVersionProvider,
   )
   from .cache import NagCache, NagCacheRecord
   from .config import UpgradeConfig
   from ._detect.install_method import InstallMethod, detect_install_method
   from .upgrade_hint import UpgradeHint, build_upgrade_hint
   ```
2. Add an `__all__` listing the same names.
3. Note: this WP **owns** `__init__.py` (per ownership rules). WP01 created the placeholder; WP06 takes it over to populate.

**Files**: `src/specify_cli/compat/__init__.py` (overwrite the WP01 placeholder).

**Validation**: `from specify_cli.compat import plan; plan(Invocation.from_argv(["spec-kitty","--version"]))` returns a Plan with decision=ALLOW.

### T026 — Comprehensive tests (planner + messages)

**Steps**:
1. `tests/specify_cli/compat/test_planner.py`:
   - One test per Decision, using injected providers/caches and a fixture project.
   - Tests for the corrupt-metadata, missing-project, no-network, fresh-cache, expired-cache, version-key-mismatch, mode-aware-safety predicates.
   - Test the fail-closed catch: monkeypatch `decide` to raise; assert `plan()` returns BLOCK_PROJECT_CORRUPT with `metadata_error="planner_error"`.
   - Use parametrize to keep tests dense.
2. `tests/specify_cli/compat/test_messages.py`:
   - For each Fr023Case, render_human + render_json produce expected golden output.
   - Sanitisation rejects ANSI/shell-metachar inputs and substitutes `<unavailable>`.
   - JSON output validates against `contracts/compat-planner.json` (load schema, validate via stdlib `jsonschema` if available; else hand-check key set + types).

**Files**: `tests/specify_cli/compat/test_planner.py`, `tests/specify_cli/compat/test_messages.py`.

**Validation**: full pytest suite for `compat/` green; coverage on `planner.py` and `messages.py` ≥ 90%.

## Definition of Done

- [ ] Every entity in data-model.md exists with correct fields.
- [ ] `decide()` follows data-model §2 exactly.
- [ ] `plan()` is fail-closed for unexpected exceptions.
- [ ] `compat/__init__.py` exposes the full public API.
- [ ] `messages.py` renders every Fr023Case for human + JSON.
- [ ] JSON output validates against the contract schema.
- [ ] Coverage on `planner.py` + `messages.py` ≥ 90%.
- [ ] `mypy --strict src/specify_cli/compat/` clean.
- [ ] `ruff check` clean.
- [ ] No CLI surface modified yet (that's WP07/WP08/WP09).

## Risks

- The `upgrade.registry` API may not expose "list migrations from schema X to Y" cleanly. If it doesn't, add a small helper inside `_adapters/` (or the registry itself, with a one-line docstring change). Stay within owned files; if registry needs to change, surface that to the WP07 owner instead.
- `Invocation.from_argv` is best-effort. WP08 will replace it with a more rigorous typer-context-aware build inside `cli/helpers.py`. Keep the standalone version for tests / programmatic use.
- The fail-closed catch must wrap the entire body of `plan()`. Confirm via test that monkeypatching any inner function to raise still produces a clean Plan.

## Reviewer Guidance

1. **Single authority**: confirm `decide()` is the only place compatibility logic lives. No other module makes the safe/unsafe / nag/no-nag judgment.
2. **Fail-closed**: a planner that explodes does NOT leave the gate open.
3. **Sanitisation everywhere**: any string flowing into `rendered_human` or `rendered_json` is regex-checked.
4. **Schema fidelity**: `rendered_json` matches `contracts/compat-planner.json` for every example in the contract.
5. **Public API**: `from specify_cli.compat import …` works for every name in data-model §5.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent <name>
```
