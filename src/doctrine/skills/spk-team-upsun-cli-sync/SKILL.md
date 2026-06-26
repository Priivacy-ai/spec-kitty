---
name: spk-team-upsun-cli-sync
description: "Point a local Spec Kitty CLI at Spec Kitty SaaS on Upsun (main or preview): set sync vars via use-upsun-env.sh, authenticate against Upsun Teamspace, check readiness, or drain local events."
---

# spk-team-upsun-cli-sync

Wire a local `spec-kitty` CLI to Spec Kitty SaaS on Upsun. Prefer the SaaS
repo's `scripts/use-upsun-env.sh` over hand-written env exports: it resolves the
primary Upsun URL and keeps the variable contract consistent.

## Canonical References

In the `spec-kitty-saas` checkout, consult as needed:
`docs/runbooks/upsun-cli-auth-and-sync.md` (auth + drain),
`docs/runbooks/upsun-preview-environments.md` (preview env lookup),
`docs/env-var-contract.md`, and `scripts/use-upsun-env.sh` (env setup).
Constants: project `67rt36f456a5m`, app `teamspace`, main env `main`, main URL
fallback `https://main-bvxea6i-67rt36f456a5m.us-3.platformsh.site`.

## Setup Flow

Start in `spec-kitty-saas`. Run `eval "$(scripts/use-upsun-env.sh main)"` (or
`<branch-env>` for a preview; no argument uses the current git branch). It
exports `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_SAAS_URL=<upsun-primary-url>`,
and `SPEC_KITTY_HOME=$HOME/.spec-kitty-upsun`. Then wire the local CLI from the
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

Local testing rule: any command touching hosted auth, tracker, or sync must run
with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The env script sets it; preserve it when
composing commands manually.

## Verification

Health-check before trusting an environment:
```bash
curl -sS "$SPEC_KITTY_SAAS_URL/health/"
curl -sS "$SPEC_KITTY_SAAS_URL/health/ready/"
upsun environment:info -p 67rt36f456a5m -e <env-name> --no-interaction
```

Pass a Keychain-stored Upsun token inline (do not print it):
`UPSUN_CLI_TOKEN="$(security find-generic-password -a "$USER" -s upsun-cli-token -w)"`.

## Draining Events

Drain only when the local event queue must be sent to the target
(`spec-kitty sync now --report sync-report.json`). Behavior:

- Event rows are deleted on server `success`, `duplicate`, or `failed_permanent`,
  so `sync now` is not replay-safe across transient Upsun environments.
- Event queues resolve under the state root: scoped queues at
  `<root>/queues/queue-<hash>.db`, legacy fallback `<root>/queue.db`. `<root>` is
  `SPEC_KITTY_HOME` when set, else `~/.spec-kitty` on POSIX.
- `SPEC_KITTY_HOME` now isolates **all** local state — sync config, hosted-auth
  session/refresh-lock, event queues and active scope, the Lamport clock, the
  sync daemon, and tracker credentials/cache — not just runtime assets, giving
  the Upsun target a fully isolated session (fixes
  [#2171](https://github.com/Priivacy-ai/spec-kitty/issues/2171)). When unset on
  Windows it resolves onto the platformdirs app-data base; existing
  `~/.spec-kitty` data is not auto-migrated. Verify by running a config-writing
  command under temp `HOME` + `SPEC_KITTY_HOME` — `config.toml` must appear only
  under `$SPEC_KITTY_HOME`, never `$HOME/.spec-kitty`.

## Server Drain Inspection

```bash
upsun ssh -p 67rt36f456a5m -e <env-name> -A teamspace -- \
  '.venv/bin/python manage.py reconcile_sync_drain --json'
```

Add `--drain` to force pending server-side durable drain rows. An empty local
queue means the CLI has no queued rows for that scope — it does not prove SaaS
projections finished.
