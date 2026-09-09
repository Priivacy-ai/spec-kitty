---
affected_files: []
cycle_number: 1
mission_slug: ci-pipeline-reinstatement-01M1X35E
reproduction_command: spec-kitty agent tasks move-task WP17 --to approved --mission ci-pipeline-reinstatement-01M1X35E
reviewed_at: '2026-09-07T16:06:01Z'
reviewer_agent: claude
wp_id: WP17
---

Approved by claude: Independent adversarial review APPROVE: T088 reproduces real #2967 bare-name false-pass (verified at parent commit), oracle single-source via gate_selection (no second parser, grep-confirmed), #2967 fix genuine (planted zero-producer no longer covered, 17-line narrow CompiledGate fix), planted-orphan→ZeroGatedGroupError + non-vacuity floor→OracleVacuousError both fire, SC-004 negative (MustRunGateUnwiredError), 32 tests pass. test_workflow_coherence red is a known merge-time consolidation fold (WORKFLOW_FILES needs the full on-disk set), tracked for wrap-up.
