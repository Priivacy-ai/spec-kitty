---
title: Doctrine Packs
description: Index of optional Spec Kitty doctrine packs that activate through charter selection.
---

# Doctrine Packs

A **doctrine pack** is a bundle of related shipped doctrine artifacts
(paradigm, tactics, styleguide, directive, template fragment, skill, and
docs) that a project can activate as a unit through charter selection.

Doctrine packs are **opt-in**. Projects that do not select a pack see no
behavior change. Projects that do select a pack receive guidance scoped to
the workflow action they are running.

Charter selection happens during the
[governance setup workflow](../how-to/setup-governance.md). To verify which
doctrine is active for the current project, run:

```bash
spec-kitty charter context --action specify --json
```

## Optional doctrine packs

| Pack | Summary |
|---|---|
| [SPDD and the REASONS Canvas](spdd-reasons.md) | Structured-Prompt-Driven Development with a seven-section change-intent canvas. For high-risk and multi-WP missions where a clear change boundary reduces drift. Code remains the source of truth for current behavior; the canvas records approved intent. |

## See also

- [How to set up project governance](../how-to/setup-governance.md)
- [Spec-driven development explained](../explanation/spec-driven-development.md)
