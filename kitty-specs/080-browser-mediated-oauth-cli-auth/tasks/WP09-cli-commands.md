---
work_package_id: WP09
title: CLI Commands - Login, Logout, Status
dependencies:
- WP05
- WP06
- WP04
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T065
- T066
- T067
- T068
- T069
- T070
- T071
- T072
- T073
history: []
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/auth.py
- tests/cli/test_auth_commands.py
status: pending
tags: []
---

# WP09: CLI Commands - Login, Logout, Status

**Objective**: Build user-facing command interface: `spec-kitty auth login`, `spec-kitty auth login --headless`, `spec-kitty auth logout`, `spec-kitty auth status`.

**Context**: User-facing feature. Depends on WP05-WP06 (auth flows), WP04 (TokenManager).

**Acceptance Criteria**:
- [ ] `auth login` opens browser, handles callback
- [ ] `auth login --headless` uses device flow
- [ ] `auth logout` revokes session, deletes credentials
- [ ] `auth status` shows user, teams, token expiry
- [ ] Progress messages shown during login
- [ ] Error messages guide user recovery
- [ ] All tests pass (100% coverage)

---

## Implementation Guidance

Create `src/specify_cli/cli/commands/auth.py`:
```python
@app.command()
async def login(headless: bool = False):
    """Log in with OAuth."""
    tm = TokenManager.get_instance()
    
    if tm.is_authenticated:
        typer.echo("Already logged in as " + tm.session.username)
        return
    
    if headless or not BrowserLauncher.is_available():
        flow = DeviceCodeFlow()
    else:
        flow = AuthorizationCodeFlow()
    
    session = await flow.login()
    typer.echo(f"✓ Authenticated as {session.username}")

@app.command()
async def logout():
    """Log out and revoke session."""
    tm = TokenManager.get_instance()
    if not tm.is_authenticated:
        typer.echo("Not logged in")
        return
    
    try:
        await tm.logout()
    except:
        pass  # Continue with local cleanup
    
    typer.echo("✓ Logged out")

@app.command()
async def status():
    """Show authentication status."""
    tm = TokenManager.get_instance()
    session = tm.get_current_session()
    
    if not session:
        typer.echo("Not logged in")
        return
    
    typer.echo(f"User: {session.username}")
    typer.echo(f"Teams:")
    for team in session.teams:
        default = " [default]" if team.id == session.default_team_id else ""
        typer.echo(f"  - {team.name} ({team.role}){default}")
```

**Files**:
- `src/specify_cli/cli/commands/auth.py` (~100 lines)
- `tests/cli/test_auth_commands.py` (~150 lines)

---

## Definition of Done

- [ ] Commands parse arguments correctly
- [ ] Browser/headless auto-detection works
- [ ] Progress displayed during login
- [ ] Error messages are actionable
- [ ] Status shows all required information

