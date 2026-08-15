# Implementation Plan: Self-documenting repo — migrate agent-memory gap-fillers

**Branch**: `kitty/mission-self-doc-gapclose` | **Date**: 2026-08-15 | **Spec**: `kitty-specs/self-documenting-repo-01M0287X/spec.md`
**Input**: Feature specification from `kitty-specs/self-documenting-repo-01M0287X/spec.md`

## Summary

Migrate maintainer agent-memory shadow-documentation into the repo so a bare-system agent (repo + skills/packs only) is self-sufficient. Six clusters (G1–G6, audited in `work/memory-gap-filler-analysis.md`): (G1) enrich architectural/docs gate assertions with content-anchored remedies **derived from the current gate logic**; (G2) sweep every stale `src/doctrine/missions/…` reference in CLAUDE.md to `packs/built-in/missions/…`; (G3) publish coord/lane split-brain recovery entries in the existing `docs/operations/` home, leading with shipped `doctor … --fix`; (G4) make repo-owned workflow commands discoverable; (G5) file (not fix) three behavior-quirk bugs; (G6) put env/tracker conventions in dev docs; plus a committed **migration manifest** as the repo-testable proof.

## Technical Context

**Language/Version**: Python 3.11+ (test assertions, `scripts/docs/`), Markdown + YAML frontmatter (docs).
**Primary Dependencies**: pytest (architectural + docs gates), the docs inventory/retrieval-index tooling (`scripts/docs/`), the `spec-kitty doctor` command surface.
**Storage**: files (docs, tests, a manifest under `kitty-specs/<mission>/`).
**Testing**: pytest — `tests/architectural/**`, `tests/docs/**`; each new remedy validated by *tripping the gate*; docs validated by `check_docs_freshness --ci`.
**Target Platform**: repo/CI (Linux).
**Project Type**: single project.
**Performance Goals**: N/A.
**Constraints**: content-anchored (no file:line / whole-file allowlists — DIRECTIVE_041); no new merge-blocking red (ADR 2026-07-17-1); `divio_type` closed enum; docs-freshness errors=0; terminology-canon clean.
**Scale/Scope**: ~6 clusters, ~12–16 gate/doc surfaces, one manifest, three filed issues.

## Charter Check

- **ATDD/red-first**: each FR-001 remedy is proven by tripping the gate before/after; docs gates verified via `check_docs_freshness --ci`.
- **Canonical sources**: edit sources, not generated copies; remedies derived from gate code, not memory (C-005).
- **Terminology + docs-freshness**: run `test_no_legacy_terminology.py` + `check_docs_freshness --ci` on every prose touch.
- **No new red**: NFR-002.

## Project Structure

### Documentation (this mission)
```
kitty-specs/self-documenting-repo-01M0287X/
  spec.md, plan.md, tasks.md, tasks/, migration-manifest.md
```

### Source Code (repository root)
```
tests/architectural/**        # G1 gate-remedy enrichment (assertion strings)
tests/docs/**                 # G1 docs-gate remedies
CLAUDE.md                     # G2 source-location sweep
docs/operations/**            # G3 recovery entries + recovery-index.md registration
docs/development/**           # G4 command discoverability, G6 dev-setup gotchas
docs/**contributing**         # G6 tracker conventions
scripts/docs/                 # G4 (freshen), G1 (docs gates)
```

**Structure Decision**: single project; changes are localized to `tests/`, `docs/`, `CLAUDE.md`, and one manifest — no `src/` behavior change (G5 fixes are deferred to filed issues, so no runtime code changes land here except possibly extending gate *messages*, which are test-side strings).

## Complexity Tracking

| Deviation | Need | Simpler rejected because |
| --- | --- | --- |
| Editing many gate assertion strings | Each gate owns its own message | A single shared remedy helper would couple unrelated gates and hide per-gate specifics |

## Implementation Concern Map

