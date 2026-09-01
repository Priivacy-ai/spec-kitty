---
title: 'SaaS & Hosted Sync — Domain Plan'
description: 'Durable, version-spanning domain plan for the SaaS / hosted-sync surface: sync & event-envelope integrity, consent & identity, auth & token lifecycle, and hosted rollout readiness.'
doc_status: deprecated
updated: '2026-08-31'
related:
- docs/plans/index.md
- docs/plans/3-2-x-open-core-delivery-plan.md
- docs/plans/glossary-doctrine-overhaul-program.md
- docs/adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md
- docs/adr/3.x/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md
- docs/adr/3.x/2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md
- docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md
- docs/adr/2.x/2026-01-27-12-two-branch-strategy-for-saas-transformation.md
---

# SaaS & Hosted Sync — Domain Plan

> **Removed in 3.2.6; kept as historical record.** This durable plan describes
> the deleted CLI→SaaS sync domain. It is scheduled for deletion in 3.2.7.

**Audience:** the project maintainer — technical, time-pressed, wants signal over ritual.

> **Status: durable domain plan (throughline).** Unlike the release-scoped
> `docs/plans/` working notes that follow the distil-then-retire lifecycle, this
> document is one of the **standing domain throughlines** meant to persist across
> releases. It is the index and the "why" for the SaaS / hosted-sync surface; the
> release milestones and epics it references are the "what ships when." Where a
> release plan and this plan disagree on *scope of the domain*, this plan is the
> canonical map; where they disagree on *what ships in a given tag*, the milestone
> roadmap and the owning epic win. Keep this plan factual and current; do not let it
> accrete release-scoped tracking that belongs in an epic.

---

## 1. Purpose & scope

**Purpose.** Give the SaaS / hosted-sync surface a single durable home that states
the *invariants* the surface must hold, groups the domain's lasting sub-areas, and
points at the epics and ADRs that carry the design and the tracking. Before this
plan, SaaS planning had no standalone document (see §2). This plan becomes the
domain's index.

**In scope — the hosted surface.** "SaaS" and "hosted sync" here mean the hosted
Team Kitty product and the CLI ↔ hosted boundary that feeds it:

- The **sync path** (offline queue, batch transport, daemon, drain/dispatch) that
  carries local mission and event state to the hosted projection.
- The **event envelope** (`spec-kitty-events`) — the identity, ordering, and
  contract fields every synced event must carry.
- **Consent & identity** — which project's state is allowed to leave the machine,
  and under whose authenticated identity.
- **Auth & token lifecycle** — browser-mediated human login, machine/non-interactive
  auth, and token refresh/invalidation.
- **Hosted rollout & readiness gating** — the `SPEC_KITTY_ENABLE_SAAS_SYNC` stealth
  gate, the `HostedReadiness` evaluator, and the Team Kitty launch defaults.

**Explicit non-goals.**

- **Not the open-core doctrine/charter split.** Despite the "SaaS" label sometimes
  attached to it, the open-core work (charter-as-sole-door, built-in doctrine module
  extraction, Creed/Values schema) is a *different domain*. It lives in the
  [3.2.x Open-Core Delivery Plan](../3-2-x-open-core-delivery-plan.md) and the
  doctrine+charter throughline. This plan does not restate it. (This distinction is
  the single most-common miscategorisation in the corpus: the open-core plan's "SaaS"
  is the open-core split of the doctrine layer, not the hosted product.)
- **Not the tracker/connector product design** beyond the hosted-sync boundary it
  shares. Connector-auth and tracker-binding decisions are referenced where the sync
  boundary depends on them, not owned here.
- **Not release scheduling.** Which fix ships in 3.2.6 vs 3.3.x is the milestone
  roadmap's and the epic's job (§5).

