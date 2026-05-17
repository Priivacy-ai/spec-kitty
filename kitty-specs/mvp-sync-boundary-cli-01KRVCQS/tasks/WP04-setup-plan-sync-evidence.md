---
work_package_id: WP04
title: Setup-plan SaaS-evidence guarantee
dependencies:
- WP01
- WP02
requirement_refs:
- FR-011
- FR-012
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-003
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
phase: Phase 2 - Setup-plan
agent: claude
history:
- timestamp: '2026-05-17T16:42:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- tests/runtime/test_setup_plan_sync_evidence.py
role: implementer
tags: []
---

# Work Package Prompt: WP04 — Setup-plan SaaS-evidence guarantee

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Lock the setup-plan code path so that:

1. (FR-011) When `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and the foreground is NOT authenticated, `spec-kitty agent mission setup-plan` exits non-zero with a specific diagnostic that names "SaaS sync cannot be guaranteed" and writes NO rows to any queue DB.
2. (FR-012) Every body-upload-emitting and canonical-event-emitting code path inside setup-plan goes through `default_queue_db_path()`. No setup-plan code path may open the legacy DB directly.
3. (Regression) An authenticated tmp HOME running setup-plan produces ≥1 row in the active scoped queue and 0 rows in legacy.

Done means:
- Setup-plan refuses loudly under FR-011 conditions, with a clear error message and non-zero exit.
- Audit comment in the setup-plan code path lists every queue-write call site and references this WP as the source of the lock.
- Regression test at `tests/runtime/test_setup_plan_sync_evidence.py`:
  - Test A: tmp HOME with valid session/credentials → setup-plan succeeds; assert scoped DB row count > 0 AND legacy DB row count == 0.
  - Test B: tmp HOME without auth + `SPEC_KITTY_ENABLE_SAAS_SYNC=1` → setup-plan exits non-zero; assert error message contains "SaaS sync cannot be guaranteed"; assert no DB writes occurred (scoped DB does not exist or is unchanged; legacy unchanged).
  - Test C: AST or grep-style regression — search every file in the setup-plan code path for `_legacy_queue_db_path(` calls; assert zero hits outside of explicitly-documented "legacy access" call sites (the migration function itself is exempt).
- `mypy --strict src/specify_cli/cli/commands/agent/` passes.
- Final NFR-002 gate: `uv run pytest tests/sync tests/status tests/runtime` passes.
- Final NFR-004 gate: `mypy --strict src/specify_cli/sync/ src/specify_cli/cli/commands/sync/ src/specify_cli/cli/commands/agent/` passes.

## Context & Constraints

- Spec: FR-011, FR-012, NFR-001..NFR-004, C-001, C-003, C-004.
- Depends on WP01 (scoped DB writes) and WP02 (auth coherence helpers).
- Existing setup-plan: search via `grep -rn "setup-plan\|setup_plan" src/specify_cli/cli/commands/agent/`. Most likely entrypoint is `src/specify_cli/cli/commands/agent/mission.py` (a `setup_plan` Typer command).
- Existing auth detection: use whatever the project already has — typically `read_queue_scope_from_session()` returning non-None means authenticated, plus a credentials check.

## Subtasks

### T017 — Audit setup-plan write paths
- Read the setup-plan code path top to bottom.
- For each call site that opens or writes to a queue DB (`sqlite3.connect`, `_legacy_queue_db_path`, `default_queue_db_path`, `OfflineQueue`, body upload helpers), document the call site.
- Confirm every body-upload-emitting path uses `default_queue_db_path()`. If any path uses `_legacy_queue_db_path()` directly, replace it with `default_queue_db_path()` (this is the FR-012 fix).
- Add a code comment block at the top of the setup-plan command block listing the audited call sites, the date (2026-05-17), and the FR-012 lock.

### T018 — FR-011 refuse-loudly
- At the start of the setup-plan command (before any queue write), check:
  ```python
  if os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC") == "1":
      scope = read_queue_scope_from_session() or read_queue_scope_from_credentials()
      if not scope:
          raise typer.Exit(code=2, ...)  # or rich-formatted error with message containing
          # "SaaS sync cannot be guaranteed: no authenticated session/credentials found."
  ```
- Use the project's existing error-reporting pattern (Rich Console + non-zero exit). Use exit code 2 or whatever convention exists.

### T019 — Regression tests
- Create `tests/runtime/test_setup_plan_sync_evidence.py`:
  - Test A (`test_authenticated_setup_plan_lands_in_scoped`):
    - `monkeypatch.setenv("HOME", str(tmp_path))`; create a fake credentials file (mirror the format `read_queue_scope_from_credentials` expects).
    - Invoke setup-plan via the typer runner.
    - Assert `scope_db_path(<scope>).exists()` AND has > 0 rows in `body_upload_queue` or `queue`.
    - Assert `_legacy_queue_db_path()` either doesn't exist or has 0 rows in those tables.
  - Test B (`test_setup_plan_refuses_without_auth_when_saas_enabled`):
    - `monkeypatch.setenv("HOME", str(tmp_path))`; `monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")`; no credentials.
    - Invoke setup-plan; assert non-zero exit.
    - Assert the error message contains the FR-011 phrase.
    - Assert no scoped DB or legacy DB was created.
  - Test C (`test_no_legacy_db_path_calls_in_setup_plan_code`):
    - Use `ast` to walk every Python file in the setup-plan code path (resolve via grep/imports) and assert no `Call(func=Name(id='_legacy_queue_db_path'))` exists.

### T020 — Full gate
- `uv run pytest tests/sync tests/status tests/runtime` — green.
- `uv run mypy --strict src/specify_cli/sync/ src/specify_cli/cli/commands/sync/ src/specify_cli/cli/commands/agent/` — green.

## Branch Strategy

Planning base: `main`. Final merge target: `main`. This WP lands last in the mission; it provides the cross-cutting regression test.

## Definition of Done

- [ ] FR-011 refuse-loudly implemented and tested
- [ ] FR-012 audit comment in setup-plan code; no direct `_legacy_queue_db_path` calls in setup-plan paths
- [ ] All three tests in T019 pass
- [ ] NFR-002 full suite green
- [ ] NFR-004 mypy --strict green
- [ ] No new deps

## Risks

- Setup-plan may have hidden indirect callers of `_legacy_queue_db_path()` (e.g., via shared helpers). Mitigated by T017 audit + T019 Test C AST regression.

## Reviewer Guidance

- Confirm: setup-plan exits non-zero with no DB writes when SAAS_SYNC=1 and unauth.
- Confirm: setup-plan writes to scoped DB only when authenticated.
- Confirm: AST regression test catches `_legacy_queue_db_path` calls anywhere in the audited setup-plan modules.
- Run the full suite locally: green.
