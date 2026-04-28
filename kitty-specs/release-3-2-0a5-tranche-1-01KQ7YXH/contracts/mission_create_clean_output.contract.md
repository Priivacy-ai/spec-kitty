# Contract: `spec-kitty agent mission create --json` clean output

**Traces to**: FR-008 (#735), FR-009 (#717), NFR-004, NFR-005

## Stimulus

A user (or agent) runs:

```bash
spec-kitty agent mission create "<slug>" \
  --friendly-name "<title>" \
  --purpose-tldr "<tldr>" \
  --purpose-context "<context>" \
  --json
```

in a spec-kitty-initialized project. The command succeeds (exit code `0`).

## Required behavior

After exit:

1. **Stdout**:
   - Contains exactly one valid JSON document (the mission-create payload).
   - The document's last character (modulo a trailing newline) is the
     closing `}` of the JSON object.
2. **Stderr**:
   - MAY contain at most ONE occurrence of any given diagnostic message
     family ("Not authenticated, skipping sync", "token refresh failed",
     equivalent variants).
   - MUST NOT contain red-styled error output (Rich `[red]…[/red]`,
     `[bold red]…[/bold red]`, or terminal escape sequences for red) AFTER
     the JSON payload has been written to stdout when the command's exit
     status is `0`.
3. **Exit code**: `0`.

## Forbidden behavior

- Multiple repetitions of "Not authenticated, skipping sync" within one
  invocation (FR-009 / #717).
- Red shutdown / "final sync" error lines after the JSON payload on
  success (FR-008 / #735).
- Any diagnostic that says "error" while exit code is `0`.

## Implementation hint (informative, not normative)

Two cooperating pieces:

1. **In-process dedup**: a new module
   `src/specify_cli/diagnostics/dedup.py` provides `report_once(cause_key)`
   backed by a `contextvars.ContextVar`. The two callsites in
   `src/specify_cli/sync/background.py:270` and `:325` consult it before
   logging.
2. **Atexit success-flag**: the `agent mission create` JSON-payload writer
   sets a process-state flag (`mark_invocation_succeeded()`) right after
   the final `print(json.dumps(...))`. The atexit handlers in
   `src/specify_cli/sync/background.py:456` and
   `src/specify_cli/sync/runtime.py:381` consult that flag and downgrade
   any warning to debug-level (or skip entirely) when it's `True`.

See [research.md R7](../research.md#r7--diagnostic-noise-post-success-errors-and-dedup-fr-008--fr-009--735--717).

## Verifying tests

- Unit: `tests/sync/test_diagnostic_dedup.py` — drive
  `BackgroundSyncService` directly with a mock unauthenticated session,
  invoke the noisy code path twice, assert the warning fires exactly once.
- E2E: `tests/e2e/test_mission_create_clean_output.py` — use Click's
  `CliRunner` (or subprocess) to invoke `mission create` against a tmp
  project; capture stdout/stderr; assert (a) JSON payload appears, (b)
  stderr contains zero "Not authenticated, skipping sync" repeats, (c)
  zero red-styled lines after the JSON.

## Out-of-scope

- This contract does NOT mandate suppressing diagnostics on failure paths.
  When the command exits non-zero, all warnings remain at their normal
  log level.
