---
description: Explore a product idea and produce a structured vision document with feature map and build order.
---

# /spec-kitty.vision - Product Vision

**Version**: 0.14.1+
**Purpose**: Help the user articulate their product idea and produce a structured vision document with a prioritized feature map.

## Location

- Work in: **Project root** (not a worktree)
- Creates: `.kittify/memory/vision.md`
- This is a **product-level** document, not feature-level
- Lives alongside `constitution.md` in `.kittify/memory/`

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Philosophy

This command is **divergent, not convergent**. Unlike `/spec-kitty.specify` which narrows toward a formal spec, vision explores the idea space. The goal is to help the user think out loud and capture what emerges.

**Tone**: Curious friend, not product manager. No jargon. No "functional requirements" or "acceptance criteria" - those come later in specify.

**For vibe coders**: This may be the user's first interaction with spec-kitty. They might have nothing more than "I want to build a thing that does stuff." That's perfectly fine. Meet them where they are.

**Key principle**: The user should feel like they're having a conversation, not filling out a form. Your job is to listen, reflect, probe gently, and organize what emerges.

## Discovery Flow

### Phase 1: The Spark

Start with the most open question possible. If `$ARGUMENTS` is provided, use it as the starting point - reflect back what you understood and ask one follow-up.

Goal: Understand the core idea in the user's own words.

Questions to explore (pick what's natural, not all):
- "What's the idea? What made you think of this?"
- "If it existed right now, what would you do with it today?"
- "Who said 'someone should build this' and why?"

**One question at a time.** Let the user talk. Reflect back what you hear. Use their language, not yours.

### Phase 2: Day-in-the-Life

Ground the abstract idea in concrete reality.

- "Walk me through a real day where you'd use this."
- "What's the first thing you'd do when you open it?"
- "What's the thing you'd do most often?"

This phase often reveals what the user *actually* wants vs. what they *think* they want. Pay attention to the verbs they use - those become features.

### Phase 3: What Exists (and what's wrong with it)

- "What do you use today for this? Even if it's just a spreadsheet or your memory."
- "What's close to what you want but not quite right?"
- "What specifically frustrates you about current options?"

This reveals implicit requirements and anti-patterns to avoid.

### Phase 4: Shape & Priorities

Now start gently converging. Reflect back everything you've heard and sort it:

- What's **essential** (product doesn't make sense without it)
- What's **important but not first** (clearly needed, can come after MVP)
- What's **nice to have** (would be cool, explicitly deferred)
- What's **not this product** (anti-goals, scope boundaries)

Ask the user to confirm or adjust the prioritization.

### Phase 5: Feature Map

Break the vision into capability areas. These are NOT detailed specs - they're headlines with one-line descriptions and rough dependency ordering.

Group into:
- **MVP**: Must ship first for the product to be usable at all
- **Phase 2**: After MVP works, these make it good
- **Future**: Nice to have, explicitly deferred

For each feature area, note:
- One-line description
- Why it matters (ties back to vision)
- What it depends on (rough dependency)

### Phase 6: Summary & Confirmation

Present the full vision summary and ask:
- "Does this capture what you're thinking?"
- "Anything missing or wrong?"
- "Ready to write it down?"

## Scope Proportionality

- **Quick/simple product** (1-2 features, clear scope): Phases 1-2 might be 2-3 questions total. Don't over-interrogate a simple idea.
- **Medium product** (3-6 features): Full flow, 8-12 exchanges.
- **Complex product** (many features, unclear scope): Extended exploration, possibly 15+ exchanges.

**User signals to move faster**: "that's basically it", "pretty simple really", "let's just get started" - respect these and compress remaining phases.

## Output: vision.md

After confirmation, write to `.kittify/memory/vision.md`:

```markdown
# Product Vision: [Product Name]

> Created: [YYYY-MM-DD]
> Last updated: [YYYY-MM-DD]
> Status: Draft | Active | Revised

## The Idea

[1-2 paragraphs in plain, conversational language. No jargon. Written so anyone could understand what this product is and why it matters.]

## The Problem

[What pain does this solve? Why does this need to exist? What's broken or missing today?]

## Target User

[Who is this for? Be specific - not "everyone" but the actual person/people who would use this.]

## Day-in-the-Life Scenarios

[2-3 concrete examples of real usage, written as mini-narratives]

### Scenario 1: [Title]
[Short narrative of the user doing the thing]

### Scenario 2: [Title]
[Short narrative]

## What Exists Today

[Current alternatives and specifically what's wrong with them or what's missing]

## Core Principles

[Ranked list of what matters most about this product. These guide trade-off decisions in every feature.]

1. [Most important principle]
2. [Second]
3. [Third]

## Feature Map

### MVP (ship first)

| Feature | Description | Depends On |
|---------|-------------|------------|
| [name]  | [one line]  | -          |
| [name]  | [one line]  | [name]     |

### Phase 2 (makes it good)

| Feature | Description | Depends On |
|---------|-------------|------------|
| [name]  | [one line]  | [MVP feature] |

### Future (deferred)

| Feature | Description | Notes |
|---------|-------------|-------|
| [name]  | [one line]  | [why deferred] |

## Open Questions

[Things explicitly decided to figure out later. Not gaps - conscious deferrals.]

- [Question]: [Why it's okay to defer]

## Anti-Goals

[What this product is NOT. Boundaries that prevent scope creep.]

- NOT [thing]
- NOT [thing]
```

## Updating an Existing Vision

If `.kittify/memory/vision.md` already exists:

1. Read the existing vision
2. Ask the user what changed or what they want to update
3. Walk through only the relevant phases
4. Update the document, incrementing the "Last updated" date
5. Change status to "Revised" if significant changes
6. Preserve feature map entries that haven't changed; update or add as needed

## Integration

This document is referenced by:
- `/spec-kitty.next` - reads feature map to recommend next feature with copy-paste blurb
- `/spec-kitty.specify` - uses vision as context for feature discovery (avoids re-asking answered questions)
- `/spec-kitty.plan` - checks architectural decisions against product vision and principles
- `/spec-kitty.analyze` - validates feature alignment with vision

## Report

After writing, provide:
- Path to vision.md
- Feature count by phase (MVP: X, Phase 2: Y, Future: Z)
- Suggested next step: `/spec-kitty.next` or `/spec-kitty.constitution` or `/spec-kitty.specify [first MVP feature blurb]`

## General Guidelines

- Use the user's language, not product management jargon
- Keep the vision document readable by anyone - no technical terms unless the user introduced them
- The feature map uses plain names, not kebab-case slugs (those come during specify)
- Vision is a living document - it should be updated as the product evolves
- UTF-8 only (no smart quotes, em dashes, etc.)
- If the user wants to skip phases or move fast, let them. Capture what you have and note gaps in Open Questions.
