---
affected_files: []
cycle_number: 1
mission_slug: ci-pipeline-reinstatement-01M1X35E
reproduction_command: spec-kitty agent tasks move-task WP10 --to approved --mission ci-pipeline-reinstatement-01M1X35E
reviewed_at: '2026-09-07T16:06:25Z'
reviewer_agent: claude
wp_id: WP10
---

Approved by claude: Review APPROVE after reject→rework: shipped ci-aggregate collect script now derives expected basenames from ci-module-registry + sys.exit(1) fail-loud on shard-missing-from-both (verified pre-fix exit0 → post-fix exit1), outputs.complete consumed by diff-cover gate + fail-loud step under always(), new tests exercise the real extracted heredoc, 16/16 pass. Plus prior: red-first, basename-dedup, FR-007, diff-cover ≥90% + census-dead exclusion, SHA-pins, governance-map untouched
