---
work_package_id: WP05
title: Integration Tests and Dev Smoke
dependencies:
- WP03
- WP04
requirement_refs:
- FR-015
- FR-016
- FR-017
planning_base_branch: auth-tranche-2-5-cli-contract-consumption
merge_target_branch: auth-tranche-2-5-cli-contract-consumption
branch_strategy: Planning artifacts for this feature were generated on auth-tranche-2-5-cli-contract-consumption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into auth-tranche-2-5-cli-contract-consumption unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "39407"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/auth/integration/
execution_mode: code_change
owned_files:
- kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/dev-smoke-checklist.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

This is the verification and closure WP. It:

1. Runs the focused test suites to confirm zero legacy `/api/v1/logout` references survive (T020/e2e test is already updated in WP02).
2. Runs the full auth + status suite to confirm offline doctor tests pass unchanged.
3. Produces the dev smoke checklist against `https://spec-kitty-dev.fly.dev`.

**Preconditions**: WP03 (refresh 409 + revoke/logout) and WP04 (doctor --server) are both merged into the planning branch.

---

## Context

**Repository root**: `/Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty`

**Dev server environment variables** (required for smoke):
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
```

**Known non-issue**: `spec-kitty sync now` may report `server_error` for non-private teamspace ingress (issue #889). This is unrelated to auth — do not block smoke on it.

**Verification commands** (from start-here.md):
```bash
# Focused:
uv run pytest tests/cli/commands/test_auth_logout.py tests/auth/integration/test_logout_e2e.py
uv run pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py

# Full auth suite:
uv run pytest tests/auth tests/cli/commands/test_auth_status.py
```

---

## Branch Strategy

- **Planning base branch**: `auth-tranche-2-5-cli-contract-consumption`
- **Merge target**: `auth-tranche-2-5-cli-contract-consumption`
- **Start command**: `spec-kitty agent action implement WP05 --agent claude`

---

## Subtask T021 — Run Focused Test Suites; Confirm Zero Legacy Assertions

**Purpose**: Systematic sweep to confirm no surviving `/api/v1/logout` references and that the focused test commands from start-here.md all pass.

**Steps**:

1. Run the logout-specific suite:
   ```bash
   uv run pytest tests/cli/commands/test_auth_logout.py tests/auth/integration/test_logout_e2e.py -v
   ```
   All tests must pass. Zero failures or errors.

2. Grep for legacy endpoint references:
   ```bash
   grep -r "api/v1/logout" tests/ src/
   ```
   This must return no matches. If any are found, fix them before proceeding.

3. Run the doctor-specific suite:
   ```bash
   uv run pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_repair.py tests/auth/test_auth_doctor_offline.py -v
   ```
   All tests must pass, including the offline tests that assert no outbound calls.

**Validation**:
- [ ] Logout suite passes with zero failures.
- [ ] `grep -r "api/v1/logout" tests/ src/` returns no results.
- [ ] Doctor suite passes with zero failures.

---

## Subtask T022 — Run Full Auth + Status Suite

**Purpose**: Broader regression check covering all auth code touched by Tranche 2.5.

**Steps**:

1. Run the full auth suite plus auth_status:
   ```bash
   uv run pytest tests/auth tests/cli/commands/test_auth_status.py -v
   ```

2. If any failures are found:
   - Concurrency tests: verify the new `RefreshReplayError` handler in `_run_locked` doesn't break existing stale-grant-preservation test assertions.
   - Session tests: verify `StoredSession.from_dict()` backward-compat (missing `generation` key).
   - Token-manager tests: verify no new outcome branches are missing from its switch statement.

3. Fix any failures; do not skip tests.

4. Optionally (if time allows), run the broader sync-adjacent tests:
   ```bash
   uv run pytest tests/auth tests/sync/test_auth.py tests/sync/test_batch_sync.py -v
   ```
   These catch regressions in the shared token manager path, which WP03 touched. If these fail due to known issue #889 (sync queue ingress), note it as pre-existing.

**Validation**:
- [ ] `uv run pytest tests/auth tests/cli/commands/test_auth_status.py -v` passes with zero failures.
- [ ] Any sync test failures are confirmed as pre-existing (issue #889), not introduced by this branch.

---

## Subtask T023 — Produce `dev-smoke-checklist.md`

**File**: `kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/dev-smoke-checklist.md` (new file)

**Purpose**: Step-by-step checklist for manual verification against the live dev server. This is a planning artifact, not runnable in CI.

**Content**:

```markdown
# Dev Smoke Checklist: CLI Auth Tranche 2.5

