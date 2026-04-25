---
work_package_id: WP05
title: spec-kitty mission run CLI Subcommand
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- C-007
- FR-001
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase 3 - Operator surface
assignee: ''
agent: claude
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/mission_loader/command.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission_loader/command.py
- src/specify_cli/cli/commands/mission_type.py
- tests/unit/mission_loader/test_command.py
role: implementer
tags: []
---

# Work Package Prompt: WP05 – `spec-kitty mission run` CLI Subcommand

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Add `spec-kitty mission run <mission-key> --mission <mission-slug> [--json]` to the existing `mission` Typer group. The handler validates the custom mission, registers synthesized contracts in the per-process registry shadow, starts (or attaches to) the runtime, and renders a stable success / error envelope.

Success criteria:
1. `spec-kitty mission run --help` shows the documented arguments + options.
2. Happy path: success envelope rendered; `kitty-specs/<slug>/` exists; runtime registered for the run.
3. Validation failure: error envelope rendered; exit code 2; no runtime started.
4. Infrastructure failure (e.g., repo root missing): exit code 1.
5. `--json` output is byte-stable per [contracts/mission-run-cli.md](../contracts/mission-run-cli.md).
6. ≥ 90% line coverage on `command.py`; `mypy --strict` clean.

## Context & Constraints

- WP05's CLI handler is a thin wrapper. Functional core is in `command.py` for testability.
- Validation errors do NOT create `kitty-specs/<slug>/`. Only successful validation triggers `runtime_bridge.get_or_start_run(...)` (which creates the tracked mission).
- The registry-shadow `with` block must enclose the `get_or_start_run` call AND any subsequent `decide_next_via_runtime` calls. For v1, the run-start happens once and the registry is held for the run's lifetime via the singleton's persistent state — the `with` block enters at run-start and only exits on process termination. (Future tranches may revisit this lifetime.)
- See [contracts/mission-run-cli.md](../contracts/mission-run-cli.md) and [data-model.md](../data-model.md) §State transitions.
- Charter: integration tests for CLI commands (these are in WP06; WP05 ships unit tests).

## Subtasks & Detailed Guidance

### Subtask T023 — Create `mission_loader/command.py` (functional core)

- **Purpose**: Pure orchestration that's trivial to unit-test without Typer.
- **Steps**:
  1. Create `src/specify_cli/mission_loader/command.py`.
  2. Implement:
     ```python
     @dataclass(frozen=True)
     class RunCustomMissionResult:
         exit_code: int
         envelope: dict[str, Any]


     def run_custom_mission(
         mission_key: str,
         mission_slug: str,
         repo_root: Path,
         *,
         discovery_context: DiscoveryContext | None = None,
     ) -> RunCustomMissionResult:
         """Validate, register synthesized contracts, and start (or attach to)
         the runtime for the requested custom mission. Returns a result with
         exit code and the envelope dict (for JSON or panel rendering)."""
     ```
  3. Implementation outline:
     ```python
     ctx = discovery_context or _build_discovery_context(repo_root)
     report = validate_custom_mission(mission_key, ctx)

     if not report.ok:
         err = report.errors[0]
         return RunCustomMissionResult(
             exit_code=2,
             envelope={
                 "result": "error",
                 "error_code": str(err.code),
                 "message": err.message,
                 "details": err.details,
                 "warnings": [_warning_dict(w) for w in report.warnings],
             },
         )

     # Register synthesized contracts. The registry is process-singleton; we
     # enter the with-block but never exit it (the run lives for the process
     # lifetime in v1). For tests, callers can clear the registry manually.
     registry = get_runtime_contract_registry()
     registry.register(synthesize_contracts(report.template))

     try:
         run_ref = runtime_bridge.get_or_start_run(
             mission_slug=mission_slug,
             repo_root=repo_root,
             mission_type=mission_key,
         )
     except Exception as exc:
         registry.clear()
         return RunCustomMissionResult(
             exit_code=1,
             envelope={
                 "result": "error",
                 "error_code": "RUN_START_FAILED",
                 "message": str(exc),
                 "details": {"mission_key": mission_key, "mission_slug": mission_slug},
                 "warnings": [_warning_dict(w) for w in report.warnings],
             },
         )

     return RunCustomMissionResult(
         exit_code=0,
         envelope={
             "result": "success",
             "mission_key": mission_key,
             "mission_slug": mission_slug,
             "mission_id": _read_mission_id(repo_root, mission_slug),
             "feature_dir": str(_feature_dir_for(repo_root, mission_slug)),
             "run_dir": str(run_ref.run_dir),
             "warnings": [_warning_dict(w) for w in report.warnings],
         },
     )
     ```
  4. Helper `_build_discovery_context(repo_root)`: construct a `DiscoveryContext` matching what `runtime_bridge._build_discovery_context` produces (or import that function if it's exported).
- **Files**: `src/specify_cli/mission_loader/command.py`.
- **Notes**: `RUN_START_FAILED` is reserved for infrastructure-level errors and is NOT in the validator's closed enum (it's not produced by `validate_custom_mission`). Document it in [contracts/validation-errors.md](../contracts/validation-errors.md) as a CLI-layer infrastructure code if reviewer requests.

