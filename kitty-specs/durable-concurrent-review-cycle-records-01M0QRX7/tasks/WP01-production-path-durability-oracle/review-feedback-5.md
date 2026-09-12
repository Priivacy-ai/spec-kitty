# WP01 Review Feedback — Cycle 6

## Verdict

Rejected after fresh native Linux run 32741726527 exposed an observed
concurrent ownership-refusal shape that the SC-004 oracle correctly classified
as unproven.

## Required correction

After WP04 produces a typed ownership_refusal, allowlist that exact code only
when the payload proves:

- current/requested lanes match the authoritative state and requested verdict;
- assigned and requesting agents are distinct;
- the requesting agent is the refused reviewer;
- durability is false with no evidence, destination, or event id.

Independently prove that the refused reviewer left no working-tree or governed
event/evidence authority. Do not parse the error message and do not relax any
existing success/refusal checks.
