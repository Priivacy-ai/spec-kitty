# Implementation Plan: docs/plans Tier 3 Closeout (Scope A)

**Branch**: `feat/docs-plans-tier3-closeout` | **Date**: 2026-08-12 (re-scoped after post-plan squad split) | **Spec**: [spec.md](spec.md)
**Input**: Scope A of the split — docs/plans closeout. Scope B (doctrine schema diagrams + PlantUML rendering + per-module READMEs) is a separate mission.

## Summary

Finish the `docs/plans` curation begun in PR #3324: retire shipped/superseded working-note clusters (evidence-gated; roadmap deferred on open-core item R), author the two remaining domain plans (`packs-extraction`, `api-dashboard`) with explicit boundary seams, migrate all four domain plans into a `docs/plans/domains/` cluster (occurrence-mapped), and add a reserved `durable` `doc_status` value — amending the **authoritative directive 042** first, then mirroring it in the enum and every validation site so a throughline is never swept.

## Technical Context

**Language/Version**: Python 3.11+ (the `DocStatus` enum + validation-site edits); Markdown + YAML frontmatter (docs); YAML (directive 042, styleguide, occurrence map)
**Primary Dependencies**: the existing docs tooling — `scripts/docs/frontmatter_backfill.py` (`DocStatus`), the structural-lint asset + `common-docs.styleguide.yaml`, the docs lockfile generators (`docs_index.py`, `inventory_lockfile.py`), the relative-link-fixer; ruamel.yaml; pytest; ruff; mypy
**Storage**: Files — Markdown/YAML docs, the two docs lockfiles
**Testing**: `tests/docs/` (must stay green), `tests/doctrine/test_schema_generation_integrity.py` (the schema-integrity gate if `durable` is encoded structurally), the terminology guard, the relative-link-fixer; ATDD-first (C-011) — the "durable accepted everywhere" assertion lands red-first
**Target Platform**: Linux CI (docs workflows) + the published docsite
**Project Type**: single (docs + a small enum/validation change)
**Performance Goals**: N/A (editorial + one enum value)
**Constraints**: no content deletion on retire; `closeout` is not an enum value; directive 042 is the vocabulary authority; the `domains/` migration is occurrence-mapped
**Scale/Scope**: ~11 retire-candidate clusters (3 auto, 8 evidence-gated, 1 deferred); 2 new + 2 migrated domain plans; 1 `doc_status` value across all validation sites

## Charter Check

*GATE: pass before Phase 0; re-check after Phase 1.*

- **ATDD-First (C-011)** — the `durable`-accepted-everywhere test lands red-first. ✅
- **Terminology Canon** — terminology guard; the api-dashboard plan documents killing `Feature:` drift (C-003). ✅
- **Canonical Sources** — the occurrence map uses the canonical template/schema; directive 042 is edited as the authority, the enum mirrors it. ✅
- **Quality gates** — the enum/validation change passes ruff + mypy with zero suppressions + focused tests. ✅

No violations requiring Complexity Tracking.

## Project Structure

```
docs/plans/domains/            # NEW home — 4 domain plans + domains/index.md
├── saas-hosted-sync-domain-plan.md, doctrine-charter-domain-plan.md   # MOVED
├── packs-extraction-domain-plan.md, api-dashboard-domain-plan.md      # NEW
└── index.md
docs/plans/index.md            # EDIT — domains/ cluster; retire-index updates
docs/plans/** (engineering-notes/, reviews/, refactor/, 3-2-doc-publication/, doctrine/, investigations/)  # retire targets
docs/plans/3-2-x-*.md          # EDIT — reciprocal domain-plan links after move
packs/built-in/directives/042-common-docs.directive.yaml   # EDIT — add durable to the authoritative vocabulary
packs/built-in/styleguides/common-docs.styleguide.yaml     # EDIT — structural_lint / vocabulary prose (+ durable ∉ point_in_time)
scripts/docs/frontmatter_backfill.py                       # EDIT — DocStatus.DURABLE (mirror)
src/doctrine/styleguides/models.py                         # EDIT (if durable encoded structurally) + regenerate schema
tests/docs/*, tests/doctrine/test_schema_generation_integrity.py   # EDIT/NEW — durable accepted; drift red-first
kitty-specs/<mission>/occurrence_map.yaml                  # bulk-edit map (canonical schema)
```

