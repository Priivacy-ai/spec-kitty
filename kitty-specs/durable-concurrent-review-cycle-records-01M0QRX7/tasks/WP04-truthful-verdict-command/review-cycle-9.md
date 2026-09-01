---
affected_files: []
cycle_number: 9
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T15:03:53Z'
reviewer_agent: user
wp_id: WP04
---

# WP04 Review Feedback — Cycle 8

## Verdict

Rejected after fresh native run 32741726527, Linux job 97477519028,
observed a concurrent verdict-save ownership refusal that was explicit to a
human but lacked a stable machine-readable refusal envelope.

## Evidence

At SC-004 round 23, reviewer-b completed a durable rejection. The concurrent
reviewer-a command then exited nonzero with only a generic Agent mismatch error.
No verdict loss occurred, but the result could not prove false durability or
the authoritative assigned/requesting agents without parsing prose.

## Required correction

Preserve the ownership policy and exit code. For automatic verdict-target
moves only, return a stable ownership_refusal diagnostic containing:

- current and requested lanes;
- assigned and requesting agents;
- verdict_durably_persisted false;
- null evidence/destination references;
- no event id.

Do not add a retry, use message parsing, weaken assignment policy, or broaden
the verdict-save queue to unrelated operations.

## Required evidence

- pure transition-core and live command tests for the typed refusal;
- compatibility tests proving the human error remains;
- Ruff, strict mypy, and diff-check.
