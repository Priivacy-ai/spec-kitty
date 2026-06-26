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
  `failed_permanent` outcomes, so `sync now` is not replay-safe across multiple
  transient Upsun environments.
- Queue storage: `~/.spec-kitty/queues/queue-<hash>.db` for scoped queues, with
  legacy fallback `~/.spec-kitty/queue.db`.
- `SPEC_KITTY_HOME` isolates auth/state but may not isolate the event queue;
  verify before relying on it.

## Server Drain Inspection

Operator checks against the target environment:

```bash
upsun ssh -p 67rt36f456a5m -e <env-name> -A teamspace -- \
  '.venv/bin/python manage.py reconcile_sync_drain --json'
```

Add `--drain` to force pending server-side durable drain rows. Interpret results
as server-side materialization state: an empty local queue means the CLI has no
queued rows for that scope; it does not prove SaaS projections finished.
