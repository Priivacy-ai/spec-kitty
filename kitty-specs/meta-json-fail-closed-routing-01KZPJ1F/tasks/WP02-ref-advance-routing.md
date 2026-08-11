---
work_package_id: WP02
title: ref_advance routing + comparator unification (atomic)
dependencies:
- WP01
requirement_refs:
- C-005
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-004
planning_base_branch: feat/meta-json-l1-seam-routing-3259
merge_target_branch: feat/meta-json-l1-seam-routing-3259
branch_strategy: Planning artifacts for this mission were generated on feat/meta-json-l1-seam-routing-3259. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-json-l1-seam-routing-3259 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
history:
- at: '2026-08-10'
  note: Authored by /spec-kitty.tasks (post-plan-squad model).
agent_profile: python-pedro
authoritative_surface: src/specify_cli/git/ref_advance.py
create_intent:
- tests/specify_cli/git/test_ref_advance_meta_diagnosability.py
execution_mode: code_change
owned_files:
- src/specify_cli/git/ref_advance.py
- tests/specify_cli/git/test_ref_advance_meta_diagnosability.py
- tests/specify_cli/cli/commands/test_issue_2795_claim_blocker.py
- tests/architectural/test_layer_rules.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Apply it, then read this WP, `spec.md` (US1/US2, FR-003/004/005/006/007, NFR-004, C-005), `data-model.md` (sites A/B rows + error-translation table), and `research.md` (D6/D7). WP01 must be merged first (you consume `kernel.meta_decode` + `kernel.vcs_lock`).

## Objective

Route ref_advance's two `meta.json` reads (site A `_meta_change_is_vcs_lock_only`, site B `_committed_meta_object`) fail-closed onto the kernel L1, delete the private parser, and switch ref_advance onto the **kernel comparator** (absent≠null). This is **one atomic unit** — deleting `_parse_meta_object` breaks its in-module callers, so the deletion and the rewiring land together. **Census-neutral**: you route onto `decode_meta` (not in `ROUTED_CALLEES` until WP05); do not touch the floor.

`git/ref_advance.py` currently imports **zero** `specify_cli` modules (verify: `grep -nE "^\s*(from|import)\s+specify_cli" src/specify_cli/git/ref_advance.py`). Adding `from kernel.meta_decode import decode_meta, MetaDecodeError` and `from kernel.vcs_lock import is_vcs_lock_only_change, VCS_LOCK_META_FIELDS` is a legal downward import; the layer test only forbids `kernel → specify_cli`.

### Subtask T007 — Delete the private parser + local comparator/field-set

In `src/specify_cli/git/ref_advance.py`: delete `_parse_meta_object` (~:181), `_VCS_LOCK_META_FIELDS` (~:42), and `_is_vcs_lock_only_meta_change` (~:210). Import the kernel decode + comparator symbols. (This is atomic with T008 — the tree is non-importable in between.)

### Subtask T008 — Route sites A and B onto kernel L1

- **Site B `_committed_meta_object` (~:192)**: `git show HEAD:path` stdout `str`. Route the parse to `decode_meta(stdout, on_malformed="raise")`. **The absent-at-HEAD arm stays benign**: when `git show` returns `returncode != 0` (path absent at HEAD, ~:204-207), keep returning benign `{}`/existing sentinel — only a **present-but-unparseable** committed blob raises `MetaDecodeError`.
- **Site A `_meta_change_is_vcs_lock_only` (~:231)**: reads the worktree `meta.json` (~:247) — route to `decode_meta`; and calls site B for the committed side. Switch its comparison to `is_vcs_lock_only_change(committed, worktree)` (kernel comparator).
- ref_advance must reach `MetaDecodeError` without importing `specify_cli` — it's kernel-resident, so this holds.

### Subtask T009 [P] — NFR-004 ratchet

