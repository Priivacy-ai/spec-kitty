# Information Architecture: Charter End-User Docs Parity (#828)

**Phase**: 1 — Design
**Date**: 2026-04-29
**Mission**: `charter-end-user-docs-828-01KQCSYD`

This document defines the IA structure, page map, TOC strategy, and linking conventions for the documentation PR. It serves as the authoritative design contract that the Generate phase implements.

---

## 1. IA Strategy (resolved)

**Hybrid (C)**: `docs/3x/` is the Charter-era hub for current mental model content and deep product surfaces. The main Divio sections (`tutorials/`, `how-to/`, `reference/`, `explanation/`) are updated so users who enter via natural Divio entry points find Charter workflows without needing to know about version sections.

`docs/2x/` is relabeled as a historical archive — no content is deleted, but `docs/2x/index.md` gains a clear notice and forward pointer to `docs/3x/`.

---

## 2. Updated Root `docs/toc.yml`

```yaml
- name: Home
  href: index.md
- name: Tutorials
  href: tutorials/
- name: How-To Guides
  href: how-to/
- name: Reference
  href: reference/
- name: Explanation
  href: explanation/
- name: 3.x Docs (Current)
  href: 3x/
- name: 1.x Docs
  href: 1x/
- name: 2.x Docs (Archive)
  href: 2x/
```

Changes: add `3x/` entry before `1x/`; change `2.x Docs` label to `2.x Docs (Archive)`; ensure `retrospective-learning-loop.md` is NOT in the root toc (it moves to `explanation/`).

---

## 3. Page Map

### New: `docs/3x/` (Charter-era hub)

| File | Title | Divio shape | Status |
|---|---|---|---|
| `docs/3x/index.md` | Charter Era (3.x) — Current Docs | landing/hub | NEW |
| `docs/3x/charter-overview.md` | How Charter Works: Synthesis, DRG, and the Bundle | explanation | NEW |
| `docs/3x/governance-files.md` | Authoritative vs Generated Governance Files | reference | NEW |
| `docs/3x/toc.yml` | toc for 3x section | toc | NEW |

`docs/3x/index.md` purpose: orient readers arriving via the nav ("you are here — current product"), briefly describe the Charter model, then link to each Divio section for tasks. Not a deep-dive itself.

`docs/3x/charter-overview.md` purpose: explain the DRG-backed governance context model, the charter bundle, synthesis flow, and how runtime context injection works. This is the canonical mental model page referenced by all other new pages.

`docs/3x/governance-files.md` purpose: table of every `.kittify/charter/` file, what it is, who writes it (human vs auto-generated), and what happens if you edit an auto-generated file.

### New/Updated: `docs/tutorials/`

| File | Title | Status | FR coverage |
|---|---|---|---|
| `docs/tutorials/charter-governed-workflow.md` | Tutorial: Governed Charter Workflow End-to-End | NEW | FR-017 |

Tutorial arc: initialize governance → validate bundle → synthesize doctrine → run one governed mission action (`spec-kitty next`) → view retrospective summary → next-step learning. No assumed knowledge of the Charter model. Links to `docs/3x/charter-overview.md` for background.

### New/Updated: `docs/how-to/`

| File | Title | Status | FR coverage |
|---|---|---|---|
| `docs/how-to/setup-governance.md` | How to Set Up Project Governance | UPDATE | FR-004 |
| `docs/how-to/synthesize-doctrine.md` | How to Synthesize and Maintain Doctrine | NEW | FR-005 |
| `docs/how-to/run-governed-mission.md` | How to Run a Governed Mission | NEW | FR-008 |
| `docs/how-to/use-retrospective-learning.md` | How to Use the Retrospective Learning Loop | NEW | FR-010 |
| `docs/how-to/troubleshoot-charter.md` | Troubleshooting Charter Failures | NEW | FR-014 |

`setup-governance.md` update scope: add Charter bundle validation step; update to current `spec-kitty charter interview` -> `generate` -> `lint` -> `synthesize` -> `bundle validate` flow; remove "Spec Kitty 2.x" prerequisite; note synthesis vs sync distinction.

`synthesize-doctrine.md` scope: cover `charter status`, `charter lint`, `charter synthesize`, `charter resynthesize`, and `charter bundle validate`; synthesis vs resynthesis; dry-run vs apply; idempotency; provenance; staged recovery; what to do when the bundle is stale.

`run-governed-mission.md` scope: `spec-kitty next --agent <agent>`; composed step contract; how Charter context is injected; blocked decisions; how to read `next --json` output.

`use-retrospective-learning.md` scope: `retrospect summary`; `agent retrospect synthesize --mission <mission>` default dry-run; `agent retrospect synthesize --mission <mission> --apply`; proposal kinds; conflict resolution; staleness; provenance; HiC vs autonomous behavior; skip semantics.

`troubleshoot-charter.md` scope: stale bundle (symptoms, fix); missing doctrine (symptoms, fix); compact-context limitation (what it is, workaround, issue link if open); retrospective gate failure (symptoms, fix); synthesizer rejection (exit codes, fix).

### New/Updated: `docs/explanation/`

