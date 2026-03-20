# Research: State Architecture Cleanup Phase 2

**Feature**: 054-state-architecture-cleanup-phase-2
**Date**: 2026-03-20
**Source**: Obsidian evidence vault 007-spec-kitty-2x-state-architecture-audit (refresh 2026-03-20)

## Overview

No unknowns remain. All design decisions were resolved during discovery (constitution Git policy) and planning (atomic write utility approach, active-mission removal strategy). This document records the decisions and their rationale for traceability.

## D1: Atomic Write Utility Location

**Decision**: `src/specify_cli/core/atomic.py`
**Rationale**: The `core/` package already contains cross-cutting utilities (`project_resolver.py`, `events/`). An atomic write function is a foundational utility used by 9+ modules across the package.
**Alternatives considered**:
- Inline per module — rejected: 9 copies of identical logic
- `src/specify_cli/utils.py` — rejected: core/ is the established location for shared internals

## D2: Active-Mission Removal Approach

**Decision**: Hard removal, no deprecation period
**Rationale**: The migration `m_0_8_0_remove_active_mission.py` (v0.8.0) already declared the marker "no longer used." Production code reading it is a cleanup gap, not intentional backward compatibility. The switch_cmd was also removed in v0.8.0.
**Alternatives considered**:
- Deprecation warning for one release cycle — rejected: the deprecation period already passed (v0.8.0 → v2.0.9 is well past one cycle)
- Keep as read-only fallback with warning — rejected: the vault audit proved this fallback produces incorrect results (mission mismatch)

## D3: Constitution Git Policy

**Decision**: Hybrid — commit shared state, ignore local state
**Rationale**: `answers.yaml` and `library/*.md` define the project's way of working (team knowledge). `references.yaml` contains local machine paths that cause merge conflicts.
**Alternatives considered**:
- Commit everything — rejected by user: `references.yaml` causes merge conflicts
- Ignore everything — rejected by user: constitution is part of the project way of working
- Ignore `references.yaml` + `library/*.md` — rejected by user: library is shared knowledge, only references are local

## D4: Acceptance Deduplication Direction

**Decision**: Canonical implementation in `acceptance.py`, thin re-export wrapper in `acceptance_support.py`
**Rationale**: The standalone script needs `acceptance_support.py` to exist as an import path. Moving logic into the canonical module and re-exporting satisfies both import paths with zero duplication.
**Alternatives considered**:
- Delete `acceptance_support.py` entirely — rejected: breaks standalone `tasks_cli.py` import path
- Keep both copies with regression test — rejected: the audit explicitly calls this out as maintenance overhead

## D5: Legacy Bridge Import Handling

**Decision**: Top-level import, remove `ImportError` catch, keep `Exception` catch for bridge update failures
**Rationale**: `legacy_bridge.py` is in-tree, tested, and required on 2.x. An ImportError now indicates a packaging regression, not a transitional state. Bridge update failures are non-critical (canonical state is already persisted).
**Alternatives considered**:
- Keep silent ImportError catch — rejected: hides real packaging regressions
- Remove both ImportError and Exception catches — rejected: bridge update failures should not block canonical state transitions

## Evidence Cross-References

All decisions are backed by specific observations in the Obsidian evidence vault:

| Decision | Vault Finding | Evidence Log Entry |
|----------|-------------|-------------------|
| D1 | "single writer cleanup incomplete" (§ New Finding 3) | "Remaining non-atomic state writes" |
| D2 | "active-mission is still a live execution surface" (§ New Finding 1) | "Minimal repro for mission mismatch" |
| D3 | "Constitution state still only partially aligned" (§ Still True 4) | "inside_repo_not_ignored surfaces" |
| D4 | "implementation still duplicated" (§ New Finding 4) | "Duplicated acceptance implementations" |
| D5 | "transitional fallback now suspicious" (§ New Finding 5) | "Transitional fallback that appears vestigial" |