### Subtask T024 — Register `@app.command("run")` in `mission_type.py`

- **Purpose**: The Typer surface is a 30-line wrapper.
- **Steps**:
  1. Open `src/specify_cli/cli/commands/mission_type.py`.
  2. Add (after the existing `@app.command("create")`):
     ```python
     @app.command("run")
     def run_cmd(
         mission_key: Annotated[str, typer.Argument(help="The reusable custom mission key.")],
         mission_slug: Annotated[str, typer.Option("--mission", help="Tracked mission slug.")],
         json_output: Annotated[bool, typer.Option("--json/--no-json", help="Emit JSON envelope to stdout.")] = False,
     ) -> None:
         """Start (or attach to) a runtime for a project-authored custom mission definition."""
         from specify_cli.mission_loader.command import run_custom_mission
         project_root = get_project_root_or_exit()
         result = run_custom_mission(mission_key, mission_slug, project_root)
         _render_envelope(result.envelope, json_output)
         raise typer.Exit(code=result.exit_code)
     ```
  3. Implement `_render_envelope(envelope, json_output)` in the same file (private helper) that either prints `json.dumps(envelope, indent=2)` or builds a `rich.panel.Panel`.
- **Files**: `src/specify_cli/cli/commands/mission_type.py`.
- **Notes**: Use `Annotated[..., typer.Argument(...)]` style — that's what other commands in this file use.

### Subtask T025 — Wire validation → registry → run-start

- **Purpose**: Implement the orchestration body inside `run_custom_mission` per T023's outline.
- **Steps**:
  1. Verify `validate_custom_mission(...)`, `synthesize_contracts(...)`, `get_runtime_contract_registry()`, and `runtime_bridge.get_or_start_run(...)` exist (WP02, WP03, WP04 deliverables).
  2. Confirm import order: `from specify_cli.mission_loader import ...` for the loader pieces; `from specify_cli.next import runtime_bridge` (or specific function).
  3. On any exception inside `get_or_start_run`, clear the registry to avoid stale shadows in process-bound test runs.
- **Files**: `src/specify_cli/mission_loader/command.py`.

### Subtask T026 — JSON envelope rendering

- **Purpose**: Lock the shape per [contracts/mission-run-cli.md](../contracts/mission-run-cli.md).
- **Steps**:
  1. Implement `_render_envelope(envelope: dict, json_output: bool)`:
     ```python
     def _render_envelope(envelope: dict[str, Any], json_output: bool) -> None:
         if json_output:
             # Stable key order: result, error_code|mission_key, ...
             print(json.dumps(envelope, indent=2, sort_keys=False))
             return
         # human path implemented in T027
     ```
  2. Ensure `print` writes to stdout (Typer/Rich do that by default). For tests, `capsys` will capture it.
- **Files**: `src/specify_cli/cli/commands/mission_type.py`.

### Subtask T027 — Human (`rich.panel.Panel`) rendering

