# Phase 0 Research: Charter as Sole Door: Close Bypass Access Paths

Three parallel research agents were dispatched against the spec's four bypass categories, reading full call
sites (not just the file:line anchors) and, where relevant, git history. Their findings produced four
planning-time corrections to the spec (each confirmed with the operator via `AskUserQuestion` before this
plan was written) plus a set of implementation-level design decisions that did not require operator input.

## Corrections requiring operator decision (resolved)

### D1 — FR-004's original acceptance criterion is unsatisfiable

- **Decision**: Promote `MissionTemplateRepository.default_missions_root()` (`src/doctrine/missions/
  repository.py:98`) as the single missions-root authority; retarget the other two hardcodes onto it. Defer
  the `doctrine.pack_paths.built_in_dir` convergence to `#3091`.
- **Rationale**: `doctrine.pack_paths.built_in_dir` resolves under `packs/built-in/<kind.plural>/`, which has
  no `missions/` subdirectory today — confirmed on disk (`packs/built-in/` contains `directives/ tactics/
  styleguides/ procedures/ paradigms/ agent_profiles/ glossary_packs/ toolguides/ assets/`, no `missions/`).
  `pack_paths.py`'s own docstring names `TEMPLATE`/`MISSION_STEP_CONTRACT`/`ANTI_PATTERN` as kinds with no
  built-in content dir, citing `#3091` (the missions→packs relocation, itself deferred by this mission's
  C-003) as the future work that adds one. `default_missions_root()` was found already correctly
  implemented — `importlib.resources`-based (wheel-safe), with a documented fallback — making it the better
  promotion target than inventing a new shared constant.
- **Alternatives considered**: Drop FR-004 entirely (rejected — operator wanted the duplication closed now,
  not deferred wholesale); retarget onto `pack_paths.built_in_dir` as originally specced (rejected — would
  require the deferred `#3091` relocation to exist first, making the acceptance criterion unsatisfiable).

### D2 — Two `AgentProfileRepository` sites are not doctrine-asset bypasses

- **Decision**: `src/specify_cli/invocation/registry.py:48` and `src/specify_cli/cli/commands/
  profiles_cmd.py:83` are excluded from FR-001's scope (C-006). Both construct `AgentProfileRepository`
  against `.kittify/profiles`, and both already separately call the canonical factory correctly for their
  doctrine-layer data.
- **Rationale (operator)**: "`.kittify` contains local overrides, this slice is to be reworked, do not route
  it." `.kittify/profiles` is a legitimate local-override mechanism outside the doctrine activation model by
  design, not a bug; it is scoped for its own future rework, separate from this mission.
- **Alternatives considered**: Widen the factory's conceptual scope to also cover `.kittify/profiles`
  (rejected by operator — risks conflating two deliberately-separate concerns, and the research found no
  existing factory affordance for that directory to extend from).

### D3 — A real C-001 violation surfaced as a byproduct: two divergent builders

- **Decision**: Fold in unifying `specify_cli.doctrine_service_factory.build_activation_aware_doctrine_
  service` and `charter.activation.doctrine_service_builder._build_activation_aware_doctrine_service` as new scope
  (FR-008), rather than deferring it as a separate issue.
- **Rationale**: The two functions are NOT behaviourally identical. The `charter` builder passes
  `active_languages=infer_repo_languages(repo_root)` into the inner `DoctrineService` construction; the
  `specify_cli` builder omits `active_languages` entirely. `active_languages` flows into every per-kind
  repository (`src/doctrine/service.py:72,82,92,111,148`) for language-scoped filtering, so the two builders
  can return **different catalogs for the same `repo_root`**. Separately, the `charter` builder requires an
  explicit `org_roots` argument (defaulting to `None` → no org layer) while the `specify_cli` builder always
  self-resolves org roots via `resolve_org_roots` — a caller of the `charter` variant who forgets `org_roots`
  silently loses the org layer. This directly undercuts the very "single canonical authority" claim this
  mission's C-001 makes, discovered while doing this mission's own work — domain-matched, unlike the five
  issues confirmed adjacent-but-separate pre-spec.
- **Alternatives considered**: File as a separate GitHub issue and leave the mission's original FR list
  unchanged (rejected by operator — the divergence is inside the exact factory this mission is making the
  sole door, so leaving it standing would ship a mission that claims C-001 while visibly violating it).

### D4 — `mission-type` does not fit the mechanical 9-kind pattern

