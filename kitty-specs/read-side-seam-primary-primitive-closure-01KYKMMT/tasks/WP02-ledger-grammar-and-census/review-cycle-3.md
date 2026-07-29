---
affected_files:
- path: docs/development/read-side-seam-classification.md
- path: tests/architectural/test_no_read_side_bypass.py
cycle_number: 3
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q
reviewed_at: '2026-07-28T13:05:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP02
---

**Verdict: APPROVED.** Both cycle-1 blockers are closed, verified independently
(not by reading the implementer's claims), and nothing I upheld in cycle 1
regressed. Fix commit `feb88514f`; diff is exactly the two owned files.

## Blocker 1 (FR-009 / G2 / SC-015) — CLOSED

I re-ran **both bite directions against the real ledger table**, not against the
test's own fixture:

- **New shape passes.** Injecting the three would-be `_find_meta_path`
  `primary_feature_dir_for_mission` rows into the *shipped* stay-lenient index
  parses cleanly to **26 distinct keys** (was 23). The concrete downstream
  requirement is therefore met: those three sites at `:499` / `:522` / `:543`
  can land as three distinct rows without any later WP editing this ledger's
  grammar or this gate (`tasks.md` §6).
- **Old shape reds.** The identical table reduced back to the 3-column shape
  reds through the gate's own detector:
  `DUPLICATE key ('src/specify_cli/status/aggregate.py', 'MissionStatus._find_meta_path', 'primary_feature_dir_for_mission')`.
  So the fourth column is load-bearing, not decorative.

**Token is a normalised token, not a line number in disguise.** The three
tokens are `primary_dir = primary_feature_dir_for_mission (`,
`composed_primary = primary_feature_dir_for_mission ( repo_root , bare_dir_name )`,
and `canonical_primary = primary_feature_dir_for_mission (` — distinct call
shapes, zero `file.py:NNN` anchoring. This is structurally enforced, not merely
documented: the site-token cell must equal the descriptor's own
`token_substring` by set equality, and the exactly-one-plus-key-equal staleness
twin-guard (`descriptor_still_live`) would red on any fabricated or
line-numbered token. DIRECTIVE_041 respected.

The re-authored `test_index_discriminator_represents_a_four_site_qualname` now
exercises `_assert_no_duplicate_keys` directly and pins the collapse
(`len(set(old_shape_keys)) == 2`), replacing the cycle-1 `as_allow_key()`
assertion that was true with or without the fix.

## Blocker 2 (T010.3 / NFR-008) — CLOSED

End-state counts are declared (`resolve_feature_dir_for_mission`:
`migrate-fail-loud 0`, `Total 7 / 6`; `primary_feature_dir_for_mission`:
`expected-red 0 / 0`, `Total 3 / 2`), with the deliberate reconciliation red
recorded and **WP08** named as greening owner (also in
`research/expected-reds.md` § WP02, commit `c135de0d0`).

**NFR-008 both directions hold.** The historical pre-migration record is
preserved verbatim under its own heading (90 / 54, 60-file census) and the
in-flight audit figures are preserved too, in § "Method (WP02 this revision)"
(`resolve_feature_dir_for_mission 8 / 7`, `primary_feature_dir_for_mission
34 / 19`). No figure was rewritten to make a check pass.

**The exemption is narrowly KIND-scoped — mutation-proved, four ways:**

| Mutation | Result |
|---|---|
| third mismatch on a non-exempt primitive (`candidate` total +2) | RED (unexpected mismatch) |
| exempt primitive, verdict-sum break (`expected-red` 0 → 9) | RED |
| exempt primitive, stay-lenient break (0 → 9) | RED |
| expected red REMOVED (as-of-now counts silently restored) | RED (presence assertion) |

The prefix `"<primitive>: ledger declares"` matches only the two live-census
error forms; the stay-lenient, sanction-infra, verdict-sum and missing-row
errors all carry different prefixes and still bite on all four primitives.
A silent revert to as-of-WP02 counts cannot pass.

## Item 3 — the mutation-test vacuity claim, audited

The proactive hardening is **genuine and non-vacuous for all four primitives**;
one vacuity was not traded for another.

- Each primitive's row is located by a regex anchored on its own trailing
  `primitive` cell and resolves **under the live-census heading** (never the
  3-column historical table) — I confirmed the matched row for each.
- Each mutation yields exactly **2 new errors, both naming that primitive**
  (stay-lenient count + verdict-sum), including for the two primitives that
  carry persistent baseline reds.
- **Neutering the reconciler to always return the baseline reds REDS all four**
  — so the new-error *diff*, not bare truthiness, is what carries the test.
- **Injecting a new error that does not name the primitive REDS all four** — so
  the primitive-name check bites too.

## Reconciliation / no regressions

Exactly **32 offenders** (31 `primary_feature_dir_for_mission` + 1
`decisions/emit.py:71`), item-for-item as recorded. Ratchet intact: allow-list
still 23 entries, `primary_feature_dir_for_mission` stay-lenient still `0 | 0`,
zero unrouted sites pre-populated. All six G1 grammar tests still pass.
`50 passed, 1 failed` (the expected ratchet red). `ruff` exit 0; terminology
guard 4 passed; working tree clean; diff exactly the two owned files.

## Non-blocking (do not reject; fold when convenient)

1. **New `mypy --strict` error in the changed file.**
   `tests/architectural/test_no_read_side_bypass.py:1787` —
   `Argument 1 to "_assert_no_duplicate_keys" has incompatible type
   list[tuple[str, str, str]]; expected list[tuple[str, ...]]` (list
   invariance). This is new code from `feb88514f`. It is **outside** the gated
   scope — CI runs `mypy --strict src/specify_cli src/charter src/doctrine`, and
   that job is advisory — so nothing is red because of it, but the "mypy no
   issues in 1088 files" claim did not cover this file. Fix is one annotation:
   `old_shape_keys: list[tuple[str, ...]] = [row[:3] for row in synthetic_rows]`.
2. **Residual looseness inside the exemption (for WP08).** Because check #4 is
   fully waived for the two exempt primitives, an arbitrary but internally
   consistent end-state total passes: rewriting `primary` `Total 3 | 2` to
   `8 | 6` with `expected-red 5 | 4` reconciles green. The `migrate-fail-loud`
   and `expected-red (unrouted)` buckets carry no independent authority, so
   nothing pins them while the live-census closure is suspended. This is
   inherent to waiving a check — and real unrouted sites are independently
   caught by the 32-offender ratchet — but when WP08 greens these rows it should
   restore the closure rather than just make the numbers agree. An optional
   interim tightening would be asserting the declared total *converges* (declared
   < live) for the exempt primitives.

## Reproduction

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty/.worktrees/read-side-seam-primary-primitive-closure-01KYKMMT-lane-b
PWHEADLESS=1 uv run pytest tests/architectural/test_no_read_side_bypass.py -q
# 50 passed, 1 failed (the 32-offender expected red) -- correct as designed.
```
