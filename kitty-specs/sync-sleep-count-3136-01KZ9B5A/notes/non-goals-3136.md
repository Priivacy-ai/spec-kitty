# Recorded non-goals — mission `sync-sleep-count-3136`

This is the `<guard-rationale>` referenced by `SC-010` sub-3 and by `plan.md`'s `IC-07`.

It exists so that the decision **not** to do a thing is inherited as a decision, with its
reasoning, rather than re-derived at the cost of another agent-day. Everything here was settled
by the operator and by the post-spec squad. **It is not open for relitigation inside this
mission** — it is open to being *overturned by new evidence*, which is a different act and
should be recorded as such.

---

## Non-goal 1 — a live CPU-contention reproduction (`C-005`)

**Decision: do not attempt a live 4-vCPU contention reproduction.**

The authoritative statement of this constraint is `spec.md`'s `C-005` row (the constraints
table). Its **three** reasons are recorded below individually, because collapsing them into one
sentence ("we can't reproduce it locally") keeps only the weakest of the three and discards the
decisive one.

### Reason 1 — the producer is already named, so a reproduction has nothing left to identify

The producer construct is **CPython's `subprocess.Popen._wait(timeout)` POSIX busy-wait**, whose
loop body is `delay = min(delay * 2, remaining, .05)` with base `0.0005`. CI's observed
`556 = 1 + 6 + 549` is **one** loop caught in flight — the victim's own `call(2.0)`, one
six-term geometric ramp, then saturation at the `0.05` cap. It is **not** two producers.

This was **independently reproduced by two parties**, and corroborated by a positive control: a
standalone `Popen.wait(timeout=0.2)` on a background thread, run through the attribution
instrument, was attributed `subprocess.py:2047 in _wait` as the modal stack — the instrument
names a known producer correctly.

Two further candidate sites were retired rather than left open: `restart.py:147` and
`daemon.py:1382` are **falsified** (flat `0.05`, no ramp). Two more are excluded **structurally**
— `psutil.Process.wait` is invisible to this patch because `psutil._psposix.wait_pid_posix` binds
`_sleep=time.sleep` as a **function default at import time**.

A contention reproduction **cannot name a producer**. It can only make an already-named producer
likelier to be caught in the act. There is no identification left for it to perform.

### Reason 2 — a negative result would be uninformative by construction

For a narrow-window race, **a local pass is the default outcome**, not evidence of absence. So a
negative result is **uninformative by construction**: it is what the experiment returns whether
or not the defect is present, which makes it incapable of discriminating between the two.

This is not hypothetical. The predecessor's own probe missed — and the reason is known: the
polluting thread **had not yet entered its wait loop** when the sub-millisecond test body ran.
The probe was sound; the window was simply not open when it looked.

This is the **decisive** reason of the three. Reasons 1 and 3 say a reproduction would not be
*useful*; reason 2 says it would not be *valid*.

### Reason 3 — the lever is the assertion class, not the intruder

The operator's ruling is that **the lever is the assertion class, not the intruder**. The
mission's fix makes the census assertions immune to an unrelated caller landing inside their
patch window; it does not, and does not need to, remove that caller. **The intruder's identity
is therefore not on this mission's critical path.**

> **Prompt defect — this reason was dropped.** `WP06`'s own prompt enumerates the "three
> `C-005` reasons" as (a) producer already named, (b) a repro cannot name a producer, (c) a local
> pass is uninformative by construction. That is `spec.md`'s reason 1 **split into two**, with
> `spec.md`'s reason 3 — the operator's lever ruling — **absent entirely**. Since the lever
> ruling is precisely the decision this work package was dispatched to record, following the
> prompt's enumeration verbatim would have lost the point of the task. Both decompositions are
> preserved above: reason 1 carries the prompt's (a) and (b) as its two limbs, and reason 3 is
> restored from the authoritative source.

---

## Non-goal 2 — hunting the intruder population (issue `#3130`)

**Decision: do not fix the process-global and live-thread leaks.**

This is `C-003`, and it is the same ruling as reason 3 above viewed from the other side. The
leaks are real, active, and confirmed — one was caught live, in-session, during this mission's
own instrumented runs. They are nonetheless **out of scope**, and their teardown `ERROR`s may
remain red. They must **not** be counted as this mission's failures. The leak-guard attribution
race (`#3193`) is likewise out of scope.

