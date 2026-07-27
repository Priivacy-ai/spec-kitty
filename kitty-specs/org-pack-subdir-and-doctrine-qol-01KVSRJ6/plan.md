# Implementation Plan: Org-Pack Subdir Source & Doctrine QoL

**Branch**: `feat/doctrine-qol-2083` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/org-pack-subdir-and-doctrine-qol-01KVSRJ6/spec.md`

## Summary

Four threads. **A (#2083)**: add an optional `subdir` to `OrgPackConfig` and compute a single canonical **effective pack root** at the registry seam so every consumer (incl. the `doctor doctrine` health path) loads a subdir-rooted pack; plus containment validation, YAML round-trip, fetch effective-root reporting, and a config-schema contract update. **B (#707)**: document the (honest, current-vs-aspirational) ruamel.yaml-vs-PyYAML rule. **C (#1843 → child #2096)**: a non-orphan tiered-standards `styleguide` + one DRG edge (doctrine-only; CI/agent-effort deferred to the epic). **D (#2092)**: a validate-time fail-loud guard rejecting `applies_to_languages: [any]`/`[all]` + a "present-but-scope-filtered" catalog-miss diagnostic.

The design was corrected by a post-spec adversarial squad: the resolution seam is `OrgPackConfig`-level, **not** `resolve_org_roots` (see [research.md](research.md) and `research/post-spec-squad-findings.md`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2 (`OrgPackConfig` model, `extra="forbid"`), ruamel.yaml (config round-trip), PyYAML (`safe_load` loaders), typer + rich (CLI), pytest / mypy / ruff (quality)
**Storage**: filesystem — `.kittify/config.yaml`, doctrine pack directories, generated `src/doctrine/graph.yaml`
**Testing**: pytest (unit + integration). SC-001 requires an end-to-end `doctor doctrine`-on-subdir integration test exercising the real `load_org_drg` health path; parallel-run discipline per `docs/development/testing-parallel.md`
**Target Platform**: Linux / macOS developer + CI
**Project Type**: single (Python CLI + library)
**Performance Goals**: N/A — correctness-focused; effective-root resolution is O(packs), no hot path
**Constraints**: behavior-additive (NFR-001 — no-subdir resolves identically); `ruff`+`mypy` zero issues, cyclomatic complexity ≤ 15 (NFR-003); **no** CI gate or agent-effort change (C-001); register doctrine artifact via generator, not hand-edit (C-004); canonical field name `subdir`, no `pack_path` alias (C-002)
**Scale/Scope**: Thread A ≈ 6 consumer adoption sites + 2 round-trip seams + 1 contract file; Thread D = 2 surfaces; Thread C = 1 styleguide + 1 DRG edge + 1 test; Thread B = docs

## Charter Check

*GATE: charter present (`.kittify/charter/charter.md`).*

- **Terminology Canon** — honored: canonical field `subdir`, no `pack_path` alias (C-002); glossary disambiguation from the resolver's existing `subdir` param noted.
- **Canonical sources** — honored: doctrine artifact registered via `spec-kitty doctrine regenerate-graph` (C-004), not hand-edited; no improvised substitutes.
- **Single-authority / no shadow paths** — the mission *reduces* split surfaces by routing the ≥6 direct `pack.local_path` readers through one `effective_root` seam (C-007). No new shadow path introduced.
- **Scope discipline** — #1843 deliberately bounded to slice ① (doctrine-only) via child #2096; #2080 ruled a follow-up. No charter violations. **PASS.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/org-pack-subdir-and-doctrine-qol-01KVSRJ6/
├── plan.md              # This file
├── spec.md
├── research.md          # Phase 0 — design decisions (squad-derived)
├── data-model.md        # Phase 1 — entities/value objects
├── issue-matrix.md
├── contracts/           # Phase 1 — config-schema delta
├── checklists/requirements.md
└── research/post-spec-squad-findings.md
```

### Source Code (repository root)

