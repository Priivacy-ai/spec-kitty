# Phase 0 Research — Mission-Type Doctrine Authority

All architectural unknowns were resolved before planning by a four-lens research
squad, an architect design pass, and an adversarial four-lens second-opinion squad,
then ratified in [ADR 2026-07-14-2](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md).
There are **no open `[NEEDS CLARIFICATION]` items**. This file records the decisions
in Decision / Rationale / Alternatives form; the full evidence (with file:line) is in
the [research dossier](../../docs/plans/engineering-notes/883-research-synthesis.md).

## D1 — Resolution seam

- **Decision**: One charter-mediated `resolve_mission_type_context(repo_root, *, mission_type=None, feature_dir=None) → ResolvedMissionType`, keyed off `meta.json`, subsuming `resolve_action_sequence` / `resolve_mission_type_governance` / `load_profile`.
- **Rationale**: These three already live in `charter/mission_type_profiles.py` and are already keyed by mission type; unifying them gives one path both consumers (prompt build + step bootstrap) read, and makes the `MissionType` artefact load-bearing.
- **Alternatives**: populate the inert `governance_refs` (rejected — no runtime reader, cannot carry tactics/styleguides, false freshness); fill `governance-profile.yaml` only (rejected — leaves the action-path leak).

## D2 — Governance declaration shape (Q1)

- **Decision**: The `MissionType` artefact **references** the sibling `governance-profile.yaml` for type-grain governance; action-grain stays in `actions/*/index.yaml`; the resolver unions them.
- **Rationale**: `governance-profile.yaml` is the live, schema'd (`extra="forbid"`), hard-failing surface the resolver already reads — lowest churn; the override rides it.
- **Alternatives**: absorb governance as a field on `mission_types/<type>.yaml` (rejected by operator — more churn, retires a live surface).

## D3 — Two grains, URN-normalized disjointness

- **Decision**: type-grain ∪ action-grain, with a **construction-time guard forbidding** the same artifact in both grains, compared on **canonical URN**.
- **Rationale**: string equality across `003-…` / `DIRECTIVE_003` / URN gives false assurance; forbidding (not de-duplicating) closes the double-declaration defect class by construction.
- **Alternatives**: silent de-dup (rejected — hides a real authoring error).

## D4 — Per-type override adapter (Q2)

- **Decision**: Ride the existing `doctrine/base.py` builtin → org → project overlay stack by adding an `id` to `MissionTypeProfile` + a `BaseDoctrineRepository[MissionTypeProfile]` subclass.
- **Rationale**: canonical layering + `DoctrineLayerCollisionWarning` + #832 org-layer support without a bespoke second merge site; the base loader keys on `id` (the real, named adapter cost).
- **Alternatives**: a bespoke field-merge in the resolver (rejected — duplicate merge site, the anti-pattern #2628 warns against).

## D5 — Close the leak (per-entry, off `meta.json`)

- **Decision**: Rewire the *live* `_load_action_doctrine_bundle` (`context.py:865`, via `build_charter_context` + `build_charter_context_json`) to key off `meta.json mission_type`; delete the dead `_render_action_scoped`/`_append_action_doctrine_lines` pair; split `template_set` (kept for template-file selection, removed as governance proxy); a single canonicalizer removes the `mission.py:575` governance default. Behaviour is **per entry**: prompt path supplies `feature_dir`; planning-from-root requires explicit `--mission-type`; mission-less callers degrade neutrally, never software-dev.
- **Rationale**: the second opinion proved the ADR's first-draft anchors were dead code and that `mission.py:575` leaks on the dossier path behind the `charter ↛ specify_cli` boundary.
- **Alternatives**: blanket hard-error on all paths (rejected — breaks dispatch/workflow which have no mission).

## D6 — Gates/dossier swap (detachable)

- **Decision**: Reconcile the drifted `expected-artifacts.yaml` **upward** into the doctrine tree, build a `ConfigResult → ExpectedArtifactManifest` adapter (+ cache), flip the dossier reader, delete the `specify_cli` copies — as a **detachable, non-blocking** lane whose final flip may defer to slice 2 on deep drift.
- **Rationale**: it is a type-boundary crossing over already-drifted content (`specify_cli` ahead — `charter-lint.decay`/`lint-report`); reconcile-first + a transitional dossier-parity scaffold keeps the swap user-invisible; isolating the lane keeps a dossier regression from gating the governance seam.
- **Alternatives**: naive repoint (rejected — silently drops software-dev gate entries); firm in-scope deletion (rejected — over-commits a non-gating swap).

## D7 — Test posture

- **Decision**: parity/snapshot tests are **transitional** (added at each swap's start, deleted before merge); enduring verification is **behavioural** at doctrine-module + integration level; non-leakage (URN denylist) + non-vacuity twin (shared action name) + deterministic ordering are the enduring guards; **no code kept solely to avoid test churn**.
- **Rationale**: operator-mandated; a surviving parity ratchet entrenches the split the swap removes, and compat shims are dead weight.
- **Alternatives**: a surviving byte-snapshot gate (rejected — ratchet); freezing the substring content-suite (rejected — it asserts the fallback being deleted).

## D8 — Scope (Q3)

- **Decision**: slice 1 = governance + gates + **steps** (step-contract resolution through the artefact); templates and the remaining `specify_cli/missions` readers + tree deletion + the mission-instance addendum are later slices.
- **Rationale**: makes the artefact load-bearing for three of the four axes now; templates are the cleanest defer.
- **Alternatives**: governance-only (rejected — leaves gates leaking); full merge now (rejected — unbounded blast radius).
