# Implementation Plan: Org-Tier Doctrine Reaches Its Consumers

**Branch**: `pr/up-org-doctrine-consumers-01M05YAB` | **Date**: 2026-08-16 | **Spec**: [kitty-specs/up-org-doctrine-consumers-01M05YAB/spec.md](kitty-specs/up-org-doctrine-consumers-01M05YAB/spec.md)
**Input**: Mission specification from `/kitty-specs/up-org-doctrine-consumers-01M05YAB/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `packs/built-in/missions/mission-steps/software-dev/plan/prompt.md` for the execution workflow.

## Branch Contract

- **Current branch at plan start**: `pr/up-org-doctrine-consumers-01M05YAB`
- **Planning/base branch**: `pr/up-org-doctrine-consumers-01M05YAB`
- **Final merge target**: `pr/up-org-doctrine-consumers-01M05YAB`
- `branch_matches_target`: `true` (per `spec-kitty agent mission setup-plan --mission up-org-doctrine-consumers-01M05YAB --json`)

This mission's own `target_branch` in `meta.json` reads `main`, but the operator instruction for
this planning pass pins branch/base/merge-target uniformly to
`pr/up-org-doctrine-consumers-01M05YAB` (confirmed identical across `current_branch`,
`target_branch`, `base_branch`, `planning_base_branch`, and `merge_target_branch` in the
`setup-plan --json` payload). No push to `main` occurs from this planning pass.

## Summary

Five call sites across the doctrine consumption surface construct doctrine repositories or call
the DRG loader without the organisation tier they already have the parameter shape to accept (four
of five) or lack entirely (one). The fix is caller-side threading at five sites plus one piece of
genuinely new surface (`MissionTemplateRepository`/`ManifestRegistry` have no org-tier mechanism at
all) and one observability fix (surface, don't delete, already-computed-but-unread delegation
results). Two pairs of these sites are lockstepped by the spec's own investigation: fixing one half
of a pair without the other converts a uniformly-blind failure into a worse, *inconsistent* one
(gate silently inert / accepted-then-rejected). This plan decomposes the work into five
Implementation Concerns, two of which are hard-constrained to land as a single unit each, and flags
two additional file-ownership collisions this plan's own investigation surfaced beyond the two
named in the mission brief.

## Technical Context

**Language/Version**: Python 3.11+ (repo `pyproject.toml` `requires-python = ">=3.11"`; CI runs
3.12).
**Primary Dependencies**: No new third-party dependency. All five in-scope call sites and the new
FR-008 surface consume only existing first-party modules (`doctrine.drg.org_pack_config`,
`doctrine.base.BaseDoctrineRepository`, `charter.activation.org_pack_discovery`, `charter.activation._drg_helpers`,
`ruamel.yaml` already used by `MissionTemplateRepository`).
**Storage**: N/A (filesystem doctrine tree reads only — no database).
**Testing**: `pytest`, existing fixture pattern from
`tests/charter/test_org_scan_dirs_activation_regression.py::_write_org_directive_fixture`
(flat-layout synthetic org pack: `<org_root>/<artifact-plural>/<id>.<kind>.yaml` +
`<org_root>/<stem>.graph.yaml`), `caplog` for FR-007's WARNING assertions.
**Target Platform**: spec-kitty CLI (Linux/macOS dev + Linux CI), no platform-specific code.
**Project Type**: Single project (this is spec-kitty's own `src/` tree — no frontend/backend
split).
**Performance Goals**: Not a performance-sensitive path (doctrine resolution runs once per CLI
invocation, already tolerates N configured org packs); no explicit budget beyond "no new O(n²) scan
introduced" — filesystem globbing here is already bounded by the number of configured org packs
(typically 0-2).
**Constraints**: See spec Constraints C-001 through C-006 (activation filtering unchanged, site 2
untouched, `MissionTemplateRepository` not restructured, single-org-root DRG limitation inherited,
internal-pack naming mismatch not fixed, size class is L).
**Scale/Scope**: Five in-scope call sites (FR-001, FR-004, FR-005, FR-006, FR-006a all reuse one
shared `org_dirs` helper; FR-002 resolves a structurally distinct single-path `org_root`) plus one
new-surface FR (FR-008) plus one observability FR (FR-007) — eight FRs total, six NFRs, six
constraints, seven SCs, per spec.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Relevant gates for this plan/implement pass:

- **Single canonical authority** (Governing Principles): satisfied — FR-003's shared `org_dirs`
  helper and, per this plan's own finding, a new shared FR-008 helper are each written once and
  reused, specifically to prevent the kind of caller-drift (site 3 vs site 6) this mission exists
  to close. No second authority is introduced.
- **Architectural alignment / shared-package boundaries**: satisfied — no site moves across the
  `kernel <- doctrine <- charter <- specify_cli` / `runtime.next` boundary; every new import
  direction verified against existing precedent in this plan's research (`research.md` §
  "Layer-import feasibility").
- **ATDD-first / red-first discipline** (Governance by Workflow Action → Implement): binding for
  the implement phase — NFR-001 already mandates a red-before-fix regression test per FR; this plan
  places each test per the spec's own Test Strategy section, unchanged.
- **Adversarial squad cadence**: advisory, not a hard gate here; recommended at the post-plan and
  post-tasks point-cuts given this mission's L size and the two hard lockstep constraints (a squad
  pass is well-suited to independently checking that task generation didn't split either pair).
- **Terminology canon**: NFR-006 already requires `tests/architectural/test_no_legacy_terminology.py`
  green on every changed file under `src/doctrine/`; this plan's file list includes
  `src/doctrine/drg/org_pack_config.py` (IC-01), so that gate is in scope.
- **Campsite cleaning**: no god-surface identified among the five call sites or `MissionTemplateRepository`
  — each touched function is small (typically <30 lines) and none is near the Sonar/ruff
  complexity ceiling (verified by inspection during this plan's investigation; see `research.md`).
  No preceding campsite-clean step is warranted.

No charter violation requires justification — Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/up-org-doctrine-consumers-01M05YAB/
├── plan.md              # This file (/spec-kitty.plan command output)
├── research.md          # Phase 0 output (/spec-kitty.plan command)
├── data-model.md        # Phase 1 output (/spec-kitty.plan command)
├── quickstart.md        # Phase 1 output (/spec-kitty.plan command)
├── contracts/           # Phase 1 output (/spec-kitty.plan command)
│   └── org-tier-resolution-contract.md
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command - NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── doctrine/
│   ├── drg/
│   │   └── org_pack_config.py          # IC-01: new resolve_org_dirs() helper (FR-003)
│   └── missions/
│       └── step_contracts.py           # C-002: read-only reference, NOT modified (site 2, out of scope)
├── charter/
│   ├── _drg_helpers.py                 # reference only: load_validated_graph(org_root=...) signature (unmodified)
│   ├── org_pack_discovery.py           # reference only: _enumerate_org_pack_paths (unmodified, reused by IC-02)
│   ├── action_doctrine_bundle.py       # reference only: first-match org_root pattern (unmodified, mirrored by IC-02)
│   ├── mission_type_profiles.py        # IC-04 (FR-004) + IC-05 (FR-008) — see file-collision note below
│   └── org_expected_artifacts.py       # IC-05: new shared org-file-check helper (FR-008)
├── specify_cli/
│   ├── mission_step_contracts/
│   │   └── executor.py                 # IC-02: FR-001 (__init__) + FR-002 (execute())
│   ├── review/
│   │   └── gate_bindings.py            # IC-02: FR-005 (_build_repository) — LOCKSTEP PAIR A with executor.py
│   ├── mission_loader/
│   │   └── command.py                  # IC-03: FR-006a (_resolve_contract_refs) — LOCKSTEP PAIR B
│   └── dossier/
│       └── manifest.py                 # IC-05: FR-008 (ManifestRegistry.load_manifest)
└── runtime/
    └── next/
        └── runtime_bridge_composition.py  # IC-03: FR-006 (_resolve_runtime_contract_for_step, LOCKSTEP PAIR B)
                                             #        + FR-007 (_dispatch_via_composition) — file-collision fold-in

tests/
├── specify_cli/
│   ├── mission_step_contracts/
│   │   ├── test_executor.py            # FR-001/FR-002 red-first regression (SC-001, SC-002)
│   │   └── test_executor_activation.py # FR-001/FR-002 activation-interaction coverage
│   ├── review/
│   │   └── (new or existing gate_bindings test module)  # FR-005 regression (SC-003 shared fixture)
│   └── mission_loader/                 # location TBD at tasks phase — see NFR-004 note
├── unit/mission_loader/                # FR-006a regression (SC-003 shared fixture; --cov-fail-under=90 gate)
├── runtime/
│   └── test_bridge_composition.py      # FR-006 (SC-003) + FR-007 (SC-004) regressions
├── charter/
│   └── test_mission_type_profiles.py   # FR-004 (governance) + FR-008 (expected-artifacts) regressions
└── dossier/
    └── test_manifest.py                # FR-008 ManifestRegistry regression (SC-005)
```

