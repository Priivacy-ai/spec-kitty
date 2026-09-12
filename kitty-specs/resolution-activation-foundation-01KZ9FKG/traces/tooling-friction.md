# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

Mission: `resolution-activation-foundation-01KZ9FKG` · #2657 + #3210.
Seeded at planning with **known friction to watch** (from the shadow-clone setup + spec-kitty
governance context). **Append every real friction hit during implement; assess at close and file
durable ones to the tracker.**

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Watch-list carried in (verify before treating a red as yours)

- **W1 — Baseline-red gotcha.** Broad `pytest` shows reds that are NOT your diff (known-P0 reds
  #2736/#2772/#1834; CI-env auth/sync toggles; stale-install false reds). Classify against the
  merge-base before folding. (CLAUDE.md "Test-run baseline-red gotcha".)
- **W2 — CI-only shards.** Terminology + some repo-wide gates run only in CI's
  `integration-tests-core-misc`, not the `fast-tests-*` suites. Run `tests/architectural/` locally
  (esp. `test_no_legacy_terminology.py`) before pushing — this mission touches `kernel/README.md`
  prose (FR-005) and charter provisioning.
- **W3 — Arch gates are vacuous under `.worktrees/`.** Verify architectural gates (layer rules,
  built-in-location authority, single-door invariant) from the **primary checkout**, not inside a
  lane worktree — a green marker inside a worktree proves nothing.
- **W4 — Monkeypatch seams in `tests/runtime/test_home_unit.py`.** Collapsing `home.py` onto the
  kernel authority (FR-001/FR-006) will break patch targets; they must be retargeted in the same
  change (C-007), not orphaned.
- **W5 — Env split-brain is under-tested.** No test asserts the missions tree honors
  `SPEC_KITTY_PACKS_ROOT` today (NFR-006 adds one). When adding it, set BOTH `SPEC_KITTY_PACKS_ROOT`
  and `SPEC_KITTY_TEMPLATE_ROOT` in at least one case to pin the confirmed precedence (PACKS_ROOT
  wins for missions).
- **W6 — Real-port/daemon tests run serially.** If any provisioning test touches the daemon/queue,
  run it `-n0`; parallel `-n auto --dist loadfile` per-worker HOME isolation does not cover real ports.
- **W7 — coord topology routes commits to the coordination branch.** This mission is `topology: coord`
  (coord branch `kitty/mission-resolution-activation-foundation-01KZ9FKG`). `spec-commit` and lane
  commits route there; write `kitty-specs/` tracer/plan edits from the primary checkout, not a lane
  worktree (lane-branch tracer edits can block `move-task`).
- **W8 — Shadow-clone isolation.** All `spec-kitty` commands must run through the clone-local
  `.venv/bin/spec-kitty` with `SPEC_KITTY_HOME=<clone>/.spec-kitty-home`; a bare `spec-kitty` hits the
  machine-global install against this clone's files.

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

- 2026-08-05 — `spec-kitty agent mission setup-plan` is not read-only: running it to *check* the
  spec-phase gate scaffolded an empty `plan.md` and appended a status event. There is no dry-run
  flag to inspect `phase_complete`/`blocked_reason` without side effects. Minor, but a friction
  worth a `--check` flag on the tooling-gap backlog.
- 2026-08-05 — **Rebasing the mission branch onto upstream leaves the coordination branch stale
  (coord-topology).** After rebasing `feat/` onto the landed #3211, the coordination branch
  `kitty/mission-…` stayed on the pre-#3211 base, so `implement`'s lane allocation failed:
  "cannot auto-merge the recorded planning commit … into lane 'lane-a': the merge conflicts"
  (207 files / -36k lines — the lane base was missing all of #3211, plus add/add on the identical
  `kitty-specs/` files). Recovery: `git worktree remove --force` the half-allocated lane worktrees,
  `git branch -D` the lane branches, `git -C .worktrees/…-coord reset --hard feat/…` to realign
  coord to feat, re-run `finalize-tasks`, then `implement`. **Lesson:** when a coord-topology mission
  is rebased onto a new base, realign the coordination branch to the mission branch BEFORE
  `implement`; a `spec-kitty` "rebase/realign coordination branch" helper would remove the manual
  surgery. Compounding: `spec-kitty agent action implement` takes >2min to allocate a lane worktree
  (heavy: full tree materialization); run it backgrounded, not in a 2min-capped foreground call.
- 2026-08-05 — **Lane worktree editable-install trap.** The clone-local `.venv` editable install
  resolves `specify_cli`/`kernel` imports to the PRIMARY checkout's `src/`, not the lane worktree's.
  Tests run in a lane worktree must set `PYTHONPATH=<worktree>/src` or they validate the wrong code
  (false green/red). Passed this instruction to every implement/review subagent.
