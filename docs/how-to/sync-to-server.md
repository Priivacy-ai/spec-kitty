# How to Sync with a Spec Kitty Server

Spec Kitty stores events locally and synchronizes them with your team's server. This page covers how to trigger and monitor that synchronization -- pushing your local events to the server and pulling down events from your teammates.

> **Not what you're looking for?**
>
> - To sync your workspace with upstream worktree changes (local), see [Sync Workspaces](sync-workspaces.md).
> - This page covers pushing/pulling events to/from a remote spec-kitty server.

---

## Prerequisites

- An authenticated session -- run `spec-kitty auth status` and confirm it shows a valid session
- A server URL configured in `~/.spec-kitty/config.toml`

If you haven't authenticated yet, run `spec-kitty auth login` first.

---

## Push and Pull Events

To synchronize your local events with the server, run:

```bash
spec-kitty sync now
```

This command:

1. Sends all locally queued events to the server in batches
2. Pulls new events from the server
3. Drains the offline queue

Representative output:

```
Syncing with https://your-server.example.com...
 Pushed 12 events (2 batches)
 Pulled 5 new events
 Sync complete
```

> **Note**: The output format above is representative and may differ from the actual implementation. Events are sent in batches of up to 1000, gzip-compressed.

### Verbose Output

Add `--verbose` (or `-v`) for detailed per-event output:

```bash
spec-kitty sync now --verbose
```

### Dry Run

Preview what would be synced without actually pushing or pulling:

```bash
spec-kitty sync now --dry-run
```

You can also use the short flag `-n`:

```bash
spec-kitty sync now -n
```

---

## Check Sync Status

To see your sync configuration and connection state:

```bash
spec-kitty sync status
```

Output:

```
Spec Kitty Sync Status

Server URL   https://your-server.example.com
Config File  /Users/you/.spec-kitty/config.toml
Connection   Not checked (use --check to test)
```

### Test Connectivity

Use the `--check` (or `-c`) flag to test the actual connection to the server:

```bash
spec-kitty sync status --check
```

Output with `--check`:

```
Spec Kitty Sync Status

Server URL   https://your-server.example.com
Config File  /Users/you/.spec-kitty/config.toml
Connection   Reachable (auth required)
             Server online (access forbidden)
```

### Connection States

When using `--check`, the connection field will show one of:

| State | Meaning |
| --- | --- |
| **Connected** | Successfully reached the server with valid authentication |
| **Reachable** | Server is online but authentication is required or has expired |
| **Unreachable** | Connection timed out or was refused |
| **Error** | Connection test failed for an unexpected reason |

---

## Working Offline

Spec Kitty is designed to work seamlessly offline:

- When you work without a server connection, events are queued locally in SQLite
- Your work is never lost -- events accumulate in the offline queue
- When you're back online, run `spec-kitty sync now` to push everything
- The Lamport clock ordering ensures events merge correctly even after a long offline period

If a WebSocket connection is configured, the queue will also drain automatically when connectivity returns -- no manual sync needed.

> **Tip**: You can check how many events are queued with `spec-kitty sync status`.

---

## Troubleshooting

### "Cannot reach server"

- Verify your network connection
- Check the server URL in `~/.spec-kitty/config.toml`
- Run `spec-kitty sync status --check` to diagnose the connection state

### "Authentication expired"

Re-authenticate with the server:

```bash
spec-kitty auth login
```

Then retry the sync:

```bash
spec-kitty sync now
```

### "Partial sync"

Some events may fail during sync. The server returns per-event status, so successfully synced events are acknowledged while failed events remain in the queue. Run `spec-kitty sync now` again after resolving any issues.

### "Queue not draining"

If events remain in the queue after running `sync now`:

1. Confirm your authentication is valid: `spec-kitty auth status`
2. Confirm the server is reachable: `spec-kitty sync status --check`
3. Check for event format errors in verbose output: `spec-kitty sync now --verbose`

> **Note**: `spec-kitty sync now` is idempotent -- it is safe to run multiple times.

---

## See Also

- [Sync Workspaces](sync-workspaces.md) -- Local worktree sync (different from server sync)
- [CLI Commands: `spec-kitty sync`](../reference/cli-commands.md#spec-kitty-sync) -- Detailed command reference
- [Authentication How-To](authenticate.md) -- Setting up credentials
- [Sync Architecture](../explanation/sync-architecture.md) -- How the sync system works
