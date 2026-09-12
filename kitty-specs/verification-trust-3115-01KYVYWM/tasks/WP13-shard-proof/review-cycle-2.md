---
affected_files:
  - scripts/verify_shard_3115.sh
  - scripts/verify_shard_3115.recorded-output.md
cycle_number: 2
mission_slug: verification-trust-3115-01KYVYWM
reproduction_command: 'stub-interpreter replay of .worktrees/wp13-integration-probe/out/reports/probe-run3/ against scripts/verify_shard_3115.sh'
reviewed_at: '2026-08-01T12:58:46Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP13
---

# WP13 — APPROVED

Independent review, three rounds. Final commits `fd1d540180` (script) and `c9034b08c9`
(recorded output). Nothing above MEDIUM stands.

Cycle 1 in this directory is a **dependency unblock**, not a review response — it carries
`verdict: rejected` because that is the transition mechanism out of `blocked`, and it says so in its
own body. This is the first cycle recording an actual review verdict.

## What the review found, and why it mattered

WP13 is the mission's own shard proof — the artefact that certifies the other twelve packages work.
The mission's thesis is *our own verification lies to us*, and the review's governing question was
therefore whether **this script can report success for having measured nothing.**

It could. Twice.

### HIGH-1 — "all checks passed" with no input count

The PASS block claimed *"every T041 node-id resolved to a PASSED verdict line"* and never said how
many node-ids that was. The reviewer stripped all seven `check_node` call sites, left the function
and everything downstream intact, and re-ran against the real captures:

```
VACUOUS EXIT=0
PASS: both shards ran, both collected non-zero, and every T041 node-id
  resolved to a PASSED verdict line with no FAILED/ERROR/ABSENT among them.
```

Zero checks run. Identical PASS text. Exit 0. This is `standing-rules.md` verbatim — *"print the
input count alongside any 'all checks passed'"* — honoured for the shard-collection claim and
violated for the node-id claim, which is the claim the PASS line actually makes.

**Discharged.** `CHECKS_RUN` increments in `check_node`'s body; `EXPECTED_CHECKS=17` is `readonly`
next to the node-id list; the guard folds into `FAIL`. Re-measured by the reviewer with the identical
mutation: `FAIL: only 0/17 T041 node-id checks were executed.`, exit 1. The reviewer added a boundary
case the implementer had not tested — deleting exactly one call site yields `16/17`, exit 1 — proving
it is not a zero-only tripwire. `CHECKS_RUN` scope proven rather than inferred: the parent shell reads
17, 16 and 0 across the three mutations, which is impossible if the increment were lost to a subshell.

### HIGH-2 — the evidence could go missing and the proof still passed

Every extractor's failure was printed and none folded into the exit status. Two measured:

- **Blank count line** — `extract_count_line` had no sentinel and no non-zero return. Script printed
  `count line    :` and an empty line, exited **0** with PASS. **This had already happened**: the
  record itself notes the count line was blank in runs 1 and 2. A human caught it; the script did not.
  And `run_shard` tells the reader *"the collected count and the count line below are the evidence"* —
  so the script named that line as its evidence, then passed when it was empty.
- **Missing worker header** — the function returned 1 correctly, but the call site discarded the
  status. NFR-001's "worker count quoted from the run's own header, never inferred" evidence absent,
  proof reporting success.

**Discharged, all four extractors.** Each verified individually against a capture with exactly one
piece of evidence doctored out, each attributed to a single FAIL cause. The isolation case matters:
with the `platform` line kept and only `plugins:` removed, the function still returns non-zero — so
the `|| echo` fix addresses the real mechanism rather than a coincidence of both lines vanishing
together. Round 2's five controls re-run for regression; all still exit 1.

## Residuals closed in round 4

- **MEDIUM** — the round-3 replay transcript was labelled "full" but hand-condensed in four places.
  Nothing false; the reviewer independently confirmed `PASS`, `17/17`, `EXIT=0` and every quoted
  count. But round 2's finding was about *fidelity*, and the fix had traded a verbatim-but-stale
  transcript for a current-but-paraphrased one. Re-pasted byte-for-byte.
- **LOW-a** — a walked-back framing survived in the summary bullet, so a reader of that bullet alone
  got the uncorrected version. Aligned.
- **LOW-b** — a cross-reference pointing the wrong way and asserting "unchanged" about text that had
  changed. Eliminated by pasting the reconciliation inline.
- **LOW-c** — the checks-run guard was `-lt`, catching only shrinkage. Now `-ne`, which also catches
  substitution at *changed* cardinality (delete one site, add two, land on 18). The script now
  documents what neither operator catches: **substitution at constant cardinality**. `17/17` means
  seventeen checks ran; it does not mean they were *these* seventeen. A count is a cardinality check,
  never an identity check.

## Carried forward

The recorded output is a **replay**, disclosed as one — stub interpreter, named captures, probe SHA
`eef820144f`, "no new shard executed" stated before the transcript. The reviewer read the labelling
hostilely and judged that a skimmer could not come away believing a fresh shard was run.

`extract_collected_line` remains the one unfolded extractor. Not a finding: its empty case is a
strict subset of two guarded cases, so it is covered twice by construction.

## Verified independently at approval

Probe worktree clean at `eef820144f`; captures byte-identical to round 2 (`sync.out` md5
`f8d9fbfcf26758e4c1eb65e9d786455b`, `cli.out` md5 `c1795f6937b03ef7779aff29ffd6b85d`) with mtimes
predating both reviews, so no capture was regenerated to fit; round-4 diff confined to the two
deliverable files; `bash -n` clean; `FAIL=1` set inside the guard rather than logged beside it.