### IC-01 — Gate-remedy enrichment (G1)
- **Purpose**: every enumerated architectural/docs gate prints a content-anchored remedy derived from its own current logic, validated by tripping it.
- **Relevant requirements**: FR-001; NFR-003; C-005; SC-001.
- **Affected surfaces**: `tests/architectural/test_arch_shard_marker_completeness.py`, `test_no_write_side_rederivation.py`, `test_golden_count_ban.py` (model), the gate-coverage/docs-move/analysis-report/schema-slot/mission-gate gates; a small test asserting each remedy substring exists.
- **Sequencing/depends-on**: none (independent).
- **Risks**: transcribing a stale symbol from memory (C-005) — mitigate by deriving from code + a trip-the-gate check.

### IC-02 — CLAUDE.md source-location sweep (G2)
- **Purpose**: correct every `src/doctrine/missions/…` reference to `packs/built-in/missions/…`.
- **Relevant requirements**: FR-002; SC-003.
- **Affected surfaces**: `CLAUDE.md` (the Template-Source table, the flow diagram, the "Use Canonical Sources" section).
- **Sequencing/depends-on**: none.
- **Risks**: missing the second reference (the squad flagged two) — grep-sweep all occurrences.

### IC-03 — Operations recovery entries (G3)
- **Purpose**: publish the six coord/lane split-brain recovery entries in `docs/operations/`, each leading with the shipped `doctor … --fix` where one exists, manual otherwise; registered in `recovery-index.md`.
- **Relevant requirements**: FR-003, FR-004; C-001, C-002; NFR-001; SC-002.
- **Affected surfaces**: `docs/operations/*.md`, `docs/operations/recovery-index.md`, the page-inventory + retrieval-index (`docs/development/3-2-*.yaml`).
- **Sequencing/depends-on**: **first sub-task = audit `doctor --fix` coverage** per class (present/partial/absent) before authoring, so entries point at real commands.
- **Risks**: divio_type must be `none` (closed enum); docs-freshness registration; over-promising an absent `--fix`.

### IC-04 — Discoverable workflow commands (G4)
- **Purpose**: make the repo-owned commands (docs-inventory freshen, mission wrap-up) discoverable; regen is a pointer to #3447.
- **Relevant requirements**: FR-005; C-003.
- **Affected surfaces**: `docs/development/**` (or a make target / skill reference).
- **Sequencing/depends-on**: none.
- **Risks**: do not duplicate #3447's regen entrypoint.

### IC-05 — File bugs + env/tracker docs (G5, G6)
- **Purpose**: file the three behavior-quirk bugs (fixes deferred) and document env/tracker conventions.
- **Relevant requirements**: FR-006, FR-007; SC-004.
- **Affected surfaces**: GitHub issues (refs recorded in the manifest); `docs/development/**` dev-setup; contributing/tracker docs.
- **Sequencing/depends-on**: issue refs feed IC-06's manifest.
- **Risks**: scope — filing only, no fixing.

### IC-06 — Migration manifest (FR-008)
- **Purpose**: a committed manifest mapping each G1–G6 gap-filler to its repo home or tracking issue — the repo-testable proof.
- **Relevant requirements**: FR-008; C-004; SC-005.
- **Affected surfaces**: `kitty-specs/self-documenting-repo-01M0287X/migration-manifest.md`.
- **Sequencing/depends-on**: aggregates IC-01…IC-05 outputs (last).
- **Risks**: completeness — every audited gap-filler must appear.

---

## Post-plan squad reconciliation (folded)

Two lenses (implementer-ivan feasibility, paula-patterns brownfield/SSOT) corrected the IC map before decomposition:

