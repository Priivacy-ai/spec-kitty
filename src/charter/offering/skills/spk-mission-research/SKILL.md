---
name: spk-mission-research
description: "Operate pre-spec or in-mission research workflows while keeping findings tied to mission decisions."
---

# spk-mission-research

Use this skill when a mission needs discovery, external facts, design precedent,
technical investigation, or decision support.

## Flow

1. Use a research mission for pre-spec discovery workflows.
2. Invoke `/spec-kitty.research` only after `/spec-kitty.plan`; it scaffolds
   research artifacts from an existing plan.
3. Write findings as decision-ready evidence, not a loose reading list.
4. Record assumptions, source quality, and unresolved questions.
5. Return findings to `spk-mission-specify` or `spk-mission-plan`.

## Rule

Research is not a substitute for a spec. It should narrow uncertainty enough for
the next mission phase.
