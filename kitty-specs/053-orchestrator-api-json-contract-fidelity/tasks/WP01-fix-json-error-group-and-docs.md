---
work_package_id: WP01
title: Fix _JSONErrorGroup Error Handling + Docs
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-005
- NFR-001
- NFR-002
- C-001
- C-003
base_branch: 2.x
base_commit: 9812ee34905de737259c9019dd6e85fb9249a129
created_at: '2026-03-20T12:35:22.058330+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Core Fix
history:
- timestamp: '2026-03-20T12:31:02Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WVZGV7TH7WMR2CN9PZ
owned_files:
- docs/reference/orchestrator-api.md
- src/specify_cli/__init__.py
- src/specify_cli/cli/commands/__init__.py
- src/specify_cli/orchestrator_api/commands.py
- tests/agent/test_json_envelope_contract_integration.py
- tests/agent/test_orchestrator_commands_integration.py
wp_code: WP01
---

# Work Package Prompt: WP01 – Fix _JSONErrorGroup Error Handling + Docs

## Objectives & Success Criteria

- `_JSONErrorGroup` catches all `click.UsageError` and `click.Abort` exceptions at both the `invoke()` (nested dispatch) and `main()` (direct invocation) levels.
- All orchestrator-api commands produce JSON envelopes on stdout for both success and error cases, regardless of invocation path.
- No `--json` flag referenced in `docs/reference/orchestrator-api.md`.
- Existing sub-app tests in `tests/agent/test_json_envelope_contract_integration.py` and `tests/agent/test_orchestrator_commands_integration.py` still pass.
- Net code change is negative or zero (less code, not more).

## Context & Constraints

**Root cause** (from plan.md): When the orchestrator-api is registered as a sub-group of the root CLI via `app.add_typer()`, Click dispatches to it via `invoke()`, not `main()`. The existing `_JSONErrorGroup.main()` override is never called in this path — errors propagate to `BannerGroup`, which prints prose stderr.

**Key files**:
- `src/specify_cli/orchestrator_api/commands.py` — `_JSONErrorGroup` class (lines 46-98)
- `docs/reference/orchestrator-api.md` — stale `--json` on line 87
- `src/specify_cli/__init__.py` — root CLI registration (line 79-84, `BannerGroup`)
- `src/specify_cli/cli/commands/__init__.py` — sub-app registration (line 59)

**Constraints**:
- C-001: No backward compatibility — no `--json` shim.
- C-003: Prefer deleting code over adding it.
- No changes to `__init__.py` or the registration in `commands/__init__.py`. The fix lives entirely in `orchestrator_api/commands.py` and `docs/`.

**Click dispatch flow (nested path)**:
```
BannerGroup.main() → BannerGroup.invoke() → _JSONErrorGroup.invoke() → subcommand.invoke()
```
Errors from subcommand parsing propagate back through this chain. We intercept at `_JSONErrorGroup.invoke()`.

## Subtasks & Detailed Guidance

### Subtask T001 – Extract `_emit_error()` helper method

- **Purpose**: Eliminate duplication between `invoke()` and `main()` error handling. Both paths need to emit a `USAGE_ERROR` JSON envelope — extract this into a single method.

- **Steps**:
  1. Add a new method `_emit_error(self, message: str) -> None` to `_JSONErrorGroup`.
  2. The method should call `_emit(make_envelope(...))` with `command="unknown"`, `success=False`, `data={"message": message}`, `error_code="USAGE_ERROR"`.
  3. Refactor the existing `main()` exception handlers to use `self._emit_error()` instead of inline envelope construction.

- **Files**: `src/specify_cli/orchestrator_api/commands.py`

- **Parallel?**: No — T002 depends on this.

- **Notes**: The helper is intentionally on the class (not module-level) because it's specific to the error-handling contract of this group.

### Subtask T002 – Add `invoke()` override to `_JSONErrorGroup`

- **Purpose**: This is the core fix. When the orchestrator-api is nested as a sub-group, Click calls `invoke()` not `main()`. Override `invoke()` to catch `click.UsageError` and `click.Abort` at the dispatch level.

- **Steps**:
  1. Add `invoke(self, ctx)` method to `_JSONErrorGroup`, before the existing `main()`.
  2. Wrap `super().invoke(ctx)` in a try/except.
  3. Catch `click.UsageError`: call `self._emit_error(exc.format_message())`, then `ctx.exit(2)`.
  4. Catch `click.Abort`: call `self._emit_error("Command aborted")`, then `ctx.exit(2)`.
  5. Return the result of `super().invoke(ctx)` on success.

