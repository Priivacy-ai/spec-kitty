---
work_package_id: WP02
title: Strict JSON envelope on --json commands (#842)
dependencies: []
requirement_refs:
- FR-003
- FR-004
planning_base_branch: release/3.2.0a6-tranche-2
merge_target_branch: release/3.2.0a6-tranche-2
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a6-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a6-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
history:
- at: '2026-04-28T09:30:00Z'
  by: spec-kitty.tasks
  note: Created as part of tranche-2 specify→plan→tasks pipeline
authoritative_surface: src/specify_cli/sync/diagnose.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/diagnose.py
- src/specify_cli/sync/__init__.py
- src/specify_cli/auth/transport.py
- tests/integration/test_json_envelope_strict.py
tags: []
---

# WP02 — Strict JSON envelope on `--json` commands (#842)

## Branch Strategy

- **Planning/base branch**: `release/3.2.0a6-tranche-2`
- **Final merge target**: `release/3.2.0a6-tranche-2`
- Lane B (independent). Implementation command: `spec-kitty agent action implement WP02 --agent claude`.

## Objective

Every covered `--json` command produces stdout that `json.loads(stdout)` accepts under all four SaaS states. Sync, auth, and tracker diagnostics route to **stderr** by default; in-envelope diagnostics are permitted only under a documented top-level key.

## Context

GitHub issue #842. Today, lines like `Not authenticated, skipping sync` are printed to stdout by sync/auth/tracker code paths, breaking strict JSON parsing for any external script that pipes a `--json` command into `json.loads`.

**FRs**: FR-003, FR-004 · **NFR**: NFR-001 · **SC**: SC-002 · **Spec sections**: Scenario 2, Domain Language ("Strict JSON", "JSON envelope") · **Contract**: [contracts/json-envelope.md](../contracts/json-envelope.md)

## Always-true rules

- `json.loads(stdout)` succeeds on every covered `--json` command in every SaaS state.
- No bare diagnostic line appears on stdout outside the JSON object.
- Diagnostic content goes to **stderr** by default.

---

## Subtask T007 — Inventory covered `--json` commands and their stdout writers

**Purpose**: Build the test surface and identify every site that currently writes to stdout from a sync/auth/tracker code path.

**Steps**:

1. Grep the codebase for `--json` flag declarations in CLI commands. Likely sites: `cli/commands/mission.py`, `cli/commands/charter.py`, `cli/commands/decision.py`, `cli/commands/context.py`, `cli/commands/_auth_*.py`, `cli/commands/agent/*.py`, etc.
2. Build the **covered set** as a Python list in the integration test (T010): one entry per `(command_argv, expects_json=True)`. At minimum:
   - `mission create`, `mission setup-plan`, `mission branch-context`, `mission check-prerequisites`
   - `agent context resolve`
   - `charter context`
   - `agent decision open|resolve|defer|cancel|verify`
   - any other `--json` command exercised by existing tests
3. Grep `print(`, `console.print`, `typer.echo`, `sys.stdout.write` calls in `src/specify_cli/sync/`, `src/specify_cli/auth/`, and any tracker-client glue. Record the file:line of each call that runs unconditionally during a `--json` command's lifecycle.

**Output**: an internal note (kept in code comments or PR description) listing the `_diagnostic_print_sites` and the `_covered_commands`.

---

## Subtask T008 — Add diagnostic-routing helper

**Purpose**: One canonical entry point for all sync/auth/tracker diagnostics that is JSON-aware.

**Steps**:

1. Add (or extend) `src/specify_cli/sync/diagnose.py`. Public surface:
   ```python
   def emit_diagnostic(
       message: str,
       *,
       category: str,           # "sync" | "auth" | "tracker"
       json_mode: bool,         # True if the calling command is in --json mode
       envelope: dict | None = None,  # if json_mode and envelope is provided, nest under envelope["diagnostics"][category]
   ) -> None: ...
   ```
   Behavior:
   - If `json_mode is False`: write `message` to **stderr** (rich-aware if available, plain otherwise).
   - If `json_mode is True` and `envelope is None`: write to **stderr** (still never stdout).
   - If `json_mode is True` and `envelope is not None`: append to `envelope.setdefault("diagnostics", {}).setdefault(category, []).append(message)`. Do not print.
2. Export from `src/specify_cli/sync/__init__.py`.

**Files to create/edit**:
- `src/specify_cli/sync/diagnose.py` (or extend if exists)
- `src/specify_cli/sync/__init__.py`

**Type contract**:
- All parameters typed; `mypy --strict` clean.

---

## Subtask T009 — Refactor sync/auth/tracker print sites to use the helper

**Purpose**: Replace bare stdout-bound diagnostic prints with the helper.

**Steps**:

1. For each call site identified in T007:
   - If the site sits behind a `--json`-aware CLI command (most CLI sync paths), pass `json_mode=is_json` and the envelope dict if the command wants nested diagnostics.
   - Otherwise (background / non-CLI contexts), default to `json_mode=False` (writes to stderr).
2. Specifically:
   - `src/specify_cli/auth/transport.py`: replace any `Not authenticated, skipping sync` style prints with `emit_diagnostic(..., category="auth", json_mode=...)`. The two visible lines from earlier `mission create` runs are good ground-truth for what to delete.
   - `src/specify_cli/sync/`: same treatment for sync-skipped messages.
3. Make sure the helper call signature does not bleed `json_mode` plumbing into deep call stacks; thread it via an explicit context object or per-call argument as the existing code style allows.

**Files to edit**:
- `src/specify_cli/auth/transport.py`
- One or more files under `src/specify_cli/sync/` (depending on T007 inventory)

**Acceptance**:
- After this subtask, `grep -r "skipping sync" src/specify_cli/sync/ src/specify_cli/auth/` should return only test fixtures or strings inside the helper, not bare `print` calls.

---

## Subtask T010 — Parametrised integration test across 4 SaaS states  [P]

**Purpose**: Lock in the strict-JSON contract across the full SaaS state matrix.

**Steps**:

1. Create `tests/integration/test_json_envelope_strict.py`.
2. Define `_covered_commands` as a list of argv lists (from T007 inventory).
3. Define `_saas_states = ["disabled", "unauthorized", "network_failed", "authorized_success"]`.
4. Helpers to enter each state:
   - `disabled`: `monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)` and ensure no auth.
   - `unauthorized`: set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, force auth-failed mock.
   - `network_failed`: set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, monkeypatch the SaaS HTTP client to raise a connection error.
   - `authorized_success`: set up a passing auth + reachable mock.
5. Test body:
   ```python
   @pytest.mark.parametrize("argv", _covered_commands)
   @pytest.mark.parametrize("saas_state", _saas_states)
   def test_strict_json(argv, saas_state, runner, set_saas_state):
       set_saas_state(saas_state)
       result = runner.invoke(argv + ["--json"])
       parsed = json.loads(result.stdout)  # MUST succeed
       assert isinstance(parsed, dict)
   ```
6. The test MUST run in isolation (no real SaaS). Use the existing test fixtures for HTTP mocking and CLI invocation.

**Files to create**:
- `tests/integration/test_json_envelope_strict.py` (~180 lines)

---

## Subtask T011 — Bare-string regression scan of stdout  [P]

**Purpose**: Catch the original bug class directly.

**Steps**:

1. In the same test file as T010, add `test_no_bare_diagnostic_lines_on_stdout`:
   ```python
   FORBIDDEN_STRINGS = [
       "Not authenticated, skipping sync",
       "skipping sync",
       # add any other bare strings discovered in T007
   ]

   @pytest.mark.parametrize("argv", _covered_commands)
   def test_no_bare_diagnostic_lines_on_stdout(argv, runner, set_saas_state):
       set_saas_state("unauthorized")
       result = runner.invoke(argv + ["--json"])
       for forbidden in FORBIDDEN_STRINGS:
           assert forbidden not in result.stdout, f"{forbidden!r} leaked to stdout"
   ```
2. The forbidden list MUST include the exact strings observed during local `mission create --json` runs prior to the fix.

**Acceptance**:
- Running this test against the pre-fix code FAILS (sanity).
- Running it against the fixed code PASSES.

---

## Subtask T012 — Verify contracts cross-refs  [P]

**Purpose**: Keep planning docs in sync with what was built.

**Steps**:

1. Verify `kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/contracts/json-envelope.md` reflects what was actually built; if `T009`'s implementation chose a slightly different nesting key, update the contract doc to match.
2. **CHANGELOG entry is owned by WP07** (the capstone tranche-summary entry covers all seven issues including #842). Do **not** edit `CHANGELOG.md` from this WP — leave a one-line note in the PR description that #842's user-visible change is already covered by WP07's CHANGELOG entry.

---

## Test Strategy

- **Unit**: helper-level tests for `emit_diagnostic()` in each branch (json_mode × envelope).
- **Integration**: T010 + T011 together cover the full contract surface.
- **Coverage**: ≥ 90% on changed code (NFR-002).
- **Type safety**: `mypy --strict` on `sync/diagnose.py` and `auth/transport.py`.

## Definition of Done

- [ ] T007 — call sites inventoried; covered command list captured in test.
- [ ] T008 — `emit_diagnostic` helper exists with the specified signature.
- [ ] T009 — every identified bare-stdout diagnostic site refactored.
- [ ] T010 — parametrised test passes for all `(command, saas_state)` pairs.
- [ ] T011 — bare-string regression test passes.
- [ ] T012 — contracts cross-refs verified (CHANGELOG owned by WP07).
- [ ] No `print(...)` or `typer.echo(...)` in `sync/` or `auth/transport.py` writes to stdout during a `--json` command.
- [ ] `mypy --strict` clean on touched modules.

## Risks

- **Risk**: Threading `json_mode` through every diagnostic call site is noisy.
  **Mitigation**: Default the helper to stderr when `json_mode` is unknown — that matches the safe behavior. Add `json_mode` plumbing only for in-envelope nesting.
- **Risk**: Some `--json` command currently builds its envelope after a sync diagnostic was already printed.
  **Mitigation**: T009 must move the diagnostic emission **before** the envelope is finalised, or buffer it via the helper.
- **Risk**: Existing consumers may already swallow specific diagnostic strings on stdout.
  **Mitigation**: Diagnostics still appear on stderr or under the envelope; the only thing removed is the bare-stdout leak.

## Reviewer guidance

- Confirm the strict-JSON contract holds in all four SaaS states.
- Confirm there are no `print(` or `typer.echo(` calls that write to stdout from sync/auth/tracker paths during a `--json` invocation.
- Verify the helper is the **only** way bare diagnostics leave the runtime — a future maintainer should fail review if they bypass it.
- Confirm `tests/integration/test_json_envelope_strict.py` runs in isolation without real SaaS.

## Out of scope

- Adding `--json` to commands that don't have it today.
- Changing the SaaS protocol or the diagnostic content itself (only the routing changes).
- Reformatting the JSON output of any command — strict parsability does not require shape changes for already-strict commands.