| File | Title | Status | FR coverage |
|---|---|---|---|
| `docs/explanation/charter-synthesis-drg.md` | Understanding Charter: Synthesis, DRG, and Governed Context | NEW | FR-003, FR-006 |
| `docs/explanation/governed-profile-invocation.md` | Understanding Governed Profile Invocation | NEW | FR-007 |
| `docs/explanation/retrospective-learning-loop.md` | Understanding the Retrospective Learning Loop | NEW (split from root) | FR-010 |

`charter-synthesis-drg.md` scope: what the charter bundle is; how DRG edges are computed; bootstrap vs compact context; why the authoritative-vs-generated distinction matters; known limitations (compact context #787 or current). This is the "why" complement to `docs/3x/charter-overview.md` (which is the "what").

`governed-profile-invocation.md` scope: the `(profile, action, governance-context)` primitive; `ask`, `advise`, `do` modes; profile invocation lifecycle; `profile-invocation complete`; evidence/artifact correlation; invocation trail model; reference to `docs/trail-model.md`.

`retrospective-learning-loop.md` scope: why retrospectives exist; the gate model (autonomous mandatory, HiC optional with audit); proposal lifecycle; synthesizer role. Factual/explanatory counterpart to the how-to guide. Root-level `docs/retrospective-learning-loop.md` becomes a redirect stub.

### New/Updated: `docs/reference/`

| File | Title | Status | FR coverage |
|---|---|---|---|
| `docs/reference/cli-commands.md` | CLI Reference | UPDATE | FR-012 |
| `docs/reference/charter-commands.md` | Charter CLI Reference | NEW | FR-012 |
| `docs/reference/profile-invocation.md` | Profile Invocation Reference | NEW | FR-007 |
| `docs/reference/retrospective-schema.md` | Retrospective Schema and Events Reference | NEW | FR-010 |

`cli-commands.md` update scope: add a Charter-era section with links to `charter-commands.md`, `profile-invocation.md`, and summary entries for `next`, `profiles`, `ask`, `advise`, `do`, `profile-invocation`, `mission`, `glossary`, `retrospect`, and `agent retrospect`. Do not duplicate flag tables — cross-link.

`charter-commands.md` scope: one section per command: `charter interview`, `charter generate`, `charter context`, `charter status`, `charter sync`, `charter synthesize`, `charter resynthesize`, `charter lint`, and `charter bundle validate` (verify each exists). Each section: description, flags, example, and expected output. All flags verified against `uv run spec-kitty charter <subcommand> --help`.

`profile-invocation.md` scope: `ask`/`advise`/`do` flag semantics; `profile-invocation complete` syntax; invocation trail fields; lifecycle states; example JSON output.

`retrospective-schema.md` scope: `retrospective.yaml` field schema; proposal kinds and required fields; status event fields for retrospective; exit codes for synthesizer.

### New: `docs/migration/`

| File | Title | Status | FR coverage |
|---|---|---|---|
| `docs/migration/from-charter-2x.md` | Migrating from 2.x / Early 3.x Charter Projects | NEW | FR-013 |

Scope: changes between 2.x and Charter-era 3.x that affect operators; new paths and commands; what to re-run after upgrade; known migration failures and fixes.

### Archive update: `docs/2x/`

| File | Change |
|---|---|
| `docs/2x/index.md` | Add archive notice: "This section documents Spec Kitty 2.x behavior. It is preserved for reference. For current 3.x Charter documentation, see [3.x Docs](../3x/)." |

---

## 4. Linking Strategy

**Rule 1 — Hub-and-spoke**: Every new Divio page opens with a one-line context link to `docs/3x/charter-overview.md` (for mental model) and closes with a "See also" block pointing to related pages in other Divio sections.

**Rule 2 — No duplication**: When a concept (e.g. DRG edge semantics) is explained in an explanation page, how-to pages use a cross-link rather than restating. Reference pages define syntax only.

**Rule 3 — Retrospective root stub**: `docs/retrospective-learning-loop.md` becomes a redirect stub with a single line: "This page has moved to [explanation/retrospective-learning-loop.md](explanation/retrospective-learning-loop.md)." This preserves any existing deep links.

**Rule 4 — CLI flag sourcing**: CLI reference content comes from `--help` output, not from reading source code directly. Flag descriptions must match the running CLI exactly.

**Rule 5 — Issue links for limitations**: Any known limitation must include a link to the open issue (e.g., compact-context limitation → link #787 or current equivalent). If the issue is closed and the limitation is resolved, omit the limitation claim.

---

## 5. TOC Registration Checklist

Every new page must appear in the toc.yml for its directory:

| Directory | toc.yml to update |
|---|---|
| `docs/3x/` | `docs/3x/toc.yml` (new) |
| `docs/tutorials/` | `docs/tutorials/toc.yml` |
| `docs/how-to/` | `docs/how-to/toc.yml` |
| `docs/explanation/` | `docs/explanation/toc.yml` (check if toc.yml exists; create if not) |
| `docs/reference/` | `docs/reference/toc.yml` |
| `docs/migration/` | `docs/migration/toc.yml` (check if toc.yml exists; create if not) |
| Root `docs/` | `docs/toc.yml` — add 3x/ entry; update 2.x label |

---

## 6. Page Count Summary

| Category | Count |
|---|---|
| New pages | 14 |
| Updated pages | 5 (`setup-governance.md`, `cli-commands.md`, `docs/2x/index.md`, `docs/toc.yml` + section toc.yml files, `docs/retrospective-learning-loop.md` → stub) |
| Total touchpoints | 19 |