- **Purpose**: Operator-friendly console output that mirrors the JSON envelope.
- **Steps**:
  1. Build the panel:
     ```python
     def _render_human(envelope: dict[str, Any]) -> None:
         from rich.panel import Panel
         from rich.text import Text

         if envelope["result"] == "success":
             title = "Mission Run Started"
             body = Text()
             body.append(f"mission_key: {envelope['mission_key']}\n")
             body.append(f"mission_slug: {envelope['mission_slug']}\n")
             body.append(f"feature_dir: {envelope['feature_dir']}\n")
             body.append(f"run_dir: {envelope['run_dir']}\n")
         else:
             title = envelope["error_code"]
             body = Text(envelope["message"])
             for k, v in envelope["details"].items():
                 body.append(f"\n  {k}: {v}")
         for warn in envelope.get("warnings", []):
             body.append(f"\n[warn] {warn['code']}: {warn['message']}")
         console.print(Panel(body, title=title, border_style="red" if envelope["result"] == "error" else "green"))
     ```
  2. Wire `_render_envelope` to call `_render_human(envelope)` when `json_output is False`.
- **Files**: `src/specify_cli/cli/commands/mission_type.py`.

### Subtask T028 — Unit tests for `run_custom_mission`

- **Purpose**: Exit-code matrix + envelope shape lock.
- **Steps**:
  1. Create `tests/unit/mission_loader/test_command.py`.
  2. Cases (use `tmp_path` and minimal mission YAML fixtures inline):
     - `test_happy_path_returns_zero_and_success_envelope` — valid mission, asserts `exit_code == 0` and `envelope["result"] == "success"` with all expected keys.
     - `test_validation_error_returns_two_and_error_envelope` — invalid mission (missing retrospective), asserts `exit_code == 2`, `envelope["error_code"] == "MISSION_RETROSPECTIVE_MISSING"`.
     - `test_unknown_mission_key_returns_two` — `mission_key` not in any tier; `exit_code == 2`, code `MISSION_KEY_UNKNOWN`.
     - `test_run_start_exception_returns_one` — monkeypatch `runtime_bridge.get_or_start_run` to raise; `exit_code == 1`, code `RUN_START_FAILED`.
     - `test_warnings_pass_through_on_success_and_error` — shadowed mission produces success envelope with `warnings: [{"code": "MISSION_KEY_SHADOWED", ...}]`.
  3. Use `get_runtime_contract_registry().clear()` in `autouse=True` fixture teardown.
- **Files**: `tests/unit/mission_loader/test_command.py`.
- **Parallel?**: [P] with T026/T027.

## Test Strategy (charter required)

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/unit/mission_loader/test_command.py tests/architectural/test_shared_package_boundary.py -q
UV_PYTHON=3.13.9 uv run --no-sync ruff check src/specify_cli/mission_loader/command.py src/specify_cli/cli/commands/mission_type.py tests/unit/mission_loader/test_command.py
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/mission_loader/command.py src/specify_cli/cli/commands/mission_type.py
UV_PYTHON=3.13.9 uv run --no-sync spec-kitty mission run --help
UV_PYTHON=3.13.9 uv run --no-sync pytest --cov=src/specify_cli/mission_loader/command --cov-fail-under=90 tests/unit/mission_loader/test_command.py -q
```

End-to-end integration tests live in WP06.

## Risks & Mitigations

- **Risk**: Registry-shadow lifetime is broader than the run-start call, leaking state across CLI invocations in interactive shells.
  - **Mitigation**: V1 acceptance for now. Document the limitation in `command.py`'s module docstring. Future tranche addresses lifetime explicitly.
- **Risk**: `get_or_start_run` performs filesystem I/O that races with concurrent runs.
  - **Mitigation**: Out of scope for this WP; `runtime_bridge` already handles its own locking.
- **Risk**: `_build_discovery_context` is private to `runtime_bridge`.
  - **Mitigation**: If it's not exported, copy the construction logic in `command.py` (it's simple) — but mark with a comment to be cleaned up in a follow-on if desired.

## Review Guidance

- Reviewer confirms `mission_type.py`'s diff is additive only (no existing commands modified).
- Reviewer confirms `command.py` returns a `RunCustomMissionResult` and never calls `sys.exit` directly (testability).
- Reviewer confirms `--json` output round-trips through `json.loads(json.dumps(...))`.

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
