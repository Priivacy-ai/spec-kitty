# Post-plan adversarial squad — convergent findings (2026-07-30)

Point-cut: post-`/spec-kitty.plan`. Three profile-loaded read-only lenses:
reviewer-renata (plan-vs-spec completion integrity), paula-patterns (split-brain/bypass/foldable),
python-pedro (implementer feasibility). All load-bearing claims re-verified against code before folding.

## Folded corrections

1. **[paula HIGH — DESIGN DEFECT] Composite predicate was still too narrow.** `charter_activated_urns()` covers 6 URN kinds but excludes `activated_mission_step_contracts` + `activated_glossary_packs` (both charter-activatable per `CHARTER_KIND_TOKENS`) and org packs. A glossary-pack-only / step-contract-only / org-pack configured repo would false-fallback to generic-agent with a wrong "unconfigured" warning. → predicate now ANDs all dimensions + `org_roots == ()`. (`anti_pattern` excluded — not charter-activatable.) Verified `pack_context.py:167-176`, `artifact_kinds.py:208`.

2. **[paula MEDIUM → HIGH, verified] "Governance agrees by construction" was FALSE.** `render_compact_view` (`compact.py:216-230`) merges `resolver_directives` into the `Directive IDs:` block independent of profile; under empty charter `_resolve_directives_selection` (`resolver.py:233-260`) catalog-falls-back to `sorted(doctrine_catalog.directives)` = **the full built-in DIR canon**. So an unadjusted generic-agent dispatch leaks all directives → violates C-003/SC-001. → US1 gains **FR-010** (scope the empty-charter governance block, bounded to the fallback path) + a **red-first** agreement test asserting the `Directive IDs:` block is empty. This is the first squad's split-brain warning, proven real.

3. **[renata BLOCKER + pedro MEDIUM] US3 completion signal was re-negotiable prose; ceiling number unrealistic.** context.py already passes all gates on the monolith. → wired `test_context_decomposition_completion.py` with a **seam-existence manifest** (primary, un-fakeable) + `wc -l ≤ 600` (grounded floor ≈500–540 per pedro's orchestrator measurement; ≤500 stretch; 400 dropped). Missing ≤600 = BLOCKER needing operator re-sign-off, not an implementer tweak.

4. **[renata HIGH] Parity-corpus non-triviality unenforced.** → the parity test enumerates the 3 behaviour-bearing cases and asserts each hit its distinguishing marker; deleting an input reds the suite.

5. **[renata HIGH] "Baseline after US1+US2 merge" unenforceable in one mission.** → `/tasks` encodes an explicit WP dependency (baseline WP depends on US1+US2 approved) and the golden must include the empty-charter input (provenance proof).

6. **[renata MEDIUM] FR-005 under-tested SC-002.** → added an activatability test (activate the scaffold in a temp repo → valid charter, user charter untouched).

7. **[renata MEDIUM] FR-004 had no wired assertion.** → assert software-dev availability + generic-agent on the empty path in the owned tests.

8. **[pedro MEDIUM] `empty_charter_fallback` slot-default footgun.** Dynamic `InvocationPayload.__init__`/`to_dict getattr` → legacy payloads emit `null`/`AttributeError`. → thread the kwarg at the single construction site; `dispatch.py` reads via `getattr(..., False)`.

9. **[pedro LOW guardrail] Cycle placement.** `fetch_stanza.py` gets ONLY the pure renderer; `_budget_estimate` + limit const → `token_budget.py` (already imports fetch_stanza). Co-locating the budget gate into fetch_stanza would re-form the cycle. `_build_doctrine_service`/`_maybe_build_doctrine_service` each need their own `import doctrine.service as _doctrine_service_module` in new homes.

10. **[paula LOW] Asset naming.** Renamed `common-default-charter` → `common-charter-scaffold-minimal` to avoid colliding with `charter/packs/default.yaml`; cross-ref both files. Mime rationale corrected (py3.11 already returns application/yaml → guard, not 3.13-fix).

11. **[renata LOW] AS2 wording** reworded ("re-expressed via a new convergence test", no fixture re-baselined).

## Confirmed sound (no defect)
- **[paula CONFIRMED]** `executor.py:255-259` is the ONLY auto-route (no-profile-hint) entry point — `.route(` has one caller; workflow/doctor/orchestrator-api paths use explicit profiles. Option-A boundary is correct and surgical.
- **[pedro]** globals + `_reset_agent_profile_cache` relocate cleanly (function-object re-export → single source of truth, no dual-cache trap); Literal widening mypy-strict clean; `self._repo_root` available at the seam.

## Carry-forward
- **#2399 (P1)** "structurally enforce agent-profile loading across invocation contexts" is adjacent — note so its future enforcement accounts for the new generic-agent fallback path. No foldable dup.
