---
affected_files:
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp05-probes/survivor-negative-invariants.json
- docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/raw/wp05-results.json
cycle_number: 3
mission_slug: assertive-test-suite-sanitation-01KZME3P
reproduction_command: exact artifact replay at c1c79d53937abf11b1c8435311a9eaa47f4d8d8f
reviewed_at: '2026-08-10T12:19:41Z'
reviewer_agent: independent-review-cycle-3
wp_id: WP05
---

# WP05 Review — Cycle 3

## Verdict

Changes requested. Five artifacts reproduce completely, all six artifact hashes match their manifest and references, and all restore/clean/green controls pass. The retained survivor artifact contains one false red claim, so only 12 of 13 declared mutations demonstrate their stated oracle.

## Blocking issue — Legacy status-emitter probe targets the approved module and stays green

At exact base `c1c79d53937abf11b1c8435311a9eaa47f4d8d8f`, replaying `survivor-negative-invariants.json` materializes all five declared changed paths, but its exact test command reports `4 failed, 1 passed`, not the retained `5 failed` result. The passing node is `tests/architectural/test_no_legacy_status_emit_callers.py::test_production_code_has_no_legacy_status_emit_callers`.

The mutation appends:

```python
from specify_cli.coordination.status_transition import emit_status_transition
emit_status_transition()
```

The guard intentionally forbids imports from `specify_cli.status.emit`; `specify_cli.coordination.status_transition` is the approved transactional surface. Therefore the artifact neither represents the named legacy-emitter fault nor makes the claimed oracle red. `wp05-results.json` nevertheless states that this exact artifact proves the guard reports import/call lines 924/926.

Arbiter action: treat this one survivor proof as unverified. Either accept WP05 with that explicit evidence exception or require a future correction that materializes an actual `specify_cli.status.emit` import/call. Per operator instruction, no cycle-4 review is permitted.

## Verified gates

- All six retained artifacts have byte hashes equal to `probe_artifact_manifest` and all disposition/survivor references checked resolve to those hashes.
- Exact-base disposable replay materialized declared path sets for 1 + 1 + 1 + 6 + 4 + 5 mutations; every restore returned clean; all six restored-green reruns exited 0.
- Five artifacts reproduced every claimed red result. The final artifact reproduced four of five reds and the false claim above.
- Prior cycle-1 brittle local-name guard is deleted; its retained disposable probe independently shows the behavior-preserving rename leaves two behavioral nodes green while the deleted shape guard reds.
- Evidence schema validator: valid; 8 dispositions, 45 unique members, zero errors.
- WP implementation commits touch only WP05-owned tests/evidence; no product source or central shard-map edit. `git diff --check` passes.

## WP anti-pattern checklist

1. Dead code: N/A — no production code added.
2. Synthetic-fixture test: PASS for retained production-path tests.
3. Silent empty return: N/A — no production code change.
4. FR coverage: **FAIL** — one retained structural survivor lacks its claimed causal red proof.
5. Frozen surface: PASS.
6. Locked decision: **FAIL** — retained evidence asserts a red result that exact replay contradicts.
7. Shared-file ownership: PASS — WP07 handoff is explicit and central map untouched.
8. Production fragility: N/A — no production code change.
