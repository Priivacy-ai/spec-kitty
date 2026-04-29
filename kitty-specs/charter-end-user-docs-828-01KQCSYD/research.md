# Research: Charter End-User Docs Parity (#828)

**Phase**: 0 — Gap Analysis and Source-of-Truth Audit
**Date**: 2026-04-29
**Mission**: `charter-end-user-docs-828-01KQCSYD`

---

## Scope

This document records the findings of the discovery and audit phases. It maps every #828-required documentation area to its current state in `docs/`, classifies each cell by Divio type and coverage status, and names the source-of-truth for generating or updating each page.

---

## 1. Docs Framework

**Decision**: DocFX (toc.yml hierarchy, Markdown source)
**Rationale**: The repository has `docs/docfx.json` and hierarchical `toc.yml` files at each directory level. No MkDocs or Sphinx config found at the repo root.
**Alternatives considered**: MkDocs (not present), Sphinx (not present).
**Implications**: New pages must be registered in the correct `toc.yml` file at their directory level, not in a global mkdocs.yml. DocFX link validation (`docfx build --serve`) is the authoritative link checker.

---

## 2. Divio Coverage Matrix

Key: `present-current` | `present-stale` | `missing` | `intentionally-deferred`

| Area | Tutorial | How-To | Reference | Explanation | Notes |
|---|---|---|---|---|---|
| Charter overview / mental model | missing | — | — | missing | No current-state overview exists. `docs/2x/doctrine-and-charter.md` describes 2.x only. |
| Governance setup / bootstrap | — | present-stale | — | — | `docs/how-to/setup-governance.md` has "Spec Kitty 2.x installed" prerequisite; covers interview/generate/sync only; no bundle validation or synthesis. |
| Charter synthesis / resynthesis | — | missing | — | missing | No synthesis, dry-run, apply, status, lint, provenance, or recovery docs exist. |
| Unified charter bundle / canonical paths | — | missing | missing | missing | No bundle validation docs. No canonical path reference. |
| DRG-backed action context | — | — | missing | missing | No docs on DRG edges, action identities, bootstrap vs compact context. |
| Profile invocation / invocation trails | — | missing | missing | missing | No docs on ask/advise/do, profile-invocation complete, lifecycle, or trails. |
| `spec-kitty next` / mission composition | — | missing | — | missing | `docs/reference/missions.md` exists but predates Charter composition. `docs/how-to/run-external-orchestrator.md` is tangentially related. |
| Research mission under Charter | — | missing | — | — | No research-mission-specific docs exist. |
| Documentation mission under Charter | — | missing | — | present-stale | `docs/explanation/documentation-mission.md` exists but describes old phase names. |
| Custom missions / retrospective marker | — | missing | — | missing | No custom mission docs. |
| Glossary as doctrine / runtime surface | — | missing | — | missing | `docs/how-to/manage-glossary.md` exists but predates Charter glossary runtime integration. |
| Retrospective learning loop | — | missing | present-stale | missing | `docs/retrospective-learning-loop.md` exists at root level, has `TODO: register in docs nav` marker, not in toc.yml, covers HiC/autonomous behavior but lacks synthesizer dry-run/apply details. |
| Cross-mission retrospective summary | — | missing | missing | missing | Not documented. |
| Event / sync / SaaS at operator level | — | missing | missing | — | `docs/reference/event-envelope.md` exists but is internal/dev-focused. |
| Migration from older Charter docs | — | missing | — | — | `docs/migration/` directory exists (from-charter-2x.md is absent). |
| Troubleshooting / failure modes | — | missing | — | — | No Charter-specific troubleshooting. `docs/how-to/diagnose-installation.md` and `troubleshoot-merge.md` exist but are not Charter-failure-mode focused. |
| CLI reference (Charter era) | — | — | present-stale | — | `docs/reference/cli-commands.md` exists but predates Charter subcommands (`charter`, `next`, `retro`, `agent decision`, `agent mission`). |
| docs/2x/ section label | — | — | — | present-stale | Not labeled as archive/historical. Risks users treating it as current. |
| docs/retrospective-learning-loop.md nav registration | — | — | — | present-stale | File exists; `TODO: register in docs nav` comment present; not in root toc.yml. |

---

## 3. Source-of-Truth Inputs per Area

### Charter overview / mental model
- **Source code**: `src/specify_cli/charter/` module tree; `src/specify_cli/next/` for DRG-backed context injection
- **Existing spec**: `kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/spec.md` (if present); `kitty-specs/drg-phase-zero-01KP2YCE/spec.md`
- **CLI**: `uv run spec-kitty charter --help`; `uv run spec-kitty charter status`; `uv run spec-kitty charter lint`; `uv run spec-kitty charter bundle`
- **Stale doc**: `docs/2x/doctrine-and-charter.md`

### Governance setup / bootstrap
- **Source code**: `src/specify_cli/charter/interview.py`; `src/specify_cli/charter/generate.py`; `src/specify_cli/charter/sync.py`
- **CLI**: `uv run spec-kitty charter interview --help`; `uv run spec-kitty charter generate --help`
- **Stale doc**: `docs/how-to/setup-governance.md`

