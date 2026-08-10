---
verdict: fail
mode: lightweight
reviewed_at: 2026-08-10T12:18:01.959503+00:00
findings: 7
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: spec-kitty review (internal gate 1)
    exit_code: 1
    result: fail
  - id: gate_2
    name: dead_code_scan
    command: spec-kitty review (internal gate 2)
    exit_code: 1
    result: fail
  - id: gate_3
    name: ble001_audit
    command: spec-kitty review (internal gate 3)
    exit_code: 0
    result: pass
issue_matrix_present: not_applicable
mission_exception_present: not_applicable
---

## Findings

- **wp_not_done** `WP01`: lane is `approved`
- **wp_not_done** `WP02`: lane is `approved`
- **wp_not_done** `WP03`: lane is `approved`
- **wp_not_done** `WP04`: lane is `approved`
- **wp_not_done** `WP05`: lane is `approved`
- **wp_not_done** `WP06`: lane is `approved`
- **dead_code_baseline_missing** `LIGHTWEIGHT_REVIEW_MISSING_BASELINE`: Run `spec-kitty merge` to bake baseline_merge_commit into meta.json, or rerun review with `--mode post-merge` after merge.
