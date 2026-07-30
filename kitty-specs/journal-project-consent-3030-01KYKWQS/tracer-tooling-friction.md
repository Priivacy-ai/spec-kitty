# Tracer: tooling friction — journal-project-consent-3030

## Lane worktrees are allocated from a stale base

`spec-kitty agent action implement` cut lane-c from a commit predating the mission's
own acceptance pins, so the lane reported a clean 0-failure baseline while the
tests that define success were absent from the tree. This is the most dangerous
friction encountered: it manufactures a false green at the exact moment an
implementer establishes trust in their baseline. Worked around by merging the
mission branch into each fresh lane before measuring.

## The `done` gate cannot be satisfied per-WP

`--to done` requires every issue in `issue-matrix.md` to hold a terminal verdict.
In a multi-WP mission that means **no** WP can reach `done` until the mission's
issues are closed, even when the WP itself is complete and merged. Neither
`--force` nor `--done-override-reason` bypasses it. WP01/02/04/05/06/09 are
therefore parked at `approved` despite being finished and merged.

## Dossier edits from a lane branch are rejected

The lane guard refuses `kitty-specs/` writes from implementation branches, so
ownership and DoD edits must be committed on the mission branch. An ownership
commit made in lane-b had to be reverted and re-applied. Compounding this: no WP
in this mission declared any test file in `owned_files`, so every red-first commit
tripped `ACTIVE_WP_SCOPE_VIOLATION` until each WP's ownership was amended — after
finalize, since `spec-kitty tasks` regenerates frontmatter.

## The analysis report goes stale on any spec/tasks edit

`analysis-report.md` hashes its inputs, so remediating a finding invalidates the
report and blocks the next `implement` until it is re-recorded. Correct, but it
means remediation and re-analysis must be batched or the loop repeats.

## Pre-review regression gate times out

The `--to for_review` gate runs scoped tests with a 300s cap and reports
`timed_out`, refusing the transition. The suite this mission touches takes ~2
minutes on its own, so the gate could not complete and was skipped with the
evidence measured manually instead.

## Bulk-edit inference false-positives on "migrate"/"rename"

The mission spec scores 4/4 on bulk-edit heuristics because it discusses a schema
migration, requiring `--acknowledge-not-bulk-edit` on every lane allocation.

## Concurrent implementers in one working tree: `git add -A` swallows their edits

Self-inflicted, 2026-07-30, and worth recording because the loop invites it.

Four implementers were dispatched in parallel on disjoint *file* sets — sound for
content, but three of them shared one working tree on `feat/journal-project-consent-3030`.
The orchestrator (me) then ran `git add -A && git commit` for a dossier-only change
while one of them had uncommitted source edits in flight.

Result: commit `2e6aa1d78f`, whose message describes un-marking T004/T005, actually
carries eight source files plus a test — `delivery/selection.py`,
`event_journal/{journal,models}.py`, `sync/{consent,emitter,routing,runtime}.py`,
`tests/architectural/test_no_dead_symbols.py`. The implementer noticed, correctly
refused to rewrite history unasked, and reported it.

**Not rewritten.** Two other implementers were mid-commit on the same branch; a
`reset --soft` between their commits risks destroying uncommitted work. The content
is correct and wanted, so an honest note beats surgery. History is misleading in one
commit message; nothing is lost.

**Rules adopted mid-mission**, and they should be standing practice whenever more
than one agent shares a checkout:

- Never `git add -A` / `git add .` / `git commit -a`. Enumerate owned paths.
- `git status --short` before every commit; unstage anything outside your ownership.
- Never `reset`, `checkout --`, `stash` or `rebase` on a shared branch — report instead.
- Modifications to your own files that you did not make are a signal, not yours to
  revert.

Better still: give each concurrent implementer its **own lane worktree** even when
file sets are disjoint. Disjoint files do not make a shared index safe, because
`git add -A` is index-wide, not path-aware.

## Concurrent pytest sessions over `tests/sync` and `tests/cli` produce false reds

Found 2026-07-30 by an implementer that ran two sessions in parallel to save wall-clock
and got **16 failing daemon tests** that pass in isolation.

