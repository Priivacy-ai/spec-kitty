---
affected_files: []
cycle_number: 3
mission_slug: mvp-cli-sync-boundary-completion-01KRX11M
reproduction_command:
reviewed_at: '2026-05-18T10:24:15Z'
reviewer_agent: codex:gpt-5:reviewer-rita:reviewer
verdict: approved
wp_id: WP03
---

# WP03 — sync.py expansion (cycle 2 review, override-approved)

**Verdict: approved**

This artifact records the cycle-2 approval that the original reviewer
(`codex:gpt-5:reviewer-rita:reviewer`) issued verbally but could not persist
because the codex sandbox denied writes to the planning repo. The orchestrator
applied `spec-kitty agent tasks move-task WP03 --to approved
--skip-review-artifact-check` with the verbal approval recorded in the
override note.

## Summary

- `sync status --check` and `sync status --check --json` now exit `2` when
  `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set but no auth is present (FR-004).
  JSON includes `ok=false, auth_required=true, auth_present=false`.
- Worst-case `PreflightResult.render()` is 24 visible lines at 80 columns
  (NFR-004: ≤25). Daemon-class field mismatches share one
  `restart-daemon` bullet; auth/orphan/legacy remain on their own lines.
- The line-count test was tightened to reproduce the worst case so it
  cannot regress.
- 47 focused tests pass; 82 sync tests pass overall.
- `mypy --strict src/specify_cli/cli/commands/sync.py` clean.
- `mypy --strict src/specify_cli/sync/preflight.py` clean.

## Acceptance criteria

- [x] FR-002 (sync now gated by run_preflight)
- [x] FR-004 (sync status --check non-zero on documented split-brain shapes,
      including auth-required + auth-absent)
- [x] FR-005 (printed-field coverage matches contracts/sync-status-output.md)
- [x] NFR-001 (≥90% coverage)
- [x] NFR-002 (mypy --strict clean on sync.py and preflight.py)
- [x] NFR-004 (refusal ≤25 lines, verified worst-case = 24 lines at 80 columns)

## Implementing commit

`c9c9bfdf fix(WP03): auth-required exit code on sync status --check; compress render to <=25 lines`