- **Decision**: Gate the `mission-type` token via `charter.activation.mission_type_profile_repository.
  MissionTypeProfileRepository` / `charter.activation.mission_type_profiles.resolve_mission_type_context()` (FR-006),
  not via a new property on `charter.activation.resolver.DoctrineService`. Per operator decision, do the real work
  rather than narrowing the "all 10 kinds" claim to 9.
- **Rationale**: `PackContext.activated_mission_types` (`src/charter/activation/pack_context.py:120`) is a plain
  `frozenset[str]`, never `None` — `_read_activated_mission_types` (`pack_context.py:601-619`) already
  collapses "key absent" to `builtin_mission_type_id_set()` at construction time, so the three-state
  semantics (`None`/`frozenset()`/`{ids}`) the other 6 kinds use don't apply here; the default is baked in
  before any resolver sees it. Separately, `src/doctrine/service.py` has no `mission_types` property at all
  (confirmed by grepping every `@property` on the raw service: directives, tactics, styleguides, toolguides,
  paradigms, procedures, mission_step_contracts, glossary_packs, assets, agent_profiles — no mission-type
  entry) — mission-type resolution has always lived entirely outside `DoctrineService`, in a separate
  repository. There is nothing for `charter.activation.resolver.DoctrineService.__getattr__` to even unfilteredly
  forward for this token the way it does for the other 7 — the "ungated passthrough" framing doesn't fit.
- **Alternatives considered**: Narrow to 9/10 real `ArtifactKind` gating, name `mission-type` as an explicit
  carve-out matching how `TEMPLATE`/`ASSET`/`ANTI_PATTERN` are already carved out via
  `_NON_AUGMENTATION_ELIGIBLE_KINDS` (rejected by operator — "extend to `MissionTypeProfileRepository` too,
  your original intent").

## Design decisions resolved without operator input

### R1 — `_resolve_directives_selection` clarifies, does not contradict, the "3 of 10 gated" premise

`charter/resolver.py::_resolve_directives_selection` (lines 233-298) already implements the exact
three-state semantics for `directive` and reads `PackContext.activated_directives` directly — but it is
private, used only inside the separate `resolve_project_governance()` function, and is **not** wired to
`charter.activation.resolver.DoctrineService`'s properties (which are exactly `paradigms`, `procedures`,
`agent_profiles` — confirmed by grepping `@property` in the file). It is the fallback-source *exemplar* to
copy the three-state logic from for FR-005's 6 mechanical kinds, not evidence that `directive` gating
already exists on the factory. The spec's "3 of 10 gated" premise stands correctly.

### R2 — FR-005's 6 mechanical kinds require zero `PackContext` schema changes

`PackContext` (`src/charter/activation/pack_context.py:100-259`) already carries a three-state `activated_<kind>` field
for every one of `directive` (144), `tactic` (152), `styleguide` (155), `toolguide` (158),
`mission_step_contract` (170), `glossary_pack` (173) — each populated via a dedicated `_read_activated_*`
reader (lines 622-676), structurally identical to the readers already wired for `paradigms`/`procedures`/
`agent_profiles`. `src/doctrine/service.py` confirms matching raw properties for all 6: `directives` (57),
`tactics` (66), `styleguides` (76), `toolguides` (86), `mission_step_contracts` (115), `glossary_packs`
(124). Extending `resolver.py` for these 6 is copy-paste of the existing property pattern — no new
`PackContext` field, no new raw-service property, no activation-engine change.

### R3 — The "boundary ratchet" comment is a red herring for this migration

