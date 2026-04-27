---
work_package_id: WP04
title: Safety registry with fail-closed default
dependencies: []
requirement_refs:
- FR-008
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
agent: "claude:opus:python-reviewer:reviewer"
shell_pid: "88877"
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/safety.py
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/safety.py
- tests/specify_cli/compat/test_safety.py
- tests/architectural/test_safety_registry_completeness.py
priority: P0
tags: []
---

# WP04 — Safety registry with fail-closed default

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP04 --agent <name>` from `lanes.json`.

## Objective

Implement the central safety registry that classifies each CLI invocation as `Safety.SAFE` or `Safety.UNSAFE` for the purpose of the schema-mismatch gate. Seed the registry centrally for known-safe commands. Anything not registered is `UNSAFE` (fail-closed) — this is the property that protects the user from new commands being silently allowed under an incompatible schema.

## Context

- Spec: FR-008 (gate before unsafe commands), FR-011 (read-only/help/diagnostic commands remain available), §"Safe / Unsafe Command Classification".
- Plan: §"Engineering Alignment" Q3-A with the user's refinement: central seeding, fail-closed for unregistered commands, no mechanical per-file edit pass.
- Research: [`research.md`](../research.md) §R-10.
- Data model: [`data-model.md`](../data-model.md) §1.5 (`Safety`), §1.12 (`Invocation`).
- Existing code: `src/specify_cli/migration/gate.py` already has `_EXEMPT_COMMANDS = {"upgrade", "init"}` — the seed for the new registry expands on this.

## Subtasks

### T014 — `Safety` enum + seeded `SAFETY_REGISTRY`

**Steps**:
1. In `src/specify_cli/compat/safety.py`:
   - `class Safety(str, Enum): SAFE = "safe"; UNSAFE = "unsafe"`.
   - `SafetyPredicate = Callable[["Invocation"], Safety]` type alias.
   - Module-level `SAFETY_REGISTRY: dict[tuple[str, ...], SafetyPredicate | None]` — keys are `command_path` tuples (e.g. `("upgrade",)`, `("agent","mission","branch-context")`); value `None` means "always safe", value `SafetyPredicate` means "ask the predicate". Anything not in the registry is treated as UNSAFE.
2. **Seed entries** (inline at module scope, no per-file edits required):
   - `("upgrade",)` → None (always safe — remediation path)
   - `("init",)` → None (creates project, no metadata yet)
   - `("status",)` → None (read-only)
   - `("dashboard",)` → None *initially* — a later mission package replaces this with a mode predicate.
   - `("doctor",)` → None *initially* — a later mission package replaces this with a mode predicate.
   - `("--help",)` and `("--version",)` are short-circuited *before* the planner runs (handled in the typer-callback wiring package). Still register `("help",)` and `("version",)` for completeness.
   - `("agent", "mission", "branch-context")` → None (read-only).
   - `("agent", "mission", "check-prerequisites")` → None (read-only).
   - `("agent", "mission", "setup-plan")` → None (read-only — does not mutate project).
   - `("agent", "context", "resolve")` → None (read-only).
   - `("agent", "tasks", "status")` → None (read-only).
3. Add a comment block at the top documenting the rule: **"If you add a new CLI command, register it here or it will be treated as UNSAFE under schema mismatch."**

**Files**: `src/specify_cli/compat/safety.py`.

**Validation**: registry contains the seed entries; `Safety` enum exposed.

### T015 — `register_safety()` API + `classify(invocation)` with fail-closed default

**Steps**:
1. `register_safety(command_path: str | tuple[str, ...], predicate: SafetyPredicate | None = None) -> None`:
   - Accepts either a string (single command name like `"dashboard"`) or a tuple (multi-level path).
   - String form is normalised to `(string,)`.
   - Updating an existing entry replaces the prior predicate (predictable for later mode-predicate overrides).
2. `classify(invocation: "Invocation") -> Safety`:
   - Look up `invocation.command_path` in `SAFETY_REGISTRY`.
   - If not found: return `Safety.UNSAFE` (fail-closed).
   - If found and value is `None`: return `Safety.SAFE`.
   - If found and value is callable: return `predicate(invocation)`. Wrap the call in try/except; any exception from a predicate falls through to `Safety.UNSAFE` (defensive).
3. Typing: `Invocation` is defined in the planner package (later mission package). To avoid an import cycle, declare a `Protocol` locally in `safety.py` describing the fields `safety.classify` actually reads (`command_path: tuple[str, ...]`, `raw_args: tuple[str, ...]`). Or use a `TYPE_CHECKING` guard on the import. Either is fine; document the choice.

**Files**: `src/specify_cli/compat/safety.py` (extend).

**Validation**:
- `classify(Invocation(command_path=("status",), ...)) == Safety.SAFE`.
- `classify(Invocation(command_path=("not-a-real-command",), ...)) == Safety.UNSAFE`.
- A predicate that raises is treated as UNSAFE.

### T016 — Architectural test: every typer command is either registered or observably unsafe

**Steps**:
1. `tests/architectural/test_safety_registry_completeness.py`:
   - Walk the typer app (likely accessible via `from specify_cli.cli.main import app` or similar — inspect existing entry point).
   - For each registered command (recursively, for subgroups like `agent`), build the command_path tuple.
   - Assert: every command_path is either present in `SAFETY_REGISTRY` *or* `classify(...)` returns `Safety.UNSAFE` for it.
   - This is a **soft** test: it does NOT enforce that every command is registered safe. It only enforces the policy: unregistered ⇒ unsafe.
2. Test file lives under `tests/architectural/` (create the directory if it doesn't exist).

**Files**: `tests/architectural/__init__.py` (new if missing), `tests/architectural/test_safety_registry_completeness.py`.

**Validation**: `pytest tests/architectural/test_safety_registry_completeness.py -v` green. Specifically, if a hypothetical unknown command `("explode",)` is checked, the test passes because classify returns UNSAFE.

### Plus: `tests/specify_cli/compat/test_safety.py`

Cover:
- Seeded entries return SAFE.
- Unregistered entries return UNSAFE.
- Predicate registered via `register_safety` is consulted.
- A predicate that raises is treated as UNSAFE.
- `register_safety` overrides an existing entry.
- Threading note: the registry is accessed concurrently in tests — confirm the simple dict is acceptable (Python GIL ensures atomic dict ops; document this).

## Definition of Done

- [ ] `compat/safety.py` exposes `Safety`, `SAFETY_REGISTRY`, `register_safety`, `classify`.
- [ ] Seed entries cover the safe commands listed in spec §"Safe / Unsafe Command Classification" that exist today.
- [ ] Fail-closed semantics enforced and tested.
- [ ] Architectural test passes for the live typer app.
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.
- [ ] Coverage ≥ 90% on `safety.py`.

## Risks

- The typer app structure may differ from what's assumed — inspect `src/specify_cli/cli/` to discover the actual entry point and command tree before writing the architectural test.
- `dashboard` and `doctor` are seeded as unconditionally safe in this package. A later mission package will override them with mode predicates. This is fine because:
  - With this package alone, the gate is no stricter than today (dashboard/doctor were not gated before).
  - With the later predicate package, the registrations become mode-aware.
  - At no point are these commands made unsafe-by-default (which would be a regression).

## Reviewer Guidance

1. **Fail-closed**: a fresh registry (no seeds) classifies every invocation as UNSAFE.
2. **Predicate safety**: a predicate that raises does NOT crash the planner.
3. **No import cycle**: `safety.py` does not import from `planner.py`. Use `TYPE_CHECKING` or the local Protocol pattern.
4. **Comment for posterity**: the "register or it will be unsafe" comment is present.
5. **Architectural test correctness**: the test must walk the actual typer command tree, not a mock.

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Activity Log

- 2026-04-27T09:05:39Z – claude:sonnet:python-implementer:implementer – shell_pid=82236 – Started implementation via action command
- 2026-04-27T09:10:37Z – claude:sonnet:python-implementer:implementer – shell_pid=82236 – Ready: safety registry seeded + fail-closed + arch test
- 2026-04-27T09:10:58Z – claude:opus:python-reviewer:reviewer – shell_pid=88877 – Started review via action command