Cause: those tests spawn real `run_sync_daemon` processes and then `pgrep`/port-scan to
find them. A sibling pytest session's daemons are indistinguishable from orphans, so each
session reaps or trips over the other's. The failures look exactly like a regression in
daemon lifecycle handling.

Two consequences worth carrying forward:

- **Do not parallelise those two paths on one machine** to save time. The 16 reds cost
  more to diagnose than the parallelism saved, and one of them (`test_issue_1071_…`) was
  *already* a genuine port-band-collision bug earlier in this mission — so a real defect
  and this artefact present identically.
- **If CI ever shards `tests/sync` and `tests/cli` into parallel jobs on a single runner,
  this reproduces.** Worth a port-range or `SPEC_KITTY_HOME` partition per shard before
  anyone tries it.

Related: the same mission already fixed `test_issue_1071_singleton_reconfirmation`, whose
final sweep asserted over a hardcoded port band rather than the ports it allocated. Same
root cause class — a test reasoning about the machine rather than about its own fixtures.

## A shared fixture whose guard is filename-matched can silence the pins it guards

`tests/sync/conftest.py` applies a package-wide "assume a consenting checkout" fixture,
with a protected-suite guard so that consent tests are exempt. The guard matched on the
**filename token `"consent"`** — which does not match
`test_capture_gate_project_identity_3030.py`.

Extending that fixture naively during M1-1 would have applied a blanket grant to
**eight bidirectional pins** and converted them into decoration, green forever. Caught
before landing; the guard is now `("consent", "capture_gate")`.

That widening is a patch, not a fix. The guard still enumerates *names*, so any future
per-project pin in a file matching neither token is silently granted consent by its own
conftest. The durable shape is a marker or an explicit opt-in the test declares, not a
substring the fixture guesses. Flagged as still needing another look.

This is the same class as the swallowed-arity fake green earlier in this mission: the
mechanism that is supposed to protect a test is capable of disabling it, and nothing
fails when it does.

## `asyncio.get_event_loop()` makes negative pins pass for the wrong reason

M1-1's own new anchors passed in isolation and failed in the full suite. `_route_event`
calls `asyncio.get_event_loop()`; a sibling test had closed the loop, so the publish
raised and was **caught** as "send failed".

The positive controls failed loudly, which is how it was found — but consider the
negative controls: "no envelope was published" is exactly what a closed loop produces.
Every refusal pin in that file would have passed with the consent gate deleted. Fixed by
owning the loop per test.

Carry forward: for any pin whose assertion is *absence* of egress, ask what else in the
process could produce that absence. Order-dependent infrastructure failure and a working
refusal are indistinguishable at the assertion.

## WPs created after planning have no lane, so two gates silently no-op

WP12 was added mid-mission (`2b1cf5a157`) for the third egress path. `lanes.json` was
written at planning time and maps `lane-a` to **WP01 only**; WP12 appears in it nowhere.
The tooling defaults such a WP to `lane-a`, with two consequences that both fail quietly.

**The lane-staleness gate becomes inapplicable but still fires.** `move-task WP12 --to
for_review` refused with *"Your branch is behind by 130 commit(s) … cd
.worktrees/…-lane-a && git rebase"* — advice which, followed literally, would rebase
**WP01's approved lane** on WP12's behalf. WP12's commits (`d923f31476`, `d6294245d7`,
`6c48815fbd`) are on the mission branch itself, which is where a reviewer reads them.
Overridden with `--force` and the reasoning recorded in the transition note, because the
check was inapplicable rather than inconvenient.

**The pre-review regression gate skips entirely.** Both WP11 and WP12 transitioned with
`Pre-review regression gate: no_coverage — no changed files detected for this WP —
skipping the gate cheaply`. The gate appears to diff the WP's lane worktree, so a WP whose
work landed directly on the mission branch presents no changed files and is waved through.

That second one is worth more than its friction-tracer placement suggests. Both affected
WPs are **egress-path confidentiality work** — body uploads and local-commit frames — and
both received *no* pre-review regression gate while printing a line that reads like a
gate ran and found nothing to worry about. "Skipping the gate cheaply" is the same
sentence shape as this mission's other fake greens: a mechanism reporting success for
having done nothing. The independent reviews and mutation testing are what actually
covered these two WPs; had we relied on the printed gate, coverage would have been zero.

