---
description: "Work package task list for the org doctrine-pack tier mission (#3523)"
---

# Work Packages: Org Doctrine-Pack Tier for the Template Resolution Chain and FSM Discovery

**Inputs**: Design documents from `kitty-specs/up-org-template-fsm-01M06F9K/`
**Prerequisites**: `plan.md` (Implementation Concern Map IC-01..IC-06), `spec.md` (4 user stories,
FR-001–012, NFR-001–006, C-001–006, SC-001–008, 11 Decisions)

**Tests**: Explicitly required by the spec's Verification Design table — every FR names a
before/after test, red-first. This mission does not treat tests as optional.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). Each work
package is one Implementation Concern (IC-01..IC-06) from `plan.md`, translated 1:1. Subtask IDs
are globally unique across the whole mission (`T001` upward, never restarting per WP).

**Prompt Files**: Each work package references a matching prompt file in `/tasks/`. Treat this
file as the high-level checklist; deep implementation detail (exact citations, red-first test
bodies, risk call-outs) lives in the prompt files.

## Subtask Format: `Txxx [P?] Description (WPxx)`

- **[P]** indicates the subtask can proceed in parallel with sibling subtasks *inside the same WP*
  (different files/functions). It is not a cross-WP parallelism marker.
- Subtasks are **reference rows**, not checkboxes: record completion with
  `spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event-log snapshot is the
  sole subtask-completion authority.

## Path Conventions

Single project (`src/`, `tests/`). Every path below is repo-root-relative, matching `plan.md`'s
Project Structure section.

---

## Concern → Work Package Map (from `plan.md`'s Implementation Concern Map)

| WP | Concern | FRs | Depends on | File-collision note |
|----|---------|-----|------------|----------------------|
| WP01 | IC-01 — converge the forked `_resolve_asset` tier-1 probe | FR-001 | — | — |
| WP02 | IC-02 — `ResolutionTier.ORG` + `_tier_to_origin` label | FR-002, FR-012 | — | — |
| WP03 | IC-03 — org tier in both template resolvers | FR-003, FR-004, FR-005 | WP01, WP02 | — |
| WP04 | IC-04 — org tier in both FSM walks, all three wiring sites | FR-007, FR-008, FR-009 | WP02 | shares `runtime_bridge_io.py` with WP06 |
| WP05 | IC-05 — `list_cmd.py` honest reporting | FR-006 | WP02, WP03 | — |
| WP06 | IC-06 — de-silence Walk B's swallowed failures | FR-010, FR-011 | WP04 | shares `runtime_bridge_io.py` with WP04 |

**Hard sequencing constraints carried forward from `plan.md` (not optional):**

1. **WP01 is the prerequisite for WP03.** `plan.md`'s dependency-order line is explicit: "IC-01 is
   its own concern and is a hard prerequisite for IC-03 (the org tier cannot be added to the
   `specify_cli` resolver in a way that agrees with the doctrine resolver until the two
   `_resolve_asset` tier-1 probes already agree)." Adding an org tier to
   `specify_cli/runtime/resolver.py` before its tier-1 probe agrees with `doctrine/resolver.py`
   bakes the existing disagreement in one position higher. WP03's own prompt restates this — it is
   not left only to this table.
2. **WP04 and WP06 both touch `src/runtime/next/runtime_bridge_io.py`.** This is the single
   `owned_files` overlap in the mission (`plan.md`'s "owned_files note"): WP04 edits
   `_build_discovery_context` and `_runtime_template_key`'s `project_tiers` construction; WP06
   edits `_template_key_for_file` and `_resolve_runtime_template_in_root`. Different functions,
   same file — a **file collision, not a functional dependency**. They are sequenced (WP06 depends
   on WP04) rather than parallelized so two WPs never edit the same file concurrently. Both WP04's
   and WP06's own prompts restate this explicitly so a lane agent reading only its own prompt still
   sees it.

---

## Work Package WP01: Converge the Forked `_resolve_asset` Tier-1 Probe (Priority: P1 — prerequisite)

**Goal**: Add the missing mission-scoped override probe to
`specify_cli/runtime/resolver.py:_resolve_asset`, mirroring `doctrine/resolver.py:172-179`
verbatim, so the production `mission create` / plan-setup lane agrees with `charter
list`/`show-origin` on tier-1 resolution before any org tier is added to either resolver.
**Independent Test**: User Story 2's Independent Test — before the fix,
`specify_cli.runtime.resolver.resolve_template(...)` raises `FileNotFoundError` on a
`.kittify/overrides/missions/<m>/templates/<n>` fixture while `doctrine.resolver.resolve_template`
succeeds on the identical fixture; after the fix, both resolve to the identical `(path, tier)` at
`tier == ResolutionTier.OVERRIDE`.
**Prompt**: `/tasks/WP01-converge-resolver-tier1-probe.md`
**Requirement Refs**: FR-001

### Included Subtasks

T001 Red-first test reproducing the `FileNotFoundError` regression + cross-module comparison (WP01)
T002 Add the mission-scoped override probe to `specify_cli/runtime/resolver.py:_resolve_asset` (WP01)
T003 Cross-module parametrized equality test at `tier == ResolutionTier.OVERRIDE` (SC-002) (WP01)
T004 Update `_resolve_asset`'s docstring to document the new tier-1 probe (WP01)
T005 NFR-005 regression check — full resolver test suite passes unmodified except new tests (WP01)

### Implementation Notes

Purely additive (DEC-002) — never merge `doctrine/resolver.py` and
`specify_cli/runtime/resolver.py` into one module. `tests/architectural/test_charter_sole_door_resolver_imports.py`
gate-mandates the two modules stay separate.

### Parallel Opportunities

None meaningful — this is a small, single-file, sequential fix; T001 must precede T002 (red before
fix).

### Dependencies

None (first work package).

### Risks & Mitigations

The "before" state (the `FileNotFoundError` regression) must be captured in a test *before* the fix
lands, or SC-002's regression-proof shape is lost. Every later WP that touches
`specify_cli/runtime/resolver.py` (WP03) depends on this WP landing first.

---

## Work Package WP02: `ResolutionTier.ORG` Enum Member + `_tier_to_origin` Label (Priority: P1)

**Goal**: Establish the new tier's identity once, in the one place both resolver modules and the
charter facade share it from (`doctrine/resolver.py`'s `ResolutionTier` enum, re-exported by
identity through `charter.resolution`), plus the small, independent `_tier_to_origin` label fix.
**Independent Test**: `ResolutionTier.ORG` exists and is importable from both `doctrine.resolver`
and `charter.resolution` by identity; `CharterTemplateResolver._tier_to_origin(ResolutionTier.ORG,
...)` renders `"org/..."` instead of falling back to `"unknown/..."`.
**Prompt**: `/tasks/WP02-resolution-tier-org-enum.md`
**Requirement Refs**: FR-002, FR-012

### Included Subtasks

T006 [P] Add `ResolutionTier.ORG = "org"` between `LEGACY` and `GLOBAL_MISSION` (WP02)
T007 Identity test: `charter.resolution.ResolutionTier is doctrine.resolver.ResolutionTier` (WP02)
T008 [P] Red-first test: `_tier_to_origin(ResolutionTier.ORG, ...)` renders `"unknown/..."` today (WP02)
T009 Add `ResolutionTier.ORG: "org"` to `_tier_to_origin`'s `tier_prefix` dict (WP02)
T010 Grep sweep for exhaustive `ResolutionTier` match/if-elif chains that might need a new `ORG` arm (WP02)

### Implementation Notes

FR-012 has zero production callers today (DEC-008) — only
`tests/charter/test_template_resolver.py` exercises `_tier_to_origin`. Low risk, but still a
silent-degradation defect if skipped: without the label, an org-tier resolution reached through
`CharterTemplateResolver` renders as `"unknown/<mission>/<asset_type>/<filename>"`.

### Parallel Opportunities

T006/T008 can be drafted in parallel (different files: `doctrine/resolver.py` vs
`charter/template_resolver.py`), but T008's assertion needs `ResolutionTier.ORG` to exist
(T006) before it can even reference the member, so land T006 first in practice.

### Dependencies

None at the file level. Sequenced after WP01 per the spec's "converge first, then extend"
ordering (not file-coupled to WP01).

### Risks & Mitigations

Enum member insertion position (between `LEGACY` and `GLOBAL_MISSION`) should not break exhaustive
match/if-elif chains over all tiers — T010 is the explicit check for this; none identified during
planning, but not exhaustively ruled out.

---

## Work Package WP03: Org Tier in Both Template Resolvers (Priority: P1) 🎯 core defect fix

**Goal**: Add the org tier, sourced from `resolve_org_roots`, at the identical relative position
(between `LEGACY` and `GLOBAL_MISSION`) in both `doctrine/resolver.py` and
`specify_cli/runtime/resolver.py`'s `_resolve_asset` and `resolve_mission` functions.

**⚠️ Prerequisite (restated from `plan.md`, not just this table)**: **WP01 must already be merged
before this WP starts.** `specify_cli/runtime/resolver.py`'s tier-1 mission-scoped override probe
(WP01/FR-001) must already agree with `doctrine/resolver.py`'s before an org tier is layered on top
of either — adding a tier to two functions that still disagree below it would bake the disagreement
in at a higher position. This is DEC-002/DEC-003's explicit ordering, not an incidental convenience.

**Independent Test**: User Story 1's Independent Test — an org-pack `spec-template.md` for a
built-in mission type, declared only via `doctrine.org.packs[].local_path`, resolves through
`resolve_configured_template` (the production lane) at `tier == ResolutionTier.ORG`, and loses to a
project override at `.kittify/overrides/missions/<m>/templates/<n>`.
**Prompt**: `/tasks/WP03-org-tier-template-resolvers.md`
**Requirement Refs**: FR-003, FR-004, FR-005

### Included Subtasks

T011 Red-first test: `doctrine.resolver._resolve_asset` falls org-pack files through to `PACKAGE_DEFAULT` (WP03)
T012 Add org tier to `doctrine/resolver.py:_resolve_asset` (direct `doctrine.drg` import, same-layer) (WP03)
T013 Red-first test: production `resolve_configured_template("spec", ...)` falls through to `PACKAGE_DEFAULT` (WP03)
T014 Add org tier to `specify_cli/runtime/resolver.py:_resolve_asset` via the lazy `charter.drg` facade (WP03)
T015 Mirror the org tier into `resolve_mission` in both modules (FR-005) (WP03)
T016 Acceptance Scenario 2 test: project override still wins over org (`tier == ResolutionTier.OVERRIDE`) (WP03)
T017 NFR-001(b)/SC-004 regression test: malformed `.kittify/config.yaml` still resolves built-in templates (WP03)
T018 Update both `_resolve_asset`/`resolve_mission` docstrings for the now-6-tier chain; sweep "5-tier" prose (WP03)

### Implementation Notes

**Use `charter.drg.resolve_org_roots` via the existing lazy-import pattern** for the
`specify_cli/runtime/resolver.py` half — five `src/specify_cli/**` call sites already do it
(`_layer_roots.py:16,31`, `_doctrine_asset.py:87,90`, `_doctrine_collect.py:239,339,497,946`,
`profiles_cmd.py:106,108`, `invocation/org_profiles.py:63,66`). **Never import `doctrine.*`
directly from `specify_cli` or `runtime`** — `tests/architectural/test_runtime_charter_doctrine_boundary.py`
scans all of `src/specify_cli/**` for exactly that, in both module-level and lazy (function-body)
form, against an only-shrink baseline.

**Do not wrap `resolve_org_roots` in `try/except Exception`.** `OrgPackSubdirEscapeError` and
`OrgPackEnvVarUnsetError` are deliberately raised and must propagate;
`tests/doctrine/test_org_pack_subdir.py::test_escape_is_not_swallowed_to_empty_registry` asserts
this. `load_pack_registry` already fail-softs the malformed-YAML case internally — wrapping the
call regresses a tested security invariant while still passing the new feature's own tests.

`doctrine/resolver.py`'s half uses a same-layer direct import
(`from doctrine.drg.org_pack_config import resolve_org_roots`) — no facade needed there, it is
already inside the doctrine layer.

### Parallel Opportunities

T011/T012 (doctrine-layer half) and T013/T014 (specify_cli half) touch disjoint files and can be
drafted in parallel once WP01 has landed; T015 (resolve_mission) depends on both halves' tier logic
existing.

### Dependencies

**WP01 (hard prerequisite, see above), WP02** (`ResolutionTier.ORG` must exist first).

### Risks & Mitigations

No new `try/except Exception` around `resolve_org_roots()` calls — the single easiest thing to get
wrong by reflex ("wrap the new external call for safety"). Position parity with WP04's FSM tiers is
a cross-concern risk, caught by WP04's NFR-004 parametrized test, not by code review alone.

---

## Work Package WP04: Org Tier in Both FSM Discovery Walks, All Three Wiring Sites (Priority: P1)

**Goal**: Mirror WP03's org tier into FSM mission discovery — Walk A (`discovery.py`'s generic
engine loader) and Walk B (`runtime_bridge_io.py`'s `_runtime_template_key`) — wired at **three**
real production `DiscoveryContext` construction sites (DEC-006), not the two the originating
research named.

**⚠️ File collision with WP06 (restated from `plan.md`, not just the table above)**: WP04 and WP06
both edit `src/runtime/next/runtime_bridge_io.py`. WP04 owns `_build_discovery_context` and
`_runtime_template_key`'s `project_tiers` construction; WP06 owns `_template_key_for_file` and
`_resolve_runtime_template_in_root`. **This is a file collision, not a functional dependency** —
do not treat WP06's dependency on WP04 as evidence they could otherwise run in parallel; they
cannot, because they touch the same file. WP06 is sequenced strictly after this WP for that reason
alone.

**Independent Test**: User Story 3's Independent Test — an org-pack runtime-schema `mission.yaml`
(`mission.key: software-dev`, non-empty `steps`) at `<org-pack>/missions/software-dev/mission.yaml`,
declared only via `doctrine.org.packs[].local_path`, is discovered by Walk A, Walk B, and
`mission run <key>` (the third wiring site) at the org tier.
**Prompt**: `/tasks/WP04-org-tier-fsm-discovery.md`
**Requirement Refs**: FR-007, FR-008, FR-009

### Included Subtasks

T019 Red-first test: `DiscoveryContext` has no `org_roots` field; `_build_tiers` has no `"org"` tier (WP04)
T020 Add `org_roots` field to `DiscoveryContext`; insert `"org"` tier in `_build_tiers` after `project_legacy` (WP04)
T021 Populate `org_roots` via the lazy `charter.drg` facade inside `runtime_bridge_io.py`'s `_build_discovery_context` (WP04)
T022 Wire the DEC-006 third site: `mission_loader/command.py`'s own `_build_discovery_context` (WP04)
T023 Insert the org tier into `_runtime_template_key`'s `project_tiers` list (Walk B) (WP04)
T024 Precedence test: project-legacy file wins over org-pack file in both walks (Acceptance Scenario 3) (WP04)
T025 Position-parity test (NFR-004/SC-008) across all four resolver/discovery sites (WP04)
T026 NFR-001/SC-004 regression test (FSM side): malformed `.kittify/config.yaml` still resolves built-in FSM discovery (WP04)

### Implementation Notes

**Use `charter.drg.resolve_org_roots` via the lazy-import pattern, never a direct `doctrine.*`
import** — this applies here too, even though no architectural gate currently scans
`src/runtime/next/**` (filed as #3522, DEC-004). `src/runtime/next/**` is **not covered by an
automated gate for this discipline (NFR-003)** — compliance is verified by manual review at
implementation and PR-review time, not by CI. **The PR description MUST state explicitly** that
`discovery.py` and `runtime_bridge_io.py`'s facade discipline was confirmed by manual review (not
CI) and name issue #3522 as the reason no gate caught it. A green CI run on this WP's changes is
not evidence of compliance — say so in the PR, do not let a reviewer infer it from a green run.

`src/specify_cli/mission_loader/command.py` (T022, the third wiring site) is inside the **enforced
≥90% mission-loader coverage gate** (`.github/workflows/ci-quality.yml:1437-1462`,
`--cov-fail-under=90`, scoped to `src/specify_cli/mission_loader`). The test for T022 must exercise
`run_custom_mission`/`_build_discovery_context` and land where that coverage run actually collects
from (`tests/unit/mission_loader/` or `tests/integration/test_mission_run_command.py`), not only in
a `tests/next/` test that never touches `command.py`'s own code.

### Parallel Opportunities

T019/T020 (discovery.py) can proceed independently of T021/T022/T023 (runtime_bridge_io.py /
mission_loader/command.py) drafting, but T025 (position parity) needs all of them landed, plus
WP03.

### Dependencies

WP02 (`ResolutionTier.ORG`-adjacent vocabulary consistency; no hard code dependency). Not
file-dependent on WP01/WP03, but T025's position-parity test needs WP03's FR-003/FR-004 already
landed to be meaningfully green — flag this explicitly if WP04 is implemented before WP03 in
practice.

### Risks & Mitigations

Three wiring sites, not two — the easiest mistake is fixing only the two sites the originating
research named and missing `mission_loader/command.py:187-200`, leaving `mission run <key>` blind
to the org tier while `spec-kitty next` sees it (the "third precedence divergence" NFR-004/SC-008
exists to catch). File collision with WP06 (see callout above) — do not parallelize.

---

## Work Package WP05: `list_cmd.py` Reports the Org Tier Honestly (Priority: P2)

**Goal**: Fix `_template_tier_roots`'s org branch to resolve `<org_root>/missions` (flat, not the
currently-nested `<org_root>/doctrine/missions`) and tag it `ResolutionTier.ORG` instead of the
borrowed `GLOBAL_MISSION`.
**Independent Test**: User Story 1, Acceptance Scenario 3 — `charter list --all` reports the
template's tier as `ORG` at the flat `<org_root>/missions/software-dev/templates/` path.
**Prompt**: `/tasks/WP05-list-cmd-org-tier-reporting.md`
**Requirement Refs**: FR-006

### Included Subtasks

T027 Red-first test: `charter list --all` reports `GLOBAL_MISSION` at the nested path today (WP05)
T028 Fix `_template_tier_roots`'s org branch: flat path, `ResolutionTier.ORG` tag (WP05)
T029 Confirm DEC-007's architectural-gate ruling holds — no new allow-list entry needed (WP05)
T030 Focused unit test per repo Sonar new-code-coverage expectation for the org branch (WP05)

### Implementation Notes

DEC-009: `_template_tier_roots`'s **project**-tier path mismatch
(`project_root / "doctrine" / "missions"`) is a separate, pre-existing oddity — **out of scope**
(C-004). Do not fix it while touching this function; note it if it is confusing but leave it alone.

### Parallel Opportunities

None meaningful — small, single-function fix.

### Dependencies

WP02 (`ResolutionTier.ORG` must exist to be used as the tag). Sequenced after WP03 — the listing
only makes sense to fix once the resolver-side org tier behavior it describes actually exists,
even though there is no direct code coupling between `list_cmd.py` and the resolver modules.

### Risks & Mitigations

This surface is **not** in the diff-coverage critical-path list (NFR-006) — a missed test here will
not fail CI's numeric gate. Do not let that lower the bar in practice; T030 is the only thing that
actually guards this surface.

---

## Work Package WP06: De-Silence Walk B's Swallowed FSM Template-Load Failures (Priority: P3)

**Goal**: Route `_template_key_for_file`'s bare `except Exception: return None` into a named
`DiscoveryWarning`-shaped diagnostic, and add a second named diagnostic when a non-built-in tier
ships both `mission.yaml` and `mission-runtime.yaml` sidecars for the same key.

**⚠️ File collision with WP04 (restated from `plan.md`, not just the table above)**: WP04 and WP06
both edit `src/runtime/next/runtime_bridge_io.py`. WP06 owns `_template_key_for_file` and
`_resolve_runtime_template_in_root`; WP04 owns `_build_discovery_context` and
`_runtime_template_key`'s `project_tiers` construction. **This is a file collision, not a
functional dependency** — WP06 depends on WP04 in the dependency graph specifically to avoid two
WPs editing the same file concurrently, not because WP06's diagnostics logic needs WP04's tier
logic to function. Do not "optimize" these back into parallel WPs.

**Independent Test**: User Story 4's Independent Test — a malformed `mission.yaml` at the org tier
produces zero warnings today (silent fallthrough); after the fix, a named warning identifies the
offending path and tier.
**Prompt**: `/tasks/WP06-desilence-walk-b-failures.md`
**Requirement Refs**: FR-010, FR-011

### Included Subtasks

T031 Red-first test: Walk B swallows a malformed org-tier `mission.yaml` with zero warnings anywhere (WP06)
T032 Route `_template_key_for_file`'s failure into a named `DiscoveryWarning`-shaped diagnostic (WP06)
T033 Red-first test: a non-built-in tier shipping both sidecars produces no diagnostic today (WP06)
T034 Add the sidecar diagnostic in `_resolve_runtime_template_in_root`, scoped to non-built-in tiers only (WP06)
T035 Regression test: all four built-in mission directories still produce zero diagnostics (WP06)
T036 NFR-003 compliance confirmation: grep both `discovery.py` and `runtime_bridge_io.py` for direct `doctrine.*` imports; state the finding in the PR description (WP06)

### Implementation Notes

T031's red-first test overlaps an **existing** test:
`tests/runtime/test_bridge_io.py::test_template_key_for_file_returns_none_on_load_failure`
currently asserts the exact swallow behavior this WP changes. Update that test's assertion as part
of this WP rather than leaving it contradicting the fix — do not just add a new test alongside a
now-stale one.

`_runtime_template_key`'s existing fallback-to-`mission_type`-string behavior (the string returned
when nothing resolves) must be preserved — this WP adds a warning alongside that fallback, not a
new exception that would change the function's return contract.

Same NFR-003 discipline as WP04 applies here (`src/runtime/next/**`, no automated gate, review +
PR-description requirement — see WP04's Implementation Notes for the full text, repeated in this
WP's own prompt file per the operator brief's instruction that a lane agent must see it without
reading WP04's prompt).

### Parallel Opportunities

T031/T032 (de-silencing) and T033/T034 (sidecar diagnostic) touch different functions in the same
file — draft sequentially within this WP to avoid merge noise, even though they are logically
independent.

### Dependencies

WP04 (`ResolutionTier.ORG`/org tier must exist for User Story 4's Acceptance Scenario 1 — "a
malformed `mission.yaml` at the org tier" — to be a meaningful test fixture; also the file-collision
sequencing described above).

### Risks & Mitigations

The built-in vs. non-built-in distinction (FR-011's AC2) is the main correctness risk — T035 is the
explicit regression guard; a positive test alone (T033/T034) is not sufficient.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → WP03 → WP04 → WP05 → WP06 is a valid total order consistent with
  every dependency edge above (WP01 and WP02 have no dependency between them and could be done in
  either order, but WP03 needs both).
- **Parallelization**: WP01 and WP02 have no dependency on each other and can proceed in parallel.
  WP03 and WP04 both depend only on WP02 (not on each other) and could in principle proceed in
  parallel once WP02 lands — but WP04's own position-parity subtask (T025) needs WP03's org tier to
  already exist to go green, so implementing WP03 before WP04 in practice is strongly recommended
  even though no hard dependency edge forces it. WP05 and WP06 are each single-predecessor tails.
- **MVP Scope**: WP01 + WP02 + WP03 deliver User Story 2 (P1) and User Story 1's template-resolution scenarios — the core template User Story 1's Acceptance Scenario 3 (`charter list --all` reporting, FR-006) belongs to WP05, so User Story 1 is not fully delivered until WP05 lands.
  resolution defect. WP04 adds User Story 3 (P2, FSM discovery). WP05 and WP06 are the P2/P3
  reporting-honesty and diagnostic-visibility polish.
- **Single-branch topology**: per `plan.md`'s Branch contract, this mission has no coordination
  worktree and no lane split — all six WPs land on `up-org-template-fsm`.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP02 |
| FR-003 | WP03 |
| FR-004 | WP03 |
| FR-005 | WP03 |
| FR-006 | WP05 |
| FR-007 | WP04 |
| FR-008 | WP04 |
| FR-009 | WP04 |
| FR-010 | WP06 |
| FR-011 | WP06 |
| FR-012 | WP02 |
| NFR-001 | WP03, WP04 |
| NFR-002 | WP03 |
| NFR-003 | WP04, WP06 |
| NFR-004 | WP03, WP04 |
| NFR-005 | WP01, WP03 |
| NFR-006 | WP04, WP05 |
| C-001 | WP01, WP03 |
| C-004 | WP05 |
| C-005 | WP06 |
| SC-001 | WP03 |
| SC-002 | WP01 |
| SC-003 | WP04 |
| SC-004 | WP03, WP04 |
| SC-005 | WP06 |
| SC-006 | WP05 |
| SC-007 | WP01, WP03, WP04 |
| SC-008 | WP04 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Red-first FileNotFoundError regression test | WP01 | P1 | No |
| T002 | Add tier-1 mission-scoped override probe | WP01 | P1 | No |
| T003 | Cross-module equality test (SC-002) | WP01 | P1 | No |
| T004 | Update `_resolve_asset` docstring | WP01 | P1 | No |
| T005 | NFR-005 regression check | WP01 | P1 | No |
| T006 | Add `ResolutionTier.ORG` enum member | WP02 | P1 | Yes |
| T007 | Identity test across `doctrine.resolver`/`charter.resolution` | WP02 | P1 | No |
| T008 | Red-first `_tier_to_origin` test | WP02 | P1 | Yes |
| T009 | Add `ORG` entry to `_tier_to_origin` | WP02 | P1 | No |
| T010 | Grep sweep for exhaustive `ResolutionTier` matches | WP02 | P1 | No |
| T011 | Red-first `doctrine.resolver` org-tier test | WP03 | P1 | Yes |
| T012 | Add org tier to `doctrine/resolver.py:_resolve_asset` | WP03 | P1 | Yes |
| T013 | Red-first production `resolve_configured_template` test | WP03 | P1 | Yes |
| T014 | Add org tier to `specify_cli/runtime/resolver.py:_resolve_asset` | WP03 | P1 | Yes |
| T015 | Mirror org tier into `resolve_mission` (both modules) | WP03 | P1 | No |
| T016 | Acceptance Scenario 2 (project override wins) test | WP03 | P1 | No |
| T017 | NFR-001(b)/SC-004 regression test (template side) | WP03 | P1 | No |
| T018 | Docstring/prose sweep ("5-tier" → "6-tier") | WP03 | P1 | No |
| T019 | Red-first `DiscoveryContext`/`_build_tiers` test | WP04 | P1 | Yes |
| T020 | Add `org_roots` field + `_build_tiers` insertion | WP04 | P1 | Yes |
| T021 | Populate `org_roots` in `_build_discovery_context` | WP04 | P1 | No |
| T022 | Wire DEC-006 third site (`mission_loader/command.py`) | WP04 | P1 | No |
| T023 | Insert org tier into `_runtime_template_key`'s `project_tiers` | WP04 | P1 | No |
| T024 | Precedence test (Acceptance Scenario 3) | WP04 | P1 | No |
| T025 | Position-parity test (NFR-004/SC-008) | WP04 | P1 | No |
| T026 | NFR-001/SC-004 regression test (FSM side) | WP04 | P1 | No |
| T027 | Red-first `charter list --all` test | WP05 | P2 | No |
| T028 | Fix `_template_tier_roots` org branch | WP05 | P2 | No |
| T029 | Confirm DEC-007 architectural-gate ruling | WP05 | P2 | No |
| T030 | Focused unit test for org branch | WP05 | P2 | No |
| T031 | Red-first Walk B swallow test | WP06 | P3 | Yes |
| T032 | Route failure into named `DiscoveryWarning` | WP06 | P3 | Yes |
| T033 | Red-first sidecar-pair diagnostic test | WP06 | P3 | Yes |
| T034 | Add sidecar diagnostic (non-built-in only) | WP06 | P3 | Yes |
| T035 | Regression test: built-in dirs stay silent | WP06 | P3 | No |
| T036 | NFR-003 compliance confirmation (grep + PR note) | WP06 | P3 | No |
