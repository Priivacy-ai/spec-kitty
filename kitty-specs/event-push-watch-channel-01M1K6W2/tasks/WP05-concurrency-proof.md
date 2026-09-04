---
work_package_id: WP05
title: Concurrency proof — writer safety under a concurrent tail reader
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- NFR-004
- NFR-005
- C-008
- C-009
- C-010
planning_base_branch: feat/event-push-watch-channel-3841
merge_target_branch: feat/event-push-watch-channel-3841
branch_strategy: Planning artifacts for this mission were generated on feat/event-push-watch-channel-3841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/event-push-watch-channel-3841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-push-watch-channel-01M1K6W2
base_commit: c269cad808059ad513f3942fd24eec2de2ace0d6
created_at: '2026-09-03T16:25:01.639240+00:00'
subtasks:
- T031
- T032
- T033
- T034
- T035
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/status/
create_intent:
- tests/status/test_events_tail_concurrency.py
execution_mode: code_change
model: ''
owned_files:
- tests/status/test_events_tail_concurrency.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – Concurrency proof — writer safety under a concurrent tail reader

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Prove, with a real concurrent execution — not an assertion, not a mocked reader — that a live
`events tail` reader running against a mission's `status.events.jsonl` while that mission's own
normal writer path (`status.emit.emit_status_transition`) is actively appending to it produces
zero behavioral change on the writer side (NFR-004/SC-005). This is the mission's final work
package and its only true integration/concurrency tier: everything WP01–WP04 built is exercised
together, for the first time, against a genuinely overlapping writer and reader.

## Context

- **This is the mission's only true integration/concurrency tier**: a real writer
  (`status.emit.emit_status_transition`), a real reader (this mission's actual
  `tail_events()`/CLI command), and a real git fixture, proving NFR-004/SC-005's "writer sees zero
  behavioral change from a concurrent reader" property (FR-010 makes this true by construction —
  the reader never writes — but this WP is the empirical proof, not just an assertion).

- **C-009 (SK-147) fixture freezing**: if this WP mints one or more real spec-kitty mission fixture
  directories in quick succession to generate log content, it MUST freeze `ULID` generation and
  `now_utc_iso()` per ledger SK-147's pattern, to avoid a structural `mid8` collision between
  fixture missions created within the same ~256ms window.

- **C-007 immutable-roots hygiene**: this WP's fixtures MUST use `tmp_path`-based synthetic mission
  directories — never this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or
  any other pre-existing path under `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
  `kitty-ops/`, or `.kittify/missions/`.

- **C-010 (informational, not an action this WP performs)**: the eventual implementation PR body
  must carry `Closes #3841` — this is a note for whoever opens the PR (the orchestrator), not
  something this WP's own commits do.

- **PR-shape recommendation (plan.md's PR Shape section, restated for the final WP)**: this mission
  ships as ONE PR (spec-kitty's default), but given the genuine engineering weight (dual truncation
  detection, tear tolerance, a bounded-generator seam, a resumable cursor with a non-trivial
  backward-scan verification path), the plan judges the aggregate diff NOT trivially reviewable in
  one sitting and recommends the pre-merge adversarial squad and the operator's final PR review
  budget real time proportional to a small-subsystem review — WP-level review, including this WP's,
  must NOT be compressed or skipped even though the final artifact is one PR.

- **`__all__` (C-007/C-002) does NOT apply** — this WP's new file is a test, not a
  `src/charter/`/`src/kernel/` module.

- **Terminology canon**: no `--feature*` aliases anywhere in this WP's own test code/fixtures.

- **Commit discipline**: conventional-commits, every message ends with
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

- **ATDD precision**: T031's failing-first test must fail against WP04's final commit — this exact
  concurrent-execution scenario (a live writer running alongside a live reader against the same
  mission directory) has never been exercised by any earlier WP's tests (WP01-04 all test the
  reader in isolation, never alongside a real concurrent writer), so this is a genuine new-behavior
  red, not an import failure. State this precisely: at WP04's final commit, `tail_reader.tail_events()`
  and `events.py`'s CLI shell both fully exist and are independently tested — the RED this WP
  introduces is a **behavioral** failure (an assertion comparing the writer's output with and
  without a concurrent reader present does not hold, or the harness itself does not yet exist), not
  a `ModuleNotFoundError`/`ImportError`/collection error. If the very first commit of this WP is
  only the test harness/fixture scaffolding with no assertion exercised yet, say so explicitly and
  identify which later commit is the actual red-to-green ATDD pivot.

