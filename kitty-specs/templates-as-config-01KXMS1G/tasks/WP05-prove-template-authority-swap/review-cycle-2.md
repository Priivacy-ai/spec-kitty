---
cycle_number: 2
mission_slug: templates-as-config-01KXMS1G
wp_id: WP05
reviewer_agent: codex:gpt-5:reviewer-renata:reviewer
reviewed_at: '2026-07-16T10:04:09Z'
verdict: approved
affected_files:
  - path: tests/architectural/test_no_parity_scaffold.py
  - path: tests/e2e/test_cli_smoke.py
  - path: tests/integration/test_mission_type_resolution_integration.py
reproduction_command: >-
  git diff --name-only kitty/mission-templates-as-config-01KXMS1G..HEAD | rg '^tests/.*\.py$' | xargs env -u SPEC_KITTY_ENABLE_SAAS_SYNC SPEC_KITTY_TEST_DB_NAME=test_templates_as_config_01KXMS1G_lane_e uv run pytest -q
---

# WP05 Review — Cycle 2

Reviewer profile: `reviewer-renata`.

Applied lenses: incremental review and locality of change; reverse-speccing of enduring integration/e2e tests; mutation resistance for the AST and residue gates; test-scaffolding scrutiny; independent test, type, coverage, performance, scope, and evidence verification. The test-scaffolding lens concedes that the small synthetic AST/bytecode fixtures are appropriate here because they mutate the permanent guard itself while the FR assertions continue to exercise production entry points.

## Prior blocker reproduction

1. **Order isolation — PASS.** The exact changed-test path-order command above, where e2e runs before integration, passed `189 passed, 4 warnings` in 61.47s. The explicit implementer order with integration before e2e also passed `189 passed, 4 warnings` in 62.32s. `test_software_development_mission_resolves_exact_configured_templates` now owns the higher global tier through an empty temporary `SPEC_KITTY_HOME`.
2. **Exact typeless AST predicate — PASS.** The focused mutation replay passed both nodes: `is` evaluates accepted and `is not` evaluates rejected. The production-reader assertion also requires the legacy call inside the exact `mission_type is None` body and absent from the else body.
3. **Compiled scaffold residue — PASS.** A synthetic `test_template_resolution_parity_scaffold.*.pyc` is detected while only the permanent guard source and its own compiled artifact are exempt. The final recursive residue test passes; no transient scaffold source or bytecode remains.
4. **Parity replay auditability — PASS.** The renewed evidence records the exact command, exit 0, four full node IDs, compared package/project-override tiers, path/tier/mission/exact-byte semantics, deliberate architecture-gate failure while source and bytecode existed, and deletion afterward. Coordinator commit `6d52d6694cb82b97a5173f986385c371ed8facc0` contains the renewed entries. Recorded SHA-256 values independently match: `approach.md` `62035c17e736ce2dcddc4f72a0e9cdefcbffe6d70e34495db9bec0f9c7b9edae`; `design-decisions.md` `7f9e27bda371e7e5c8b17038fa91b1a6cd5265619cacff51ef4d02a947864d25`; `tooling-friction.md` `e768667b1249847d7b3c87355992931a12b8cc430dfa404a8c54e236021924bc`.

## Full WP verification

- Independent aggregate coverage run: 189 passed; `diff-cover` reports 100% over 75 changed production lines, 0 missing, against `kitty/mission-templates-as-config-01KXMS1G`.
- Ruff check passes on every changed Python file. Strict mypy passes on all five changed production files. All three WP05-owned files pass `ruff format --check`; the nine formatter failures outside WP05 exactly match the mission-base frozen baseline, so this WP introduces no formatter growth.
- Determinism, ordered governance selection, and the action-sequence hot-path `<100 ms` tests pass.
- Real subprocess CLI smoke covers configured specification and planning overrides and fail-closed null mapping before mission state creation. Both nodes are included in each 189-test replay.
- `git diff --check` passes. WP05 commits modify only its three enduring owned test files; the temporary scaffold is absent. No version/release file changed, no new `--feature` interface was introduced, and no #2659–#2661 implementation surface entered the diff.
- Production seams have live callers from both reader entry points. No WP05 production code or silent failure path was added. New fail-loud exceptions carry mission type, artifact kind, mapped filename where applicable, and preserve the `FileNotFoundError` cause.
- Issue #2658 remains open and assigned to `robertDouglass`; the mission claim comment is `https://github.com/Priivacy-ai/spec-kitty/issues/2658#issuecomment-4989267695`. The issue-matrix row is `in-mission`, valid for per-WP approval.
- T026–T032 are marked complete and the renewed coordinator acknowledgment satisfies the three-trace handoff gate.

## Anti-pattern checklist

1. Dead code: **PASS** — production resolver and both readers have live callers; WP05 adds only enduring tests.
2. Synthetic-fixture test: **PASS** — FR behavior tests invoke real activated context, resolver, mission creation, setup-plan, and subprocess CLI paths. Synthetic fixtures are limited to mutating the architecture guard itself.
3. Silent empty return: **PASS** — no WP05 production path is added; reviewed mission returns of `None` are the explicit null-mapping contract.
4. FR coverage: **PASS** — FR-001 through FR-009 have doctrine, resolver, reader, integration/e2e, parity, and architecture evidence.
5. Frozen surface: **PASS** — WP05 commits touch only declared enduring owned files.
6. Locked decision: **PASS** — no software-development magic default enters activated readers; typeless compatibility remains confined to its exact temporary branch.
7. Shared-file ownership: **PASS** — WP05 has no shared owned-file edits; dependency production changes were independently tested, not modified.
8. Production fragility: **PASS** — no WP05 production raise exists; reviewed configuration raises are deliberate fail-loud contract behavior.

## Verdict

**APPROVED.** All four cycle-1 blockers are resolved and independently reproduced. The complete WP contract passes with no remaining critical, high, medium, or low code finding.
