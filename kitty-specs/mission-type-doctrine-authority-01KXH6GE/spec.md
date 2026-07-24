# Feature Specification: Mission-Type Doctrine Authority

**Mission:** mission-type-doctrine-authority-01KXH6GE
**Tracker:** [#883](https://github.com/Priivacy-ai/spec-kitty/issues/883) (slice 1 of the `specify_cli/missions` retirement; epics #461 / #901)
**Design authority:** [ADR 2026-07-14-2](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md) · [mission brief](../../docs/plans/engineering-notes/883-mission-type-authority-brief.md) · [research dossier](../../docs/plans/engineering-notes/883-research-synthesis.md)

> This spec states **what** must be true and **why**. The **how** is fixed by the
> ADR above (Accepted); the plan phase turns it into design artifacts. Requirements
> are written to be testable at the behaviour level.

## Overview

Spec Kitty resolves each mission type's rules, steps, and gates through two
parallel trees (`src/doctrine/missions/` and derived `src/specify_cli/missions/`)
and three competing governance surfaces, with a hardcoded `software-dev` default
woven through the core loop. As a result a documentation, research, or plan mission
that never set a template can **silently inherit software-development doctrine**
(test-first, implementation architecture, code review). This mission makes the
doctrine **MissionType artefact the single, load-bearing source of truth** for
"what is this mission type, what governance applies, what gates are checked, what
steps does it contain?", routes resolution through one charter-mediated
doctrine → charter → core path, closes the leak, and demotes `software-dev` to a
peer mission type — as the first slice of retiring the duplicate tree.

## Intent Summary (confirmed)

- **Primary actors:** (1) a mission author running a documentation / research /
  plan mission; (2) a doctrine maintainer authoring or overriding mission-type
  governance; (3) the Spec Kitty runtime resolving a mission's context.
- **Trigger:** the runtime resolves governance / gates / steps for a mission of a
  given type (at prompt build and at step bootstrap).
- **Desired outcome:** the mission receives exactly its own mission type's doctrine
  — never software-dev by default — sourced from the doctrine tree.
- **Invariant that must always hold:** a non-software mission never resolves
  software-dev-only doctrine unless a project or mission policy explicitly selects
  it; an unknown mission type fails loudly rather than falling back to software-dev.
- **Canonical term:** **MissionType** (doctrine artefact). Per the Terminology
  Canon, the domain object is a **Mission**, never a "feature".

## User Scenarios & Testing

1. **Non-software governance (happy path).** A documentation mission author runs
   the workflow; the resolved governance and step context contain documentation
   doctrine (audience, Divio type, plain language, accessibility, freshness,
   source-of-truth, publication, review flow) and **no** software-dev-only doctrine.
2. **Software-dev unchanged.** A software-dev mission author runs the workflow; the
   resolved governance, gates, and steps are behaviourally identical to today.
3. **Unknown type fails loudly.** A mission whose recorded type is missing or
   unrecognised produces a clear, remediable error on every resolution path — never
   a silent software-dev load.
4. **Empty grain is legitimate.** A known mission type that declares no
   action-scoped governance for a given step resolves to an empty set for that step
   without error.
5. **Project customises a type.** A project adds or overrides governance for one
   mission type without editing the project charter or the shipped doctrine, and
   the override wins over the shipped baseline with a reported collision.
6. **One source of truth for gates.** The artefacts a mission is expected to
   produce (its gates) resolve from the doctrine tree; the duplicate `specify_cli`
   copies no longer exist and no reader depends on them.

## Domain Language

| Term | Meaning |
|------|---------|
| **MissionType artefact** | The doctrine declaration that is the single source of truth for a mission type's governance, gates, and steps. Load-bearing after this mission. |
| **Type-grain governance** | Governance that applies to a whole mission type (referenced sibling `governance-profile.yaml`). |
| **Action-grain governance** | Governance scoped to one action/step of a mission type (action index). |
| **The swap** | Making the doctrine path live and removing the derived `specify_cli/missions/` copies, without the user noticing a behavioural change. |
| **Per-type override** | A project-layer customisation of one mission type's governance, resolved through the shipped → org → project overlay. |
| **Transitional parity scaffold** | A temporary test proving the swap is behaviour-preserving; added at a swap's start and deleted before merge. |

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Governance/steps/gates resolution is keyed off the mission type recorded in mission metadata; it is never inferred from a template selection and never defaults to `software-dev`. | Draft |
| FR-002 | A documentation, research, or plan mission resolves only its own mission type's doctrine; no software-dev-only doctrine is included unless a project or mission policy explicitly selects it. | Draft |
| FR-003 | A mission whose recorded mission type is **present but unrecognised** raises a clear, remediable error on every governance-resolution path (prompt build and step bootstrap); the resolver never silently falls back to `software-dev`. A type that is unrecognised as *shipped* but has a resolvable project override is not "unknown" and resolves via that override (see FR-011). | Draft |
| FR-003a | A **typeless / mission-less** governance-context caller (e.g. dispatch, planning from the repo root, workflow rendering) receives a defined **neutral/degrade** result — never a `software-dev` load. Where the path can supply a mission type explicitly (e.g. planning-from-root via an explicit flag) it must; where it genuinely has no mission, it degrades without erroring. | Draft |
| FR-004 | A known mission type with an empty governance grain for a step resolves to an empty set for that step without error. | Draft |
| FR-005 | Each non-software built-in mission type (documentation, research, plan) ships a populated governance set covering its domain requirements (documentation: audience, Divio type, plain language, accessibility, freshness, source-of-truth, publication, review flow; research: decision/evidence + investigation; plan: decomposition + design + decision capture). | Draft |
| FR-006 | The doctrine MissionType artefact is the single source of truth for a mission type's governance, gates, and steps; the runtime resolves all three through one charter-mediated path. | Draft |
| FR-007 | A mission type's gates (expected artifacts) resolve from the doctrine tree, with the drifted content reconciled **upward** into the doctrine tree first. The reader flip and removal of the duplicate `specify_cli/missions/*/expected-artifacts.yaml` copies run as a **detachable, non-blocking** step that must not gate the mission's enforcement checks; on deep drift the final flip may defer to a later slice while the reconciliation still lands. | Draft |
| FR-008 | Step-contract resolution for a mission type flows through the doctrine MissionType artefact, not a `specify_cli` copy. | Draft |
| FR-009 | `software-dev` is resolved as a peer mission type with no special-casing in the resolution path; its effective governance, gates, and steps are preserved. | Draft |
| FR-010 | The inert per-type `governance_refs` field and its dangling references are removed; all governance references resolve in the doctrine reference graph (no danglers). | Draft |
| FR-011 | A project can override a mission type's governance without editing the project charter or shipped doctrine; resolution composes shipped → org → project layers and reports collisions. | Draft |
| FR-012 | A single mission-type canonicalizer resolves the mission-type key consistently across the `charter` and `specify_cli` boundaries and removes the `software-dev` governance default (`get_mission_type`), closing the leak on the governance/dossier path within this slice. It respects the layer rule (C-001). | Draft |
| FR-013 | The resolver **forbids** the same doctrine artifact appearing in both the type-grain and the action-grain, compared on **canonical URN** (not raw string form); a double declaration is a construction-time error, not a silent de-duplication. | Draft |

## Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Software-dev behaviour is preserved across the swap. | The resolved governance text and the resolved required-artifact (gate) set for a `software-dev` mission are identical before and after the change (0 diffs), proven by a transitional parity scaffold before its removal. | Draft |
| NFR-002 | Code quality holds. | `ruff` and `mypy --strict` report 0 issues / 0 warnings on changed code; no new `# noqa` / `# type: ignore` / per-file ignores. | Draft |
| NFR-003 | Complexity ceiling. | Every new/modified function has cyclomatic complexity ≤ 15 (ruff C901 / Sonar S3776). | Draft |
| NFR-004 | Reduced `specify_cli/missions` dependence. | When the detachable dossier flip lands (FR-007), the dossier gate reader reads the doctrine tree, 0 readers reference `specify_cli/missions/*/expected-artifacts.yaml`, and those copies are deleted. If the final flip defers on deep drift, the upward reconciliation still lands and the deferral is recorded — the deferral must not be silent. | Draft |
| NFR-005 | Enduring tests verify behaviour, not the removed path. | Enduring coverage lives as doctrine-module + integration tests; 0 parity/snapshot scaffolds referencing the removed path remain at merge. | Draft |
| NFR-006 | Non-leakage is enforced, not aspirational. | An automated test proves each non-software type's resolved (type ⊕ action) set is disjoint from a curated software-dev-only denylist, with both sets normalized to **canonical URNs** before comparison; a **non-vacuity twin** — exercised through an action name **shared** across mission types so it cannot pass vacuously — proves `software-dev` does resolve that denylisted set. | Draft |
| NFR-007 | Governance resolution is deterministic. | Resolved governance renders in a deterministic order; two resolutions of identical inputs produce byte-identical output (verified at the doctrine-module level). | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The `charter/` layer must not import `specify_cli` (existing layer rule); the single mission-type canonicalizer must respect that boundary. | Draft |
| C-002 | No surviving parity ratchet, and no code (wrapper, shim, preserved signature) kept solely to avoid test-suite churn. Tests are updated to the new behaviour. | Draft |
| C-003 | No new content is added to `specify_cli/missions/`; no "keep the two trees in sync" guard is introduced. | Draft |
| C-004 | `template_set` is retained for template-file selection and removed as the mission-type proxy in governance routing. | Draft |
| C-005 | (Q1) The MissionType artefact references the sibling `governance-profile.yaml` for type-grain governance (not absorbed). (Q2) The per-type override rides the `doctrine/base.py` overlay stack (`id` on the profile + a `BaseDoctrineRepository` subclass), not a bespoke second merge. | Draft |
| C-006 | Slice-1 scope is governance + gates + steps, including the single canonicalizer that removes the `mission.py` **governance** default (FR-012). Template resolution, the remaining `specify_cli/missions` readers (enumeration, mission-runtime, copy step), the `mission.py` **template-file-selection** fallback removal, tree deletion, and the mission-instance addendum layer are later slices. | Draft |
| C-007 | Terminology Canon holds: **Mission**, never "feature"; no legacy terminology (guarded by `tests/architectural/test_no_legacy_terminology.py`). | Draft |

## Success Criteria

- **SC-001** — In an integration run, a documentation / research / plan mission resolves **zero** software-dev-only doctrine artifacts.
- **SC-002** — An unknown mission type yields a clear, remediable error **100%** of the time; there is no silent software-dev fallback on any resolution path.
- **SC-003** — A `software-dev` mission shows **no** behavioural change (governance + gates identical before/after).
- **SC-004** — Each of documentation, research, and plan has a **non-empty** governance set that covers its named domain requirements.
- **SC-005** — When the detachable dossier flip lands, the dossier gate reader reads the doctrine tree and the `specify_cli/missions/*/expected-artifacts.yaml` copies **no longer exist**; if the final flip defers on deep drift, the upward reconciliation has still landed and the deferral is explicitly recorded (never silent).
- **SC-006** — The non-leakage test (with its non-vacuity twin) passes and is an enduring doctrine-module/integration check; no transitional parity scaffold survives merge.
- **SC-007** — Step-contract resolution for each mission type reads the doctrine MissionType artefact; the `specify_cli` step-contract readers are migrated (0 remaining) and any transitional parity scaffold for the step swap is deleted before merge.

## Key Entities

- **MissionType artefact** — the doctrine declaration of a mission type; references its governance (`governance-profile.yaml`), its gates (expected-artifacts), and its steps (action sequence + step contracts).
- **ResolvedMissionType** — the resolved bundle the core consumes (governance, action_sequence, expected_artifacts/gates, step_contracts populated in slice 1; template_set later).
- **Governance grains** — type-grain (`governance-profile.yaml`) unioned with action-grain (action index); the same artifact is **forbidden** in both grains, compared on canonical URN (FR-013).
- **Per-type override** — a project-layer `governance-profile.yaml` resolved through the shipped → org → project overlay.

## #883 Coverage (partial close)

This mission delivers the layered, mission-aware governance #883 asks for at three
layers — `project_charter ⊕ shipped_mission_type ⊕ project_override` (the project
override is FR-011) — plus the leak closure and the doctrine-as-authority swap. The
**fourth** layer, the per-mission-**instance** governance addendum, is deliberately
deferred (Out of Scope). Therefore this mission **partially** addresses #883 and
must **not** use a PR auto-close keyword for it; it relates-to / advances #883, with
the instance-addendum layer tracked as a follow-up.

## Assumptions

- The ADR (2026-07-14-2) and mission brief are the authoritative design; where this spec and the ADR differ, the ADR governs the mechanism.
- The mission executes in the `spec-kitty-gate-doctrine` clone on branch `mission/883-mission-type-governance-profiles`; the whole branch becomes an upstream PR the operator merges.
- FR-005's per-type governance sets require authoring **6–8 net-new DRG-resolvable doctrine artifacts** (per the ADR: Divio-type, plain-language, accessibility, publication, freshness-SLA styleguides; a research citation-discipline artifact; and the referenced-but-missing `spike-timebox-policy` procedure). Work-package sizing for the content lane must be driven by that artifact inventory, not by the requirement count alone.
- Two items are settled inside their work packages (not at spec level): the exact software-dev-only denylist membership for the non-leakage test, and the per-entry degrade behaviour for the mission-less governance-context callers.

## Out of Scope (explicit — later slices of the retirement epic)

- Template (`template_set`) resolution through the artefact.
- Migrating mission enumeration / `mission-runtime` readers off `specify_cli/missions/`.
- Removing the `meta.json`-less **template-file-selection** `software-dev` fallback in `mission.py` (the `get_mission_type` **governance** default *is* removed this slice — FR-012).
- Deleting the doctrine → specify_cli copy step and the `specify_cli/missions/` tree.
- The mission-instance governance addendum layer (designed in the ADR, deferred).
