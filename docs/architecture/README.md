---
title: Architecture
description: 'The canonical architecture corpus landing page: the two-surface boundary rule (architecture/ vs docs/) and how living architecture sits above versioned history.'
doc_status: active
updated: '2026-06-12'
related:
- docs/architecture/ARCHITECTURE_DOCS_GUIDE.md
- docs/architecture/NAVIGATION_GUIDE.md
- docs/architecture/diagrams/01_context/README.md
- docs/architecture/diagrams/02_containers/README.md
- docs/architecture/diagrams/03_components/README.md
---
# Architecture

This directory is the canonical architecture corpus for Spec Kitty.

## Boundary rule (single source of truth)

Two top-level surfaces, two jobs — they never duplicate each other:

| Surface | Holds | Authority |
|---|---|---|
| `architecture/` | **Decisions & models** — ADRs, C4 diagrams, vision, audits, calibration | Authoritative; changes are deliberate and reviewed |
| `docs/` | **Consumption** — Divio tutorials, how-tos, reference, explanation | Reader-facing; narrates and links *up* to architecture |

- **`architecture/` = decisions & models.** ADRs, the C4 model, vision, audits, and
  calibration live here. This is the deliberately-changed source of truth.
- **`docs/` = consumption.** `docs/explanation/` narrates the "why" and **links up to
  architecture — it never duplicates architecture narrative.** When the two overlap,
  architecture wins; explanation points at it.
- **C4 stays in `architecture/`** (under `diagrams/`), not in `docs/`.
- **Vision is an architecture concern** — there is no `docs/vision/`. Forward intent
  lives in `architecture/vision/`.
- **Terminology canon lives in the top-level `glossary/`** surface (promoted out of
  `architecture/` — see the project-root `glossary/README.md`). Architecture docs
  *reference* glossary terms; they do not host a second glossary.

## Living architecture at the top, versioned history beneath

`architecture/` follows a **living-at-top + versioned-history-beneath** model:

- **Top-level living surfaces** describe the architecture *now and going forward*:
  - `architecture/vision/` — current + future vision (forward intent; may change).
  - `architecture/diagrams/` — the living C4 model (`01_context/`, `02_containers/`,
    `03_components/`), hand-authored Markdown + Mermaid.
  - `architecture/audience/` — stakeholder/persona views.
- **Per-version directories** (`architecture/1.x/`, `architecture/2.x/`,
  `architecture/3.x/`) are the **traceability record** — each carries
  `adr/ vision/ research/` for its era and is treated as immutable history.
- **Current-era ADRs keep landing in `architecture/3.x/adr/`.** The living top-level
  surfaces synthesize and *reference* those era-stamped ADRs; the ADRs themselves stay
  immutable and dated.

### Decay rule (so the layout can't re-drift)

When a piece of the living top-level architecture is **no longer current or future**,
it is **demoted into its version directory** — moved from `architecture/vision/`
(or a refreshed `architecture/diagrams/` snapshot) into
`architecture/<version>/vision/` (or `…/research/`). History accrues by version;
**nothing is deleted.** This decay path is the only sanctioned way content leaves the
living top level, which keeps the top-level surface honestly "current" over time.

## Structure

| Path | Purpose |
|---|---|
| `architecture/vision/` | Living current + future architecture vision (forward intent) |
| `architecture/diagrams/` | Living C4 model — `01_context/`, `02_containers/`, `03_components/` |
| `architecture/audience/` | Persona catalog for architecture audiences and actor links |
| `architecture/3.x/` | Current track (3.x) — `adr/`, `vision/`, `research/` (current-era ADRs land here) |
| `architecture/2.x/` | Prior track (2.x) — frozen snapshot incl. the 2.x C4 and `adr/ vision/ research/` |
| `architecture/1.x/` | Legacy track (1.x) — frozen, incl. 1.x ADRs and notes |
| `architecture/adrs/` | Backward-compatibility links to moved 1.x ADR files (legacy compat shim) |
| `architecture/audits/` | Architecture audits and assessments |
| `architecture/calibration/` | Per-mission-type calibration notes |
| `architecture/assessments/` | Code-as-a-crime-scene and similar assessments |
| `architecture/adr-template.md` | Shared ADR template used by all tracks |

> **Layout is structure, not policy.** Directory layout here intentionally encodes only
> the boundary + version + decay rules. It does **not** encode per-artifact tiering: a
> future optional per-artifact *tier* (upstream `#1843`), if introduced, is a **declared
> field** on artifacts — never a directory level. New tier semantics must not be expressed
> by adding a tier directory under `architecture/`.

## Versioned ADR Locations

- Current-era (3.x) ADRs: `architecture/3.x/adr/` — **canonical for the current track.**
- 2.x ADRs: `architecture/2.x/adr/` (frozen 2.x-era decisions).
- 1.x ADRs: `architecture/1.x/adr/`.
- Legacy 1.x path compatibility: `architecture/adrs/`.

When a coding agent needs **architectural intent for a change today**, the current-era
ADR surface is `architecture/3.x/adr/`; older era directories carry the decisions made
in those eras and remain authoritative for that history.

## C4 model

The living C4 lives under `architecture/diagrams/` with stable numbered levels:

1. [`architecture/diagrams/01_context/README.md`](diagrams/01_context/README.md) — system boundary and external interactions.
2. [`architecture/diagrams/02_containers/README.md`](diagrams/02_containers/README.md) — runtime/governance container responsibilities.
3. [`architecture/diagrams/03_components/README.md`](diagrams/03_components/README.md) — component-level behavior sequences.

C4 is **hand-authored Markdown + Mermaid** (renders on GitHub, no build tooling).
The 2.x C4 under `architecture/2.x/{01_context,02_containers,03_components}/` is kept
frozen as the 2.x snapshot; the living copy under `diagrams/` is the one that is
refreshed against the current domain model. (Generated-C4 tooling is deferred — `#1812`.)

## Creating a New ADR

Use the shared template, landing current-era ADRs in the 3.x track:

```bash
cp architecture/adr-template.md architecture/3.x/adr/YYYY-MM-DD-N-your-decision.md
```

Use `architecture/1.x/adr/` or `architecture/2.x/adr/` only when documenting legacy
behavior for those eras.

## Find ADRs

```bash
ls -1 architecture/3.x/adr | sort
ls -1 architecture/2.x/adr | sort
ls -1 architecture/1.x/adr | sort
rg -n "Status:|Decision Outcome|Technical Story" architecture/3.x/adr architecture/2.x/adr architecture/1.x/adr
```

## See also

- Project terminology canon: project-root [`glossary/README.md`](../glossary/README.md)
- [`architecture/ARCHITECTURE_DOCS_GUIDE.md`](ARCHITECTURE_DOCS_GUIDE.md)
- [`architecture/NAVIGATION_GUIDE.md`](NAVIGATION_GUIDE.md)
