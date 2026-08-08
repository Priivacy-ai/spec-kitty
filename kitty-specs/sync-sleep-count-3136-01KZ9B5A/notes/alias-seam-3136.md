# Alias seam and patch-target retargets — WP02 evidence

**Produced by**: WP02 (T005–T013), agent `claude` / profile `python-pedro`
**Lane worktree**: `/home/jeroennouws/dev/sk-missions/3136/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-b`
**Lane branch**: `kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-b`

This file is WP02's own notes file. It is a declared out-of-map planning write (`wps.yaml` WP02
block); `owned_files` carries no path under `kitty-specs/`. WP02 writes **nothing** into
`notes/constraint-enforcement-3136.md` — that file is WP07's, has exactly one writer, and WP07 runs
after WP02. The write direction is one-way: WP07 T037 may read this file and quote it.

---

## Toolchain — captured before any acceptance arm ran

```
$ date -u "+%Y-%m-%dT%H:%M:%SZ"
2026-08-07T01:18:19Z

$ export PATH="/home/jeroennouws/dev/sk-missions/3136/.venv/bin:$PATH"
$ command -v python pytest ruff mypy spec-kitty
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/pytest
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/mypy
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/spec-kitty

$ python -V
Python 3.12.13
$ pytest --version
pytest 9.0.3
$ ruff --version
ruff 0.15.12
$ mypy --version
mypy 1.20.2 (compiled: yes)
```

All five resolve under the **root checkout's** `.venv/bin`. The four gate values match WP01's
`notes/environment-3136.md` T001 transcript exactly: `3.12.13` / `9.0.3` / `0.15.12` / `1.20.2`.

**No `uv` subcommand of any kind was executed by WP02** — not even `uv --version`. The venv was
never disturbed and no recovery was performed.

### The lane worktree has no `.venv`, and that makes R5 live here too

The lane worktree carries no `.venv` of its own, so WP02 uses the root checkout's interpreter. The
root venv's editable-install path file points at the **root** `src`, so an unpinned import inside the
lane silently measures the wrong tree. Verified, not assumed:

```
$ python -c "import specify_cli; print(specify_cli.__file__)"                      # UNPINNED
/home/jeroennouws/dev/sk-missions/3136/src/specify_cli/__init__.py                 # ← ROOT tree

$ PYTHONPATH="$PWD/src" python -c "import specify_cli; print(specify_cli.__file__)"  # PINNED
/home/jeroennouws/dev/sk-missions/3136/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-b/src/specify_cli/__init__.py
```

**Every WP02 measurement pins `PYTHONPATH` to the lane's `src`.** An unpinned arm in this WP is
invalid by construction, exactly as WP01 R5 found for the base-tree arm.

---

## Base-ref discipline, re-derived this session

`98198e980` is the mission's **diff base**, not the merge base — WP01 recorded this as a prompt defect
(`RL-002`) and it is re-derived here rather than inherited:

```
$ git merge-base HEAD main
1aed89411b50203c8dbd9b284d70cc8fefbf32fa      # the actual merge base with main
$ git merge-base --is-ancestor 98198e980 HEAD ; echo $?
0                                             # 98198e980 IS an ancestor of HEAD
```

Every `git diff 98198e980` in this WP is therefore valid. Where a red had to be attributed as
pre-existing relative to `main`, the ref used is `1aed89411`.

## Lane provenance — and the destructive instruction that is live in this worktree

WP02 was started with `spec-kitty implement WP02 --mission sync-sleep-count-3136-01KZ9B5A` and every
edit was made inside `.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-b`. RL-007 was therefore never
reached. Allocation nevertheless failed once, on a **different** mechanism, recorded as `RL-012`.

**`AGENTS.md:589` in this lane — reached as `CLAUDE.md`, a symlink — still instructs the destructive
bare form** (`PWHEADLESS=1 uv run pytest tests/ui/ -q`). The fix landed on
`feat/sync-sleep-count-3136`, which the lane does not contain. Verified:

```
$ grep -c 'uv run' AGENTS.md                                    # lane-b
1
$ grep -c 'uv run' /home/jeroennouws/dev/sk-missions/3136/AGENTS.md   # main tree, fixed
0
```

**WP02 did not execute it, and did not fix it in-lane** (fixing would collide with the landed fix at
merge). Already covered by `RL-004` / `RL-006`. A second, machine-readable instance found this session
is recorded as `RL-013`.

---

## T005 — the guard, and the two reds on `98198e980`

The guard is `tests/sync/tracker/test_sleep_attribution_guard_3136.py`, committed **alone** as
`fd8ff6cd0`, before any implementation commit (coupling E).

`pytestmark = [pytest.mark.fast]` is a **top-level `ast.Assign`** (line 71) — verified by AST, because
the marker gates parse a top-level assignment and never see a class- or function-level mark.

### Red 1 — the sync shard, observed text recorded verbatim

Taken in a **throwaway detached worktree**, never by checking out base content in place:

```
$ git -C /home/jeroennouws/dev/sk-missions/3136 worktree add --detach /tmp/wp02-base-98198e9 98198e980
$ git -C /tmp/wp02-base-98198e9 rev-parse HEAD
98198e980045752a1f5ce0ba75796d3e5dddadf1
$ PYTHONPATH=/tmp/wp02-base-98198e9/src <venv>/python -c "import specify_cli; print(specify_cli.__file__)"
/tmp/wp02-base-98198e9/src/specify_cli/__init__.py        # R5 satisfied — the arm is valid
$ PYTHONPATH=/tmp/wp02-base-98198e9/src <venv>/python -c \
    "import specify_cli.tracker.saas_client as m; print('_sleep' in dir(m), '_monotonic' in dir(m), '_randbelow' in dir(m))"
False False False
```

```
PYTEST EXIT=1
5 failed in 56.82s
FAILED …::test_row1_backoff_sleep_call_count
FAILED …::test_row2_backoff_sleep_delays
FAILED …::test_row3_429_respects_retry_after
FAILED …::test_row4_429_defaults_to_5s
FAILED …::test_row5_origin_429_retries_then_raises
```

**Selected count: 5** (5 failed, 0 passed). The failure is structural, at `patch()` setup, and the
`[UNVERIFIED]` placeholder in the prompt is now **resolved by observation**:

```
E   AttributeError: <module 'specify_cli.tracker.saas_client' from
    '/tmp/wp02-base-98198e9/src/specify_cli/tracker/saas_client.py'> does not have the attribute '_sleep'
```

The prompt anticipated the wording *"no attribute '_sleep' in 'specify_cli.tracker.saas_client'"*.
That is **not** what `unittest.mock` raises; the observed form is the one quoted above, with the
module `repr` and its resolved path. Recorded as observed, not as predicted.

### Red 2 — `scripts/check_patch_targets.py`, naming all three alias targets

```
TARGETS EXIT=1
::error::Broken patch() targets (3 of 5058 checked):
  tests/sync/tracker/test_sleep_attribution_guard_3136.py:158: 'specify_cli.tracker.saas_client' has no attribute '_sleep'
  tests/sync/tracker/test_sleep_attribution_guard_3136.py:279: 'specify_cli.tracker.saas_client' has no attribute '_monotonic'
  tests/sync/tracker/test_sleep_attribution_guard_3136.py:280: 'specify_cli.tracker.saas_client' has no attribute '_randbelow'
```

Note the checker's own message order differs from the prompt's paraphrase as well:
`'<module>' has no attribute '<attr>'`.

**The control that makes this a real red.** A gate that reds on everything grades nothing, so the
pre-fix target was evaluated through the same `validate()` function in the same interpreter:

```
specify_cli.tracker.saas_client.time.sleep : None          <-- resolves; the control
specify_cli.tracker.saas_client._sleep     : "'specify_cli.tracker.saas_client' has no attribute '_sleep'"
specify_cli.tracker.saas_client._monotonic : "'specify_cli.tracker.saas_client' has no attribute '_monotonic'"
specify_cli.tracker.saas_client._randbelow : "'specify_cli.tracker.saas_client' has no attribute '_randbelow'"
```

Both reds are **expected, attributable and positive evidence**: a retarget that did not change the
resolved object would not have moved either gate.

### Cleanup — the throwaway is gone

```
$ git worktree remove --force /tmp/wp02-base-98198e9      # exit 0
$ git worktree list
/home/jeroennouws/dev/sk-missions/3136                     5b482029e [feat/sync-sleep-count-3136]
…/.worktrees/sync-sleep-count-3136-01KZ9B5A-coord          1cdee8540 [kitty/mission-…]
…/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-b         fd8ff6cd0 [kitty/mission-…-lane-b]
…/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-c         28bb40ac8 [kitty/mission-…-lane-c]
…/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-f         45a6f7b98 [kitty/mission-…-lane-f]
$ ls -d /tmp/wp02-base-98198e9
ls: cannot access '/tmp/wp02-base-98198e9': No such file or directory
```

`/tmp/wp02-base-98198e9` is absent. `lane-c` and `lane-f` are **sibling WPs running concurrently** —
see § *C-001* below.

---

## T006 / T007 / T008 — the seam (commit `e652ff9fa`)

### T006 — three module-scope aliases, by assignment

```
$ <venv>/python -c "import specify_cli.tracker.saas_client as m, time, secrets; \
    print(m._sleep is time.sleep, m._monotonic is time.monotonic, m._randbelow is secrets.randbelow)"
True True True
```

Arm 4b, structurally — `ast.Assign`, never `ast.FunctionDef`:

```
line 58: ast.Assign  _sleep = time.sleep
line 59: ast.Assign  _monotonic = time.monotonic
line 60: ast.Assign  _randbelow = secrets.randbelow
```

Zero `ast.FunctionDef` nodes named `_sleep` / `_monotonic` / `_randbelow`. Each carries a comment
naming it a declared testability seam for `#3136`, in dead-symbol-sweep vocabulary.