- **Baseline-red methodology (NFR-005)**: before T031's red-first commit, run the exact targeted
  test path set from plan.md's "Baseline & Pre-existing Red" section against merge-base
  `db5014ab5`, quoting the baseline red WITH that path set:

  ```bash
  git stash   # or run from a clean worktree checked out at db5014ab5
  .venv/bin/python -m pytest tests/status/ tests/specify_cli/status/ -m "fast and not (git_repo or integration or stress)" -q
  .venv/bin/python -m pytest tests/cli/ tests/specify_cli/cli/ -m "fast" -q
  ```

  Since `test_events_tail_concurrency.py` is a brand-new file, the realistic baseline-red finding
  is "zero pre-existing red in this WP's own new test file" — the check matters for the SURROUNDING
  suite in the same path set, so you do not misattribute unrelated pre-existing red (tracked under
  #3284/#3283) as your own regression. This WP's own test is marked `integration`+`git_repo`, so
  also run the equivalent integration-tier path set (`tests/status/ tests/specify_cli/status/ -m
  "integration and git_repo"`) against the same merge-base before your red-first commit, and quote
  that baseline too — the note above about `fast`-only path sets covers the surrounding suite, not
  this WP's own marker tier. If you find pre-existing red not already covered by #3284/#3283, open
  a GitHub issue reporting it before proceeding past it.

### Fixture pattern to reuse (do not hand-roll a new one)

`tests/status/conftest.py` already provides everything a WP needs to drive
`status.emit.emit_status_transition` against a synthetic, `tmp_path`-only mission directory without
minting a real mission via the CLI:

- A `feature_dir` fixture pattern (see `tests/status/test_emit.py`) — `tmp_path / "kitty-specs" /
  "<slug>"`, created directly under `tmp_path`, never touching this mission's own `kitty-specs/`
  tree.
- `seed_wp_to_planned(feature_dir, wp_id, slug=...)` / the `seed_to_planned` fixture — seeds a WP
  from `GENESIS` to `PLANNED` by writing directly to the event log (no emit pipeline, no fan-out),
  exactly what `finalize-tasks` does before the lane lifecycle begins. Its own event IDs come from
  a deterministic module-level counter (`_make_seed_event_id()`), not real ULID/clock generation —
  seeding itself does not trigger the SK-147 collision window.
- The standard transition-call shape from `test_emit.py`:
  ```python
  from specify_cli.status.emit import emit_status_transition
  from specify_cli.status.models import TransitionRequest

  event = emit_status_transition(
      TransitionRequest(
          feature_dir=feature_dir,
          mission_slug="events-tail-concurrency",
          wp_id="WP01",
          to_lane="claimed",
          actor="claude",
      ),
      ensure_sync_daemon=False,
      sync_dossier=False,
  )
  ```
  `ensure_sync_daemon=False, sync_dossier=False` keep the pipeline scoped to the local durable
  write this WP cares about — no SaaS fan-out, no real sync daemon, no unrelated network/process
  dependency introduced into a concurrency test.

Because this pattern never invokes `spec-kitty agent mission create` (or any other real-ULID-minting
codepath), the C-009/SK-147 freeze described above is conditional, not automatically load-bearing:
if your harness stays entirely within this `tmp_path`-feature_dir + `seed_wp_to_planned` +
`emit_status_transition` pattern, no real `ULID`/`now_utc_iso()` mission-mint call is on the path
and there is nothing to freeze. If you instead choose (or need, for a more end-to-end proof
including the real CLI's `--mission <slug>` resolution) to mint one or more actual mission
directories via a real mission-creation codepath in quick succession, you MUST apply the SK-147
freeze at that point — do not assume the lighter fixture pattern above is what you ended up using
without checking.

## Subtask T031: Failing-first ATDD test — concurrent writer + bounded reader, byte-identical to control

Write a new top-level pytest test function in the NEW file
`tests/status/test_events_tail_concurrency.py` that:

1. Builds a `tmp_path`-based `feature_dir` (per the Fixture pattern above) and seeds one or more WPs
   to `PLANNED` via `seed_wp_to_planned`.
2. Defines a fixed, deterministic sequence of writer operations against that `feature_dir` — a
   handful of `emit_status_transition(...)` calls advancing one or more WPs through several lane
   transitions (e.g. `planned` → `claimed` → `in_progress`), each with `ensure_sync_daemon=False,
   sync_dossier=False`.
3. Runs that exact sequence TWICE against two independently-seeded, otherwise-identical
   `feature_dir`s (two separate `tmp_path` subdirectories, same seed/transition script):
   - **Control run**: the writer sequence runs alone, no reader present.
   - **Concurrent run**: the writer sequence runs on a background thread (or subprocess) while, on
     another thread, a bounded `tail_events()` call (or the real `events tail --max-events N` CLI
     invocation via `CliRunner`/subprocess) polls the SAME `feature_dir`'s `status.events.jsonl`
     concurrently, genuinely overlapping in wall-clock time with the writer's calls — not started
     and joined before the writer begins, and not started only after the writer has already
     finished.
4. Asserts the writer's own event count/content from the concurrent run is **byte-identical** to
   the control run: read `status.events.jsonl` from both `feature_dir`s (e.g. via
   `(feature_dir / "status.events.jsonl").read_bytes()`, or `store.read_events_raw()`/`read_events()`
   if you additionally want a parsed-level comparison) and assert exact equality of the raw bytes —
   not "approximately the same event count," not "same number of lines," but the literal byte
   content, modulo only the parts that are legitimately non-deterministic across two independent
   runs (e.g. `event_id`/timestamp fields, if your writer sequence does not otherwise pin them —
   prefer pinning them via a frozen clock/deterministic ID source in the harness itself so the
   comparison can be truly byte-identical rather than needing a field-by-field exception list; see
   T032).

This is the failing-first commit: at WP04's final commit, this exact concurrent-execution scenario
has never been run anywhere in this mission's test suite (WP01–WP04 all test the reader in
isolation against static or externally-mutated-between-polls fixture files, never against a live,
actively-running writer thread). Per the ATDD precision note in Context above, state explicitly in
your commit message which assertion is red and why (harness not yet built vs. behavioral mismatch
under real concurrency) — this is a genuine new-behavior red, not an import/collection failure.
Own commit: `test(status): add failing-first writer-vs-reader concurrency proof` (or equivalent
conventional-commits scope), ending with the required trailer.

## Subtask T032: Real-writer fixture harness — deterministic writer sequence, threading, SK-147 freeze if applicable

Build out the harness T031's test depends on:

- A small, reusable helper (module-level function or fixture in the new test file — this file is
  the sole owner of its own content, so no cross-file sharing concern) that runs the fixed writer
  sequence from T031 against a given `feature_dir`, returning nothing but leaving the event log in
  its final state.
- A way to run that helper on a background thread (`threading.Thread`) that the test can `start()`
  and later `join()`, and a way to signal/synchronize so the reader's polling genuinely overlaps the
  writer's writes — e.g. a small `threading.Event` the writer sets partway through its sequence
  (after its first write, before its last) that the reader waits on before beginning its own poll
  loop, or simply starting both threads together and asserting via elapsed-time bookkeeping that
  the reader's poll window and the writer's write window overlapped. Prefer the explicit
  `threading.Event`/checkpoint approach — it makes "genuinely overlapping, not sequential-then-
  compared" verifiable in the test itself rather than merely likely.
- Determinism for the byte-identical comparison in T031: either (a) pin `event_id` generation and
  the transition timestamp in the harness's writer sequence (e.g. supply explicit, fixed values the
  writer path accepts, mirroring `seed_wp_to_planned`'s own deterministic `_make_seed_event_id()`
  approach) so the control and concurrent runs produce truly identical bytes, or (b) if the writer
  path does not expose a way to pin those fields for a real `emit_status_transition` call, parse
  both logs and compare on a normalized/whitelisted-field basis (document explicitly which fields
  are excluded from the comparison and why they are legitimately non-deterministic — this must be a
  narrow, justified exception list, not a blanket "close enough" comparison). Prefer (a); fall back
  to (b) only if (a) is genuinely not achievable against the real `emit_status_transition` pipeline,
  and say so in your commit message.
