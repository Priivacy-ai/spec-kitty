---
name: spk-mission-research
description: "Operate pre-spec or in-mission research workflows while keeping findings tied to mission decisions."
---

# spk-mission-research

Use this skill when a mission needs discovery, external facts, design precedent,
technical investigation, or decision support before specification or planning.

## Flow

1. Invoke `/spec-kitty.research` when the mission supports a research phase.
2. Write findings as decision-ready evidence, not a loose reading list.
3. Record assumptions, source quality, and unresolved questions.
4. Return findings to `spk-mission-specify` or `spk-mission-plan`.

## Rule

Research is not a substitute for a spec. It should narrow uncertainty enough for
the next mission phase.