### T007 — the five call sites, POST-FIX line numbers

`C-004`'s permitted-hunk set is enumerated by pre-fix line number, and three new module-scope
definitions shift everything below them. Both readings, so the hunks can be read semantically:

| Pre-fix | Post-fix | Text |
|---|---|---|
| `:439` | **`:461`** | `_sleep(float(wait_seconds))` |
| `:481` | **`:503`** | `start = _monotonic()` |
| `:484` | **`:506`** | `elapsed = _monotonic() - start` |
| `:515` | **`:537`** | `jitter_basis_points = _randbelow(4000)` |
| `:518` | **`:540`** | `_sleep(jittered_delay)` |

Name substitution only; branch delta **0** for both functions. `delay = 1.0` and `cap = 30.0` were not
touched (post-fix `:500` / `:501`).

**After T008's delete the five sites moved again** — the final committed positions are `:461`, `:503`,
`:506`, `:537`, `:540` (the table above is already the post-T008 state; T007-only positions were
`:466`, `:508`, `:511`, `:542`, `:545`). Stated because a reviewer diffing an intermediate commit will
see the earlier set.

### T008 — `_poll_jitter_multiplier`: outcome **(A) DELETE**, and its price

```
$ grep -rn '_poll_jitter_multiplier' src/ tests/ | wc -l
0
```

**0**, never `1`. Priced:

- It had **zero callers** — the pre-edit `grep -rn` returned exactly one hit, its own definition.
- It disagreed with the live inline jitter on the upper bound (**1.2** vs **1.1999**). Deleting it
  removes the disagreement without moving the reachable delay set, so `C-004`'s *"delay values
  unchanged"* clause is satisfied **trivially** rather than argumentatively. Under (B) the reachable
  bound would have moved `1.1999 → 1.2`, which is the change `C-004` says does not happen.
- The `SC-007` arm-4d rerouted-site count therefore **stays at 5**. **WP05 needs no notification** —
  that obligation attaches only to outcome (B).
- One `C901` subject removed.

**The deferred half of T007's arm closes here.** Whole-file AST probe, after the delete:

```
$ <venv>/python -c "import ast,pathlib; t=ast.parse(pathlib.Path('src/specify_cli/tracker/saas_client.py').read_text()); \
    print([(n.lineno, ast.unparse(n.func)) for n in ast.walk(t) if isinstance(n, ast.Call) \
    and ast.unparse(n.func) in {'time.sleep','time.monotonic','secrets.randbelow'}])"
[]
```

`[]` — zero calls in the module whose callee resolves to any of the three. At the end of **T007** the
same probe printed `[(133, 'secrets.randbelow')]`, exactly as the prompt predicts, which is the
control proving the probe can see a hit.

### The seam is self-enforcing — measured, not asserted

With the seam landed and the decorators **not yet** retargeted, the census nodes failed **loudly**:

```
E   assert 0 == 3
E   AssertionError: Expected 'sleep' to be called once. Called 0 times.
```

`0`, not `3`. This is the property that makes skipping the 24 retargets **impossible to ship** under
the assignment form, and it is why the wrapper form was refused: a wrapper would have shown `3` here
and passed silently with the defect intact.

---

## T009 / T010 / T011 — the 24 retargets and the docstring (commit `154cad083`)

### The 24, re-derived by opening every line

| File | Pre-fix → post-fix | Live | Lines |
|---|---|---:|---|
| `test_saas_client.py` | `time.sleep` → `_sleep` | **13** | `:385 :412 :467 :502 :789 :809 :899 :939 :959 :1087 :1128 :1152 :1319` |
| `test_saas_client.py` | `time.monotonic` → `_monotonic` | **9** | `:386 :413 :468 :503 :790 :810 :1088 :1129 :1153` |
| `test_saas_client.py` | `secrets.randbelow` → `_randbelow` | **1** | `:499` (target string; the `@patch(` spans `:498`–`:501`) |
| `test_saas_client_origin.py` | `time.sleep` → `_sleep` | **1** | `:229` |

`13 + 9 + 1 + 1 = ` **24**. Every line was opened before editing and asserted to contain the expected
pre-fix string; the edit script aborts on any mismatch.

### DoD 5's instrument — AST `patch()` nodes, never grep

```
 13  tests/sync/tracker/test_saas_client.py         specify_cli.tracker.saas_client._sleep
  9  tests/sync/tracker/test_saas_client.py         specify_cli.tracker.saas_client._monotonic
  1  tests/sync/tracker/test_saas_client.py         specify_cli.tracker.saas_client._randbelow
  1  tests/sync/tracker/test_saas_client_origin.py  specify_cli.tracker.saas_client._sleep
```

`_sleep` **13 + 1 = 14**, `_monotonic` **9**, `_randbelow` **1**. The three pre-fix strings are
**absent from the listing entirely** — **0** in both files. (The listing also shows `httpx.Client`
41/20 and `_force_refresh_sync` 4/2, untouched.)