**Why a durable domain plan and not a release plan.** The hosted surface is a
standing set of invariants (data must not be lost or mis-attributed; a machine must
not leak a non-consenting project's state; a logged-in CLI must stay authenticated).
Those invariants outlive any one tag. Release plans churn as milestones close; the
invariants and their sub-areas do not. The issue tracker is already unwieldy, so the
throughline deliberately holds the *durable spine* and cross-references the
release-scoped docs rather than duplicating their tables.

---

## 2. Where SaaS planning lives today (honest inventory)

There has been **no standalone SaaS plan** before this document. A sweep of
`docs/plans/` finds no SaaS-, sync-, or auth-named plan, only a per-team tracker
prompt inside a tracker-binding initiative and one event-sync research synthesis
note. SaaS planning was instead distributed across five surfaces:

1. **[3.2.x Open-Core Delivery Plan](../3-2-x-open-core-delivery-plan.md)** — despite
   "open-core," it is scoped to the *doctrine/charter* seam. Its §3 remaining-work
   table has **no sync, hosted-sync, or auth row**, and its readiness posture (§1.5)
   is about the CI-red baseline, not the P0 SaaS cluster. It is a non-goal boundary
   for this plan, not a home for the hosted surface.
2. **ADR [2026-04-11-1 SaaS Rollout Gate and Hosted Readiness Split](../../adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md)**
   — the `src/specify_cli/saas/` rollout-gate + `HostedReadiness` evaluator design.
   The closest thing to a SaaS design of record, but a single-mission ADR, not a
   program plan.
3. **ADR [2026-01-27-12 Two-Branch Strategy for SaaS Transformation](../../adr/2.x/2026-01-27-12-two-branch-strategy-for-saas-transformation.md)**
   — historical origin of the SaaS transformation (2.x greenfield branch, YAML →
   event-log migration). Superseded in practice by the single-`main` posture; kept
   for lineage.
4. **Epic #1800 "SaaS sync & event-envelope hardening"** — the de-facto home for the
   sync plumbing (69 sub-issues, 28 complete as of 2026-08-11). Scope: event
   envelope, sync protocol, concurrency/safety, local durability. It is an
   issue-tracker grouping with scope bullets, **not a written plan** (now milestone
   3.3.x).
5. **Epic #1091 "Team Kitty launch gate"** (milestone 3.3.x) — the launch-blocker
   checklist for the hosted/MVP path; owns launch defaults (#1621) and the
   identity-boundary MVP work.

**This plan now becomes the domain's index.** It does not replace #1800, #1091, or
the ADRs — it ties them together under one set of invariants and surfaces the gap
they collectively leave open (§4).

---

## 3. Standing concerns — the durable spine

The domain divides into four lasting sub-areas. Each states the **invariant** it must
hold (the durable "why"), then lists the **currently open issues** grouped beneath it
(the release-scoped "what," which will turn over across versions).

### 3.1 Sync & event-envelope integrity

**Invariant.** Sync never reports success while authored state is still stranded, and
every synced event carries a complete, contract-valid envelope. Local mission and
event state converges to the hosted projection **without loss and without a false
"done" signal**. The event contract (`spec-kitty-events`) is authoritative — the CLI
must not emit envelopes the pinned events library declares invalid.

**Design of record.** Epic #1800 scope bullets (event envelope, sync protocol,
concurrency/safety, local durability); the event-sync retention/delivery research
synthesis that feeds it; ADR
[2026-06-30-1 sync-daemon identity and cleanup classification](../../adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md).

**Open issues.**

- **#3278 (P0, 3.2.x, → #1800)** — sync reports success while a `MissionCreated`
  event remains stranded in the legacy queue. Direct violation of the no-false-success
  invariant.
- **#3307 (P0, 3.2.x, → #1800)** — CLI emits `force=False` for review-rejection
  rollbacks that `spec-kitty-events` 6.1.0 declares contract-invalid. Envelope
  contract violation. *(Reparent to #1800 is done — it was previously an orphan P0.)*
- **#3191 (P1, 3.2.x, → #1800)** — per-event historical mission-state screen lost with
  the #3167 drain retirement; the daemon dispatch path has no equivalent.
- **#3201 (P2, 3.2.x, → #1800)** — `cli/commands/sync.py:2081` is an enforcement site,
  not a display-only read; #3167 misclassified it.
- **#3237 (P2, → #1800)** — `sync.runtime` async-loop thread can outlive a caller's
  `reset_runtime()` and be orphaned by later runtime churn.
- **#3290 (P3, 3.2.x, → #1800)** — `runtime_bridge` hard-imports
  `sync.runtime_event_emitter`: an unguarded core-loop → sync coupling outside the
  integration-boundary gate.

### 3.2 Consent & identity boundary

**Invariant.** A machine only transmits the state of a project that has **explicitly
consented**, under a **single, unambiguous** project→identity resolution, and consent
state is scoped to the grant (never silently written machine-global or outliving the
grant). No non-consenting project's events leave the machine.

**Design of record.** Epic #1091 identity-boundary MVP work and the cross-repo sync
identity boundary epic it references; the consent/identity issues clustered under #1800.

**Open issues.**

- **#3178 (P0, 3.2.x, → #1800)** — decision-widen resolves the destination team from
  the environment **before** the per-project auth file, so FR-007 is not discharged by
  FR-002. Wrong-authority egress: the load-bearing consent/identity P0.
- **#3197 (P1, 3.2.x, → #1800)** — three envelope→`project_uuid` resolvers disagree,
  including a nil-sentinel *deny* vs *pass-through* split. Ambiguous identity resolution.
- **#3196 (P1, 3.2.x, → #1800)** — `consented_project_uuids()` writes machine-global
  config on read, and the write outlives the grant. Consent-scope leak.
- **#3198 (P1, 3.2.x, → #1800)** — a consenting project's events are silently withheld
  when the daemon's frozen cwd is inside no project. Consent honoured in the wrong
  direction (false withhold).
- **#3262 (P1, 3.3.x, → #1091)** — hosted-sync consent: explicit per-project opt-in +
  per-project ledger, no default-on. The forward-looking consent model this sub-area
  converges toward.

### 3.3 Auth & token lifecycle

**Invariant.** A logged-in CLI stays authenticated until explicit logout or
server-side invalidation; human auth is browser-mediated (never CLI password entry);
non-interactive/machine contexts have a supported auth path; and token-refresh
failures are diagnosed by name, never surfaced as an unexplained error.

**Design of record.** ADR
[2026-04-09-2 CLI-to-SaaS auth is browser-mediated OAuth](../../adr/3.x/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md)
(PKCE loopback default, device flow headless fallback), **superseded on local session
storage** by ADR
[2026-04-19-1 CLI auth uses encrypted-file-only session storage](../../adr/3.x/2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md);
and the auth-transport boundary ADRs (2026-04-26-2, 2026-05-18-2). Note the OAuth ADR
explicitly scopes **machine-to-machine automation as a separate, still-unspecified auth
model** — which is exactly the gap in §4.

**Open issues.**

- **#3279 (P1, 3.3.x, → #3322)** — device authorization gets a 401 *after*
  browser approval (reproduced on 3.2.5 and 3.2.6). A direct break of the
  device-flow fallback the OAuth ADR mandates.
- **#3277 (P1, 3.3.x, → #3322)** — no non-interactive machine authentication for
  hosted sync (CI). The unspecified M2M model, now a concrete blocker.
- **#3233 (P2, 3.3.x, → #3322)** — token refresh reports "you sent no
  credential" as an unexplained failure; `invalid_client` / `invalid_request` are
  unhandled. Violates the "diagnosed by name" half of the invariant.

> **This sub-area now has an owning epic — #3322 "CLI auth & token-lifecycle
> reliability" (milestone 3.3.x)**, which owns #3279 / #3277 / #3233, pulled off
> #1091 and #1800 where they were previously miscategorised. #3322 treats device-auth
> reliability, machine auth, and token-refresh error handling as one design problem —
> closing what was the domain's key structural gap (see §4).

### 3.4 Hosted rollout & readiness gating

**Invariant.** On a machine without the rollout opt-in, the hosted surface is fully
hidden and no SaaS network traffic occurs (fail-closed); in enabled mode, every
readiness failure names the specific missing prerequisite and its corrective action;
local-only and help commands never start hosted background networking. At launch, the
packaged CLI has a default hosted URL and the `SPEC_KITTY_ENABLE_SAAS_SYNC` /
`SPEC_KITTY_SAAS_URL` flags are dev/test overrides, not required launch setup.

**Design of record.** ADR
[2026-04-11-1 SaaS Rollout Gate and Hosted Readiness Split](../../adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md)
— the canonical `src/specify_cli/saas/` package (`rollout.py`, `readiness.py`), the
6-state `ReadinessState` evaluator, the `DaemonIntent` gate, and the
`BackgroundDaemonPolicy` config key. Epic #1091 launch acceptance (default hosted URL,
readiness/upgrade notifications, machine-clean output).

**Open issues.** Mostly the #1091 launch-gate children: #1621 (flip CLI workspace
launch defaults), #2262 (`sync import-history` materialisation so straddling projects
are not half-tracked), and the cross-repo launch-defaults / compatibility-metadata
items. These are milestone-3.3.x launch work; the *invariant* (fail-closed by default,
named readiness failures) is already the shipped rollout posture and must not regress
as launch defaults flip on.

