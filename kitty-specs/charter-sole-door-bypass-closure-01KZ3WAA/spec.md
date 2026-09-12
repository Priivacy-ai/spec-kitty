# Mission Specification: Charter as Sole Door: Close Bypass Access Paths

**Mission Branch**: `feat/charter-sole-door-bypass-closure`
**Created**: 2026-08-03
**Status**: Draft
**Input**: User description: "Go for item 2 [charter-as-sole-door bypass closure], see if the others can be (partially) folded in. Launch a research squad to ground the work, then proceed to spec."

## User Scenarios & Testing *(mandatory)*

The users are the **runtime** (the code paths that reach provisioned doctrine assets while executing a
mission) and the **maintainer** who needs one enforced answer to "how does the runtime reach a doctrine
asset?" The failure today: `charter.resolver.DoctrineService` (`src/charter/resolver.py:57-139`) is a
*canonical factory* that activation-gates only 3 of 10 doctrine-artifact kinds (`paradigm`, `procedure`,
`agent_profile`) and forwards the other 7 (`directive`, `tactic`, `styleguide`, `toolguide`,
`mission_step_contract`, `glossary_pack`, and the `mission-type` token) unfiltered via `__getattr__`. Worse,
it is *one of many* entry points: roughly 20 call sites across four categories reach doctrine assets
without going through the factory at all — some with code comments explicitly citing reasons for avoiding
it (a "runtime→charter→doctrine boundary ratchet"). This is the G1 done-bar named in
`docs/plans/3-2-x-open-core-delivery-plan.md` §2.2 item 1: "All provisioned assets reachable by the runtime
*through* the charter — charter as the sole door. This is a *no-bypass* condition: any path that reaches
assets around the charter is a second seam that leaks internals and forces a *second* break later."

*Revised at planning time*: a Phase 0 research pass corrected several of the pre-spec squad's counts — two
of the originally-flagged sites turned out to access a legitimately separate, out-of-scope directory
(`.kittify/profiles`, C-006); the "10 kinds" gating turned out to split into 9 mechanical kinds plus one
structurally different `mission-type` token needing a different repository; the "2 hardcoded paths" turned
out to be 3, converging on a promoted authority rather than on `pack_paths` (deferred to `#3091`); and a
real single-canonical-authority violation (two divergent builder functions) was found and folded in as new
scope. Each user story below states its planning-time revision inline rather than leaving the original,
now-superseded framing standing.

*Second revision, post-plan squad*: a 4-lens adversarial review (architect-alphonso, reviewer-renata,
debugger-debbie, planner-priti) independently verified the Phase 0 research and found 3 more construction
sites (one with a fail-open bug, folded into FR-002/FR-008), a live `._inner` reach-around that would have
defeated every gate this mission ships (closed as new FR-010), an IC-sequencing bug in the plan, and several
fakeable-assertion gaps in the NFRs — all folded into the FR/NFR text below rather than left for an
implementer to discover mid-WP. See `research.md`'s "Post-Plan Squad Findings" section for the full record.

