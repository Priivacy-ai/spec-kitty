# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

Mission: `charter-sole-door-bypass-closure-01KZ3WAA` (#189) — sole-door construction migration
for `AgentProfileRepository` sites, WP02 / NFR-005 / SC-008.

## Provenance note — read this before trusting the numbers below

This file was written during the **PR #3175 maintainer landing pass**, as a remediation fold,
**not** during WP02's original implementation. WP02's own activity log (T008 entry, 2026-08-03)
claims "NFR-005 baseline confirmed no regression (~2% delta) after a controlled A/B
re-measurement — see traces/tooling-friction.md", and `tests/perf/test_tasks_status_baseline.py`'s
module docstring repeats a "~2%" verdict citing this same file. **That original in-session
A/B was never persisted anywhere reachable**: the coordination branch that would have carried
this file was never pushed, `git log --all --diff-filter=A -- 'kitty-specs/charter-sole-door-bypass-closure-01KZ3WAA/traces/*'`
returns nothing, and this file did not exist on any ref before this fold. So the "~2%" figure in
the test docstring is not independently recomputable and SC-008 ("baseline captured and recorded
... before any FR-001 site is migrated ... not inferred retroactively") is **unmet as merged** —
the capture-before-migration ordering that made the number falsifiable never happened, or at
least never left a trace.

What follows is a **fresh, honest, reproducible A/B measurement taken now** (landing time,
2026-08-04), comparing the pre-mission merge-base commit against the current PR head, on the
same machine, in the same session, using the mission's own perf harness. It is explicitly **not**
a recovery of the original pre-migration capture — that data is gone. Where my own number lands
close to the previously-claimed "~2%" is coincidence of measuring the same code paths, not
confirmation that the original claim was itself real.

## NFR-005 / SC-008 — p95 latency A/B (fresh measurement, landing-time)

**Date**: 2026-08-04
**Machine**: Linux 6.8.0-136-generic x86_64, AMD Ryzen 9 7950X3D 16-Core Processor (32 logical
CPUs), Python 3.11.15 (`.python-version`-pinned in both checkouts), `uv 0.10.9`.

**Commits compared**:
- **BASE (pre-mission merge-base)**: `abca7ec9615e6e74caf9d7e807351a3a9a4d88a1` — "landing fold:
  fix CHANGELOG/docstrings to describe restored yaml-preferred/md-fallback presence, not
  yaml-only" — the last commit before `d49244cf4` (this mission's spec/plan/tasks) and before any
  WP01-WP10 commit. No FR-001 site had been touched yet.
- **HEAD (PR #3175 head at landing-fold time)**: `e309c08162776759bf30202b4229e8295479b7bb` on
  `pr-3175-local` — carries all of WP01-WP10 plus subsequent landing folds, including WP02's
  migration of `tasks_status_cmd.py:712,823` onto the charter-mediated factory.

**Harness used**: `tests/perf/test_tasks_status_baseline.py` as it exists at HEAD (added by this
mission's WP02, T006/T009; does not exist at BASE — `git show abca7ec96:tests/perf/test_tasks_status_baseline.py`
fails with "exists on disk, but not in abca7ec96"). Since the harness is a pure measurement
driver (builds its own fixture, invokes the CLI in-process via `CliRunner`, times with
`time.perf_counter()`) with no dependency on the FR-001 migration itself, the **identical,
unmodified test file** was copied byte-for-byte into a BASE worktree and executed there against
BASE's own `specify_cli` product code — this keeps the measurement method identical across both
arms rather than inventing a second one. Specifically: `test_capture_raw_timing_series`
(the developer utility test in that file) was run with `-s` to print its raw series.

**Fixture**: `_build_large_mission()` in the harness — 120 synthetic work packages (`_WP_COUNT =
120`, satisfying the 100+-WP requirement), one markdown task file + one status event per WP,
cycled across all 7 lanes (`planned/claimed/in_progress/for_review/in_review/approved/done`) and
across 4 agent-profile values including two real shipped built-in profile ids
(`python-pedro`, `human-in-charge`, `debugger-debbie`, and empty), so every rendered board/queue
row does real profile-repository lookup work, not a degenerate empty-lookup case.

**Method**: `uv run --no-sync pytest tests/perf/test_tasks_status_baseline.py::test_capture_raw_timing_series -q -s`
run in each worktree's own venv (BASE at `/tmp/perf-base-3175`, a `git worktree add` off
`abca7ec96`; HEAD in this fold's own worktree). Each invocation does 1 warm-up call (discarded,
absorbs import/doctrine-catalog cold-start) + 10 timed calls to `spec-kitty agent tasks status
--mission <fixture>` via the in-process `CliRunner`. Ran 3 full repetitions per side (30 samples
per side total), **interleaved** in actual execution order BASE, HEAD, HEAD, BASE, HEAD, BASE (not
a clean strict alternation — the 2nd HEAD run was an initial sanity check before the interleaving
plan was fixed — but no more than 2 consecutive same-side runs occurred, so machine drift is not
concentrated on one arm) to spread any drift (thermal, background load) across both arms rather
than letting it land entirely on whichever side ran first or last.

### Raw series (seconds), one row per repetition, in execution order

BASE (`abca7ec96`):
1. `[0.6415, 0.5863, 0.6044, 0.6212, 0.5966, 0.6182, 0.5971, 0.6331, 0.6040, 0.6530]`
2. `[0.5891, 0.5696, 0.5967, 0.6200, 0.5693, 0.6164, 0.6031, 0.6452, 0.5842, 0.5955]`
3. `[0.6201, 0.5840, 0.6131, 0.6212, 0.5783, 0.6065, 0.5733, 0.6347, 0.5786, 0.6370]`

HEAD (`e309c08` on `pr-3175-local`):
1. `[0.5862, 0.5920, 0.6171, 0.6160, 0.5851, 0.6273, 0.6294, 0.5810, 0.6232, 0.5983]`
2. `[0.5829, 0.6057, 0.5642, 0.6076, 0.5891, 0.6269, 0.6265, 0.5812, 0.6240, 0.5898]`
3. `[0.5817, 0.6191, 0.5855, 0.6283, 0.5863, 0.6163, 0.6284, 0.5837, 0.6127, 0.5834]`

### Computed statistics (pooled across the 3 repetitions, n=30 each side)

| Metric | BASE (`abca7ec96`) | HEAD (`e309c08`) | Delta |
|---|---|---|---|
| p95 (pooled, `sorted[int(0.95*30)]`) | 645.2 ms | 628.4 ms | **-2.60%** |
| mean | 606.4 ms | 602.6 ms | -0.62% |
| stdev | 23.46 ms | 19.69 ms | — |
| min / max | 569.3 / 653.0 ms | 564.2 / 629.4 ms | — |
| per-repetition p95 (ms) | [653.0, 645.2, 637.0] | [629.4, 626.9, 628.4] | — |
| per-repetition mean (ms) | [615.5, 598.9, 604.7] | [605.6, 599.8, 602.5] | — |

**NFR-005 threshold**: p95 within 10% of the pre-mission baseline (`abs(delta) <= 10%`).

**Verdict**: **PASS.** Measured delta is -2.60% (HEAD is ~2.6% *faster* at p95 than BASE, well
inside the ±10% budget), and the mean delta is -0.62%. This is a genuine measurement, not a
restatement of the prior unfalsifiable claim — it happens to land in a similar range to the
prior "~2%" figure, but that is coincidental (both measurements sample the same underlying code
paths); it is not evidence that the original, unpersisted capture was itself accurate.

**Caveat on what this measurement can and cannot support**: this is a same-machine, same-session
A/B taken at landing time, not the pre-migration-ordered capture SC-008 specifies. It answers
"does the merged code regress p95 latency on this fixture relative to the pre-mission commit,"
which is what NFR-005's regression guard needs — but it cannot retroactively prove the original
WP02 claim was correct, because that claim's underlying data no longer exists on any ref.

**Reproduction**:
```bash
# HEAD arm (run from a PR #3175 checkout):
uv run --no-sync pytest tests/perf/test_tasks_status_baseline.py::test_capture_raw_timing_series -q -s

# BASE arm (run from a worktree at the pre-mission commit, non-dot path,
# with the same test file copied in — it is not present on that commit):
git worktree add /tmp/perf-base-3175 abca7ec9615e6e74caf9d7e807351a3a9a4d88a1
cp tests/perf/test_tasks_status_baseline.py /tmp/perf-base-3175/tests/perf/test_tasks_status_baseline.py
cd /tmp/perf-base-3175 && uv run --no-sync pytest tests/perf/test_tasks_status_baseline.py::test_capture_raw_timing_series -q -s
```

**What was not measured**: nothing was skipped — both arms ran the identical harness, same
fixture size (120 WPs), same sample count (30 pooled per side), same machine/session. The only
asymmetry accepted is the harness file itself was *copied* onto the BASE worktree rather than
existing there natively (git-tracked only from WP02 onward), since it is a pure measurement
driver with no dependency on the FR-001 migration under test.

## Entries (append dated, in-the-moment)

- 2026-08-04 — Landing-fold remediation for SC-008 (see provenance note above): recorded this
  A/B here because the original WP02 in-session capture cited this exact path but was never
  pushed/persisted on any ref. Filed as a fold, not a WP02 amendment, per the pr-3175 landing
  pass instructions.
