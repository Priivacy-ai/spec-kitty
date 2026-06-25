---
name: spk-team-upsun-cli-sync
description: "Point a local Spec Kitty CLI at Spec Kitty SaaS on Upsun for main or branch-preview environments. Use when the user asks how to target Upsun from the local CLI, set Spec Kitty SaaS sync variables, use scripts/use-upsun-env.sh, authenticate against Upsun-hosted Teamspace, inspect sync readiness, or drain local events to an Upsun environment."
---

# spk-team-upsun-cli-sync

Use this skill to wire a local `spec-kitty` CLI to Spec Kitty SaaS running on
Upsun. Prefer the SaaS repo's `scripts/use-upsun-env.sh` over hand-written env
exports because it resolves the current primary Upsun URL and keeps the variable
contract consistent with the runbooks.

## Canonical References

In the `spec-kitty-saas` checkout, consult these only as needed:

- `docs/runbooks/upsun-cli-auth-and-sync.md` for local CLI auth and drain flow.
- `docs/runbooks/upsun-preview-environments.md` for branch-preview env lookup.
- `docs/env-var-contract.md` for the local/operator env var contract.
- `scripts/use-upsun-env.sh` for the executable env-var setup.

Constants:

- Upsun project: `67rt36f456a5m`
- Upsun app: `teamspace`
- Main environment: `main`
- Main URL if discovery is unavailable:
  `https://main-bvxea6i-67rt36f456a5m.us-3.platformsh.site`

## Setup Flow

Start in the `spec-kitty-saas` checkout.

For main:

```bash
eval "$(scripts/use-upsun-env.sh main)"
```

For a branch-preview environment:

```bash
eval "$(scripts/use-upsun-env.sh <branch-env-name>)"
```

With no argument, the script uses the current git branch as the Upsun
environment name.

The script exports:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1
SPEC_KITTY_SAAS_URL=<upsun-primary-url>
SPEC_KITTY_HOME=$HOME/.spec-kitty-upsun
```

Then run the local CLI wiring from the sibling `spec-kitty` checkout:

```bash
cd ../spec-kitty
spec-kitty auth login --force
spec-kitty auth whoami
spec-kitty auth doctor --server
spec-kitty sync server "$SPEC_KITTY_SAAS_URL"
spec-kitty sync opt-in
spec-kitty sync status --check
```

This machine's local testing rule: any command path touching hosted auth,
tracker, or sync behavior must run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. The
env script sets it; preserve it if composing commands manually.

## Verification

Before treating an environment as healthy:

```bash
curl -sS "$SPEC_KITTY_SAAS_URL/health/"
curl -sS "$SPEC_KITTY_SAAS_URL/health/ready/"
upsun environment:info -p 67rt36f456a5m -e <env-name> --no-interaction
```

If using Robert's macOS Keychain-stored Upsun API token for CLI reads, do not
print the token:

```bash
UPSUN_CLI_TOKEN="$(security find-generic-password -a "$USER" -s upsun-cli-token -w)" \
  upsun environment:info -p 67rt36f456a5m -e <env-name> --no-interaction
```

## Draining Events

Only drain when the user explicitly wants the current local event queue sent to
the selected SaaS target:

```bash
spec-kitty sync now --report sync-report.json
```

Important current behavior:

- Local event rows are deleted after server `success`, `duplicate`, or
  `failed_permanent` outcomes.
- Normal `sync now` is therefore not replay-safe across multiple transient
  Upsun environments.
- Current event queue storage is under `~/.spec-kitty/queues/queue-<hash>.db`
  for authenticated scoped queues, with legacy fallback `~/.spec-kitty/queue.db`.
- In the current queue implementation, `SPEC_KITTY_HOME` isolates auth/state but
  may not isolate the event queue itself; verify before relying on it.

## Server Drain Inspection

For operator checks against the target environment:

```bash
upsun ssh -p 67rt36f456a5m -e <env-name> -A teamspace -- \
  '.venv/bin/python manage.py reconcile_sync_drain --json'
```

To force pending server-side durable drain rows:

```bash
upsun ssh -p 67rt36f456a5m -e <env-name> -A teamspace -- \
  '.venv/bin/python manage.py reconcile_sync_drain --drain --json'
```

Interpret drain results as server-side materialization state. A local queue
being empty means the CLI no longer has queued rows for that scope; it does not
by itself prove SaaS projections have finished.
