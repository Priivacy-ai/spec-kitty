---
title: Doctrine documentation
description: 'How Spec Kitty doctrine works: the artifact model behind governed missions and the Structured-Prompt-Driven Development (SPDD) REASONS canvas.'
doc_status: active
updated: '2026-07-21'
related:
- docs/context/index.md
- docs/doctrine/README.md
- docs/doctrine/doctrine-kinds.md
- docs/doctrine/create-a-doctrine-artifact.md
- docs/doctrine/spdd-reasons.md
- docs/index.md
---
# Doctrine documentation

Explanation-oriented pages about Spec Kitty doctrine — the layered artifacts (paradigms,
directives, tactics, profiles) that compose governed mission behavior.

Doctrine is how a project encodes its own rules — testing standards, architectural
conventions, agent behavior — so every agent, in every session, gets the same governed
context instead of a human re-explaining it in every prompt. Doctrine artifacts are layered:
built-in packs ship with Spec Kitty, a project can author its own (directives, tactics,
styleguides, and the rest), and an organization can package and share doctrine across many
projects. All of it activates through the [Charter](../context/index.md), not by
copy-pasting text into prompts. If you're not yet sure what "Charter" means, start with
[Context](../context/index.md) first.

## Which page do I need?

| I want to... | Go here |
|---|---|
| Understand what each doctrine kind is for | [Doctrine artifact kinds](doctrine-kinds.md) |
| Set up my project's own governance from scratch | [How to Set Up Project Governance](../guides/setup-governance.md) |
| Author one new directive/tactic/etc. for this project | [Create a doctrine artifact](create-a-doctrine-artifact.md) |
| Share doctrine across multiple projects | [How to Create an Org Doctrine Pack](../guides/create-an-org-doctrine-pack.md) |
| See the built-in opt-in packs (e.g. SPDD) | [Doctrine Packs](README.md) |

## In this section

- [Doctrine artifact kinds](doctrine-kinds.md) — what each of the eight doctrine artifact kinds
  (directive, tactic, styleguide, toolguide, paradigm, procedure, agent profile, mission step
  contract) is for, with a real example of each.
- [Create a doctrine artifact](create-a-doctrine-artifact.md) — a followable, end-to-end how-to
  for authoring and activating a new doctrine artifact.
- [Doctrine Packs](README.md) — the built-in, opt-in doctrine packs (e.g. SPDD) a project can
  activate through charter selection.
- [SPDD / REASONS](spdd-reasons.md) — Structured-Prompt-Driven Development and the REASONS canvas.

## See also

- [Documentation home](../index.md)
- [How Charter works](../context/index.md)
- [Org doctrine layer](../architecture/org-doctrine-layer.md)
