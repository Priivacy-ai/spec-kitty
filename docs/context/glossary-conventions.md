---
title: Glossary Conventions
description: Authoring conventions for Spec Kitty's living glossary — source-of-truth precedence, policy/runtime layering, term status lifecycle, per-term entry schema, and runtime anchors.
doc_status: active
updated: '2026-08-10'
audience: docs/context/audience/internal/system-architect.md
type: reference
---
# Glossary Conventions

Canonical authoring conventions for Spec Kitty's living glossary. The glossary
is a living artifact organized by context domain; the per-domain term
definitions live in this directory (`docs/context/*.md`) and are indexed from
[the Context landing page](index.md). This page carries the shared conventions
those context pages follow.

## Source of Truth

When terms conflict, use this order:

1. Accepted product planning docs (PDR/PRD/ADR)
2. This glossary (policy language)
3. Runtime contracts and event logs (operational behavior)

## Architecture Framing

Spec Kitty uses two complementary layers:

1. Policy layer (glossary, specs, ADRs): defines language, intent, and invariants.
2. Runtime layer (CLI/events/projections): executes behavior and records what happened.

Use policy docs to answer "what should this mean?" and runtime artifacts to answer "what did the system do?"

## Domain Index

The canonical index of glossary context domains and their files lives on the
[Context landing page](index.md). Each filename (without `.md`) under
`docs/context/` is a valid context slug; see
[Contextive Glossary Integration](contextive-glossaries.md) for how those slugs
generate the IDE hover glossaries.

## Status Lifecycle

`candidate` -> `canonical` -> `deprecated` / `superseded`

## Term Entry Schema

Each glossary term table should include:

1. `Definition`
2. `Context`
3. `Status`
4. `Applicable to` (version scope, for example `` `1.x`, `2.x` ``)

## Runtime Anchors (`2.x`)

- `src/specify_cli/glossary/`
- `src/specify_cli/missions/glossary_hook.py`
- `src/specify_cli/missions/primitives.py`
- `src/specify_cli/cli/commands/glossary.py`

## PDR Alignment Notes

- Scoped glossary model: `spec_kitty_core`, `team_domain`, `audience_domain`, `mission_local`
- Strictness modes: `off`, `medium` (default), `max`
- Generation block policy: block unresolved high-severity semantic conflicts only
- History model: append-only glossary evolution events, replayable from canonical logs
