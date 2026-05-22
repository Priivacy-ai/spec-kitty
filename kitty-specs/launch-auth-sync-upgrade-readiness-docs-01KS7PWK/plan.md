# Implementation Plan — Launch Auth, Sync, and Upgrade Readiness Docs

Driven directly from `spec.md`. No interview questions; brief-intake mode.

## Doc-site structure and audience separation

The repo's docs follow the Diátaxis 4-quadrant layout under `docs/`:

| Quadrant | Folder | Audience |
|---|---|---|
| Tutorials | `docs/tutorials/` | New users learning Spec Kitty. |
| How-to | `docs/how-to/` | Operators solving a specific task. |
| Reference | `docs/reference/` | Lookups (CLI, env vars, config). |
| Explanation | `docs/explanation/` | Background / "why" / architecture. |

Audience routing for this mission:

- **Internal / pre-launch operators** — task-oriented, copy-pasteable
  recipes. Belongs in `docs/how-to/`.
- **Launch coordinators / readers thinking about the launch flip** —
  conceptual background on what will change. Belongs in
  `docs/explanation/`.

The two docs cross-link to each other to keep the routes obvious from
either entry point.

## File surface

| Action | Path | Type |
|---|---|---|
| Create | `docs/how-to/internal-hosted-readiness.md` | how-to (internal-audience) |
| Create | `docs/explanation/launch-readiness-future.md` | explanation (future-launch labeled) |
| Edit | `README.md` | one-line gating note next to the existing "Hosted Sync Workspaces" link |
| Edit | `docs/how-to/toc.yml` | add the new how-to entry |
| Edit | `docs/explanation/toc.yml` | add the new explanation entry |
| Edit | `docs/recovery/logged-out-teamspace.md` | append a single "see also" bullet |
| Edit | `docs/reference/environment-variables.md` | cross-link notes on `SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` |
| Edit | `CHANGELOG.md` | single `[Unreleased]` bullet |

No other paths are touched. No code, no tests, no templates, no
slash commands, no migrations.

## Audience separation contract

| Doc | Reader assumption | Allowed language |
|---|---|---|
| `README.md`, `docs/index.md` | End user, today, local-first. | "Optional", "opt-in", "later", "internal preview", "hosted is not yet generally available". Never: "launched", "now available", "generally available". |
| `docs/how-to/internal-hosted-readiness.md` | Internal operator who has cloned the repo or has commit access; willing to set env vars. | "Pre-launch", "dev / staging", "internal hosted mode", "behind `SPEC_KITTY_ENABLE_SAAS_SYNC=1`". |
| `docs/explanation/launch-readiness-future.md` | Reader planning the launch flip. | "At launch", "post-launch", "future", with a prominent banner that the doc describes behavior **not in effect today**. |

This separation is the load-bearing structural decision of the mission.
Every editorial choice in the WPs below must defer to this table.

## Content outline — internal-hosted-readiness.md

```markdown
---
type: how-to
audience: internal / pre-launch operators
---

# Internal hosted-readiness mode (pre-launch)

> Audience: internal contributors and dev operators dogfooding the
> hidden hosted-readiness path. This page is **not** for end users —
> see the public Quick Start for local-first usage.

## When this page applies
- The repo set you're testing has the SaaS rollout gate available
  (`src/specify_cli/saas/rollout.py`).
- You want the CLI to surface Teamspace-aware readiness output.

## Enable the hidden hosted mode
```bash
export SPEC_KITTY_ENABLE_SAAS_SYNC=1
spec-kitty auth login
```

(Then a "Verify locally" section, an "Override the SaaS URL" section
for `SPEC_KITTY_SAAS_URL`, a readiness-state table, suppression-contract
pointer, and "Not for end users" cross-link to the launch-future doc.)
```

## Content outline — launch-readiness-future.md

```markdown
---
type: explanation
audience: launch coordinators
---

# Launch-readiness behavior (coming soon)

> **Status: pre-launch.** This page describes the Teamspace launch
> behavior that the Spec Kitty CLI will adopt at the public launch
> milestone. **None of this is in effect today.** For today's
> local-first experience, see the [README](../../README.md). For the
> internal hosted-readiness preview, see
> [Internal hosted-readiness mode (pre-launch)](../how-to/internal-hosted-readiness.md).

## What flips at launch
- (Table of today vs at-launch for: SaaS URL default, sync default,
  meaning of `SPEC_KITTY_ENABLE_SAAS_SYNC`, default tracker.)

## Launch-day remediation commands
```bash
spec-kitty auth login
spec-kitty upgrade --cli
```

(Then "Operator playbook for the flip", "Dev / staging overrides
remain in effect — see internal doc", and a closing "out of scope"
section.)
```

## Test strategy

- **Render check:** the two new docs are valid Markdown and follow the
  same fence / heading style as their siblings in `docs/how-to/` and
  `docs/explanation/`.
- **Cross-link check:** every relative link in the two new docs
  resolves to a file that exists in this PR's tree.
- **TOC check:** `docs/how-to/toc.yml` and `docs/explanation/toc.yml`
  list the new files.
- **Leakage check (AC-7):**
  ```bash
  grep -niE 'teamspace.*launch(ed)?|launched.*teamspace|now (generally|publicly) available' README.md docs/index.md
  grep -niE 'spec-kitty.*saas.*launched|hosted.*generally available' README.md docs/index.md
  ```
  Both must return zero matches.
- **CHANGELOG check:** `CHANGELOG.md` `[Unreleased]` section has the
  new bullet and no other modifications.

These checks are manual / grep-based, performed during phase 8 of the
mission workflow (final intent-vs-outcome). They do not require new
automated tests because the mission ships no code surface.

## Dependencies

| WP depends on | Lane hint |
|---|---|
| WP02 (launch doc) → WP01 (internal doc) | WP02 cross-links into WP01's file path, so WP01 lands first. |
| WP03 (cross-links + CHANGELOG) → WP01 + WP02 | WP03 references both doc paths. |

A single lane is sufficient (no real parallelism gain — every WP
touches a small file set and depends on the prior).

## Non-goals

- No edits to `docs/1x/`, `docs/2x/`, or `docs/3x/` — those are
  versioned archive surfaces with their own rules.
- No edits to sister missions' draft mission directories under
  `kitty-specs/`. If they leak files into the working tree during
  concurrent execution, they belong to those missions, not this one.
- No edits to existing public docs other than the one-line gating
  note on the README, the env-var cross-links, and the recovery
  see-also.

## Risks (plan-level)

- The README change must not balloon — keep it to a single sentence
  next to the existing "Hosted Sync Workspaces" link.
- The launch doc's banner must be visually unmistakable. Use a
  blockquote with bold "Status: pre-launch" inside the first 5 lines
  of the file.