Worth fixing upstream: either register post-planning WPs in `lanes.json`, or have both
gates fall back to diffing the WP's `owned_files` against the merge base when no lane
exists. Failing loudly on an unmappable WP would also be acceptable — anything but a
skip that prints like a pass.

## A verification run is only honest in a tree you are not editing

WP12's first Mutation A baseline was discarded: the long pre-fix run overlapped the
implementer's own edits to the file under test. Redone against a pristine
`git worktree` of the pre-fix commit, which is what made the before/after a
measurement rather than a recollection.

The standing rule "no source edits during a verification run" is easy to obey in spirit
and violate in practice, because the natural move after launching a slow suite is to get
on with work. The durable fix is structural rather than disciplinary: **run the baseline
in a throwaway worktree**, so the working tree you are editing and the tree being measured
are different directories and cannot be confused.

This mission has now produced the same class of error from four directions: measuring over
directory sets that excluded the modified directories (four times), comparing against a
base that already contained the change, a guard whose own `except` swallowed its arity bug,
and this. The common shape is that **the thing being measured and the thing being changed
were the same thing.**

## `getattr(obj, "name", None)` is invisible to the dead-symbol gate

`tests/architectural/test_no_dead_symbols.py` scans the AST for references. An attribute
reached by string — `getattr(token_manager, "_ws_client", None)` at
`sync/local_commit.py:378` and `sync/__init__.py:373` — is a string literal, not a
reference, so a never-assigned attribute read this way is invisible to it. Nothing in
`src/` assigns `_ws_client`; only tests inject it.

The blind spot is worth recording independently of how that particular question resolves
(handed to WP12's reviewer, since a gate proven only on a path production never executes
is a different and worse problem than dead code). Any guard that reasons about symbol
liveness by AST will under-report wherever the codebase reaches attributes by name.

## Mutation plugins rot, and an obsolete mutation is indistinguishable from a passing gate

Five mutation plugins were built to prove this mission's acceptance pins load-bearing.
By the time WP07's rebase landed, **three of the five were obsolete** — and two of those
three would have been mis-reported as evidence by anyone reading tallies:

| Plugin | What it looked like | What it was |
|---|---|---|
| `mutA_no_consent` | all green → "pin no longer discriminates" | H5 pushed the consent gate **into SQL**; `selectable_event_ids` is now only a redundant *second* gate, so patching it changes nothing |
| `mutC_unfiltered` | all green | same cause, same now-secondary gate |
| `mutB_limit_first` | 3 reds → "mutation works" | the reds are **`TypeError`** from the old `read_identity_projection` signature, not assertion failures |
| `mutD`, `mutE` | 15 and 4 reds | genuinely valid |

This is the worst failure shape in the whole mission, because it is **symmetrical**. An
obsolete mutation that leaves everything green says "your pin is fine" in exactly the same
voice as a mutation that proves the pin load-bearing. And one that reds for a structural
reason says "the mutation works" in the same voice as one that reds on the invariant. The
tool built to detect decoration became decoration.

Replacements verified against the current architecture: `mutA2_no_consent_current.py`,
`mutC2_unfiltered_current.py`. `mutA2` reds the X2 pin on a genuine assertion — *"a project
that never consented must not have its event shipped… Both rows are drain-open, so consent
is the only thing that can exclude this one"*.

**Two rules for every future mutation, both structural rather than disciplinary:**

1. **Assert the mutation took effect.** A plugin patching a renamed, re-signatured or
   relocated symbol silently does nothing. The plugin must fail loudly when its target is
   absent, so a no-op cannot masquerade as a clean gate.
2. **Patch the primary decision point, not a redundant one.** Where a decision has been
   pushed down a layer, mutating the upper layer proves nothing about the invariant. Ask
   *where does this actually get decided now* before trusting either colour.

And always read failure text over tallies — `mutB`'s three reds look like a working
mutation right up until you see they are `TypeError`s.

