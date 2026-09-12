---
description: Design the documentation architecture — Divio allocation, navigation hierarchy, generators, and decision record
---
# /spec-kitty.design - Design Documentation Architecture

**Path reference rule:** When you mention directories or files, provide either the absolute path or a path relative to the project root (for example, `kitty-specs/<mission>/plan.md`). Never refer to a folder by name alone.

**In repos with multiple missions, always pass `--mission <handle>` to every spec-kitty command.** The `<handle>` can be the mission's `mission_id` (ULID), `mid8` (first 8 chars of the ULID), or `mission_slug`.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

**BEFORE PROCEEDING:** Verify you are working in the repository root checkout.

```bash
pwd
git branch --show-current
```

Expected: `pwd` ends in your project root; the branch is your mission branch, not `main`.

## What This Step Produces

```bash
spec-kitty plan --mission <handle> --json
```

This scaffolds `kitty-specs/<mission>/plan.md` from the documentation-domain plan template. The deliverable of this step is that file, **filled in** with the documentation architecture — not a blank scaffold.

## Goal

Lock the documentation architecture — the navigation hierarchy, the Divio type allocations, the chosen generators, and the ADR-shaped decisions that justify each major choice. The design plan is the contract the `generate` step implements faithfully.

## What to Do

1. **Design the architecture, not just a file layout.** State which Divio types live where, how readers move between them, and how the structure scales as content grows.

2. **Apply the Divio four-type system intentionally** — tutorial, how-to, reference, explanation. Each type has a distinct reader stance and writing voice; collapsing types into one section produces docs that satisfy no audience.

3. **Lock the Divio allocation.** For each area from `spec.md`, declare which of `tutorial`, `how-to`, `reference`, `explanation` are required, and which are deferred. Justify every deferral against the discover scope.

4. **Design the navigation hierarchy** — the top-level information architecture (sections, sub-sections, cross-links) — so a reader can locate any documented topic in two or three clicks.

5. **Select generators** — JSDoc / Sphinx / rustdoc / other — based on the source language and existing build infrastructure. Record the choice as an ADR; an ad-hoc generator pick becomes an ad-hoc maintenance burden.

6. **Define templates and shapes** — the canonical shape for each Divio type (front-matter, section headings, code-block conventions). The `generate` step writes against these shapes; without them, every author re-invents structure.

7. **Design the cross-link strategy** — how reference entries link to how-tos, how tutorials link to explanations, how explanations link back to reference. The link graph is part of the architecture, not an afterthought.

8. **Document each major design choice as an ADR-shaped decision record**: the choice, the alternatives considered, the rationale, and the trade-offs accepted. Cite established conventions (the Divio framework, generator-native idioms) rather than inventing structure; where you deviate, say why.

9. **Stay faithful to the discover `spec.md`.** The audience, scope, and goals from `discover` bound the design. If the design needs to extend scope, that's a re-scoping decision that goes back to `discover` — not a silent expansion.

## Success Criteria

- Every area in scope has an explicit Divio-type allocation in `plan.md`, with deferrals justified.
- The navigation hierarchy is concrete: a reader handed the architecture can locate where new content belongs without asking.
- Each major choice (generator, hierarchy shape, cross-link strategy) is recorded as an ADR-shaped decision.
- The design honors the discover spec — no silent scope expansion, no audience drift.

## Handoff

This step locks the documentation architecture and decisions only. It does **not** re-open the documentation needs, audience, or iteration mode (`discover` decisions, already locked), re-do the gap audit (`audit`'s job, already complete), author or fill any documentation content (`generate`'s job), or validate completed content against quality gates (`validate`'s job). A design document that already includes drafted tutorial steps or filled reference entries is a leaked generation — keep the phases clean.
