---
affected_files:
- path: src/specify_cli/migration/backfill_runtime_state.py
- path: tests/unit/migration/test_backfill_runtime_state.py
- path: tests/regression/baselines/issue_2985_red_first.md
cycle_number: 3
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: PWHEADLESS=1 python -m pytest tests/unit/migration/test_backfill_runtime_state.py::test_missing_raw_claim_witness_cannot_be_masked_by_expected_event_builder
  -q
reviewed_at: '2026-07-27T15:24:00Z'
reviewer_agent: claude
verdict: approved
wp_id: WP01
---

# WP01 Review Cycle 3 (second human-reviewed cycle)

## Numbering note

This is the **second reviewed cycle**, not the third. `review-cycle-2.md` was
already occupied by a machine-generated restatement of cycle 1: it carries
`reviewer_agent: unknown`, `verdict: rejected`, and a body whose heading still
reads "WP01 Review Cycle 1" — it is the runtime's echo of the cycle-1 rejection,
not an independent review. Earlier artifacts are immutable, so this cycle-2
verdict is filed as `review-cycle-3.md`. See tracker #2996 for the underlying
artifact defect.

## Verdict

**Approved.** The cycle-1 blocking finding is genuinely fixed. I independently
reproduced the builder/verifier tautology on the cycle-1 tree and confirmed it
is closed at cycle-2 HEAD, on both denominator branches. All gates re-run by me
are green, and the adjacent-suite failing-node set is byte-identical to the
base — zero introduced, zero masked.

## A. Denominator independence — PASS

`_claim_witness_denominator` (`backfill_runtime_state.py:1372`) consumes exactly
four inputs, and every one traces back to a primary source rather than to
builder output:

| Input | Origin | Builder-reachable? |
|---|---|---|
| `legacy` | `read_legacy_runtime(read_dir)` (`verify_backfill:1533`) | No |
| `anchors` | `_claim_anchors(feature_dir)` (`verify_backfill:1554`) | No — skips `_is_migration_actor` rows |
| `read_dir` | caller argument | No |
| `stream` | `read_event_stream(feature_dir)`, used **only** via `_wp_history_floor` | No — `_wp_events(..., include_repairs=False)` filters `_is_migration_actor`, which covers both `BACKFILL_ACTOR` and `COMPATIBILITY_REPAIR_ACTOR` |

The `stream` path was the one worth chasing, since the post-backfill stream does
physically contain builder-emitted rows. It is laundered: `_wp_history_floor`
reaches the stream only through `_wp_events(stream, wp_id, include_repairs=False)`,
whose final line is

```python
return [event for event in events if not _is_migration_actor(event.actor)]
```

so every seed the builder wrote is excluded before the floor is computed. A
builder that suppresses claim transitions cannot shrink the denominator.

The one remaining `continue` is `anchor is None`, and it is contract-correct
rather than an escape hatch: it fires only when the WP has no legitimate history
**and** `_resolve_anchor` finds neither an event-log anchor nor a synthesizable
frontmatter timestamp. That resolution reads frontmatter and `meta.json`, never
builder output, so it is not builder-controllable.

**No false-positive risk either.** The witness demand condition is exactly
congruent with the builder's emit condition, independently re-derived:

- builder (`_build_seed_events:738`): `if runtime.shell_pid is not None or runtime.agent is not None or runtime.shell_pid_created_at is not None:`
- witness (`_claim_witness_denominator:1393-1398`): non-empty `claim_slots` over `_CLAIM_SLOTS`

Both gate on the same `_resolve_seed_anchor`. The witness mirrors the builder's
*contract*, re-derived from primary inputs — not the builder's *output*. That is
precisely the remediation cycle 1 asked for.

## B. Anti-disable mutation — PASS (reproduced independently)

I did not run the implementer's test for this. I wrote my own script from the
cycle-1 rejection text and ran the identical script against both trees.

At **cycle-1** (`2e0aed884^` = `460de7769`):