## A textually clean merge can still be a behavioural regression

WP07's rebase produced code that **linted clean, contained zero conflict markers, and
crashed at runtime** in two places: `read_identity_projection` had become
`project_uuids`-mandatory (`TypeError` on every `sync doctor`/`status`/`migrate`), and
repo-slug-keyed consent had been reverted (`TypeError` on
`resolve_project_consent(..., repo_slug=)`). Both were found by **running** the report, not
by reading the diff.

Also recorded: an `__all__` conflict is a trap with no correct side. Both branches had
trimmed theirs against different live callers, so each was locally right and the merge was
wrong either way. The resolution is to recompute the union from *verified importers in the
merged tree* — never to pick a side. A stale note claiming `resolve_project_consent` "has
no production caller at all" was deleted rather than reworded, since
`build_per_project_store_report` is now its first.

## A new mission trips the birth invariant, and the remedy under-reports itself

`test_dogfood_corpus_backfilled` failed with `eligible missions not cut over:
['journal-project-consent-3030-01KYKWQS']` — **our own mission**. Found by another agent's
sweep and routed here as dossier territory.

Cause: `assert_birth_invariant_holds` requires every *eligible runtime-carrying* mission to
have `meta.json` `status_phase >= 1`. This mission accumulated runtime evidence in
`status.events.jsonl` through ordinary `move-task` transitions, which made it eligible,
while `status_phase` was never written at creation — every other mission in the corpus
carries `status_phase: 1`. So the failure is a **birth-order artefact**, not a defect in the
mission's work: a mission born after the event log existed has no legacy frontmatter state
to seed, so the cutover has nothing to do, so the field never gets set.

Remedied with the documented command, `spec-kitty migrate backfill-runtime-state --mission
<slug>`. The invariant test now passes (6 passed).

**Two observations about that command, one reassuring and one not.**

`--dry-run` genuinely does not write — verified by reverting the field, running dry-run
alone, and confirming `status_phase` stayed absent with a clean `git status`. Worth checking
rather than trusting, since this mission's own FR-016/FR-017 purge rests on exactly that
contract.

But the live run **wrote `status_phase` while reporting `Flipped: 0` and `Skipped (already
migrated): 1`.** The field went from absent to `"1"`, and the summary said nothing changed.
An operator reading that output would conclude the tool declined to act and the mission
still needs attention — the opposite of what happened. The "already migrated" classification
is about *seeding*, but the flip is a separate action that the summary folds into the same
bucket. Same family as the other gates recorded above: a mechanism whose report does not
describe what it did.

Also note the field is written as the **string** `"1"`, not an integer. `status_phase()`
parses via `int(str(...).strip())` so it works, but the corpus now contains both forms.

## `pytest | tail` throws away pytest's exit status — the shell layer of the same trap

Caught by the FR-027 implementer on its own run: `uv run pytest … 2>&1 | tail -18` reports
**`tail`'s** exit status, not pytest's. So "exit code 0" from such a pipeline is **not evidence of
a pass**, and a failing suite can be reported as succeeding by a harness that trusts the code.
The `N passed` line is the evidence; the exit code is noise.

This is the tally-versus-failure-text rule one layer down, and it had already bitten this session
in the other direction: a `pytest tests/cli tests/architectural | tail -18` run reported exit 143
with an **empty** output file, because `tail` buffers until the pipeline ends. The result was
neither a pass nor a fail — it was *no measurement at all*, and only the empty file revealed that.

Two habits to adopt, both cheap:

- **Do not pipe a suite whose exit status you intend to trust.** Write the full output to a file
  and read the tail of the file, or check `${PIPESTATUS[0]}` explicitly rather than `$?`.
- **Quote the count line as the evidence**, never the exit code — "2710 passed, 18 skipped" is a
  claim that can be checked; "exit 0" is a claim about `tail`.

The same agent also corrected itself here in the right direction: it first reported two
architectural guards as "verified by inspection, reasoned not executed", flagging the gap rather
than claiming green — and then, when the slow run (7m25s under contention) actually finished,
replaced the reasoning with **29 passed**. Reasoning that is labelled as reasoning can be
upgraded later; reasoning presented as measurement cannot.