- **SK-147 freeze, conditional**: if — and only if — this harness mints one or more real mission
  fixture directories via a genuine ULID-minting mission-creation codepath (not the lighter
  `tmp_path`-feature_dir + `seed_wp_to_planned` pattern described in Context), freeze `ULID`
  generation and `now_utc_iso()` per ledger SK-147's pattern before minting them, to avoid a
  structural `mid8` collision between fixture missions created within the same ~256ms window. State
  in your commit message whether this freeze was needed and applied, or explicitly not applicable
  because the lighter fixture pattern was used instead.
- Ensure every fixture directory used anywhere in this file is rooted under `tmp_path` (C-007) —
  never this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other
  pre-existing path under `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
  `kitty-ops/`, or `.kittify/missions/`.

Own commit(s), conventional-commits, trailer required.

## Subtask T033: Run writer and bounded reader concurrently; verify GREEN

Wire T032's harness into T031's test body (if not already fully wired by T031) and drive it to
GREEN:

- Start the writer thread and the reader (bounded `tail_events()`/`--max-events N` CLI invocation)
  such that their execution windows genuinely overlap, per T032's synchronization mechanism.
- `join()` the writer thread (with a generous but bounded timeout — this test must terminate
  deterministically, never rely on an external kill) and let the bounded reader run to its own
  natural termination (`max_events` reached, or `--once`/`--max-events` exhausted) — never an
  unbounded reader invocation anywhere in this file (mirrors NFR-001/WP03's discipline, extended to
  this WP's own CLI-shell-adjacent invocation if you use the real command rather than calling
  `tail_events()` directly).
- Assert the writer's own `status.events.jsonl` content from the concurrent run is byte-identical to
  the control run, per T031's comparison strategy.
- Additionally assert the reader itself did not error, did not raise, and — as a secondary,
  non-blocking sanity check, not the test's primary assertion — observed at least one event from the
  concurrently-running writer (this confirms genuine overlap occurred rather than the reader having
  started and finished before the writer wrote anything; if this secondary assertion is flaky under
  your chosen synchronization mechanism, tighten the checkpoint in T032 rather than loosening this
  assertion or dropping it).

Verify and record the transition to GREEN (T031's assertion now holds) on this WP's own commits.
Own commit, conventional-commits, trailer required.

## Subtask T034: Marker discipline, CI-job confirmation, baseline-red re-verification

- Add `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` at module level in
  `tests/status/test_events_tail_concurrency.py` — per C-008/SK-144, a test in the right directory
  with the wrong or missing marker is collected by zero CI jobs. Confirm (by reading the path filter
  in `.github/workflows/ci-quality.yml` for `integration-tests-status`) that `tests/status/` with
  this marker combination is actually selected by that job — do not merely assume it from this
  prompt's table, re-verify against the live workflow file.
- Confirm this test is **NOT** collected by `fast-tests-status` — its marker combination
  (`integration`+`git_repo`, not `fast`) must exclude it from that job's selector; this is the
  inverse mistake C-008 warns about (a test accidentally landing in a job that under-covers its real
  execution weight, or accidentally landing in a fast-tier job it does not belong in and slowing/
  destabilizing it).
- Run the exact targeted pytest surface for this WP's own tier plus the merge-base baseline-red
  check per plan.md's "Baseline & Pre-existing Red" section, quoting the baseline red WITH the path
  set (never a bare count):

  ```bash
  .venv/bin/python -m pytest tests/status/test_events_tail_concurrency.py -m "integration and git_repo" -q
  ```

  against this WP's final commit (GREEN expected), and separately re-confirm the merge-base baseline
  command set from the Context section's "Baseline-red methodology" against `db5014ab5` (RED/absent
  as appropriate — this file does not exist at that ref) to close out NFR-005's obligation for this
  WP.
- Run the full local suite invocation this mission's surrounding WPs used
  (`tests/status/ tests/specify_cli/status/`) once more at this WP's final commit to confirm no
  regression was introduced in sibling tests by this WP's fixtures (e.g. thread leakage, a lingering
  background thread from a failed `join()`).

## Subtask T035: Final mission-wide terminology guardrail; confirm C-010 linkage is a note, not an action

- Run `pytest tests/architectural/test_no_legacy_terminology.py` as a final mission-wide guardrail
  before considering this WP (and the mission's implementation surface) complete — this is cheap
  (≈0.1s) and mandatory per the charter's pre-push guidance; it covers every commit this mission has
  authored across WP01–WP05, not just this WP's own new file, since it is the last WP in the
  dependency chain.
- Confirm — do not action — that C-010's `Closes #3841` linkage is left as a note for the
  PR-opening step (the orchestrator), not something this WP's own commits do themselves. This WP
  must not add `Closes #3841` to any of its own commit messages or touch any PR-description
  artifact; record in your final summary that this obligation is explicitly deferred to whoever
  opens the mission's PR.

