# Spec Kitty × Doctrine Integration Proposal

**Status:** Ideation\
**Author:** Drafted via architectural synthesis\
**Date:** 2026-02-17

------------------------------------------------------------------------

## 1. Intent

This document proposes a structural integration between:

- **Spec Kitty** (mission-oriented workflow runner)
- **Doctrine** (behavioral and strategic capability library)

The goal is to:

- Preserve Spec Kitty as the **workflow engine**
- Extract Doctrine as a **portable capability layer**
- Introduce compositional modularity to missions
- Enable deep customization without turning Spec Kitty into
    configuration chaos

------------------------------------------------------------------------

## 2. Conceptual Model

### 2.1 Core Separation of Concerns

  Layer               Responsibility
  ------------------- ----------------------------------------------
  **Mission**         Structural workflow (step sequence / graph)
  **Step**            Atomic execution unit with declared contract
  **Doctrine Pack**   Behavioral + strategic configuration
  **Agent Profile**   Role definition and execution posture

------------------------------------------------------------------------

## 3. Structural Design

### 3.1 Steps (First-Class Modules)

Each step lives in a shared step repository and declares a strict
contract.

Example:

    steps/<step-id>/step.yaml

Required fields:

- `id`
- `inputs`
- `outputs`
- `preconditions`
- `success_criteria`
- `hooks` (doctrine injection points)

This prevents step soup and enforces composability discipline.

------------------------------------------------------------------------

### 3.2 Missions as Recipes

Missions become composed, versioned step bundles.

Example:

    missions/<mission-id>/recipe.yaml

Recipe structure:

- Ordered list of step IDs (or DAG)
- Default doctrine pack
- Optional step-level overrides
- Expected final artifacts

This makes missions **structural compositions** rather than monolithic
workflows.

------------------------------------------------------------------------

### 3.3 Doctrine as Behavioral Layer

Doctrine is reduced to portable assets only:

    doctrine/
      manifest.yaml
      packs/
      agents/
      directives/
      approaches/
      tactics/
      templates/

Doctrine provides:

- Strategy packs
- Role definitions
- Guardrails
- Templates
- Tactical techniques

Doctrine never orchestrates execution.\
It only injects behavior into step hooks.

------------------------------------------------------------------------

## 4. Doctrine Packs (Strategy Pattern)

Doctrine packs bundle:

- Default agent profile
- Active directives
- Preferred tactics
- Template defaults

Example packs:

- `default`
- `fast-pass`
- `audit-grade`
- `exploratory`
- `risk-first`

A mission selects a default pack but can be overridden per feature.

------------------------------------------------------------------------

## 5. Resolution Order

When running a mission:

1. Load mission recipe
2. Resolve step definitions (local → pinned shared repo)
3. Resolve doctrine pack
4. Inject doctrine snippets into step hooks
5. Execute steps in defined order

Version pinning is mandatory to prevent drift.

------------------------------------------------------------------------

## 6. Vocabulary Clarification

To avoid taxonomy confusion:

- **Mission = Recipe (structural)**
- **Doctrine Pack = Behavioral Mode**
- **Step = Atomic executable unit**

This keeps structure and strategy orthogonal.

------------------------------------------------------------------------

## 7. Customizability Without Chaos

To avoid combinatorial explosion:

- Ship stable **Core Missions**
- Allow **Custom Missions** under separate namespace
- Enforce strict step contracts
- Pin shared step repo versions
- Keep doctrine strictly non-orchestrating

------------------------------------------------------------------------

## 8. Benefits

- Structural modularity
- Behavioral modularity
- Clean separation of concerns
- Reusable step ecosystem
- Strategy flexibility without mission multiplication
- Stable core identity for Spec Kitty

------------------------------------------------------------------------

## 9. Strategic Positioning

> Spec Kitty defines *what happens next.*\
> Doctrine defines *how it is executed.*

Missions become composable structural recipes.\
Doctrine remains a portable strategy library.

The integration enables deep customization without collapsing
architectural boundaries.

------------------------------------------------------------------------

**End of Proposal**