### Charter synthesis / resynthesis
- **Source code**: `src/specify_cli/charter/synthesis/` or equivalent
- **CLI**: `uv run spec-kitty charter context --help`; `uv run spec-kitty charter status --help`; `uv run spec-kitty charter lint --help`
- **Specs**: phase-3-charter-synthesizer-pipeline, charter-synthesizer-phase-3-completion

### DRG-backed action context
- **Source code**: `src/specify_cli/next/` — DRG edge resolution, context injection
- **Specs**: `kitty-specs/drg-phase-zero-01KP2YCE/`; `kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/`
- **CLI**: `uv run spec-kitty charter context --action <action> --json`

### Profile invocation / invocation trails
- **Source code**: `src/specify_cli/` profile invocation modules
- **Specs**: `kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/`; `kitty-specs/phase-4-trail-host-surface-closeout-01KPSXD2/`
- **Existing doc**: `docs/trail-model.md` (exists — check if current)

### Mission composition (`spec-kitty next`)
- **Source code**: `src/specify_cli/next/`
- **CLI**: `uv run spec-kitty next --help`; `uv run spec-kitty next --json`
- **Specs**: `kitty-specs/software-dev-composition-rewrite-01KQ26CY/`; `kitty-specs/phase6-composition-stabilization-01KQ2JAS/`

### Retrospective learning loop
- **Source code**: `src/specify_cli/` retrospective modules
- **Specs**: `kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/`
- **Existing doc**: `docs/retrospective-learning-loop.md` (partial — needs synthesis dry-run/apply, cross-mission summary)

### CLI reference (Charter era)
- **Source**: `uv run spec-kitty --help`; each subcommand `--help`; `src/specify_cli/cli/` tree
- **Commands to cover**: `charter interview`, `charter generate`, `charter context`, `charter status`, `charter sync`, `charter lint`, `charter bundle`; `next`; `retro summary`; `retro synthesizer dry-run/apply`; `agent decision open/resolve/defer/cancel/verify`; `agent mission create/setup-plan`

### Documentation mission phases
- **Source**: `src/specify_cli/missions/documentation/mission-runtime.yaml` (or equivalent)
- **Current stale**: `docs/explanation/documentation-mission.md` (old phase names)

### Migration from 2.x
- **Source**: Breaking changes between 2.x and Charter-era 3.x; charter path changes; synthesis path changes
- **Existing migration docs**: `docs/migration/` directory (check contents)

---

## 4. Key Invariants for Generate Phase

These must hold in all generated content:

1. **File authority rule**: `charter.md` is the only human-edited governance file. Everything under `governance.yaml`, `directives.yaml`, `metadata.yaml`, and `library/*.md` is auto-generated and must never be edited directly. All docs must state this unambiguously.

2. **DRG context compact-context limitation**: When DRG context is too large to include in full, the runtime falls back to compact-context mode. Docs must name this limitation (issue #787 or current equivalent) and not promise full-context behavior unconditionally.

3. **Custom mission retrospective execution**: If current product supports it (verify against `mission-runtime.yaml`), docs must not claim it is deferred.

4. **Documentation mission phases**: Must match exactly what `mission-runtime.yaml` declares. Do not invent or elide phases.

5. **Profile invocation lifecycle**: The `(profile, action, governance-context)` triple is the correct primitive. `ask`, `advise`, `do` are the three invocation modes. `profile-invocation complete` closes the trail. All four must appear in docs.

6. **Retrospective gate**: In autonomous mode, the retrospective cannot be skipped. In HiC mode, skipping requires explicit operator action with an audit trail. Docs must reflect both modes.

---

## 5. Validation Source-of-Truth Commands

Run from repo root with `uv run spec-kitty`:

```bash
# Charter command surface
uv run spec-kitty charter --help
uv run spec-kitty charter interview --help
uv run spec-kitty charter generate --help
uv run spec-kitty charter context --help
uv run spec-kitty charter status --help
uv run spec-kitty charter sync --help
uv run spec-kitty charter lint --help
uv run spec-kitty charter bundle --help  # verify this subcommand exists

# Composition / next
uv run spec-kitty next --help

# Retrospective
uv run spec-kitty retro --help           # verify subcommand tree
uv run spec-kitty retro summary --help
uv run spec-kitty retro synthesizer --help

# Agent decision
uv run spec-kitty agent decision --help
uv run spec-kitty agent decision open --help
uv run spec-kitty agent decision resolve --help
```

Note: If any of these return "No such command", document accordingly in the CLI reference rather than assuming the command exists.

---

## 6. Docs Test Inventory

Existing test files in `tests/docs/`:
- `test_architecture_docs_consistency.py`
- `test_readme_canonical_path.py`
- `test_versioned_docs_integrity.py`

Run with:
```bash
uv run pytest tests/docs/ -q
```

These tests must pass before and after all changes. The implementer should check whether new pages need to be registered in these tests or whether tests auto-discover changed files.

---

## 7. Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Docs section IA strategy | Hybrid (C): `docs/3x/` hub + main Divio updates | Avoids version-silo (B) and addresses the `2x/` confusion (A deficiency); gives a clear current-era anchor without breaking Divio discoverability |