## Agent contention became the dominant source of false signal

At peak this session, **20+ concurrent pytest processes** were running across five agents. Effects
observed and confirmed rather than guessed: two suites killed with no output; four
`test_issue_1071_singleton_reconfirmation` reds from an exhausted `[9401, 9425)` port band on top
of a 12-hour-old leaked daemon on 9400; 14 reds in daemon-orphan classification; and one agent's
7m25s run for a suite that takes well under a minute idle.

Every one of those presents identically to a regression. The mitigations that actually worked were
(a) killing the leaked daemon, (b) per-case `SPEC_KITTY_HOME`, and (c) isolating a measurement in a
clean worktree containing only the files under test — which is how FR-027's 19-row table was made
attributable in a tree three agents were editing simultaneously.

The lesson for scheduling, not just for measurement: **parallel implementation agents are cheap;
parallel full-suite runs are not.** Fan out the coding, serialise the sweeps.

## Attributing a killed run to contention is itself an unverified attribution

The coordinator reported a killed `pytest tests/cli tests/architectural` run as "almost certainly"
the documented daemon-reaping hazard, citing the entry above. An implementer then found the same
`exit 143` on its own run had a simpler cause: **SIGTERM from its own `timeout`**, not contention
and not a failure.

The coordinator's claim was never verified. It was plausible — there really were 20+ concurrent
pytest processes and a leaked daemon on 9400 — but a documented hazard that *fits* is not evidence
that it *fired*. This is the mission's central error one more time, in the place it is hardest to
notice: reaching for a known explanation instead of checking which one applies.

What checking would have cost: reading whether the elapsed time equalled the `timeout` value.

Consequences worth carrying:

- **`exit 143` on a `timeout N ... | tail` pipeline is triply ambiguous** — the timeout firing,
  an external kill, or `tail` being signalled. None of the three is a test failure, and the exit
  code cannot distinguish them. Only elapsed time and the output text can.
- **A run that was killed was not "a run that failed", and it was also not "a run that passed
  under contention".** It is *no measurement*, and the correct response is to re-run it, not to
  explain it. The implementer got this right: on finding its architectural run had been killed, it
  stopped treating `tests/cli` as covered and re-ran the ten suites that actually touch its files
  — found by grep rather than by running all sixteen under load — capturing pytest's exit status
  directly instead of through a pipe.
- **Narrow the scope instead of raising the timeout.** Selecting the suites that touch the changed
  files is both faster and more attributable than a broad run that contention will spoil anyway.

## The consolidated rule: a shared working tree is not a measurement substrate

This subsumes most of the entries above, and it was arrived at independently by two agents after
each was nearly misled by the same thing.

**Every claim about your own change must be measured in a worktree pinned to a commit** — not in
the live shared tree. Not because contention makes runs slow, but because in a tree several agents
are editing, *the thing you measured is not the thing you changed.*

The episodes that established it, all real, all this session:

| What happened | What it would have caused |
|---|---|
| A `21 failed` result came from an **untracked file another agent created mid-run**, failing on its own WIP schema setup (`no such table: events`) | Absorbing unrelated remediation, or hunting a defect that did not exist in the change under test |
| A mutation baseline overlapped the implementer's own edits to the file under test | A before/after that measured neither state |
| Four measurements were taken over directory sets that **excluded the modified directories** | Green reported for code that was never run |
| A comparison was made against a base that **already contained the change** | A no-op diff read as "no regression" |
| A killed run was attributed to a documented hazard that fitted but had not fired | An explanation standing in for a measurement |

The remedy is mechanical rather than disciplinary, and it worked every time it was used: **create a
throwaway `git worktree` at the commit you want, copy in only the files under test, run there.**
FR-027's 19-row shape table was made attributable that way while three agents edited the live tree
simultaneously; FR-025's leak measurement likewise; WP12 redid a contaminated baseline that way;
FR-023's fence-necessity proof used runtime blinding with the bind counted rather than a source
edit.

Two corollaries:

- **Narrow the scope rather than raising the timeout.** Select the suites that touch the changed
  files, found by grep. A broad run is both slower and less attributable, and contention will spoil
  it anyway.
