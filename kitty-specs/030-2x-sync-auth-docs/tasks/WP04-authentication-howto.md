---
work_package_id: WP04
title: Authentication How-To
lane: "done"
dependencies: [WP01]
base_branch: 030-2x-sync-auth-docs-WP01
base_commit: 514106af212e8706bdecdde924cd95167e73b67d
created_at: '2026-02-05T15:20:53.956867+00:00'
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - How-To
assignee: ''
agent: ''
shell_pid: "17384"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-05T15:08:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Authentication How-To

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `docs/how-to/authenticate.md` — a task-oriented guide for logging in, checking status, and logging out.
- **FR-002**: How-to for each `auth` subcommand.
- **FR-010**: Working CLI examples for all auth commands.
- A developer can follow this guide to authenticate without consulting other docs.

## Context & Constraints

- **Branch**: `docs/2x-sync-auth` off `2.x`
- **Style reference**: `docs/how-to/install-spec-kitty.md` — follow this page's structure (prerequisites, steps, troubleshooting, See Also)
- **Source for CLI output**: `git show fc0597de:src/specify_cli/cli/commands/auth.py`
- **Depends on WP01**: This page links to reference entries for auth commands
- **Implementation command**: `spec-kitty implement WP04 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T017 – Write prerequisites section

- **Purpose**: Establish what the reader needs before authenticating.
- **Steps**:
  1. Create `docs/how-to/authenticate.md`
  2. Write H1: `# How to Authenticate with a Spec Kitty Server`
  3. Write brief intro: "Connect your spec-kitty CLI to a team server for syncing project data."
  4. Prerequisites list:
     - spec-kitty 2.x installed
     - Server URL (provided by your team admin)
     - Valid credentials (username and password for the server)
     - Server URL configured in `~/.spec-kitty/config.toml` (link to configuration reference)
  5. Add horizontal rule `---` separator
- **Files**: `docs/how-to/authenticate.md`

### Subtask T018 – Write login procedure

- **Purpose**: Step-by-step guide to authenticating.
- **Steps**:
  1. Add `## Log In` section
  2. Document interactive login:
     ```bash
     spec-kitty auth login
     ```
     Expected prompts:
     ```
     Username: user@example.com
     Password: ********
     Authenticating with https://your-server.example.com...
     ✅ Login successful!
        Logged in as: user@example.com
     ```
  3. Document non-interactive login (for scripts/CI):
     ```bash
     spec-kitty auth login --username user@example.com --password "$PASSWORD"
     ```
  4. Document re-authentication with `--force`:
     ```bash
     spec-kitty auth login --force
     ```
     Explain: Use when tokens are corrupted or you need to switch accounts
  5. Add horizontal rule separator
- **Files**: `docs/how-to/authenticate.md`

### Subtask T019 – Write status check section

- **Purpose**: Show how to verify authentication state and interpret output.
- **Steps**:
  1. Add `## Check Authentication Status` section
  2. Document the command:
     ```bash
     spec-kitty auth status
     ```
  3. Show authenticated output:
     ```
     ✅ Authenticated
        Username: user@example.com
        Server:   https://your-server.example.com
        Access token: valid (23h remaining)
        Refresh token: valid (6d remaining)
     ```
  4. Explain token expiry: access tokens auto-refresh, but when the refresh token expires, you'll need to `auth login` again
  5. Show unauthenticated output:
     ```
     ❌ Not authenticated
        Run 'spec-kitty auth login' to authenticate.
     ```
- **Files**: `docs/how-to/authenticate.md`

### Subtask T020 – Write logout procedure

- **Purpose**: Document how to clear credentials.
- **Steps**:
  1. Add `## Log Out` section
  2. Document:
     ```bash
     spec-kitty auth logout
     ```
     Expected output:
     ```
     ✅ Logged out successfully.
        Cleared credentials for: user@example.com
     ```
  3. Note: Logging out clears stored tokens. You'll need to log in again to use sync features.
- **Files**: `docs/how-to/authenticate.md`

### Subtask T021 – Write troubleshooting section

- **Purpose**: Address common auth problems.
- **Steps**:
  1. Add `## Troubleshooting` section
  2. Document these scenarios (based on error handling in auth.py):
     - **"Invalid username or password"**: Check credentials, try again
     - **"Cannot reach server"**: Check network, verify server URL in config.toml
     - **"Server temporarily unavailable"**: Try again in a few minutes
     - **"Session expired"**: Refresh token has expired, run `auth login` again
     - **"Cannot access credentials file"**: Check file permissions (`chmod 600 ~/.spec-kitty/credentials.json`)
  3. Each troubleshooting item should show the error message and the fix
- **Files**: `docs/how-to/authenticate.md`

### Subtask T022 – Write See Also links

- **Purpose**: Link to related documentation.
- **Steps**:
  1. Add `## See Also` section
  2. Links:
     - [CLI Commands: `spec-kitty auth`](../reference/cli-commands.md#spec-kitty-auth) — Detailed flag reference
     - [Configuration: Server & Credentials](../reference/configuration.md#server-configuration-2x) — Config file formats
     - [Server Connection Tutorial](../tutorials/server-connection.md) — End-to-end setup guide
     - [Sync Architecture](../explanations/sync-architecture.md) — How authentication fits into sync
- **Files**: `docs/how-to/authenticate.md`

## Risks & Mitigations

- **Risk**: CLI output may differ when commands are restored → Representative output from source code
- **Risk**: Error message text may change → Keep troubleshooting generic enough to remain useful

## Review Guidance

- Verify the page follows how-to style (task-oriented, not tutorial or reference)
- Check all CLI examples show realistic output
- Verify links to WP01 reference entries use correct anchors
- Confirm troubleshooting covers all error paths from the source code

## Activity Log

- 2026-02-05T15:08:07Z – system – lane=planned – Prompt created.
- 2026-02-05T15:23:11Z – unknown – shell_pid=17384 – lane=for_review – Created how-to/authenticate.md covering login, logout, status, troubleshooting
