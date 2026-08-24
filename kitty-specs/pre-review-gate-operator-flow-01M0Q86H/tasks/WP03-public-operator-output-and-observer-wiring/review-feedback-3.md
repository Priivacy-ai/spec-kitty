## WP03 acceptance follow-up: public NEW_FAILURES evidence is not live

### Blocking finding

The mission acceptance matrix cannot mark FR-005 or the public-entry Definition
of Done as passed while seven tests in
`tests/review/test_pre_review_gate_integration.py` terminate at a
`NO_COVERAGE` binding-resolution result instead of exercising the registered
pre-review handler. Issues #3694 and #3695 correctly classify this as
base-reproduced fixture drift, but “pre-existing” does not make the evidence
valid for this mission's acceptance gate.

Affected nodes:

1. `test_new_failure_surfaced_by_the_real_gate_red_first`
2. `test_pre_existing_failure_does_not_block`
3. `test_bounded_scope_status_shard_excludes_core_misc`
4. `test_consumer_repo_missing_gate_authority_degrades_to_calm_warn`
5. `test_block_mode_blocks_without_force`
6. `test_force_bypasses_block_and_is_recorded`
7. `test_baseline_uncomputable_degrades_to_warn_never_blocks`

All seven currently report the same upstream reason:

`NO_COVERAGE: no gate contract for (, review) governing edge in_progress->for_review`

### Root cause

`_build_wp_file` creates the WP and calls `provision_test_charter`, but does not
write the fixture mission's canonical `meta.json`. Status-event materialization
therefore logs an orphaned mission and leaves the snapshot mission type blank.
The live hook calls `resolve_mission_type(st, feature_dir=st.feature_dir)`, then
`resolve_gate_bindings_for_transition`; with the blank identity it queries the
real repository for `("", "review")`. `_load_review_contract` returns `None`,
so resolution stops at `GateCoverage.NO_CONTRACT`. It never reaches the active
`software-dev/review` contract, `spec-kitty-pre-review` registry handler,
scope-source resolution, real head subprocess, baseline diff, or warn/block/
force policy.

The existing `_pre_review_gate_filter_groups` and
`_pre_review_gate_composite_routing` monkeypatches are not the cause. They remain
supported hermetic overrides passed by `_mt_resolve_scope_source` into the live
`GateCoverageScopeSource`; today they are simply unreachable because binding
resolution exits first.

### Minimal remediation

1. Make `_build_wp_file` write canonical mission metadata for
   `test-pre-review-gate`, including `mission_type: "software-dev"` (and the
   normal canonical slug/identity fields used by nearby move-task fixtures),
   before seeding events. Do not hardcode `software-dev` in production or mock
   `_mt_resolve_active_gate_bindings`.
2. Keep `provision_test_charter(tmp_path)` so the owning
   `mission_step_contract:software-dev/review` URN is genuinely activated.
3. Add a fixture-level assertion that the real binding resolver returns
   `GateCoverage.ACTIVE` for `software-dev`, action `review`, edge
   `in_progress->for_review`, with handler `spec-kitty-pre-review`. This prevents
   future silent fallback to `NO_CONTRACT`, `NO_BINDING`, or `NOT_ACTIVATED`.
4. Preserve the current hermetic filter/routing overrides for the six
   auto-derived gate scenarios, or replace them only with an equivalently real
   `GateCoverageScopeSource` injection. Do not stub a verdict or bypass the
   registry. The consumer-authority scenario should activate the same real
   binding but intentionally omit the coverage authority so it reaches the
   handler-owned `GateAuthoritiesUnavailable` -> visible `NO_COVERAGE` path.
5. Re-run the full integration module and require the seven nodes above to pass.
   In particular, prove the same real public entry produces:
   - default `NEW_FAILURES` warning with one transition;
   - opt-in blocking with zero transitions;
   - `--force` admission with `force_bypassed: true`;
   - baseline-relative `NO_NEW_FAILURES` and uncomputable-baseline warning;
   - bounded derived scope; and
   - handler-level consumer-authority degradation.

### Guardrails

- Do not accept or rewrite expected outcomes to the current binding-level
  `NO_COVERAGE`; that would launder a dead test path.
- Preserve the real `_do_move_task` public entry, registry dispatch, real gate
  engine, real throwaway git repository, and real head-side pytest/baseline
  comparison.
- Preserve warn-by-default, configured block, and `--force` semantics exactly.
- Do not broaden the validation scope, change production contract resolution,
  redesign CI, or add a second classification/binding authority.
- This is a fixture/evidence repair. Product behavior should remain unchanged.
