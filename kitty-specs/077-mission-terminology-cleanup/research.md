# Phase 0 Research: Mission Terminology Cleanup

**Mission**: `077-mission-terminology-cleanup`
**Date**: 2026-04-08
**Validated against `spec-kitty` HEAD**: `35d43a25294639fece46a7c89098062f1313a064`

This document resolves all open questions identified during plan generation. Each item follows the template:

> **Decision** — what was chosen
> **Rationale** — why
> **Alternatives considered** — what else was on the table

---

## Q0.1 — Does an existing selector-resolution helper already do what this mission needs?

**Decision**: There is one existing helper, `require_explicit_feature(feature: str | None, *, command_hint: str = "") -> str` at `/private/tmp/241/spec-kitty/src/specify_cli/core/paths.py:273`. It does **not** cover this mission's requirements. A new helper module `src/specify_cli/cli/selector_resolution.py` is required.

**Rationale**:
- `require_explicit_feature` only validates "is the slug present and non-empty?". It receives a single `feature: str | None` parameter, which means by the time it runs, typer has already collapsed any multi-alias `Option` declaration into a single value with last-value-wins resolution. This is exactly the architectural cause of the verified bug in `mission current` (spec §8.2).
- The fix has to happen *before* the parameters are collapsed. The cleanest way to do this in typer is to declare the canonical flag and the alias flag as **two separate parameters**, then resolve them in the body of the command (or in a small helper called from the body). That helper is what this mission introduces.
- The new helper is intentionally small and focused: it takes the two parsed values, applies the §11.1 policy, raises `typer.BadParameter` on conflict, emits the deprecation warning when needed, and returns the resolved canonical value. It then hands that value to `require_explicit_feature` for the existing "is it actually present?" check. The existing helper is not modified and not deprecated.
- Verified: `require_explicit_feature` is currently called from 14 source files under `src/specify_cli/` (plus 4 test files and several `kitty-specs/**` historical artifacts that the new helper must not scan). All current call sites pass `command_hint="--mission <slug>"`, which means the canonical hint is already correct in the existing helper — only the upstream typer declarations need to change.

**Alternatives considered**:
- **Modify `require_explicit_feature` to accept multiple values and reconcile them.** Rejected: this would force every existing call site to be modified to pass two values, even commands that have only ever accepted `--mission`. It would also overload the helper's responsibility (currently "is it present?" — would become "is it present and non-conflicting and non-deprecated?"), violating single-responsibility.
- **Use a typer `Context.params` post-callback to detect conflict.** Rejected: typer doesn't expose a clean post-callback hook for this case. The natural unit of post-parse logic is the function body itself.
- **Use a `typer.Typer` middleware / global callback.** Rejected: typer's global callbacks run *before* per-command parsing in the model used here; they cannot see the per-command parameter values without sniffing argv directly. Argv sniffing is brittle and gets the conflict-detection logic wrong when the same flag appears multiple times.
- **Keep multi-alias `Option` declarations but add a `callback=` that validates uniqueness.** Rejected: typer callbacks fire per-parameter and only see one value at a time; they cannot see the *other* alias's value to compare. This is the same architectural limitation as Q0.3.

---

## Q0.2 — How does the existing codebase emit non-fatal CLI warnings to stderr?

**Decision**: Use `rich.console.Console(stderr=True)` and `console.print("[yellow]Warning:[/yellow] <message>")`. Match the existing precedent at `src/specify_cli/cli/commands/agent/mission.py:604` exactly.

**Rationale**:
- Three existing files already use `Console(stderr=True)`:
  - `src/specify_cli/cli/commands/agent/tests.py:31` (`err_console = Console(stderr=True)`)
  - `src/specify_cli/sync/project_identity.py:331`
  - `src/specify_cli/sync/emitter.py:29` (`_console = Console(stderr=True)`)
- The exact deprecation precedent already in production at `src/specify_cli/cli/commands/agent/mission.py:604`:
  ```python
  console.print("[yellow]Warning:[/yellow] --require-tasks is deprecated; use --include-tasks.")
  ```
  This is the precise visual style and prose pattern users already pattern-match in spec-kitty CLI output. Matching it makes the new deprecation warning look native to the codebase.
