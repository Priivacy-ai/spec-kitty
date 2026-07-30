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
