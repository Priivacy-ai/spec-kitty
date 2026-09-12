# The CI baseline this PR lands on

Built from the two `CI Quality` runs on `bb2020fea924d6e5b157974f27a7cab1a77ad259` — the SHA this
mission branched from — before opening the PR. Its purpose is narrow and specific: **to make "no new
red is attributable to this PR" a checkable claim rather than an impression.**

| Run | Trigger | When |
|---|---|---|
| [`30681941495`](https://github.com/Priivacy-ai/spec-kitty/actions/runs/30681941495) | schedule | 2026-08-01T03:24:54Z |
| [`30621215287`](https://github.com/Priivacy-ai/spec-kitty/actions/runs/30621215287) | push | 2026-07-31T09:47:27Z |

Two runs on one commit is the whole point of the exercise: it separates stable failures from flakes,
which a single run cannot do.

## The shape of it

**41 distinct failing node-ids** in the union. **39 are stable** — identical in both runs, same
job(s). The only instability is the `#3136` sleep-pollution class, which lands on a different victim
each run, exactly as `#3136` itself predicts.

| Class | Count | Meaning |
|---|---|---|
| ATDD-red — open issue, test is its marker | 11 | expected; `#2996`, `#3045`, `#3086`, `#2782`, `#3092` |
| environmental — shard isolation, tracked by open `#3115` | 12 | expected; not product defects |
| mission's own expected red — `#3136` | 3 (2 per run) | filed by this mission |
| regression against a **closed** issue | 1 | **filed as #3138** |
| unfiled | 18 | **filed as #3139 (14) and #3140 (4)** |

## What this means for the PR

**`tests/architectural/` is clean on the baseline.** No failures under that path in either run; all
three `arch-adversarial` shards green. This mission adds tests there, so any red under
`tests/architectural/` on the PR is **mine** and must be treated as such.

**`tests/sync/` is not clean, and the reds there have owners.** The `_3030`/`h4` consent files
(`#3115`), `test_strict_json_stdout.py` (`#2782`), and the `test_saas_client*` pair (`#3136`). This
mission adds a leak guard to `tests/sync/conftest.py`, so the attribution question is live — but it
is answerable: the guard tags every error it raises with `[FR-007 leak guard]`. A red in that cone
**without** the tag is baseline; with the tag, it is mine.

## The correction that mattered most

The 12 consent-test reds were initially classified as a **regression** against closed `#3030`, on the
reasoning that the test files are named `_3030` and that issue is closed. That was wrong, and the
correction is worth recording because the wrong version was mine.

`#3115`'s body names all six of those files as a known shard-isolation victim class. The tracking
issue is `#3115` (open), not `#3030` (closed) — a keyword search for `consent_write_refusal` finds
nothing because the tracking issue contains neither the filename nor the test name.

**This does not orphan them when the PR lands.** `issue-matrix.json` records `#3115` as
`deferred-with-followup`, not `fixed`, because the sync half did not resolve. The row's own scope
text is explicit that a partial resolution takes the whole row to deferred: *"the issue is one defect
report and it is not closed while one of its named affected tests is unexplained. A green shard does
not close it (that is the exact path that produced 578a659162)."* So `#3115` stays open and keeps
carrying them.

## One claim this mission must not make

**The PR does not green those 12.** They are a *different* defect from the one this mission fixed.

The mission's CLI fix is the render-width fold: rich returns `(80, 25)` from the `is_dumb_terminal`
branch, and uuids fold in an `overflow=fold` column. The consent-test failures show a **complete,
well-formed panel** reporting an empty queue —

```
Sync Doctor  Queue size 0 / 100,000 (0%)  Oldest event n/a (empty)  Queue DB /tmp/…
```

— with head and tail both intact. That is a data problem (the command resolves a different, unseeded
journal under shard pollution), not a rendering problem. A render-width defect would show a
*populated* panel with folded paths.

Worth stating separately, because it is a trap this mission has already fallen into once: the `...`
in those assertion dumps is **pytest's own middle-elision of a long repr**, not evidence that the CLI
truncated anything. Reading it as truncation would have manufactured a false confirmation of the
mission's own thesis. Checked, and it is not one.

## The four-job blackout

`fast-tests-sync` has failed on **13 consecutive push/schedule runs** since 2026-07-28T05:10, taking
four jobs to `skipped` with it: `fast-tests-status`, `integration-tests-sync`,
`integration-tests-sync-real-port`, and `integration-tests-status` (the last as a second-order
cascade — `fast-tests-status` was *skipped*, and `== 'success'` cannot tell a skip from a failure).

Filed as `#3127`; its streak count and casualty list were both stale, corrected in
[a comment](https://github.com/Priivacy-ai/spec-kitty/issues/3127#issuecomment-5151454066).

**Consequence for this PR, stated plainly: those four jobs contribute no baseline.** If this PR turns
one of them green→red, the comparison that would reveal it does not exist. That is a known,
unclosable gap in the un-draft evidence, not something to be talked around.

## The standard being applied

The operator's instruction was to un-draft once CI is green. `main` has not had a clean push/schedule
run in ~4 days and 263 commits, so green in the literal sense is unavailable and waiting for it would
mean waiting on five unrelated issues.

The operative standard is therefore: **un-draft when no new red is attributable to this PR** — every
red on the PR matches this baseline by node-id, or is one of the mission's own expected reds. If a
red appears that cannot be attributed to either, the PR stays a draft and the specific ambiguity goes
to the operator rather than being resolved by inference.

---

*Full per-node-id table, with job, assertion text, stability and issue linkage, is in the baseline
inventory this file summarises. Raw failed-log captures for both runs were retained for the session
that produced it.*
