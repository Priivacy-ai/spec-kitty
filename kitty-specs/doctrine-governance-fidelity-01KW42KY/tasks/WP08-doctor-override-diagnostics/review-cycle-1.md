---
affected_files: []
cycle_number: 1
mission_slug: doctrine-governance-fidelity-01KW42KY
reproduction_command:
reviewed_at: '2026-06-27T10:25:19Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP08
review_artifact_override_at: "2026-06-27T10:36:06Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP08"
review_artifact_override_reason: "Cycle-1 re-review by reviewer-renata APPROVED (golden re-pin content-anchored, zero net-new failures, 5/5 override green); supersedes the cycle-0 rejection artifact review-cycle-1.md"
---

# WP08 review feedback (cycle 1/3) — reviewer-renata

Implementation is correct and approved on substance (C-006 single-merge reuse,
in-ownership health flip via org_drg["errors"], dedicated unsanctioned_overrides
key, pure _adjudicate_org_overrides ≤15, FR-012 boundary documented, WP07
predicates now live-called, 5/5 new tests green). ONE blocking gate regression:

## 1. (BLOCKING) Re-pin the doctrine help golden snapshot
Your FR-012 docstring addition to `doctrine_check` changed `doctor doctrine --help`,
which broke a real, current golden test that was NOT re-pinned:
`tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py::test_subcommand_help_snapshot[doctrine]`
— passes on the WP07 parent (4eabafc6f), fails on your tip. This is exactly one
NET-NEW failure introduced by your owned docstring change.

Fix: update `EXPECTED_HELP["doctrine"]` (the doctrine entry) in that golden file
to include the new "Override governance (FR-010 / FR-012)" block. The assertion is
STALE (the product change is correct), so re-pin it — do not weaken or skip the test.
This file is outside your declared owned_files, but the break is directly caused by
your owned change → re-pin it here under ownership leeway (rationale: caused-break).
Verify: `pytest "tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py::test_subcommand_help_snapshot[doctrine]" -q` is GREEN.

## 2. (Optional, non-blocking) canonical config key
Switch the new test fixtures from the deprecated top-level `organisation_packs`
to `doctrine.org.packs[].local_path` to silence the DeprecationWarning.

## DO NOT touch the other ~20 pre-existing failures in that golden file
They are present at the WP07/mission base (constant across base→tip), NOT caused by
WP08 — likely a local Typer/venv-skew artifact. Leave them; the orchestrator will
adjudicate them at the pre-PR full-gate sweep. Your goal: ZERO net-new failures.