```
[0] post-backfill baseline (no mutation): VerifyResult(ok=True, wp_count=1, mismatches=())
[C] CONTROL mutation-only, claim seed intact: VerifyResult(ok=True, wp_count=1, mismatches=())
[B] rows before=7 after=6 (claim seed removed)
[B] surviving migration annotation seeds: 4
[B] _has_snapshot_runtime(WP01) after deletion: True
[B] RESULT verify_backfill(): ok=True wp_count=1

VERDICT: MUTATION PROOF FAILED
  - ANTI-DISABLE FAILED: verify_backfill returned VerifyResult(ok=True, wp_count=1, mismatches=())
```

This reproduces the cycle-1 observation verbatim, including
`VerifyResult(ok=True, wp_count=1, mismatches=())`.

At **cycle-2 HEAD**:

```
[0] post-backfill baseline (no mutation): VerifyResult(ok=True, wp_count=1, mismatches=())
[C] CONTROL mutation-only, claim seed intact: VerifyResult(ok=True, wp_count=1, mismatches=())
[B] rows before=7 after=6 (claim seed removed)
[B] surviving migration annotation seeds: 4
[B] _has_snapshot_runtime(WP01) after deletion: True
[B] RESULT verify_backfill(): ok=False wp_count=1
      mismatch: WP01: raw claim-slot witness missing for agent (deterministic claim seed absent)
      mismatch: WP01: reduced claim-slot witness for agent does not match legacy seed
      mismatch: WP01: raw claim-slot witness missing for shell_pid (deterministic claim seed absent)
      mismatch: WP01: reduced claim-slot witness for shell_pid does not match legacy seed
      mismatch: WP01: raw claim-slot witness missing for shell_pid_created_at (deterministic claim seed absent)
      mismatch: WP01: reduced claim-slot witness for shell_pid_created_at does not match legacy seed
[B] slots named by the witness: ['agent', 'shell_pid', 'shell_pid_created_at'] / ['agent', 'shell_pid', 'shell_pid_created_at']

VERDICT: MUTATION PROOF PASSED (control inert; deletion caught by the witness)
```

The failure is attributable to the missing witness, not to an incidental error:
the script asserts `"raw claim-slot witness missing"` appears and that every
non-null slot is named. `_has_snapshot_runtime(WP01)` is still `True` after the
deletion, so the coarse count-parity guard stays silent — only the per-slot
witness can catch this.

**Second probe — the other denominator branch.** The implementer's test uses
`build_mission()`, where the WP has legitimate history and the denominator
resolves through `_wp_history_floor`. I added a probe covering the
synthesized-anchor branch (`with_transitions=False`) and total builder
suppression (no transitions *and* no annotations). At HEAD all three scenarios
correctly returned `ok=False` with three missing-witness mismatches each; at
cycle-1 all three returned `ok=True` with zero. The fix holds on both branches,
and the cycle-1 hole was present on both.

## C. Control assertion — PASS

Verified in my own script, independently of the implementer's. With
`_build_seed_events` monkeypatched to return no transition seeds but the claim
seed still present on disk, `verify_backfill()` returns
`VerifyResult(ok=True, wp_count=1, mismatches=())` at HEAD. The mutation alone is
inert, so the red in item B is caused by the deleted claim seed and not by the
monkeypatch. The control also held in all three probe-2 scenarios.

## D. `_resolve_seed_anchor` extraction — PASS (behavior-preserving)

Old, inline in `_build_seed_events`:

```python
floor = _wp_history_floor(stream, wp_id)
if floor is None:
    anchor, synthesized = _resolve_anchor(read_dir, wp_id, runtime, anchors)
else:
    anchor, synthesized = floor, False
```

New, extracted:

```python
floor = _wp_history_floor(stream, wp_id)
if floor is not None:
    return floor, False
return _resolve_anchor(read_dir, wp_id, runtime, anchors)
```

Logically identical — same call order, same arguments, same `(anchor, synthesized)`
tuple, same `MigrationOrderingError` propagation from `_wp_history_floor`. The
inverted conditional is the only textual change. Migration eligibility is
unaffected.