A pre-spec research squad enumerated the concrete bypass list (this spec's FR anchors), extracted the
established "make X the sole door" pattern from `charter-pack-usage-journey-01KYWWTF`, extracted the
non-vacuous-gate idiom from `doctrine-charter-split-unification-01KZ0SRB` (WP10/WP11), and assessed five
adjacent GitHub issues (#2986, #3036, #3039, #3091, #3022) for fold-in — all five came back
**ADJACENT-BUT-SEPARATE**: same governing principle or same "gate enforces the bug it should catch" shape,
but a different code surface, violation class, or track (import-direction ratchets, doctrine-content
shippability, doctrine-tree relocation, pack extraction) than access-path bypass closure. They stay
deferred as their own missions (C-003).

### User Story 1 — Direct repository/service construction goes through the factory, no exceptions — except the legacy profiles directory (Priority: P1)

Five of the seven originally-flagged `AgentProfileRepository(...)` sites, plus six raw
`doctrine.service.DoctrineService(...)` construction sites, bypass `charter.resolver.DoctrineService`
entirely and are eliminated by this mission. **Two of the seven are reclassified, not eliminated**, per a
planning-phase finding: `src/specify_cli/invocation/registry.py:48` and
`src/specify_cli/cli/commands/profiles_cmd.py:83` construct `AgentProfileRepository` against
`.kittify/profiles` — a **local-override directory outside the doctrine activation model by design**, not a
doctrine-asset access path. Both sites already call `charter.resolver.DoctrineService` separately, correctly,
for their doctrine-layer data; the `.kittify/profiles` construction is a legitimately different concern
slated for its own future rework and is explicitly **out of scope** here — do not route it through the
factory (operator decision).

Two of the five remaining `AgentProfileRepository` sites
(`src/specify_cli/cli/commands/agent/tasks_status_cmd.py:712,823`, dashboard status icons) carry code
comments explicitly justifying the bypass as avoiding a "runtime→charter→doctrine boundary ratchet". Per
operator decision, this mission does **not** grandfather these as exceptions — it eliminates every one of
the five, which means first understanding and resolving whatever concern each comment names (e.g., a
lazy-construction, caching, or import-timing reason), not just deleting the comment and routing through the
factory blindly.

This user story also folds in a **planning-phase discovery**: `specify_cli.doctrine_service_factory.
build_activation_aware_doctrine_service` and `charter.doctrine_service_builder.
_build_activation_aware_doctrine_service` — the two functions this mission treats as the sanctioned
construction path — are themselves **not behaviourally identical** (divergent `active_languages` handling;
divergent `org_roots` defaulting). Left alone, "route through the factory" would still resolve to one of two
silently-different catalogs depending on which builder a caller happens to use — a live violation of C-001
discovered as a byproduct of this mission's own work, and domain-matched enough to fold in rather than defer.

**Why this priority**: this is the largest concrete bypass count (11 of ~18 in-scope sites, after the
`.kittify/profiles` reclassification) and carries the most "this bypass exists for a stated reason" risk —
get it wrong and either a regression ships (the avoided ratchet reappears) or the "no exceptions" decision
quietly regresses into a new allowlist.

**Independent Test**: grep `src/` for `AgentProfileRepository(` and `DoctrineService(` outside
`src/charter/resolver.py`, its two (now-unified) builder call sites, and the two explicitly-excluded
`.kittify/profiles` sites — zero matches. A second test constructs the unified builder twice with the same
`repo_root` from both its old call sites and asserts identical output (proving the divergence is closed, not
just hidden).

**Acceptance Scenarios**:

1. **Given** the dashboard status-icon renderer (`tasks_status_cmd.py:712,823`), **When** it needs an agent
   profile, **Then** it resolves through `charter.resolver.DoctrineService`, and the concern the removed
   comment named (the boundary ratchet) is proven not to reappear — either because it was never a real risk
   for this call shape, or because the underlying cause (e.g. eager construction cost) is fixed.
2. **Given** `src/charter/compiler.py:802` and the four `_doctrine_collect.py` sites, **When** they read
   `.agent_profiles` / `.glossary_packs` from a raw `DoctrineService`, **Then** they read the same data
   through `charter.resolver.DoctrineService`; the four `_doctrine_collect.py` diagnostic sites use the
   factory's explicit unfiltered mode (`pack_context=None`) so doctor/health output is not silently narrowed
   by activation state.
3. **Given** `registry.py:48` and `profiles_cmd.py:83`, **When** they construct `AgentProfileRepository`
   against `.kittify/profiles`, **Then** that specific construction call is left untouched — only their
   separate, already-correct doctrine-layer factory calls are in scope.
4. **Given** the two divergent builder functions, **When** a caller invokes either one with the same
   `repo_root`, **Then** both now return the same catalog (unified `active_languages` and `org_roots`
   handling) — there is exactly one construction behaviour, not two call paths that happen to look similar.

---

### User Story 2 — The 5-tier template/command resolver axis goes through the factory (Priority: P1)

`src/doctrine/resolver.py::_resolve_asset` resolves templates/commands across five tiers (OVERRIDE, LEGACY,
GLOBAL_MISSION, GLOBAL, PACKAGE_DEFAULT), and `resolve_mission` duplicates four of those tiers again for
mission-type resolution. Neither routes through the charter factory; `charter.template_resolver.
CharterTemplateResolver` calls the raw resolver directly. This axis has no activation concept at all today.
`_resolve_asset`/`resolve_mission` **stay in `doctrine/resolver.py`** — that module deliberately lives there
so the sanctioned `charter → doctrine` import direction can reach it; the fix adds resolution methods to
`charter.resolver.DoctrineService` itself (mirroring `CharterTemplateResolver`'s current public surface) that
internally call into `doctrine/resolver.py`, rather than moving the tier logic or inventing a second
charter-layer resolver object (C-001).

A planning-phase sweep for other direct `doctrine.resolver` importers found two more in-scope sites beyond
the original FR-003 anchor, both already inside `src/charter/**` but still bypassing the to-be-added factory
methods: `src/charter/resolution.py` (a facade re-export consumed by `specify_cli/runtime/resolver.py`) and
`src/charter/context_renderers/template_include.py` (a lazy `ResolutionTier` import). Both fold into FR-003's
scope. (`specify_cli/runtime/resolver.py`'s own tier-1-through-4 reimplementation is a separate semantic-drift
risk — noted in research.md — but is not a factory bypass and is out of this mission's scope.)

**Why this priority**: it is a whole resolution axis, not a single call site — every template/command
render in the product currently bypasses the sole door.

**Independent Test**: `CharterTemplateResolver`, `charter/resolution.py`, and `template_include.py` reach
`doctrine/resolver.py`'s tier functions only via `charter.resolver.DoctrineService`; a direct import of
`doctrine.resolver` from outside `src/charter/**` is the new bypass-door signature this mission eliminates.

**Acceptance Scenarios**:

1. **Given** a project with an OVERRIDE-tier template, **When** `CharterTemplateResolver` resolves it,
   **Then** the resolution call passes through the charter factory and returns the same template a direct
   `doctrine.resolver` call would have.
2. **Given** `resolve_mission`'s duplicated tier logic, **When** it is retargeted, **Then** the duplication
   with `_resolve_asset` is resolved through the factory without silently diverging tier semantics between
   the two call paths.

---

### User Story 3 — Duplicate hardcoded missions-root paths consolidate onto one promoted authority (Priority: P1)

**Revised at planning time**: the original framing (retarget both hardcodes onto
`doctrine.pack_paths.built_in_dir`) is **unsatisfiable as specified** — `pack_paths` has no `missions/`
content directory at all; that only exists after the deferred `#3091` relocation (C-003). Planning research
also found a **third** independent hardcode of the same missions-root, bringing the real count to three:
`src/charter/mission_type_profile_repository.py:66::builtin_missions_root()`
(`Path(__file__).resolve().parents[1]/"doctrine"/"missions"`), `src/specify_cli/runtime/home.py:107-108`'s
`dev_roots` fallback tuple, and — already correctly implemented —
`src/doctrine/missions/repository.py:98::MissionTemplateRepository.default_missions_root()`, which resolves
the same root via `importlib.resources` (wheel-safe, with a documented fallback). This mission **promotes
`default_missions_root()` as the one shared authority** and retargets the other two hardcodes onto it — a
duplication fix achievable now, distinct from the `pack_paths` convergence that `#3091` will deliver later.

**Why this priority**: a hardcoded path is a silent, hard-to-grep bypass that survives even after every
repository-construction site is fixed — and three independent copies of the same root is exactly the
single-canonical-authority violation C-001 exists to close, even before `#3091` lands.

**Independent Test**: neither `builtin_missions_root()` nor `runtime/home.py`'s `dev_roots` contains its own
literal `Path(__file__)`-relative missions-root construction; both call
`MissionTemplateRepository.default_missions_root()`.

**Acceptance Scenarios**:

1. **Given** a standard install, **When** `builtin_missions_root()` is called, **Then** it returns exactly
   `MissionTemplateRepository.default_missions_root()`'s output, proven by an equality regression test (not
   just "still returns a path").
2. **Given** a dev checkout, **When** `runtime/home.py` resolves its dev-root fallback, **Then** it calls the
   same promoted authority instead of its own duplicated literal tuple.
3. **Given** this mission's diff, **When** it is reviewed against `#3091`, **Then** the PR description states
   explicitly that full convergence onto `doctrine.pack_paths.built_in_dir` still requires the `#3091`
   relocation and is not claimed here (NFR-004).

---

### User Story 4 — The factory activation-gates all 10 doctrine-artifact kinds (Priority: P1)

`charter.resolver.DoctrineService` filters exactly 3 properties (`paradigms`, `procedures`,
`agent_profiles`); every other property falls through `__getattr__` to the raw inner service, unfiltered.
Per operator decision, this mission extends activation-gating to the remaining 7 kinds (`directive`,
`tactic`, `styleguide`, `toolguide`, `mission_step_contract`, `glossary_pack`, plus the `mission-type`
token), so "sole door" and "gated" are not two different claims — routing every call site through the
factory (User Stories 1-3) would otherwise still leak ungated data for 7 of 10 kinds.

**Revised at planning time — two different shapes of work, not one uniform one.** Six of the seven kinds
(`directive`, `tactic`, `styleguide`, `toolguide`, `mission_step_contract`, `glossary_pack`) are mechanical:
`PackContext` already carries a three-state `activated_<kind>` field for each, and `doctrine.service.
DoctrineService` already exposes a matching raw property — the fix copies the existing `paradigms`/
`procedures`/`agent_profiles` property pattern six times. The **`mission-type` token is structurally
different** and does not fit that pattern: its `PackContext.activated_mission_types` field is a plain
`frozenset[str]` (never `None` — the catalog-default collapse already happens at `PackContext` construction
time, so the three-state semantics don't apply to it), and `doctrine.service.DoctrineService` has **no
`mission_types` property at all** — mission-type resolution lives entirely in a separate repository,
`charter.mission_type_profile_repository.MissionTypeProfileRepository` /
`charter.mission_type_profiles.resolve_mission_type_context()`. Per operator decision (real 10/10 coverage,
not a 9/10 carve-out), this mission adds equivalent activation filtering **to that repository**, not to
`charter.resolver.DoctrineService` — a genuinely different, non-mechanical change from the other 9 kinds.

**Why this priority**: without this, User Stories 1-3 make the factory the sole *path* without making it a
real *gate* for most of what travels through that path — the "3 of 10 kinds" gap is the other half of the
G1 done-bar, not a separate concern.

**Independent Test**: for each of the 6 mechanical kinds, a project with that pack tier deactivated returns
a filtered (non-empty-catalog-default or explicitly-empty, per the three-state semantics below) result from
the factory property, not the raw unfiltered catalog. For `mission-type`, a project with a subset of
mission-types activated returns only that subset from `MissionTypeProfileRepository`, not the full built-in
set.

**Acceptance Scenarios**:

1. **Given** a bare project with no activated packs, **When** the factory resolves a previously-ungated
   mechanical kind (e.g. `directives`), **Then** it returns the same three-state semantics already proven for
   `directives` resolution elsewhere in the codebase (`None` → catalog default; `frozenset()` → explicit
   opt-out, empty; `{ids}` → filtered) — not a naive `sorted(activated or frozenset())` regression that
   silently empties a bare project's default catalog.
2. **Given** a project with a subset of `glossary_pack`s activated, **When** the factory resolves
   `glossary_packs`, **Then** only the activated subset is returned.
3. **Given** a project with a subset of mission-types activated, **When** `MissionTypeProfileRepository`
   resolves the available mission-type set, **Then** it returns only that subset, without regressing a bare
   project's full built-in default (`research`, `software-dev`, `documentation`, `plan`, etc. still resolve
   when nothing is explicitly activated).

---

### User Story 5 — A new bypass cannot be silently reintroduced (Priority: P2)

Closing today's ~20 bypass doors is only durable if a future PR cannot casually reopen one. This mirrors
the charter's architectural-gate-discipline standing order and the WP10 (`test_charter_no_specify_cli_
import.py`) / WP11 (`test_charter_path_literal_authority.py`) precedent from `doctrine-charter-split-
unification-01KZ0SRB` — except here the operator has chosen a **zero-tolerance frozen baseline**, not a
shrink-only allowlist, because User Story 1 already rejected keeping any site as a permitted exception.

**Why this priority**: P2, not P1 — it is the durability guarantee on top of User Stories 1-4's (FR-001-006)
actual closure, not the closure itself; a mission that closes the doors without a gate still delivers the
SC-001 outcome, just without the anti-regression guarantee.

**Independent Test**: reintroduce any one of the four closed bypass shapes (a raw `AgentProfileRepository(`
construction, a raw `DoctrineService(` construction, a direct `doctrine.resolver` import from outside
`src/charter/**`, or a hardcoded doctrine-asset-root literal) in a scratch module and confirm the new
gate(s) go red, naming the exact site — proving the gate is non-vacuous (mirrors NFR-004 of the WP10/WP11
precedent).

**Acceptance Scenarios**:

1. **Given** the gate(s) shipped by this mission, **When** a self-mutation test reintroduces each closed
   bypass shape, **Then** the relevant gate fails and names the offending file/line.
2. **Given** `tests/architectural/test_org_activation_seam.py` and `tests/architectural/test_layer_rules.py`
   (existing, narrower coverage), **When** the new gates are added, **Then** they extend rather than
   duplicate that existing coverage — no two gates assert the same fact.

### Edge Cases

- What happens when a project has activated **no** packs at all? Extending activation-gating to the 7
  previously-unfiltered kinds (User Story 4) must preserve the existing three-state semantics
  (`None`/`frozenset()`/`{ids}`) proven for the 3 already-gated kinds — a bare project must keep seeing its
  full built-in default catalog for those 7 kinds, not silently see it empty out.
- What happens when a call site needs a doctrine asset **before** the charter factory itself is
  constructible (e.g., during the charter compilation pass that produces the very config the factory reads,
  or during agent-profile resolution used to pick which profile loads the charter)? This bootstrap/circularity
  case is the most likely reason a "no exceptions" site turns out to be genuinely irreducible — the mission
  must surface this to the operator as a scoped finding rather than silently allowlisting it (C-002).
- How does the system handle a dashboard render loop calling the factory at a frequency where the earlier
  bypass comment's stated concern (a "boundary ratchet") was actually a real performance guard, not just
  caution? NFR-005 requires measuring this, not assuming it away.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Eliminate 4 of the 7 originally-flagged direct `AgentProfileRepository(...)` construction sites outside `charter.resolver.DoctrineService`: `src/runtime/next/runtime_bridge_io.py:576`, `src/specify_cli/tool_surface/profiles/projection.py:84`, `src/specify_cli/cli/commands/agent/tasks_status_cmd.py:712` and `:823`. **Excluded (planning-phase reclassification):** `src/specify_cli/invocation/registry.py:48` and `src/specify_cli/cli/commands/profiles_cmd.py:83` construct against `.kittify/profiles` (a local-override directory outside the doctrine activation model, slated for separate future rework) — leave untouched. **Confirmed bootstrap carve-out, not migrated** (post-tasks squad correction): `src/charter/profile_resolution.py:81`'s `_default_agent_profile_repository()` is a zero-argument, module-level cached function with no `repo_root` to build a factory from — document it as a genuine C-002 bootstrap case, do not attempt to route it through the factory. `projection.py:84` needs a new public accessor on the factory (`agent_profile_repository`) for mutation-capable repository access, since the filtered property alone cannot support `register_overlay()` (the only method this site needs — `get_ancestors()` is unused here). For the two `tasks_status_cmd.py` sites whose comments cite avoiding a "runtime→charter→doctrine boundary ratchet": the concern is confirmed a red herring against the existing gate (`tests/architectural/test_runtime_charter_doctrine_boundary.py` only scans module-level imports; both the old and new construction are function-local) — the real, unmeasured risk is construction cost, covered by NFR-005. | Draft |
| FR-002 | Eliminate the unwrapped raw `doctrine.service.DoctrineService(...)` construction sites — the original 6 (`src/charter/compiler.py:802`, `src/specify_cli/cli/commands/_doctrine_asset.py:75`, `src/specify_cli/cli/commands/_doctrine_collect.py:193`, `:283`, `:420`, `:828`) plus **3 more found by the post-plan squad**: `src/specify_cli/charter_runtime/lint/checks/org_layer.py:244` and `:275`, and `src/specify_cli/cli/commands/charter/generate.py:56` — routing each through `charter.resolver.DoctrineService` instead of the raw inner service. `org_layer.py:252-253`'s `except ImportError: pass` currently **fails open**, silently returning the bare unfiltered inner service when the wrap import fails — this must become fail-closed (raise or fail the operation), never a silent unfiltered fallback. The four `_doctrine_collect.py` diagnostic sites (profile/glossary-pack health, cross-layer collision detection, provenance lookup) need the **unfiltered, all-layer** view to avoid silently narrowing doctor/health output for deactivated packs; wrap them via the factory's explicit unfiltered mode (`charter.resolver.DoctrineService(inner, pack_context=None)`) rather than the activation-filtered path — same class, same single canonical authority (C-001), documented rationale at each site. | Draft |
| FR-003 | Retarget the 5-tier template/command resolver axis (`src/doctrine/resolver.py::_resolve_asset`, tiers OVERRIDE/LEGACY/GLOBAL_MISSION/GLOBAL/PACKAGE_DEFAULT, ~lines 164-213) and its duplicated tier logic in `resolve_mission` (~lines 284-342) by adding resolution methods to `charter.resolver.DoctrineService` (mirroring `CharterTemplateResolver`'s current public surface) that call into `doctrine/resolver.py` internally — the tier functions stay in `doctrine/resolver.py` (the sanctioned `charter → doctrine` import direction), only the entry point moves. Retarget `charter.template_resolver.CharterTemplateResolver`'s one real caller (`specify_cli/runtime/resolver.py`'s tier-5 routing) onto the new factory methods, pinning the construction contract (the caller has a `missions_root`/cached `from_missions_root` shape today; the factory is built from `repo_root` — this WP resolves that mismatch, not tasks-time improvisation). **Corrected scope** (post-plan squad): `src/charter/resolution.py` and `src/charter/context_renderers/template_include.py` are NOT bypasses — both import only the `ResolutionResult`/`ResolutionTier` *types* (not resolution calls), sanctioned by an existing facade contract; retargeting a type import onto a factory method is a category error and is dropped from this FR. A real, previously-unenumerated third tier surface was found instead: `doctrine.template_catalog.resolve_template_by_id`, with 5 importers (`charter/template_catalog.py`, `specify_cli/runtime/resolver.py`, `charter/context.py`, `cli/commands/charter/list_cmd.py`, `charter/context_renderers/template_include.py`) — named as explicit deferred debt alongside `runtime/resolver.py`'s tier 1-4 reimplementation (R6), not folded into this FR's blast radius. | Draft |
| FR-004 | Promote `src/doctrine/missions/repository.py:98::MissionTemplateRepository.default_missions_root()` (already correctly `importlib.resources`-based) as the single shared missions-root authority, and retarget the other two hardcodes onto it: `src/charter/mission_type_profile_repository.py:66::builtin_missions_root()` (currently `Path(__file__).resolve().parents[1]/"doctrine"/"missions"`) and `src/specify_cli/runtime/home.py:107-108`'s hardcoded `dev_roots` fallback tuple. `builtin_missions_root()` was itself previously promoted as a shared authority (WP06/#2668, referenced at `charter/action_grain.py:203-204` and `charter/mission_type_profiles.py:646-647`) — this FR makes it a **thin delegate** to `default_missions_root()`, not a second co-equal authority; existing callers of `builtin_missions_root()` are unaffected. `home.py`'s import of the doctrine-layer `MissionTemplateRepository` is function-local, matching the file's own existing pattern at `home.py:49` (also function-local) — the mission does not introduce a new module-level `runtime → doctrine` edge; note this explicitly in the PR description as a residual risk that shares the exact blind spot `#2986` (deferred, C-003) would close, not a silently different shape. `home.py`'s `importlib.resources` lookup step (lines 97-104, preceding the `dev_roots` fallback) is a fourth resolution path for the same root and is explicitly OUT of this FR's scope — only the `dev_roots` tuple is retargeted. Ship an equality regression test proving both retargeted sites now resolve identically to `default_missions_root()`'s output. **Revised scope**: full convergence onto `doctrine.pack_paths.built_in_dir` is deferred to `#3091` (C-003) — `pack_paths` has no `missions/` content directory today; this FR closes the duplication, not the eventual packs-relocation. | Draft |
| FR-005 | Extend `charter.resolver.DoctrineService` (`src/charter/resolver.py:57-139`) to activation-gate the 6 mechanical currently-unfiltered kinds — `directive`, `tactic`, `styleguide`, `toolguide`, `mission_step_contract`, `glossary_pack` — replacing the `__getattr__` unfiltered passthrough (lines 136-139) for those kinds with the same three-state activation-aware filtering (`None`=catalog default / `frozenset()`=explicit empty opt-out / `{ids}`=filtered) already proven for the 3 existing gated kinds (`PackContext` already carries a matching `activated_<kind>` field for each; `doctrine.service.DoctrineService` already exposes a matching raw property — this is a mechanical copy of the existing pattern). Ship a bare-project regression test per newly-gated kind proving the default catalog is NOT silently emptied. | Draft |
| FR-006 | Add equivalent activation filtering for the `mission-type` token **entirely within `charter.mission_type_profiles.resolve_mission_type_context()`** — **not** in `charter.mission_type_profile_repository.MissionTypeProfileRepository`'s own file (post-tasks squad correction: that file is a different WP's exclusive ownership for an unrelated change; touching it here would create a real ownership overlap), and **not** in `charter.resolver.DoctrineService`, since `doctrine.service.DoctrineService` has no `mission_types` property and `PackContext.activated_mission_types` is not three-state (the catalog-default collapse already happens at `PackContext` construction). This is a structurally different, non-mechanical change from FR-005's 6 kinds; ship a bare-project regression test proving set-equality against `builtin_mission_type_id_set()` (not a fakeable subset check) when nothing is explicitly activated. | Draft |
| FR-007 | Ship non-vacuous architectural gate(s) (AST-walk or call-site-census style, self-mutation proven, per the WP10 idiom) for each of **five** closed bypass categories: the four original (FR-001/002/003/004) plus a fifth closing the `._inner` reach-around (below). Zero-tolerance baseline — no shrink-only allowlist, per the operator's "no exceptions" decision (C-002). **Post-plan squad corrections**: (a) the gate must resolve each `DoctrineService(` call site's **bound qualname** (via import resolution, not text matching) to distinguish `doctrine.service.DoctrineService` (forbidden) from `charter.resolver.DoctrineService` (the sanctioned wrapper, including its `pack_context=None` unfiltered-mode constructions) — a text-only grep cannot tell the two apart; (b) the two `.kittify/profiles` exclusions (FR-001) must be keyed by composite identity (file + qualname + line, mirroring `test_charter_path_literal_authority.py`'s allowlist shape), never a whole-file exclusion, so a genuinely new bypass added to the same file still reds; (c) every self-mutation proof must inject its violating construct at function-local or nested (`try`/`except`) scope specifically, matching the actual shape of the real violations found (R3) — a mutation that only tests module-level injection does not prove non-vacuity, per the exact lesson WP10 already learned. Extend `tests/architectural/test_org_activation_seam.py` and `tests/architectural/test_layer_rules.py` where their existing coverage is adjacent; do not re-assert what they already prove. | Draft |
| FR-008 | Unify the divergent "canonical" construction paths discovered during planning and the post-plan squad into one builder: `specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service`, `charter.doctrine_service_builder._build_activation_aware_doctrine_service`, and the inline "build raw, conditionally wrap" pattern repeated in `org_layer.py:244,275` and `generate.py:56` (FR-002) all collapse onto one function. Resolve the two named builders' discovered divergence by picking the *fuller* behaviour on each axis: `active_languages=infer_repo_languages(repo_root)` is always computed (the `charter` builder's behaviour) and `org_roots` is always self-resolved via `resolve_org_roots` (the `specify_cli` builder's behaviour) — never an arbitrary pick that silently drops either. **Sequencing note superseded** (post-tasks squad): the original plan staged this FR's proof across two separate work packages (a 3-kind proof, extended to 9 once FR-005 landed elsewhere). After the post-tasks squad merged FR-005's 6-kind work into the same work package as this FR, the regression test proves identical output across all 9 gated kinds in one unstaged pass — there is no cross-work-package sequencing constraint to observe. | Draft |
| FR-010 | Close the `._inner` attribute reach-around: `src/specify_cli/invocation/registry.py:64` and `src/specify_cli/invocation/org_profiles.py:117` both read `service._inner.agent_profiles` directly, bypassing every gate FR-001-008 add — an unguarded escape hatch that defeats the entire mission if left open (a genuinely gated 9-of-10 factory with a `._inner` side door is not a sole door). Both sites need the `agent_profile_repository` accessor named in FR-001, calling `get_provenance()` specifically (not `register_overlay()`, which `projection.py` needs, or `resolve_profile()`, which `runtime_bridge_io.py` needs) — use the same new public accessor rather than reaching past it a third and fourth time. | Draft |
| FR-011 | Record #2986, #3036, #3039, #3091, and #3022 as explicit deferred follow-ons, each with its one-line reason (different pair/violation-class/track), confirmed adjacent-but-separate by a pre-spec research squad. **Strengthened scope** (post-plan squad, Standing Order #8): PR-description prose alone is not durable — the precedent mission (`doctrine-charter-split-unification-01KZ0SRB`) already sets the bar by carrying `issue-matrix.json` rows with `verdict: "deferred-with-followup"` for two of these exact issues. This mission adds an `issue-matrix.json` row **and** an actual tracker comment naming this mission on each of the five issues before merge, so a later reader can discover the deferral by opening the issue itself, not only by reading this mission's PR. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Zero in-scope raw bypass call sites remain, provably, by *qualname*, not by text match. | A committed architectural test resolves each `AgentProfileRepository(`/`DoctrineService(` call site's bound import to its originating module and asserts zero matches for `doctrine.service.DoctrineService`/`agent_profiles.repository.AgentProfileRepository` outside `src/charter/resolver.py` and the one unified builder (FR-008) — explicitly NOT a text-only grep, since `charter.resolver.DoctrineService(inner, pack_context=None)` (FR-002's sanctioned unfiltered mode) and a forbidden raw `doctrine.service.DoctrineService(...)` share the literal substring `DoctrineService(` and a name-only gate cannot tell them apart. The two `.kittify/profiles` sites (`registry.py:48`, `profiles_cmd.py:83`, FR-001) are excluded by composite key (file+qualname+line), not by file. Zero `._inner` attribute accesses on a `charter.resolver.DoctrineService` instance outside `src/charter/**` (FR-010). | Draft |
| NFR-002 | No new lint/type regressions. | `ruff` + `mypy --strict` zero new issues on all changed modules; no new `# noqa` / `# type: ignore` / per-file ignore additions. | Draft |
| NFR-003 | Every new gate is non-vacuous. | Each gate shipped under FR-007 has a self-mutation test that reintroduces the exact closed bypass shape **at function-local or nested scope** (not module-level-only — matching the actual shape of the real violations, per R3) and asserts the gate fails naming the offending site — proven for all five categories (including the FR-010 `._inner` closure), not a sample. | Draft |
| NFR-004 | Behaviour change is explicit, not slipped. | CHANGELOG entry (per DIR-009) documents: (a) the factory now activation-gates all 10 kinds (previously 3) — a project that activates a subset of a newly-gated kind's packs will see a narrower result than before this mission; (b) the two `.kittify/profiles` sites are explicitly excluded, not silently missed; (c) FR-004's missions-root consolidation does not claim convergence with `doctrine.pack_paths.built_in_dir` — that remains `#3091`'s to deliver. All three named as intentional scope, not discovered later as gaps. | Draft |
| NFR-005 | No unmeasured performance regression on the sites the "boundary ratchet" comments were guarding. | p95 render latency for `spec-kitty agent tasks status` on a fixture project with 100+ work packages stays within 10% of the pre-mission baseline measured on the same fixture; if it regresses beyond that, the underlying cause named in FR-001 (e.g. eager construction cost) is fixed architecturally (caching, lazy init) rather than accepted. **Baseline capture is an explicit, scheduled step** (post-plan squad finding: "within 10% of baseline" is unfalsifiable if no one captures the baseline) — the 100+-WP fixture is built and its pre-mission p95 is measured and recorded (in the mission tracer file, per Standing Order #3) on the merge-base commit BEFORE any FR-001 site is migrated, not inferred after the fact. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **One canonical factory, extended — not a second one invented.** `charter.resolver.DoctrineService` is the single canonical factory every in-scope access path in this mission routes through, constructed by exactly one unified builder (FR-008). Reconcile / extend it (governing principle: single canonical authority); do not introduce a parallel wrapper, adapter, or second "activation-aware" factory. | Active |
| C-002 | **No shrink-only allowlist for in-scope sites; zero exceptions.** Per operator decision, every identified in-scope bypass site (FR-001-006, FR-010) must be eliminated outright. A site that cannot be resolved without a proven, unavoidable behaviour change (e.g. a genuine bootstrap/circularity case per the Edge Cases section) is a blocking finding surfaced to the operator during planning or implementation — never a silently added allowlist entry, and never grounds for skipping FR-007's zero-tolerance gate. This does not apply to the two `.kittify/profiles` sites (C-006) or the `_doctrine_collect.py` diagnostic sites' explicit unfiltered mode (FR-002) — both are named, reasoned exclusions from the *doctrine-asset* bypass count, not exceptions to it. | Active |
| C-003 | **Out of scope — confirmed adjacent-but-separate, stays deferred.** #2986 (runtime→doctrine import-ratchet's own function-local-import blind spot, 61 sites/30 files, different pair), #3036 (a doctrine-content-shippability gate contradiction, different domain), #3039 (a test-file reorganisation unrelated to access-path enforcement), #3091 (relocate `src/doctrine/missions/` to `packs/built-in`, packaging track), and #3022 (extract built-in packs into `spec-kitty-packs-open`, packaging/distribution track) are untouched by this mission's diff. The #3101 kernel→doctrine→charter wheel-cutover track (and its ADR, `docs/adr/3.x/2026-08-02-1-charter-wheel-assessment.md`) is likewise untouched. | Active |
| C-004 | **PRs only; operator merges; coord topology hygiene.** Every folded issue gets an issue-matrix row + tracker comment naming the mission; reviewer ≠ implementer; no direct push to `main`. | Active |
| C-005 | **Red-main discipline.** Classify any red test against the merge-base before treating it as pre-existing; never green-wash an honest red; file per DIR-013 if a pre-existing failure is newly encountered. | Active |
| C-006 | **`.kittify/profiles` is out of scope.** `registry.py:48` and `profiles_cmd.py:83`'s construction of `AgentProfileRepository` against `.kittify/profiles` (a local-override directory outside the doctrine activation model) is explicitly excluded per operator decision — that area is slated for separate future rework. Do not route it through the factory; do not fold its rework into this mission. | Active |

### Key Entities

- **`charter.resolver.DoctrineService`** (`src/charter/resolver.py:57-139`) — the canonical, activation-aware
  factory this mission makes the *sole* access path for doctrine assets; currently gates 3 of 10 kinds, gains
  6 more mechanically (FR-005) plus new resolution methods (FR-003) and an unfiltered-diagnostic mode (FR-002).
- **`doctrine.service.DoctrineService`** — the raw inner service; must never be constructed directly outside
  the factory and its one unified builder function (FR-008) after this mission.
- **`ArtifactKind`** (`src/doctrine/artifact_kinds.py:128-139`) — the 10-kind (9 charter-activatable kinds +
  `mission-type` token) universe; 9 are gated via `charter.resolver.DoctrineService`, `mission-type` is gated
  separately via `resolve_mission_type_context()` (FR-006).
- **`resolve_mission_type_context()`** (`src/charter/mission_type_profiles.py`) — the sole function the
  `mission-type` token's activation gating lands on, since it has no property on the raw `DoctrineService`
  and its own repository (`MissionTypeProfileRepository`, `src/charter/mission_type_profile_repository.py`)
  is a different WP's exclusive ownership for an unrelated change.
- **`AgentProfileRepository`** — the profile-loading repository; 5 of 7 originally-flagged direct
  construction sites eliminated; 2 (`.kittify/profiles`) explicitly excluded (C-006).
- **`doctrine.resolver` 5-tier axis** (`_resolve_asset`, `resolve_mission`) — the template/command resolution
  tiers (OVERRIDE, LEGACY, GLOBAL_MISSION, GLOBAL, PACKAGE_DEFAULT); stay in `doctrine/resolver.py`, reached
  only via new methods on the factory (FR-003).
- **`MissionTemplateRepository.default_missions_root()`** (`src/doctrine/missions/repository.py:98`) — the
  promoted single missions-root authority (FR-004); full convergence with `doctrine.pack_paths.built_in_dir`
  awaits the deferred `#3091`.
- **The five deferred issues** (#2986, #3036, #3039, #3091, #3022) — explicitly out of scope (C-003), each
  closed with an `issue-matrix.json` row and a tracker comment naming this mission (FR-011).
- **The `._inner` reach-around** (`registry.py:64`, `org_profiles.py:117`) — the escape hatch found by the
  post-plan squad that would have defeated every gate this mission ships if left open; closed by FR-010 via
  the same new lineage/mutation accessor FR-001 already needs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero unwrapped `doctrine.service.DoctrineService(...)` constructions (by resolved qualname, not
  text match — including the 3 additional sites found by the post-plan squad in `org_layer.py`/`generate.py`)
  and zero direct `AgentProfileRepository(...)` constructions remain anywhere in `src/` outside
  `charter.resolver.DoctrineService`, its one unified builder function, and the two explicitly-excluded
  `.kittify/profiles` sites (excluded by composite key, not by file) — gate-enforced, not a point-in-time
  grep.
- **SC-002**: The 5-tier template/command resolver axis and its `resolve_mission` duplicate are reachable
  only through new methods on the charter factory from outside `src/charter/**`. `charter/resolution.py` and
  `template_include.py`'s type-only imports are confirmed not bypasses (corrected post-plan) and are excluded
  from this criterion.
- **SC-003**: The three duplicate missions-root hardcodes consolidate onto one promoted authority
  (`MissionTemplateRepository.default_missions_root()`, with `builtin_missions_root()` now a thin delegate
  rather than a second co-equal authority), proven by an equality regression test; the PR description states
  that full convergence with `doctrine.pack_paths.built_in_dir` still awaits `#3091`.
- **SC-004**: `charter.resolver.DoctrineService` activation-gates all 9 charter-activatable `ArtifactKind`
  members (up from 3), and `resolve_mission_type_context()` separately activation-gates the `mission-type`
  token — real 10/10 coverage across two functions, not a mechanical 9/10 shortcut; a bare project with no
  activated packs sees a catalog **equal to** the raw unwrapped inner service's output for every kind
  (equality-proven, not merely "non-empty") and the mission-type set equals `builtin_mission_type_id_set()`.
- **SC-005**: A non-vacuous, self-mutation-proven (function-local/nested-scope injection, per NFR-003)
  architectural gate exists for each of the **five** bypass categories (including the FR-010 `._inner`
  closure), with a frozen zero-tolerance baseline that excludes the two `.kittify/profiles` sites and the
  `_doctrine_collect.py` unfiltered-mode sites by composite key, never by whole file.
- **SC-006**: #2986, #3036, #3039, #3091, and #3022 remain untouched by this mission's diff and each carries
  an `issue-matrix.json` row and a tracker comment naming this mission, confirmed still open at merge time.
- **SC-007** (sequencing superseded, post-tasks squad — see FR-008): The unified builder (covering the two
  named builder functions plus the `org_layer.py`/`generate.py` inline pattern) proves identical output
  across all 9 gated kinds in one unstaged pass, since FR-005's 6-kind work landed in the same work package
  (WP01) as the builder unification — there is no cross-work-package sequencing constraint to observe.
- **SC-008**: A pre-mission p95 latency baseline for `spec-kitty agent tasks status` on a 100+-WP fixture is
  captured and recorded before any FR-001 site is migrated (NFR-005) — not inferred retroactively.
