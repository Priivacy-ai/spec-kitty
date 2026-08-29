# Implementation Plan: Org Doctrine-Pack Tier for the Template Resolution Chain and FSM Discovery

**Branch**: `up-org-template-fsm` | **Date**: 2026-08-17 | **Spec**: [`kitty-specs/up-org-template-fsm-01M06F9K/spec.md`](./spec.md)
**Input**: Feature specification from `kitty-specs/up-org-template-fsm-01M06F9K/spec.md`

**Branch contract** (repeated per the plan-step protocol): current branch at plan start is
`up-org-template-fsm`; planning/base branch for this mission is `up-org-template-fsm`; the final
merge target for completed changes is `up-org-template-fsm` — `branch_matches_target: true`
(confirmed via `spec-kitty agent mission setup-plan --mission up-org-template-fsm-01M06F9K --json`).
Single-branch topology (`meta.json: "topology": "single_branch"`) — no coordination worktree, no
lane split; all work lands on this one branch.

## Summary

Two forked 5-tier asset resolvers (`src/doctrine/resolver.py`, the doctrine-layer "sole door", and
`src/specify_cli/runtime/resolver.py`, the production `mission create` / plan-setup lane) disagree
on the mission-scoped override probe, and neither has a tier for an org doctrine pack's own
templates or mission-FSM content. Neither of the two FSM discovery walks
(`src/runtime/next/_internal_runtime/discovery.py` Walk A,
`src/runtime/next/runtime_bridge_io.py` Walk B) has an org tier either, and Walk B silently
swallows template-load failures. The mission converges the resolver drift first (Step 0, additive
only — never a module merge), then adds a `ResolutionTier.ORG` sourced from the already-sanctioned
`charter.drg.resolve_org_roots` facade at the identical relative position across four independent
call sites (`doctrine/resolver.py`, `specify_cli/runtime/resolver.py`, FSM Walk A, FSM Walk B),
fixes `list_cmd.py`'s org-tier reporting to match what actually resolves, and de-silences Walk B's
swallowed FSM load failures. `charter.activation.template_resolver.CharterTemplateResolver._tier_to_origin`
gets a matching `ORG` label as a small, independent consistency fix. Twelve FRs, sized M upper-edge
(~123 production / ~340 test LOC per the spec's own estimate — see Sizing Assessment below).

## Technical Context

**Language/Version**: Python 3.11+ (existing project baseline; no new language/runtime need)
**Primary Dependencies**: None added. Reuses `doctrine.drg.org_pack_config.resolve_org_roots` via
the existing `charter.drg` re-export facade; reuses `pydantic` (`DiscoveryContext` is already a
`BaseModel`) for the new `org_roots` field; reuses the existing `DiscoveryWarning` model for the
two new diagnostics (FR-010, FR-011).
**Storage**: N/A — filesystem-tier resolution only, no persisted state added.
**Testing**: `pytest` (repo standard). New tests live under `tests/doctrine/`,
`tests/specify_cli/runtime/` (or the existing resolver test module's location — verify at
implementation time), `tests/runtime/next/` (Walk A/B), `tests/charter/test_template_resolver.py`
(FR-012), and `tests/specify_cli/cli/commands/charter/` (FR-006 / `list_cmd.py`). Architectural
gates (`tests/architectural/test_charter_sole_door_resolver_imports.py`,
`tests/architectural/test_runtime_charter_doctrine_boundary.py`) and the existing
`tests/doctrine/test_org_pack_subdir.py` "not swallowed" assertions must continue green unmodified
— these are regression fences, not new-feature tests.
**Target Platform**: Same as the existing CLI/library — cross-platform (macOS/Linux/Windows) Python
package; no platform-specific behavior introduced.
**Project Type**: Single project (existing `src/` layout: `doctrine`, `charter`, `specify_cli`,
`runtime` packages under the documented dependency direction `kernel <- doctrine <- charter <-
specify_cli`, with `src/runtime/next/**` as a sibling package per the Shared Package Boundary ADR).
**Performance Goals**: N/A — filesystem-probe resolution, same order of magnitude as the existing
4-5 tier walks (one more `is_file()`/`is_dir()` probe per asset per configured org pack). No
numeric target; the spec sets none.
**Constraints**: C-001 (no resolver-module merge), C-002 (3-kind built-in carve-out untouched),
C-003 (`mission_packs:` kept as-is, not sanctioned), C-004 (list_cmd.py PROJECT-tier path mismatch
out of scope), C-005 (FSM sidecar preference mechanics unchanged), C-006 (mission-type roster /
`ArtifactKind` work out of scope) — see spec.md Constraints table.
**Scale/Scope**: 12 FRs across 4 independent-but-position-coupled call sites (2 template resolvers
+ 2 FSM walks) plus 2 small consistency fixes (`list_cmd.py`, `_tier_to_origin`). No user-facing
API surface, no data migration, no schema change.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.yaml`, `.kittify/charter/charter.md`, org pack
`spec-kitty-internal`). Directives loaded via `spec-kitty charter context --action plan --json`
relevant to this mission:

- **Single canonical authority / canonical sources** — this mission is itself an instance of that
  principle: it exists because two resolver modules drifted into being two different sources of
  truth for the same tier semantics. The plan's Step 0 (converge) directly serves this directive;
  it does not introduce a new competing implementation.
- **Architectural alignment / tiered rigour** — DEC-002/DEC-003/DEC-004 are the load-bearing
  architectural decisions: the tier-5 charter-facade split stays a real boundary
  (`test_charter_sole_door_resolver_imports.py`), `specify_cli/**` may only reach
  `resolve_org_roots` through `charter.drg` (`test_runtime_charter_doctrine_boundary.py`), and
  `src/runtime/next/**` follows the same discipline by convention pending #3522. No violation to
  justify in Complexity Tracking — the design is gate-compliant by construction, not by exception.
- **DIR-007 (docstrings for public APIs)** — the new `ResolutionTier.ORG` member, `DiscoveryContext.
  org_roots` field, and the two new diagnostic paths need docstring coverage matching the existing
  tier documentation style (both `_resolve_asset` docstrings already enumerate tiers by number —
  update those enumerations, do not leave them saying "5-tier" once ORG exists).
- **DIR-012 (assign tracker issue to HiC before/when starting implementation)** — applies at
  `/spec-kitty.implement` time for issue #3523, not at planning time; flagged here so the
  implementer does not skip it.
- **DIR-013 (pre-existing test failures → file an issue before treating as baseline)** — applies if
  implementation surfaces unrelated baseline reds; not applicable to the plan itself.
- No conflicts found between the charter and the spec's Decisions Log. Re-checked after Phase 1
  design below (Post-Design Charter Check) — still no new gaps.

No violations requiring Complexity Tracking entries.

## Project Structure

### Documentation (this mission)

```
kitty-specs/up-org-template-fsm-01M06F9K/
├── plan.md              # This file
├── research.md          # SKIPPED — see Phase 0 note below
├── data-model.md         # SKIPPED — see Phase 1 note below
├── quickstart.md         # SKIPPED — see Phase 1 note below
├── contracts/             # SKIPPED — see Phase 1 note below
└── tasks.md              # Phase 2 output (/spec-kitty.tasks — NOT created by this command)
```

**Phase 0 (research.md) — skipped, with reason.** The spec's Provenance section and eleven-entry
Decisions Log already are the research output: every load-bearing claim was independently
re-verified against this checkout's tip (`main@2cffc248f`) during specification, not carried over
from an external spike. This plan's own grounding pass (below) re-confirmed the same file:line
citations directly against the current tree during planning (see "Plan-Time Verification" below).
There are no `NEEDS CLARIFICATION` markers in the spec's Technical Context-equivalent sections and
no open decision requiring a `research.md`-style consolidation. Producing a separate `research.md`
that restates the Decisions Log would be duplication, not new research — explicitly against this
repo's "Use Canonical Sources, Never Improvise" guidance (CLAUDE.md), which here means: the spec
*is* the canonical research record for this mission.

*Note on the spec's own provenance claim*: the spec's Provenance section cites a spike at
`_rnd/spikes/up-org-template-fsm.md`. That path does not exist in this checkout (no `_rnd/`
directory is present at all). This is recorded as a **verification gap** (see "Could Not Verify"
in the report) — it does not affect the plan because the spec's Decisions Log is explicitly
re-verified against the live codebase independent of the spike, and this plan re-confirmed the
same citations directly.

**Phase 1 (data-model.md, contracts/, quickstart.md) — skipped, with reason.** This mission adds no
new persisted entities, no new API/CLI surface, and no new external contract (webhook, endpoint,
payload shape) — the spec's own "Key Entities" section (four entries: `ResolutionTier.ORG`, "Org
root", `DiscoveryContext.org_roots`, `DiscoveryWarning`) already fully describes the in-process
data shapes this mission touches, all of which are extensions of existing types, not new models.
`contracts/` is an API-contract artifact (OpenAPI/GraphQL/webhook payload per the plan template);
this mission's "contract" in the applicable sense is FR/SC pairing in the spec itself (each FR has
a paired SC with a before/after test), which is captured in this plan's Verification Design section
below rather than duplicated into a separate `contracts/` directory. `quickstart.md` (an
onboarding/usage walkthrough) does not apply — this mission changes internal resolution precedence,
not a user-facing workflow that needs a walkthrough; the spec's User Scenarios already carry the
concrete "Given/When/Then" walkthroughs a quickstart would otherwise restate.

### Source Code (repository root)

Existing single-project layout — no new top-level directories. Concrete paths this mission touches
(module names, not options):

```
src/
├── doctrine/
│   ├── resolver.py                    # FR-002 (ResolutionTier.ORG), FR-003 (_resolve_asset org tier),
│   │                                   #   FR-005 (resolve_mission org tier)
│   └── drg/org_pack_config.py         # unchanged — resolve_org_roots already lives and is exported here
├── charter/
│   ├── drg.py                          # unchanged — resolve_org_roots re-export already exists (line 97, 152)
│   ├── resolution.py                   # unchanged — ResolutionTier re-exported by identity; ORG needs no new declaration
│   └── template_resolver.py           # FR-012 (_tier_to_origin ORG label)
├── specify_cli/
│   ├── runtime/resolver.py            # FR-001 (Step 0 mission-scoped override probe),
│   │                                   #   FR-004 (_resolve_asset org tier via charter.drg facade),
│   │                                   #   FR-005 (resolve_mission org tier)
│   ├── cli/commands/charter/list_cmd.py  # FR-006 (_template_tier_roots org branch: flat path, ORG tier)
│   ├── core/mission_creation.py       # unchanged — call site only (resolve_configured_template at :577)
│   └── mission_loader/command.py      # FR-008 (third DiscoveryContext wiring site, _build_discovery_context :187-200)
└── runtime/next/
    ├── _internal_runtime/discovery.py  # FR-007 (org_roots field + _build_tiers org tier — Walk A)
    ├── runtime_bridge_io.py           # FR-008 (org_roots population), FR-009 (Walk B org tier in
    │                                   #   _runtime_template_key), FR-010 (de-silence _template_key_for_file),
    │                                   #   FR-011 (sidecar diagnostic in _resolve_runtime_template_in_root)
    └── _internal_runtime/engine.py     # unchanged — DiscoveryContext() fallback at :176 is explicitly out of scope (DEC-006)

tests/
├── doctrine/                          # FR-002, FR-003, FR-005 unit tests; NFR-001(b) regression test
├── specify_cli/runtime/               # FR-001, FR-004, FR-005 unit tests (verify exact test-module path at implementation time)
├── specify_cli/cli/commands/charter/  # FR-006 test
├── specify_cli/mission_loader/        # FR-008 third-site test (mission-loader coverage gate)
├── runtime/next/                      # FR-007, FR-008, FR-009, FR-010, FR-011 tests (Walk A/B)
├── charter/                            # FR-012 test (test_template_resolver.py)
└── architectural/                      # regression-only: existing gates continue green, no new allow-list entries
```

**Structure Decision**: Single project, no new modules or packages. Every FR lands inside an
existing module at a cited line range; the mission's shape is "insert a tier at a known position in
four already-forked call sites," not new architecture. The two resolver modules
(`doctrine/resolver.py`, `specify_cli/runtime/resolver.py`) remain two modules per C-001 — this
plan does not propose consolidating them, only converging one probe (Step 0) and adding one tier
to each in parallel.

## Complexity Tracking

*No Charter Check violations to justify — table intentionally empty.*

## Plan-Time Verification

Every file:line citation load-bearing to this plan's Implementation Concern Map was re-read
directly in this checkout during planning (not inherited from the spec without a second check):

- `src/doctrine/resolver.py:145-179` (Tier 1 with mission-scoped probe) and
  `src/specify_cli/runtime/resolver.py:259-286` (Tier 1, no mission-scoped probe) — confirmed the
  drift is real and matches DEC-002's citation exactly.
- `src/doctrine/resolver.py:303-361` (`resolve_mission`, 4-tier) — confirmed no org tier exists yet
  and the tier-4 `except (FileNotFoundError, ImportError)` pattern that must not be broadened.
- `src/charter/drg.py:97,152` — confirmed `resolve_org_roots` is re-exported by identity.
- `src/charter/resolution.py:29` — confirmed `ResolutionTier` is re-exported from
  `doctrine.resolver` by identity (a new `ORG` member needs no separate declaration here).
- `src/specify_cli/cli/commands/charter/list_cmd.py:48-90` — confirmed the org branch resolves
  `org_root / "doctrine" / "missions"` (nested, wrong) and tags `ResolutionTier.GLOBAL_MISSION`
  (borrowed, wrong) — exactly as FR-006/DEC-007 describe.
- `src/runtime/next/_internal_runtime/discovery.py:90-97` (`DiscoveryContext`, no `org_roots`
  field) and `:201-245` (`_build_tiers`, tier order `explicit, env, project_override,
  project_legacy, user_global, project_config, builtin`) — confirmed the insertion point is
  between `project_legacy` and `user_global`, matching FR-007's citation.
- `src/runtime/next/runtime_bridge_io.py:230-241` (`_build_discovery_context`, no org-root
  population), `:294-299` (`_template_key_for_file`'s bare `except Exception: return None`), and
  `:325-351` (`_runtime_template_key`'s `project_tiers` list — 5 entries, `.kittify/missions` at
  index 3, `_project_config_pack_paths` at index 4, then builtin/global ordered by mission type) —
  confirmed the FR-009 insertion point sits between those two indices.
- `src/specify_cli/mission_loader/command.py:73-99` (`run_custom_mission`) and `:187-200`
  (`_build_discovery_context`, docstring explicitly says it duplicates
  `runtime_bridge._build_discovery_context` to avoid depending on a private surface) — confirmed
  DEC-006's third wiring site is real and independent of Walk A/B's own construction sites.
- `src/charter/activation/template_resolver.py:165-174` (`_tier_to_origin`'s `tier_prefix` dict, `.get(tier,
  "unknown")` fallback) — confirmed the missing-`ORG` gap DEC-008 describes.
- `src/doctrine/artifact_kinds.py:65-92` (`_HAS_BUILT_IN_CONTENT_DIR`) — confirmed `template` stays
  `False`; this mission's changes do not touch this map.
- `.github/workflows/ci-quality.yml:3349-3400` (diff-coverage critical-path list includes
  `'src/doctrine/*'` and `'src/runtime/next/*'`, `--fail-under=90` on changed lines) and
  `:1437-1462` (`mission-loader-coverage` job, `--cov-fail-under=90`, scoped to
  `src/specify_cli/mission_loader`) — confirmed NFR-006's gate citations are accurate.
- `tests/architectural/test_charter_sole_door_resolver_imports.py`,
  `tests/architectural/test_runtime_charter_doctrine_boundary.py`,
  `tests/doctrine/test_org_pack_subdir.py`, `tests/integration/test_mission_run_command.py` — all
  confirmed present in this checkout.

**Verification gap** (recorded, not blocking): `_rnd/spikes/up-org-template-fsm.md`, cited in the
spec's Provenance section as the originating research artifact, does not exist in this checkout —
there is no `_rnd/` directory at all. This does not undermine the spec's citations (independently
re-verified per its own Provenance section, and re-verified again here), but an implementer should
not go looking for that file as a supplementary reference; it is not retrievable from this branch.

## Implementation Concern Map

> Implementation concerns are NOT work packages and are NOT executable units. `/spec-kitty.tasks`
> translates these into executable WPs — one concern may become multiple WPs; multiple small
> concerns may merge into one WP. IDs below are concern IDs, not sequencing/WP IDs.

**Dependency order**: IC-01 → IC-02 → IC-03 → IC-04 → IC-05 → IC-06 (IC-06 also depends on IC-02's
`ResolutionTier.ORG` existing, but not on IC-03/04/05). IC-05 (list_cmd.py) depends only on IC-02.
IC-04 (FSM discovery) depends on IC-02 for the `ResolutionTier`-adjacent precedent but is otherwise
independent of IC-01/IC-03 — it converges its own, separately-forked walks. This is the spec's
"converge first, then extend" sequencing made concrete: **IC-01 is its own concern and is a hard
prerequisite for IC-03** (the org tier cannot be added to the `specify_cli` resolver in a way that
agrees with the doctrine resolver until the two `_resolve_asset` tier-1 probes already agree).

### IC-01 — Converge the forked `_resolve_asset` tier-1 probe (Step 0)

- **Purpose**: Add the missing mission-scoped override probe to
  `specify_cli/runtime/resolver.py:_resolve_asset`, mirroring
  `doctrine/resolver.py:172-179` verbatim, so the production `mission create` / plan-setup lane
  agrees with `charter list`/`show-origin` on tier-1 resolution before any org tier is added to
  either. This is the prerequisite named in DEC-002/DEC-003: "add an org tier to both" only makes
  sense once both already agree below the insertion point.
- **Relevant requirements**: FR-001 (User Story 2).
- **Affected surfaces**: `src/specify_cli/runtime/resolver.py` (`_resolve_asset`, tier 1 only —
  ~6 LOC per the spec's estimate).
- **Sequencing/depends-on**: none — this is the first concern, and every later concern that touches
  `specify_cli/runtime/resolver.py` (IC-03) depends on it.
- **Risks**: Purely additive (DEC-002) — must not become a module merge. The new probe must not
  change tier ordering for any existing non-override-using caller (NFR-005 zero-behavior-change
  when no override is configured). Low risk given the mirror-verbatim instruction, but the "before"
  state (reproducing the `FileNotFoundError` regression from User Story 2's Independent Test) must
  be captured in a test *before* the fix lands, or the regression-proof shape of SC-002 is lost.

### IC-02 — `ResolutionTier.ORG` enum member + `_tier_to_origin` label

- **Purpose**: Establish the new tier's identity once, in the one place both resolver modules and
  the charter facade share it from (`doctrine/resolver.py`'s `ResolutionTier` enum, re-exported by
  identity through `charter.resolution`), plus the small, independent `_tier_to_origin` label fix
  so the public `charter` surface never renders an org-tier resolution as `"unknown/..."`.
- **Relevant requirements**: FR-002 (User Story 1, 3), FR-012 (no user story — DEC-008 consistency
  fix).
- **Affected surfaces**: `src/doctrine/resolver.py` (`ResolutionTier` enum), `src/charter/template_
  resolver.py` (`_tier_to_origin`'s `tier_prefix` dict). `src/charter/resolution.py` needs no edit
  — the re-export is by identity.
- **Sequencing/depends-on**: IC-01 (sequenced after Step 0 per the spec's mandated ordering,
  though not strictly file-coupled to it — kept in order to preserve "converge first, then extend"
  as a literal sequence, not just a file-dependency graph).
- **Risks**: Low. FR-012 has zero production callers today (DEC-008) — its own test
  (`tests/charter/test_template_resolver.py`) is the only thing exercising it; no risk of behavior
  change to a live path. Enum member insertion position (between `LEGACY` and `GLOBAL_MISSION`)
  should not break any code that iterates `ResolutionTier` by value equality, but an implementer
  should grep for exhaustive-match code (e.g. `match`/`if-elif` chains over all tiers) that might
  need a new arm — none identified during this plan's grounding pass, but not exhaustively ruled
  out either.

### IC-03 — Org tier in both template resolvers' `_resolve_asset` and `resolve_mission`

- **Purpose**: The mission's core defect fix — add the org tier, sourced from
  `resolve_org_roots`, at the identical relative position (between LEGACY and GLOBAL_MISSION) in
  both `doctrine/resolver.py` (same-layer direct import — no facade needed, DEC-003) and
  `specify_cli/runtime/resolver.py` (lazy `from charter.drg import resolve_org_roots`, mirroring
  the five existing `specify_cli/**` call sites — DEC-003), and mirror the same tier into both
  modules' `resolve_mission` functions (FR-005) so mission-config resolution gets the identical
  guarantee.
- **Relevant requirements**: FR-003, FR-004, FR-005 (User Story 1).
- **Affected surfaces**: `src/doctrine/resolver.py` (`_resolve_asset`, `resolve_mission`),
  `src/specify_cli/runtime/resolver.py` (`_resolve_asset`, `resolve_mission`).
- **Sequencing/depends-on**: IC-01 (the `specify_cli` resolver's tier-1 probe must already match
  before the org tier is layered on top of it — adding a tier to two functions that still disagree
  below it would bake the disagreement in at a higher position), IC-02 (`ResolutionTier.ORG` must
  exist first).
- **Risks**: No new `try/except Exception` around `resolve_org_roots()` calls (DEC-005, NFR-001) —
  this is the single most important thing to get right and the single easiest thing to get wrong by
  reflex ("wrap the new external call for safety"). `OrgPackSubdirEscapeError` /
  `OrgPackEnvVarUnsetError` must propagate unswallowed; `load_pack_registry`'s own internal
  fail-soft already covers the malformed-config case. Position parity with IC-04's FSM tiers is a
  cross-concern risk — NFR-004's one parametrized test (see Verification Design) is what actually
  catches drift between this concern and IC-04, not code review alone.

### IC-04 — Org tier in both FSM discovery walks, all three production wiring sites

- **Purpose**: Mirror IC-03's org tier into FSM mission discovery, which has its own, separately
  forked walks (Walk A: `discovery.py`'s generic engine loader; Walk B:
  `runtime_bridge_io.py`'s `_runtime_template_key`). Both source `org_roots` via
  `charter.drg.resolve_org_roots(repo_root)` (DEC-004 — by convention, not gate-enforced for
  `src/runtime/next/**`). Wires `org_roots` at all three real production
  `DiscoveryContext` construction sites, not the two the originating research named (DEC-006): the
  generic engine path, Walk B's own `_build_discovery_context`, and the third,
  independently-duplicated `_build_discovery_context` in `mission_loader/command.py` that backs
  `mission run <key>`.
- **Relevant requirements**: FR-007, FR-008, FR-009 (User Story 3).
- **Affected surfaces**: `src/runtime/next/_internal_runtime/discovery.py` (`DiscoveryContext.
  org_roots` field, `_build_tiers` insertion), `src/runtime/next/runtime_bridge_io.py`
  (`_build_discovery_context` population, `_runtime_template_key`'s `project_tiers` insertion),
  `src/specify_cli/mission_loader/command.py` (`_build_discovery_context`, DEC-006's third site).
- **Sequencing/depends-on**: IC-02 (`ResolutionTier.ORG` — FSM discovery does not itself return a
  `ResolutionTier`, but the tier label `"org"` string used in `_build_tiers` should read as the
  same concept; no hard code dependency, but conceptually sequenced after the enum exists so the
  vocabulary is consistent mission-wide). Not dependent on IC-01/IC-03 at the file level — Walk
  A/B's forks are independent of the template resolvers' fork — but the spec's "converge first,
  then extend" framing places FSM discovery last because it is the third distinct forked pair in
  the mission, following the same discipline established by IC-01/IC-03.
- **Risks**: Three wiring sites, not two — the easiest mistake is fixing only the two sites the
  originating research named and missing `mission_loader/command.py:187-200`, which would leave
  `mission run <key>` blind to the org tier while `spec-kitty next` sees it (exactly the
  "third precedence divergence" NFR-004/SC-008 exists to catch). `command.py` sits inside the
  always-enforced `mission-loader-coverage` `>=90%` gate (NFR-006) — test placement must land
  inside `tests/specify_cli/mission_loader/` or wherever that coverage run collects from, not
  bundled only into a `tests/runtime/next/` test that never touches `command.py`'s own code path.
  Position parity with IC-03 (same NFR-004 test) is again a cross-concern risk, not purely local to
  this concern.

### IC-05 — `list_cmd.py` reports the org tier honestly (flat path, ORG label)

- **Purpose**: Fix `_template_tier_roots`'s org branch to resolve `<org_root>/missions` (flat, not
  the currently-nested `<org_root>/doctrine/missions`) and tag it `ResolutionTier.ORG` instead of
  the borrowed `GLOBAL_MISSION`, so `charter list --all` stops advertising a path the resolver does
  not read and a tier that does not describe what actually resolved.
- **Relevant requirements**: FR-006 (User Story 1, Acceptance Scenario 3).
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/list_cmd.py` (`_template_tier_roots`,
  `:76-86` org branch only).
- **Sequencing/depends-on**: IC-02 (`ResolutionTier.ORG` must exist to be used as the tag).
  Independent of IC-03/IC-04 at the file level, but conceptually the "does the listing agree with
  what the resolver does" check only makes sense once IC-03 has actually landed the resolver-side
  behavior it is describing — sequence after IC-03 for that reason even though there is no direct
  code coupling.
- **Risks**: DEC-007 already confirmed no new architectural allow-list entry is needed (neither
  `test_charter_path_literal_authority.py` nor `test_built_in_location_authority.py`'s join-only AST
  ratchet is tripped by `org_root / "missions"`) — low structural risk. This surface is **not** in
  the diff-coverage critical-path list (NFR-006) — it still needs a focused unit test per the
  repo's Sonar new-code-coverage expectation, but a missed test here will not fail CI's numeric
  gate the way a missed IC-03/IC-04 test would; do not let that lower the bar in practice.

### IC-06 — De-silence Walk B's swallowed FSM template-load failures

- **Purpose**: Route `_template_key_for_file`'s bare `except Exception: return None` into a named
  `DiscoveryWarning`-shaped diagnostic (matching Walk A's existing warning channel) instead of
  silently falling through to the bare `mission_type` string, and add a second named diagnostic
  when a non-built-in tier ships both `mission.yaml` and `mission-runtime.yaml` sidecars for the
  same key (built-in directories, which already legitimately do this, must stay silent).
- **Relevant requirements**: FR-010, FR-011 (User Story 4).
- **Affected surfaces**: `src/runtime/next/runtime_bridge_io.py` (`_template_key_for_file`,
  `:294-299`; `_resolve_runtime_template_in_root`, `:302-319`, for the sidecar diagnostic;
  `_runtime_template_key` to thread the resulting warning(s) out to a caller-visible channel).
- **Sequencing/depends-on**: IC-04 (the org tier must exist for User Story 4's Acceptance Scenario
  1 — "a malformed `mission.yaml` at the org tier" — to be a meaningful test fixture; without the
  org tier there is no org-tier position to place the malformed file at). Also touches the same
  file as IC-04 (`runtime_bridge_io.py`) — sequenced strictly after IC-04 to avoid two concerns
  editing overlapping functions in the same file concurrently (see `owned_files` note below).
- **Risks**: The built-in vs. non-built-in distinction (FR-011's AC2) is the main correctness risk
  — the diagnostic must not fire for the four existing built-in mission directories that already
  ship both sidecar files; this needs an explicit regression test proving built-in behavior is
  unchanged, not just a positive test proving the new diagnostic fires for a non-built-in tier.
  `_runtime_template_key`'s existing fallback-to-`mission_type`-string behavior (the string
  returned when nothing resolves) must be preserved — this concern adds a warning alongside that
  fallback, not a new exception that would change the function's return contract (which would be a
  larger, out-of-scope behavior change).

**`owned_files` note (pairwise disjointness with one stated exception)**: IC-04 and IC-06 both
touch `src/runtime/next/runtime_bridge_io.py`. This is flagged explicitly rather than silently
overlapping `owned_files`: IC-04 edits `_build_discovery_context` and `_runtime_template_key`'s
`project_tiers` construction; IC-06 edits `_template_key_for_file` and
`_resolve_runtime_template_in_root`. These are different functions in the same file, but task
generation should either (a) sequence IC-06's work package strictly after IC-04's in this file, or
(b) merge both into one work package scoped to `runtime_bridge_io.py` as a whole, rather than
parallelizing two work packages against the same file. No other file is touched by two concerns.

## Sizing Assessment

The spec's own Mission Sizing table (~123 production / ~340 test LOC, "M, upper edge") is confirmed
plausible by this plan's concern decomposition: six concerns, each scoped to 1-3 files, none of
which requires new abstractions, new dependencies, or new persisted state — consistent with a
sizing table dominated by "insert N lines at a cited position" rather than open-ended design work.
The mission's own stated risk is not LOC volume but **position-parity discipline across four
independently-edited call sites** (NFR-004) plus the **three-not-two FSM wiring sites** (DEC-006) —
both risks are structural/coordination risks, not size risks, and this plan's IC-01→IC-06 ordering
and the `owned_files` note above are the direct response to them. This plan does not suggest a
larger decomposition than the spec's estimate; six concerns, 3-7 subtasks each expected at task
generation, sit within the 3-7 (ceiling 10) constraint per concern once `/spec-kitty.tasks` expands
IC-01..IC-06 into work packages.

## Verification Design (per-FR before/after measurement)

Every FR below names **where** its before/after measurement lives (a test file, or explicitly
"recorded evidence" for the one FR with no automated gate) and **which tier the after-state must
name** — not merely "a passing test," per the operator brief's requirement.

| FR | Before state | After state (tier named) | Measurement location |
|----|----|----|----|
| FR-001 | `specify_cli.runtime.resolver.resolve_template` raises `FileNotFoundError` on a `.kittify/overrides/missions/<m>/templates/<n>` fixture | Resolves at `tier == ResolutionTier.OVERRIDE`, identical `(path, tier)` to `doctrine.resolver.resolve_template` on the same fixture | New parametrized test in the `specify_cli/runtime` resolver test module — the exact test SC-002 requires |
| FR-002 | `ResolutionTier` has 5 members (no `ORG`) | 6th member `ORG` exists, importable from both `doctrine.resolver` and `charter.resolution` by identity | `tests/doctrine/test_resolver.py`-equivalent unit test asserting `ResolutionTier.ORG` exists and `charter.resolution.ResolutionTier is doctrine.resolver.ResolutionTier` (identity, not just value equality) |
| FR-003 | `doctrine.resolver._resolve_asset` falls through org-pack files to `PACKAGE_DEFAULT` | Resolves org-pack `spec-template.md` at `tier == ResolutionTier.ORG` | `tests/doctrine/` new test — the exact test SC-001 requires (one half; FR-004 is the other) |
| FR-004 | `specify_cli.runtime.resolver._resolve_asset` (production `mission create` lane) falls through the same org-pack file to `PACKAGE_DEFAULT` | Resolves at `tier == ResolutionTier.ORG` through `resolve_configured_template` — the production call | New test calling `resolve_configured_template("spec", ...)` directly (SC-001's literal test, per User Story 1's Independent Test) |
| FR-005 | `resolve_mission` in both modules has no org tier for a `mission.yaml` mission-config (distinct from a template) | Both modules resolve an org-pack `mission.yaml` at `tier == ResolutionTier.ORG`, same relative position as FR-003/FR-004 | Parametrized test mirroring FR-001/SC-002's cross-module equality shape, applied to `resolve_mission` instead of `resolve_template` |
| FR-006 | `charter list --all` reports the org template tier as `GLOBAL_MISSION` at `<org_root>/doctrine/missions/` | Reports `ORG` at `<org_root>/missions/` (flat) | `tests/specify_cli/cli/commands/charter/` — the exact test SC-006 requires |
| FR-007 | `DiscoveryContext` has no `org_roots` field; `_build_tiers` has no `"org"` tier | `org_roots: list[Path]` field exists; `_build_tiers` returns an `("org", ..., context.org_roots)` tuple positioned immediately after `"project_legacy"`, before `"user_global"` | `tests/runtime/next/` (or wherever `discovery.py`'s existing tier tests live) — position-assertion test plus a discovery test proving `selected=True` at tier `"org"` (SC-003, part 1) |
| FR-008 | Walk A's `org_roots` is empty at all production `DiscoveryContext` construction sites (generic engine + `mission_loader/command.py`) | Both sites populate `org_roots` via `charter.drg.resolve_org_roots(repo_root)`; `mission run <key>` discovers the org-pack fixture at tier `"org"` | SC-003 part 3 (`mission run <key>` discovery) — test must exercise `run_custom_mission`/`_build_discovery_context` in `mission_loader/command.py`, placed so it counts toward the `mission-loader-coverage` gate, not just `tests/runtime/next/` |
| FR-009 | Walk B's `_runtime_template_key` has no org entry in `project_tiers`; returns the built-in `mission-runtime.yaml` path for a mission type the org pack also ships | Returns the org-pack's `mission.yaml` path, inserted immediately after the `.kittify/missions` project-legacy entry, before `user_global`/`builtin` | SC-003 part 2 — `tests/runtime/next/` test calling `_runtime_template_key` directly |
| FR-010 | Walk B's `_template_key_for_file` swallows a malformed `mission.yaml` via bare `except Exception: return None`; zero warnings anywhere | A named `DiscoveryWarning`-shaped warning identifies the offending path and tier | SC-005's exact test — `tests/runtime/next/` |
| FR-011 | A non-built-in tier shipping both `mission.yaml` and `mission-runtime.yaml` produces no diagnostic (same silent intra-directory preference as built-in tiers) | A named diagnostic is emitted **only** for non-built-in tiers; the four existing built-in directories (`plan`, `research`, `documentation`, `software-dev`) continue producing zero diagnostics | Two tests: one positive (non-built-in sidecar pair → diagnostic fires), one regression (all four built-in directories → no diagnostic, proving User Story 4 AC2's negative case) |
| FR-012 | `CharterTemplateResolver._tier_to_origin(ResolutionTier.ORG, ...)` renders `"unknown/..."` | Renders `"org/..."` | `tests/charter/test_template_resolver.py` — direct unit test of `_tier_to_origin`, since DEC-008 confirms zero production callers exercise this path today |

**NFR/SC coverage not already folded into the FR rows above**:
- **NFR-001 / SC-004** (fail-soft preserved): (a) `tests/doctrine/test_org_pack_subdir.py`'s
  existing "not swallowed" assertions run unmodified post-change; (b) one new regression test
  proves a malformed `.kittify/config.yaml` still resolves built-in templates AND built-in FSM
  discovery, both before and after — this is a regression guard, not a before/after delta (the
  property is pre-existing per DEC-005), so its "before" and "after" runs should be the same test
  executed against both the pre-fix and post-fix tree (e.g. via a base-branch comparison at
  implementation time, not two different test bodies).
- **NFR-002** (layer boundary): measured by `test_runtime_has_no_direct_doctrine_imports` and
  `test_runtime_has_no_new_lazy_doctrine_imports` continuing green with no new allow-list entries,
  and `test_charter_sole_door_resolver_imports.py` continuing green — existing gates, no new test
  authored, just confirmed still passing after IC-01/IC-03 land.
- **NFR-003** (facade discipline for `src/runtime/next/**`) — see the dedicated section below; this
  is the one NFR with no automated gate.
- **NFR-004 / SC-008** (position parity across all four insertion points): one new parametrized
  test asserting the org tier's relative position is identical in `doctrine/resolver.py`,
  `specify_cli/runtime/resolver.py`, FSM Walk A, and FSM Walk B — green only once FR-003, FR-004,
  FR-007, FR-009 all land. This is the single test that actually catches an IC-03/IC-04 drift; no
  other test in this table substitutes for it.
- **NFR-005 / SC-007** (zero behavior change, no org pack configured): existing template/discovery
  test suites pass unmodified except for this mission's new tests — measured by running those
  suites before and after, excluding baseline reds already known per AGENTS.md's baseline-red
  policy (not this mission's to fix).
- **NFR-006**: covered by the `owned_files`/gate-placement notes on IC-04 and IC-05 above — no
  separate test, this is a test-placement discipline, not a behavior to assert.

## NFR-003 Compliance Without a Gate

`tests/architectural/test_runtime_charter_doctrine_boundary.py`'s `_RUNTIME_ROOT` is hardcoded to
`src/specify_cli` and does not scan `src/runtime/next/**` at all (filed as #3522) — a green CI run
on this mission's PR is **not** evidence that `discovery.py` and `runtime_bridge_io.py` route their
org-root lookups through `charter.drg.resolve_org_roots` rather than a direct `doctrine.*` import.
Compliance here is verified by **review, not by CI**:

1. **At implementation time**: the implementer (or WP reviewer) must manually confirm both files
   import `resolve_org_roots` via `from charter.drg import resolve_org_roots` (lazy, matching the
   existing pattern already present in `runtime_bridge_io.py:106,582,641,681` for other symbols),
   not `from doctrine.drg.org_pack_config import resolve_org_roots` directly.
2. **At PR-description time**: the PR body MUST state explicitly that `src/runtime/next/**`'s
   facade discipline for this mission's changes was confirmed by manual review, not by an
   automated gate, and MUST link or name issue #3522 as the reason no gate caught it. This is a
   textual requirement, not implied by a green run — a reviewer reading only "CI is green" must not
   conclude NFR-003 holds.
3. **At mission-review time**: the post-merge mission review should re-confirm the import
   statements directly (a two-line `grep -n "^from doctrine\|^    from doctrine" src/runtime/next/
   _internal_runtime/discovery.py src/runtime/next/runtime_bridge_io.py` is sufficient) rather than
   trusting the PR description's claim without a spot check, since #3522 remains open and nothing
   will re-verify this automatically on a later, unrelated PR that might touch the same files.

This mission does not fix #3522 itself (Out of Scope, spec.md) — it works around the gap by
convention and by making the gap's existence explicit at every review point above, per the
operator brief's instruction not to let a green run imply more than it proves.

## Post-Design Charter Check

Re-checked after the Implementation Concern Map above: no new gaps. The IC-01→IC-06 decomposition
does not introduce a new architectural layer, a new dependency, or a new persisted format — it
stays inside the "insert a tier at a cited position" shape the Charter Check above anticipated. The
`owned_files` overlap noted for IC-04/IC-06 (both touch `runtime_bridge_io.py`) is a sequencing
note, not a charter violation — no directive requires strict per-concern file exclusivity, only
that task generation not silently parallelize two concerns against one file (handled explicitly
above).
