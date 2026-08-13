---
affected_files: []
cycle_number: 2
mission_slug: worktree-owned-root-3328-01KZRG01
reproduction_command:
reviewed_at: '2026-08-11T15:32:59Z'
reviewer_agent: user
wp_id: WP01
---

The experimental probe confirms a boundary violation. Here's the superseding verdict.

**Reviewer identity:** OpenRouter Kimi  
**Reviewed commit:** `2d1721c24c4394aee5cbf8b02cd28377fe0be100` (ancestor of lane HEAD, file unchanged)

**Exact probe executed (real temporary git repos, lane `.venv`/source):**
1. Created a real git repo `primary` with initial commit.
2. Created subdirectory `primary/pkg/sub` (no `.git` dir, not a checkout root).
3. Called `resolve_ownership_claim(subdir, resolved_primary=primary)` and `is_worktree_of(primary, subdir)`.
4. Created linked worktree `linked` + subdirectory `linked/inner/deep`.
5. Called `resolve_ownership_claim(linked_subdir, resolved_primary=primary)` and `is_worktree_of(primary, linked_subdir)`.

**Observed values:**
- `primary-subdir`: `resolve_ownership_claim` → `result='OWNED'` `opted_in=True`
- `primary-subdir`: `is_worktree_of` → `True`
- `linked-subdir`: `resolve_ownership_claim` → `result='NESTED'` `opted_in=True` (detail names registered worktree)
- `linked-subdir`: `is_worktree_of` → `True`

**Blocker:** `resolve_ownership_claim` in `src/specify_cli/core/checkout_ownership.py` does not verify that the *claimed path itself* is a git checkout root. It relies on `is_worktree_of` (common-dir match) and the worktree registry (nested-worktree detection). A plain subdirectory inside the primary checkout shares the primary's common dir and is not nested inside any *other* registered worktree, so it passes through to `OWNED`. This violates the explicit contract that an explicit checkout scope succeeds only when the claimed path is the current validated checkout ROOT.

**File / line:** `src/specify_cli/core/checkout_ownership.py`, `resolve_ownership_claim`, approximately lines 99–140 (the `belongs_to_primary` True branch).

**Missing regression test:** `tests/core/test_checkout_ownership.py` has no test asserting that a subdirectory inside the primary checkout is refused. The existing NESTED test only covers a worktree nested inside another *registered* worktree, not a non-checkout subdirectory inside the primary checkout.

**Required behavior (not implementation prescription):** Any claimed path that is not itself a git checkout root (i.e. `git rev-parse --show-toplevel` from that path does not equal the claimed path) must not produce `OwnershipValidationResult.OWNED`, regardless of whether it resides inside the primary checkout or a linked worktree. The validation boundary must treat such claims as invalid ownership.

**Prior APPROVE superseded explicitly:** This focused review is mandatory and supersedes the prior verdict for this question. The prior approval did not experimentally disposition the primary-subdirectory concern.

---

`VERDICT: REQUEST_CHANGES`

## Governed evidence correlation

- Reviewer profile / Op: `reviewer-renata` / `01KZRNH7WBH5CCY3EZA8TP5WF0` (closed `done` after verdict)
- Harness: Prime Agent `0.7.1`; OpenRouter `~moonshotai/kimi-latest`; thinking `high`; JSONL; `--no-session`; required appended communication system prompt
- Provider response identities observed: `moonshotai/kimi-k3`, `moonshotai/kimi-k2.6`
- Initial incomplete APPROVE raw: `/tmp/core-3328-wp01-prime.jsonl`, SHA-256 `47cf915f92d1267b8dfbb35fb79c068dc09006c73043b15fb94c8f5f3f4c51c8`
- Initial condensed output: `/tmp/core-3328-wp01-prime-final.md`, SHA-256 `eb813954a2a6a39bf580330fed35ba2b6b627fa1ee1c1d2ce75c89c0af440c8e`
- Focused superseding raw: `/tmp/core-3328-wp01-prime-subdir.jsonl`, SHA-256 `d7bb71765638f347488ea33178c513376c8c8b8e1b4a3e7e5a7a30aa48be3260`
- Focused condensed output: `/tmp/core-3328-wp01-prime-subdir-final.md`, SHA-256 `458de23af06d2fc5e10388f05de2afe3adba5dec982b4021652a4de481c97f81`

Raw JSONL remains outside git history under `/tmp`; this review-cycle artifact is the durable condensed proof.
