---
name: "058 Architectural Review Findings"
description: "Architect Alphonso review of mission 058 (Mission Repository Encapsulation) against 2.x vision — 4 findings, AR-1 critical"
type: architecture-review
feature: "058-mission-template-repository-refactor"
date: "2026-03-27"
reviewer: architect
---

# Architectural Review: Mission 058 — Mission Repository Encapsulation

**Reviewer**: Architect Alphonso | **Date**: 2026-03-27 | **Status**: Pending HiC decisions

## AR-1 (CRITICAL): `resolve_*` methods violate `doctrine` → `specify_cli` dependency ban

**Principle**: Doctrine is a root dependency with zero external dependencies (C4 landscape, PR #305).

**Problem**: FR-004/FR-005 place `resolve_command_template()` and `resolve_content_template()` on `MissionTemplateRepository` in `src/doctrine/missions/repository.py`, with lazy imports from `specify_cli.runtime.resolver` (FR-018). Even lazy imports are runtime dependencies — `doctrine` becomes non-distributable standalone.

**Verified**: `src/doctrine/` currently has zero imports from `specify_cli` or `charter`. This must be preserved.

**HiC Decision**: **(B) — `CharterTemplateResolver` in `src/charter/template_resolver.py`**. Charter is the concretization of doctrine into local context-aware legislation. The 5-tier override chain is "how project context modifies doctrine defaults" — that's charter by definition.

**Corrected dependency model** (per HiC): `kernel` is the true zero-dependency root. `doctrine` depends only on `kernel`. `charter` depends on `doctrine` + `kernel` + may import `specify_cli.runtime`. `specify_cli` depends on all three.

**Applied**: FR-004, FR-005, FR-018 updated in spec. WP03 restructured: T014/T015 now create `CharterTemplateResolver` in `src/charter/`. Plan updated with decision rationale.

## AR-2 (MEDIUM): `ProjectMissionPaths` targets legacy charter location

**Problem**: WP09 places `ProjectMissionPaths` in `src/specify_cli/charter/mission_paths.py` but PR #305 extracted charter to `src/charter/` as standalone package. Both directories exist; legacy will eventually be removed.

**Fix**: Target `src/charter/mission_paths.py` instead.

## AR-3 (LOW): `MissionTemplateRepository` not wired into `DoctrineService`

**Context**: `DoctrineService` is the lazy aggregation facade for all doctrine repositories but doesn't include `MissionRepository`. The rename + API expansion is a good opportunity to integrate.

**Pre-existing gap**: Not caused by 058, but 058 is the right time to address it.

## AR-4 (LOW): Class name "Template" is reductive

**Problem**: Class provides 6 asset types (command templates, content templates, action indexes, action guidelines, mission configs, expected artifacts). Only 2 are templates. `MissionAssetRepository` would be more accurate.

**Note**: HiC chose `MissionTemplateRepository` in the spec. Flagging for awareness.