---

## 4. Known gaps

1. **Auth-reliability epic — done (was the key gap).** Epic **#3322 "CLI auth &
   token-lifecycle reliability"** (milestone 3.3.x) now owns **#3279 / #3277 / #3233**,
   reparented off #1091 (launch-defaults checklist) and #1800 (sync hardening) where
   they were miscategorised. #3322 is the single design home for device-auth
   reliability, non-interactive machine auth, and token-refresh error handling — the
   M2M model the OAuth ADR flagged as unspecified. This closes what was the one
   genuinely unplanned area of the domain.
2. **#3307 reparent — done.** The formerly orphan P0 is now parented under #1800 (§3.1).
   No further action beyond keeping it visible in the P0 readiness view.
3. **#1800 milestone — assigned (3.3.x).** The sync-plumbing epic (69 children) now
   carries milestone 3.3.x, so the sync-integrity spine is schedulable as a unit. Its
   P0/P1 children still carry 3.2.x milestones (they ship in the current cycle); the
   epic-level 3.3.x tag tracks the full spine, not the individual bug fixes.
4. **No unified SaaS readiness view outside this plan.** The P0 SaaS cluster
   (#3178 / #3278 / #3307) is not reflected in the open-core plan's readiness posture,
   so a PO reading only that plan would not see these P0s. §5 is the reconciling view;
   keep it current as the cluster clears.

---

## 5. Release-scoped view (the "what ships when")

This plan tracks the **why** (invariants and sub-areas); the epic tracks the
**what-ships-when**. The table below is a snapshot for orientation, not a schedule.
It will turn over as milestones close. Verify live state via
`gh issue view <n> --repo Priivacy-ai/spec-kitty` before acting.

| Issue | Pri | Sub-area (§3) | Milestone | Owning epic | Notes |
|---|---|---|---|---|---|
| #3178 | P0 | Consent & identity (3.2) | 3.2.x | #1800 | Wrong-authority egress; FR-007 not discharged |
| #3278 | P0 | Sync integrity (3.1) | 3.2.x | #1800 | Sync false success, `MissionCreated` stranded |
| #3307 | P0 | Sync integrity (3.1) | 3.2.x | #1800 | Envelope contract (`force=False` rejected by events 6.1.0); reparent done |
| #3197 | P1 | Consent & identity (3.2) | 3.2.x | #1800 | Three `project_uuid` resolvers disagree |
| #3196 | P1 | Consent & identity (3.2) | 3.2.x | #1800 | Consent write outlives grant |
| #3198 | P1 | Consent & identity (3.2) | 3.2.x | #1800 | Consenting project's events silently withheld |
| #3191 | P1 | Sync integrity (3.1) | 3.2.x | #1800 | Historical state screen lost with #3167 drain retirement |
| #3279 | P1 | Auth lifecycle (3.3) | 3.3.x | #3322 | Device auth 401 after browser approval |
| #3277 | P1 | Auth lifecycle (3.3) | 3.3.x | #3322 | Non-interactive machine auth (CI) |
| #3262 | P1 | Consent & identity (3.2) | 3.3.x | #1091 | Per-project sync consent opt-in |
| #3233 | P2 | Auth lifecycle (3.3) | 3.3.x | #3322 | Token-refresh error handling |
| #3201 | P2 | Sync integrity (3.1) | 3.2.x | #1800 | Enforcement site misclassified as display-only |
| #3237 | P2 | Sync integrity (3.1) | — | #1800 | Async-loop orphan on runtime churn |
| #3290 | P3 | Sync integrity (3.1) | 3.2.x | #1800 | `runtime_bridge` → sync hard-import coupling |

*Read the WHY in §3; the epic tracks the WHAT-ships-when. The three auth rows now sit
under #3322 — the former §4 gap, now closed.*

---

## 6. Cross-references

**Sibling domain throughlines (the durable spine of `docs/plans/`):**

- **Doctrine & charter** — [3.2.x Open-Core Delivery Plan](../3-2-x-open-core-delivery-plan.md)
  and [Glossary Doctrine Overhaul — Program Plan](../glossary-doctrine-overhaul-program.md).
  The open-core plan is the **non-goal boundary** for this plan (§1): its "SaaS" is the
  open-core split of the doctrine layer, not the hosted product.
- **Packs extraction** — *(planned sibling domain plan; not yet written.)* Will own the
  built-in → module → repo extraction lineage the open-core plan currently carries.
- **API & dashboard** — *(planned sibling domain plan; not yet written.)* Will own the
  hosted API surface and dashboard the sync projection feeds.

**SaaS ADRs (design of record):**

- [2026-04-11-1 SaaS Rollout Gate and Hosted Readiness Split](../../adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md) — rollout gate + `HostedReadiness`.
- [2026-04-09-2 CLI-to-SaaS auth is browser-mediated OAuth](../../adr/3.x/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md) — human auth model (superseded on session storage).
- [2026-04-19-1 CLI auth uses encrypted-file-only session storage](../../adr/3.x/2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md) — the superseding session-storage decision.
- [2026-06-30-1 sync-daemon identity and cleanup classification](../../adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md) — daemon identity/cleanup.
- [2026-01-27-12 Two-Branch Strategy for SaaS Transformation](../../adr/2.x/2026-01-27-12-two-branch-strategy-for-saas-transformation.md) — historical origin.

**Epics:** #1800 (SaaS sync & event-envelope hardening, 3.3.x), #1091 (Team Kitty
launch gate, 3.3.x), #3322 (CLI auth & token-lifecycle reliability, 3.3.x).

**Plans index:** [docs/plans/index.md](../index.md).
