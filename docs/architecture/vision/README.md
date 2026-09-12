---
title: Architecture Vision (living)
description: 'Landing page for the living architecture vision: the current and future, still-changeable forward intent at the top of architecture/, above versioned history.'
doc_status: active
updated: '2026-08-12'
related:
- docs/architecture/README.md
- docs/plans/code-quality/index.md
---
# Architecture Vision (living)

This directory holds the **current and future** architecture vision for Spec Kitty —
forward intent that may still change. It is part of the *living architecture at the
top* of `architecture/` (see [`../README.md`](../README.md) for the boundary and decay rules).

## What belongs here

- The synthesized "where the architecture is going" narrative for the active era.
- Forward-looking structural intent that has not yet been ratified as an ADR.

## What does NOT belong here

- **Ratified decisions** — those are ADRs under `architecture/<version>/adr/` (immutable, era-stamped).
- **Explorations / spikes** — those are research notes under `architecture/<version>/research/`.
- **Historical vision** — when a vision statement is no longer current/future it is
  *demoted* into its era directory `architecture/<version>/vision/` (the decay path; nothing is deleted).

## Vision vs Decision vs Spike

| Artifact | Meaning | Home | Mutability |
|---|---|---|---|
| Vision | Forward intent | `docs/architecture/vision/` (top-level, living) | May change |
| Decision (ADR) | Ratified decision | `architecture/<version>/adr/` | Immutable, era-stamped |
| Spike | Exploration | `architecture/<version>/research/` | Versioned record |

## Current-era forward signal (2026-08-12)

Forward intent, corroborated by the 2026-08-12 code-health measurement (full detail:
[Code Quality — Working Collection](../../plans/code-quality/index.md)). Not yet an ADR.

The 3.x north-star — a **doctrine-governed, charter-activated runtime with a hardened
execution model** — is showing up in the measurements, not just the design:

- **The stabilization cycle is converging.** Coverage recovered from a mid-2026 trough
  of ~47% to a project-high **84%**, reliability bugs cleared to **0**, and duplication
  holds at **0.5%**. The `next` control loop and the execution-lane / coord-primary
  model are built and canonical; the health signal now tracks the "hardened execution
  model" intent rather than lagging it.
- **The remaining structural debt is scoped, not drifting.** The one standing red — a
  SonarCloud `security_rating` of E from ~21 pre-existing subprocess/path findings —
  concentrates in the lane / coordination / sync surfaces the 3.x execution model built
  out, and maps almost 1:1 onto the **already-planned** Wave 2 / Wave 4 degod slices.
  The forward intent is to burn that backlog down *through* the degod program (with
  characterization tests first), not as cosmetic passes, and to keep the
  charter-as-sole-door and governance-honesty through-lines as the gate on new debt.
- **Governance honesty holds as a design principle.** "Red main is honest; CI is the
  release authority" (ADR 2026-07-17-1) is what lets an honest standing red coexist
  with a cuttable release candidate — the release posture is read from the *functional*
  gates, with the Sonar backlog tracked as known/deferred.
