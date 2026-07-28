---
affected_files: []
cycle_number: 2
mission_slug: charter-preflight-remediation-01KYG9WK
reproduction_command:
reviewed_at: '2026-07-27T01:05:00Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

# WP01 review — cycle 1

## Verdict: substantively PASSED — blocked only by a mechanical gate

The mechanism itself is sound and correctly built. `spec-kitty agent tasks move-task WP01 --to
approved` currently refuses the transition with:

```
Error: ERROR: issue-matrix.md has unresolved entries. Fill in verdicts before approving.
Unknown: #2831
```

`kitty-specs/charter-preflight-remediation-01KYG9WK/issue-matrix.md` still has the template
placeholder row (`Verdict: unknown`) for the mission's central issue, #2831. This is a required,
tool-enforced gate (FR-037 / Gate-4) that must be resolved before ANY WP in this mission can reach
`approved`. As WP01 is the first implementation WP (no dependencies), it is the natural place to
set this — recommended verdict is `in-mission` (WP01 lands the enforcement mechanism RED by design;
WP02 is the WP that actually clears #2831's charter-sync loop), with an evidence ref to this WP's
commit (`2446a0bcd`).

**This is the only requested change.** No code, test, or fixture change is required — see the full
verification below. Please update the one row in `issue-matrix.md`, then re-request review; I expect
to approve on the next pass without re-running the full verification.

---

## Full verification performed (all passed)

1. **Red for the right reason** — `pytest tests/architectural/test_remediation_effectiveness.py -q`
   → exactly 4 failed / 8 passed, failing tests named exactly
   `charter_source_309`, `charter_source_318`, `synced_bundle_348`, `synced_bundle_357`. Assertion
   messages show real before/after state + real CLI stdout/stderr, not synthetic values.

2. **Flip test (highest-value check)** — temporarily changed the `:309` remediation string in
   `computer.py` to `spec-kitty upgrade --yes` and reran `charter_source_309` alone: it stayed red
   (`spec-kitty upgrade --yes` aborts on the unrelated `0.10.1_populate_slash_commands` migration
   precondition on WP01's minimal F2 fixture — verified via direct migration-object invocation that
   `ConsolidateCharterBundleMigration.apply()` correctly writes `charter.yaml` from the legacy bundle
   when reached, and via reproducing the same command against a fixture augmented with a realistic
   `.claude/commands/` directory, which DOES flip the assertion green). This confirms the driver's
   assertion/comparison plumbing is correct — it faithfully reports whatever the command actually
   does. The RED result under a bare `spec-kitty upgrade` is real (WP01's F2 fixture, matching
   `data-model.md`'s F2 definition exactly — legacy-bundle files only, no agent scaffolding — cannot
   satisfy `spec-kitty upgrade`'s unrelated migration-chain precondition). `computer.py` and
   `runner.py` were reverted after each experiment (`git status` confirmed clean throughout).
   **Flagging for WP02's reviewer**: re-verify empirically per WP02's own T008 rather than assuming
   `spec-kitty upgrade` (bare) will flip WP01's exact fixture green — my testing shows it will not,
   though the underlying migration mechanism itself is proven correct. This exact risk was already
   raised and explicitly ruled out-of-scope for the mission's spec in `.gates/post-spec.json`
   (`why_refuted` for the same finding), so it is a known, accepted mission-level risk — not a WP01
   defect — but it is real and will resurface at WP02.

3. **Non-vacuity** — removed the `_compute_synthesized_drg` call from `compute_freshness` (reverted
   after): `test_producer_floor_is_pinned` correctly went red (`found 2` vs pinned floor `3`).
   AST-derivation independently reproduced outside the test module and matches the contract's census
   exactly (7 states at lines 309/318/348/357/447/478/491, 3 producers) — genuinely AST-derived, not
   hand-copied.

4. **Operator-visible surface (C-EFF-3)** — mutated `runner.py`'s composed line to always emit
   `spec-kitty charter status` regardless of `check.remediation` (reverted after): the three
   previously-green `synthesized_drg` cases (447/478/491) correctly went red, proving the mechanism
   binds the composed `blocked_reason`, not the raw field.

5. **Isolation (C-EFF-5)** — every fixture is `tmp_path`-rooted; `run_cli`'s `cwd=project_path` and
   `PYTHONPATH` pin to this checkout's own `src/`. No path in the driver references the repo root.

6. **Scope discipline** — `git diff <base>..<lane-a> -- src/specify_cli/charter_runtime/freshness/computer.py`
   is empty.

7. **DIRECTIVE_044** — extends `tests/specify_cli/charter_preflight/_fixtures.py`; no parallel
   fixture mechanism. `build_f1_no_charter` / `build_f3_valid_charter` are unused by this WP's own
   test module, but are explicitly required forward-looking infra — WP04/WP05/WP06's task docs
   instruct "reuse the fixture builders from WP01's `_fixtures.py` extension. Do not author a third
   set." — not dead code.

8. **No leftover mutation** — `git status --short` clean after all experiments.

Additionally: `ruff check` and `mypy --strict` both clean on the two changed files; existing
`tests/specify_cli/charter_preflight/test_runner.py` and
`tests/specify_cli/charter_freshness/test_computer.py` (40 tests) pass unchanged.
