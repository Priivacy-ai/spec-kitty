# Post-spec adversarial squad — convergent findings (2026-07-30)

Point-cut: post-`/spec-kitty.specify`. Four profile-loaded read-only lenses:
reviewer-renata (anti-laziness), architect-alphonso (seams/layering),
paula-patterns (brownfield/duplicate-authority), planner-priti (scope/sequencing).
All claims below were **re-verified against code** by the orchestrator before folding.

## Load-bearing convergent findings (folded into spec.md)

1. **WS2/#3064 seam was wrong.** The "all built-ins" fallback is **not** in
   `invocation/registry.py`; it is the shared three-state activation gate in
   `charter/resolver.py` (via `doctrine_service_factory.py`), consumed by **both**
   routing (`ProfileRegistry`) and governance context (`build_charter_context`).
   → Fix is a **new routing-seam pre-check** keyed on `charter_activated_urns()`
   (`pack_context.py:496`, returns ∅ when empty, excludes always-on software-dev),
   **not** a mutation of the shared gate. Routing and governance-context must **agree**
   (no doctrine in either) — the R3 parity invariant is re-baselined, not deleted.
   [renata HIGH, alphonso HIGH, paula HIGH]

2. **generic-agent coherence gap.** `generic-agent` is itself a shipped built-in
   doctrine profile (`src/doctrine/agent_profiles/built-in/generic-agent.agent.yaml`).
   → Model it as a routing-layer **synthetic/constant target** (outside catalog
   admission) so "no doctrine admitted" stays literally true; amend C-003. [alphonso HIGH]

3. **WS3/#2532 was fakeable end-to-end.** `context.py` **already** declares `__all__`
   (L79) and has **zero** `specify_cli` imports → layer-rule/`__all__`/dead-symbol gates
   and NFR-001 byte-parity are all green on the untouched monolith. Only "thin"
   (unmeasurable) signalled completion. → Bind completion to a **residual-LOC ceiling** +
   **each seam is a real sibling module imported from its own home** (not re-exported
   through context.py). [renata BLOCKER, priti MAJOR]

4. **Decomposition is CONSOLIDATION, not greenfield.** `context_renderers/` already holds
   7 extracted modules incl. `token_budget.py` and `section_bodies.py` — two seams FR-008
   listed to "extract". → Continue the existing package convention; consolidate into
   existing homes; pin the 4 lazy-cycle symbols (`_render_fetch_stanza`, `_budget_estimate`,
   `_diagnose_catalog_miss`, `_PROFILE_INLINE_BODY_LIMIT_CHARS`) to **leaf** modules so the
   `profile_sections` import cycle **dissolves** (not relocates). [alphonso MEDIUM, paula MEDIUM]

5. **FR-009 undercounted the preserved surface.** `_reset_agent_profile_cache` is imported
   from `charter.context` by 4 test files → keep a re-export shim or move import sites with
   the seam. [alphonso HIGH]

6. **Real cross-WP collision is US1∩US3, not US2∩US3.** US2's fetch fix lands in the
   already-extracted `fetch_stanza.py` (US3 doesn't touch context_renderers/). The material
   collision: US1 changes `build_charter_context` output for empty-charter input (breaking
   US3's parity baseline) and mutates the activation-wrapper region (~context.py:1550-1566)
   US3 relocates. → **Required order: US2+US1 land first; US3 parity baseline captured after;
   US3 last against a frozen wrapper seam.** P1→P2→P3 is load-bearing. [priti MAJOR, paula MEDIUM]

7. **FR-006 blast radius mis-scoped.** `test_registry_builtin_activation_parity.py` has only
   **2** test functions; the real re-baseline spans `test_doctrine_service_factory.py::
   test_absent_key_returns_all_builtins` + the `tests/charter/*` activation suite (~11 files).
   → Enumerate the grep-verified set at plan; freeze into WP owned_files. [renata MEDIUM, priti MAJOR]

8. **`_WHEN_DOING_RE` is a closed 6-verb set** (`are about to|need to|encounter|introduce|
   rename|review`) — verified at test_wp_prompt_governance_contract.py:221. The #3082 fix must
   be grammatical **and** land in that set (or widen the regex as a deliberate contract change),
   and the gate does whole-prompt `.search()` today → assert per-stanza. [renata MEDIUM]

9. **FR-007 forward-pointer is stale on arrival.** No forward "pending decomposition" pointer
   exists in siblings; only retrospective notes (`doctor.py:10` "was decomposed into…"). Since
   FR-008 decomposes in the same mission → make FR-007 a retrospective note or fold into FR-008.
   [renata MEDIUM, paula LOW]

## Plan-phase carry-forward (not spec-blocking)

- Run the #2532 decomposition **research pass** (function→seam map across ~90 functions +
  import-cycle map) BEFORE WP slicing — the mission `research/` dir is empty. [priti MAJOR]
- Rename `test_no_activation_key_admits_all_builtins_in_routing` → generic-agent semantics. [renata LOW]
- Seed the issue-matrix (#3082/#3064/#2532) before/at tasks; verify it survives finalize-tasks. [priti MINOR]
- Epic linkage nuance: #2532 body declares `Epic: #2173` but is labelled tech-debt/tidy-up and is
  behaviour-preserving (not ports-injection) — planner-priti argues #2519 (charter authoring epic)
  is the better parent. Honour the issue author's `#2173` unless operator redirects; note the tension. [priti MINOR]
- #3082 carries no priority/type label — add one at plan for dashboard/matrix consistency. [priti NIT]

## No foldable duplicate mission found
Related-issue sweep: routing/dispatch/default-charter → only #3064; context.py decomposition →
only #2532. Sibling god-module tickets #2057 (merge.py, open), #2059 (doctor.py, open),
#2464 (workflow.py, CLOSED) are precedent, not overlap. #2173 epic is open; asset surface is real;
no default `charter.yml` asset exists yet (FR-005 net-new). [paula]
