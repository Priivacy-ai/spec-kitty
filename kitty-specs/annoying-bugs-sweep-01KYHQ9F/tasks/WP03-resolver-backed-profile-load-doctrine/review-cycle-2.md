---
affected_files: []
cycle_number: 2
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command:
reviewed_at: '2026-07-27T14:11:49Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 Review Cycle 1

## Verdict

Changes requested. The canonical profile-load skill, alias direction, adversarial-squad
guidance, tracker correction, and reference projection are sound, but the implementation
does not yet cover two known raw-directory fallback instructions and the architectural
guard has a matching false negative.

## Findings

**[HIGH] `src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md:555` and
`src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md:234` - known
CLI-unavailable profile-directory fallbacks remain unbounded and uncaveated - update both
canonical source prompts so the fallback is restricted to a read-only harness that cannot
invoke the CLI and states the overlay/lineage/override divergence warning. Issue #1840's
corrected body explicitly lists these as two of the four raw-read sites, so leaving them
unchanged fails FR-008, C-006, and the WP definition of done. These paths are not in WP03's
current ownership map; revise/finalize ownership before editing them and do not edit
generated agent copies.**

**[HIGH] `tests/architectural/test_profile_load_resolver_guidance.py:24` - the guard only
recognizes paths ending in `.agent.yaml`, so it reports no offender for the exact surviving
instruction `look for profiles under src/doctrine/agent_profiles/built-in/` - extend the
semantic predicate to recognize imperative directory lookups as raw profile resolution,
then add a planted-offender test using the exact canonical-prompt wording. Preserve benign
data/path references and the fully bounded read-only fallback. The current focused suite
passes while this known form survives, so the guard is not yet non-vacuous for the declared
defect class (FR-007/FR-008/NFR-003).**

## Verification

- `PWHEADLESS=1 pytest tests/architectural/test_profile_load_resolver_guidance.py
  tests/doctrine/test_spk_skill_pack.py
  tests/architectural/test_docs_cli_reference_parity.py
  tests/architectural/test_no_legacy_terminology.py
  tests/doctrine/test_procedure_consistency.py -q` - 21 passed, 2 skipped.
- Diff-scoped Ruff - passed.
- The guard reports 18 guidance files and zero offenders on the current tree.
- A temporary fixture containing the exact `look for profiles under
  src/doctrine/agent_profiles/built-in/` instruction returns `[]`, confirming the false
  negative.
- Issue #1840 is assigned to the Human-in-Charge, names this Mission, corrects both stale
  claims, and contains implementation evidence for commit `c3f290654`.
- Changed implementation files match WP03's declared ownership and do not overlap another
  WP's product files.

## Anti-Pattern Checklist

- Dead code: N/A - doctrine and tests only; the new reference is discovered through
  `CanonicalSkill.references`.
- Synthetic-fixture test: FAIL - the planted guard fixture omits a known raw-directory
  instruction form, allowing the production doctrine defect to survive.
- Silent empty return: PASS.
- FR coverage: FAIL - FR-008 and NFR-003 are incomplete for the two known fallbacks.
- Frozen surface: PASS.
- Locked decision: PASS.
- Shared-file ownership: PASS for the submitted diff; ownership must be revised before
  adding the two missing canonical prompts.
- Production fragility: N/A.
