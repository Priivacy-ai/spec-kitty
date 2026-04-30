---
work_package_id: WP01
title: Error Foundation and StoredSession Extension
dependencies: []
requirement_refs:
- FR-001
- FR-010
planning_base_branch: auth-tranche-2-5-cli-contract-consumption
merge_target_branch: auth-tranche-2-5-cli-contract-consumption
branch_strategy: Planning artifacts for this feature were generated on auth-tranche-2-5-cli-contract-consumption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into auth-tranche-2-5-cli-contract-consumption unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-auth-tranche-2-5-cli-contract-consumption-01KQEJZK
base_commit: bc3d205cc57f7d50786b83c99b1a5bb1e15a7b1c
created_at: '2026-04-30T12:49:18.179828+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: claude
shell_pid: '88259'
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/errors.py
- src/specify_cli/auth/session.py
- tests/auth/test_session.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This sets your working style, quality bar, and tool preferences for this work package.

---

## Objective

Establish the two type additions that every downstream work package depends on:

1. `RefreshReplayError` — the new exception raised by `TokenRefreshFlow` on HTTP 409 benign replay.
2. `StoredSession.generation` — an optional int field for the token-family generation counter returned by Tranche 2 refresh responses.

These are small, additive changes. Both must be backward-compatible with existing persisted sessions.

---

## Context

**Repository root**: `/Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty`

**Mission**: CLI Auth Tranche 2.5 — aligning the CLI with the server's Tranche 2 auth contract (`/oauth/revoke`, refresh replay semantics, session-status). This WP is the foundation; WP02 (logout), WP03 (refresh 409), and WP04 (doctor) build on it.

**Key constraint**: The `from_dict()` change must use `data.get("generation")` (not `data["generation"]`) so that existing encrypted session files deserialized before Tranche 2.5 still load correctly with `generation=None`.

---

## Branch Strategy

- **Planning base branch**: `auth-tranche-2-5-cli-contract-consumption`
- **Merge target**: `auth-tranche-2-5-cli-contract-consumption`
- **Worktree**: Allocated by `finalize-tasks` / `lanes.json`. Use the path given by `spec-kitty agent action implement WP01 --agent claude`.

---

## Subtask T001 — Add `RefreshReplayError` to `auth/errors.py`

**File**: `src/specify_cli/auth/errors.py`

**Purpose**: Provide a typed exception that `TokenRefreshFlow.refresh()` raises on HTTP 409 `refresh_replay_benign_retry`. The `retry_after` field carries the server's hint (0–5 seconds).

**Steps**:

1. Open `src/specify_cli/auth/errors.py`.
2. Add after the existing `SessionInvalidError` class (which is also a `TokenRefreshError`):

```python
class RefreshReplayError(TokenRefreshError):
    """Raised when the server returns 409 refresh_replay_benign_retry.

    Indicates the presented refresh token was spent within the server's
    reuse-grace window. The token family is NOT revoked. The retry decision
    is made by run_refresh_transaction._run_locked, not the caller.
    """

    def __init__(self, retry_after: int = 0) -> None:
        super().__init__(
            f"Refresh token was just rotated by another process "
            f"(retry_after={retry_after}s)."
        )
        self.retry_after: int = retry_after
```

3. Add `RefreshReplayError` to `__all__` if the module uses one (check the file — it may not).

**Validation**:
- [ ] `from specify_cli.auth.errors import RefreshReplayError` works in a Python REPL.
- [ ] `RefreshReplayError` is a subclass of `TokenRefreshError` and `AuthenticationError`.
- [ ] `RefreshReplayError(retry_after=3).retry_after == 3`.
- [ ] `RefreshReplayError()` (no args) works with default 0.

---

## Subtask T002 — Add `generation: int | None = None` to `StoredSession`

**File**: `src/specify_cli/auth/session.py`

**Purpose**: `StoredSession` needs to hold the `generation` integer returned by the Tranche 2 refresh response. This is a forward-compatibility addition; existing sessions have `generation=None`.

**Steps**:

1. Open `src/specify_cli/auth/session.py`. Locate the `StoredSession` dataclass definition (it is NOT frozen — it uses `@dataclass` without `frozen=True`).

2. Append `generation` as the **last field** with default `None`:

```python
@dataclass
class StoredSession:
    # … existing fields …
    auth_method: AuthMethod  # existing last field

    generation: int | None = None  # ADD THIS — last, with default
```

   Placing it last with a default preserves compatibility for callers that construct `StoredSession` by positional args (if any exist — check `from_dict` and flow constructors).

**Validation**:
- [ ] `StoredSession` can be constructed without `generation` argument.
- [ ] `session.generation` is accessible and defaults to `None`.
- [ ] `mypy` (or `pyright`) doesn't flag the new field.

---

## Subtask T003 — Update `to_dict()` and `from_dict()` for `generation`

**File**: `src/specify_cli/auth/session.py`

**Purpose**: Serialize `generation` to disk and deserialize it safely from existing files that lack the field.

**Steps**:

1. In `StoredSession.to_dict()`, add the `generation` key to the returned dict (it is hand-written, not `asdict()`):

```python
def to_dict(self) -> dict[str, Any]:
    return {
        # … existing fields …
        "auth_method": self.auth_method,
        "generation": self.generation,  # ADD — None for pre-Tranche-2 sessions
    }
```

2. In `StoredSession.from_dict()`, read `generation` with `.get()` (key missing on old sessions → `None`):

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> StoredSession:
    # … existing field reads …
    return cls(
        # … existing args …
        auth_method=data["auth_method"],
        generation=data.get("generation"),  # ADD — None for legacy sessions
    )
```

**Validation**:
- [ ] `session.to_dict()["generation"]` is `None` for sessions without a generation.
- [ ] `StoredSession.from_dict(session.to_dict())` round-trips without loss.
- [ ] `StoredSession.from_dict({"generation": None, ...other_fields...})` works.
- [ ] `StoredSession.from_dict({...other_fields_without_generation...})` works (backward-compat).

---

## Subtask T004 — Verify Existing Round-Trip Tests

**File**: `tests/auth/test_session.py`

**Purpose**: Confirm that existing tests that construct `StoredSession` from dict or JSON still pass. No new tests need to be written here — if the existing tests pass, the change is safe.

**Steps**:

1. Run the session-specific tests:
   ```bash
   uv run pytest tests/auth/test_session.py -v
   ```

2. If any test fails, the failure is almost certainly one of two things:
   - A test constructing `StoredSession` positionally (fix: add `generation=None` to the construction, or verify the new field is at the end with a default).
   - A test asserting exact `to_dict()` output (fix: add `"generation": None` to the expected dict).

3. Fix failures; do not skip or comment out tests.

4. Optionally, add one round-trip regression test that explicitly verifies a dict without `"generation"` deserializes cleanly:
   ```python
   def test_from_dict_backward_compat_no_generation(make_stored_session):
       d = make_stored_session().to_dict()
       del d["generation"]
       session = StoredSession.from_dict(d)
       assert session.generation is None
   ```

**Validation**:
- [ ] `uv run pytest tests/auth/test_session.py -v` passes with no failures or errors.
- [ ] No test was skipped to make the suite green.

---

## Definition of Done

- [ ] `RefreshReplayError` importable from `specify_cli.auth.errors`.
- [ ] `StoredSession.generation` field exists with default `None`.
- [ ] `to_dict()` serializes `generation`; `from_dict()` deserializes it with `.get()`.
- [ ] `uv run pytest tests/auth/test_session.py -v` passes.
- [ ] No modifications to files outside `owned_files`.

## Risks

| Risk | Mitigation |
|------|-----------|
| `from_dict()` uses `data["generation"]` → `KeyError` on old sessions | Use `data.get("generation")` — always |
| New field breaks positional `StoredSession(...)` calls | Field is last with default; positional callers don't pass it |
| Test uses exact `to_dict()` output comparison | Extend expected dict to include `"generation": None` |