The reasoning is not that the leaks are harmless. It is that the mission's contract is the
**assertion class** — an assertion that changes its verdict when an unrelated thread calls a
patched module attribute is defective regardless of which thread that is, and regardless of how
many such threads exist. Fixing the intruder population is unbounded work whose completion
cannot be verified; fixing the assertion class is bounded and statically decidable.

---

## The post-spec squad's sharper framing of the defect

The squad falsified the framing the spec was originally built on, and the correction changes what
counts as evidence. Recorded here because a reader who misses it will re-derive the falsified
claim.

**The original claim.** The class reddens on the `#3209` shard's composition while pristine
`main` is green, therefore the failure is a **composition** dependence.

**Measured, from CI's own logs — the claim is false.** Pristine `main` reddens on this class in
**11 of 18** consecutive `fast-tests-sync` jobs — **61%** — *including at this mission's own
baseline commit* `98198e980`:

```
job 92278529393 (main @ 98198e980):
  3 failed, 2113 passed, 11 skipped, 2 warnings in 100.79s
  assert 174 == 3 ; Called 153 times. ; Called 507 times.
```

`2113 + 3 = 2116` — the **same selection** as the local all-green run. The variable is therefore
**topology (parallel vs serial) plus timing**, **not composition**.

**And it is nondeterministic at a fixed commit.** Three of six same-SHA run pairs disagree.
`abca7ec96` reddened two nodes in one job and was clean in another. `bb2020fea9` produced
**different victim sets with different magnitudes on identical commits** — 71 vs 115 calls on the
same node.

**Why this matters for every acceptance arm in this mission.** Pre-fix, a single full-shard run
shows zero class failures **39%** of the time. So "the arm came back green, therefore it is
fixed" commits exactly the inference error the spec's own adversarial table forbids. A
single-run green is not evidence here; only an injection arm or a static measurement is.

Source: `analysis-report.md` (the topology finding and the same-SHA disagreement).

---

## Consequences for the inventory verdict stamp

The verdict stamp landed in `docs/development/process-global-inventory-3115.md` by this work
package is scoped to the **Dependence column only**, body-only, no frontmatter field touched.

### "Body-only" is not one property — it is two, and this work package checked only one

This is the correction most worth inheriting from `WP06`, and it cost a `REJECT` to learn.

`Risk 3` framed "body-only" as a single safety property protecting a single generated file. It is
not. It decomposes into **two independent properties**, each guarding a **different** generated
artifact through a **different** checker:

| Property | What it means | Generated artifact it protects | Rule that reds |
|---|---|---|---|
| **frontmatter-inert** | the edit changes no frontmatter field | `docs/development/3-2-page-inventory.yaml` | `INVENTORY-LOCKFILE-DRIFT` |
| **heading-inert** | the edit adds/removes/renames no body **heading** | `docs/development/3-2-docs-retrieval-index.yaml` | `DOCS-INDEX-DRIFT` |

**`WP06` established the first and assumed the second.** The frontmatter mitigation was **correct
and complete** — zero `INVENTORY-LOCKFILE-DRIFT` findings, and `git diff -U0` showed no hunk
before `:231`. That half needs no revisiting.

The gap is that **body headings are index input too**. `scripts/docs/docs_index.py:184-196` builds
each index row's `anchors` from `scan_headings(body)` — *body* headings, not frontmatter — and
`scripts/docs/check_docs_freshness.py:767-813` (`_check_docs_index_drift`) regenerates that index
and emits `DOCS-INDEX-DRIFT` at `severity="error"` on any `title`/`abstract`/`anchors`
disagreement. A body-only edit that introduces a level-2 heading is therefore **not** inert.

**Measured.** The original stamp's `## ⚠ Verdict-column stamp …` heading took the page's
regenerated anchor count from the committed **16** to **17**; the delta was exactly
`verdict-column-stamp-unverified-and-falsified-in-the-direction-that-matters-3136`. `title` and
`abstract` were unchanged. Gate result: planning-branch tree `exit=0 findings=0 errors=0`,
lane-f `exit=1 findings=1 errors=1`.

