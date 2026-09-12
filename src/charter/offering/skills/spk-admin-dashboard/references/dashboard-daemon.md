# Dashboard Daemon

Spec Kitty dashboard runs as a local daemon for the current project.

## Metadata File

Dashboard metadata lives at:

```text
.kittify/.dashboard
```

The file has two required lines and two optional lines:

1. URL
2. Port
3. Token (optional)
4. PID (optional)

If the file exists, use the dashboard lifecycle command to validate health,
project identity, token, and daemon state before showing the URL.

## Commands

```bash
spec-kitty dashboard --open
spec-kitty dashboard --json
spec-kitty dashboard --kill
```

- `--open` starts or locates the daemon and opens the browser.
- `--json` prints mission registry JSON and does not start the server.
- `--kill` stops the project daemon and clears `.kittify/.dashboard`.

If metadata is stale or absent, run `spec-kitty dashboard --open`.