- **Suspect your own reds as hard as your greens.** This mission spent most of its effort on fake
  greens, but the two nearest misses at the end were fake *reds* — someone else's failure, and a
  killed run — either of which would have sent an agent to fix code that was already correct.

## A hang is not a measurement, and two suites hang instead of failing

Found while pinning NFR-002's permanence clause. `tests/delivery/test_dispatch_window_consent_3030.py`'s
two loop-driving tests do **not** red when the drain fails to terminate — they **hang**. Under a
mutant implementing the "just loop a few more times" fix, they logged **1,603 empty selections
retried** and reported only `Failed: Timeout (>30.0s) from pytest-timeout`, and that only because
the run was forced to `--timeout-method=signal`.

`pytest.ini` **registers** the `timeout` marker but sets **no timeout in `addopts`**. So in the real
suite a non-terminating drain hangs indefinitely rather than failing — in CI that is a job that
burns its wall clock and reports a timeout, not a test naming the defect.

The first attempt to measure this was itself killed by pytest-timeout's thread method mid-session,
producing no summary and therefore **no verdict** — the same "empty output is not a failure" trap
recorded above, arriving from a third direction.

Two consequences:

- **A pin whose failure mode is a hang is not a pin.** The replacement counts `dispatch` calls
  through a wrapper with a hard cap, so non-termination is a clean red naming the call count
  rather than a stalled job. Any assertion about *termination* needs a counter, never a timeout.
- Worth fixing upstream: either set a default timeout in `addopts`, or mark the loop-driving tests
  with an explicit `@pytest.mark.timeout(...)`. Registering a marker that nothing applies is the
  same shape as an allowlist with no enforcement.

## A mutation must not hard-code what the tests vary

`mutB2` recovers the dispatch window **from the calling frame** rather than hard-coding the
default 1000. This is not defensiveness: `test_dispatch_window_consent_3030` monkeypatches the
window to 4, so a mutation hard-coded to 1000 would have been a **no-op for exactly the tests most
likely to catch the defect** — and a no-op mutation reads as a passing gate, which is how three
earlier plugins on this mission reported false confidence.

Generalisation: before trusting a mutation's colour, ask **what the tests vary that the mutation
assumes is fixed.** The mutant reported 43/43 calls recovering a real window, 15 truncations, 1,135
rows discarded and 4 starved windows — counts that make a no-op impossible to mistake for a pass.

Its isolation control deserves copying too: a second mode running the pre-H5
correct-but-slow implementation (unfiltered read, consent applied in Python, **no** truncation)
separated the 8 ordering-attributable kills from the 1 that detects the missing SQL filter — and
doubled as the positive control, since 12 tests exercising the mutated function still passed. One
switch, three jobs.

## CRITICAL ADDENDUM: an editable install defeats worktree isolation silently

The rule "measure in a worktree pinned to a commit" is **not sufficient on its own** in this
repo. `.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` contains the
**absolute path of the main checkout**:

```
/home/jeroennouws/dev/spec-kitty/src
```

So pytest run *inside* a throwaway worktree, using the main `.venv`, imports
`/home/jeroennouws/dev/spec-kitty/src/specify_cli` — the **live tree**, not the worktree's
source. Verified directly: `uv run python -c "import specify_cli; print(...)"` resolves to the
main checkout.

**This makes the failure worse than no isolation at all**, because the isolation *looks*
performed. A before/after across two pinned worktrees would import identical source on both
sides and report "byte-identical" or "identical failure sets" — which reads as a clean
exoneration and is actually a tautology.

**Required, in addition to the worktree:** either `PYTHONPATH=$WT/src`, or a dedicated `.venv`
created inside the worktree (`uv run` from within a fresh worktree will create one, which is why
some runs were unaffected).

Two agents handled it correctly and are worth naming as the pattern: the CI-routing agent used a
"clean worktree pinned to `23f81350ce`, **dedicated `.venv`**"; the purge-CLI agent found its
**first baseline had silently measured the change under test**, discarded it, and re-ran with
`PYTHONPATH` set.

