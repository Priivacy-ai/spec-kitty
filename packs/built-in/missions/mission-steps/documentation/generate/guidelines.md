# Generate Action — Governance Guidelines

These guidelines govern the implementation discipline for the **generate** phase of a documentation mission. The deliverable is the documentation content itself — Divio-typed pages written against the design's templates, plus any auto-generated reference output produced by configured generators. Generate is execution: the planning is already done.

---

## Core Authorship Focus

- Stay **faithful to plan.md** and the design's architecture. Generate is not the place to redesign; if the design has a defect, fix it in design and rerun.
- Honor the **Divio type contract** for every page: tutorial pages teach, how-to pages solve a stated task, reference pages describe a stable surface, explanation pages give context and rationale. Mixing voices inside one page is a defect.
- Drive every reference-style page from the **source of truth** — code, schemas, configuration. Hand-maintained reference drifts; generated reference stays aligned.
- Where the design deferred a Divio cell, leave it deferred. Filling deferred cells silently expands scope and breaks the discover-design-generate trace.

---

## Implementation Discipline

- **Invoke generators** as the design specifies — JSDoc, Sphinx, rustdoc, or other. Capture the exact command and configuration so a future author can rerun. Reference output that cannot be regenerated is technical debt.
- **Populate templates** completely. Replace every `[TODO: ...]` placeholder with real content; a published page with TODO markers is a quality-gate failure caught after the fact.
- **Link as designed**. Cross-links from reference into how-to, how-to into tutorial, explanation into the rest follow the design's link graph; do not invent ad-hoc links that the navigation does not anticipate.
- **Commit content in small, reviewable increments**. A single commit covering an entire section is hard to review and harder to revert.

---

## Source-of-Truth Alignment

- Reference content **must match** the underlying surface. If the surface changed during generate, update both — or fail the generate step and surface the drift to validate.
- Tutorials and how-tos must be **verbatim runnable**. Every command, every code block, every URL is something a reader will actually type. If it does not work in your environment, it will not work in the reader's.
- Where examples reference unstable APIs, mark them with the API's stability status so readers can self-protect.
- Living-documentation pages — those expected to evolve with the code — declare the cadence and the owner so the next generate cycle has a target.

---

## What This Phase Does NOT Cover

The generate action produces documentation content against the locked design. It does **not**:

- Reopen needs, audience, or scope (discover decisions).
- Reopen the gap analysis (audit decisions).
- Reopen the architecture or generator selection (design decisions).
- Decide whether the result is fit to publish (that is the validate action's job).

A generate output that includes new design decisions or revised audit findings is a leaked planning step. Keep the phases clean.

---

## Quality Gates

- Every required Divio cell from the design is filled or explicitly deferred with a recorded reason.
- Generator output is reproducible: the recorded command and configuration produce the same result in a clean environment.
- Reference content is aligned with the source of truth at the moment of generation.
- No `[TODO: ...]` placeholders remain in pages flagged for publication.
