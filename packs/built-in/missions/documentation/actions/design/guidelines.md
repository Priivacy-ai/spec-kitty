# Design Action — Governance Guidelines

These guidelines govern the quality and rigor standards for the **design** phase of a documentation mission. The deliverable is a documentation architecture — the navigation hierarchy, the Divio type allocations, the chosen generators, and the ADR-shaped decisions that justify each major choice. The design plan is the contract the generate phase implements faithfully.

---

## Core Authorship Focus

- Design the documentation **architecture**, not just a file layout. The architecture states which Divio types live where, how readers move between them, and how the structure scales as content grows.
- Apply the **Divio four-type system** intentionally — tutorial, how-to, reference, explanation. Each type has a distinct reader stance and writing voice; collapsing types into one section produces docs that satisfy no audience.
- Document each major design choice as an **ADR-shaped decision record**: the choice, the alternatives considered, the rationale, and the trade-offs accepted. A design without recorded decisions is a design that cannot be revisited.
- Stay faithful to the **discover spec**: the audience, scope, and goals from discover bound the design. If the design needs to extend scope, that is a re-scoping decision that goes back to discover, not a silent expansion.

---

## Architecture Components to Lock Down

- **Divio allocation** — for each area, declare which of `tutorial`, `how-to`, `reference`, `explanation` are required, and which are deferred. Justify deferrals against the discover scope.
- **Navigation hierarchy** — the top-level information architecture (sections, sub-sections, cross-links). A reader can locate any documented topic in two or three clicks.
- **Generator selection** — choose JSDoc / Sphinx / rustdoc / other based on the source language and existing build infrastructure. Document the choice as an ADR; ad-hoc generator picks become ad-hoc maintenance burden.
- **Templates and shapes** — the canonical shape for each Divio type (front-matter, section headings, code-block conventions). Generate phase writes against these shapes; without them, every author re-invents structure.
- **Cross-link strategy** — how reference entries link to how-tos, how tutorials link to explanations, how explanations link back to reference. The link graph is part of the architecture.

---

## Decision Documentation Discipline

- Treat generator selection, hierarchy choice, and Divio-allocation trade-offs as **decisions** worth recording. Use the ADR pattern: context, options, choice, consequences.
- Cite established conventions (Divio framework, generator-native idioms) rather than inventing structure. Where you deviate, document why.
- Pre-register naming conventions and section shapes. Adjusting conventions mid-generate produces inconsistent docs.

---

## What This Phase Does NOT Cover

The design action locks the documentation architecture and decisions. It does **not**:

- Re-open the documentation needs, audience, or iteration mode (those are discover decisions, already locked).
- Re-do the gap audit (that is the audit action's job, already complete).
- Author or fill any documentation content (that is the generate action's job).
- Validate completed content against quality gates (that is the validate action's job).

A design document that already includes drafted tutorial steps or filled reference entries is a leaked generation. Keep the phases clean.

---

## Quality Gates

- Every area in scope has an explicit Divio-type allocation, with deferrals justified.
- The navigation hierarchy is concrete: a reader can be handed the architecture diagram and locate where new content belongs without asking.
- Each major choice (generator, hierarchy shape, cross-link strategy) is recorded as an ADR-shaped decision.
- The design honors the discover spec — no silent scope expansion, no audience drift.