## Definition of Done

| WP | Test file(s) | Marker(s) | CI job |
|---|---|---|---|
| WP05 | `tests/status/test_events_tail_concurrency.py` | `integration`+`git_repo` | `integration-tests-status` |

- T031's RED is verified against WP04's final commit specifically — a genuine new-behavior red (the
  concurrent-execution scenario has never been exercised anywhere in the mission's test suite before
  this WP), never an import/collection failure and never a RED verified against some other ref.
- GREEN is verified on this WP's final commit for T031's test.
- The fixture ULID/clock freeze (SK-147, C-009) is applied if — and only if — this WP's harness
  mints real mission fixture directories via a genuine ULID-minting codepath in quick succession;
  the WP's own commit history/summary states explicitly whether this applied or was not applicable
  given the fixture pattern actually used.
- Every fixture directory used by this WP's test is rooted under `tmp_path` — none writes to or
  reads from this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other
  pre-existing path under `kitty-specs/`, `.kittify/migrations/mission-state/quarantine/`,
  `kitty-ops/`, or `.kittify/missions/`.
- Every commit in this WP is conventional-commits-formatted and ends with the required
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer.
- `pytest tests/architectural/test_no_legacy_terminology.py` passes at this WP's final commit.
- C-010's `Closes #3841` linkage is confirmed left as a note for the PR-opening step — not added by
  any of this WP's own commits.

