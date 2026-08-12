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
**Scale/Scope**: **4 priority schema diagrams + a cross-kind overview** across 3 doc files (FR-003 is the authoritative count — NOT "~12"; the drift-guard binding table sizes to this); 1 render script; 2 workflow edits; 1 ADR; 1 drift guard; ~17 module READMEs (EXTEND-heavy — they already exist); 2 kinds filled

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
- **Plan specifics** (post-plan squad): **execution locus** — Python orchestration runs host-native + **stdlib-only** (`docs-pages.yml` has no setup-python / no pip install); only `java -jar` is wrapped in `docker run --network=none -v <tmp>:<tmp> <digest-pinned-JRE-image>` (prefetch the image **before** isolation; **drop host `setup-java`**, redundant). Insert **immediately after `glossary_linker`, before redirect-stub + `seo_verify`** in BOTH workflows (+ extend the `docs-pages.yml` enumerated `paths:` allowlist — not a glob). `html.unescape()` the payload + confirm the emitted fence class against real `_site` HTML.
- **The egress spike is a BLOCKING WP01** — runnability is currently **UNPROVEN** (not "de-risked"): render a REAL `@startyaml` diagram under `--network=none` on **both** `ubuntu-latest` and `blacksmith-4vcpu-ubuntu-2404`, confirming no font/DNS-driven failure. Its green exit-criterion gates every render/diagram WP.
- **Sequencing/depends-on**: none — **its render-acceptance precedes IC-03's SVG scenario** (IC-04 does NOT need it, see IC-04)
- **Risks**: CI isolation runnability (the spike is the gate); glossary_linker SVG corruption (mitigated by ordering + `<pre><code>` recovery form).

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
- **Plan specifics**: both sides pinned — **diagram-side parse** (top-level `@startyaml` keys, recursing into nested sub-maps, = declared field set) AND model introspection (`FieldInfo.alias or name` + transitive recursion; dataclass `fields()`; StrEnum `list()`). Non-fakeable tests: **completeness over ALL `ArtifactKind`** (a synthetic new member FAILS until dispositioned — not just the 4 priority kinds); **omit-a-field** (a diagram missing a model field FAILS); **nested depth-2** pinned to `AgentProfileSchema → AgentSpecialization` (DRG is FLAT — not usable for the depth test). ATDD red-first.
- **Sequencing/depends-on**: **parallel with IC-01** — it is a pytest parsing `@startyaml` text + introspecting models; it does NOT need the render pipeline. Only IC-03's render-acceptance serializes behind IC-01.

### IC-05 — Per-module code→docs READMEs

- **Purpose**: pointer-only bridge from source modules to canonical docs.
- **Requirements**: FR-005, C-005
- **Affected surfaces**: `src/doctrine/**/README.md` (extend, don't clobber); a README structural lint
- **Plan specifics**: **independently landable** — each README's fallback links point at **in-mission** targets (the doctrine-kinds entry + the schema diagram) that always resolve, so FR-005's link check never reds on an external merge; the "owning domain plan" link is added opportunistically (doctrine-charter is already on `main` via #3324; packs-extraction/api-dashboard arrive with Scope A). **N≈17 modules already carry READMEs → EXTEND-heavy**, don't clobber. A machine lint (length cap / forbid field-table markers) enforces pointer-only.
- **Sequencing/depends-on**: **LAST, decoupled, abandonable** WP — never on the critical path to mission merge; no hard external dependency (fallback links resolve in-mission).

### IC-06 — Fill genuinely-thin kinds + campsite

- **Purpose**: fill `glossary-pack` + `anti-pattern`; tidy the catalog.
- **Requirements**: FR-006, C-004
- **Affected surfaces**: `doctrine-kinds.md` (fill + sweep the stale "## The eight doctrine artifact kinds" heading to the 12-member reality; record the `template` audit note); `doctrine-relationships.md` (note the unguarded "15" prose literal)
- **Sequencing/depends-on**: **hard co-location, not a suggestion** — a SINGLE WP owns `doctrine-kinds.md` (overview diagram + glossary-pack/anti-pattern fills + "eight"→12 heading sweep) AND a single WP owns `doctrine-relationships.md` (DRG diagram + the unguarded "15" prose note), since both files are shared by IC-03 and IC-06.

## Notes

Post-spec squad (3 lenses) applied: no-egress mechanism (docker `--network=none` + spike, not `unshare` alone); behavioral SANDBOX; drift-guard binding-completeness + nested-depth + explicit binding table; accessibility reconciliation carve-out; both-workflow insertion; FR-005 module→plan mapping; action-index standalone prose; `list(NodeKind)` (no literal); template/heading/`15` campsite notes.

**Post-plan squad (3 lenses) applied** (this revision): IC-01 execution-locus pinned (Python host-native stdlib-only + `java -jar` in `docker --network=none` with a digest-pinned JRE, drop `setup-java`); egress spike is a **blocking WP01**, runnability **UNPROVEN**; render slot pinned after `glossary_linker` before redirect-stub/`seo_verify`; drift guard's diagram-side parse pinned + completeness-over-all-`ArtifactKind` + omit-a-field + depth-2-on-a-real-nested-model; SANDBOX negative test uses a local listener (not "build fails"); alt-text made a concrete distinct-caption predicate; IC-04 parallel to IC-01; **IC-05 made independently-landable** (in-mission fallback links; last/abandonable), diagram count reconciled to FR-003's 4+overview; hard single-WP ownership of `doctrine-kinds.md` and `doctrine-relationships.md`.

**Tracker (DIR-012/DIR-013)**: this mission edits `.github/workflows/docs-*.yml` and pins an external `plantuml.jar` — capture/assign a backing tracking issue to the HiC before `implement`, and pre-declare the DIR-013 baseline-red attribution posture for the `tests/docs/` touch.