**It survived composition, which is what made it a blocker rather than a lane-local nit.** `WP04`
*did* regenerate `3-2-docs-retrieval-index.yaml` (lane-d, commit `a5ee0baea`) — but against a tree
without this stamp. **No lane in this mission regenerates that file after the stamp's heading
lands** (verified: `verdict-column-stamp` occurrences in the committed index → `0` on coord,
lane-b, lane-c, lane-d, lane-f and `feat/`), and `.github/workflows/docs-freshness.yml:3-4` runs on
every `pull_request` with **no draft exemption**. The composed PR would have been red.

**The fix shape, and the one that was rejected.** The stamp was restructured to introduce **no new
heading** — folded under the existing `## Legend — the four mandatory values` section as a
blockquote, the form the module-surface correction block further down that same page had already
proved produces zero anchors. Regenerating
`3-2-docs-retrieval-index.yaml` on lane-f was **explicitly rejected**: it would have made `WP06` a
co-owner of a file `WP04` also regenerates — precisely the cross-lane collision `Risk 3` exists to
prevent — trading a docs red for a merge conflict.

**Why the blind spot persisted.** The sibling checker never entered this work package's world
model at all. Its own docstring calls itself *"a sibling artifact to the page inventory"* and
*"the inverted ruler"* — it announces the symmetry `Risk 3` missed. Measured against both
deliverables **before** this remediation:
`grep -n 'freshness\|retrieval\|DOCS-INDEX\|anchor\|3-2-docs'` → **zero hits**. `Risk 3` reasoned
about one generated index because one generated index was the one it had heard of.

**For a successor:** when a work package claims an edit is "body-only", ask which *generated*
artifacts consume that page, and derive the list — do not inherit it. This page feeds **two**.

The set of inventory rows this mission's fix depends on is **empty — zero rows** (`T034`,
Branch A). It was derived, not assumed; the derivation and the individual adjudication of the two
live candidate rows live **in the inventory page itself**, which is the surface licensed to name
rows. This file deliberately carries **zero** inventory row-id tokens, which is what `SC-010`
sub-3 requires of it.

---

## Verification battery

Run from the lane worktree. `D` is the inventory page, `N` is this file.

```
D=docs/development/process-global-inventory-3115.md
N=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md
```

Measured against the **committed** file (`git show HEAD:$N`), not an editor buffer:

| # | Command | Required | Measured |
|---|---|---|---|
| 1 | `grep -c '3136' "$D"` | ≥ 1 | `9` |
| 2 | `grep -cE '^\| E[0-9]+ \|' "$D"` | 53 | `53` |
| 3 | `grep -cE '\bE([1-9]\|[1-4][0-9]\|5[0-3])\b' plan.md` | 0 (bounded) | `0` |
| 4 | `grep -cE '\bE[0-9]+\b' plan.md` | reported as measured | `1` (the `E402` lint code at `plan.md:354`) |
| 5 | `grep -cE '\bE([1-9]\|[1-4][0-9]\|5[0-3])\b' "$N"` | 0 | `0` |
| 6 | `test -s "$N"` + `wc -l < "$N"` | non-empty | `359` lines |
| 7 | `grep -c 'uninformative by construction' "$N"` | ≥ 1 | `4` |
| 8 | `grep -c '11 of 18' "$N"` | ≥ 1 | `2` |

**Rows 3 and 4 are two separate single-value commands, never one command over two files.**
`grep -cE … file1 file2` prints one count *per file* and has no single value to compare against
`0`; a single number reported from that form is a defect, not a pass.

**Row 4 is the known false positive, and it is already remediated in the spec.** The unbounded
pattern matches `# noqa: E402` in `plan.md` — a lint code, not an inventory row id. `spec.md`'s
`SC-010` sub-3 **already** specifies the bounded form (row 3), so no criterion escalation is
owed; the `WP06` prompt's Risk 1, which asks for that escalation, is stale relative to the spec
as committed. Both values are reported above regardless, and the pattern was **not** quietly
changed — both forms are shown.

**Rows 7 and 8 are self-inclusive.** The command text in this table itself contains the strings
being counted, so each measured value includes its own command line as one occurrence. Reported
as measured rather than adjusted, because an adjusted count is not a reproducible one.

**Rows 6–8 are the same-file positive twins for the row-5 negative.** Row 2's `53` fires against
a **different** file (`$D`) and therefore cannot distinguish an absent or empty `$N` from a
compliant one: `grep -c` on a missing file prints no count and exits `2`, which reads as
satisfied by a naive check. The twins close that hole.

