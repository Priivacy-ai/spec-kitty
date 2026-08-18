# Contracts: Checkout-Identity Seam & Verdict-CLI Parity

Behavioral interface contracts (not HTTP schemas), each testable and FR-pinned. "MUST" is normative. Reframed 2026-08-18 after the post-plan squad: the remediation is the **#3128 fail-closed refusal**, not a checkout-local redirect; there is no clone/primary classifier (C-005).

## C-1 — Checkout-identity guard (FR-001, FR-008)

**Interface**: `resolve_checkout_identity(cwd, intent) -> CheckoutIdentity`.

- MUST decide `is_owner` from decidable local git state (worktree-pointer topology + ownership claim), NOT from a clone-vs-primary guess.
- For `intent == PRIMARY_READ`, MUST return `canonical_target` unchanged regardless of `cwd` — preserving the deliberate anchors (`get_feature_target_branch`, `resolve_merge_target_branch`, `mission_runtime/resolution.py`). A characterization test MUST pin each anchor GREEN.
- For `intent == WRITE` from a foreign lane worktree (`is_owner == False`), MUST signal fail-closed (see C-2).
- MUST NOT change read-path behavior for the ~130 `get_main_repo_root` callers not in the adopter set (C-008 read-seam fence).

**Contract test**: fixtures {owner-primary, foreign-lane-worktree, nested-clone} × {WRITE, PRIMARY_READ}; assert ownership and that every PRIMARY_READ anchor returns its primary target unchanged. **Red-first**: none for the classifier itself (identity is new); the red-first tests live in the adopters (C-2/C-3).

## C-2 — Fail-closed write refusal (FR-002, FR-003, NFR-003)

- A foreign-checkout `WRITE` invocation MUST refuse via the single `FailClosedRefusal` seam; the message MUST contain the `refusal_path` (the checkout it would otherwise have acted on) verbatim.
- An **owner** invocation MUST proceed exactly as today (no new refusal).
- Per-command decisions (no blanket-REFUSE loophole):
  - `intake` (FR-002): MUST perform the identity check before writing the shared untracked brief slot; `--force` MUST NOT overwrite a slot owned by a different checkout without it.
  - `doctor tool-surfaces --fix` (FR-003): from a lane, MUST refuse (naming primary) rather than silently repair the primary's per-checkout agent-surface manifest.
