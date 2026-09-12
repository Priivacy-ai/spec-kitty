# Coordination note — sibling mission `scopesource-gate-followup-01KY6S9P`

**Status:** planning note, not a binding constraint. Recorded 2026-07-23.

A sibling remediation mission runs concurrently in a separate clone
(`/home/stijn/Documents/_code/SDD/fork/spec-kitty-gate-doctrine`, branch
`fix/scopesource-gate-followup`, same base `eb06ca176`). It is TASKED and
squad-hardened (5 WPs) ahead of this mission, which is only SPECCED.

## Agreed sequencing

The sibling lands first. Rationale:

- It is further along; rebasing SPECCED work is cheaper than rebasing TASKED work.
- Its diff in the shared files is dominantly **subtractive** (~450 LoC deletion of a
  production-dead census tier in `review/pre_review_gate.py`). Rebasing additive work
  onto a deletion is easier than the reverse.
- Threading execution-context plumbing through code the sibling is about to delete
  would be wasted work and would convert their clean deletion into a conflicted one.
- Their decoupling of the `ScopeBreakdownSource` port is architecturally aligned with
  this mission's seam. A decoupled port is a better substrate for context threading,
  so waiting makes the follow-on migration cheaper.

## Scope consequence — `review/pre_review_gate.py` is OUT for this mission

None of this mission's live defects lives in that file:

| Defect | Actual home |
|---|---|
| #1834 | `acceptance/matrix.py`, `acceptance/gates_core.py` |
| #2885 | `merge/forecast.py`, `post_merge/review_artifact_consistency.py` |
| #2795 | `cli/commands/implement.py`, merge preflight |
| #2882 | acceptance write-side |

`pre_review_gate.py` appeared on the surface list only because the execution-context
seam should *eventually* cover every gate. Migrating the pre-review gate onto the seam
is a declared **follow-on consumer**, to be done after the sibling's decoupling lands.
Planning must not re-import it into this mission.

## Remaining overlap — NOT as disjoint as first assessed

**Corrected 2026-07-23 after a boy-scout audit. The original "different functions, no shared
hunk, auto-merge expected" assessment was optimistic and covered only part of the footprint.**

Exemption #7 is not a 12-line console block. Measured, it spans **~10 sites across `:1115-1632`**
in `cli/commands/agent/tasks_move_task.py`: the `new_checkout_paths` parameter, the JSON metadata
emit, a docstring, the `dirty_before` field on the `_TransitionGateInputs` dataclass, the
dirty-set capture and its threading, a second parameter and pass-through, the console emit, and
the `dirty_after - dirty_before` computation. Retiring it removes **a parameter threaded through
four function signatures and a dataclass field** — not a console block.

The overlap that matters (verified on this base):

| Ours | Sibling's WP04 | Gap |
|---|---|---|
| `dirty_before` field at `:1209`, inside `_TransitionGateInputs` (`:1199-1211`) | console-ladder region ending `:1184` | **15 lines** |
| the same dataclass | their `scope_source` reportedly flows through the **same construction site** | same declaration |

The console emit is genuinely disjoint. **The dataclass is not.** If the sibling adds a field to
`_TransitionGateInputs` while we remove one, that is a same-hunk conflict, not an auto-merge.

**Binding consequence — RE-DIFF DONE (2026-07-23, post-#2888):** exemption #7 is unblocked. The
re-diff against the landed sibling change is complete: `_TransitionGateInputs` survived the
sibling's 152-line refactor of `tasks_move_task.py` — it moved from `:1199` to **`:1172`**, and the
exemption-7 field `dirty_before` is now at **`:1182`** (`new_checkout_paths` at `:1076/:1494/:1545`).
The field is intact; only line numbers shifted. IC-07 group (f) may proceed once tasking begins.
Size the WP for the ~10-site footprint, not the console block, and confirm the line numbers again
at implement time (the sibling may see further landing folds).

## Sibling status (UPDATED 2026-07-23 — PUBLISHED)

**PR #2888 MERGED** to `upstream/main` (now at `6d9ed490d`) — *"feat(review): retire dead census
tier + SOURCE_MISMATCH + unify baseline↔head authority (#2873)"*. Our branch is rebased onto it.
The blocker is cleared. The distinction matters now that the vocabulary
is governed: their *consolidation* lands on their own mission branch and changes nothing here. It
is their *publish* to `upstream/main` that moves our base and unblocks exemption #7. Watch for the
PR, not the consolidation.

## Shared watch items

- **Compat golden — DONE.** The sibling moved `SYMBOL_TO_MODULE` 157 → **156** (landed in #2888; our base now carries 156). This mission adds
  seam symbols and must re-baseline **from 156**. Neither side may attribute a
  golden-count failure without checking who moved it last.
- **`TransitionGateContext` / `review/gate_registry.py`.** The sibling treats it as a
  read-only dependency whose signature changes ripple into their tests. Because the
  pre-review-gate migration is deferred, this mission expects to not touch it at all.
- **No pre-existing reds** (corrected 2026-07-23). Both `test_no_dead_symbols` and
  `golden_count_ban` are **green** on base `8074107d7` — verified by running them. #2825 was
  fixed upstream. The earlier claim in this note was stale; relay the correction to the sibling
  session, which was given the same stale information.
- **Reciprocal caution passed to the sibling.** This mission retires all eight
  exemption mechanisms. Behaviour moves to an owner rather than disappearing, but any
  test asserting on the *mechanism* will need updating.

## Unclaimed

**#2741** (pre-review diffs the working tree; appears already fixed by `55d060016`) is
claimed by neither mission.
