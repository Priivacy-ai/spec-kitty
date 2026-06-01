---
work_package_id: WP05
title: Agent-profile load diagnostics + lineage via DRG
dependencies:
- WP03
- WP06
requirement_refs:
- FR-002
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/agent_profiles/repository.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/agent_profiles/repository.py
- src/doctrine/agent_profiles/diagnostics.py
- src/doctrine/agent_profiles/__init__.py
- src/doctrine/service.py
- tests/doctrine/test_profile_diagnostics.py
role: implementer
tags: []
---

# WP05 — Agent-profile load diagnostics + lineage via DRG

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Retain structured diagnostics for skipped profile files (FR-005/006/007), keep them deterministic (NFR-002) and zero for built-ins (NFR-005), and migrate the profile hierarchy resolver to consume `specializes_from` via **DRG traversal** rather than the (now-removed) field (FR-002, C-009). Collapse the three duplicated layer loops while instrumenting (R-011-B).

## Context

- Spec: FR-002, FR-005..007, NFR-002/005; research R-011-B (AgentProfileRepository is the only repo off `BaseDoctrineRepository`; 5 `warnings.warn` drop sites + silent `continue`/`pass`; unsorted `glob`/`rglob`; lineage read from the field at `:476-580`).
- Data model: §4. Contract: [../contracts/wave1-diagnostics.md](../contracts/wave1-diagnostics.md) C1.1-C1.3; [../contracts/wave2-authoring-migration.md](../contracts/wave2-authoring-migration.md) C2.3.

### Code map

- `src/doctrine/agent_profiles/repository.py` — drop sites `:250,279,311,342,371`; silent `:241,271,336`; `delete()` swallow `:744`; `_load()` `:232-316`; `_load_org_profiles_from_dir()` `:318-376`; lineage `:476-580`; `list_all()` `:437`.
- `src/doctrine/service.py:130-138` — `agent_profiles` cached property.
- Post-WP06: `AgentProfile.specializes_from` field is **gone**; lineage must come from the merged DRG (post-WP03 `doctrine.drg.merge`).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`.
- Depends on WP06 (field removed) and WP03 (doctrine-merged DRG to traverse). Runs after both in its lane.

## Subtasks

### T019 — `SkippedProfile` record

**Steps**: Create `src/doctrine/agent_profiles/diagnostics.py` with a frozen `SkippedProfile{layer: str, path: str, profile_id: str | None, error_summary: str}`. Export from `__init__.py`.

**Validation**: - [ ] importable; frozen; typed.

### T020 — Route drop sites through `_record_skip`; add accessor

**Steps**:
1. Add `self._skipped: list[SkippedProfile]` and a private `_record_skip(layer, path, profile_id, error_summary)`.
2. Replace all five `warnings.warn` drop sites and the silent `continue`/`pass` skips (incl. `delete()` swallow) with `_record_skip(...)`. Use `validate_agent_profile_yaml()` (`validation.py:49`) for richer summaries where available.
3. Add `skipped_profiles() -> list[SkippedProfile]` returning a **sorted copy** (sort key `(layer_rank, path)`). Keep `list_all()` valid-only (FR-006).

**Validation**: - [ ] every skip is recorded; `list_all()` unchanged (valid-only).

### T021 — Collapse the three layer loops; sort scans

**Steps**: Extract one shared per-layer loader used by built-in/org/project (port toward the `BaseDoctrineRepository` overlay pattern without a full migration). Sort `rglob`/`glob` results so record order is deterministic (NFR-002).

**Validation**: - [ ] one loader path; scans sorted.

### T022 — Preserve diagnostics on `DoctrineService` (FR-007)

**Steps**: Confirm `DoctrineService.agent_profiles` caches the repo so `skipped_profiles()` survives; if construction discards anything, fix it. Expose diagnostics for all configured layers.

**Validation**: - [ ] `service.agent_profiles` accessed twice exposes the same diagnostics without re-scan.

### T023 — Lineage resolver via DRG traversal (FR-002, C-009)

**Steps**: Replace the `profile.specializes_from` reads in the hierarchy methods (`:476-580`) with traversal of `SPECIALIZES_FROM` edges in the doctrine-merged DRG (from WP03). Preserve parent/ancestors/root-detection/cycle-detection behavior. Lineage cycle must still be detected and reported.

**Validation**: - [ ] hierarchy + cycle detection work via DRG; no reference to the removed field remains (grep).

### T024 — Tests

**Steps**: `tests/doctrine/test_profile_diagnostics.py` covering: invalid profile retained with all fields; deterministic sorted records across two loads (NFR-002); `list_all()` valid-only; zero diagnostics for built-ins (NFR-005); lineage parent/ancestors/cycle via DRG.

**Validation**: - [ ] all green; ruff/mypy clean.

## Definition of Done

- [ ] `SkippedProfile` + accessor; all drop sites instrumented; loops collapsed; determinism; service preserves diagnostics; lineage via DRG; field no longer read.
- [ ] CC-2 gates pass.

## Risks

- The agent-profile merge semantics differ from the base repo (union-merge/`excluding`/kebab aliasing) — preserve them when collapsing loops (do not regress to `{**a,**b}`).
- Ordering matters: this WP assumes WP06 removed the field and WP03 provides the merged DRG. If the lane ordering is off, lineage reads will fail — verify dependencies in `lanes.json`.

## Reviewer Guidance (reviewer-renata)

- Confirm `list_all()` stays valid-only and a separate accessor exposes skips (FR-006).
- Confirm determinism (sorted at read boundary), and that lineage no longer touches the removed field.
- Incorrect doc/contract references are blocking, not warnings.
