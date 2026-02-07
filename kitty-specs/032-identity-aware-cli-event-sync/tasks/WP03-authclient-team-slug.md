---
work_package_id: "WP03"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
title: "AuthClient Team Slug"
phase: "Phase 1 - Core Implementation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – AuthClient Team Slug

## Implementation Command

```bash
spec-kitty implement WP03
```

No `--base` flag needed (can run in parallel with WP02).

---

## Objectives & Success Criteria

**Goal**: Add `get_team_slug()` method to AuthClient and store team_slug on login.

**Scope Note**: Post-MVP (only required once SaaS exposes team_slug in auth/user endpoints).

**Success Criteria**:
- [ ] `AuthClient().get_team_slug()` returns team slug after login
- [ ] Team slug stored in credentials file
- [ ] Returns "local" when not authenticated
- [ ] All tests pass

---

## Context & Constraints

**Target Branch**: 2.x

**Supporting Documents**:
- [spec.md](../spec.md) - User Story 4 (Team Slug Resolution)
- [data-model.md](../data-model.md) - EventEnvelope team_slug field

**Key Constraints**:
- Must not break existing auth flow
- Credentials file format must remain backward compatible
- Default to "local" for unauthenticated users

**Parallel**: This WP can run in parallel with WP02 (different files).

---

## Subtasks & Detailed Guidance

### Subtask T012 – Add get_team_slug() method to AuthClient

**Purpose**: Provide method for EventEmitter to resolve team context.

**Steps**:
1. Open `src/specify_cli/sync/auth.py`
2. Find the `AuthClient` class
3. Add `get_team_slug()` method:
   ```python
   def get_team_slug(self) -> str | None:
       """Return stored team slug, or None if not authenticated."""
       if not self.is_authenticated():
           return None
       
       return self.credential_store.get_team_slug()
   ```

**Files**:
- `src/specify_cli/sync/auth.py` (modify, ~10 lines added)

**Notes**:
- This method is already expected by `EventEmitter._get_team_slug()` (see emitter.py)
- Returns `None` if not authenticated (caller converts to "local")

---

### Subtask T013 – Store team_slug in credentials during login

**Purpose**: Persist team_slug received from SaaS during OAuth flow.

**Steps**:
1. Find the login flow in `AuthClient` (`obtain_tokens()` in 2.x)
2. After successful authentication, store team_slug:
   ```python
   def login(self, ...) -> bool:
       # ... existing OAuth flow ...
       
       # After getting tokens from SaaS, also get team info
       team_slug = self._fetch_team_slug()  # API call to SaaS
       
       # Store in credentials
       self.credential_store.save(
           access_token=access_token,
           refresh_token=refresh_token,
           access_expires_at=access_expires_at,
           refresh_expires_at=refresh_expires_at,
           username=username,
           server_url=self.server_url,
           team_slug=team_slug,  # NEW field (optional)
       )
       
       return True
   ```
3. Extend `CredentialStore.save()`/`load()` to persist `user.team_slug` and add
   `get_team_slug()` helper for retrieval.
4. If SaaS doesn't provide team_slug yet, set to `None` (graceful)

**Files**:
- `src/specify_cli/sync/auth.py` (modify, ~20 lines changed)

**Notes**:
- Team slug typically comes from `/api/v1/me` or similar endpoint
- If SaaS doesn't have this endpoint yet, store `None` (will be added later)
- Credentials are stored in TOML at `~/.spec-kitty/credentials`

---

### Subtask T014 – Handle unauthenticated case

**Purpose**: Return sensible default when not authenticated.

**Steps**:
1. Update `EventEmitter._get_team_slug()` in emitter.py to handle `None`:
   ```python
   def _get_team_slug(self) -> str:
       """Get team_slug from AuthClient. Returns 'local' if unavailable."""
       try:
           if hasattr(self.auth, "get_team_slug"):
               slug = self.auth.get_team_slug()
               if slug:
                   return slug
       except Exception as e:
           _console.print(f"[yellow]Warning: Could not resolve team_slug: {e}[/yellow]")
       return "local"  # Default for unauthenticated or missing team
   ```
2. This code may already exist (check emitter.py); ensure it handles `None` properly

**Files**:
- `src/specify_cli/sync/emitter.py` (verify/modify, ~5 lines)

**Notes**:
- "local" is the default for offline/unauthenticated operation
- Never raise exception - team_slug is optional context

---

### Subtask T015 – Write tests for get_team_slug

**Purpose**: Verify team slug resolution in all scenarios.

**Steps**:
1. Create or update `tests/sync/test_auth.py`
2. Add tests:
   ```python
   class TestAuthClientTeamSlug:
       def test_get_team_slug_authenticated(self, mock_credentials):
           """get_team_slug returns stored slug when authenticated."""
           mock_credentials["user"]["team_slug"] = "my-team"
           client = AuthClient()
           assert client.get_team_slug() == "my-team"
       
       def test_get_team_slug_unauthenticated(self):
           """get_team_slug returns None when not authenticated."""
           client = AuthClient()
           # Ensure not authenticated
           assert client.get_team_slug() is None
       
       def test_get_team_slug_missing_from_creds(self, mock_credentials):
           """get_team_slug returns None when field missing from creds."""
           # Authenticated but no team_slug field
           del mock_credentials["user"]["team_slug"]
           client = AuthClient()
           assert client.get_team_slug() is None
   ```

**Files**:
- `tests/sync/test_auth.py` (modify, ~40 lines added)

**Test Commands**:
```bash
pytest tests/sync/test_auth.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SaaS doesn't provide team_slug yet | Gracefully handle None; store when available |
| Credentials file format change | Keep backward compatible; handle missing field |

---

## Review Guidance

**Reviewers should verify**:
1. `get_team_slug()` never raises exception
2. Credentials file format is backward compatible
3. Default to "local" works correctly

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