### Docs-scoped guards and lint

| Command | Required | Measured |
|---|---|---|
| `pytest tests/architectural/test_no_legacy_terminology.py -q` | `EXIT=0` | `EXIT=0` — `10 passed in 61.64s` |
| `pytest tests/architectural/test_glossary_canonical_terms.py -q` | `EXIT=0` | `EXIT=0` — `9 passed in 59.64s` |
| `ruff check .` | `All checks passed!` | `EXIT=0` — `All checks passed!` |

Both guards were invoked through the project interpreter by absolute path (see
*Environment* below), never a bare `uv run`.

`C-002` — the linter's reformatting subcommand was **never** invoked, and its literal name is
deliberately absent from this file so the constraint's own grep returns `0`. Only `ruff check`
was run.

`C-001` — **no `tests/sync` or `tests/cli` run appears anywhere in this work package.** Every
check here is a grep, a docs-scoped architectural test, or `ruff check`. The `tests/sync` window
remains held (`PENDING — WP07 (T043)`); this work package neither acquired nor released it.
Reading files under `tests/sync/` is not running them, and several were read.

---

## Environment

The lane worktree has **no `.venv` of its own**. The `./.venv/bin/…` command forms given
throughout this mission's prompts are unsatisfiable from the lane worktree — which the same
prompt mandates as the working directory. The project interpreter was therefore invoked by
absolute path from the repository root checkout:

```
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python   # Python 3.12.13
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff     # ruff 0.15.12
                                                          # pytest 9.0.3
```

`command -v` output, **quoted**, to show what would have been picked up instead — neither is this
project's interpreter, and neither was used:

```
pytest -> "/home/jeroennouws/.local/bin/pytest"
ruff   -> "/home/jeroennouws/.local/bin/ruff"
```

**A bare `uv run` or `uv sync` was never issued.** It re-solves against the tracked
`.python-version` and destroys `.venv`; this has already cost this mission four rebuilds.

> **Live hazard in this worktree.** The lane branch is seeded from `98198e980`, which predates the
> repository-root fix to that instruction. The `CLAUDE.md` reachable from **this worktree** still
> instructs the destructive bare form in its closing notes section. The corrected text exists only
> on the mission branch head. Not fixed here: the file is not owned by this work package, and
> editing it on this lane would collide with the fix already landed upstream. **Ledgered, not
> actioned.**

---

## This work package's output is split across two branches — this file is one half

**This file has a sibling.** `WP06` delivers two records, and they live on **different branches**.
A reviewer should not have to reconstruct that from `git show af2dc559a`, so it is stated here.

| Half | Path | Lives on |
|---|---|---|
| the non-goal record (this file) | `kitty-specs/…/notes/non-goals-3136.md` | **`feat/sync-sleep-count-3136`** only, added by `8ab0b7627` |
| the verdict-column stamp | `docs/development/process-global-inventory-3115.md` | **lane-f** (`kitty/mission-…-lane-f`) only |

**What forced it.** `move-task` refuses `kitty-settings`-adjacent `kitty-specs/` changes on lane
branches, so a `kitty-specs/` artifact cannot be committed on the lane that produced it. The
sanctioned route is to port the content to `feat/` and then clean the lane — which is what `WP04`
did, and this split is identical in shape to `WP02`'s accepted one.

**Nothing was duplicated and both halves are reachable** — verified, not asserted:

```bash
P=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md
git rev-parse af2dc559a^:$P   # 9dd7083eaa453fb5322c732ca24a4241c0ab4317  (deleted from lane-f)
git rev-parse 8ab0b7627:$P    # 9dd7083eaa453fb5322c732ca24a4241c0ab4317  (added on feat/)
```

Byte-identical across the split; the lane's copy was removed only after the `feat/` copy existed.
The commit that removed it, `af2dc559a`, touches that one path and nothing else (`1 file changed,
359 deletions(-)`).

**What was *not* done, deliberately.** When `move-task` refuses, it suggests
`git restore --source … --worktree -- kitty-specs/`. That command **destroys uncommitted work** in
that path. It was not run. Port first, verify the blob matches, clean the lane only then.

---

## Ownership gap — read this before approving

**This file is required by `plan.md`'s `IC-07` and by `SC-010` sub-3, but it is absent from
`WP06`'s `owned_files`.** `plan.md`'s `## Project Structure` assigns it to `IC-07` and to no
other concern, so no other work package will create it.