### The prose occurrences — THREE, not two, and the measured counts

The prompt insists on *"TWO occurrences, not one"*. There are **three**; the third is
`test_saas_client.py:39`, carrying `saas_client.time.monotonic`. Recorded as **`RL-009`**.

| Site | String | Disposition |
|---|---|---|
| `:39` | `…time.monotonic` | **Left alone** — T009 step 5 requires it; it is past-tense history that becomes *more* accurate after the fix |
| `:559` → `:562` | `…time.sleep` | **Rewritten, not swapped** — see below and `RL-010` |
| `:715` → `:724` | `…time.sleep` | **Explicitly FROZEN**, with a `measured pre-fix` clause in the text |

**`:559` could not be string-swapped.** The sentence *asserts* that this target patches the stdlib
`time` module and that the recorder is process-wide. Substituting `_sleep` would have made the
codebase state the opposite of this mission's finding. The paragraph was rewritten: the pre-fix hazard
in the past tense, the pre-fix string retained as the *named historical hazard*, and a new clause
naming the post-fix `…_sleep` target and why it is unreachable. The **site changes**, so `WP03` T019
arm F's `(file, line)` pin still sees a moved site — flagged for WP03's reviewer.

**`:715` frozen, and why.** It is a historical *measurement record* (*"Neither run put any extra call
on … (still 12, still all `MainThread`)"*). Rewriting a past observation to name a target that did not
exist when it was taken would falsify the record. The text now says so in one clause.

**Measured pre- and post-edit grep counts** — reported, not reconciled by editing prose:

| Grep | Pre | Post | Why |
|---|---:|---:|---|
| `saas_client\.time\.sleep` in `test_saas_client.py` | **15** | **2** | `:562` history + `:724` frozen; 13 decorators moved |
| `saas_client\.time\.monotonic` in `test_saas_client.py` | **10** | **1** | `:39` frozen by T009 step 5; 9 decorators moved |
| `saas_client\.secrets\.randbelow` in `test_saas_client.py` | **1** | **0** | the single decorator moved |
| `saas_client\.time\.sleep` in `test_saas_client_origin.py` | **1** | **0** | the single decorator moved |

The prompt predicts `15 → 0` or `15 → 1`, and predicts nothing for `monotonic`. The measured answers
are **2** and **1**. Both survivors of each are prose; **the AST decorator count for all three pre-fix
strings is 0**. Recorded as `RL-009` / `RL-010` rather than silently landing a number the DoD does not
predict, and emphatically **not** fixed by editing prose to satisfy a numeric gate.

### T011 — the false docstring claim

`:55-57` claimed *"there the second value \*is\* the assertion, and it never reaches ``_request``"*.
False: `[0.0, 301.0]` is a `side_effect` **stimulus**, and the node's only assertion is the
`pytest.raises`. Corrected — a correction, not a deletion.

```
$ grep -cE 'is\*? the assertion' tests/sync/tracker/test_saas_client.py
0                                        # was 1
$ grep -c 'side_effect stimulus' tests/sync/tracker/test_saas_client.py
1                                        # was 0
```

The plain-text form `grep -c 'is the assertion'` returns **0** on both trees and grades nothing — the
`-E` form is the binding one, as the prompt says.

**The cited line moved.** The DoD says the correction must name `:806`; that is the **base-tree**
number. The correction itself, plus the `:559` and `:715` edits above it, push the `pytest.raises` to
**`:819`** (+13, re-derived and verified by reading line 819 back). The docstring therefore names
`:819` as live and `:806` as its pre-fix location on `98198e980`, so the citation is true *and* the
DoD's literal `:806` grep is satisfiable. Recorded as `RL-011`.

### Diff shape

`git diff 98198e980 -- <the two census files>` → `49 insertions(+), 36 deletions(-)`. Every changed
line is (a) inside the `:55-57` docstring correction, (b) a `patch()` target-string move, or (c) the
`:559` / `:715` prose. **No assertion expression changed** — the only `assert`-matching removed line is
docstring prose inside (a).

### Both reds are now green

```
$ <venv>/python -m pytest <4 census nodes in test_saas_client.py> -q -ra -n0     EXIT=0   4 passed in 62.35s
$ <venv>/python -m pytest <origin census node>                -q -ra -n0        EXIT=0   1 passed in 60.34s
$ <venv>/python scripts/check_patch_targets.py                                  EXIT=0
All 5058 patch() targets valid.
```

---

## `_PINNED_LEAKS` — 12, and which reading of "11" is wrong

`tests/sync/_leak_guard.py:333` is an **`ast.AnnAssign`**, not an `ast.Assign`. The control the prompt
demands, run first:

```
CONTROL ast.Assign filter -> 0 hits          # a walk filtering on ast.Assign finds NOTHING
ast.AnnAssign filter      -> 1 hit, line 333
len(node.value.elts)      -> 12
grep -c '_PinnedLeak('    -> 12              # agrees
```

**12 is correct; "11" is the wrong number, and it is a miscount of _kind_ — an observability tally
read as a registry tally.** Evidence:

- All **12** entries carry the literal `'#3130'`. So the alternative explanation the spec offers —
  *"a pin that is not a `#3130` leak"* — is **refuted**: there is no such pin.
- Exactly **one** of the 12 carries `requires_clean_baseline=True`
  (`_leak_guard.py:412`, `test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target`,
  `baseline_watch='E51/E52'`). That pin is **suppressed as unobservable** whenever its own
  before-snapshot for `SPEC_KITTY_SAAS_URL` is already dirty — which is the ordinary case.
- `12 − 1 = ` **11**. An empirically-derived count of *leaks actually observed in a run* lands on 11
  while the registry holds 12.

So: the registry number **12** stands, `SC-008`'s pin at 12 is correct, and "11 confirmed leaks"
should be read as "11 unconditionally observable pins". Two numbers are no longer left in the tree.

**WP02 added zero pins**: `git diff 98198e980 -- tests/sync/_leak_guard.py | grep -cE '^\+\s*_PinnedLeak\('` → **0**.

---

## C-001 — window discipline

WP01 holds the `tests/sync` window (`PENDING — WP07 (T043)`, not released) and WP02 is its intended
user. **No sweep of `tests/sync` was run, and `tests/cli` was not touched at any point.** Every run in
this WP is a targeted node-id selection or the single guard file. Node ids used:

- `tests/sync/tracker/test_sleep_attribution_guard_3136.py` (whole file — 5 nodes, this WP's own)
- `…/test_saas_client.py::TestPolling::test_exponential_backoff_intervals`
- `…/test_saas_client.py::TestPolling::test_timeout_after_5_minutes`
- `…/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`
- `…/test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing`
- `…/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises`

The NFR-004 leak arm additionally runs the two census **files** in full at `-n0` — that is prescribed
by T012 step 4 and is not a `tests/sync` sweep.

**Concurrency observed.** `lane-c` and `lane-f` worktrees appeared mid-WP and `lane-c` was running
`tests/architectural/test_patch_seam_census_control.py` during WP02's arms. That is a **different
shard**, so the C-001 `tests/sync` window was not contended. It cannot perturb WP02's mock-based
assertions either: mocks are process-local, and separate OS processes cannot share a recorder's state.

---

## The guard's contents — DoD items 1a–1e, graded directly

A guard whose whole body were `with patch("…_sleep"): pass` would be red on `98198e980`, green on
head, pass 10/10 and 6/6, and add zero `^ERROR tests/`. It would satisfy every *other* DoD item. These
five items are the only thing standing between that cheat and approval, so they are evidenced here.

### 1a — ten arms, five rows × two. Counted, not asserted.

```
test functions                                  : 5
arm (a) markers                                 : 5
arm (b) markers                                 : 5
with pytest.raises(AssertionError):  (arm b)    : 5
assert stdlib_mock.call_count >= _MIN_STDLIB_CALLS : 5
assert alias_mock.call_count == …               : 5
```

Five rows are written out as **five separate test functions**, not a loop and not a parametrisation,
so each arm-(b) expression is individually greppable and individually diffable.

### 1b — arm (b) is the LITERAL pre-fix form, read off the STDLIB recorder

Each row diffed against `98198e980`'s own assertion text. Rows 1–2 inline the base's two intermediate
bindings (`sleep_calls = mock_sleep.call_args_list` at base `:783`, `delays = [c.args[0] for c in
sleep_calls]` at base `:785`); rows 3–5 are character-identical but for the recorder name.

| # | `git show 98198e980:<file>` | guard arm (b) |
|---|---|---|
| 1 | `:784` `assert len(sleep_calls) == 3` | `:350` `assert len(stdlib_mock.call_args_list) == 3` |
| 2 | `:786` `assert delays == [0.9, 2.0, 4.4]` | `:367` `assert [c.args[0] for c in stdlib_mock.call_args_list] == [0.9, 2.0, 4.4]` |
| 3 | `:937` `mock_sleep.assert_called_once_with(3.0)` | `:385` `stdlib_mock.assert_called_once_with(3.0)` |
| 4 | `:957` `mock_sleep.assert_called_once_with(5.0)` | `:403` `stdlib_mock.assert_called_once_with(5.0)` |
| 5 | origin `:261` `mock_sleep.assert_called_once_with(2.0)` | `:428` `stdlib_mock.assert_called_once_with(2.0)` |

Every arm (b) reads `stdlib_mock`, **never** `alias_mock`. This is the settled reading: post-fix the
alias recorder sees exactly `3 / 1 / 1 / 1`, so an arm (b) pointed at it would **pass rather than
raise** and would grade nothing — silently inverting the guard. The stdlib mock is bound with the
**literal pre-fix decorator target** `specify_cli.tracker.saas_client.time.sleep`, so the polluted
view is reached the same way the pre-fix decorators reached it.

**Arm (b) and the probe floor are ONE instrument.** Arm (b) raises *because* the probe polluted the
stdlib view; a probe landing 0 calls would make all five arm-(b) expressions pass, and
`pytest.raises(AssertionError)` would then fail. A vacuous probe is structurally impossible here, not
merely discouraged. This is stated in a comment on the arm block in the guard itself.

### 1c / 1d — both numbers read off recorders, printed per row

Captured with `-s` (`5 passed in 72.35s`):

```
[#3136 guard] row=1 census_site=test_saas_client.py:784        probe_thread=sk3136-stdlib-sleep-probe stdlib_mock.call_count=150 alias_mock.call_count=3
[#3136 guard] row=2 census_site=test_saas_client.py:786        probe_thread=sk3136-stdlib-sleep-probe stdlib_mock.call_count=150 alias_mock.call_count=3
[#3136 guard] row=3 census_site=test_saas_client.py:937        probe_thread=sk3136-stdlib-sleep-probe stdlib_mock.call_count=150 alias_mock.call_count=1
[#3136 guard] row=4 census_site=test_saas_client.py:957        probe_thread=sk3136-stdlib-sleep-probe stdlib_mock.call_count=150 alias_mock.call_count=1
[#3136 guard] row=5 census_site=test_saas_client_origin.py:261 probe_thread=sk3136-stdlib-sleep-probe stdlib_mock.call_count=150 alias_mock.call_count=1
```

- `stdlib_mock.call_count` = **150** every row, against the asserted floor of **100** (NFR-001). It is
  read off a `patch()` **recorder**, not self-reported by the probe.
- `alias_mock.call_count` is an **equality**: `3, 3, 1, 1, 1` — i.e. **`3 / 1 / 1 / 1` across the four
  census nodes**, rows 1 and 2 sharing the backoff node. Also read off a `patch()` recorder.
- Both mocks are bound in **one** window (`_dual_recorder_window`).
- The probe thread is named `sk3136-stdlib-sleep-probe`, so an unattributable thread would be visible.
- The five row identifiers and their census sites are printed, so a reviewer can count the rows without
  reading the source.

**This is the pollution-immunity result in one line: 150 foreign `time.sleep` calls landed on the
stdlib view while the alias view saw exactly the attributed number, in the same patch window.**
Pre-fix, those 150 would have been on the same recorder the assertion reads.

### 1e — every probe joined in a `finally`, spawn gated on first recorded call

```python
163 def _run_polluted(body: Callable[[], None]) -> str:
168     probe = _SleepProbe()
169     probe.start()
170     try:
171         body()
172     finally:
173         # NFR-004 — every probe is joined in a `finally`, on every path
174         # including an assertion failure inside `body`.
175         probe.join()
```

All **5** rows route through `_run_polluted`, so the single `finally` covers every row on every path,
including an assertion failure inside the body. `probe.join()` raises if the thread is still alive
after the timeout rather than leaking it silently.

The spawn gate is `first_call_recorded`, a `threading.Event` **set after the probe's first recorded
call** (`if index == 0: self.first_call_recorded.set()`), and `start()` blocks on it and raises if it
never arrives. So the production call cannot begin before pollution is genuinely in flight.

### Scope, stated honestly

The guard proves the seam exists, is import-bound, is load-bearing (the production call sites really
route through it — a missed reroute shows up as `alias_mock.call_count == 0`), and is immune to
foreign `time.sleep` traffic. It does **not** catch a fully-retargeted `def` wrapper, which is
runtime-immune and passes every arm here — that refusal is static (`SC-007` arm 4b: `ast.Assign`,
never `ast.FunctionDef`). Nor does it inspect the shipped test files' decorators; those are graded
from AST `patch()` nodes by arm 4c. **The prompt's claim that SC-005 "catches incomplete-retarget
trees" is only true of an incomplete *reroute* (T007), not an incomplete *retarget* (T009/T010)** —
the guard patches `_sleep` by name, so it is indifferent to what the census files' decorators target.
Runtime and static evidence are complementary here, not interchangeable.

---

## T012 — both reds green, then the determinism arms

### Step 1 — both reds green

```
$ <venv>/python -m pytest <guard> -q -ra -p no:cacheprovider -n0     EXIT=0
5 passed in 59.17s
$ <venv>/python scripts/check_patch_targets.py                       EXIT=0
All 5058 patch() targets valid.
```

Both gates that the guard commit reddened are now green. Neither red was breakage; both were the
gates correctly reporting that the alias attributes did not yet exist.

### Step 2 — NFR-002: **10 of 10**, per-run counts, never a summary verdict

| run | EXIT | result | wall |
|---:|---:|---|---|
| 1 | 0 | `5 passed` | 58.46s |
| 2 | 0 | `5 passed` | 47.49s |
| 3 | 0 | `5 passed` | 49.44s |
| 4 | 0 | `5 passed` | 55.92s |
| 5 | 0 | `5 passed` | 62.60s |
| 6 | 0 | `5 passed` | 60.76s |
| 7 | 0 | `5 passed` | 61.16s |
| 8 | 0 | `5 passed` | 71.82s |
| 9 | 0 | `5 passed` | 71.78s |
| 10 | 0 | `5 passed` | 71.29s |

**10/10.** Selected count 5 every run, 0 failed. The probe is not racing the test body.

### Step 3 — NFR-003: topology invariance, **6 runs, 6 identical pass sets**

Four census nodes: the backoff node, the two 429 nodes in `test_saas_client.py`, and the origin 429
node — i.e. the `3 / 1 / 1 / 1` set.

| topology | run | EXIT | result | wall |
|---|---:|---:|---|---|
| `-n0` | 1 | 0 | `4 passed` | 63.13s |
| `-n0` | 2 | 0 | `4 passed` | 64.25s |
| `-n0` | 3 | 0 | `4 passed` | 63.11s |
| `-n auto --dist loadfile` | 1 | 0 | `4 passed` | 132.63s |
| `-n auto --dist loadfile` | 2 | 0 | `4 passed` | 129.93s |
| `-n auto --dist loadfile` | 3 | 0 | `4 passed` | 124.13s |

**6 runs, 6 identical pass sets**, verdicts identical across topologies.

### Step 4 — NFR-004 / SC-008: leak neutrality, `-n0` pinned

```
$ <venv>/python -m pytest <guard> tests/sync/tracker/test_saas_client.py \
    tests/sync/tracker/test_saas_client_origin.py -q -ra -p no:cacheprovider -n0
EXIT=0
78 passed in 68.96s (0:01:08)
```

`-n0` is pinned deliberately: under xdist the controller prints a different line and a real `-n 4`
run reports `inspected 0 test(s)`. That false red was not "fixed".

**The `^ERROR tests/` probe, controlled against a known answer** — a `0` from a grep is only evidence
if the grep works:

```
$ cat /tmp/…/wp02-grep-control.txt          # fixture with KNOWN answers
ERROR tests/sync/tracker/test_alpha.py::test_one
ERROR tests/sync/tracker/test_beta.py::test_two
ERROR    some unrelated log line from a library
2026-01-01 ERROR tests/ not at line start
ERROR tests/cli/test_gamma.py::test_three

$ grep -c '^ERROR tests/' <control>   ->  3     # known answer 3 — anchored form correct
$ grep -c '^ERROR '       <control>   ->  4     # known answer 4 — over-matches, as documented
```

Applied to the real run, with existence and identity twins **before** the zero is read:

```
test -s                              -> NON-EMPTY
wc -l                                -> 14
grep -c 'passed'   (twin, must be >=1) -> 1
grep -c '^ERROR tests/'              -> 0        <- a REAL zero
```

On this particular run `^ERROR ` also returns `0`, so **this arm does not by itself discriminate the
two patterns** — the control fixture above is what does. Stated rather than glossed (the same honesty
WP01 applied to its own arm).

```
$ git diff 98198e980 -- tests/sync/_leak_guard.py | grep -cE '^\+\s*_PinnedLeak\('
0
```

WP02 added **zero** pins. The `_PINNED_LEAKS` count and the 12-vs-11 reconciliation are in their own
section above.

---

## T013 — SC-003 mutation arms (applied and reverted, NEVER committed)

**Revert method.** Byte-exact copies were taken before the first mutation and copied back after each
arm. **No `git checkout -- .`, no `git reset --hard`, no `git clean`, no `git stash`** was used at any
point in this WP — those commands destroyed 468 uncommitted lines of a sibling's work earlier in this
mission. `cmp -s` against the pristine copies is the revert proof.

### Arm 1 — wrong value (`delay = 1.0` → `1.5`, post-fix `:500`)

```
ARM1 EXIT=1
1 failed in 71.60s
E   assert [1.35, 3.0, 6...0000000000005] == [0.9, 2.0, 4.4]
E     At index 0 diff: 1.35 != 0.9
```

**The pinned literal is satisfied, but pytest truncated it.** `-q` elides the middle of a long repr,
so the transcript shows `6...0000000000005` and a naive `grep -c '6.6000000000000005'` returns **0**.
The visible head (`1.35, 3.0, 6`) and tail (`0000000000005`) are consistent with
`6.6000000000000005` and **inconsistent with `6.6`**. Confirmed independently against production
arithmetic (`6.0 * 1.1`):

```
$ <venv>/python -c "d=1.5
… for bp in (1000,2000,3000): f=0.8+(bp/10000); out.append(d*f); d=min(d*2,30.0)"
[1.35, 3.0, 6.6000000000000005]
```

Anyone re-running this arm and wanting the untruncated literal in the transcript must use `-vv`.

### Arm 2 — wrong per-call value (`_sleep(float(wait_seconds) * 2)`, post-fix `:461`)

```
ARM2 EXIT=1
3 failed in 70.98s
E   AssertionError: expected call not found.   (x3)
  names 6.0 : 1     names 10.0 : 1     names 4.0 : 1
```

The three 429 census nodes, each naming its doubled value — `3.0→6.0`, `5.0→10.0`, `2.0→4.0`.

### Arm 3 — wrong cardinality. **Redone, because the first attempt was red for the WRONG reason.**

The first attempt applied exactly what the prompt prescribes — duplicate `_sleep(...)` at `:461` and
add a fourth `pending` response — and produced `4 failed`. But the backoff node's failure was:

```
E   StopIteration
```

That is a **fixture artifact**, not the cardinality defect: the node's `_randbelow` mock carries
`side_effect=[1000, 2000, 3000]` (three values), and a fourth `pending` forces a fourth poll
iteration, which exhausts the list before the count assertion is ever reached. Arm 3 requires each
node to fail **on the count**. Counting that run would have repeated the mistake two sibling WPs
already had to redo.

**The prompt's arm-3 mutation set is incomplete** and is recorded as `RL-016`. The corrected set adds
a third element — extend the jitter list to four values — so the loop completes and the assertion is
actually evaluated:

```
ARM3 EXIT=1
4 failed in 116.32s
E   assert 4 == 3                                                      <- backoff node, the COUNT
E   AssertionError: Expected '_sleep' to be called once. Called 2 times.
E   Calls: [call(3.0), call(3.0)].
E   AssertionError: Expected '_sleep' to be called once. Called 2 times.
E   Calls: [call(5.0), call(5.0)].
E   AssertionError: Expected '_sleep' to be called once. Called 2 times.
E   Calls: [call(2.0), call(2.0)].

StopIteration present : 0
'assert 4 == 3'       : 1
'Called 2 times'      : 3
```

**4 failed, every one on a count (`4 != 3`, `2 != 1`), none on a delay value, zero `StopIteration`.**
This is the arm that refuses `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]`, which is
green on a cardinality mutation and would otherwise satisfy every other criterion.

### Arm 4 — revert everything

```
byte-identical to pristine?
  SRC: IDENTICAL
  FIX: IDENTICAL
ARM4 EXIT=0
4 passed in 72.41s
$ git status --porcelain src/ tests/
                                        # (empty)
```

`4 passed`, both files byte-identical to their pre-mutation copies, working tree clean. The same
`cmp` + empty-`git status` proof was re-taken after the arm-3 redo. **No mutation was committed.**

---

## T013 — lint, types, suppressions, config

```
$ <venv>/ruff check <the four owned files>
All checks passed!
$ <venv>/ruff check --select C901 <the four owned files>
All checks passed!
```

`ruff format` was **never** run, in this WP or anywhere near it.

```
$ git diff 98198e980 -- src/ tests/ | grep -cE '^\+.*(# noqa|# type: ignore)'
0
$ git diff 98198e980 -- src/ tests/ | grep -cE '^\+'
513                                     # CONTROL — the 0 above is read against 513 added lines
```

**`ruff.toml` / `pyproject.toml` diff, reported as DIFF TEXT rather than as a count:**

```
$ git diff 98198e980 -- ruff.toml pyproject.toml
```

*(no output — both files are untouched by this WP; `ruff.toml` exists at the repo root, so the silence
is a real silence and not a missing-path artifact)*

### `mypy --strict` — graded as "no NEW findings", not "clean"

```
$ <venv>/mypy --strict src/specify_cli/tracker/saas_client.py
src/specify_cli/tracker/saas_client.py:184: error: Returning Any from function declared to return "str | None"  [no-any-return]
src/specify_cli/tracker/saas_client.py:185: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)
```

**These two are the file's pre-existing baseline**, proved by running the same command against the
base tree's own copy of the file:

```
$ git show 98198e980:src/specify_cli/tracker/saas_client.py > /tmp/wp02-base-saas.py
$ <venv>/mypy --strict /tmp/wp02-base-saas.py
/tmp/wp02-base-saas.py:162: error: Returning Any from function declared to return "str | None"  [no-any-return]
/tmp/wp02-base-saas.py:163: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)
```

Same count, same code, same function (`_current_team_slug_sync` — `return team.id` and
`return session.teams[0].id`). The `+22` shift is exactly WP02's net insertion above them. **Exactly
these two findings and no others: the criterion is met.** Not fixed (outside `C-004`'s permitted-hunk
set) and not `# type: ignore`d (the suppression grep above is `0`).

**The prompt's own citation has moved.** It gives `:162-163` as the post-WP location; that is the
**base** location. Post-fix they are at **`:184-185`**. Recorded as part of `RL-015`.

**They are NOT filed, and that is a governance conflict rather than an omission** — DoD item 8 requires
filing per the charter's *Pre-existing Failure Reporting Rule*, while the operator direction bars
`gh issue create`. WP01 recorded this conflict as latent at `RL-005`; WP02 is the first WP to trigger
it. There is **no issue number** to hand to WP07 T042. Full detail at `RL-015`.