In `tests/architectural/test_layer_rules.py`, add a **bespoke AST scan** asserting `src/specify_cli/git/ref_advance.py` imports **zero** `specify_cli` modules. Mirror the existing `TestRuntimeBoundary` pattern (~:341-354) — do NOT use a pytestarch `LayerRule` (ref_advance lives inside the `specify_cli` layer, so a layer rule can't express it). This ratchets C-003 so the plumbing boundary cannot silently regress.

### Subtask T010 — Red-first A/B diagnosability tests

Create `tests/specify_cli/git/test_ref_advance_meta_diagnosability.py` with `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` (ref_advance shells out to real `git show`; register in `tests/_next_shard_map.py` only if it lands under `tests/runtime` — it does not, so path-routing suffices). Assert per site:
- corrupt committed/worktree `meta.json` → `pytest.raises(MetaDecodeError, match="meta.json")` (name the `ref:path` for the committed read);
- **C-005 verdict**: a present-but-`null` `vcs_locked_at` vs absent → `is_vcs_lock_only_change` returns the new deterministic verdict (distinguishes them);
- absent-at-HEAD committed → benign `{}` (no raise);
- valid `meta.json` → pre-routing verdict unchanged (FR-005 happy path).

**Capture proof-of-red**: run the corrupt-arm tests against the pre-T007 tree (they’re red because ref_advance silently absorbs) and save that output in your WP notes before routing.

### Subtask T011 — Retarget test_issue_2795_claim_blocker.py

`tests/specify_cli/cli/commands/test_issue_2795_claim_blocker.py:62-63` imports `_is_vcs_lock_only_meta_change` + `_parse_meta_object` and `:300` asserts `_parse_meta_object("{not json") is None`. Retarget: import the kernel comparator + `decode_meta`; rewrite the `is None` assertion to `pytest.raises(MetaDecodeError)` (or `decode_meta(..., on_malformed="none") is None` for the silent-mode unit). Keep the claim-blocker behavior assertions intact.

### Subtask T012 — Confirm importable + census-neutral + green

- `python -c "import specify_cli.git.ref_advance"` succeeds.
- Measure census — must be unchanged vs WP01's end state (routing onto `decode_meta` is uncounted). Do NOT edit `ROUTED_CALLEES`/floor.
- Run: `PWHEADLESS=1 python -m pytest tests/specify_cli/git/test_ref_advance_meta_diagnosability.py tests/specify_cli/cli/commands/test_issue_2795_claim_blocker.py tests/architectural/test_layer_rules.py tests/architectural/test_inline_meta_read_gate.py -q` → green.

## Branch Strategy

Base + merge target: `feat/meta-json-l1-seam-routing-3259`. Worktree per computed lane from `lanes.json`. Depends on WP01 — `spec-kitty implement WP02` branches from the correct base.

## Definition of Done

- `_parse_meta_object` + local field-set + local comparator deleted; kernel symbols imported; ref_advance importable.
- Sites A/B route onto kernel L1; absent-at-HEAD benign; present-but-corrupt fails loud naming meta.json.
- NFR-004 ratchet added and green; `test_issue_2795_claim_blocker` retargeted and green.
- **Git-verifiable red-first**: commit the A/B diagnosability test in a commit that PRECEDES the routing commit, so `git show <routing-parent>:...` proves the corrupt-arm test existed and was red before the fix (proof-of-red is a git artifact, not WP-notes prose).
- **Tests provably ran**: run the diagnosability file with `-rs` and confirm the named corrupt-arm tests show `passed` (nonzero), **0 unexpected skips** — a `git_repo`-fixture skip must not vacuously satisfy "green".
- **Census-neutral, proven**: grep that ref_advance's new decode callee is `decode_meta` and is NOT any `ROUTED_CALLEES` member; the reviewer independently re-runs the census one-liner and confirms it is unchanged vs WP01's end state (do not trust self-recorded numbers). No `ROUTED_CALLEES`/floor change.
- `ruff` + `mypy --strict` clean.

## Reviewer guidance

Verify: ref_advance imports 0 `specify_cli` (and the ratchet enforces it); the committed absent-at-HEAD arm still returns benign `{}`; the C-005 verdict flip is asserted, not accidental; proof-of-red captured; census untouched.
