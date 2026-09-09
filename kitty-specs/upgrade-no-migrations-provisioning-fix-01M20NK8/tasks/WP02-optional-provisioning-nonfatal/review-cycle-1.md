---
affected_files: []
cycle_number: 1
mission_slug: upgrade-no-migrations-provisioning-fix-01M20NK8
reproduction_command: spec-kitty agent tasks move-task WP02 --to approved --mission upgrade-no-migrations-provisioning-fix-01M20NK8
reviewed_at: '2026-09-08T17:34:04Z'
reviewer_agent: user
wp_id: WP02
---

Approved by user: Review passed: single-seam Optional provisioning nulled once in assessment.py and threaded to both guard call sites + dataclass (FR-002/A1); finalizer .apply() no-ops on None + no create effect, config.yaml not created (C-001); deferred_provisioning is info-severity, out of errors/warnings, complete stays true, flows through _print_non_error_diagnostics + JSON payload (FR-003); guard still raises exact ValueError on present non-canonical descriptor (FR-004/DIRECTIVE_043); b"" degenerate authority non-fatal (C-006); 3 out-of-map upgrade.py edits minimal+rationale-commented. test_upgrade_guard_absent 5 passed, ruff clean.
