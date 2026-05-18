---
affected_files: []
cycle_number: 5
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T09:06:07Z'
reviewer_agent: codex:gpt-5:reviewer-rita:reviewer
verdict: approved
wp_id: WP01
---

# WP01 — Sync boundary preflight module (cycle 3 review, override-approved)

**Verdict: approved**

This artifact records the cycle-3 approval that the original reviewer
(`codex:gpt-5:reviewer-rita:reviewer`) issued verbally but could not persist
because the codex sandbox denied writes to the planning repo. The orchestrator
applied `spec-kitty agent tasks move-task WP01 --to approved
--skip-review-artifact-check` with the verbal approval recorded in the
override note.

## Summary

- `run_preflight(foreground=None)` no longer calls
  `read_queue_scope_from_session`, `resolve_private_team_id_for_ingress`, or
  `TokenManager.rehydrate_membership_if_needed`. A new helper
  `_read_queue_scope_local_only()` reads the in-memory session and on-disk
  credentials only.
- New regression test `test_run_preflight_never_calls_rehydrate_membership`
  monkeypatches the SaaS-touching helpers to raise and asserts the preflight
  never invokes them.
- 24/24 preflight tests pass. `mypy --strict src/specify_cli/sync/preflight.py`
  clean. Coverage on `preflight.py`: 92%.

## Acceptance criteria

- [x] FR-001 (reusable preflight gate exists)
- [x] FR-003 (named mismatched fields, canonical six)
- [x] NFR-001 (≥90% coverage on changed module)
- [x] NFR-002 (mypy --strict clean)
- [x] NFR-003 (≤100 ms latency)
- [x] NFR-004 (≤25-line refusal — verified worst-case at WP03 cycle 2 = 24 lines)

## Implementing commit

`bcda08ef fix(WP01): preflight uses local-only scope resolution; no SaaS round-trip`
