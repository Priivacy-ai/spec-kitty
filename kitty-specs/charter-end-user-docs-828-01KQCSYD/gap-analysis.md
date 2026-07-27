# Gap Analysis — Charter End-User Docs Parity (#828)

**Mission**: `charter-end-user-docs-828-01KQCSYD`
**Date**: 2026-04-29
**Framework**: DocFX (toc.yml hierarchy, Markdown source)

---

## 1. Coverage Matrix (Divio Framework)

Key: `present-current` | `present-stale` | `missing` | `intentionally-deferred`

| Area | Tutorial | How-To | Reference | Explanation |
|---|---|---|---|---|
| Charter overview / mental model | missing | — | — | missing |
| Governance setup / bootstrap | — | present-stale | — | — |
| Charter synthesis / resynthesis | — | missing | — | missing |
| Unified charter bundle / canonical paths | — | missing | missing | missing |
| DRG-backed action context | — | — | missing | missing |
| Profile invocation / invocation trails | — | missing | missing | missing |
| `spec-kitty next` / mission composition | — | missing | — | missing |
| Retrospective learning loop | — | missing | present-stale | missing |
| CLI reference (Charter era) | — | — | present-stale | — |
| docs/2x/ section label | — | — | — | present-stale |
| Migration from older Charter docs | — | missing | — | — |
| Troubleshooting / Charter failure modes | — | missing | — | — |

---

## 2. Gap Priority Table

| Area | Divio Type | Priority | Planned Page | FR Coverage |
|---|---|---|---|---|
| Charter overview / mental model | Explanation | P0 | `docs/3x/charter-overview.md` | FR-003 |
| Charter overview / mental model | Tutorial | P0 | `docs/tutorials/charter-governed-workflow.md` | FR-017 |
| Charter synthesis / resynthesis | How-To | P0 | `docs/how-to/synthesize-doctrine.md` | FR-005 |
| Charter synthesis / resynthesis | Explanation | P0 | `docs/explanation/charter-synthesis-drg.md` | FR-003, FR-006 |
| Unified charter bundle / canonical paths | How-To | P0 | `docs/3x/governance-files.md` (reference) | FR-004 |
| Unified charter bundle / canonical paths | Reference | P0 | `docs/3x/governance-files.md` | FR-004 |
| Unified charter bundle / canonical paths | Explanation | P1 | `docs/explanation/charter-synthesis-drg.md` | FR-006 |
| DRG-backed action context | Reference | P0 | `docs/reference/charter-commands.md` | FR-012 |
| DRG-backed action context | Explanation | P1 | `docs/explanation/charter-synthesis-drg.md` | FR-003 |
| Profile invocation / invocation trails | How-To | P1 | `docs/how-to/run-governed-mission.md` | FR-008 |
| Profile invocation / invocation trails | Reference | P1 | `docs/reference/profile-invocation.md` | FR-007 |
| Profile invocation / invocation trails | Explanation | P1 | `docs/explanation/governed-profile-invocation.md` | FR-007 |
| `spec-kitty next` / mission composition | How-To | P1 | `docs/how-to/run-governed-mission.md` | FR-008 |
| `spec-kitty next` / mission composition | Explanation | P1 | `docs/explanation/charter-synthesis-drg.md` | FR-006 |
| Retrospective learning loop | How-To | P1 | `docs/how-to/use-retrospective-learning.md` | FR-010 |
| Retrospective learning loop | Reference | P1 | `docs/reference/retrospective-schema.md` (update) | FR-010 |
| Retrospective learning loop | Explanation | P1 | `docs/explanation/retrospective-learning-loop.md` | FR-010 |
| CLI reference (Charter era) | Reference | P1 | `docs/reference/charter-commands.md` (new) + `cli-commands.md` (update) | FR-012 |
| Governance setup / bootstrap | How-To | P2 | `docs/how-to/setup-governance.md` (update) | FR-004 |
| Migration from older Charter docs | How-To | P2 | `docs/migration/from-charter-2x.md` | FR-013 |
| Troubleshooting / Charter failure modes | How-To | P2 | `docs/how-to/troubleshoot-charter.md` | FR-014 |
| docs/2x/ section label | Explanation | P2 | `docs/2x/index.md` (archive notice) | FR-016 |

---

## 3. Source-of-Truth Notes

| Area | CLI Command / Source File |
|---|---|
| Charter overview / mental model | `uv run spec-kitty charter --help`; `uv run spec-kitty charter status`; `src/specify_cli/charter/` |
| Governance setup / bootstrap | `uv run spec-kitty charter interview --help`; `uv run spec-kitty charter generate --help`; `docs/how-to/setup-governance.md` (stale) |
| Charter synthesis / resynthesis | `uv run spec-kitty charter synthesize --help`; `uv run spec-kitty charter resynthesize --help`; `uv run spec-kitty charter lint --help`; `uv run spec-kitty charter bundle validate --help` |
| Unified charter bundle / canonical paths | `uv run spec-kitty charter bundle --help`; `.kittify/charter/` directory layout |
| DRG-backed action context | `uv run spec-kitty charter context --action <action> --json`; `src/specify_cli/next/` |
| Profile invocation / invocation trails | `uv run spec-kitty ask --help`; `uv run spec-kitty advise --help`; `uv run spec-kitty do --help`; `uv run spec-kitty profile-invocation complete --help`; `docs/trail-model.md` |
| `spec-kitty next` / mission composition | `uv run spec-kitty next --help`; `uv run spec-kitty next --json` |
| Retrospective learning loop | `uv run spec-kitty retrospect summary --help`; `uv run spec-kitty agent retrospect synthesize --help`; `docs/retrospective-learning-loop.md` (stale, root level) |
| CLI reference (Charter era) | `uv run spec-kitty charter <subcommand> --help` for all subcommands; `src/specify_cli/cli/` |
| Migration from 2.x | Breaking changes between 2.x and Charter-era 3.x; `docs/migration/` directory |

