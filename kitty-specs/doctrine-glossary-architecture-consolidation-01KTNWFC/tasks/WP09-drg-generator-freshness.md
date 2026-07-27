---
work_package_id: WP09
title: DRG generator + freshness gaps
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/doctrine-glossary-consolidation-01KTNWFC
merge_target_branch: feat/doctrine-glossary-consolidation-01KTNWFC
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-glossary-consolidation-01KTNWFC. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-glossary-consolidation-01KTNWFC unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-glossary-architecture-consolidation-01KTNWFC
base_commit: 7e8ba507b05d4a38ba4edf81f11008a583d0bc29
created_at: '2026-06-11T14:50:36.655583+00:00'
subtasks:
- T026
- T027
- T028
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "793145"
history:
- '2026-06-09: created by /spec-kitty.tasks (planner-priti)'
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
owned_files:
- src/doctrine/drg/**
- src/glossary/drg_builder.py
- tests/doctrine/drg/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
Load your profile first: `/ad-hoc-profile-load python-pedro`.

## Objective
Close the DRG generator/freshness gaps (FR-009, #1755): a single **regeneration command** producing deterministic `graph.yaml`, and **symmetric profile-edge detection** so a declared edge is validated/detected in both directions. (Code only; the built-in graph/profile *data* re-curation is WP10.)

## Context
- Contract: `contracts/charter-extends-and-drg-regen.md` §C2. DRG code in `src/doctrine/drg/` + `src/glossary/drg_builder.py`; output `src/doctrine/graph.yaml` (owned by WP10 — this WP regenerates it only in tests).
- #1755: today there's no regeneration command and profile-edge detection is asymmetric.
- PROVENANCE STATUS (updated): the declared `provenance: str | None` field on `DRGNode`/`DRGEdge` **has shipped** (mission 01KTRC04; `_tag_source` returns `model_copy(update=...)` — no `object.__setattr__` sidecar). The `graph.yaml` serialization is unaffected (extractor excludes the field). This WP does NOT need to create the provenance field — it is already present. Focus on regeneration command + symmetric edge detection only.

## Subtasks
### T026 — Regeneration command
Provide a deterministic `spec-kitty`-surfaced regeneration of `graph.yaml` (idempotent: regenerate-twice → byte-identical).
### T027 — Symmetric profile-edge detection + freshness
Detect/validate profile edges (e.g. `specializes_from`, `delegates_to`) symmetrically; wire into the freshness gate.
### T028 — Tests
Regenerate-twice-identical test; freshness gate green; `ruff` + `mypy` clean.

## Branch Strategy
Plan/merge target `feat/doctrine-glossary-consolidation-01KTNWFC`; per-lane worktree from `lanes.json`. **No dependencies — start immediately (parallel code lane).**

## Ownership & out-of-map edits
Owned: `src/doctrine/drg/**`, `src/glossary/drg_builder.py`, `tests/doctrine/drg/**`. **Out-of-map edits allowed with a recorded one-line rationale.** The committed `graph.yaml` is WP10's — only regenerate it in tests here.

## Review / Sign-off (R-07)
Doctrine sign-off + reviewer profile; reviewer verifies determinism + symmetric detection.

## Definition of Done
- Regeneration command deterministic; symmetric edge detection; freshness gate green; tests + ruff + mypy clean.

## Risks
- Non-determinism (ordering/timestamps) in graph output — sort + stamp deterministically.

## Activity Log

- 2026-06-11T15:05:20Z – claude – shell_pid=754690 – DRG freshness: regenerate-graph CLI (--check twin of freshness gate, deterministic), symmetric profile-edge validation + lineage DAG check wired into validate_graph; 86+14+20+93 tests green, mypy --strict clean. Implementer: python-pedro, lane-h d7ad400dc.
- 2026-06-11T15:05:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=793145 – Started review via action command
- 2026-06-11T15:11:00Z – user – shell_pid=793145 – Review passed: deterministic regenerate-graph CLI (byte-identical x2, generated_at=STATIC, sorted iteration, reachable via doctrine app, --check fresh+exit0); symmetric validate_profile_edges wired into validate_graph+assert_valid (independently proved: both endpoints flagged, specializes_from 2-cycle caught, delegates_to cycle allowed, dangling not double-reported); 89 drg+CLI tests green, mypy --strict clean (drg/ + doctrine.py), ruff clean; graph.yaml untouched (WP10-owned), no provenance sidecar, no terminology violations; out-of-map CLI edit intrinsic to WP objective + commit-message rationale.
