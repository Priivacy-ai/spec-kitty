---
title: WP & Op Schema Model — Formalising Work-Package and Op Records
description: 'Design idea: replace markdown-with-frontmatter WP files (and the facts-only Op record) with a code-owned logical model + schema, persisted as YAML/rendered markdown, extending the model-first doctrine-schema precedent to execution and op artefacts.'
doc_status: idea
updated: '2026-07-16'
---
# WP & Op Schema Model

| Field | Value |
|---|---|
| Date | 2026-07-16 |
| Stage | Idea — pending research grounding |
| Author | Operator (via Spec Kitty session `SK_DESIGN`) |
| Branch | `design/wp-op-schema-model` (isolated worktree) |
| Grounds against | model-first doctrine schema precedent, degodding roadmap, mission-type→doctrine migration, Op record schema v2 |
| Related | [model-first-schema-generation.md](model-first-schema-generation.md), `src/specify_cli/invocation/record.py`, `src/specify_cli/core/wps_manifest.py`, `src/specify_cli/task_metadata_validation.py` |

> **This is an idea note, not a decision.** It captures intent verbatim from the
> originating session and frames the research questions. It is deliberately
> unresolved on trade-offs; the accompanying research squad grounds it against
> the code as-is, the roadmap/vision, and the existing ADRs before any
> spec/plan work is contemplated.

---

## The itch

Recent and in-flight roadmap movement — **degodding** (god-module decomposition),
**`specify_cli` cleanup**, and **moving mission-type configuration into doctrine** —
has surfaced that the current representation of **Work-Package (WP) files** is
lacklustre. Today a WP is a **markdown file with a YAML frontmatter block**
(`kitty-specs/<mission>/tasks/WP##.md`): structured metadata up top, free-prose
body below.

Observed pain points with that format:

1. **Hash / content-address mismatch churn.** Minor, semantically-inert edits
   (e.g. flipping a task to complete) shift content and trip
   hashcode-mismatch warnings/errors. The content-address machinery treats the
   whole file as one opaque blob, so bookkeeping mutations are indistinguishable
   from substantive ones.
2. **Context sizing / retrieval friction.** The prose-heavy body is expensive to
   load and hard to slice; there is no clean way to pull "just the scope" or
   "just the acceptance criteria" without parsing free text.
3. **Inconsistencies.** Free-form bodies drift in structure across missions;
   there is no enforced shape, so downstream tooling parses defensively.
4. **Duplicated information.** The same facts live in **both** the frontmatter
   metadata **and** the body prose (title, anchors, requirement refs, scope
   headings), and the two can diverge.

## The idea

With WP **prompt templates** shifting into **doctrine elements** (the
mission-type→doctrine migration), this is an opportune moment to revamp the WP
representation into a **formal schema format**:

- A **code-owned logical model** (Pydantic, matching the existing model-first
  doctrine-schema pattern) is the **single source of truth** for a WP's shape.
- A **schema** + **schema checks** validate WP records — no hand-authored,
  drift-prone structure.
- These models live inside the code logic and are used to **create, update, and
  process** WP records (not re-parsed ad hoc at each call site).
- On disk, records still **render to markdown** for human readability and
  dashboard display — but the **authoritative representation is structured**
  (YAML / model), and the markdown is a **derived view**, not the source.

The distinction that unblocks the hash-churn problem: separate **semantic
content** (scope, requirements, acceptance) from **mutable bookkeeping** (lane,
task-complete flags, history) so a status flip does not perturb the
content-addressed identity of the semantic record.

## Extension: Op records should carry "why & what", not just "something was done"

The same logical-model + schema approach applies to the **Op run-type** (ad-hoc
dispatch / `profile-invocation`). Today an Op record
(`src/specify_cli/invocation/record.py`, schema v2) captures the **facts of an
invocation** — `request_text`, `action`, `mode_of_work`, `outcome`, `closed_by`
— i.e. *that* something was dispatched and *how* it closed. It does **not**
persist a structured account of the **why and what** — the scope the Op set for
itself, the intent, the change surface, the reasoning. It stores that something
was done, not what was undertaken and to what end.

This is **incongruent with Spec Kitty's core vision** (specifications ahead of
implementation; traceability from intent to artefact) and it **blurs the line
between `ad-hoc` and `op`**: if an Op leaves no more trace of intent than a raw
ad-hoc action, the governance ceremony buys little.

Applying the **same schema model** to Op scope would let an Op carry a
lightweight, structured **intent + scope + outcome** record — a "small WP for a
non-mission action" — restoring the traceability that distinguishes a governed
Op from an ungoverned ad-hoc edit.

## Why now (timing)

- **WP templates → doctrine.** The prompt templates that shape WP files are
  being lifted into doctrine artefacts; changing the *representation* at the
  same moment avoids a second disruptive migration later.
- **Degodding / `specify_cli` cleanup.** Numerous call sites parse WP frontmatter
  and bodies today (`wps_manifest.py`, `task_metadata_validation.py`,
  `status/*`, `dependency_parser.py`, …). A single code-owned model is exactly
  the kind of consolidation the degodding roadmap favours (one authority, ports
  over scattered parsing).
- **Precedent exists.** [Model-first schema generation](model-first-schema-generation.md)
  already made **Pydantic models the single source of truth for all 10 doctrine
  YAML schemas**, with `scripts/generate_schemas.py --check` as a drift gate.
  This idea extends that proven pattern from *doctrine* artefacts to *execution*
  (WP) and *op* artefacts.

## Explicitly out of scope for the idea (for the squad to confirm/deny)

- A specific migration mechanism or backwards-compat window.
- Whether markdown remains round-trippable or becomes strictly one-way (derived).
- The exact content-address boundary (what counts as semantic vs bookkeeping).
- Any commitment to a version number or milestone.

## Research questions to ground this

1. **Code as-is.** Where and how are WP files created, mutated, hashed, and
   parsed today? Enumerate the call sites and the current content-address /
   hash-mismatch machinery. What does the frontmatter↔body duplication actually
   cost? How does the Op record (schema v2) store intent today, and what is
   genuinely missing vs. the WP shape?
2. **Roadmap / vision alignment.** Does this fit the degodding, `specify_cli`
   cleanup, and mission-type→doctrine directions — or does it collide with
   in-flight work (e.g. runtime/state overhaul #1619, infra-logic separation
   #2173, doctrine extensibility)? Is now genuinely the right seam?
3. **ADR / precedent.** Which existing ADRs bind here (doctrine-layer merge
   semantics, shared-package boundary, model-first schema generation, status
   append-only event model)? Does the append-only status event log already solve
   the "bookkeeping churn" half, meaning the WP file only needs to shed its
   mutable fields rather than adopt a new store?
4. **Feasibility & risk.** Is a structured-authoritative / markdown-derived split
   realistic given human-editing workflows and the many agents that read WP
   files? What breaks? What is the smallest first slice that de-risks the rest?

## Next step

The research squad (below) grounds questions 1–4. Its synthesis determines
whether this becomes a spec, a narrower slice, or a documented "not now".