```
src/
├── doctrine/
│   ├── drg/org_pack_config.py        # A: OrgPackConfig.subdir + effective_root + round-trip + legacy inline
│   ├── shared/scoping.py             # D: applies_to_languages_match (any/all)
│   ├── service.py                    # D: active-language set construction
│   └── styleguides/built-in/         # C: new tiered-standards styleguide (+ inbound DRG edge from a directive/paradigm)
├── charter/
│   ├── drg.py                        # A: load_org_pack consumer (BLOCKER path — doctor health)
│   ├── pack_context.py               # A: PackContext._read_org_packs consumer
│   ├── context.py                    # A: org-charter.yaml consumer
│   └── _catalog_miss.py              # D: present-but-scope-filtered diagnostic
└── specify_cli/
    ├── core/utils.py                 # A: ensure_within_directory (reuse)
    ├── doctrine/org_charter.py       # A: load_org_charter_policy consumer
    ├── doctrine/sources/git_source.py# A: clone target unchanged (C-003) — confirm only
    ├── doctrine/snapshot.py          # A: fetch effective-root reporting
    ├── charter_runtime/lint/checks/org_layer.py  # A: org-layer lint consumer
    └── cli/commands/
        ├── doctor.py                 # A: _build_pack_entries consumer
        └── doctrine.py               # A: fetch reporting / D: validate guard

tests/
├── doctrine/                         # unit: effective_root, scoping guard, round-trip, non-orphan styleguide
└── (integration)                     # SC-001 doctor-doctrine-on-subdir end-to-end
```

**Structure Decision**: Single Python project; brownfield edits across `src/doctrine`, `src/charter`, `src/specify_cli`. The load-bearing change is a single `effective_root` seam on `OrgPackConfig` that the enumerated consumers adopt.

## Brownfield Checks (standing post-planning order — 2026-06-23)

