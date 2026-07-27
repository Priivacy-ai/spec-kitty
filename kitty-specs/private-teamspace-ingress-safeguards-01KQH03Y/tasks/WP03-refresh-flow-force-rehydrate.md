---
work_package_id: WP03
title: Refresh-Hook Integration Tests
dependencies:
- WP02
requirement_refs:
- FR-008
- FR-011
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-01T06:33:00+00:00'
subtasks:
- T012
- T013
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "63593"
history:
- date: '2026-05-01'
  author: spec-kitty.tasks
  note: Initial WP generated
- date: '2026-05-01'
  author: spec-kitty.analyze
  note: Reduced to test-only WP. The hook code was moved into WP02 (T011) because TokenManager.refresh_if_needed() is the actual adoption boundary; flows/refresh.py only returns a session, it does not adopt or persist. T011 was dropped from this WP and reassigned to WP02. owned_files no longer includes auth/flows/refresh.py because that file is not modified.
agent_profile: python-pedro
authoritative_surface: tests/auth/
execution_mode: code_change
owned_files:
- tests/auth/test_refresh_flow.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Write the integration tests that prove the post-refresh rehydrate hook (delivered in WP02 / T011) behaves correctly:

- When a token refresh adopts a session that lacks a Private Teamspace, exactly one `/api/v1/me` GET fires, the session is updated on disk, and the result returned to the caller has a Private Teamspace.
- When a token refresh adopts a session that already has a Private Teamspace, **no** `/api/v1/me` GET fires — the refresh stays a single round trip.

This WP touches only `tests/auth/test_refresh_flow.py`. It does **not** modify any source files. The hook code itself lives in `TokenManager.refresh_if_needed()` (WP02 owns `token_manager.py`), and the file `src/specify_cli/auth/flows/refresh.py` is not modified by this mission at all.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP03 --agent <name>`; do not guess the worktree path

## Context

### Why this WP is test-only

The reviewer correctly observed that `TokenRefreshFlow.refresh(session)` in `auth/flows/refresh.py:56` only returns a fresh `StoredSession`. Adoption (`self._session = result.session`) and persistence happen inside `TokenManager.refresh_if_needed()` at `auth/token_manager.py:171`. A hook in `flows/refresh.py` would therefore not run on the hot path. The hook lives in `refresh_if_needed()`, and **WP02 owns that file**.

This WP exists to (a) lock down the integration behavior with explicit tests at the `await token_manager.refresh_if_needed()` boundary, and (b) regression-protect the "healthy refresh = single round trip" property (FR-011 / NFR-004 spirit).

### Existing code surface

- `auth/token_manager.py:171` — `async def refresh_if_needed(self) -> bool`. WP02 / T011 adds the post-adoption hook here.
- `auth/flows/refresh.py:56` — `async def refresh(session) -> StoredSession`. Unchanged.
- `tests/auth/test_refresh_flow.py` — existing test file. Add new cases here.

### Spec & contract references

- `spec.md` — FR-008, FR-011, Scenario 5
- `contracts/api.md` §6
- `plan.md` §1.6

## Scope guardrail (binding)

This WP MUST NOT:

- Touch any source file under `src/specify_cli/`.
- Add new test fixtures that overlap with WP02's; reuse the fixtures from `tests/auth/conftest.py` and `tests/auth/test_token_manager.py`.

This WP MUST:

- Drive the integration test through `await token_manager.refresh_if_needed()`, **not** through `flow.refresh()` directly. The hook only runs through the TokenManager entry point.

## Subtasks

### T012 — Test: refresh adopting a shared-only session triggers the rehydrate hook

**Purpose**: Prove that `TokenManager.refresh_if_needed()` calls `rehydrate_membership_if_needed(force=True)` after adopting a session whose `teams` list lacks a Private Teamspace, AND that the resulting session contains the Private Teamspace from the SaaS.

**Steps**:

In `tests/auth/test_refresh_flow.py`:

```python
@pytest.mark.asyncio
@respx.mock
async def test_refresh_force_rehydrates_when_adopted_session_lacks_private_team(
    token_manager_with_expired_shared_only_session,
):
    """A refresh whose adopted session lacks a Private Teamspace must trigger
    rehydrate_membership_if_needed(force=True) and end with a private session."""
    # OAuth refresh response
    respx.post("https://saas.example/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "new-tok",
                "refresh_token": "new-rtok",
                "expires_in": 3600,
            },
        )
    )
    # /api/v1/me — provides the Private Teamspace
    me_route = respx.get("https://saas.example/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {"id": "t-private", "is_private_teamspace": True},
                    {"id": "t-shared", "is_private_teamspace": False},
                ],
            },
        )
    )

    refreshed = await token_manager_with_expired_shared_only_session.refresh_if_needed()

    assert refreshed is True
    assert me_route.call_count == 1
    updated = token_manager_with_expired_shared_only_session.get_current_session()
    assert any(t.is_private_teamspace for t in updated.teams)
    assert updated.default_team_id == "t-private"  # recomputed via pick_default_team_id