I also checked whether reusing this helper inside verification widens the
exception surface, since `_wp_history_floor` can raise on a malformed or naive
timestamp. It does not: `verify_backfill` already calls `_build_seed_events`
(line 1581) *before* `_verify_claim_slot_witnesses` (line 1598), and the builder
runs `_resolve_seed_anchor` over **all** of `legacy`, whereas the witness runs it
over the subset with claim slots. The witness's raise surface is a strict subset
of one that already executed. No new failure mode.

## E. Later-legitimate-writer snapshot semantics — PASS (unchanged)

I extracted the tail of `_verify_claim_slot_witnesses` from the cycle-1 tree via
`inspect.getsource` and compared. The block is byte-identical:

```python
later_value = legitimate.get(slot)
expected_value = (later_value if later_value is not None else legacy_value)
if actual.get(slot) != expected_value:
    owner = ("later legitimate writer" if later_value is not None else "legacy seed")
    mismatches.append(f"{wp_id}: reduced claim-slot witness for {slot} does not match {owner}")
```

`test_claim_slot_witness_allows_later_legitimate_writer` remains green.

## F. Dead code — PASS

Chain verified by grep, and the callers are real and live:

- `_resolve_seed_anchor` ← `_build_seed_events:720` and `_claim_witness_denominator:1400`
- `_claim_witness_denominator` ← `_verify_claim_slot_witnesses:1439`
- `_verify_claim_slot_witnesses` ← `verify_backfill:1599`
- `verify_backfill` ← `runtime_state_cutover._verify_phase:121` → `cutover_mission`, which is reached from `merge/executor.py:997` (merge bake), `upgrade/migrations/m_zz_runtime_state_backfill.py:221`, `cli/commands/migrate_cmd.py:868` and `:870` (single + corpus), `cli/commands/accept.py` via `stamp_accept_cutover`, and `cli/commands/_cutover_doctor.py:110`
- `verify_backfill` ← `status/cutover_eligibility.py:250` → `is_cut_over` → `cli/commands/cutover_guard.py:147`

One correction to the implementer's evidence file, non-blocking: it lists
`status/cutover_eligibility.py:303` as a production caller. That site is inside
`assert_birth_invariant_holds`, whose only callers are in
`tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` — it is a
test-facing corpus gate, not a production path. It is also pre-existing at the
base, so it is not dead code introduced by this WP. The two genuinely production
callers (`:121` and `:250`) are sufficient.

## Gates (all re-run by me, verbatim)

```
tests/unit/migration/test_backfill_runtime_state.py        43 passed in 40.81s
tests/integration/test_migration_backfill.py                9 passed in 38.45s
exact #2985 node                                            1 passed in 38.97s
  tests/regression/test_birth_cutover.py::test_issue_2985_birth_cutover_preserves_every_wp_lane_and_repairs_old_seed
real merge caller (coord + flat)                            2 passed in 38.88s
  tests/regression/test_birth_cutover.py::test_birth_cutover_reconciles_at_merge_no_manual_backfill
pytest tests/ -m regression --collect-only -q
                        41/33857 tests collected (33816 deselected) in 56.65s
  grep -c '<exact #2985 node>' -> 1   (node IS selected by the blocking marker)
ruff check (diff-scoped, base kitty/mission-annoying-bugs-sweep-01KYHQ9F)
  src/specify_cli/migration/backfill_runtime_state.py
  tests/integration/test_migration_backfill.py
  tests/regression/test_birth_cutover.py
  tests/unit/migration/test_backfill_runtime_state.py
                        All checks passed!   (exit 0)
mypy src/specify_cli/migration/backfill_runtime_state.py
                        Success: no issues found in 1 source file
```

I confirmed pytest resolves the lane worktree's own `src/` and not the ambient
editable install (which points at a sibling `spec-kitty` checkout):
`backfill_runtime_state.py` resolved to the lane path with
`_claim_witness_denominator` present.

## Baseline-red attribution (independently measured)

Adjacent suites — `tests/unit/migration/`,
`tests/integration/test_migration_backfill.py`,
`tests/regression/test_birth_cutover.py`,
`tests/regression/test_corpus_frontload_idempotent.py`,
`tests/specify_cli/migration/`,
`tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py`,
`tests/specify_cli/cli/test_accept_birth_cutover.py`,
`tests/specify_cli/cli/commands/test_cutover_doctor.py` — run at lane HEAD and
at base `kitty/mission-annoying-bugs-sweep-01KYHQ9F` (`8bd056190`) in a
throwaway worktree:

