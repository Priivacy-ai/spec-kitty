# Implementation Plan: Charter as Sole Door: Close Bypass Access Paths

**Branch**: `feat/charter-sole-door-bypass-closure` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/charter-sole-door-bypass-closure-01KZ3WAA/spec.md`

The planner did not begin until all planning questions were answered — captured below (spec-time operator
scope decisions + a Phase 0 research squad that surfaced four planning-time corrections, each resolved with
the operator before this plan was written; see spec.md's "Revised at planning time" notes per user story).

## Summary

Make `charter.resolver.DoctrineService` (`src/charter/resolver.py`) the sole, fully-gated access path to
provisioned doctrine assets. The mission (a) eliminates 5 of 7 flagged direct `AgentProfileRepository`
construction sites plus 9 raw `DoctrineService` construction sites (6 original + 3 found by a post-plan
adversarial squad) — excluding 2 sites that turned out to access a legitimately separate `.kittify/profiles`
directory (C-006) — (b) adds resolution methods to the factory so `CharterTemplateResolver`'s one real
caller stops importing `doctrine.resolver` directly, (c) consolidates 3 duplicate missions-root path
hardcodes onto one promoted authority (deferring full `pack_paths` convergence to `#3091`), (d) extends
factory activation-gating to 6 mechanical kinds and separately gates the structurally-different
`mission-type` token via `resolve_mission_type_context()` only (not `MissionTypeProfileRepository`'s own
file — WP06 ownership boundary), (e) unifies five divergent "canonical" construction
paths discovered as a byproduct (2 named builders + 3 inline reimplementations) into one, (f) closes a live
`._inner` reach-around that would otherwise defeat the whole mission, and (g) ships non-vacuous,
zero-tolerance, qualname-resolving architectural gates so none of this quietly regresses. A pre-mission
performance baseline is captured before any site migrates (NFR-005). Five adjacent GitHub issues (#2986,
#3036, #3039, #3091, #3022) are confirmed out of scope, stay deferred, and each gets a durable tracker trace
(FR-011). A 4-lens post-plan adversarial squad independently verified the Phase-0 research and found the
additional construction sites, the `._inner` gap, an IC-sequencing bug, and several fakeable-assertion gaps
— all folded in above rather than discovered mid-implementation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — typer, ruamel.yaml, pydantic/dataclasses (`PackContext`,
  `ArtifactKind`), `importlib.resources` (`MissionTemplateRepository.default_missions_root()`); no new
  third-party dependencies
**Storage**: files — `.kittify/charter/charter.yaml`, `.kittify/profiles/` (explicitly untouched, C-006),
  `packs/built-in/`, `src/doctrine/missions/`
**Testing**: pytest; targeted surfaces per WP (see Project Structure below); existing named gates read but
  not duplicated — `tests/architectural/test_org_activation_seam.py`,
  `tests/architectural/test_layer_rules.py`, `tests/architectural/test_runtime_charter_doctrine_boundary.py`
  (referenced to confirm the "boundary ratchet" comment doesn't trip it); new non-vacuous gates per FR-007
**Target Platform**: Linux/macOS/Windows CLI
**Project Type**: single project (`src/{charter,doctrine,specify_cli,runtime,mission_runtime}/`)
**Performance Goals**: NFR-005 — p95 `spec-kitty agent tasks status` render latency on a 100+-WP fixture
  project stays within 10% of pre-mission baseline
**Constraints**: C-001 (one canonical factory, one unified builder); C-002 (zero exceptions for in-scope
  sites); C-003 (five issues + #3101 stay untouched); C-004 (PRs only, coord hygiene); C-005 (red-main
  discipline); C-006 (`.kittify/profiles` out of scope)
**Scale/Scope**: 9 FRs across 6 implementation concerns; 11 direct-construction sites (5 profile-repo + 6
  raw-service) + 3-consumer resolver axis + 3 hardcoded-path sites + 6 mechanical kinds + 1 separate
  mission-type repository + 1 builder unification + zero-tolerance gates for all four categories

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Single canonical authority** (Governing Principle; DIR-044). ✅ The mission's spine: `charter.resolver.
  DoctrineService` becomes the one factory every in-scope site routes through, built by one unified builder
  (FR-008) — the two-builder divergence found during planning is exactly the kind of second-authority drift
  this principle exists to close, and it is folded in rather than left standing.
- **Architectural alignment** (DIR-001). ✅ Respects the sanctioned `charter → doctrine` import direction;
  `doctrine/resolver.py`'s tier functions stay where they are (their own documented rationale for living
  there), only the entry point moves onto the factory (FR-003) — extends the existing pattern already proven
  at `specify_cli/runtime/resolver.py`'s tier-5 routing, rather than inventing a second charter-layer resolver
  object.
- **ATDD-first** (C-011). ✅ Every implementation WP commits a failing-first test (a red assertion that the
  bypass call exists, or that the ungated kind leaks unfiltered data) before the routing/gating change lands.
- **Non-vacuous gates** (DIR-043). ✅ FR-007's gates ship with self-mutation proofs per category, frozen
  zero-tolerance baselines (no allowlist, per C-002) — mirrors the WP10/WP11 idiom from
  `doctrine-charter-split-unification-01KZ0SRB`, extended rather than duplicated.
- **Fold only domain-matched debt** (Standing Order #2). ✅ FR-008 (builder unification) is folded in because
  it is the same factory this mission is already making the sole door; the five adjacent issues (#2986,
  #3036, #3039, #3091, #3022) are confirmed NOT domain-matched (research squad) and stay deferred; the
  `.kittify/profiles` sites are confirmed a different concern (C-006) and are excluded, not force-fitted.
- **Terminology canon.** ✅ Mission (not Feature) throughout; no `--feature` flags touched.
- **Git/workflow discipline** (DIR-045). ✅ Draft-PR-first; operator merges; coord topology
  (`kitty/mission-charter-sole-door-bypass-closure-01KZ3WAA`); issue-matrix row per folded issue.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-sole-door-bypass-closure-01KZ3WAA/
├── plan.md              # This file
├── spec.md              # Mission spec (9 FR + 5 NFR + 6 C), revised post-Phase-0
├── research.md          # Phase 0 — the four planning-time corrections + design decisions
├── data-model.md        # Phase 1 — ArtifactKind→gating-owner map, three-state contract, builder contract
├── contracts/           # Phase 1 — DoctrineService public-surface contract, MissionTypeProfileRepository
│                         #   activation contract, unified-builder contract
├── quickstart.md         # Phase 1 — how to verify the sole-door property post-mission
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── resolver.py                    # THE factory (FR-002/003/005): +6 mechanical kind properties,
│   │                                   #   +resolution methods for the 5-tier axis, +unfiltered mode
│   ├── resolution.py                  # retarget onto new factory methods (FR-003)
│   ├── context_renderers/template_include.py  # retarget onto new factory methods (FR-003)
│   ├── template_resolver.py           # CharterTemplateResolver — becomes a thin delegate or is retired
│   │                                   #   in favour of direct factory use (FR-003)
│   ├── profile_resolution.py          # route :81 through the factory (FR-001)
│   ├── compiler.py                    # route :802 through the factory (FR-002)
│   ├── mission_type_profile_repository.py  # builtin_missions_root() → promoted authority (FR-004);
│   │                                   #   UNCHANGED for FR-006 (WP06 ownership boundary)
│   ├── mission_type_profiles.py       # resolve_mission_type_context() activation-aware, sole FR-006 site
│   ├── doctrine_service_builder.py    # unify with specify_cli's builder (FR-008)
│   └── pack_context.py                # read-only reference — activated_<kind> fields already exist (FR-005)
├── doctrine/
│   ├── resolver.py                    # UNCHANGED — tier functions stay here (FR-003 rationale)
│   ├── service.py                     # read-only reference — raw per-kind properties already exist
│   └── missions/repository.py         # MissionTemplateRepository.default_missions_root() — PROMOTED
│                                       #   to single authority (FR-004), no code change, just new callers
├── specify_cli/
│   ├── doctrine_service_factory.py    # unify with charter's builder (FR-008)
│   ├── invocation/registry.py         # UNCHANGED at :48 (.kittify/profiles, C-006)
│   ├── runtime/home.py                # dev_roots :107-108 → promoted authority (FR-004)
│   ├── tool_surface/profiles/projection.py  # route :84 through factory + new lineage accessor (FR-001)
│   └── cli/commands/
│       ├── profiles_cmd.py            # UNCHANGED at :83 (.kittify/profiles, C-006)
│       ├── agent/tasks_status_cmd.py  # route :712,:823 through factory; NFR-005 latency measurement (FR-001)
│       ├── _doctrine_asset.py         # route :75 through factory (FR-002)
│       └── _doctrine_collect.py       # route :193,:283,:420,:828 through factory UNFILTERED mode (FR-002)
├── runtime/next/runtime_bridge_io.py  # route :576 through factory (FR-001)
tests/architectural/
├── test_org_activation_seam.py        # existing — extended, not duplicated
├── test_layer_rules.py                # existing — read-only reference
├── test_runtime_charter_doctrine_boundary.py  # existing — read-only reference (confirms non-blocking)
└── <new> test_charter_sole_door_*.py  # zero-tolerance gates, one per closed bypass category (FR-007)
```

**Structure Decision**: Single-project layered `src/` — no new top-level trees. All in-scope construction,
resolution, and path-authority changes land inside the existing `charter`/`doctrine`/`specify_cli` layers;
nothing crosses the sanctioned `charter → doctrine` direction upward, and the two `.kittify/profiles` sites
are deliberately left untouched in place (C-006) rather than moved.

## Complexity Tracking

*No charter-check violations — none.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs — one concern may
> become several WPs, and small concerns may merge.

### IC-01 — Direct construction sites eliminated + builder unification + `._inner` closure

- **Purpose**: Close all in-scope direct-construction bypasses (5 `AgentProfileRepository` + 9 raw
  `DoctrineService`, after the post-plan squad's 3 additional sites) and the single-canonical-authority gap
  across five divergent construction paths (2 named builders + 3 inline reimplementations), plus the
  `._inner` reach-around that would otherwise defeat every other IC's gating.
- **Relevant requirements**: FR-001, FR-002, FR-008, FR-010, NFR-001, NFR-005, C-002, C-006.
- **Affected surfaces**: `runtime_bridge_io.py:576`, `projection.py:84`, `tasks_status_cmd.py:712,823`,
  `charter/profile_resolution.py:81`, `charter/compiler.py:802`, `_doctrine_asset.py:75`,
  `_doctrine_collect.py:193,283,420,828`, `charter_runtime/lint/checks/org_layer.py:244,275`,
  `cli/commands/charter/generate.py:56`, `charter/doctrine_service_builder.py`,
  `specify_cli/doctrine_service_factory.py`, `invocation/registry.py:64`, `invocation/org_profiles.py:117`.
- **Sequencing, superseded (post-tasks squad — supersedes the post-plan-squad note below)**: unify the
  builders (FR-008) FIRST. The post-plan squad's original note here said FR-008's proof could only assert
  identical output across the 3 kinds gated at IC-01 time, deferring a 9-kind assertion to an IC-04-time
  follow-up. That staging is no longer applicable: the post-tasks squad merged FR-005's 6-kind work into the
  same work package (WP01) as the builder unification, so FR-008's regression proof asserts identical output
  across all 9 gated kinds in one unstaged pass — there is no cross-work-package sequencing constraint to
  observe, and no follow-up assertion to schedule. The new
  lineage/mutation accessor (pinned semantics: `contracts/charter-doctrine-service-contract.md`) should land
  alongside the builder unification, before `projection.py:84`, `runtime_bridge_io.py:576`, `registry.py:64`,
  and `org_profiles.py:117` are migrated onto it (all four need the same accessor — build it once).
- **Risks**: the accessor's two semantic questions (does mutation leak through the filter; does lineage
  traversal cross into deactivated parents) are now pinned in the contract file — implement against that
  text, do not re-derive at tasks time. The two `tasks_status_cmd.py` sites need the NFR-005 latency
  measurement, and that measurement needs a **pre-captured baseline** (see IC-00 below) — measuring only
  after the change lands makes "within 10%" unfalsifiable. `_doctrine_collect.py`'s 4 sites and the
  `org_layer.py`/`generate.py` sites must use the unfiltered mode explicitly, not a plain activation-aware
  swap (silent doctor/health regression). `org_layer.py:252-253`'s `except ImportError: pass` must become
  fail-closed, not merely rewrapped.

### IC-00 — NFR-005 baseline capture (must precede IC-01)

- **Purpose**: Make NFR-005's "within 10% of pre-mission baseline" falsifiable by actually capturing that
  baseline before any FR-001 site changes.
- **Relevant requirements**: NFR-005.
- **Affected surfaces**: a new or reused 100+-WP fixture project; the mission tracer file (baseline number
  recorded there per Standing Order #3).
- **Sequencing/depends-on**: none — this must run before IC-01's `tasks_status_cmd.py` sites are touched, on
  the merge-base commit.
- **Risks**: none identified; this is measurement, not code change. Skipping it is the risk (flagged by the
  post-plan squad as otherwise unfalsifiable).

### IC-02 — Template/command resolver axis routed through the factory

- **Purpose**: Give `charter.resolver.DoctrineService` resolution methods for the 5-tier axis so
  `CharterTemplateResolver`'s one real caller (`specify_cli/runtime/resolver.py`'s tier-5 routing) stops
  importing `doctrine.resolver` directly.
- **Relevant requirements**: FR-003, NFR-001, SC-002.
- **Affected surfaces**: `charter/resolver.py` (new methods), `charter/template_resolver.py`,
  `specify_cli/runtime/resolver.py` (construction-contract fix — see below).
- **Corrected scope (post-plan squad)**: `charter/resolution.py` and `charter/context_renderers/
  template_include.py` are dropped from this concern — both import only the `ResolutionResult`/
  `ResolutionTier` *types*, sanctioned by an existing facade contract, not resolution calls; there is nothing
  to retarget. `doctrine.template_catalog.resolve_template_by_id` (5 importers, including
  `template_include.py`'s real resolution call) is a genuine third tier surface the original FR-003 anchor
  missed entirely — it is named as explicit deferred debt (alongside `runtime/resolver.py`'s tier-1-4
  reimplementation) and is OUT of this concern's scope; do not fold it in without a separate scope decision.
- **Sequencing/depends-on**: independent of IC-01/IC-00; can run in parallel. Must resolve a real
  construction-contract mismatch: `specify_cli/runtime/resolver.py`'s `_charter_template_resolver_for()`
  helper is cached (`lru_cache`) and keyed on a `missions_root` string via `CharterTemplateResolver.
  from_missions_root(...)`, while `charter.resolver.DoctrineService` is constructed from `repo_root` via the
  unified builder — the WP must design this mapping explicitly (e.g. resolve `repo_root` at the same call
  site, or add a `from_missions_root`-equivalent path to the factory), not discover it mid-implementation.
- **Risks**: `doctrine/resolver.py`'s tier functions must NOT move — moving them fights the module's own
  documented rationale for living there (charter needs to import doctrine, not vice versa). The
  `specify_cli/runtime/resolver.py` tier-1-4 reimplementation and the `template_catalog` axis are both noted
  semantic-drift/scope risks but are explicitly OUT of this concern (do not touch them here).

### IC-03 — Missions-root path consolidation

- **Purpose**: Retarget the 3 duplicate missions-root hardcodes onto one promoted authority.
- **Relevant requirements**: FR-004, NFR-004, C-003, SC-003.
- **Affected surfaces**: `charter/mission_type_profile_repository.py:66`, `specify_cli/runtime/home.py:
  107-108`; `doctrine/missions/repository.py:98` (read-only — the promoted authority, no code change).
- **Sequencing/depends-on**: independent; small, mechanical.
- **Risks**: do not claim convergence with `doctrine.pack_paths.built_in_dir` in the PR description — that is
  `#3091`'s to deliver (NFR-004 requires this be stated explicitly, not implied away).

### IC-04 — Factory activation-gating extended to all 10 kinds (two shapes of work)

- **Purpose**: Close the "3 of 10 gated" gap — 6 kinds mechanically on the factory, 1 token (`mission-type`)
  structurally elsewhere.
- **Relevant requirements**: FR-005, FR-006, NFR-004, SC-004.
- **Affected surfaces**: `charter/resolver.py` (6 new properties, copy-paste of the `paradigms` pattern),
  `charter/mission_type_profiles.py::resolve_mission_type_context()` ONLY (new, non-mechanical filtering —
  post-tasks squad correction: `charter/mission_type_profile_repository.py` is a different WP's exclusive
  ownership for an unrelated change and must not be touched here).
- **Sequencing/depends-on**: FR-005 (mechanical) and FR-006 (mission-type) are independent of each other;
  FR-005 can run in parallel with IC-01/IC-02/IC-03. FR-006 should NOT be estimated or scheduled as if it
  were the same size as FR-005's six kinds — it is a different repository with no existing three-state
  precedent to copy.
- **Risks**: a bare-project regression per kind is mandatory (mirrors the `charter-pack-usage-journey`
  bare-project pin) — the classic failure mode here is a naive `sorted(activated or frozenset())` that
  silently empties a project that never activated anything.

### IC-05 — Durability gates + deferred-issue tracker hygiene

- **Purpose**: Ship the zero-tolerance, self-mutation-proven gates for all **five** bypass categories
  (including FR-010's `._inner` closure), and give the five confirmed-deferred issues a durable tracker
  trace, not just PR-description prose.
- **Relevant requirements**: FR-007, FR-010, FR-011, NFR-003, SC-005, SC-006.
- **Affected surfaces**: `tests/architectural/` (new gate files, qualname-resolving not text-matching, per
  NFR-001's correction), `issue-matrix.json`, GitHub issue comments on #2986/#3036/#3039/#3091/#3022, PR
  description.
- **Corrected scope (post-plan squad)**: FR-011 is strengthened beyond PR-description prose — this concern
  now includes writing an `issue-matrix.json` row and posting an actual tracker comment on each of the five
  deferred issues (matching the precedent mission's own practice), not merely narrating the deferral in the
  PR body.
- **Sequencing/depends-on**: MUST run AFTER IC-00/IC-01/IC-02/IC-03/IC-04 land — a zero-tolerance gate written
  before the bypasses are closed would either be vacuous (pass despite the bypasses) or immediately red
  (fail before any fix lands); neither is useful. Land last.
- **Risks**: the WP10 lesson applies directly — a gate that doesn't actually walk in-function/nested-scope
  constructs is worse than no gate (manufactures false confidence); NFR-003 now requires each self-mutation
  to inject at function-local/nested scope specifically, not module-level. Each of the five gates needs its
  own self-mutation proof, not a shared one. The `.kittify/profiles` and `_doctrine_collect.py` exclusions
  must be composite-key, not whole-file (NFR-001) — a whole-file exclusion silently waives the entire module,
  not just the named line.