```

The fixture `token_manager_with_expired_shared_only_session` builds a `TokenManager` with:
- An expired access token (so `refresh_if_needed()` actually runs the OAuth dance).
- An initial `StoredSession.teams` containing only shared teams.
- `_saas_base_url = "https://saas.example"` (or the equivalent attribute the implementation uses).

If a similar fixture already exists in `tests/auth/conftest.py`, reuse it; otherwise define this one in `tests/auth/test_refresh_flow.py` directly.

**Files**:

- `tests/auth/test_refresh_flow.py` — add 1 test function and possibly 1 fixture.

**Validation**:

- [ ] Test asserts `me_route.call_count == 1`.
- [ ] Test confirms post-refresh session contains a Private Teamspace.
- [ ] Test confirms `default_team_id` was recomputed via `pick_default_team_id` (i.e., points at the private team), not preserved from the old session.

---

### T013 — Test: healthy refresh stays a single round trip (no extra `/api/v1/me`)

**Purpose**: Prove that when the refreshed session already contains a Private Teamspace, no `/api/v1/me` call is made. This is the FR-011 / NFR-004 regression guard — healthy refresh is byte-identical to pre-mission behavior in HTTP traffic.

**Steps**:

```python
@pytest.mark.asyncio
@respx.mock
async def test_refresh_healthy_session_no_extra_me_call(
    token_manager_with_expired_private_session,
):
    """Refresh with an already-private session must NOT issue /api/v1/me."""
    respx.post("https://saas.example/oauth/token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "new-tok",
                "refresh_token": "new-rtok",
                "expires_in": 3600,
            },
        )
    )
    me_route = respx.get("https://saas.example/api/v1/me").mock(return_value=httpx.Response(200, json={}))

    refreshed = await token_manager_with_expired_private_session.refresh_if_needed()

    assert refreshed is True
    assert me_route.call_count == 0
```

The fixture `token_manager_with_expired_private_session` is the parallel of T012's fixture, but the initial session has `teams=[Team(id="t-private", is_private_teamspace=True)]`.

**Files**:

- `tests/auth/test_refresh_flow.py` — add 1 test function and possibly 1 parallel fixture.

**Validation**:

- [ ] Test asserts `me_route.call_count == 0`.
- [ ] Refresh still completes successfully and returns the new tokens.

---

## Definition of Done

- [ ] Two new tests in `tests/auth/test_refresh_flow.py` (T012, T013), both green.
- [ ] All pre-existing `tests/auth/test_refresh_flow.py` tests still pass.
- [ ] No source files were modified by this WP.
- [ ] `mypy --strict` and `ruff check` green for the test file.

## Risks & reviewer guidance

| Risk | Mitigation |
|------|------------|
| Tests pass even if WP02's hook is missing | Each test asserts `me_route.call_count` (1 in T012, 0 in T013) at the `await token_manager.refresh_if_needed()` boundary. If WP02/T011 was forgotten, T012's count would be 0 and the test would fail. |
| Test-only WP feels under-budget | Intentional — the hook code is in WP02. Two focused integration tests are enough to lock the cross-module contract. |
| The fixture for an "expired session with shared-only teams" doesn't exist | Author it in this file; it's a 5-line factory. Do not refactor `tests/auth/conftest.py` for this. |

**Reviewer should verify**:

- Both tests drive through `await token_manager.refresh_if_needed()` — NOT directly through `TokenRefreshFlow.refresh(...)`.
- T013 asserts zero `/api/v1/me` GETs (the healthy-path regression guard).
- T012 asserts both the call count AND the resulting session shape (private team present, `default_team_id` is the private team's id).

---

## Implementation command (after dependencies satisfied)

```bash
spec-kitty agent action implement WP03 --agent <name>
```

This WP depends on **WP02** (the hook code in `TokenManager.refresh_if_needed()` must exist).

## Activity Log

- 2026-05-01T09:48:53Z – claude:sonnet:python-pedro:implementer – shell_pid=35491 – Started implementation via action command
- 2026-05-01T09:53:22Z – claude:sonnet:python-pedro:implementer – shell_pid=35491 – Ready for review: 2 integration tests for the refresh-hook delivered in WP02.
- 2026-05-01T09:53:46Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=63593 – Started review via action command
- 2026-05-01T09:57:46Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=63593 – Review passed: refresh-hook integration tests cover forced rehydrate and healthy no-/me path