- Rich-styled stderr output is testable via `pytest`'s `capsys` fixture, which the existing CLI test suite already uses heavily. No new test plumbing is needed.
- typer also offers a `deprecated=True` flag on `Option(...)` and on `@app.command(...)`. It is used at `src/specify_cli/cli/commands/mission.py:273` and `src/specify_cli/cli/commands/mission_type.py:273` for whole-command deprecation. typer renders `deprecated=True` parameters in help with a "(deprecated)" annotation but does **not** emit a runtime warning. For this mission we need a runtime warning *and* the parameter must be hidden from help, so `deprecated=True` alone is insufficient. The new helper produces the runtime warning; `hidden=True` keeps the alias out of help text.

**Alternatives considered**:
- **`warnings.warn(..., DeprecationWarning)`**. Rejected: Python's `warnings` module has surprising default filters (DeprecationWarning is hidden by default outside of test runs unless `-W default::DeprecationWarning` is set), tests would need `pytest.warns` plumbing the existing CLI suite doesn't use, and the visual output doesn't match the rest of the codebase's warning style.
- **typer's `deprecated=True` only**. Rejected: it sets a help annotation but does not emit a runtime warning. We need both runtime visibility (so legacy scripts learn) and help-text hiding (so new users never see it).
- **stdlib `print(..., file=sys.stderr)` without Rich**. Rejected: violates the "use Rich" charter convention and produces unstyled output that breaks the visual pattern users expect.

---

## Q0.3 — How does typer behave when a single `Option` parameter declares multiple flag aliases, and is there a way to detect dual-flag conflict at the typer layer?

**Decision**: typer collapses multi-alias `Option` declarations to a single parameter with last-value-wins semantics. There is no built-in way to detect dual-flag conflict at the typer layer. The mission must declare canonical and alias flags as **two separate parameters** and detect conflict in the helper.

**Rationale**:
- Verified by reading the existing buggy code at `src/specify_cli/cli/commands/mission.py:172-194`:
  ```python
  @app.command("current")
  def current_cmd(
      feature: str | None = typer.Option(
          None,
          "--mission",
          "--feature",
          "-f",
          help="Mission slug",
      ),
  ) -> None:
  ```
  When the user runs `mission current --mission A --feature B`, both flags resolve to the same `feature` parameter. typer applies them in argv order, so the second one wins. There is no exception, no warning, and no way for the function body to know that two different values were passed.
- typer `Option(..., callback=...)` parameter callbacks fire per-parameter with only that parameter's value, not the values of other parameters in the same command. They cannot detect cross-parameter conflict.
- typer global callbacks (`@app.callback()`) fire *before* per-command parameter parsing in the typical model and cannot see the parsed parameter values for a subcommand.
- The clean solution: declare the two flags as two separate parameters (`mission: str | None = Option(None, "--mission", ...)` and `feature: str | None = Option(None, "--feature", ..., hidden=True)`), then in the function body call `resolve_mission_selector(mission=mission, feature=feature)` from the new helper. The helper sees both values and can raise `typer.BadParameter` when `mission != feature` and both are set.

**Alternatives considered**:
- **Keep the multi-alias declaration and sniff argv with `sys.argv` or `click.get_current_context().protected_args`**. Rejected: brittle, breaks under test runners that don't use real argv, and doesn't compose with typer's `CliRunner` in unit tests.
- **Use typer's `param_type` system to plug in a custom converter**. Rejected: same per-parameter limitation as callbacks.
- **Wrap typer with a custom decorator that splits a single conceptual flag into two parameters automatically**. Rejected: would introduce hidden magic and make the parameter declarations harder to read at the call site. The two-parameter approach is more explicit and grep-friendly, which matches how the rest of the codebase declares typer commands.

---

## Q0.4 — What is the authoritative scope of `src/specify_cli/core/upstream_contract.json`?

**Decision**: `upstream_contract.json` is the authoritative machine-readable contract for the **orchestrator-api surface specifically** (and adjacent machine-facing surfaces: envelope, payload, body_sync, tracker_bind). It already lists `--feature` as a forbidden CLI flag in the `orchestrator_api` section. This mission **does not modify** the orchestrator-api section of that file. Scope B may extend other sections of this file as part of the machine-facing alignment, but the orchestrator-api section is untouched.