- **IC-01 re-scope (MAJOR).** The "new arch test → append `_ARCH_SHARD_N_FILES`" remedy is obsolete: `tests/_arch_shard_map.py:46-63` documents the #2671 **auto-cover fallback** (`arch` group `default_fallback=True`) — a new arch file is auto-covered, so the completeness gate (`test_arch_shard_marker_completeness.py:12`, authority `tests._shard_registry`) does **not** trip on it. That memory (`reference_arch_gate_campsite_fixes`) is itself a **stale gap-filler** (C-005 failure mode); its manifest outcome is "behavior retired — delete the memory, no gate remedy." IC-01's actionable G1 remedy set is therefore smaller and must be **located in code first**: confirmed remedy-extensible gates = `test_no_write_side_rederivation.py`, `test_no_inert_schema_slots.py` (+ `golden-count` as the already-complete **model**). Reclassify/locate: `analysis-report-staleness` = `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` (narrow correctness test — likely NOT remedy-bearing); `docs-move-relative-link` = `tests/docs/test_relative_link_fixer.py` + `test_related_validator.py`; `mission-gate-artifact` = owning gate unidentified → locate or drop.
- **IC-03 recovery-home reconciliation (MAJOR).** A **second active recovery home** exists: `docs/guides/how-to/recovery/` (crash/interrupted-merge how-tos). Reuse `docs/operations/` for the coord/lane operational recoveries (operator-grant / `doctor --fix`), but add an IA rationale + **bidirectional cross-links** between the two homes (fold, don't silently pick). Cite the existing root-cause note `docs/plans/engineering-notes/coord-splitbrain-rootcause.md` for the "why"; the six recovery *procedures* are genuinely new. Verify each `doctor <sub> --fix` name/semantics first (`workspaces --fix` → `_workspace_husk_doctor.py` husk cleanup — confirm it's the right op).
- **Generated-yaml serialization (MAJOR).** `docs/development/3-2-page-inventory.yaml` + `3-2-docs-retrieval-index.yaml` are generated rollups behind a **global** freshness gate; every doc-adding WP regenerates them via `inventory_lockfile.py --write`. Serialize: doc WPs co-own the two yaml with a "no-parallel, serialized regen" rationale.
- **Manifest (IC-06).** Must allow a gap-filler to map to "behavior retired — no repo home" (the MAJOR-1 case), not force every G1 entry to a live remedy — else completeness pressure re-introduces the stale guidance the mission exists to delete.

### Work Package decomposition (feeds /tasks)

| WP | Scope | owned_files | depends_on |
|----|-------|-------------|-----------|
| **WP01** | G1: locate each enumerated gate in code; add content-anchored remedies to the confirmed remedy-extensible gates (derive-from-code, trip-to-validate); a meta-test asserting each *registered* gate's assertion carries a remedy substring. | the confirmed gate test files, new `tests/architectural/test_gate_remedy_presence.py`, `tests/_shard_registry.py` (register the meta-test if needed) | none |
| **WP02** | G2: sweep every `src/doctrine/missions/…` ref in CLAUDE.md → `packs/built-in/…`; grep-guard regression test. | `CLAUDE.md`, `tests/architectural/test_claudemd_template_source.py` | none |
| **WP03** | G3: 6 coord/lane recovery entries in `docs/operations/` (doctor `--fix` audit first; cross-link `docs/guides/how-to/recovery/` + cite the root-cause note); register in `recovery-index.md` + `toc.yml`. | `docs/operations/<6 new>.md`, `docs/operations/recovery-index.md`, `docs/operations/toc.yml`, + the two generated yaml (serialized) | none |
| **WP04** | G4 + G6: command discoverability (freshen, wrap-up) + env/tracker conventions in `docs/development/**`. | `docs/development/**`, + the two generated yaml (serialized) | **WP03** (serialize yaml regen) |
| **WP05** | G5 + manifest: file the 3 quirk bugs (refs recorded); write `migration-manifest.md` mapping every G1–G6 gap-filler → repo home / issue / "retired". | `kitty-specs/self-documenting-repo-01M0287X/migration-manifest.md` | WP01–WP04 |

Parallel: WP01, WP02, WP03. WP04 after WP03 (shared yaml). WP05 terminal.
