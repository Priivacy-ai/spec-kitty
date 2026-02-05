# How to Authenticate with a Spec Kitty Server

Connect your spec-kitty CLI to a team server for syncing project data.

## Prerequisites

- **spec-kitty 2.x** installed ([Installation Guide](install-spec-kitty.md))
- **Server URL** provided by your team admin
- **Valid credentials** (username and password for the server)
- **Server URL configured** in `~/.spec-kitty/config.toml` under the `[server]` table ([Configuration Reference](../reference/configuration.md))

---

## Log In

### Interactive login

Run the login command and follow the prompts:

```bash
spec-kitty auth login
```

Expected output:

```
Username: user@example.com
Password: ********
Authenticating with https://your-server.example.com...
✅ Login successful!
   Logged in as: user@example.com
```

On success, JWT tokens are stored in `~/.spec-kitty/credentials.json`.

### Non-interactive login (scripts and CI)

Pass credentials directly via flags to skip the interactive prompts:

```bash
spec-kitty auth login --username user@example.com --password "$PASSWORD"
```

This is useful for CI pipelines and automated scripts where interactive input is not available.

### Re-authentication

If your tokens are corrupted or you need to switch accounts, use `--force` to discard
existing credentials and authenticate fresh:

```bash
spec-kitty auth login --force
```

Without `--force`, the CLI exits early if you are already authenticated.

---

## Check Authentication Status

Verify your current authentication state at any time:

```bash
spec-kitty auth status
```

**Authenticated output:**

```
✅ Authenticated
   Username: user@example.com
   Server:   https://your-server.example.com
   Access token: valid (23h remaining)
   Refresh token: valid (6d remaining)
```

Access tokens refresh automatically in the background. When the **refresh token** expires,
the CLI can no longer obtain new access tokens and you will need to run `spec-kitty auth login`
again.

**Not-authenticated output:**

```
❌ Not authenticated
   Run 'spec-kitty auth login' to authenticate.
```

---

## Log Out

Clear your stored credentials:

```bash
spec-kitty auth logout
```

Expected output:

```
✅ Logged out successfully.
   Cleared credentials for: user@example.com
```

Logging out removes all stored tokens from `~/.spec-kitty/credentials.json`. You will need
to log in again before using any sync features.

---

## Troubleshooting

### "Invalid username or password"

Your credentials were rejected by the server.

**Fix:** Double-check your username and password, then try again:

```bash
spec-kitty auth login
```

### "Cannot reach server"

The CLI cannot connect to the configured server URL.

**Fix:** Check your network connection and verify the server URL in your configuration file:

```bash
cat ~/.spec-kitty/config.toml
```

Confirm the `[server]` section contains the correct URL. If the URL is wrong, update it and
retry.

### "Server temporarily unavailable"

The server is reachable but returned an error indicating it cannot handle requests right now.

**Fix:** Wait a few minutes and try again. If the problem persists, contact your team admin.

### "Session expired"

Your refresh token has expired and the CLI can no longer obtain new access tokens.

**Fix:** Log in again to obtain fresh tokens:

```bash
spec-kitty auth login
```

### "Cannot access credentials file"

The CLI cannot read or write the credentials file due to file system permissions.

**Fix:** Check and correct the file permissions:

```bash
chmod 600 ~/.spec-kitty/credentials.json
```

Ensure the `~/.spec-kitty/` directory exists and is owned by your user.

---

## See Also

- [CLI Commands: `spec-kitty auth`](../reference/cli-commands.md#spec-kitty-auth) -- Detailed flag reference
- [Configuration: Server & Credentials](../reference/configuration.md#server-configuration-2x) -- Config file formats
- [Server Connection Tutorial](../tutorials/server-connection.md) -- End-to-end setup guide
- [Sync Architecture](../explanation/sync-architecture.md) -- How authentication fits into sync
