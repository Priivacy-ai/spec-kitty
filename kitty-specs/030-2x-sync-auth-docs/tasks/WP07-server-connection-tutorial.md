---
work_package_id: WP07
title: Server Connection Tutorial
lane: "done"
dependencies: [WP04, WP05]
base_branch: 030-2x-sync-auth-docs-WP04
base_commit: 6f6fbb5be34a1b0bc64b3a67471d3dbaaf9f1c3d
created_at: '2026-02-05T15:31:10.184368+00:00'
subtasks:
- T034
- T035
- T036
- T037
- T038
- T039
phase: Phase 4 - Tutorial
assignee: ''
agent: ''
shell_pid: "19631"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-05T15:08:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 – Server Connection Tutorial

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `docs/tutorials/server-connection.md` — end-to-end tutorial from zero to first sync.
- **FR-001**: Tutorial covers server URL config, `auth login`, verify with `auth status`.
- **SC-002**: A new 2.x user can follow start-to-finish and have a working sync connection.
- Must be a **standalone guide** — reader should not need to consult other docs to complete it.

## Context & Constraints

- **Branch**: `docs/2x-sync-auth` off `2.x`
- **Divio tutorial style**: Learning-oriented, concrete steps, defined start/end states
- **References existing tutorials**: Follow style of `docs/tutorials/getting-started.md` and `docs/tutorials/your-first-feature.md`
- **This is the MVP entry point** for 2.x server features
- **Implementation command**: `spec-kitty implement WP07 --base WP04` (or `--base WP05`, whichever is merged last)

## Subtasks & Detailed Guidance

### Subtask T034 – Write introduction and prerequisites

- **Purpose**: Set expectations and define what the reader will learn.
- **Steps**:
  1. Create `docs/tutorials/server-connection.md`
  2. Write H1: `# Connect to a Spec Kitty Server`
  3. Write intro:
     > In this tutorial, you'll connect your spec-kitty CLI to a team server. By the end, you'll have authenticated, verified your connection, and pushed your first sync.
  4. **What you'll learn**:
     - How to configure the server URL
     - How to authenticate from the CLI
     - How to verify your connection
     - How to sync events with the server
  5. **Prerequisites**:
     - spec-kitty 2.x installed (`spec-kitty --version` shows 2.x)
     - A spec-kitty server URL (provided by your team admin)
     - Your username and password for the server
     - At least one spec-kitty project with events (from using `specify`, `plan`, `tasks`, etc.)
  6. **Time estimate**: 5 minutes
- **Files**: `docs/tutorials/server-connection.md`

### Subtask T035 – Write Step 1: Configure server URL

- **Purpose**: First concrete step — tell the CLI where the server is.
- **Steps**:
  1. Add `## Step 1: Configure the Server URL` section
  2. Document:
     ```bash
     # Create or edit the config file
     mkdir -p ~/.spec-kitty
     ```
  3. Show config file content:
     ```toml
     # ~/.spec-kitty/config.toml
     [server]
     url = "https://your-server.example.com"
     ```
  4. Replace `your-server.example.com` with your actual server URL
  5. Verify:
     ```bash
     cat ~/.spec-kitty/config.toml
     ```
  6. **Expected state**: Config file exists with the server URL
- **Files**: `docs/tutorials/server-connection.md`

### Subtask T036 – Write Step 2: Authenticate

- **Purpose**: Log in from the CLI.
- **Steps**:
  1. Add `## Step 2: Log In` section
  2. Document:
     ```bash
     spec-kitty auth login
     ```
  3. Show the interactive prompts:
     ```
     Username: your-email@example.com
     Password: ********
     Authenticating with https://your-server.example.com...
     ✅ Login successful!
        Logged in as: your-email@example.com
     ```
  4. **If something goes wrong**: Brief inline troubleshooting
     - "Invalid username or password" → Double-check credentials
     - "Cannot reach server" → Check URL in config.toml, check network
  5. **Expected state**: Authenticated session, tokens stored
- **Files**: `docs/tutorials/server-connection.md`

### Subtask T037 – Write Step 3: Verify connection

- **Purpose**: Confirm everything is working.
- **Steps**:
  1. Add `## Step 3: Verify Your Connection` section
  2. Check auth status:
     ```bash
     spec-kitty auth status
     ```
     Expected:
     ```
     ✅ Authenticated
        Username: your-email@example.com
        Server:   https://your-server.example.com
        Access token: valid (23h remaining)
        Refresh token: valid (6d remaining)
     ```
  3. Check server connectivity:
     ```bash
     spec-kitty sync status --check
     ```
     Expected:
     ```
     Server URL   https://your-server.example.com
     Config File  /Users/you/.spec-kitty/config.toml
     Connection   Reachable (auth required)
     ```
  4. Explain: "Reachable" means the server is online. The "auth required" message is expected — it confirms the server is responding.
  5. **Expected state**: Auth valid, server reachable
- **Files**: `docs/tutorials/server-connection.md`

### Subtask T038 – Write Step 4: Run first sync

- **Purpose**: Push events to the server for the first time.
- **Steps**:
  1. Add `## Step 4: Sync Your Events` section
  2. Document:
     ```bash
     spec-kitty sync now
     ```
  3. Show expected output:
     ```
     Syncing with https://your-server.example.com...
     ↑ Pushed 48 events (1 batch)
     ↓ Pulled 0 new events
     ✅ Sync complete
     ```
  4. Explain: "The number of pushed events depends on how much work you've done locally. All your project, feature, and work package events are now on the server."
  5. Optional: "Open your server's dashboard in a browser to see your synced data: `https://your-server.example.com/a/<team>/dashboards/`"
  6. **Expected state**: Events synced, visible in dashboard
- **Files**: `docs/tutorials/server-connection.md`

### Subtask T039 – Write next steps section

- **Purpose**: Guide the reader to deeper documentation.
- **Steps**:
  1. Add `## Next Steps` section
  2. Content:
     - **Explore the dashboard**: [How to Use the SaaS Dashboard](../how-to/use-saas-dashboard.md) — See your projects, kanban board, and activity feed
     - **Understand sync**: [Sync Architecture](../explanations/sync-architecture.md) — Learn how events flow between CLI and server
     - **Ongoing sync**: [How to Sync with a Server](../how-to/sync-to-server.md) — Detailed guide for daily sync workflows
     - **Manage credentials**: [How to Authenticate](../how-to/authenticate.md) — Login, logout, token management
  3. Add `## See Also` section:
     - [CLI Commands: auth](../reference/cli-commands.md#spec-kitty-auth)
     - [CLI Commands: sync](../reference/cli-commands.md#spec-kitty-sync)
     - [Configuration Reference](../reference/configuration.md#server-configuration-2x)
- **Files**: `docs/tutorials/server-connection.md`

## Risks & Mitigations

- **Risk**: CLI commands may have different output when restored → Keep output representative
- **Risk**: Tutorial becomes outdated → Link to reference/how-to for current details

## Review Guidance

- **MOST IMPORTANT**: Can a new user complete this tutorial without consulting any other docs?
- Verify each step has a clear "expected state" so the reader knows they succeeded
- Check that inline troubleshooting covers the most common failures at each step
- Confirm the tutorial flows naturally from one step to the next
- Verify all "See Also" and "Next Steps" links use correct relative paths

## Activity Log

- 2026-02-05T15:08:07Z – system – lane=planned – Prompt created.