- **Implementation**:
  ```python
  def invoke(self, ctx):
      """Catch errors during subcommand dispatch (nested invocation path).

      When this group is registered as a sub-group of the root CLI via
      add_typer(), Click dispatches to invoke(), not main(). This override
      ensures parse/usage errors produce JSON envelopes even when the root
      CLI's BannerGroup would otherwise emit prose.
      """
      try:
          return super().invoke(ctx)
      except click.UsageError as exc:
          self._emit_error(exc.format_message())
          ctx.exit(2)
      except click.Abort:
          self._emit_error("Command aborted")
          ctx.exit(2)
  ```

- **Files**: `src/specify_cli/orchestrator_api/commands.py`

- **Parallel?**: No — depends on T001.

- **Notes**:
  - `ctx.exit(2)` internally raises `SystemExit(2)`, same as the `main()` path.
  - When both `invoke()` and `main()` are in play (direct invocation), errors from subcommand parsing are caught by `invoke()` first. The resulting `SystemExit(2)` propagates to `main()`, which passes it through via `except SystemExit: raise`. No double emission.
  - Group-level arg parsing errors (e.g., `orchestrator-api --unknown-group-flag`) happen in `main()` before `invoke()` is called, so the `main()` override still handles those.

### Subtask T003 – Update `_JSONErrorGroup` class docstring

- **Purpose**: Document the two-level error handling design so future maintainers understand why both `invoke()` and `main()` are overridden.

- **Steps**:
  1. Replace the existing class docstring with one that explains:
     - The JSON-first contract guarantee
     - Why `invoke()` is needed (nested dispatch path via `add_typer()`)
     - Why `main()` is needed (direct invocation + group-level arg errors)
     - The interaction between the two (no double emission)

- **Files**: `src/specify_cli/orchestrator_api/commands.py`

- **Parallel?**: Can be done with T001/T002 in the same edit.

### Subtask T004 – Remove `--json` from docs

- **Purpose**: The docs at `docs/reference/orchestrator-api.md` line 87 show `--json` in the `contract-version` signature. This flag does not exist. The API is always-JSON by design.

- **Steps**:
  1. Open `docs/reference/orchestrator-api.md`.
  2. Line 87: Change `spec-kitty orchestrator-api contract-version --json [--provider-version <semver>]` to `spec-kitty orchestrator-api contract-version [--provider-version <semver>]`.
  3. Verify no other `--json` references exist in the file (there shouldn't be).

- **Files**: `docs/reference/orchestrator-api.md`

- **Parallel?**: Yes — independent of T001-T003.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `ctx.exit(2)` behaves differently from `raise SystemExit(2)` | Click's `ctx.exit()` calls `raise SystemExit()` internally. Verified in Click source. |
| Double JSON emission from invoke() + main() | invoke() catches error → ctx.exit(2) → SystemExit → main() has `except SystemExit: raise` → passes through. |
| Breaking existing tests | No API surface changed. Sub-app tests still invoke directly → main() → invoke(). The invoke() override doesn't interfere with normal command execution. |

## Review Guidance

- **Critical check**: Run `spec-kitty orchestrator-api contract-version --bogus` through the root CLI. Must produce JSON on stdout with `error_code: "USAGE_ERROR"`, not prose stderr.
- **Regression check**: Run `pytest tests/agent/test_json_envelope_contract_integration.py tests/agent/test_orchestrator_commands_integration.py -v` — all existing tests must pass.
- **Code delta**: Net change should be small. The `_emit_error()` helper replaces inline duplication; `invoke()` is ~10 lines.
- **Docs check**: `docs/reference/orchestrator-api.md` line 87 has no `--json`.

## Implementation Command

```bash
spec-kitty implement WP01
```

## Activity Log

- 2026-03-20T12:31:02Z – system – lane=planned – Prompt created.
- 2026-03-20T12:35:22Z – coordinator – shell_pid=39519 – lane=doing – Assigned agent via workflow command
- 2026-03-20T12:38:08Z – coordinator – shell_pid=39519 – lane=for_review – invoke() override + _emit_error() helper + docs fix complete. All 52 existing tests pass.
- 2026-03-20T12:38:28Z – codex – shell_pid=49444 – lane=doing – Started review via workflow command
- 2026-03-20T12:44:36Z – codex – shell_pid=49444 – lane=approved – Arbiter decision: Approved. Implementation correct — invoke() override, _emit_error() helper, docstring, docs fix all verified. All 52 existing tests pass. Codex reviewed wrong feature context.
- 2026-03-20T12:45:03Z – codex – shell_pid=49444 – lane=planned – Moved to planned
- 2026-03-20T12:52:42Z – codex – shell_pid=49444 – lane=approved – Re-approving: arbiter decision stands. Implementation verified correct.
- 2026-03-20T12:56:16Z – codex – shell_pid=49444 – lane=done – Merged to 2.x | Done override: Merged to 2.x via WP02 (WP01 is ancestor of WP02)