**Claims that may need re-verification** — any worktree-based measurement in this mission that did
not state a dedicated venv or `PYTHONPATH`. Most at risk are the ones whose *conclusion was
sameness*, since that is exactly what this defect manufactures:

- FR-027's "clean HEAD worktree with only my three source files copied in → byte-identical table"
- FR-027's A/B exonerating the 21 purge failures ("identical 21-failure sets" on both trees)
- NFR-002's "three other agents' edits landed in the main tree during the run; none reached the
  measurement"

Note the asymmetry before re-running everything: a measurement whose conclusion was a
**difference** (a red that turned green, a mutant that killed pins) is largely unaffected — the
defect can only collapse two states into one, not invent a distinction. It is the
*sameness* conclusions that are suspect.

This is the session's own central lesson turned on the fix for that lesson: the remedy for
"the thing you measured is not the thing you changed" itself had a way of measuring the wrong
thing.

## A mutation can be inert on your interpreter and live on CI's

A fourth way for a mutation plugin to rot, found while auditing `sync/owner.py`. The first
version patched the obvious line — `except OSError: return False` — and reported
`unknown_branch=0` with the suite green. That reads exactly like "the pin does not hold".

It was neither. On **Python 3.14** that branch is unreachable, because `Path.exists()` delegates to
`os.path.exists` and swallows `EACCES` itself. On **Python 3.11/3.12 — CI's version** — the
exception propagates and the branch is live. So the mutant was inert on the interpreter it ran on
while the code it targeted was load-bearing on the interpreter that matters.

Caught only because the plugin asserted its own reachability. Rewritten against `os.stat`
(identical across 3.11–3.14) it killed all four unverifiable-path pins.

**Generalisation:** the standing rules already say *assert the mutation bound* and *patch the
primary decision point*. Add: **a branch's reachability can depend on the interpreter, the OS or a
library version**, so a zero-invocation count is not evidence the code is dead — it may be evidence
your environment differs from production's. The same asymmetry applies to the code under test: a
guard that looks redundant locally can be the only thing standing on CI.

## Applying the asymmetry: which worktree claims actually needed re-running

After finding that the editable install's `.pth` defeats worktree isolation, three claims were
flagged for re-verification. Rather than re-run all three on a contended machine, the asymmetry
was applied — **the defect can only collapse two states into one, never invent a distinction** —
and each claim was checked for whether its *conclusion* was a sameness or a difference.

| claim | conclusion type | verdict |
|---|---|---|
| FR-027's "byte-identical table" from a clean worktree | The **finding** (19 leaking shapes, before → after) is a **difference**. Only the *attribution* was a sameness. | Finding safe. Attribution corroborated independently — the shapes red before the fix and green after in the live tree too. |
| FR-027's A/B exonerating 21 purge failures ("identical failure sets") | **Sameness** — the suspect kind. | Conclusion holds on two *independent* grounds that do not depend on the A/B at all: the file is **untracked and was created after** that commit, so it is in neither tree; and the failure is `sqlite3.OperationalError: no such table: events` from the suite's own seeding helper, i.e. another agent's WIP. The A/B was corroboration, not the basis. |
| NFR-002's "other agents' edits did not reach the measurement" | The **result** (9 pins killed, 264 → 255 passed, each with genuine assertion text) is a **difference**. | Safe. A shared-source defect could not manufacture 9 kills with distinct failure messages. |

**None of the substantive conclusions rest on the compromised property.** In every case the
sameness claim was about *attribution* — "this result is mine and not contaminated" — and in every
case the finding itself was a measured difference that the defect is incapable of fabricating.

Recording the reasoning rather than the reruns, because the reasoning is the transferable part:
when a measurement technique is found faulty, **classify the affected claims by what they assert
before re-running anything.** A defect that collapses distinctions invalidates conclusions of
sameness and leaves conclusions of difference intact. Re-running everything would have cost five
agent-hours on a machine already producing false reds from contention, to re-confirm results the
failure mode cannot reach.

The one thing this does *not* excuse: every future worktree measurement must set
`PYTHONPATH=$WT/src` or use a dedicated venv, because the next claim may well be a sameness one.