`git log -p -S 'boundary ratchet'` traces the `tasks_status_cmd.py:712,823` comments to commit `873832aa1`.
The stated fear — a direct doctrine import tripping the boundary ratchet — is checked by
`tests/architectural/test_runtime_charter_doctrine_boundary.py`, which only scans **module-level**
`from doctrine.*` imports (lines 98-102 of that test explicitly exclude lazy/function-local imports). Both
the existing `AgentProfileRepository` import and the factory's internal `DoctrineService` import are
function-local at these sites, so routing through the factory does **not** trip this gate — the comment's
named concern does not reappear. The real, previously-unmeasured risk is construction cost (the factory adds
`PackContext.from_config` + `resolve_org_roots` + a wrapper vs. today's bare `AgentProfileRepository()`),
covered by NFR-005's latency measurement, not an architectural blocker.

### R4 — `_doctrine_collect.py`'s 4 diagnostic sites need the factory's *unfiltered* mode, not the filtered path

`_collect_profile_health`, `_collect_glossary_pack_health`, `_collect_doctrine_collisions`, and
`_build_selection_block` all deliberately need the unfiltered, all-layer view — activation-aware filtering
would silently narrow doctor/health output for deactivated packs, which is exactly the anti-pattern the
spec's Acceptance Scenario 2 (User Story 1) warns against. Fix: wrap with
`charter.activation.resolver.DoctrineService(inner, pack_context=None)` — same class, explicit unfiltered construction,
satisfying C-001 (one factory) without regressing diagnostic completeness.

### R5 — `projection.py:84` and `runtime_bridge_io.py:576` need capabilities the filtered wrapper doesn't expose

`projection.py:84` (`default_profile_repository`) needs `register_overlay()` (mutation) and `get_ancestors()`
(lineage) — neither exists on the filtered dict `charter.activation.resolver.DoctrineService.agent_profiles` returns.
`runtime_bridge_io.py:576` needs `repo.resolve_profile(profile_id)` (lineage composition), also absent from
the filtered dict. Both currently reach around the gate via `svc._inner.agent_profiles` (already used at
`registry.py:64`) — a private-attribute reach-around that works but isn't a real public contract. **Design
decision**: add one new public accessor to `charter.activation.resolver.DoctrineService` for "the mutable/lineage-
capable repository, still activation-aware for read paths" before migrating these two call sites, so the
mission doesn't trade one reach-around for a proliferation of `_inner` accesses at every migrated site.

### R6 — FR-003's tier functions stay in `doctrine/resolver.py`; only the entry point moves

`doctrine/resolver.py::_resolve_asset`/`resolve_mission` are pure filesystem-tier functions, unrelated to the
`DoctrineService` object the factory wraps. An existing correct precedent already solves this exact shape:
`src/specify_cli/runtime/resolver.py` reimplements tiers 1-4 itself (pure `.kittify`/`~/.kittify` filesystem
checks) and routes only tier 5 (package-default) through `charter.activation.template_resolver.CharterTemplateResolver`
— its own comment states the intent: *"Keep this call routed through charter so runtime never binds directly
to doctrine's repository shape."* (Landed under `charter-mediated-doctrine-selection-01KRTZCA`, WP07.)
**Design decision**: add resolution methods to `charter.activation.resolver.DoctrineService` that internally call
`doctrine.resolver.resolve_command`/`resolve_template`/`resolve_mission` (legal — `charter → doctrine` is the
sanctioned direction); `CharterTemplateResolver` becomes a thin delegating shim or is retired in favour of
direct factory use by its one real caller. Two additional in-scope importers were found during this research
and folded into FR-003: `src/charter/resolution.py` (facade re-export) and `src/charter/context_renderers/
template_include.py` (lazy `ResolutionTier` import) — both already inside `src/charter/**` but still
bypassing the new factory methods.

**Explicitly out of scope, noted as debt**: `specify_cli/runtime/resolver.py`'s own tier-1-4
reimplementation is a second, parallel filesystem-tier implementation (not a `doctrine.resolver` import, so
not a literal bypass) with already-observed semantic drift from `doctrine/resolver.py` (different exception
handling: catches only `FileNotFoundError` vs. `doctrine.resolver`'s `(FileNotFoundError, ImportError)`).
Flagged for a future mission; not folded in here (would expand IC-02's blast radius well beyond the named
FR-003 anchor).

## Post-Tasks Squad Findings

A second 4-lens adversarial squad (reviewer-renata, debugger-debbie, paula-patterns, python-pedro) reviewed
the 10 generated WP prompts before locking `finalize-tasks`. All four returned READY WITH FIXES or NOT
READY pending fixes; every finding below was folded into the WP prompts and `tasks.md` (this section
records what was found, not a duplicate of the WP text):

| Finding | Lens | Severity | Folded into |
|---|---|---|---|
| WP02/WP03/WP04's `dependencies: []` frontmatter never declared WP01, despite prose saying so everywhere — found INDEPENDENTLY by 3 of 4 delegates | reviewer-renata, paula-patterns, python-pedro | CRITICAL | WP02/03/04 frontmatter fixed |
| WP01 (accessor) and former WP07 (6 properties) both edited `src/charter/activation/resolver.py`; the 3-way split (with WP05) forced an awkward, benefit-free serialization | paula-patterns | HIGH | WP01+WP07 merged |
| Gate 5 (`._inner`) and Gate 4 (hardcoded paths) each only ever guarded one WP's own surface; a separate WP for them added dependency edges for no benefit | paula-patterns | HIGH | Gate 5 → WP04, Gate 4 → WP06 |
| Accessor method name never pinned ("e.g. `agent_profile_repository`") — three dependent WPs could each invent something different | reviewer-renata, python-pedro | CRITICAL (compounding) | Pinned exact name in WP01 |
| Accessor method-list wrong: `get_ancestors()` unused; `projection.py` needs only `register_overlay()`; `registry.py`/`org_profiles.py` need `get_provenance()`, named nowhere | debugger-debbie | MEDIUM | Corrected in WP01/WP02/WP04 |
| `_doctrine_collect.py` line citations drifted +2 (193/283/420/828, not 191/281/418/826) after a later commit inserted 2 lines | debugger-debbie | MEDIUM | Corrected in WP03/WP09 |
| WP05's core premise was false: `specify_cli/runtime/resolver.py` never imported `doctrine.resolver` — it imports the `charter.resolution` facade and `charter.activation.template_resolver`, both already inside `src/charter/**` | debugger-debbie | HIGH | WP05 reframed as entry-point consolidation, not bypass removal |
| WP05's suggested new method names collided with `CharterTemplateResolver`'s existing `resolve_command_template`/`resolve_content_template` (different signatures) | debugger-debbie | LOW | WP05 requires distinct names |
| Gate 3 (`doctrine.resolver` import) is already green today — proves nothing about a WP05 closure, since no such violation existed outside `src/charter/**` | debugger-debbie | HIGH | WP09 T039 reframed as forward-looking guard only |
| Gate 5's naive `._inner`-anywhere scan would false-positive on unrelated `._inner` attributes in `auth/transport.py`/`events/decision_log.py` | debugger-debbie | HIGH | WP04's gate scoped to doctrine-service-typed receivers |
| `resolver.py:402-413` cited as lineage-traversal precedent is actually an `isinstance(dict)` compat fallback — weak/wrong precedent | debugger-debbie | MEDIUM | Softened in WP01/WP02 |
| WP07's "remove from `__getattr__` passthrough" step was wrong — `__getattr__` is a generic catch-all a new `@property` shadows automatically; nothing to edit | debugger-debbie | MEDIUM | Step removed from WP01 |
| `profile_resolution.py:81`'s `_default_agent_profile_repository()` is a zero-arg module-level cache with no `repo_root` — WP02's original T010 ("replace with the gated property") was a type mismatch, not implementable | reviewer-renata | HIGH | WP02 T010 reframed as confirm-and-document, not migrate |
| NFR-005's perf DoD (a single committed p95 constant) is author-written and unfalsifiable; cross-machine comparison invalid | reviewer-renata | MEDIUM | WP02 requires raw timing series, same session |
| FR-007's composite-key exclusions and function-local self-mutation requirement were correctly specified, but WP10's "post a GitHub comment" DoD had no non-fakeable evidence requirement | reviewer-renata | MEDIUM | WP10 requires pasted `gh issue view --comments` output |
| A post-tasks sweep for additional missions-root hardcodes found 3 more root-relative constructions (`kernel/paths.py`, `template/manager.py`, `list_cmd.py`) beyond WP06's 2 named sites | reviewer-renata | LOW | Named as an explicit, untouched residual in WP06 (citations not independently re-verified) |

**Not folded in** (explicitly deferred to implementation-time judgment, per the squad's own concession that
these are appropriately WP-time decisions): the exact chosen names for WP05's new factory methods beyond
"must not collide"; whether `CharterTemplateResolver` becomes a thin shim or is retired outright (WP05's
T020 leaves this as an implementer choice, justified in the Activity Log).

## Post-Plan Squad Findings

A 4-lens adversarial squad (architect-alphonso, reviewer-renata, debugger-debbie, planner-priti — each
profile-loaded, each independently reading spec.md/plan.md/research.md and, for the highest-stakes claims,
the actual code and git history) reviewed the plan before `/spec-kitty.tasks`. All four returned **READY
WITH FIXES**; every HIGH-severity finding was independently verified and folded into spec.md/plan.md/
data-model.md/contracts/quickstart.md (this section records what was found and where it landed):

| Finding | Lens | Verified how | Folded into |
|---|---|---|---|
| 3 more raw `DoctrineService(...)` sites (`org_layer.py:244,275`, `generate.py:56`), one with a fail-open `except ImportError: pass` bug | debugger-debbie | Read the actual files | FR-002, FR-008 |
| `._inner.agent_profiles` reach-around at `registry.py:64` and `org_profiles.py:117` defeats every gate | reviewer-renata | Read the actual files | FR-010 (new), NFR-001 |
| NFR-001's text-grep gate can't distinguish the sanctioned `pack_context=None` wrapper from the forbidden raw class (both contain the substring `DoctrineService(`) | reviewer-renata | Read spec.md's own FR-002 vs NFR-001 side by side | NFR-001 (qualname resolution, not text match) |
| IC-01 (builder unification, FR-008) scheduled before IC-04 (FR-005's 6 new properties) means FR-008's "assert identical output across all 9 properties" can't be written yet | architect-alphonso | Read plan.md's IC-01/IC-04 dependency chain | FR-008, plan.md IC-01 (scoped to 3 kinds now, extended at IC-04) |
| `charter/resolution.py` and `template_include.py` are type-only imports, not resolution-call bypasses; a real third tier surface (`doctrine.template_catalog`, 5 importers) was missed | architect-alphonso | Read both files' actual import statements and usage | FR-003 (corrected), plan.md IC-02 |
| `runtime/home.py`'s retarget onto `MissionTemplateRepository` (doctrine-layer) creates the same runtime→doctrine boundary tension `#2986` already tracks | architect-alphonso | Read `test_runtime_charter_doctrine_boundary.py`'s scan scope + `home.py`'s existing import shape | FR-004 (named as an explicit residual risk, not silently different) |
| `builtin_missions_root()` was already a promoted authority (WP06/#2668) — FR-004 needed to make it a delegate, not a second authority | architect-alphonso | Found the prior-promotion comments in `action_grain.py`/`mission_type_profiles.py` | FR-004 |
| R5's lineage/mutation accessor left two semantic questions (mutation-leak-through-filter; lineage-crosses-deactivated-parent) unanswered | architect-alphonso | Read `resolver.py:402-413`'s existing precedent | `contracts/charter-doctrine-service-contract.md` (pinned) |
| Bare-project / mission-type regression assertions were existence/subset checks, fakeable by a partial leak | reviewer-renata | Read the contract files' assertion language | `contracts/*.md`, `data-model.md` (equality/set-equality required) |
| Self-mutation proofs unconstrained to function-local scope would repeat R3's exact vacuity lesson | reviewer-renata | Cross-checked against R3's own finding | FR-007, NFR-003 |
| FR-007's "excluding by name" had no defined shape; quickstart used whole-file `grep -v` | reviewer-renata | Read quickstart.md's actual commands | FR-007 (composite-key requirement), quickstart.md |
| NFR-005's baseline is never scheduled to be captured — "within 10%" is unfalsifiable without one | reviewer-renata + architect-alphonso (convergent) | Read plan.md's IC schedule for a baseline step (none existed) | NFR-005, plan.md IC-00 (new) |
| quickstart.md's own verification commands already produce false positives today (before any change lands) | debugger-debbie | Ran the commands | quickstart.md |
| FR-009 (deferred issues) only committed to PR-description prose; precedent mission already carries `issue-matrix.json` rows for 2 of these exact issues | planner-priti | Read the precedent mission's actual `issue-matrix.json` | FR-011 (renumbered, strengthened) |

**Not folded in** (explicitly deferred to tasks-phase WP acceptance criteria, per reviewer-renata's own
concession that these are appropriately WP-time decisions, not plan-blocking): the exact method names for
FR-003's new factory methods; the exact test file names throughout (left as "assigned at tasks time" in
quickstart.md); architect-alphonso's MEDIUM finding on whether `mission-type`'s separate-repository gating
constitutes a "two doors" seam worth a wording amendment to SC-004 rather than a design change — SC-004
already states "real 10/10 coverage across two repositories, not a mechanical 9/10 shortcut," which the
squad's own alternative resolution (amend the wording rather than redesign) is satisfied by.

### R7 — `profile_resolution.py:81`'s `repo_root is None` branch is a genuine bootstrap case

The module's `repo_root is None` branch is the process-wide cached built-in-only fast path used when there is
no repo context to build a factory instance from — the bootstrap/circularity case the spec's Edge Cases
section already anticipated. It is not a site this mission routes through the factory; it is the legitimate
absence-of-context case C-002 already carves out by design (surfaced, not silently allowlisted).