**Structure Decision**: single-project docs + a mirrored enum change. Directive 042 is the authoritative edit; the `DocStatus` enum and validation sites mirror it.

## Implementation Concern Map

### IC-01 — Durable doc_status marker + validator propagation

- **Purpose**: Add `durable` as a reserved, never-retire `doc_status` value across the full vocabulary chain.
- **Relevant requirements**: FR-002, NFR-001, C-004, C-005
- **Affected surfaces**: **directive `042-common-docs` (authority — edit first)**; `scripts/docs/frontmatter_backfill.py:DocStatus`; `common-docs.styleguide.yaml` (structural_lint / vocabulary prose, assert `durable ∉ point_in_time_markers`); `src/doctrine/styleguides/models.py` + regenerated schema if encoded structurally; `docs-freshness-sla.styleguide.yaml`; tests in `tests/docs/` **and** `tests/doctrine/test_schema_generation_integrity.py`
- **Sequencing/depends-on**: none — **foundation; predecessor of IC-02, IC-03, IC-04** (any doc written with `doc_status: durable` fails until this lands)
- **Risks**: a missed validation site rejects `durable`. Mitigation: an enumerated test asserting `durable` passes every site (red-first); the enumeration is directive-042-led, not enum-led.

### IC-02 — Retire/archive sweep with evidence

- **Purpose**: Retire shipped/superseded plan clusters safely, each with a shipped-evidence line.
- **Relevant requirements**: FR-001, NFR-002, C-001
- **Affected surfaces**: `docs/plans/engineering-notes/**`, `reviews/**`, `refactor/**`, `3-2-doc-publication/**`, `doctrine/**`, `investigations/**`; `docs/plans/index.md`
- **Sequencing/depends-on**: IC-01
- **Decomposition note**: **fan out at tasks time** — one WP for the 3 auto-retireable clusters, plus per-evidence-source WPs for the 8 evidence-gated ones (each carries its `gh issue view` citation). Do NOT leave IC-02 as a single serial WP.
- **Risks**: premature retirement; roadmap out of scope (C-001); do not retire the #3324-relocated `charter-sole-door-deferred-issues.md`.

### IC-03 — Two new domain plans with boundary seams

- **Purpose**: Author `packs-extraction` and `api-dashboard` domain plans with explicit boundaries.
- **Relevant requirements**: FR-003, FR-004, C-003
- **Affected surfaces**: the two new plan files; doctrine-charter §3.2/§3.6 (boundary references)
- **Sequencing/depends-on**: **IC-01** (they carry `doc_status: durable`)
- **Risks**: overlap with doctrine-charter §3.2 (packs) / §3.6 (API) — mitigated by explicit non-goal statements.

### IC-04 — domains/ migration (bulk edit)

- **Purpose**: Move all four domain plans into `docs/plans/domains/` with an index; update every reference.
- **Relevant requirements**: FR-005, C-002
- **Affected surfaces**: the 4 plan files; `docs/plans/index.md`; the four `3-2-x-*` release docs; SaaS/doctrine-charter §6 cross-refs; the docs lockfiles
- **Sequencing/depends-on**: **IC-01** (migrated plans carry `durable`) **and IC-03** (new plans exist before/at the move)
- **Shared-file note**: `docs/plans/index.md` is touched by IC-02 (retire index) and IC-04 (domains cluster) — **merge both index edits into one WP** to avoid contention.
- **Risks**: dead links if a reference is missed → `occurrence_map.yaml` (canonical schema) + the relative-link-fixer test are the mitigation.

## Notes

- **Post-plan squad applied**: this plan reflects the split (Scope A only) and the squad's Scope-A findings — the directive-042-led enumeration, the `closeout`-is-not-a-value correction, the IC-01 predecessor edges for IC-03/IC-04, the IC-02 fan-out, the shared-`index.md` merge, and the canonical occurrence map. Scope-B findings (no-egress proof, drift-guard aliasing, NodeKind=16, action-index/step-contract filing, alt-text, toolguide citation) are carried into Mission B.