## Prerequisites

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
```

Verify `spec-kitty --version` shows the Tranche 2.5 build.

## Step 1 — Login

```bash
spec-kitty auth login --force --headless
```

Expected:
- [ ] Login completes (browser or device flow).
- [ ] No error about missing SAAS_URL.

## Step 2 — Status

```bash
spec-kitty auth status
```

Expected:
- [ ] Shows email, session ID, token expiry.
- [ ] Access token is valid (not expired).

## Step 3 — Auth Doctor (offline, default)

```bash
spec-kitty auth doctor
```

Expected:
- [ ] Output includes Identity, Tokens, Storage, Refresh Lock, Daemon, Orphans, Findings sections.
- [ ] Ends with hint: "Run `spec-kitty auth doctor --server` to verify server session status."
- [ ] No outbound network calls (can verify with Wireshark or network proxy if needed).
- [ ] Exit code 0 (no critical findings).

## Step 4 — Auth Doctor with --server

```bash
spec-kitty auth doctor --server
```

Expected:
- [ ] Output includes all offline sections PLUS a "Server Session" section.
- [ ] Server Session shows "active" with a session ID.
- [ ] No raw token values, token_family_id, or revocation_reason in output.
- [ ] Exit code 0.

## Step 5 — Logout

```bash
spec-kitty auth logout
```

Expected:
- [ ] "Server revocation confirmed." (or "not confirmed" with a reason — depends on server state).
- [ ] "Local credentials deleted." or "+ Logged out."
- [ ] Exit code 0 regardless of server revocation outcome.
- [ ] Local session is gone: `spec-kitty auth status` shows "not logged in".

## Step 6 — Post-Logout Status

```bash
spec-kitty auth status
```

Expected:
- [ ] "Not authenticated" or equivalent.

## Known Non-Issue

`spec-kitty sync now` may report `server_error` for non-private teamspace ingress.
This is pre-existing issue #889 and is not related to Tranche 2.5 auth changes.
```

**Validation**:
- [ ] File written to the correct path under `kitty-specs/`.
- [ ] All 6 steps have checkbox items.
- [ ] The "Known Non-Issue" section is present.

---

## Definition of Done

- [ ] `grep -r "api/v1/logout" tests/ src/` returns no results (e2e test updated in WP02).
- [ ] `uv run pytest tests/cli/commands/test_auth_logout.py tests/auth/integration/test_logout_e2e.py -v` passes.
- [ ] `uv run pytest tests/auth/test_auth_doctor_offline.py -v` passes (offline tests unchanged).
- [ ] `uv run pytest tests/auth tests/cli/commands/test_auth_status.py -v` passes.
- [ ] `dev-smoke-checklist.md` written at correct path.
- [ ] No modification to files outside `owned_files`.

## Risks

| Risk | Mitigation |
|------|-----------|
| Full suite failures from pre-existing issues (#889) | Document as pre-existing; do not block Tranche 2.5 on them |
| Dev server unreachable at smoke time | Smoke checklist is manual; note in checklist that env vars must be set |
| `grep` misses a reference in a comment | Review any grep hits manually; comments referencing `/api/v1/logout` should also be removed |

## Activity Log

- 2026-04-30T13:55:30Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=39407 – Started implementation via action command
