---
title: Release Goals — Declarations of Intent
description: 'Explains the release-goals section: one durable declaration of intent per emergent minor release milestone, scoped by minor cycle rather than by individual patch.'
doc_status: active
updated: '2026-06-16'
---
# Release Goals — Declarations of Intent

This directory holds one **declaration of intent** per *emergent release milestone*. It is the
durable, version-controlled record of **what a release cycle is trying to achieve and why** — the
counterpart to a sprint goal, scaled to a release cycle.

## The "emergent release milestones" model

We scope by **minor cycle**, not by individual patch:

- A milestone is named for a minor cycle: **`3.2.x`**, **`3.3.x`** (plus a retroactive point-in-time
  **`3.2.0`** for what already shipped).
- A minor cycle has **one goal** (or a small coherent set). Multiple **emergent patches**
  (`3.2.1`, `3.2.2`, …) each advance that *same* goal. The cycle's milestone stays **open until the
  goal is structurally met** — then it closes and the next cycle is declared.
- This gives the freedom to split a minor cycle into as many patches as the work needs, without
  re-litigating scope each time.

## Three surfaces, one goal — and how they connect

| Surface | Role | Lives in |
|---------|------|----------|
| **Declaration of intent** | The full goal · rationale · scope · non-goals · success criteria · emergent-patch plan | `docs/release-goals/<minor>.md` (this dir) — PR-reviewed, durable |
| **Milestone** | The burndown / "what's left" tracking surface | GitHub milestone `<minor>` — one-line goal + a link back here |
| **Mission** | The execution of a patch toward the goal | `kitty-specs/<mission>/` + its `issue-matrix.md` |

The declaration is the **source of truth for intent**; the milestone description is a short pointer
(it is ephemeral, char-limited, and not reviewable). A mission's `issue-matrix.md` is the per-patch
closure ledger that rolls up into the milestone burndown.

## Authoring a new cycle

1. Write `docs/release-goals/<minor>.md` from the template shape (see `3.2.x.md`): **Goal · Why now ·
   Scope · Non-goals · Success criteria · Emergent patches · Links**.
2. Create the GitHub milestone `<minor>` (open); put the one-line goal in its description with a link
   here. (Closed/retroactive milestones must be populated via the API by *number* — `gh issue edit
   --milestone` only resolves *open* milestones by title.)
3. Attach the cycle's in-flight issues to the milestone.
4. As patches ship, keep the declaration's success-criteria checklist honest; close the milestone +
   declaration when the goal is structurally met.

See [`HOW_TO_MAINTAIN.md`](../../HOW_TO_MAINTAIN.md) for the tracker structure, priority levels, and
issue types this plugs into.
