---
title: 'ADR: Executable doctrine runs only from trusted publishers (signed built-in; TOFU for the rest)'
description: 'Shipped doctrine code (gate assets) executes only from trusted publishers: built-in is release-signed and trusted by default; org/project packs use trust-on-first-use keyed on pack-meta identity; untrusted gates are skipped with a warning and never block or prompt at run time.'
status: Proposed
date: '2026-08-13'
related:
- docs/architecture/mission-gates.md
- docs/adr/3.x/2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md
---
# Executable doctrine runs only from trusted publishers

**Filename:** `2026-08-13-4-executable-doctrine-runs-only-from-trusted-publishers.md`

**Status:** Proposed

**Date:** 2026-08-13

**Deciders:** Operator (ATDD)

**Technical Story:** [ADR 2026-08-13-2](2026-08-13-2-gates-are-declarative-asset-backed-doctrine-artefacts.md)
makes gates run shipped code. Org and project packs can ship gates too — arbitrary code
executing on every mission transition. That is a supply-chain surface and needs a trust model.

---

## Context and Problem Statement

Declarative gates execute code shipped inside a doctrine pack. Built-in gates are first-party.
But the pack ecosystem (org packs, project packs) means a downstream pack could ship a gate
whose asset runs on every transition — an unreviewed code-execution surface. There is **no
trust, signing, or provenance-verification machinery today** (grep confirms: the nearest is
`drg/override_policy.py`, which is merge policy, not trust).

Inert doctrine (directives, tactics, styleguides) is text and is never executed — so a trust
decision is only ever needed for **executing shipped code** (gate assets). The scope is narrow
by construction.

## Decision Drivers

* Never execute unreviewed third-party code silently.
* Never hang or block a mission on a trust decision — gates fire in CI and (later) under a
  daemon, where no operator is present to prompt.
* Reuse the `pack-meta.yaml` identity/version/content-hash already proposed for the pack
  restructure rather than invent a parallel identity.

## Considered Options

* **A — Trust everything** (execute any pack's gate). Rejected: supply-chain hole.
* **B — Trust nothing but built-in** (never run org/project gates). Rejected: kills the ecosystem value.
* **C — Trust-on-first-use (TOFU), SSH-`known_hosts` style**, keyed on publisher identity.

## Decision Outcome

**Chosen option: "C".**

* **Built-in / spec-kitty-signed = trusted by default.** Built-in ships a signature over its
  `pack-meta.yaml` **content-hash**, verifiable against a bundled public release key. This
  gives the content-hash a second job (it is signed) alongside its cache-invalidation role.
* **Org/project packs = TOFU.** On first encounter of a pack that ships executable gates, the
  operator is asked, once, whether they trust the publisher (identity from `pack-meta.yaml`).
  The decision persists in a `known_hosts`-equivalent trust store in the spec-kitty home,
  keyed on publisher identity + the signed/observed content-hash.
* **The trust prompt happens at pack activation/install time, never mid-transition.** At run
  time the decision is looked up non-interactively.
* **Low-trust ⇒ skip + warn, transition proceeds.** An untrusted gate is **not run**; a loud
  warning records that a transition guard was skipped due to low trust, and the transition is
  **not blocked**. Consequence stated explicitly: a fail-closed gate from an *untrusted* pack
  provides **zero protection** — gate protection is only ever as strong as the trust decision.
* **CI / non-interactive is the governing constraint.** Unknown publisher at run time defaults
  to skip+warn — never a prompt, never a hang. Trust must be **pre-seedable** (config/flag) so
  CI and the daemon can run trusted gates without interaction.

### Consequences

#### Positive
* Third-party code never runs unreviewed; the operator's trust decision is explicit and persisted.
* CI and automation never block or hang on trust; the safe default is "don't run untrusted code".

#### Negative
* Signing infrastructure (release key, signature in `pack-meta.yaml`, verification path) is
  net-new and must be got right (key rotation, offline verification).
* "Skip + proceed" means an untrusted security gate silently protects nothing — this must be
  surfaced loudly, or an operator may believe a gate is guarding a transition that it is not.

#### Neutral
* Trust is orthogonal to gate correctness — a trusted gate can still be a bad check; a rejected
  gate can still be a good one that simply won't run.

### Open questions (for the dialectics squad)
1. Prompt at activation vs first-execution (TOFU-faithful but interrupts a transition)?
2. Is "skip + proceed" the right low-trust default, or should certain gate classes be able to
   declare "block if I cannot run" (turning untrust into a hard stop)?
3. Publisher identity granularity — per pack, per publisher key, per source URL?
4. Signing: detached signature over the content-hash vs a signed manifest; where the public
   key ships and how it rotates.