- Architectural test: no in-scope command emits a write-refusal outside the `FailClosedRefusal` seam (makes NFR-003's "100%" enforced, not sampled).

**Contract test (red-first)**: from a lane worktree, `doctor tool-surfaces --fix` and `intake` are RED on base (they silently mutate primary) and GREEN after (refuse, naming the path). Owner-checkout invocation stays green throughout.

## C-3 — Guard false-green fixes (FR-005, FR-006)

- `setup-plan`: `branch_matches_target` MUST be computed from the invoking checkout / `meta.json`, never the primary's HEAD. (Target-branch resolution stays primary-anchored — deliberate — only the *match* is corrected.)
- `migrate backfill-runtime-state`: the cutover guard MUST be invoking-checkout-aware; it MUST NOT pass merely by verifying against the same redirected path it wrote. (The write target to the coord/primary event log stays deliberate per C-003.)

**Contract test (red-first)**: from a lane worktree on a lane branch, `setup-plan` reports `branch_matches_target: true` on base (primary's HEAD) → RED; GREEN after it reflects the invoking checkout. `backfill` verify passes-against-redirected-path on base → RED; GREEN after it is lane-aware / refuses.

## C-4 — mission-state reconciliation (FR-004, FR-009)

- `doctor mission-state --audit/--fix` MUST preserve the deliberate primary status-home (#2320) — the canonicalization target stays primary.
- It MUST add checkout-identity awareness so a lane invocation does not act as an unannounced primary canonicalization, and its audit MUST NOT report a false-green from a redirected read.
- The repair manifest MUST enumerate every field it touches, including removed fields (manifest honesty). Verdict destruction is already fixed (C-002) — no destruction fix.

**Contract test**: a lane invocation is surfaced (refused/announced), not silent; the manifest lists every touched field; a green sentinel pins `bec7c25273` (NFR-004).

## C-5 — find_repo_root nested-clone boundary (FR-007)

- `find_repo_root` MUST stop at a nested-clone `.git`-directory boundary consistently with `resolve_canonical_root` (which already stops at rule 1 / `.kittify`), eliminating the resolver disagreement.

**Contract test (red-first)**: a nested clone inside a primary — `find_repo_root` re-anchors to the outer primary on base (RED, disagrees with `resolve_canonical_root`); after the fix both return the nested clone.

## C-6 — Unified review-verdict CLI path (FR-010, FR-012, FR-013)

- `agent status emit` MUST accept `--review-result-json`, validated by the same hoisted `_parse_review_result_json` as `orchestrator-api transition`; the parsed `review_result` MUST be threaded into the `TransitionRequest`.
- A WP MUST be walkable `in_progress -> for_review -> in_review -> approved -> done` via `agent status emit` alone.
- `--help` MUST document only working paths; the misleading `in_review`/`--evidence-json` verdict example MUST be corrected.
- The `in_review -> approved` guard MUST admit the `ReviewResult` path on both surfaces.

**Contract test (red-first)**: identical verdict JSON → identical validation on both surfaces; an emit-only lifecycle walk reaches `done` (RED on base — no `--review-result-json` exists); `--help` snapshot contains no non-functional example.

## C-7 — Shared, topology-aware `for_review` gate, both directions (FR-011)

- One shared gate implementation (hoisted to a `lanes`-side leaf, surface-neutral error contract) enforced on both surfaces.
- Topology-aware: a clone with satisfied commits PASSES and a clone with **unsatisfied** commits FAILS — **both** asserted identically on both surfaces (no always-pass-for-clone fake).

**Contract test**: same repo state → same verdict on both surfaces across {primary, worktree, clone}; the negative case (clone, unsatisfied commits) fails on both.

## C-8 — Snapshot value round-trip & audit registration (FR-014, FR-015, FR-016, FR-018)

- Replaying a persisted snapshot's event log MUST reproduce the snapshot's projected fields **by value** (not key-presence); the property generator MUST emit ≥1 `review_result`-carrying event (non-vacuous).
- A `status_event_row` carrying `review_result` MUST audit clean (0 `UNKNOWN_SHAPE`).
- A **new `status_event_row`-scoped** drift test MUST fail when a persisted event shape is unregistered (the existing `meta.json`-scoped test cannot cover this artifact).
- After the writer migration, persisted coordination-key rows MUST carry the registered shape.

**Contract test (red-first for the audit half)**: audit a `review_result` row → `UNKNOWN_SHAPE` on base (RED, verified absent from the `status_event_row` frozenset); GREEN after registration. Value round-trip: a snapshot with a corrupted-value replay FAILS (guards against key-only fakes).

## C-9 — Review-cycle write-side kind (FR-017)

- `review/cycle.py` write-side MUST emit the correct artifact kind (not `WORK_PACKAGE_TASK`); `resolve_review_verdict_facts` (`tasks_verdict_persistence.py:404`) MUST be migrated and `test_analysis_report_rehome` re-verified green.

**Contract test**: a review-cycle write lands under the review-cycle kind; verdict-facts resolution reads it; the rehome test passes.

## Cross-cutting

- **Red-first (NFR-001)**: every release-blocking contract ships a `@pytest.mark.regression` test, issue-pinned, **authored and shown failing on base** through the real CLI where one exists (fail-closed slices assert refusal/absence-of-false-green per #3128). FR-015/FR-016 are internal-API-level and marked as such.
- **Green sentinels (NFR-004)**: `407ea376c4` (projection) and `bec7c25273` (repair preservation) each ship a green sentinel — no WP manufactures a red by regressing them.
- **Must-not-flip (C-004/FR-008)**: the primary-read anchors keep passing characterization tests.
