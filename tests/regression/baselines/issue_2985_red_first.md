# Issue #2985 Red-First Evidence

- Mission: `annoying-bugs-sweep-01KYHQ9F`
- Work package: `WP01`
- Tracker assignment: <https://github.com/Priivacy-ai/spec-kitty/issues/2985>
- Implementation-start comment:
  <https://github.com/Priivacy-ai/spec-kitty/issues/2985#issuecomment-5092237003>
- Regression node:
  `tests/regression/test_birth_cutover.py::test_issue_2985_birth_cutover_preserves_every_wp_lane_and_repairs_old_seed`
- Merge base: `d0a5bacf726c839696c1f4ec38743f8ac93bfd4d`
  (`git merge-base HEAD upstream/main`).
- Baseline command:
  `PYTHONPATH=/tmp/spec-kitty-issue-2985-base/src PWHEADLESS=1 python -m pytest tests/regression/test_birth_cutover.py::test_issue_2985_birth_cutover_preserves_every_wp_lane_and_repairs_old_seed -q --tb=short`
- Baseline result: **FAILED** at the lane-delta oracle. The reduced lane map was
  `{"WP01": "claimed", "WP02": "claimed", "WP03": "claimed"}` instead of
  `{"WP01": "done", "WP02": "approved", "WP03": "in_progress"}`.
- Fixed result: **PASSED** (`1 passed`) with the same exact node after the
  per-WP floor and compatibility repair implementation.
- CI collection proof:
  `PWHEADLESS=1 python -m pytest tests/ -m regression --collect-only -q`
  selected this exact node (`41/33853 tests collected`).
- Caller proof: the owned integration file passes nine tests covering the
  shared backfill, accept stamp, upgrade migration, and both single/corpus
  `migrate backfill-runtime-state` modes. The existing real merge regression
  passed in both coordination and flat topologies.

## Baseline-Red Attribution

The full owned regression file completed with 9 passing tests and four
pre-existing `PlacementMismatchError` failures caused by an ambient
`/tmp/.git` marker redirecting synthetic pytest missions. The representative
failure reproduced unchanged with `PYTHONPATH` pinned to the merge-base source.
It is reported at <https://github.com/Priivacy-ai/spec-kitty/issues/2990>;
WP01 does not alter the placement resolver or those existing harness contracts.

## Cycle 2 — Independent Claim-Slot Witness (review remediation)

Review cycle 1 rejected the claim-slot witness as a builder/verifier tautology
(plan IC-02 / C-002): `_verify_claim_slot_witnesses()` derived its denominator
from `_build_seed_events` output, so a builder that emitted annotations while
suppressing claim transitions produced `VerifyResult(ok=True, wp_count=1,
mismatches=())` with every raw claim seed deleted.

- Fix: the denominator now comes from `read_legacy_runtime()` output plus the
  independently resolved eligibility contract (`_resolve_seed_anchor`, shared
  with the writer but never the builder's emitted rows). Every eligible non-null
  `shell_pid` / `shell_pid_created_at` / `agent` looks up the deterministic raw
  claim row by its own seed id; an absent row is a mismatch, not a skip.
- Anti-disable node:
  `tests/unit/migration/test_backfill_runtime_state.py::test_missing_raw_claim_witness_cannot_be_masked_by_expected_event_builder`
- Control assertion inside that node: with `_build_seed_events` mutated but the
  claim seed intact, `verify_backfill()` stays `ok=True` — so the red below is
  caused by the deleted witness, not by the monkeypatch.
- Pre-fix result (source restored to `460de7769`, cycle-1 implementation):
  **FAILED** — `assert True is False` where
  `True = VerifyResult(ok=True, wp_count=1, mismatches=()).ok`, reproducing the
  reviewer's exact observed output.
- Post-fix result: **PASSED**; `verify_backfill()` itself returns non-OK with
  one `raw claim-slot witness missing for <slot>` mismatch per claim slot.
- Live-path proof (no dead code): `_resolve_seed_anchor` <- `_build_seed_events`
  and `_claim_witness_denominator`; `_claim_witness_denominator` <-
  `_verify_claim_slot_witnesses` <- `verify_backfill` <-
  `migration/runtime_state_cutover.py:121` and
  `status/cutover_eligibility.py:250,303`.
- Cycle-2 gates: unit `43 passed`; integration `9 passed`; exact #2985 node
  `1 passed`; real merge caller coord+flat `2 passed`; regression collection
  `41/33857 tests collected` including the exact node; `ruff check` exit 0;
  `mypy` on the migration owner `Success: no issues found in 1 source file`.
- Cycle-2 baseline-red attribution: the adjacent migration/CLI/upgrade/corpus
  suites report 35 failures on this branch and the **same 35** at the merge base
  (`comm` diff empty in both directions) — all ambient `/tmp/.git`
  `PlacementMismatchError`, issue #2990. Not this WP's.

## Campsite Finding

The owned migration function is long because it separates legacy reading, deterministic
seed construction, append, and verification, but the #2985 change has a natural
pure-helper boundary at per-WP ordering. No unrelated domain-matched Sonar finding or
safe behavior-preserving cleanup was found that should precede the red-first fix.
