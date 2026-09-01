---
divio_type: explanation
audience: agentic-framework-core-team
updated: 2026-08-23
---

# Approach Tracer

## Planning

- Began from issue #3235 and an adversarial finding that SC-004 was not met: the event leg was exercised, but committed Markdown evidence was allowed to disappear.
- Selected a dedicated checkout-wide verdict-save queue after operator interrogation. The chosen behavior is wait in line, 10-second timeout, explicit refusal, and no automatic retry.
- Kept the status lock separate and short to preserve the no-Git-under-status-lock invariant.
- Chose retained-artifact adoption for identical retries and preserved `--no-auto-commit` as local-only.
- Designed the acceptance oracle to inspect independent durable state rather than trust the result field under test.

## Implementation updates

Append material deviations, discoveries, and verification evidence here during implementation.