It was created here because the alternative is a criterion that no package can satisfy. The gap
was recorded rather than silently widened: **`owned_files` was not modified** at the time, and the
question was surfaced for adjudication instead.

**Adjudicated 2026-08-07 — operator ruling: creating it was right; correct the manifest now.**
The manifest was accordingly corrected in this remediation pass:
`kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md` is now listed in `WP06`'s
`owned_files`, alongside `docs/development/process-global-inventory-3115.md`. The ordering of
events is the point and is preserved on the record: **surface, adjudicate, then widen** — not
widen and report.

---

## Ledger — findings outside this work package's scope

Recorded, not actioned. None is a defect in this work package's own output.

**Disposition into the shared register (`residual-ledger.md`), settled 2026-08-07.** An earlier
revision recorded these five here and filed **none** of them, so three never reached the shared
register. Now reconciled item by item:

| # | Disposition | Shared-register entry |
|---|---|---|
| 1 | duplicate — already registered | `RL-012` / `RL-020` |
| 2 | **filed** | **`RL-023`** |
| 3 | **filed** | **`RL-024`** |
| 4 | **filed** | **`RL-025`** |
| 5 | duplicate — already registered | `RL-005` / `RL-019` |

**IDs came from the reserved `RL-023`…`RL-029` block** (WP03 / WP06 remediation), **not** from the
running maximum. The ledger's own header explains why that distinction is load-bearing: the maximum
on any one branch is not a fact about the composed tree, and reading it that way has already caused
two ID collisions in this mission — one of them the orchestrator's own allocator commit. The
authoritative copy read before picking was the one on **`feat/sync-sleep-count-3136`** (25 entries,
max `RL-052`, zero duplicates); the coord copy is stale at `RL-016` and was not consulted.

1. **The recorded planning commit is stale, and workspace allocation fails closed on it.**
   `spec-kitty implement WP06` refused to allocate, because it auto-merges a recorded planning
   commit (`4bdcb48f1`, 2026-08-06) into a lane whose seed (`ab3368840`) is a newer squashed
   planning snapshot. Their merge base is `98198e980`, so every planning path present on both
   sides is an add/add conflict — 10 of them. Resolved manually, `--ours`, verified
   content-neutral: for all 9 paths the stale commit modifies, the lane blob is byte-identical to
   the mission branch head, so taking *theirs* would have **regressed the work package prompts to
   their 2026-08-06 text**. A lane seeded from a squashed snapshot can never fast-forward the
   commit the runtime records.

2. **The lane worktree's sparse-checkout blocks conflict resolution.** `git checkout --ours` could
   not write `status.events.jsonl`; it is excluded by this worktree's sparse rules, so the path
   had to be resolved directly in the index. A sparse-excluded path that conflicts cannot be
   resolved by the documented command.

3. **The bounded row-id pattern does not disambiguate what it was introduced to disambiguate.**
   `spec.md` bounds the pattern to the real id range specifically to stop `E402`-style lint codes
   matching. But `tests/architectural/_baselines.yaml` carries tokens inside that bounded range
   which belong to **issue `#3030`'s egress-boundary enumeration**, an entirely different
   namespace — **seven lines, nine distinct tokens, twelve occurrences**.

   **Measurement-labelling correction (2026-08-07).** An earlier revision of this entry read
   "carries **seven** tokens", sourced from `grep -c`. `grep -c` counts **matching lines, not
   matches** — the true distinct-token count is nine and the occurrence count twelve. Same
   measurement-labelling class this mission keeps re-incurring (a count reported under the wrong
   noun), so it is corrected rather than merely noted.

   **The conclusion is untouched, and never rested on the count.** Decisive: one single id in that
   range names a **retired queue drain** in `_baselines.yaml` (`:375`) *and* a **frozen string
   constant** in the process-global inventory. Two enumerations share one range, and no range-bound
   can separate them; only a path or context qualifier can. This bears directly on live criterion
   `SC-010` sub-3, whose negative uses exactly this bounded pattern.

   **The token-level evidence — the commands, the nine ids, and the colliding id by name — is
   recorded in `residual-ledger.md` under `RL-024`, deliberately not here.** `SC-010` sub-3 requires
   this file to carry **zero** inventory row-id tokens, so naming the id here would break the very
   criterion this finding is about. The ledger is not under that constraint; the argument is
   complete there.

