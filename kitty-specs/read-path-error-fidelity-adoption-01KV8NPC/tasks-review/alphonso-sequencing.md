# Adversarial Post-Tasks Review — Sequencing / Ownership / Build-Breaker Ordering

**Reviewer:** architect-alphonso (profile-loaded — DIR-001 one-owning-module, DIR-003 decision-documented,
DIR-031 bounded-context translation)
**Date:** 2026-06-16
**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**Lens:** sequencing + ownership + build-breaker ordering + architectural soundness
**Artifacts read:** `tasks.md`, `plan.md`, `lanes.json`, all 9 `tasks/WP0*.md`,
`research/investigation-3-readwrite/{alphonso-symmetry-design.md, pedro-factory-feasibility.md}`,
plus direct code reading of `resolution.py:685-815`, `context.py`, `workspace/context.py:448-456`,
`context/{resolver.py,mission_resolver.py}`, `orchestrator_api/commands.py:255-270/484/787`,
`decision.py:410-430`, `mission_runtime/__init__.py`.

---

## VERDICT (tight)

- **Build-breaker (F-1 class)? NONE.** The freeze is structurally safe. There is exactly **one**
  production `ExecutionContext(` constructor (`resolution.py:739`) and exactly **one** post-construction
  mutator block (`:800-808`, plus the `:813` `commands["workflow"]=` dict-write) — **all inside WP01's
  own file**. No out-of-scope consumer and none of WP02/03/04/05/09 mutate a built `ExecutionContext`.
  The naming-rider F-1 (a freeze/rename stranding an unconverted consumer) **does not recur here**: the
  glossary `context.<field> =` writes are a different type, and `workspace/context.py:452`'s
  `context.branch_name ==` is a *read* over persisted `MissionContext` objects, not the frozen
  `ExecutionContext`. Verified by grep + type-tracing.