**Rationale**:
- File contents (verified at HEAD `35d43a25`):
  ```json
  {
    "_source_events_commit": "5b8e6dc",
    "_schema_version": "3.0.0",
    "envelope": {
      "required_fields": ["schema_version", "build_id", "aggregate_type", "event_type"],
      "forbidden_fields": ["feature_slug", "feature_number"],
      "aggregate_type": {
        "allowed": ["Mission", "WorkPackage", "MissionDossier"],
        "forbidden": ["Feature"]
      }
    },
    "payload": {
      "mission_scoped": {
        "required_fields": ["mission_slug", "mission_number", "mission_type"],
        "forbidden_fields": ["feature_slug", "feature_number", "feature_type"]
      }
    },
    "body_sync": { ... "forbidden_fields": ["feature_slug", "mission_key"] },
    "orchestrator_api": {
      "allowed_commands": ["contract-version", "mission-state", "list-ready", "start-implementation", "start-review", "transition", "append-history", "accept-mission", "merge-mission"],
      "forbidden_commands": ["feature-state", "accept-feature", "merge-feature"],
      "allowed_error_codes": [...],
      "forbidden_payload_fields": ["feature_slug"],
      "required_payload_fields": ["mission_slug"],
      "allowed_cli_flags": ["--mission"],
      "forbidden_cli_flags": ["--feature"]
    }
  }
  ```
- The contract is sourced from `spec-kitty-events` commit `5b8e6dc` (same as the spec's validated baseline) and `spec-kitty-saas` commit `3a0e4af`. It is the operationalization of the upstream contract, not a hand-maintained list.
- The `orchestrator_api` section already aligns with this mission's intent: `--mission` is the only allowed CLI flag and `--feature` is forbidden. The orchestrator-api code at `src/specify_cli/orchestrator_api/commands.py:437` and the contract test at `tests/contract/test_orchestrator_api.py:164` both honor this. **Therefore the orchestrator-api section requires zero changes from this mission.**
- The `envelope`, `payload.mission_scoped`, and `body_sync` sections list `feature_slug` / `feature_number` / `feature_type` as forbidden fields. These constrain Scope B but are already enforced by other tests and machinery. Scope B work packages will verify that no first-party machine-facing payload re-introduces these forbidden fields.
- C-010 from the spec forbids widening the orchestrator-api envelope. The plan does not touch `src/specify_cli/orchestrator_api/envelope.py`.

**Alternatives considered**:
- **Add a `main_cli` section to `upstream_contract.json` to enforce the canonical state for human-facing commands too.** Rejected for *this* mission scope but flagged as a possible future improvement. The main CLI's "hidden secondary alias" model is incompatible with a strict `forbidden_cli_flags` list; the right enforcement mechanism for the main CLI is the new `tests/contract/test_terminology_guards.py` grep guard that allows `hidden=True` declarations and forbids visible ones. If a future iteration wants to formalize "no `--feature` in non-hidden form" as a contract entry, that's a follow-on, not a Scope A blocker.
- **Modify the `orchestrator_api.forbidden_cli_flags` list to also forbid `--mission-run`**. Considered, deferred to Scope B planning. The orchestrator-api doesn't currently accept `--mission-run` for tracked-mission selection at all, so adding it to the forbidden list would be belt-and-suspenders; the question is whether the cost of an extra contract entry is justified by the regression-prevention value. Defer to Scope B.

---

## Q0.5 — Is there already a `tests/contract/test_terminology_guards.py` or similar grep-guard file we should extend?

**Decision**: No such file exists. Create a new one at `/private/tmp/241/spec-kitty/tests/contract/test_terminology_guards.py`.

**Rationale**:
- Verified by file search: no existing test file under `tests/contract/` or elsewhere implements the kind of grep guard this mission needs (scoped to `src/doctrine/skills/**` and `docs/**`, explicitly excluding `kitty-specs/**` and `architecture/**`).
- The closest existing pattern is `tests/contract/test_orchestrator_api.py`, which is a behavior test (it invokes the CLI and asserts on output) rather than a content-grep test. They are different shapes and shouldn't share a file.
- A dedicated file is clearer to find, easier to maintain, and easier to point reviewers at when a future PR breaks a guard. The file's docstring will reference FR-022 and C-011 directly so a future maintainer cannot accidentally widen the scope to scan historical artifacts.
- The new file lives in `tests/contract/` (not `tests/integration/` or `tests/unit/`) because the grep guards are fundamentally a *contract* between the implementation and the canonical terminology model. They fail loudly when the contract is broken.

**Alternatives considered**:
- **Extend `tests/contract/test_orchestrator_api.py` with the grep guards.** Rejected: mixes two unrelated test shapes (CLI-invocation tests and content-grep tests) in one file, making both harder to maintain.
- **Put the grep guards in a non-test file (e.g., a pre-commit hook).** Rejected: pre-commit hooks aren't enforced in CI by default in this repo (verified by skimming `.pre-commit-config.yaml` if present and the existing CI workflow). Tests under `tests/contract/` are guaranteed to run in CI.
- **Use ruff or another linter rule.** Rejected: ruff doesn't natively support arbitrary content greps over markdown files. Writing a custom ruff rule is overkill for three pattern checks.

---

## Q0.6 — What is the precise list of inverse-drift sites where `--mission` currently means "blueprint/template selector"?

**Decision**: Three verified sites at HEAD `35d43a25`. WPA1 (the audit work package) is responsible for confirming the list is complete; WPA2b owns the fix. The WPA1 audit must use a content grep over `src/specify_cli/cli/commands/**` for the pattern `typer\.Option\(.*"--mission"` and inspect each match's `help=` string and surrounding context to classify the site as "tracked-mission" or "inverse-drift".

**Rationale**: The three known sites at HEAD `35d43a25`:

1. **`src/specify_cli/cli/commands/agent/mission.py:488`** — `agent mission create` declares:
   ```python
   mission: Annotated[str | None, typer.Option(
       "--mission",
       help="Mission type (e.g., 'documentation', 'software-dev')"
   )] = None,
   ```
   The help string and the parameter's actual semantic role (it's the mission *type*, not a tracked mission slug) confirm this is inverse drift. The literal flag should be `--mission-type`, with `--mission` retained as a hidden deprecated alias.

