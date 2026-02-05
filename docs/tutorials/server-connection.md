# Connect to a Spec Kitty Server

**Divio type**: Tutorial

In this tutorial, you'll connect your spec-kitty CLI to a team server. By the end, you'll have authenticated, verified your connection, and pushed your first sync.

**Time**: ~5 minutes
**Prerequisites**: spec-kitty 2.x installed, a server URL from your team admin, your server credentials

**What you'll learn**:

- How to configure the server URL
- How to authenticate from the CLI
- How to verify your connection
- How to sync events with the server


## Step 1: Configure the Server URL

First, tell the CLI where your team's server is. Create or edit the spec-kitty configuration file:

```bash
mkdir -p ~/.spec-kitty
```

Open `~/.spec-kitty/config.toml` in your editor and add the server URL:

```toml
# ~/.spec-kitty/config.toml
[server]
url = "https://your-server.example.com"
```

Replace `your-server.example.com` with the actual URL provided by your team admin.

Verify the file was saved correctly:

```bash
cat ~/.spec-kitty/config.toml
```

You should see the `[server]` section with your URL.


## Step 2: Log In

Authenticate with the server using the `auth login` command:

```bash
spec-kitty auth login
```

Follow the interactive prompts:

```
Username: your-email@example.com
Password: ********
Authenticating with https://your-server.example.com...
✅ Login successful!
   Logged in as: your-email@example.com
```

JWT tokens are now stored locally in `~/.spec-kitty/credentials.json`.

> **Something went wrong?**
>
> - **"Invalid username or password"** -- Double-check your credentials and try again.
> - **"Cannot reach server"** -- Verify the URL in `~/.spec-kitty/config.toml` and check your network connection.


## Step 3: Verify Your Connection

Confirm your authentication is active:

```bash
spec-kitty auth status
```

Expected output:

```
✅ Authenticated
   Username: your-email@example.com
   Server:   https://your-server.example.com
   Access token: valid (23h remaining)
   Refresh token: valid (6d remaining)
```

Now test that the server is reachable:

```bash
spec-kitty sync status --check
```

Expected output:

```
Spec Kitty Sync Status

Server URL   https://your-server.example.com
Config File  /Users/you/.spec-kitty/config.toml
Connection   Reachable (auth required)
```

"Reachable" confirms the server is online and responding. The "auth required" message is expected -- it means the server correctly requires authentication for API access.


## Step 4: Sync Your Events

Push your local events to the server for the first time:

```bash
spec-kitty sync now
```

Expected output:

```
Syncing with https://your-server.example.com...
↑ Pushed 48 events (1 batch)
↓ Pulled 0 new events
✅ Sync complete
```

The number of pushed events depends on how much work you've done locally. All your project, feature, and work package events are now on the server.

> **Tip**: Open your server's dashboard in a browser to see your synced data:
> `https://your-server.example.com/a/<team>/dashboards/`


## Next Steps

You're connected and syncing. Here's where to go from here:

- **Explore the dashboard**: [How to Use the SaaS Dashboard](../how-to/use-saas-dashboard.md) -- See your projects, kanban board, and activity feed
- **Understand sync**: [Sync Architecture](../explanation/sync-architecture.md) -- Learn how events flow between CLI and server
- **Ongoing sync**: [How to Sync with a Server](../how-to/sync-to-server.md) -- Detailed guide for daily sync workflows
- **Manage credentials**: [How to Authenticate](../how-to/authenticate.md) -- Login, logout, token management

## See Also

- [CLI Commands: `spec-kitty auth`](../reference/cli-commands.md#spec-kitty-auth) -- Detailed flag reference
- [CLI Commands: `spec-kitty sync`](../reference/cli-commands.md#spec-kitty-sync) -- Detailed command reference
- [Configuration Reference](../reference/configuration.md#server-configuration-2x) -- Config file formats
