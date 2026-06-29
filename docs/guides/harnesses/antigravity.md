---
title: Use Spec Kitty in Google Antigravity
description: Configure the Google Antigravity harness for Spec Kitty 3.2 workflows, partial-tier verification, and generated workflow files.
doc_status: active
updated: '2026-06-06'
related:
- docs/guides/install-spec-kitty.md
---
# Use Spec Kitty in Google Antigravity

> **Tier:** **partial** — workflow surface exists in Spec Kitty, but current
> Antigravity CLI workflow loading has not been smoke-tested end-to-end.
> **Citation (accessed 2026-06-03):** <https://www.antigravity.google/docs/rules-workflows>

## Prerequisites

- **Spec Kitty CLI installed.** See [Install Spec Kitty](../install-spec-kitty.md).
- **Project initialized for this harness:**
  ```bash
  spec-kitty init --ai antigravity
  ```
- **Google Antigravity installed and configured.** Follow the official
  [Antigravity documentation](https://www.antigravity.google/docs/overview).

## Verification status

Antigravity remains partial in Spec Kitty because live CLI verification was not
available on the 2026-06-03 audit machine. The local `agent` binary resolved to
Cursor Agent, not Google Antigravity, so the audit could not prove the current
Antigravity CLI command surface, global/workspace workflow roots, or invocation
syntax.

Do not promote Antigravity to `supported` until a maintainer with the current
Antigravity CLI installed records:

- `antigravity --help` or equivalent CLI output.
- The exact workflow search roots.
- Successful launch of at least one `spec-kitty.*` workflow from a real
  Antigravity session.

## Where Spec Kitty installs files

Per the [supported-harnesses matrix](../../api/supported-harnesses.md),
Spec Kitty currently writes Antigravity workflow files under:

- **Directory:** `.agent/workflows/`
- **Files:** the `spec-kitty.*` workflow set.

If current Antigravity versions require `.agents/workflows/` or another path,
update the installer and this page together with smoke-test evidence.

## Canonical invocation

Inside Antigravity, workflow invocation is expected to follow the host workflow
slash-command convention:

```text
/spec-kitty.specify "<one-line mission description>"
/spec-kitty.plan
/spec-kitty.tasks
/spec-kitty.implement WP01
```

This invocation remains provisional until the live CLI smoke test is recorded.

## Troubleshooting

- **`/spec-kitty.*` workflows do not appear.**
  Run `spec-kitty agent config sync` from the repo root. This rewrites
  `.agent/workflows/` from the canonical source templates. Restart
  Antigravity and re-check workflow discovery.

- **The `agent` command is present but help mentions Cursor.**
  That is not Antigravity. Install or locate the Antigravity CLI before
  recording verification evidence.
