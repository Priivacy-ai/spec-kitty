---
title: Internal Hosted-Readiness Mode (Pre-Launch)
description: 'How to internal hosted-readiness mode (pre-launch) with Spec Kitty 3.2: Internal Hosted-Readiness Mode (Pre-Launch).'
doc_status: active
updated: '2026-06-03'
type: how-to
related:
- docs/guides/upgrade-cli.md
audience: internal / pre-launch operators
---
# Internal Hosted-Readiness Mode (Pre-Launch)

> **Audience:** internal contributors and dev operators who are dogfooding
> the hidden hosted-readiness path. This page is **not** for end users.
> The public Spec Kitty experience remains local-first; see the
> [README](https://github.com/Priivacy-ai/spec-kitty/blob/main/README.md) for the current default workflow.

## When this page applies

Read on if all of the following hold:

- You are running a build of `spec-kitty-cli` that includes the SaaS
  rollout gate (`src/specify_cli/saas/rollout.py`).
- You want the CLI to surface Teamspace-aware readiness output —
  hosted auth status, sync compatibility, tracker reachability — from
  any `spec-kitty` command.
- You accept that everything below is **pre-launch** and may change
  without a deprecation window.

If none of that applies, you want the local-first quick start, not this
page.

## How the hidden mode works (one-paragraph mental model)

A single environment variable, `SPEC_KITTY_ENABLE_SAAS_SYNC`, gates every
hosted code path. With the variable unset (or any non-truthy value), the
central CLI startup readiness coordinator is a no-op: no Teamspace-labeled
output, no hosted auth probe, no tracker calls. With the variable set
to a truthy value (`1`, `true`, `yes`, `on`, case-insensitive), the
coordinator wakes up and the hosted readiness states become observable.
The byte-stable disabled-state message and the truthy-value contract are
defined in [`src/specify_cli/saas/rollout.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/specify_cli/saas/rollout.py)
and asserted by tests; do not paraphrase that message in your own
tooling.

## Enable hosted readiness locally

Run this in the shell where you want hosted output:

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
spec-kitty auth login
```

`spec-kitty auth login` is the canonical entry point for the hosted
auth flow. It opens the browser-based login and persists credentials
to the local keyring. After it succeeds, every subsequent `spec-kitty`
command in the same shell session benefits from the hosted readiness
output.

To disable, unset the variable in the shell:

```bash
unset SPEC_KITTY_ENABLE_SAAS_SYNC
```

The coordinator goes back to no-op on the next command.

## Point at a dev or staging hosted environment

The internal dev / staging environments live at non-default URLs.
`SPEC_KITTY_SAAS_URL` overrides the base URL the auth, tracker, and
sync clients dial.

```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
export SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev
spec-kitty auth login
```

> **Important framing.** `SPEC_KITTY_SAAS_URL` is an internal **dev /
> staging override**. It is not user behavior. End users — today and
> at launch — never set it. If you are documenting end-user behavior,
> reference the [launch-readiness-future](../architecture/launch-readiness-future.md)
> doc, which describes the user-facing default URL.

## Readiness states the coordinator surfaces

With `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, the coordinator (and its
companion auth probe) classify the session into one of the buckets
below. Sister missions are widening this enum; the table captures the
operator-visible behavior, not the enum literal.

| Session state | What the operator sees | Remediation |
|---|---|---|
| Hosted mode disabled (variable unset / falsy) | No Teamspace-labeled output. Coordinator is a no-op. The stable disabled-message string is emitted only by commands that explicitly ask for it (e.g., `spec-kitty sync now` without opt-in). | None — this is the local-first default. |
| Hosted mode enabled, authenticated | Hosted output flows normally. | None. |
| Hosted mode enabled, logged out on a connected Teamspace | Interactive: a Rich panel offers `[L]ogin / [S]kip / [Q]uit`. Non-interactive: a stable stderr line plus exit code `4`. See [Recovery: Logged out on a connected teamspace](../operations/logged-out-teamspace.md). | `spec-kitty auth login` |
| Hosted mode enabled, tracker unreachable | The relevant sync / tracker command surfaces the failure with a doctor pointer. | `spec-kitty sync doctor` |
| Hosted mode enabled, CLI upgrade required | The startup-readiness path nag-renders the upgrade guidance (already gated by the Wave 1 suppression contract). | `spec-kitty upgrade --cli` |

## Diagnose hosted readiness

```bash
spec-kitty sync doctor
```

`sync doctor` is the most informative single command in the
hosted-mode-enabled path. It prints which sub-systems are reachable,
what credentials are available, and which command would resolve each
broken state. When the readiness coordinator fires the
"logged out on a connected Teamspace" path, `sync doctor` will also
offer the interactive recovery prompt.

## Suppression contract

The readiness coordinator honors the **Wave 1 suppression contract**
byte-for-byte across three buckets:

| Output policy | When it applies |
|---|---|
| `INTERACTIVE` | `stdin` is a TTY and `SPEC_KITTY_NON_INTERACTIVE` is not set. |
| `NON_INTERACTIVE` | `stdin` is not a TTY, or `SPEC_KITTY_NON_INTERACTIVE=1`. |
| `MACHINE_OUTPUT` | Commands that emit JSON or other machine surfaces; suppression is the default. |

The canonical source for the policy precedence is the data-model
section of the mission spec for the readiness coordinator
(`kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/data-model.md`).
The recovery doc covers the operator-visible behavior of each bucket;
see [Recovery: Logged out on a connected teamspace](../operations/logged-out-teamspace.md).

## Verify locally end-to-end

A minimal "did it really wire up?" recipe:

```bash
# 1. Confirm the variable is set and truthy in this shell.
echo "${SPEC_KITTY_ENABLE_SAAS_SYNC}"

# 2. Confirm the CLI sees hosted mode as enabled.
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty sync doctor

# 3. Confirm the logged-out recovery surfaces in non-interactive mode.
#    Expect exit code 4 and the structured stderr line documented in
#    docs/operations/logged-out-teamspace.md.
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NON_INTERACTIVE=1 \
  spec-kitty sync now < /dev/null
echo "exit=$?"
```

If step 2 prints local-only output, the variable did not propagate to
the CLI's subprocess. Re-export and retry.

## Related

- [Recovery: Logged out on a connected teamspace](../operations/logged-out-teamspace.md)
- [Environment variables reference](../api/environment-variables.md)
  — full entries for `SPEC_KITTY_ENABLE_SAAS_SYNC` and
  `SPEC_KITTY_SAAS_URL`.
- [Upgrade the Spec Kitty CLI](upgrade-cli.md) — for the
  `spec-kitty upgrade --cli` probe shown in the upgrade-required
  scenario above.

## Not for end users

If you are documenting what end users will see, **stop reading this
page** and switch to
[Launch-Readiness Behavior (Coming Soon)](../architecture/launch-readiness-future.md).
That doc owns the at-launch user-facing semantics; this doc owns the
pre-launch internal operator experience.
