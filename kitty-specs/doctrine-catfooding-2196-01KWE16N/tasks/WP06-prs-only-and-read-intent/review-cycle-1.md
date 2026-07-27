---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T11:24:47Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP06
---

# WP06 reopened — YAML syntax error in 045 (found during WP12 graph regen)

`src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml` FAILS to
YAML-parse. Line 41 begins an `integrity_rules:` sequence item with a bare backtick:

    - `spec-kitty merge` is permitted — it operates on local main only. The
      prohibition applies to pushing the result to origin/main without a PR.

A backtick cannot start a YAML plain scalar, so `yaml.safe_load` and
`spec-kitty doctrine regenerate-graph` both crash (ScannerError, line 41 col 5). This
slipped through WP06 review because the terminology guard greps, test_shipped_graph_valid
reads the committed graph, and doctor loads leniently — none strict-parse the body. The
regen (WP12) is the first strict full-parse.

FIX: quote that sequence item (and audit the whole file for any OTHER item/value that
starts with a backtick — only line 41 is currently broken). Options:
    - "`spec-kitty merge` is permitted — it operates on local main only. The
      prohibition applies to pushing the result to origin/main without a PR."
  or a block scalar (`>-`). Do NOT change the rule's meaning — only make it valid YAML.

VERIFY before handoff:
  - python3 -c "import yaml; yaml.safe_load(open('src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml'))"  → no error
  - spec-kitty doctrine regenerate-graph --check  → runs without ScannerError
  - the three standard gates green + full test_tactic_compliance / directive_consistency suite green
