---
affected_files: []
cycle_number: 7
mission_slug: durable-concurrent-review-cycle-records-01M0QRX7
reproduction_command:
reviewed_at: '2026-08-24T12:44:44Z'
reviewer_agent: user
wp_id: WP04
---

# WP04 Review Feedback — Cycle 6

## Verdict

REJECTED. Hosted native evidence exposed an allowed concurrent state-machine
refusal that the production command reports only as an unstructured error.

## Evidence

- GitHub Actions run `32727988400`, Ubuntu job `97433508900`, round 42.
- Reviewer A durably saved its verdict and moved the WP from `in_review` to
  `planned`.
- Reviewer B then exited nonzero with only
  `{"error":"Illegal transition: planned -> planned"}`.
- The SC-004 oracle correctly classified that output as `unproven_refusal`.
- The same run passed on macOS and Windows; this correction is for the real
  concurrent state-refusal branch, not an operating-system workaround.

This contradicts FR-002, SC-001, and the plan's allowed-round contract. Those
artifacts permit one durable success plus one independently valid state refusal,
but require the refusal to be explicit and causally evidenced.

## Required correction

Within WP04's owned command-orchestration surface:

1. Detect the typed `TransitionError` produced when authoritative status has
   changed before the second verdict transition is emitted. Do not infer the
   condition by parsing its human-readable message.
2. In JSON mode, return a stable nonzero refusal envelope containing at least:
   `result: error`, `code: invalid_transition` (or `state_refusal`), the
   authoritative `current_lane`, the canonical `requested_lane`,
   `verdict_durably_persisted: false`, null `evidence_ref` and
   `destination_ref`, and no `event_id`.
3. Source both lanes from the already-resolved authoritative move state. The
   envelope must remain truthful for transition failures other than the observed
   `planned -> planned` edge.
4. Add WP04-owned focused tests proving the envelope is structured and that the
   refused reviewer creates no authoritative verdict event or evidence artifact.
   Include a red-capable assertion that the former generic envelope fails.
5. Preserve all agreed behavior: verdict saves wait in line; the queue timeout
   remains 10 seconds; no retry is added; existing state-machine semantics are
   unchanged; preservation/adoption behavior remains unchanged.

## Required validation

- WP04 focused durability and command tests pass.
- The exact three SC-004 production/mutation nodes pass locally.
- Ruff, strict mypy for changed files, and `git diff --check` pass.
- A fresh hosted Linux/macOS/Windows run is required after integration.

