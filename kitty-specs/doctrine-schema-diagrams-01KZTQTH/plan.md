# Implementation Plan: Doctrine Schema Diagrams and PlantUML Rendering (Scope B)

**Branch**: `feat/doctrine-schema-diagrams` | **Date**: 2026-08-12 | **Spec**: [spec.md](spec.md)
**Input**: Scope B of the split. Adds local PlantUML docsite rendering + code-grounded schema diagrams + per-module READMEs. Post-spec squad findings are folded in.

## Summary

Add a **local, build-time** PlantUML render step to the DocFX pipeline (a post-processor after `glossary_linker` in **both** docs workflows), governed by an ADR that reconciles the existing `plantuml-diagramming` toolguide and R-04/#1839. Then author `@startyaml` schema diagrams of the doctrine artefacts, generated from the frozen code models and enforced by a drift guard driven by an explicit `file:class` binding table (alias-normalized, transitively recursed, completeness-checked). Add pointer-only module READMEs and fill the two genuinely-thin kinds. The security claim (no egress) is proven behaviorally, not by flag presence.

## Technical Context

**Language/Version**: Python 3.11+ (render step, drift guard, README lint); PlantUML `@startyaml`; a version+sha256-pinned `plantuml.jar` (Java, build-time only); Markdown + YAML docs
**Primary Dependencies**: DocFX (`modern`); pinned `plantuml.jar`; the `scripts/docs/` HTML post-processing steps (`glossary_linker.py` pattern); **Docker** (`--network=none` for the egress-isolation proof — present on the runners); pytest; ruff; mypy; the frozen doctrine models (`src/doctrine/**`, read-only)
**Storage**: Files — Markdown/YAML docs; SVGs CI-generated into `docs/_site` (not committed)
**Testing**: `tests/docs/` (green) + NEW: drift guard, render round-trip (` ```plantuml ` → `_site` → recovered → SVG), **behavioral** SANDBOX negative test (`!includeurl` fails-closed), no-egress isolation test (`docker run --network=none`), README pointer-lint; ATDD-first (C-011)
**Target Platform**: Linux CI — `docs-build-pr.yml` (PR gate) + `docs-pages.yml` (deploy) — and the published docsite
**Project Type**: single (docs + docs-tooling)
**Performance Goals**: render adds ≤ 60s — a **monitored budget/warning**, not a hard per-PR gate (flakiness policy)
**Constraints**: zero doctrine-content egress (local jar; `docker --network=none` isolation proof); `plantuml.jar` pinned by version+sha256; SVGs CI-generated; diagrams render docsite-only (not github.com); the drift guard introspects models (never hand-counts); READMEs are pointer-only
**Scale/Scope**: ~12 artefact-kind diagrams; 1 render script; 2 workflow edits; 1 ADR; 1 drift guard; N module READMEs; 2 kinds filled

## Charter Check

- **ATDD-First (C-011)** — the drift guard, the render round-trip, the SANDBOX negative test, and the no-egress isolation test all land red-first. ✅
- **Writing/Diagramming Doctrine** — the ADR reconciles PlantUML/C4/accessibility (cites the `plantuml-diagramming` toolguide; positions schema diagrams as a new genre distinct from C4 zoom; records the "restate-facts-in-prose" carve-out). ✅
- **Privacy / no-egress** — behavioral SANDBOX + network-isolated render. ✅
- **Accessibility** — NFR-005: derived, non-trivial alt/aria on every SVG. ✅
- **Quality gates** — new Python passes ruff + mypy with zero suppressions + focused tests. ✅

No violations requiring Complexity Tracking.

## Project Structure

```
scripts/docs/plantuml_render.py        # NEW — recover ```plantuml fences from _site (html.unescape), render via pinned jar (SANDBOX), inject SVG + alt
.github/workflows/docs-build-pr.yml    # EDIT — add render step AFTER glossary_linker; setup-java + pinned jar (sha256)
.github/workflows/docs-pages.yml       # EDIT — same; also extend the paths: allowlist to include the new script
docs/architecture/doctrine-kinds.md            # EDIT — cross-kind overview diagram; fill glossary-pack + anti-pattern; sweep "eight" heading
docs/architecture/doctrine-relationships.md    # EDIT — DRG diagram; note the prose "15" is diagram-unguarded
docs/architecture/mission-type-resolution.md   # EDIT — mission-type/step + action-index diagram WITH standalone prose
docs/adr/3.x/2026-08-12-*-plantuml-schema-diagram-rendering.md   # NEW ADR (FR-002)
docs/architecture/diagrams/README.md           # EDIT — R-04 amendment (generated docsite-only schema lane)
src/doctrine/**/README.md              # NEW/EXTEND — pointer-only module READMEs (module->plan mapping)
tests/docs/ (or tests/architectural/)  # NEW — drift guard, render round-trip, SANDBOX negative, no-egress isolation, README lint
src/doctrine/** models                 # READ-ONLY — source of truth for diagrams
```

**Structure Decision**: single-project docs-tooling. The render step is confined to `scripts/docs/` + the two workflows; diagrams live in the doctrine-docs cluster; models are read-only.

## Implementation Concern Map

### IC-01 — PlantUML docsite rendering (capability)

- **Purpose**: local build-time render of `@start*` fences to SVG, zero egress.
- **Requirements**: FR-001, NFR-002, NFR-003, NFR-004, NFR-005, C-001, C-002, C-006
- **Affected surfaces**: `scripts/docs/plantuml_render.py`; `docs-build-pr.yml` + `docs-pages.yml` (both; the deploy `paths:` allowlist); a sample diagram page
- **Plan specifics** (post-spec squad): insert **after** `glossary_linker` in each workflow (fence stays `<pre><code>`, safe); `html.unescape()` the payload; assert the emitted `language-plantuml` class; **egress spike first** — confirm `docker run --network=none` (portable) renders green on `blacksmith-4vcpu-ubuntu-2404` + `ubuntu-latest` before committing the mechanism; `unshare -rn` only if the runner permits unprivileged userns (with `ip link set lo up`); behavioral SANDBOX negative test.
- **Sequencing/depends-on**: none — **precedes IC-03/IC-04**
- **Risks**: CI isolation runnability (mitigated by the spike + docker fallback); glossary_linker SVG corruption (mitigated by ordering + `<pre><code>` recovery form).

### IC-02 — ADR + R-04 amendment

- **Purpose**: govern the rendering decision and the schema-diagram genre.
- **Requirements**: FR-002, C-006, NFR-005 (carve-out)
- **Affected surfaces**: new ADR; `docs/architecture/diagrams/README.md`
- **Plan specifics**: cite the `plantuml-diagramming` toolguide (charter-prose "active", not runtime-resolved); position schema diagrams as a NEW genre distinct from C4 zoom; record the accessibility "restate-facts-in-prose → discharged by doctrine-kinds prose, not field re-listing" carve-out; state the new lane trades github.com-source rendering for generated fidelity (so R-04 and the ADR don't contradict).
- **Sequencing/depends-on**: co-lands with IC-01

### IC-03 — Schema diagrams

- **Purpose**: author `@startyaml` typed-placeholder diagrams from the frozen models.
- **Requirements**: FR-003, C-003, C-004, NFR-005
- **Affected surfaces**: `doctrine-kinds.md` (cross-kind overview), `doctrine-relationships.md` (DRG), `mission-type-resolution.md` (mission-type/step + **action-index with standalone prose**); read-only models
- **Sequencing/depends-on**: IC-01 (rendering must exist)
- **Risks**: drift → IC-04 guard is the mitigation, co-lands.

### IC-04 — Drift guard

- **Purpose**: enforce zero diagram/code drift.
- **Requirements**: FR-004, NFR-001, C-003
- **Affected surfaces**: a new guard test; the `file:class` binding table; read-only models
- **Plan specifics**: explicit binding table (1:N, e.g. DRG → `DRGNode`+`DRGEdge`+`NodeKind`+`Relation`); Pydantic `model_fields` with `FieldInfo.alias or name` + **transitive nested recursion** (test at depth — add a field to a nested value-object and assert FAIL); dataclass `fields()`; StrEnum `list()`; **binding completeness** from `list(ArtifactKind)` + the priority list. ATDD red-first.
- **Sequencing/depends-on**: with/after IC-03

### IC-05 — Per-module code→docs READMEs

- **Purpose**: pointer-only bridge from source modules to canonical docs.
- **Requirements**: FR-005, C-005
- **Affected surfaces**: `src/doctrine/**/README.md` (extend, don't clobber); a README structural lint
- **Plan specifics**: explicit module→plan mapping + fallback; **external precondition — Scope A domain plans merged to `main`** so the plan links resolve; a machine lint (length cap / forbid field-table markers) enforces pointer-only.
- **Sequencing/depends-on**: IC-03 (diagram links) + external Scope-A merge

### IC-06 — Fill genuinely-thin kinds + campsite

- **Purpose**: fill `glossary-pack` + `anti-pattern`; tidy the catalog.
- **Requirements**: FR-006, C-004
- **Affected surfaces**: `doctrine-kinds.md` (fill + sweep the stale "## The eight doctrine artifact kinds" heading to the 12-member reality; record the `template` audit note); `doctrine-relationships.md` (note the unguarded "15" prose literal)
- **Sequencing/depends-on**: pairs with IC-03 (shared file `doctrine-kinds.md` — co-locate to avoid contention)

## Notes

Post-spec squad (3 lenses) applied: no-egress mechanism de-risked (docker `--network=none` + spike, not `unshare` alone); behavioral SANDBOX negative test; drift-guard binding-completeness + nested-depth + explicit binding table; accessibility reconciliation carve-out; both-workflow insertion + order-after-glossary_linker + unescape + class assertion; FR-005 Scope-A precondition + module→plan mapping; action-index standalone prose; `list(NodeKind)` (no literal); template/heading/`15`-literal campsite notes.