## Risks

| Risk | Mitigation |
|---|---|
| Rapid fixture-mission creation in IC-05 collides on `mid8` (SK-147) | Freeze `ULID`/`now_utc_iso()` per SK-147's pattern before minting any real mission fixture in quick succession; not applicable at all if the lighter `tmp_path`-feature_dir + `seed_wp_to_planned` pattern is used instead — state which applies. |
| Fixture test writes into a pre-existing `kitty-specs/` mission dir | All fixtures use `tmp_path`-based synthetic mission dirs; never this mission's own `kitty-specs/event-push-watch-channel-01M1K6W2/` tree or any other pre-existing mission directory under the C-007-protected roots. |

## Reviewer Guidance

- Verify the concurrency test is a genuine race: the writer thread and the reader's poll loop must
  actually overlap in wall-clock time, proven by an explicit synchronization checkpoint
  (`threading.Event` or equivalent) in the test itself, not by starting the reader after the writer
  has already fully finished and merely asserting on the resulting file. A test that starts the
  writer, `join()`s it, and only then starts the reader is sequential-then-compared, not a
  concurrency proof — reject it if you find this shape.
- Verify the control-run comparison is exact: the assertion must compare byte content (or a
  fully-parsed, field-complete equality with a narrow, explicitly justified exclusion list for
  legitimately non-deterministic fields), never an approximate check like "same event count" or
  "same number of lines" alone. A count-only comparison would pass even if event ORDER or CONTENT
  differed between the control and concurrent runs, which is exactly the silent-desync class this
  mission exists to rule out.
- Verify the SK-147 freeze is actually applied if fixtures are minted in quick succession via a real
  ULID-minting codepath — check what the harness actually does (read the fixture helper, don't take
  the commit message's word for it) and confirm the freeze is present if warranted, or confirm its
  explicit absence is correctly justified if the lighter `seed_wp_to_planned` pattern was used
  instead.
- Confirm the reader invocation in this WP's test is bounded (`max_events`, `--once`, or
  `--max-events N`) and never an unbounded `tail_events()`/`events tail` call — an unbounded
  invocation in a concurrency test risks hanging CI indefinitely if the synchronization checkpoint
  is ever slightly off.
- Confirm the writer thread is always `join()`ed with a bounded timeout and that thread cleanup does
  not leak into subsequent tests in the same worker (check for any lingering non-daemon thread after
  the test function returns).

## Implementation Command

```bash
spec-kitty agent action implement WP05 --agent claude
```