**Structure Decision**: Single project (spec-kitty's own `src/` tree). No new top-level package.
Two brand-new files: `src/doctrine/drg/org_pack_config.py` gains a new function (not a new file —
`resolve_org_roots` already lives there); `src/charter/activation/org_expected_artifacts.py` is a genuinely
new small module (IC-05's shared helper). Every other change is an edit to an existing file.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No violations. Table intentionally empty.

## Implementation Concern Map

*Include this section when the mission has multiple distinct architectural areas that inform how tasks are decomposed.*

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs — one concern may become
> multiple WPs; multiple small concerns may merge into one WP. Do not label concerns
> with WP-style IDs or sequencing language.

### IC-01 — Shared `org_dirs` resolution helper

- **Purpose**: One function resolves the existing-path-filtered, declaration-ordered list of
  per-pack org directories for a given artifact subdirectory name, so the four/five sites that need
  the list-shaped `org_dirs` argument cannot independently drift the way sites 3 and 6 already had
  before this mission (the exact failure class FR-003 exists to close).
- **Relevant requirements**: FR-003 (foundation for FR-001, FR-004, FR-005, FR-006, FR-006a; NFR-003
  multi-org-pack precedence lives here).
- **Affected surfaces**: `src/doctrine/drg/org_pack_config.py` (new function, sibling to the
  existing `resolve_org_roots`).
- **Sequencing/depends-on**: none. Must land before IC-02, IC-03, and IC-04 (they import it), but
  is itself inert (unused) until they do — safe to land first with only unit tests exercising it
  directly.
- **Risks**: Low. The one design decision worth stating explicitly: existence filtering happens at
  the *org-root* level (mirroring `charter.activation.doctrine_service_builder._self_resolve_existing_org_roots`),
  not at the joined-subdirectory level — a nonexistent org root is dropped before joining, so a
  stale `local_path` config entry degrades cleanly (Edge Cases, NFR-002) without a second existence
  check downstream.

### IC-02 — Executor org-tier threading + gate-binding lockstep [LOCKSTEP PAIR A — MANDATORY SINGLE PACKAGE]

- **Purpose**: `StepContractExecutor` gains both org-tier repository construction (FR-001) and
  org-tier DRG resolution (FR-002) — the two defects User Story 1 names as compounding ("fixing (1)
  without (2) still leaves delegation dead") — and `gate_bindings._build_repository` (FR-005) is
  fixed in the same package because the executor's own docstring and `load_gate_bindings`'s
  docstring each promise the two constructions mirror each other. **This is the first of the two
  orchestrator-mandated lockstep pairs**: `specify_cli/review/gate_bindings.py:168` with
  `mission_step_contracts/executor.py:160`. Splitting FR-001/FR-005 across packages would leave a
  window where an org-tier contract's delegations resolve but its `gates:` block silently never
  fires — a new, worse failure than today's uniform blindness (User Story 3).
- **Relevant requirements**: FR-001, FR-002, FR-005 (SC-001, SC-002, SC-003 partially — the
  gate-bindings third of SC-003's shared-fixture proof lives here).
- **Affected surfaces**: `src/specify_cli/mission_step_contracts/executor.py`,
  `src/specify_cli/review/gate_bindings.py`.
- **Sequencing/depends-on**: IC-01 (FR-001 and FR-005 both consume the shared `org_dirs` helper;
  FR-002 resolves its single-path `org_root` inline via the `_enumerate_org_pack_paths` first-match
  pattern per D-000(2) — see `research.md` — and does not depend on IC-01).
- **Risks**: FR-001 and FR-002 are forced into the same file (`executor.py`) regardless of the
  lockstep rule — a second, independent reason they cannot be split. Test file
  `tests/specify_cli/mission_step_contracts/test_executor.py` and
  `test_executor_activation.py` both gain fixtures in this package; keep the activation-interaction
  test (org node visible pre-activation-filter, then correctly excluded post-filter when
  deactivated) explicit so C-001 ("no change to activation filtering") stays proven, not assumed.

### IC-03 — Runtime dispatch / mission-load validation lockstep + delegation-candidate surfacing [LOCKSTEP PAIR B — MANDATORY SINGLE PACKAGE, plus a file-collision fold-in]

- **Purpose**: `_resolve_runtime_contract_for_step` (FR-006, runtime dispatch) and
  `_resolve_contract_refs` (FR-006a, mission-load validation) must resolve an org-tier `contract_ref`
  identically — **this is the second orchestrator-mandated lockstep pair**:
  `mission_loader/command.py:237` with `runtime/next/runtime_bridge_composition.py:284`. A partial
  fix here is explicitly called out by the spec (User Story 2) as worse than no fix: it converts a
  consistent "always invisible" into an inconsistent "accepted at one point, rejected at the other."
  FR-007 (surface unresolved delegation candidates as a WARNING) is folded into this same concern —
  see Risks below for why this is not optional.
- **Relevant requirements**: FR-006, FR-006a, FR-007 (SC-003 runtime+load-time two-thirds, SC-004).
- **Affected surfaces**: `src/runtime/next/runtime_bridge_composition.py`,
  `src/specify_cli/mission_loader/command.py`.
- **Sequencing/depends-on**: IC-01 (both FR-006 and FR-006a consume the shared `org_dirs` helper).
- **Risks — file-collision fold-in (self-identified, beyond the brief's two named pairs)**: FR-007's
  edit site, `_dispatch_via_composition`, lives in the **same file** as FR-006's edit site,
  `_resolve_runtime_contract_for_step` — both in `runtime_bridge_composition.py`. Under this repo's
  `owned_files` pairwise-disjoint work-package constraint, FR-007 cannot be split into an
  independent work package without conflicting file ownership against FR-006's change. This is
  **not** a functional lockstep requirement (FR-007's WARNING logging is independently useful
  whether or not FR-006 has landed) — it is purely a file-ownership consequence task generation must
  respect. Flagging explicitly per this plan's instructions: **do not let task generation split
  FR-007 into its own work package alongside FR-006/FR-006a; all three land in one package.**

### IC-04 — Governance-profile org-tier threading

- **Purpose**: `_resolve_governance_slot` → `_mission_type_profile_repository` →
  `MissionTypeProfileRepository.for_project` threads `org_dirs` so an org-tier
  `governance-profile.yaml` override is not silently invisible in every mission-type context
  resolution (it runs eagerly, per D-004) — cheap, same shape as FR-001, and explicitly does not
  touch the deliberately built-in-only `action_grain.py:220` call site.
- **Relevant requirements**: FR-004.
- **Affected surfaces**: `src/charter/activation/mission_type_profiles.py` (`_resolve_governance_slot` around
  line 766, `_mission_type_profile_repository` around line 1148 — no change needed to
  `MissionTypeProfileRepository` itself, which already accepts `org_dirs`).
- **Sequencing/depends-on**: IC-01 (consumes the shared `org_dirs` helper, joined with the
  `mission_types` project-overlay subdirectory name — **not** an `ArtifactKind` member; see
  `research.md`). Additionally: **must be sequenced before IC-05**, not run in parallel with it —
  see IC-05's Risks for why.
- **Risks**: Low in isolation. The only material risk is the file collision with IC-05 (both touch
  `mission_type_profiles.py`) — resolved by sequencing, not by splitting the file further.

### IC-05 — Org-tier `expected-artifacts.yaml` override (new surface)

- **Purpose**: `MissionTemplateRepository`/`ManifestRegistry` have **no tiering mechanism of any
  kind** today — this is net-new surface, not caller-side parameter threading, and per the mission
  brief this is the largest single piece of work in the mission. An org pack can, after this
  concern lands, ship `<org_root>/<mission_type>/expected-artifacts.yaml` that **fully replaces**
  (not merges with) the built-in manifest for that mission type.
- **Relevant requirements**: FR-008 (SC-005).
- **Affected surfaces**: new `src/charter/activation/org_expected_artifacts.py` (shared org-file-check
  helper — see `research.md` for why this is a new module rather than a new method on
  `MissionTemplateRepository`, per C-003), `src/charter/activation/mission_type_profiles.py`
  (`_resolve_expected_artifacts_slot`, around line 971), `src/specify_cli/dossier/manifest.py`
  (`ManifestRegistry.load_manifest`).
- **Sequencing/depends-on**: **IC-04** — self-identified file collision (beyond the brief's two
  named pairs): `_resolve_expected_artifacts_slot` (this concern) and `_resolve_governance_slot`/
  `_mission_type_profile_repository` (IC-04) are different functions in the **same file**,
  `src/charter/activation/mission_type_profiles.py`. The `owned_files` pairwise-disjoint constraint means these
  two concerns cannot become two work packages running in parallel against that file. This plan
  recommends **serial sequencing** (IC-04 lands and merges first; IC-05 starts after) rather than
  forcing IC-04's small, functionally-unrelated fix into IC-05's large, higher-risk one — merging
  them into a single package is the fallback if task generation prefers fewer packages, but
  sequencing keeps IC-05's larger blast radius isolated. **Do not let task generation schedule IC-04
  and IC-05 as parallel work packages.**
- **Risks**:
  - **`MissionTemplateRepository` is not restructured** (C-003) — the org-file check is
    additive logic living beside it, not a new method on the class, not a new `BaseDoctrineRepository`
    subclass, not a new `ArtifactKind`.
  - **`ManifestRegistry.load_manifest` cache-key correctness (self-identified gap, not named by
    the spec)**: `load_manifest` is a `@staticmethod` with a process-global cache keyed only on
    `mission_type` (`ManifestRegistry._cache: dict[str, ...]`). Its sole production caller,
    `specify_cli/sync/namespace.py:resolve_manifest_version`, has no `repo_root` in scope at all.
    Introducing org-tier resolution without changing the cache key risks the built-in-only result
    from one project's first call silently shadowing a different project's org-tier override on a
    later call in the same long-lived process (a real instance of the "silent success" class NFR-002
    forbids, even though NFR-002's own text is written about the fix sites, not this cache). This
    plan's recommended shape: `load_manifest(mission_type: str, repo_root: Path | None = None)`,
    cache keyed on `(mission_type, tuple_of_resolved_org_roots_or_empty)` so
    `resolve_manifest_version` (no `repo_root`) is unaffected and keeps its exact current
    behavior (empty org-roots tuple, built-in-only, byte-identical — satisfying SC-005's Given #2),
    while a `repo_root`-carrying caller gets a correctly-scoped cache entry. Recorded here as a
    stated assumption — see "Stated Assumptions & Flagged Gaps" below.
  - Whole-file precedence (not field-merge) must be tested explicitly (SC-005 Given #3), matching
    the sibling mission's own precedent for the structurally analogous case.

## Verification & Measurement Plan

Per the mission's own Verification Bar (NFR-001, Test Strategy): every defect fix is proven by a
before/after measurement, not an assertion. This section states, per FR, what the number/boolean is
and where it is recorded.

| FR | Measurement | Where it lives |
|----|-------------|----------------|
| FR-001 | `MissionStepContractRepository.get_by_action(...)` for an org-only contract: `None` (red, pre-fix) → contract object (green, post-fix) | `tests/specify_cli/mission_step_contracts/test_executor.py` (SC-002) |
| FR-002 | `load_validated_graph(...)` DRG node count: baseline → baseline+1 when a synthetic one-node org pack is supplied as `org_root` — the live-verified **347 → 348** methodology (D-000(4)) reproduced as a committed regression, not re-asserted as a fixed literal (baseline drifts if the built-in graph grows) | `tests/specify_cli/mission_step_contracts/test_executor.py` (SC-001) |
| FR-004 | `resolve_mission_type_context(...).governance_text` (via the governance thunk) reflects an org-pack `governance-profile.yaml` override, not the built-in baseline | `tests/charter/test_mission_type_profiles.py` |
| FR-005 | `load_gate_bindings(repo_root, mission, action)` returns the org contract's `gates` list (non-empty) instead of `[]`, using the **same fixture** as FR-001/FR-006/FR-006a (SC-003) | new/existing test module under `tests/specify_cli/review/` |
| FR-006 | `_resolve_runtime_contract_for_step` returns the org-tier contract object (not `None`), same shared fixture | `tests/runtime/test_bridge_composition.py` (SC-003) |
| FR-006a | `_resolve_contract_refs` returns `None` (no `LoaderError`) for the same org-tier `contract_ref`, same shared fixture; both FR-006 and FR-006a additionally proven to fail **identically** when the org pack is absent (User Story 2, Acceptance Scenario 3) | `tests/unit/mission_loader/` (SC-003) |
| FR-007 | `caplog` WARNING count: exactly one record naming step id + contract id + unresolved candidate(s) when 1+ candidates fail to resolve; **zero** records in the same test run when every candidate resolves (negative case, same test, not a separate test) | `tests/runtime/test_bridge_composition.py` (SC-004) |
| FR-008 | `ManifestRegistry.load_manifest(...).get_step_ids()` / `required_always` count/content delta: built-in-only baseline vs. org-override-present, same process, before/after fixture mutation; plus a whole-file-precedence assertion (org file present alongside built-in → org fully replaces, not merges) | `tests/charter/test_mission_type_profiles.py` + `tests/dossier/test_manifest.py` (SC-005) |

**Shared-fixture discipline (SC-003)**: FR-005/FR-006/FR-006a are proven against **one** synthetic
org-pack fixture, exercised by three separate test functions (one per test module) — not three
independently-authored fixtures that could silently diverge. The fixture module location is decided
at tasks phase; this plan requires it be importable from all three test modules (e.g. a shared
`conftest.py` fixture or a small fixture-builder function in a location all three can import without
crossing a test-layer boundary the architectural suite would reject).

**Reviewer verification checklist** (per spec Test Strategy, unchanged by this plan): for each FR
above, a reviewer re-runs the specific before/after count or boolean locally against the PR branch,
not merely reads the CI checkmark — and, for the red-first claim specifically, checks out the
fixture's pre-fix commit in isolation and confirms the new test is RED there, then GREEN on the fix
commit (mirrors the sibling mission's own NFR-005 discipline).

## Coverage Floors & CI Shard Expectations

This repo gates on coverage floors (kernel ≥90%, mission loader ≥90%) and runs an adversarial
architectural suite (NFR-004, NFR-005). Per-IC shard exposure:

- **IC-01** (`src/doctrine/drg/org_pack_config.py`): critical-path (`src/doctrine/*`), enforced
  `diff-cover --fail-under=90` in the `ci-quality.yml` critical-path job. Also in scope for
  `tests/architectural/test_no_legacy_terminology.py` (NFR-006).
- **IC-02** (`executor.py`, `gate_bindings.py`): **neither file is in the enforced diff-cover
  critical-path list** (`src/specify_cli/mission_step_contracts/*` and `src/specify_cli/review/*`
  are absent from the `critical_paths` array in `.github/workflows/ci-quality.yml`) **and neither
  has its own dedicated ≥90% job** — this package is covered only by the advisory full-diff
  coverage step and by its own test suite passing. Do not assume a hard coverage gate catches a
  regression here; the red-first regression tests (NFR-001) are the real backstop.
- **IC-03** (`runtime/next/runtime_bridge_composition.py`): critical-path (`src/runtime/next/*`),
  enforced. `src/specify_cli/mission_loader/command.py`: **not** in the critical-path array, but
  covered by the **dedicated** mission-loader job
  (`--cov=src/specify_cli/mission_loader --cov-fail-under=90`,
  `tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py`, NFR-004's own
  citation).
- **IC-04**, **IC-05** (`src/charter/activation/mission_type_profiles.py`, new
  `src/charter/activation/org_expected_artifacts.py`): critical-path (`src/charter/*`), enforced.
  `src/specify_cli/dossier/manifest.py` (IC-05's other half): **not** critical-path, advisory only —
  same caveat as IC-02, lean on NFR-001's red-first tests as the real backstop for this file.
- **Architectural suite** (NFR-005): `tests/architectural/test_layer_rules.py` and every
  `tests/architectural/test_charter_sole_door_*.py` must stay green with zero new allowlist rows.
  This plan's only new cross-layer import is `specify_cli/dossier/manifest.py` importing the new
  `charter/org_expected_artifacts.py` (specify_cli → charter, the existing permitted direction —
  `ManifestRegistry` already imports `charter.missions.MissionTemplateRepository` today) and
  `runtime/next/runtime_bridge_composition.py` importing `doctrine.drg.org_pack_config`'s new
  function (runtime already imports `doctrine.missions.step_contracts` directly in this same file —
  same permitted direction, no new boundary crossed).

## Sizing Assessment

Spec sizing: **L**, ~170-210 production LOC, ~250-300 test LOC (C-006). This plan's own
IC-by-IC estimate:

| IC | Est. production LOC | Est. test LOC |
|----|---------------------|---------------|
| IC-01 | ~15-20 | ~20-30 (unit tests for the helper itself: empty config, one pack, two packs, nonexistent path) |
| IC-02 (FR-001+FR-002+FR-005) | ~25-35 | ~60-80 (executor red-first ×2 + gate-bindings red-first ×1, activation-interaction coverage) |
| IC-03 (FR-006+FR-006a+FR-007) | ~35-45 | ~70-90 (shared-fixture ×2 + FR-007 positive/negative ×1) |
| IC-04 | ~10-15 | ~20-30 |
| IC-05 | ~90-130 | ~90-120 (new helper unit tests, two call-site integration tests, whole-file-precedence test, cache-key regression test) |
| **Total** | **~175-245** | **~260-350** |

**This plan's assessment: L is correct, and the upper end of the spec's own range is more likely
than the midpoint**, for two reasons this plan's investigation surfaced beyond C-006's original
reconciliation:

1. **The `ManifestRegistry` cache-key fix (IC-05)** is real, load-bearing work the spec's FR-008
   text does not explicitly budget for — SC-005's Given #2 (byte-identical no-override behavior)
   cannot be honestly claimed without addressing the process-global, `mission_type`-only cache key,
   given the one production caller has no `repo_root`. This adds test and production LOC beyond a
   naive "add an org check to two functions" estimate.
2. **Two additional file-ownership collisions** (IC-04/IC-05 both touch `mission_type_profiles.py`;
   FR-007 forced into IC-03 by file, not by function) do not change LOC, but they do compress the
   achievable work-package parallelism task generation can extract from this plan — five ICs
   decompose into at most **four** independently-schedulable work packages (IC-01 → {IC-02, IC-03,
   IC-04→IC-05 chain} in parallel), not five, which is worth setting expectations on now rather than
   at tasks phase.

No compression recommended. If tasks phase finds the true total closer to ~250 production /
~350 test LOC once IC-05's cache-key handling is fully specced, that is consistent with this
plan's estimate, not a scope-creep signal.

## Stated Assumptions & Flagged Gaps

Per the operator instruction to record genuine gaps as stated assumptions rather than stopping:

1. **`ManifestRegistry.load_manifest` signature change** (IC-05): the spec's SC-005 acceptance
   scenarios exercise `load_manifest("software-dev")` (positional, one arg) unchanged — the spec
   does not explicitly specify whether `repo_root` becomes a required or optional parameter, nor
   the cache-key shape. **Assumption**: `repo_root: Path | None = None` (optional, defaulting to
   today's behavior) is the correct shape, because it is the only shape that (a) keeps
   `resolve_manifest_version` in `specify_cli/sync/namespace.py` — which has no `repo_root` in
   scope — compiling and behaviorally unchanged, and (b) satisfies SC-005 Given #2's
   byte-identical-when-no-override requirement without a second code path. Flagged for task-phase
   confirmation; not a blocker.
2. **IC-04/IC-05 sequencing vs. merging** (both touch `mission_type_profiles.py`): this plan
   recommends serial sequencing over merging into one work package, on the grounds that IC-05 is
   materially larger/riskier and IC-04 is unrelated in function. This is a planning preference, not
   a spec requirement — task generation may reasonably choose to merge them instead if that proves
   simpler to schedule. Either choice satisfies `owned_files` disjointness; only *parallel,
   file-colliding* work packages would violate it.
3. **FR-007's shared org-file-check helper for IC-05** (`src/charter/activation/org_expected_artifacts.py`) is
   this plan's own design choice, not named by the spec, which only says "adds a narrow, additive
   org-file check alongside the existing built-in-only reader" (C-003) without specifying module
   placement. A new small module was chosen over adding logic inline to both
   `_resolve_expected_artifacts_slot` and `ManifestRegistry.load_manifest` separately, to give
   FR-008 the same "written once, not duplicated" discipline FR-003 established for the org_dirs
   list shape — consistent with the mission's own throughline, not a scope addition.
4. **Test module location for FR-005** (gate-bindings regression): spec Test Strategy says
   "`tests/specify_cli/review/`" without naming a file; `tests/specify_cli/review/` today holds only
   `test_gate_binding_schema.py`. This plan leaves the exact filename (new file vs. extending the
   existing one) to task generation.

Nothing above required stopping or returning to the spec — each is resolvable at task-generation or
implementation time with the rationale already stated.