4. **The spec repeats the falsified module-surface count.** `spec.md`'s "Code facts verified
   directly" section asserts the module's module-level names are only the two, under a heading
   stating everything numeric came from a command run on `98198e980`. Re-running that command on
   `98198e980` yields three. The corresponding claim in the inventory page **was** corrected by
   this work package, because that page is owned here; the spec's copy is not owned and is left
   for the reviewer to route.

5. **`DIR-013` conflicts with this work package's dispatch.** The charter directive requires
   opening a tracker issue on encountering pre-existing failures; the dispatch bars
   `gh issue create` outright. No pre-existing test failure was encountered, so the conflict did
   not bind — but it is live for any package that does hit one.

---

## Prompt defects found in `WP06`'s own prompt

Each was measured against the tree, not inferred.

1. **The table census is wrong in all three of its numbers.** The prompt states "nine tables carry
   `E`-rows: six are five-column, three are three-column". Measured: **ten** tables carry
   `E`-rows — **eight** five-column and **two** three-column. Row totals sum to 53, confirming the
   enumeration. The prompt's third "three-column" citation points at a
   `| Category | Count | Disposition |` summary table that carries **zero** `E`-rows; it merely
   mentions row ids inside prose cells. Its two other citations point at table *separator* lines,
   not headers.

2. **`## Method` item 4 is mis-located.** The prompt gives it the line range that actually belongs
   to `## Legend` item 4. `## Method` begins near the top of the page; its item 4 is roughly a
   hundred lines above the Legend, not below it.

3. **The "exactly two names" quotation is attributed to the wrong place.** The prompt attributes it
   to the module-constants table row it names. That row says something different; the quoted claim
   lives in the prose block **above** the table. The same misattribution appears in `spec.md`,
   which is where the prompt inherited it.

4. **The staleness claim understates the defect.** The prompt says the row's measurement "goes
   stale the moment `WP02` lands". Measured: it was **already false at `98198e980`**, before any
   change by this mission — the enumeration omits a third module-level name that has been present
   all along. The seam makes a wrong count wronger; it does not make a right count wrong.

5. **`notes/` is said not to exist.** It exists, with two files already in it.

6. **The predicted non-fatal warning did not appear.** The prompt says to expect
   `code_change WP does not own any files under src/ or tests/` and to record it as deliberate. It
   was **not** emitted. A different warning was: the dependency lane `lane-a` does not resolve, so
   this lane does not contain its tip. `WP01` is approved and its lane appears to have been
   merged-and-deleted, which is consistent with that message.

7. **The declared agent profile does not match the dispatched one.** The prompt's frontmatter
   declares `curator-carla`; the dispatch loaded `python-pedro`. The work is curation, so the
   prompt's declaration is the better fit. Recorded rather than silently reconciled.

8. **`spec.md` and the prompt disagree on the stamp's wording.** The prompt and its reviewer
   guidance demand **falsified** and warn that "unverified" understates it. `spec.md`'s `SC-010`
   sub-2 asks for "an **unverified** stamp naming the … **falsification**". The stamp as written
   carries **both** tokens, which satisfies both readings; this is the spec's own phrasing, not a
   hedge.

### Checks that were mechanically unsatisfiable

None of this work package's own checks proved unsatisfiable — the twins in the battery above are
all independently required and all fire.

One prompt instruction was declined on the same grounds `WP01` declined its red-first evidence:
**no red-first evidence is owed here.** This work package changes no code, defines no behaviour,
and makes no runtime claim; its entire product is two documentation records. There is no
behavioural contract for a failing test to pin, so manufacturing a red would be inventing
evidence rather than producing it. `WP01`'s reviewer confirmed the equivalent call. The same
reasoning applies to the `[UNVERIFIED]` baseline-variance protocol: it binds any package that
touches a runtime claim, and this one touches none, so no timing arms were run and none are
reported.

---

## Subtask completion transcript

```
$ spec-kitty agent tasks mark-status T033 T034 T035 T036 --status done \
    --mission sync-sleep-count-3136-01KZ9B5A
Branch: feat/sync-sleep-count-3136 (target for this mission)
✓ Marked 4 subtasks as done: T033, T034, T035, T036
EXIT=0
```
