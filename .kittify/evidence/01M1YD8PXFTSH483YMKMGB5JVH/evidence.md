{
  "mission_slug": "upgrade-preview-mission-health-01M1V6E1",
  "mission_number": "",
  "mission_type": "software-dev",
  "overall_verdict": "pass",
  "criteria": [
    {
      "criterion_id": "FR-001",
      "description": "Public CLI dry-run modes do not mutate absent, stale, or warm project/global assets.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:05:57.392001+00:00",
      "notes": "Verified by the focused WP13 source acceptance matrix and immutable preview oracle."
    },
    {
      "criterion_id": "FR-002",
      "description": "Preview discloses every intended global and project generated-surface repair, including same-version runs.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:01.047104+00:00",
      "notes": "Verified by WP10 plan reporting tests and WP13 source acceptance scenarios."
    },
    {
      "criterion_id": "FR-003",
      "description": "Preview operation paths and kinds agree with subsequent apply effects on equivalent fixtures.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:04.422593+00:00",
      "notes": "Verified by preview/apply parity scenarios in the focused WP13 acceptance matrix."
    },
    {
      "criterion_id": "FR-004",
      "description": "A second repair is idempotent and a subsequent preview reports no remaining repair writes.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:07.682813+00:00",
      "notes": "Verified by warm-state and second-run cases in the focused WP13 acceptance matrix."
    },
    {
      "criterion_id": "FR-005",
      "description": "Human and JSON target validation agree for lower, equal, higher, and malformed target versions.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:10.946731+00:00",
      "notes": "Verified by WP10 target matrix tests and WP13 installed-wheel acceptance."
    },
    {
      "criterion_id": "FR-006",
      "description": "Target validation preserves independent compatibility blockers and supported-target policy.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:14.209955+00:00",
      "notes": "Verified by WP10 compatibility tests and WP13 installed-wheel acceptance."
    },
    {
      "criterion_id": "FR-007",
      "description": "Both named identity-less mission directories are classified without fabricated identity.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:17.440623+00:00",
      "notes": "Verified by WP11 provenance recovery tests and corpus audit."
    },
    {
      "criterion_id": "FR-008",
      "description": "Both named drifted snapshots reconcile against authoritative events without losing verdicts or provenance.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:20.697546+00:00",
      "notes": "Verified by WP11 recovery tests and WP12 archive-preservation review."
    },
    {
      "criterion_id": "FR-009",
      "description": "The full committed corpus has zero TeamSpace-blocker audit findings and resolves the four original failures.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:23.952796+00:00",
      "notes": "Verified by mission-state corpus audit: 423 missions, 0 errors, 0 TeamSpace blockers."
    },
    {
      "criterion_id": "FR-010",
      "description": "Upgrade consent remains separate from mission-state repair consent.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:27.219088+00:00",
      "notes": "Verified by WP10 upgrade composition and WP11/WP12 recovery boundary tests."
    },
    {
      "criterion_id": "FR-011",
      "description": "Every tracked issue has traceable spec, WP, test, implementation, review, and terminal matrix evidence.",
      "proof_type": "automated_test",
      "evidence": "kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP13-integrated-preview-acceptance/review-cycle-1.md",
      "pass_fail": "pass",
      "verified_by": "codex",
      "verified_at": "2026-09-07T17:06:30.491344+00:00",
      "notes": "Verified by terminal issue-matrix verdicts and WP review artifacts; WP13 used the documented focused verification variance."
    }
  ],
  "negative_invariants": []
}
