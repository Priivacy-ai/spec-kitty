---
title: Architecture Vision (living)
description: 'Landing page for the living architecture vision: the current and future, still-changeable forward intent at the top of architecture/, above versioned history.'
doc_status: active
updated: '2026-06-12'
related:
- docs/architecture/README.md
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