- **Ownership collision? NONE.** Programmatic check: zero `owned_files` entry appears in two WPs. The
  `agent/mission.py` (WP03) vs `agent/workflow.py` (WP05) surfaces are cleanly disjoint. No dependent is
  forced to edit `resolution.py`/`context.py` (WP01's files) to *consume* the factory — they import
  `resolve_action_context`/`ActionContextError` (a read API) and were doing so already.
- **WP01-first sequencing SUFFICIENT? YES, for the freeze/invariant precondition.** The freeze is
  contained to WP01's file; WP02-05/WP09 consume a read API that does not change shape. **But the
  *stated rationale* for two of the dependencies (WP09, and the D-6 framing in WP03/WP05) is partly
  fictional** — see SHOULD-FIX [S1]. The dependency edges are not *wrong* (ordering is still correct and
  harmless), but WP09's "consume the WP01 factory identity boundary" instruction points at an API WP01
  does not ship.

No BLOCKERs. Two SHOULD-FIX, three NITs.

---

## BLOCKER

*(none)*

---

## SHOULD-FIX

### [S1] WP09 (and WP03/WP05 D-6 framing) depend on a "factory identity boundary" that WP01 does not ship as a callable API — the dependency is real for ordering but the *instruction* is unactionable as written

**Where:** `WP09` T042 + DoD ("feed identity through the **WP01 factory boundary** (D-6)"); echoed in
`WP03`/`WP04`/`WP05` risk-notes ("Consume WP01's frozen context; never re-derive `mid8`/`mission_id`").

**Finding.** WP01's actual deliverable (per `pedro-factory-feasibility.md §1.4/§4.2` and WP01 T037) is:
(a) a **package-private** `build_execution_context`, (b) a frozen composite, (c) the invariant, and
(d) a **docstring** boundary contract. Pedro is explicit: **"No public factory symbol… do NOT add it to
`mission_runtime.__all__`."** Alphonso's symmetry doc proposes an *optional* `resolve_identity_only`
projection but flags it as "either/or" and ~15-25 LOC of *surface declaration*. **WP01's subtasks do not
create any identity projection** — T037 is docstring-only.

I verified the existing surface: `mission_runtime.__all__` exposes `resolve_placement_only`, which
returns a **`CommitTarget`** — it carries no `IdentityFragment`/`mid8`. There is **no importable door
that hands a write-side caller the resolved `mid8`**. So when WP09 implements M3, it cannot "feed
identity through the factory boundary"; it will (correctly, and exactly like the reference it cites)
do what `decision.py:421` does: `load_meta()` → real `mission_id` → `resolve_mid8(slug, mission_id=...)`
— a **grammar-primitive call**, not factory consumption. That is functionally fine (it fixes M3), but
the WP09 prompt frames it as adopting a WP01 API that will not exist.

**Why it matters (architectural soundness, not just wording):** the implementer of WP09 will either
(i) waste a cycle hunting for a non-existent `resolve_identity_only`, or (ii) widen WP01's scope mid-flight
to add a public projection — which would violate pedro's "no public symbol" / ADR-06-07-1 lean-API line
and is *outside WP09's owned files* (WP09 cannot add it to `resolution.py`). Either path is friction the
prompt should pre-empt.

**Fix (choose one, record in plan + WP09):**
- **(preferred, lowest-scope)** Re-word WP09 T042 + DoD to the *real* contract: "resolve the real
  `mission_id` from primary meta (the `decision.py:421`/`context.py:73` pattern) and pass it to
  `resolve_mid8(mission_slug, mission_id=<real>)` so the empty-mid8 seed is gone and the
  `bool(mid8)` fail-closed guard fires. This **honors** the WP01 boundary contract (no independent
  re-derivation of identity from a *guessed* `mission_id=None`) without importing a projection API."
  Then **WP09's WP01 dependency becomes a doc/contract dependency, not a code dependency** — and can
  arguably be relaxed to *no hard dep* (see [S2]).
- **(alternative, wider)** Expand WP01 T037 to actually export `resolve_identity_only(repo_root,
  mission_slug) -> IdentityFragment` and add it to `__all__`. This makes the "factory boundary"
  literally callable and lets WP09/WP03/WP05 consume it. **Cost:** widens the public API (fights
  pedro's recommendation + ADR-06-07-1), adds LOC to WP01. Only take this if the operator wants the
  write-side follow-on (#1716/#1878) to import a concrete door rather than re-reading meta.

The plan's D-6 already concedes the contract is "declare the boundary," not "ship the projection"
(plan line 66-68 says *contract*, and pedro caps it at a docstring). The WP prompts over-promise a
callable. Align them to the docstring reality.

### [S2] WP09's WP01 dependency is the weakest edge — once [S1] is applied it is a *contract* dependency, and the M2 half has no WP01 dependency at all

**Where:** `lanes.json` lane-i `depends_on_lanes: ["lane-a"]`; `WP09 dependencies: [WP01]`.

**Finding.** WP09 bundles **M2** (typed-error pass-through across 8 endpoints — purely "stop catching
`StatusReadPathNotFound`, surface the code"; touches `commands.py:263-266` + 8 sites; **no
ExecutionContext, no identity**) and **M3** (empty-mid8 fail-closed; reads meta + `resolve_mid8`). 
- **M2 has zero coupling to WP01** — it is the same shape as WP02's pass-through but on a different owned
  file. It does not consume `ExecutionContext` at all.
- **M3**, per [S1], does not consume a WP01 *code* surface either; it follows the `decision.py:421`
  primitive pattern. Its only tie to WP01 is the *contract* "don't seed `mission_id=None`."

So the WP09→WP01 hard edge is **conservative, not required**. It is not *wrong* (WP01 is cheap and lands
first regardless), and keeping it preserves the "one frozen seam first" narrative — but the prompt should
stop telling the implementer M3 *consumes* a WP01 API. If parallelism mattered, WP09 could start
alongside WP01. **Recommendation:** keep the edge (harmless, and it keeps the contract-adoption story
coherent), but fix the framing per [S1]. Do **not** add new edges.

Contrast: WP02/WP03/WP04/WP05 genuinely call `resolve_action_context` and benefit from the frozen,
invariant-checked context (a malformed context would surface as a different error pre-freeze). Their
WP01 dependency is **correctly justified**. WP06/WP07/WP08 are correctly **independent** (paths.py root
resolver, charter status collector, and a test-only merge regression — none touch the context factory).
Those edges are right.

---

## NITs

### [N1] `plan.md` IC-02 cites `context/mission_resolver.py:164` for M1; the bug is actually in `context/resolver.py:164` — the WP02 prompt is correct, the plan prose is stale

**Where:** `plan.md` IC-02 ("M1 `src/specify_cli/context/mission_resolver.py:164`") + D-7.

**Finding.** **Both** `context/resolver.py` and `context/mission_resolver.py` exist. I traced the live
flatten (`except ActionContextError: raise FeatureNotFoundError("…Check that the mission slug is
correct.")`) to **`resolver.py:164`**, inside `resolve_context()` — confirmed by `sed`. `mission_resolver.py`
has **no** such flatten (grep returns nothing). WP02's `owned_files`, `lanes.json` write_scope, and the
T038 *body* all correctly name **`resolver.py`**. Only the **plan IC-02/D-7 prose** says
`mission_resolver.py`. This is a documentation drift, not a build issue — WP02 will edit the right file.
Fix the plan citation so a future reader/reviewer is not sent to the wrong module.

(Sub-note: `resolve_context` at `resolver.py:117` is the persisted-`MissionContext` builder reached via
`agent context resolve` → `resolve_mission_handle` → … → `resolve_context`; the M1 fidelity fix lands
there, correctly.)

### [N2] WP01 must also fold the `commands["workflow"]=` dict write (`resolution.py:813`) into construction, not just the `:800-808` block — the prompt only names `:800-808`

**Where:** WP01 T005 + DoD ("the `:800-808` post-build mutator is deleted").

**Finding.** Freezing forbids *attribute reassignment*, not in-place dict mutation, so
`context.commands["workflow"] = command` (`:813`) would **not** raise on a frozen dataclass and the
suite could stay green with it left in place — but it is the same anti-pattern (mutating a "built"
context) and leaving it half-done undercuts the "single construction door / function-over-form" claim.
WP01's T005/DoD only call out `:800-808`. Add `:813` (the implement-action `commands["workflow"]`
write) to the fold-into-construction scope so the verification-by-deletion is complete. Pedro's analysis
implicitly covers "construct once with all fields"; make it explicit in the prompt. Pure WP01-internal,
no cross-WP impact.

### [N3] `pedro-factory-feasibility.md §1` mis-attributes `workspace/context.py:452` as an ExecutionContext reference; it is a `MissionContext` read — conclusion (frozen-safe) is right, the citation is wrong

**Where:** pedro doc §1.1/§3 ("the single external touch, `workspace/context.py:452`, is a **read**").

**Finding.** Correct that it is a read and frozen-safe; but it iterates `list_contexts(repo_root)`, which
returns persisted **`MissionContext`** objects (from `context/resolver.py`/`store.py`), **not**
`mission_runtime.ExecutionContext`. So it is not even a touch of the frozen type — the blast-radius is
*even smaller* than pedro stated. No action needed for the WP (the freeze is safe either way); flagging
only so a reviewer does not "verify" a false ExecutionContext linkage and get confused. Already
double-checked: no `append/extend/pop` on `context.dependencies/commands/warnings` anywhere in `src/`,
so frozen-with-mutable-contents has no latent in-place mutator.

---

## Cross-cutting architectural confirmation (the things that ARE sound)

- **Factory blast radius is genuinely WP01-local (pedro §3 confirmed).** "Freeze + funnel through
  `build_execution_context`" is achievable inside `mission_runtime/{context,resolution}.py` only. The
  fragment sub-objects are *already* `@dataclass(frozen=True)`; only the top-level `ExecutionContext`
  (`context.py:184`) is mutable. Folding `:800-808` (+`:813`, [N2]) into the one constructor at `:739`
  is the whole job. No leak into consumers. WP01 is truly independent.
- **Ownership is the strongest dimension of this plan** — zero overlap, god-modules (`mission.py` 3942
  LOC, `workflow.py` 2737) each owned by exactly one WP, the shared `_find_feature_directory` correctly
  fenced off in WP03 (auto-select goes in `setup_plan`, not the shared helper — DIR-001 honored).
- **The "second authority" deletions (WP02/04/05/09) are bounded-context translations, not new
  resolvers (DIR-031)** — verified the flatten/escape-walk/empty-seed sites are all consumer-side and
  each lives in a single owned file.
- **WP08 is correctly test-only and correctly independent** — owns one test file, imports merge helpers
  read-only, no `src/` edit. The falsification-guard requirement is the right live-evidence anchor.
- **WP09's legacy-grammar guard (`:484`/`:787` untouched) is precisely scoped** — I verified those two
  sites are the legacy `{slug}-{lane}` grammar, distinct from the `:261` status-read seed. The prompt's
  "diff must show only `:261`" reviewer instruction is correct and important.

---

## Recommended edits (minimal, ordered)

1. **[S1]** Re-word WP09 T042/DoD (and the D-6 risk-line echoes in WP03/WP04/WP05) so "factory identity
   boundary" means *the docstring contract* (resolve real `mission_id` from meta, pass to `resolve_mid8`),
   not an importable projection. Pick the preferred low-scope option unless the operator wants WP01 to
   export `resolve_identity_only` ([S1] alternative).
2. **[N2]** Add `resolution.py:813` (`commands["workflow"]=`) to WP01's fold-into-construction scope.
3. **[N1]** Fix the `plan.md` IC-02/D-7 citation `mission_resolver.py:164` → `resolver.py:164`.
4. **[S2]/[N3]** Optional clarity only: note in lanes/plan that WP09's WP01 edge is a contract (not code)
   dependency, and correct pedro's `workspace/context.py:452` attribution. No edge changes.

**Net:** the WP01-first sequencing and the disjoint ownership are sound and ship-ready. No build-breaker,
no collision. The one substantive risk is a **framing mismatch** (WP09 promises a WP01 API that the
agreed WP01 scope deliberately does not build) — fixable with prompt wording, no re-decomposition needed.