- **Foldable-issue search**: Done via the post-spec squad. **#2092 folded** (Thread D — same governance-layer silent-drop family, de-risks Thread C). **#2080 ruled follow-up** (daphne-led audit epic; deliverable is a remediation plan). No other open issue overlaps the touched surfaces; #1397 (`extends:`) already CLOSED.
- **Split-brain / consumer scan**: The squad enumerated the real fan-out — `resolve_org_roots` is a thin map; ≥6 consumers read `pack.local_path` directly (`charter/drg.py:137`, `charter/pack_context.py:344`, `doctrine/org_charter.py:570`, `doctor.py:2608`, `charter/context.py:746`, `charter_runtime/lint/checks/org_layer.py:236`). This mission **consolidates** them onto one `effective_root` seam (a split-reduction, not a new split). Pre-existing raw-vs-relative inconsistency retired at the seam (C-007).
- **Deprecation check**: Only deprecation marker in the touched modules is the expected legacy `organisation_packs` → `doctrine.org.packs` warning (`org_pack_config.py:122`). It is **not** due for removal this mission (read-compat path, orthogonal to `subdir`); left intact. No due deprecations to remove.
- **Orphan/DRG note (input to #2080)**: orphan styleguides auto-register as bare DRG nodes with no required edges; FR-011 forces a non-orphan edge for Thread C. Recorded for the #2080 audit.

## Implementation Concern Map

> Concerns, NOT work packages. `/spec-kitty.tasks` maps these to WPs.

### IC-01 — Effective-root resolution seam (Thread A core)
- **Purpose**: One canonical effective pack root computed at `OrgPackConfig`/registry level (joins `subdir`, normalizes relative-to-repo_root), retiring the raw-vs-relative split.
- **Relevant requirements**: FR-001, FR-002, C-007.
- **Affected surfaces**: `src/doctrine/drg/org_pack_config.py` (`OrgPackConfig`, an `effective_root(repo_root)` helper/property).
- **Sequencing/depends-on**: none (foundation for IC-02..IC-04).
- **Risks**: must be the single normalization point; getting relative-vs-absolute wrong reintroduces the split.

### IC-02 — All-consumer adoption (Thread A)
- **Purpose**: Route every pack-root reader through the effective root so a subdir pack loads everywhere, incl. the `doctor doctrine` health path.
- **Relevant requirements**: FR-004, SC-001, SC-002, NFR-001.
- **Affected surfaces**: `charter/drg.py:137`, `charter/pack_context.py:344`, `specify_cli/doctrine/org_charter.py:570`, `specify_cli/cli/commands/doctor.py:2608`, `charter/context.py:746`, `charter_runtime/lint/checks/org_layer.py:236`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: a missed consumer = silent partial fix; needs the end-to-end `doctor doctrine` integration test (SC-001) as the catch-all.

### IC-03 — subdir validation & containment (Thread A)
- **Purpose**: Reject path-escape; surface a structured error (not swallowed); correct lifecycle timing.
- **Relevant requirements**: FR-003, NFR-002.
- **Affected surfaces**: `org_pack_config.py` (field_validator for string escapes + resolution-time symlink check), reuse `specify_cli/core/utils.py:ensure_within_directory`; ensure error is not degraded by `load_pack_registry`'s warning path (`org_pack_config.py:128`).
- **Sequencing/depends-on**: IC-01.
- **Risks**: string-escape at validate time vs symlink at resolution time must be split correctly; do not let escapes degrade to "no org packs".

### IC-04 — Round-trip, legacy inline, fetch reporting, contract schema (Thread A)
- **Purpose**: Persist/read `subdir` on both config shapes; report effective-root artifact count at fetch; align the documented contract.
- **Relevant requirements**: FR-005, FR-006, FR-007, FR-008.
- **Affected surfaces**: `_pack_to_yaml_dict`, `_build_legacy_single_pack` (`org_pack_config.py`); `specify_cli/doctrine/snapshot.py` + `cli/commands/doctrine.py` (fetch reporting); `kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: `_build_legacy_single_pack` currently drops `subdir` — easy to fix canonical shape but miss the legacy read path.

### IC-05 — YAML-library documentation (Thread B)
- **Purpose**: Honest ruamel-vs-PyYAML rule, verified against ≥3 named sites, naming the mixed-usage sites.
- **Relevant requirements**: FR-009, SC-004.
- **Affected surfaces**: charter/doctrine docs under `docs/`; cite `org_pack_config.py` (ruamel) vs `org_pack_loader.py:38` (PyYAML) + the 3 dual-use modules.
- **Sequencing/depends-on**: none (parallel lane).
- **Risks**: must declare current-vs-aspirational; cannot assert a clean invariant that does not exist.

### IC-06 — Tiered-standards styleguide + DRG edge (Thread C / #2096)
- **Purpose**: A non-orphan `styleguide` defining core-vs-glue tiers mapped to named `src/` areas, with a per-tier rigour table.
- **Relevant requirements**: FR-010, FR-011, SC-005, C-001, C-004.
- **Affected surfaces**: `src/doctrine/styleguides/built-in/<name>.styleguide.yaml`; an inbound `suggests`/`requires` edge from an existing directive/paradigm; `spec-kitty doctrine regenerate-graph`; a non-orphan test.
- **Sequencing/depends-on**: graph-regeneration is a single-writer step — serialize the `graph.yaml` regen after any other graph-touching change (Thread A does **not** touch `graph.yaml`, so C is otherwise independent).
- **Risks**: orphan stub passes naively — FR-011 edge + non-orphan test prevent doctrine theater; no CI/agent-effort bleed (C-001).

### IC-07 — applies_to_languages guard + diagnostic (Thread D / #2092)
- **Purpose**: Fail loud at authoring for `any`/`all` language tokens; name scope-filtered artifacts in the catalog-miss diagnostic.
- **Relevant requirements**: FR-012, FR-013, SC-006, C-006.
- **Affected surfaces**: `spec-kitty doctrine validate` (guard); `src/doctrine/shared/scoping.py:24` (`applies_to_languages_match`); `src/charter/_catalog_miss.py` (present-but-scope-filtered branch).
- **Sequencing/depends-on**: none (parallel lane); de-risks IC-06 (a `[any]`-scoped styleguide would be silently dropped).
- **Risks**: prefer validate-time rejection over silent query-time wildcarding (C-006), so authors see the error where they write it.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*
