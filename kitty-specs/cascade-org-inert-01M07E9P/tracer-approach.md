# Tracer: Approach — cascade-org-inert-01M07E9P

## Two-round spec-fix history

**Round 1 (6 adversarial-review findings, all confirmed and fixed):**
The spec-phase R1-R6 squad (`gov`/`arch`/`verify` lens groups) found 6 real defects in the first
authored draft of `spec.md`:
- 2 severity-4 findings that the drafted FIXES themselves were wrong, not merely incomplete:
  - FR-001's `resolve_layer_roots` widening ignored a third consumer (`charter list --all-layers`)
    sharing the same `dict[str, Path]` return contract — a silent breakage risk.
  - FR-002's stated fix (swap `_load_action_doctrine_bundle` for `_resolve_action_bundle`) was a
    **no-op as scoped** — the CLI command truncates `org_root` to `org_roots[0]` BEFORE either
    function is ever called, so swapping the internal call alone changes nothing observable.
- 1 severity-2 citation error (wrong file named as evidence for a missing symbol).
- 2 findings (severity 3, severity 2) about acceptance-criteria hygiene — recommendations/open
  questions mixed into numbered "Acceptance Criteria" lists as if they were testable, and a
  quadrant-coverage gap (FR-003 had no multi-pack-chain AC or acknowledgment of the omission).
- 1 severity-3 finding that SC-004's "green post-fix" claim didn't acknowledge the repo's known
  #3284 baseline-red condition.

All 6 were fixed directly (not by the reviewing squad — a fresh pass, per review-protocol.md's
report-only/independence discipline), each with fresh live re-verification of the underlying code
claim before the fix was written (not just trusting the finding's prose). See
`reviews/spec-gov.findings.yaml`, `spec-arch.findings.yaml`, `spec-verify.findings.yaml`,
`spec.merged.yaml`, `spec-refute-1.yaml`, `spec.confirmed.yaml`, `spec-verify.yaml`,
`spec-fresh.yaml` for the full trail.

**Round 2 (scope correction — item 4 dropped):**
After Round 1 passed, the orchestrator identified that scope item 4 (the
`load_validated_graph`/`_load_action_doctrine_bundle` asymmetric-guard / whole-bundle-collapse
defect, which had been numbered FR-004 with its own SC-003) is **already fixed in open PR #3401**
(`org-pack-drg-root-graph-guard-01KZY0QT`, closes #3384) — verified live via `gh pr view 3401`
(state OPEN; description matches the mission's own live-reproduced mechanism almost exactly;
implementation touches the same two files, `_drg_helpers.py` and `action_doctrine_bundle.py`, this
mission's own FR-004 would have touched). Designing a second fix for the same defect on the same
lines would have created a merge conflict with #3401 and violated the charter's single-canonical-
authority principle. FR-004 and SC-003 were retired; every AC/scenario/entity/constraint that
referenced them was swept and corrected to state the "out of scope, #3401 owns it" reasoning
explicitly. A fresh full re-read after this round caught and fixed a self-introduced ID collision
(a new Constraints-table row initially numbered `C-005` collided with an existing external
`C-005 shared-reference-safety contract` reference already used elsewhere in the same document —
renumbered to `C-006`).

## Why this mission's scope is exactly 3 FRs, not 4

The remaining three FRs (FR-001 cascade, FR-002 context, FR-003 rebaseline) are all instances of
the SAME defect class — a caller that never threads a configured org root/chain into a shared
primitive that already knows how to use one, introduced by #3520/#3525 but left unfixed at these
specific call sites. Item 4 (now dropped) was a DIFFERENT, orthogonal defect class — a malformed
org pack's CONTENT breaking the loader/bundle builder, independent of whether org roots are
threaded at all. Both are real, both were confirmed live, but only the first class is this
mission's job; the second already has an owner (#3401).

## Plan-phase design approach

Every fix is scoped as a minimal, caller-side parameter-threading change reusing EXISTING shared
primitives (`resolve_existing_org_roots`, `_resolve_action_bundle`, `Indexer.__init__`'s
`repo_root` param) rather than inventing new abstractions — smallest-viable-diff first
(`change-apply-smallest-viable-diff`), Boy Scout Rule only within the touched file set (verified,
via live `ruff --select C901`, that none of the touched files carry complexity debt worth folding
as a distinct campsite-clean step), Locality of Change as the brake (no scope creep into
`charter list --all-layers`'s own multi-pack display, deliberately deferred to a follow-up issue).
