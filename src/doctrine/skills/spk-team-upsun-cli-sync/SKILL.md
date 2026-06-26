---
name: spk-team-upsun-cli-sync
description: "Point a local Spec Kitty CLI at Spec Kitty SaaS on Upsun (main or preview): set sync vars via use-upsun-env.sh, authenticate against Upsun Teamspace, check readiness, or drain local events."
---

# spk-team-upsun-cli-sync

Wire a local `spec-kitty` CLI to Spec Kitty SaaS on Upsun. Prefer the SaaS
repo's `scripts/use-upsun-env.sh` over hand-written env exports: it resolves the
current primary Upsun URL and keeps the variable contract consistent.

## Canonical References

In the `spec-kitty-saas` checkout, consult only as needed:
`docs/runbooks/upsun-cli-auth-and-sync.md` (local CLI auth and drain flow),
`docs/runbooks/upsun-preview-environments.md` (branch-preview env lookup),
`docs/env-var-contract.md` (env var contract), and `scripts/use-upsun-env.sh`
(executable env setup). Constants: Upsun project `67rt36f456a5m`, app
`teamspace`, main env `main`, main URL fallback
`https://main-bvxea6i-67rt36f456a5m.us-3.platformsh.site`.

## Setup Flow

Start in `spec-kitty-saas`. For main use `eval "$(scripts/use-upsun-env.sh
main)"`; for a preview use `eval "$(scripts/use-upsun-env.sh <branch-env>)"`.
With no argument the script uses the current git branch. It exports
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_SAAS_URL=<upsun-primary-url>`, and
`SPEC_KITTY_HOME=$HOME/.spec-kitty-upsun`. Then wire the local CLI from the
sibling `spec-kitty` checkout:

```bash
cd ../spec-kitty
spec-kitty auth login --force
spec-kitty auth whoami
spec-kitty auth doctor --server
spec-kitty sync server "$SPEC_KITTY_SAAS_URL"
spec-kitty sync opt-in
spec-kitty sync status --check
```

Local testing rule: any command path touching hosted auth, tracker, or sync
must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The env script sets it; preserve
it when composing commands manually.

## Verifying State Isolation

To confirm that a dedicated `SPEC_KITTY_HOME` actually captures the local state
(and that your everyday `~/.spec-kitty` is untouched), run the isolation check:

```bash
tmp_home="$(mktemp -d)"
tmp_skh="$(mktemp -d)"

HOME="$tmp_home" \
SPEC_KITTY_HOME="$tmp_skh" \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
spec-kitty sync server https://example.invalid

echo "--- default home (must be EMPTY of config) ---"
find "$tmp_home" -maxdepth 3 -type f | sort
echo "--- SPEC_KITTY_HOME (must contain config.toml) ---"
find "$tmp_skh" -maxdepth 3 -type f | sort
```

Expected: `config.toml` appears under `$SPEC_KITTY_HOME`; `$HOME/.spec-kitty/config.toml`
does **not** exist. `spec-kitty state doctor` reports the same global-sync root.

## Verification

Before treating an environment as healthy:

```bash
curl -sS "$SPEC_KITTY_SAAS_URL/health/"
curl -sS "$SPEC_KITTY_SAAS_URL/health/ready/"
upsun environment:info -p 67rt36f456a5m -e <env-name> --no-interaction
```

If using a macOS Keychain-stored Upsun API token for CLI reads, do not print it
— pass it inline: `UPSUN_CLI_TOKEN="$(security find-generic-password -a "$USER"
-s upsun-cli-token -w)" upsun environment:info -p 67rt36f456a5m -e <env> ...`.

## Draining Events

Only drain when the user explicitly wants the local event queue sent to the
selected SaaS target: `spec-kitty sync now --report sync-report.json`. Current
behavior:

- Local event rows are deleted after server `success`, `duplicate`, or
  `failed_permanent` outcomes.
- Normal `sync now` is therefore not replay-safe across multiple transient
  Upsun environments.
- Event queue storage resolves under the selected state root: scoped
  authenticated queues at `<root>/queues/queue-<hash>.db` with the legacy
  fallback `<root>/queue.db`. With `SPEC_KITTY_HOME` set, `<root>` is that
  directory; unset on POSIX it is `~/.spec-kitty`.
- `SPEC_KITTY_HOME` now isolates **all** local Spec Kitty state — sync config,
  hosted-auth session and refresh lock, the event queues and active queue scope,
  the Lamport clock, the sync daemon (state/log/lock), and tracker
  credentials/cache — not just runtime/Mission assets. Pointing it at a
  dedicated directory gives the Upsun target a fully isolated session with zero
  cross-contamination from your everyday `~/.spec-kitty` dev state (fixes
  [#2171](https://github.com/Priivacy-ai/spec-kitty/issues/2171)). On Windows the
  state resolves onto the platformdirs app-data base when the variable is unset.
  No automatic migration of existing `~/.spec-kitty` data is performed.

## Server Drain Inspection

Operator checks against the target environment:

```bash
upsun ssh -p 67rt36f456a5m -e <env-name> -A teamspace -- \
  '.venv/bin/python manage.py reconcile_sync_drain --json'
```

Add `--drain` to force pending server-side durable drain rows. Interpret results
as server-side materialization state: an empty local queue means the CLI has no
queued rows for that scope; it does not prove SaaS projections finished.
