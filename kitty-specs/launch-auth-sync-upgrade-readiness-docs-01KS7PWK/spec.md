# Specification — Launch Auth, Sync, and Upgrade Readiness Docs

**Mission slug**: `launch-auth-sync-upgrade-readiness-docs-01KS7PWK`
**Mission type**: `documentation`
**Target branch**: `main`
**Tracking issue**: [Priivacy-ai/spec-kitty#1095](https://github.com/Priivacy-ai/spec-kitty/issues/1095) (Workstream 6)
**Wave 1 dependency**: [#1093](https://github.com/Priivacy-ai/spec-kitty/issues/1093) — central CLI startup readiness coordinator (already merged)

## TL;DR

Stage two operator-facing docs — one for **internal / pre-launch** operators
who dogfood the hidden hosted-readiness mode behind
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`, and one **future-launch** readiness doc
that documents the launch-day behavior shift (labeled "coming soon /
launch"). Keep the public README and docs index local-first; do not
imply Teamspace is launched. Add copy-pasteable remediation snippets.

## Problem statement

Wave 1 (#1093) landed the central CLI startup readiness coordinator and a
stubbed `AuthStatus` enum that fires only when `SPEC_KITTY_ENABLE_SAAS_SYNC`
is truthy. Sister missions widen `AuthStatus`, render guidance from any
command, surface a Teamspace-aware sync compatibility check, and reshape
the upgrade-readiness UX. The runtime surface for these readiness states
will exist on `main` before any public launch.

Today there is no canonical operator doc explaining:

1. How an internal / pre-launch operator turns the hidden hosted-readiness
   mode on, what guidance the CLI surfaces, and how to verify locally.
2. What behavior will flip on at the public launch (default SaaS URL,
   sync-by-default, the meaning of the env var post-launch) so the
   launch handoff has a reference doc to flip on.
3. Which exact copy-pasteable commands a user runs in each readiness
   scenario (logged out, tracker unreachable, upgrade required, …).

Without these docs, internal operators cannot dogfood the readiness work
that sister missions are landing, and the eventual launch has no
operator-facing playbook ready to ship.

## Operating rules (hard constraints)

These constraints are inherited from `start-me-start-here.md` (WS6) and
issue #1095, and are non-negotiable:

- **Docs-only.** No CLI logic changes. No test changes. No new code
  surfaces. The mission touches Markdown / YAML doc files only.
- **Public docs MUST NOT imply Teamspace is launched.** The top-level
  README and the public `docs/index.md` remain local-first. They may
  link to the new internal / launch docs, but the link text must signal
  that hosted is opt-in today and labeled future-launch for the launch
  doc.
- **Internal doc** describes `SPEC_KITTY_ENABLE_SAAS_SYNC=1` as an
  internal / dev / pre-launch hosted mode. It must clearly distinguish
  dev / staging URL overrides (`SPEC_KITTY_SAAS_URL`) from the future
  launch-day user behavior.
- **Launch doc** carries an explicit "coming soon / launch" header so
  it cannot be mistaken for current behavior.
- **Remediation commands are copy-pasteable** code blocks
  (`spec-kitty auth login`, `spec-kitty upgrade --cli`, …) — not prose.
- `unset GITHUB_TOKEN` before any `gh` writes.
- No direct push to `main`. PR-bound.

## Acceptance criteria

Each criterion below maps to a verifiable artifact in this PR.

### AC-1: Public docs stay local-first

- The README's "Is It For You?" / "What It Provides" / "Quick Start"
  copy continues to frame hosted as **optional / opt-in / later**.
- The README's existing "Documentation → Hosted Sync Workspaces" link
  carries a one-line gating note pointing readers to the internal
  pre-launch doc when they need to know how the hidden mode behaves
  today.
- `grep -i -E 'teamspace.*launch(ed)?|launched.*teamspace|now (generally |publicly )?available' README.md docs/index.md` returns no
  occurrences that imply current launched status.

### AC-2: Internal / pre-launch operator doc exists

Path: `docs/how-to/internal-hosted-readiness.md` (Diátaxis: how-to;
audience: internal / pre-launch operators).

Contents must include, at minimum:

- An explicit header that this doc is for **internal / pre-launch
  operators and core contributors**, not end users.
- The single source of truth for `SPEC_KITTY_ENABLE_SAAS_SYNC` —
  truthy values, byte-wise-stable disabled message reference, and a
  note that with the flag unset the coordinator is a no-op.
- How to enable hosted readiness locally:
  ```bash
  export SPEC_KITTY_ENABLE_SAAS_SYNC=1
  spec-kitty auth login
  ```
- How to point a session at a dev / staging hosted environment via
  `SPEC_KITTY_SAAS_URL` (clearly framed as a dev override, not a user
  behavior).
- Which readiness scenarios the CLI surfaces today (auth status:
  logged-out-on-connected-teamspace, disabled, future widened states
  from sister missions) with a one-line summary of what the coordinator
  emits in each state.
- A "verify locally" recipe an internal operator can run end-to-end.
- Suppression contract pointer: a note that the coordinator honors the
  Wave 1 suppression contract (interactive / non-interactive /
  machine-output) byte-for-byte; link to the existing recovery doc and
  the rollout-contract module.
- "Not for end users — see [launch-readiness-future] for the
  launch-day playbook" cross-link.

### AC-3: Launch-readiness future doc exists

Path: `docs/explanation/launch-readiness-future.md` (Diátaxis:
explanation; audience: launch coordinators + operators planning the
flip).

Contents must include, at minimum:

- A **prominent, unmistakable** future-launch banner at the top of the
  doc (e.g., a blockquote `> Status: pre-launch — describes behavior
  that ships at the public Teamspace launch; not in effect today.`).
- The behavior shift the launch flips on, framed as a delta from
  today's local-first default:
  - The default SaaS URL on launch.
  - The role of `SPEC_KITTY_ENABLE_SAAS_SYNC` post-launch (override
    only — does **not** toggle availability for end users).
  - Sync defaults and what "Teamspace-connected" means at launch.
- Operator playbook for the launch flip itself (release-cut order,
  what becomes user-facing, what stays internal).
- Explicit "dev / staging URL overrides remain in effect for internal
  hosted environments after launch; see [internal-hosted-readiness]
  for details" cross-link.
- Remediation commands users will see at launch (copy-pasteable):
  ```bash
  spec-kitty auth login
  spec-kitty upgrade --cli
  ```

### AC-4: Remediation snippets are copy-pasteable

Every remediation command appears in a fenced code block on its own
line (no prose substitution required), in both the internal doc and
the launch doc:

- `spec-kitty auth login` — for hosted-tracker / connected-Teamspace
  logged-out recovery.
- `spec-kitty upgrade --cli` — the canonical CLI upgrade probe (prints
  the right installer command for the detected install method, per
  `docs/how-to/upgrade-cli.md`).
- `spec-kitty sync doctor` — diagnostic in the hosted-mode-enabled
  path.

### AC-5: Cross-links from existing surfaces

- `docs/how-to/toc.yml` lists the new internal doc.
- `docs/explanation/toc.yml` lists the new launch-future doc.
- `docs/recovery/logged-out-teamspace.md` gets a "see also" link to the
  internal doc (one line, end of file).
- `docs/reference/environment-variables.md`'s
  `SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` entries each
  gain a "see [internal-hosted-readiness] for the full operator
  walkthrough; see [launch-readiness-future] for launch-day behavior"
  cross-link.

### AC-6: CHANGELOG entry

A single `[Unreleased]` bullet added per repo convention:

```
- Add pre-launch and launch-readiness operator docs for hosted SaaS
  sync (#1095). Public docs remain local-first; hosted readiness
  stays opt-in via SPEC_KITTY_ENABLE_SAAS_SYNC=1.
```

### AC-7: Operator leakage check passes

The following commands run from the repo root return no
launch-implying matches in public docs:

```bash
grep -niE 'teamspace.*launch(ed)?|launched.*teamspace|now (generally|publicly) available' README.md docs/index.md
grep -niE 'spec-kitty.*saas.*launched|hosted.*generally available' README.md docs/index.md
```

The launch doc is allowed (and required) to use launch-implying
language because it is explicitly labeled future-launch.

## In scope

- `README.md` — selectively. Only the existing hosted-sync / tracker
  link area, to add a gating note.
- `docs/how-to/internal-hosted-readiness.md` — new.
- `docs/explanation/launch-readiness-future.md` — new.
- `docs/how-to/toc.yml`, `docs/explanation/toc.yml` — TOC updates.
- `docs/recovery/logged-out-teamspace.md` — single see-also link.
- `docs/reference/environment-variables.md` — cross-link additions on
  the two hosted env-var entries.
- `CHANGELOG.md` — single `[Unreleased]` bullet.

## Out of scope

- Coordinator code in `src/specify_cli/readiness/` (Wave 1 + sister
  missions C/D own that).
- Tracker client behavior (Mission E owns that).
- SaaS-side docs (separate repo — `spec-kitty-saas`).
- Marketing copy. The mission writes technical operator-facing prose
  only.
- Renaming or removing existing public docs. Additive only on the
  public surface.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Launch doc leaks as current behavior if banner is missed | AC-3 mandates a prominent banner; AC-7 leakage check verifies public docs separately. |
| Internal doc becomes stale when sister missions widen `AuthStatus` | Internal doc references the rollout-contract module and existing recovery doc rather than restating enum values; that keeps it stable across sister-mission landings. |
| Concurrent sister missions touch the same files | This mission only touches docs, README sync-link area, CHANGELOG, env-var reference, and recovery see-also. None of those are sister-mission targets. |
| CHANGELOG conflicts on merge | Single `[Unreleased]` bullet — conflicts are trivial. |

## References

- WS6 brief: `start-me-start-here.md`
- Wave 1 PR: #1282 (commit `77c1647e7`)
- Recovery doc baseline: `docs/recovery/logged-out-teamspace.md`
- Env-var reference: `docs/reference/environment-variables.md`
- Upgrade-CLI doc: `docs/how-to/upgrade-cli.md`
- Rollout contract module: `src/specify_cli/saas/rollout.py`
- Readiness coordinator module: `src/specify_cli/readiness/coordinator.py`
