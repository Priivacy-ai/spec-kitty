# Design-Decisions Trace — Doctrine Governance Fidelity

Rationale that would otherwise evaporate.

## Lane B — charter-GATED org overlay (REVISED after architectural-alignment squad)

- **Decision (revised 2026-06-27)**: the org overlay reaching dispatch/projection
  is the **charter-activated** org-provenance subset — resolved via
  `build_activation_aware_doctrine_service` (`resolve_org_roots` + `PackContext`
  three-state filter) — **merged onto** each consumer's existing project repo.
- **Rejected (original plan)**: passing raw `org_dirs`/`resolve_org_roots` into the
  routing/projection `AgentProfileRepository`.
- **Why**: the activation gate (`charter/resolver.py:121-130`) sits two layers above
  `resolve_org_roots`. A raw splice would surface declared-but-**de-activated** org
  profiles to dispatch whenever a project keeps an explicit `activated_agent_profiles`
  list — making charter no longer the runtime-resolution entry point, and creating a
  NEW split-brain opposite to the one this mission closes. Proven live by debbie's
  4×4 matrix (raw paths show a de-activated profile; activation-aware hides it). (C-008.)
- **Also rejected**: rerouting the *project* layer through `DoctrineService` — C-002
  still holds for the project overlay (`.kittify/profiles` vs `.kittify/doctrine/
  agent_profiles` are distinct). C-002 governs the project overlay; C-008 the org overlay.
- **#2156 contract**: declared in config AND passes the three-state gate. `None`
  default → all admitted (install→visible needs no activation in the common case);
  explicit list omitting the id → structured miss everywhere.
- **FR-008 gate (revised)**: assert routing/projection surfaces use the activation
  seam — forbid raw `AgentProfileRepository(org_dirs=resolve_org_roots(...))` there.
  NOT "site passes `org_dirs`" (that would certify the bypass). Built-in-only sites
  (`agent/tasks.py`, `charter/context` language cache) stay excluded with rationale. (C-003.)
- **NFR-002 (revised)**: two-regime live proof — activated→visible AND
  de-activated→absent (the activated-only assertion is fakeable).

## Lane B — provenance threading via private repo maps (implement-time, follow-up flagged)

- WP03 (registry) and WP04 (projection) MERGE the WP02 activation-admitted org
  subset onto an existing `AgentProfileRepository` by writing the org entries'
  provenance into the repo's `_profiles`/`_provenance`/`_source_paths` maps — the
  same maps `_load_layer` populates and the public `list_all`/`get_provenance`/
  `get_source_path` readers consume. Sound (mirrors the loader contract), but it
  is private-attribute coupling across the doctrine↔specify_cli boundary.
- **Decision**: accept the private-map seam in-mission (no public merge-with-
  provenance API exists; `org_dirs=` is the forbidden bypass; `save()` writes YAML
  and sets no provenance). **Follow-up (reviewer-renata)**: add a public
  `AgentProfileRepository.register_profile(profile, layer, source_path)` to remove
  the coupling — out of scope here; file post-merge.

## Lane B — FR-013 / IC-09: unify activation layout to the flat runtime layout

- **Decision (operator 2026-06-27)**: `<pack>/agent_profiles/` (flat runtime layout,
  via `resolve_org_roots`) is canonical. The charter activation subsystem's
  `<pack>/doctrine/<plural>/org/` nesting (`_layer_roots.py` doctrine-dir gate +
  `pack_manager._scan_layer_dirs`) is the mess to remove (unification, not parity).
- **Why**: today `charter activate agent-profile <id>` fails "Unknown agent-profile
  ID" against a runtime-resolvable pack — the activation gate is unusable for the
  exact org packs #2156 targets. Both resolvers must agree on layout.
- **Open (for /tasks)**: hard cutover vs layout-tolerant resolver (accept both,
  prefer flat) for backward-compat across all org-pack kinds.

## Lane C — promote, then wire, then shrink

- **Decision**: promote `find_overridden_builtin_urns` /
  `find_unsanctioned_overrides` / `UnsanctionedOverride` from
  `tests/architectural/test_builtin_override_policy.py` into
  `src/doctrine/drg/override_policy.py` (pure, fail-closed) BEFORE wiring
  `doctor doctrine`; update the test to import from production.
- **Why**: the issue presumes a production adjudicator that does not exist — the
  logic is test-local today. Wiring without promotion is impossible.
- **Seam**: reuse the merged 3-layer DRG already built in `_doctrine_collect`
  (doctor doctrine), guarded by the existing no-packs short-circuit — no new DRG
  plumbing (C-006).
- **Gate-unmask discipline**: the `category_7` 7→6 baseline lower only takes
  effect post-merge, so it is paired with a full `tests/architectural/` dry-run
  pre-PR (C-004). Override-policy is a *dormant governance gate* (test-consumed),
  not dead code — wire it, never delete it.
- **Scope boundary**: project-tier overrides remain intentionally ungoverned
  (trusted operator tier), documented per FR-012.

## Lane C — WP09 spec-premise correction (Option A, operator-decided 2026-06-27)

- **FR-011's premise was partially wrong.** It assumed wiring the predicates into
  doctor (WP08) makes all four `_CATEGORY_C` override-policy symbols live. Reality:
  only the FUNCTIONS became live-called; the type/constant exports
  (`POLICY_RELPATH`, `ReplaceableBuiltin`, `ReplaceableBuiltinsPolicy`) stay
  dead-by-name, and WP07 ADDED a fifth dead public export (`UnsanctionedOverride` —
  used by-value, never imported by name).
- **Decision (Option A)**: narrow `override_policy.__all__` to the 3 live functions;
  the dead type/constant exports leave the public API (still importable directly).
  Then `_CATEGORY_C` empties, the module leaves `_CATEGORY_7`, baseline 7→6. Honors
  FR-011's "retire the shield" intent without preserving dead public symbols.
- **Process lesson (cumulative gate debt)**: WP07's per-WP review did NOT run
  `test_no_dead_symbols.py`, so its new dead public symbol slipped through and only
  surfaced at WP09 (the integration point). Confirms the standing order to run the
  FULL `tests/architectural/` sweep at the integration/merge point, not just per-WP.
  The implementer correctly STOPPED rather than fake a caller or pad the allowlist.

## Lane A — interpolate, don't reframe

- **Decision**: mirror the `risk_boundaries` interpolation shape at
  `compiler.py:944`; one f-string change.
- **Why**: field census shows `documentation_policy` is the SOLE read-but-dropped
  field (13 siblings interpolate) — not a class. Resisted promoting it to a
  "field-interpolation framework" (over-consolidation bias). Distinct from #1416
  (key-drift in `synthesizer/`, never touched `compiler.py`).