---

## 4. Key Invariants

These must hold in all generated content:

| # | Invariant | Implication for Docs |
|---|---|---|
| 1 | `charter.md` is the only human-edited governance file. All other files under `.kittify/charter/` (`governance.yaml`, `directives.yaml`, `metadata.yaml`, `library/*.md`) are auto-generated. | All docs must state this unambiguously. Never instruct users to edit auto-generated files. |
| 2 | DRG context compact-context limitation: when DRG context is too large, runtime falls back to compact-context mode. | Docs must name this limitation (issue #787 or current equivalent) and not promise full-context behavior unconditionally. |
| 3 | Custom mission retrospective execution: if current product supports it (verify against `mission-runtime.yaml`), docs must not claim it is deferred. | Verify before writing; do not assume deferred. |
| 4 | Documentation mission phases must match exactly what `mission-runtime.yaml` declares. | Do not invent or elide phases. |
| 5 | Profile invocation lifecycle: the `(profile, action, governance-context)` triple is the correct primitive. `ask`, `advise`, `do` are the three invocation modes. `profile-invocation complete` closes the trail. | All four must appear in docs. |
| 6 | Retrospective gate: in autonomous mode, retrospective cannot be skipped. In HiC mode, skipping requires explicit operator action with an audit trail. | Docs must reflect both modes. |

---

## 5. Planned Pages Summary

### New Pages (14)

1. `docs/3x/index.md` — Charter Era (3.x) landing hub
2. `docs/3x/charter-overview.md` — How Charter Works: Synthesis, DRG, and the Bundle
3. `docs/3x/governance-files.md` — Authoritative vs Generated Governance Files
4. `docs/tutorials/charter-governed-workflow.md` — Tutorial: Governed Charter Workflow End-to-End
5. `docs/how-to/synthesize-doctrine.md` — How to Synthesize and Maintain Doctrine
6. `docs/how-to/run-governed-mission.md` — How to Run a Governed Mission
7. `docs/how-to/use-retrospective-learning.md` — How to Use the Retrospective Learning Loop
8. `docs/how-to/troubleshoot-charter.md` — Troubleshooting Charter Failures
9. `docs/explanation/charter-synthesis-drg.md` — Understanding Charter: Synthesis, DRG, and Governed Context
10. `docs/explanation/governed-profile-invocation.md` — Understanding Governed Profile Invocation
11. `docs/explanation/retrospective-learning-loop.md` — Understanding the Retrospective Learning Loop
12. `docs/reference/charter-commands.md` — Charter CLI Reference
13. `docs/reference/profile-invocation.md` — Profile Invocation Reference
14. `docs/reference/retrospective-schema.md` — Retrospective Schema and Events Reference
15. `docs/migration/from-charter-2x.md` — Migrating from 2.x / Early 3.x Charter Projects

### Updated Pages (5 touchpoints)

1. `docs/toc.yml` — add `3x/` entry; label `2x/` as Archive
2. `docs/3x/toc.yml` — new toc for 3x section
3. `docs/2x/index.md` — add archive notice + forward pointer
4. `docs/docfx.json` — add `docs/3x/` and `docs/migration/` content sources
5. `docs/tutorials/toc.yml`, `docs/how-to/toc.yml`, `docs/explanation/toc.yml`, `docs/reference/toc.yml`, `docs/migration/toc.yml` — register new pages

### FR Coverage

| FR | Description | Pages Covering It |
|---|---|---|
| FR-003 | Charter mental model explanation | `docs/3x/charter-overview.md`, `docs/explanation/charter-synthesis-drg.md` |
| FR-004 | Governance setup | `docs/how-to/setup-governance.md` (update), `docs/3x/governance-files.md` |
| FR-005 | Charter synthesis / resynthesis | `docs/how-to/synthesize-doctrine.md` |
| FR-006 | DRG-backed context | `docs/explanation/charter-synthesis-drg.md` |
| FR-007 | Profile invocation | `docs/explanation/governed-profile-invocation.md`, `docs/reference/profile-invocation.md` |
| FR-008 | Governed mission run | `docs/how-to/run-governed-mission.md` |
| FR-010 | Retrospective learning loop | `docs/how-to/use-retrospective-learning.md`, `docs/explanation/retrospective-learning-loop.md`, `docs/reference/retrospective-schema.md` |
| FR-012 | CLI reference (Charter era) | `docs/reference/charter-commands.md`, `docs/reference/cli-commands.md` (update) |
| FR-013 | Migration guide | `docs/migration/from-charter-2x.md` |
| FR-014 | Troubleshooting | `docs/how-to/troubleshoot-charter.md` |
| FR-016 | 2x archive label | `docs/2x/index.md`, `docs/toc.yml` |
| FR-017 | End-to-end tutorial | `docs/tutorials/charter-governed-workflow.md` |
