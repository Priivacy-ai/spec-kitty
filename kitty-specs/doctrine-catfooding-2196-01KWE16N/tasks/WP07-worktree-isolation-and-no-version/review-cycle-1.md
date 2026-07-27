---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T10:28:04Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP07
---

# WP07 Review — Changes Requested

Reviewer: reviewer-renata (opus). Lane: lane-g. Base: kitty/mission-doctrine-catfooding-2196-01KWE16N.

## Summary

The tactic content is well-authored: both rules present, cross-contamination
defect class named with the PR #2151→#2119 instance, no-version rule states the
PO release-authority boundary, compress-history is cross-referenced (not
restated), diff scope is clean (only `pr-agent-worktree-isolation.tactic.yaml`
in the WP07 commit; `graph.yaml` and `clean-linear-commit-history.tactic` both
untouched). The three named DoD gates pass:

- `spec-kitty doctor doctrine --json` → healthy, 18/18 valid, 0 skipped/0 invalid.
- `tests/doctrine/drg/test_shipped_graph_valid.py` → 2 passed.
- `tests/architectural/test_no_legacy_terminology.py` → 3 passed (the single
  "feature branch" occurrence is inside a prohibition and is acceptable).

The expected-and-waived `test_references_resolve[pr-agent-worktree-isolation]`
forward-ref failure on `DIRECTIVE_045` is present and correctly deferred to WP12
graph regeneration. That one is NOT a blocker.

## Blocking issue (must fix before re-review)

**Redundant tactic reference — `test_root_references_not_repeated_in_steps[pr-agent-worktree-isolation]` FAILS.**

This failure is unique to this new tactic: 115 other tactics pass the same
parametrized check; only `pr-agent-worktree-isolation.tactic.yaml` fails. It is
NOT a forward reference and has no dependency on WP06 or WP12 — it is a
self-contained authoring defect fixable now.

Root cause: the `clean-linear-commit-history` tactic reference is declared TWICE:

- Step 2 ("Cross-reference history compression — do not restate it") has an inline
  `references:` block for `clean-linear-commit-history` (file lines ~51-59).
- The root-level `references:` block ALSO declares `clean-linear-commit-history`
  (file lines ~71-78).

The compliance rule (`tests/doctrine/test_tactic_compliance.py:260`) forbids a
step-level reference from duplicating a root-level reference.

### Fix

Remove the redundant `references:` block from **step 2** (lines ~51-59), keeping
the root-level `clean-linear-commit-history` reference (lines ~71-78) as the
single authority for that edge. Step 2's prose already cross-references the
tactic by name, so no information is lost. (Equivalently you may drop the
root-level entry and keep the step-level one — but the root-level block is the
conventional home for the sibling `refines`-style edge, so removing the step-2
duplicate is preferred.)

### Verify after fix

```
PWHEADLESS=1 python -m pytest tests/doctrine/test_tactic_compliance.py -q -k "pr-agent-worktree-isolation"
```

Expect: only `test_references_resolve` still red (the waived DIRECTIVE_045
forward-ref); `test_root_references_not_repeated_in_steps` and the other
compliance checks green. Also re-run the three DoD gates to confirm no
regression.