2. **`src/specify_cli/cli/commands/charter.py:67`** — `charter interview` declares:
   ```python
   mission: str = typer.Option("software-dev", "--mission", help="Mission key for charter defaults"),
   ```
   The default value `"software-dev"` (a mission type, not a tracked mission slug) and the help string ("Mission key for charter defaults") confirm this is inverse drift.

3. **`src/specify_cli/cli/commands/lifecycle.py:27`** — `lifecycle.specify` declares:
   ```python
   mission: Optional[str] = typer.Option(None, "--mission", help="Mission type (e.g., software-dev, research)"),
   ```
   The help string explicitly names this as a mission type.

The WPA1 audit must scan for additional sites and report them in its output. The contract test in `tests/contract/test_terminology_guards.py` will include a static check that fails if a `--mission` declaration's `help=` string contains the substring "mission type" or "mission key" without an accompanying `--mission-type` parameter, to prevent regression.

**Alternatives considered**:
- **Manual file enumeration in this research doc.** Rejected: WPA1 is the right place for the comprehensive audit. The research doc captures the verified-known sites and the audit method; it doesn't pre-execute WPA1.
- **Treat inverse drift as a separate mission.** Rejected: spec already commits to fixing both directions in Scope A (FR-021, WPA2b). Splitting it would create coordination overhead with no benefit.
- **Skip the inverse drift entirely and let `--mission` ambiguously mean both things.** Rejected: this is exactly the canonical-violation that the ADR was written to eliminate.

---

## Summary of Phase 0 Resolution

| Question | Resolution | Implication for Phase 1 |
|---|---|---|
| Q0.1 | New helper at `src/specify_cli/cli/selector_resolution.py` | Defines the data model and contracts |
| Q0.2 | Rich `Console(stderr=True)` matching `agent/mission.py:604` precedent | Defines the deprecation warning contract |
| Q0.3 | Two separate typer parameters; helper detects conflict in body | Drives the data model shape: helper takes two named values, returns one |
| Q0.4 | `upstream_contract.json` orchestrator-api section is unchanged; envelope/payload/body_sync constrain Scope B | Confirms C-010; defines Scope B's contract anchor |
| Q0.5 | New file at `tests/contract/test_terminology_guards.py` | Defines the grep-guard contract |
| Q0.6 | Three known inverse-drift sites; WPA1 confirms full list | Defines the contract test's coverage scope |

No `[NEEDS CLARIFICATION]` markers remain. All Phase 0 questions are answered. Proceed to Phase 1 design.
