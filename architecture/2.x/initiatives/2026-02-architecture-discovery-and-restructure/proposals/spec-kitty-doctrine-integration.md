# Spec Kitty × Doctrine Integration Proposal

**Date:** 2026-02-28

This document captures the architectural direction for integrating
Doctrine capabilities into Spec Kitty while preserving clear separation
of concerns.

## Core Principle

Spec Kitty defines workflow structure (missions). Doctrine defines
execution behavior (agents, tactics, directives, templates).

## Architectural Layers

1.  User Journey (architectural choreography)
2.  Mission Recipe (structured step composition)
3.  Step Modules (atomic execution units)
4.  Doctrine Packs (behavioral strategy layer)

## Stability Rule

Stable C4 architecture reflects implemented reality. Initiatives contain
exploratory work. ADRs capture binding decisions.

## Strategic Framing

Spec Kitty evolves from:

> A mission runner

to

> A lifecycle-aware workflow engine supporting iterative discovery,
> disciplined formalization, and repeatable execution.