```
HEAD: 34 failed, 307 passed in 146.40s
BASE: 34 failed, 296 passed in 152.76s

INTRODUCED (red at HEAD, green at base):  0
MASKED    (red at base, not red at HEAD):  0
COMMON    (pre-existing):                 34
```

The +11 passed delta is fully accounted for: `git diff base..HEAD -- tests/`
adds exactly 11 new test functions. No test vanished or was silently skipped.

All 34 pre-existing failures are the ambient `/tmp/.git` marker (issue #2990).
Confirmed by re-running a representative node:

```
specify_cli.migration.runtime_state_cutover.PlacementMismatchError: _flip_phase refuses
to write status_phase for 'legacy-birth-first': the placement port resolved its PRIMARY
home to /tmp/kitty-specs/legacy-birth-first, which does not match the write target
/tmp/pytest-of-stijn/.../kitty-specs/legacy-birth-first (fail-closed, FR-001).
```

`/tmp/.git` exists on this machine, which is the #2990 precondition. WP01 cannot
be the cause: `git diff --name-only base..HEAD -- src/` returns exactly one file,
`src/specify_cli/migration/backfill_runtime_state.py`, and the diff against
`runtime_state_cutover.py` (which owns `_flip_phase` and `PlacementMismatchError`)
is zero lines.

Minor note: the implementer's evidence file reports "35 failed / 214 passed". My
selection is broader, hence 34/307. Different denominators, same conclusion —
I did not rely on the implementer's numbers.

## Ownership

WP01's three authored commits (`ef7d0627a`, `6934ce582`, `2e0aed884`) touch only
`src/specify_cli/migration/backfill_runtime_state.py`,
`tests/unit/migration/test_backfill_runtime_state.py`,
`tests/integration/test_migration_backfill.py`,
`tests/regression/test_birth_cutover.py`, and
`tests/regression/baselines/issue_2985_red_first.md` — all within `owned_files` /
`create_intent`. The `status.events.jsonl` (-6) and `status.json` (±40) deltas
visible in `git diff base..HEAD` come solely from the four lane merge commits and
belong to WP03/WP05 coordination traffic the lane has not yet re-merged. They are
not WP01 edits and are not an append-only violation.

## WP Anti-Pattern Checklist

1. **Dead code** — PASS. Full chain to two live production callers verified above.
2. **Synthetic-fixture test** — PASS. This was the cycle-1 FAIL. The anti-disable
   node now discriminates: red on the cycle-1 tree, green on cycle-2, with a
   control proving the mutation is inert. Verified with my own script, not the
   implementer's.
3. **Silent empty return** — PASS. The two `continue` statements in
   `_claim_witness_denominator` are the empty-claim-slots case and the
   contractually-un-seedable case; the latter carries an explicit docstring
   rationale.
4. **FR coverage** — PASS. The independent-witness portion of C-002 / FR-003 /
   FR-005 (cycle-1 FAIL) is now covered by a discriminating test.
5. **Frozen surface** — PASS.
6. **Locked decision** — PASS. No reducer change (`_should_apply_event` untouched),
   no seed suppression, no new writer, no reducer-precedence change.
7. **Shared-file ownership** — PASS. Single production file, disjoint from other WPs.
8. **Production fragility** — PASS. Cycle 2 adds no new `raise`; the verification
   raise surface is a strict subset of one that already ran earlier in the same call.

## Non-blocking observations

1. `_resolve_seed_anchor` calls `_wp_history_floor` once per WP in the builder and
   again per claim-slot WP in the witness, so a corpus-wide verify walks the
   stream roughly twice. Correct, and immaterial at mission scale, but worth
   remembering if corpus mode is ever run over a very large corpus.
2. The evidence file's "production caller" claim for
   `cutover_eligibility.py:303` is inaccurate (test-facing corpus gate). Cosmetic;
   the real production callers are verified.
