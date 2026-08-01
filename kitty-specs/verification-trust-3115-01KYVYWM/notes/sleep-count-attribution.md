# FR-005 — the sleep-count attribution, and why the negative is legitimate

WP06's record, landed by the orchestrator because a lane cannot write `kitty-specs/`. It took three
review rounds; the first two negatives were rejected, and the reasons are the transferable part.

## The victims were wrong for the whole mission, until round 2

`#3115`'s issue body names `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after`.
**That test has never exhibited the failure.** From the live CI log (job `91126025663`, run
`30621215287`, `fast-tests-sync`, Python 3.12.3, `-n auto --dist loadfile`, head `bb2020fea9`):

```
tests/sync/tracker/test_saas_client.py:534: in test_exponential_backoff_intervals
    assert len(sleep_calls) == 3
E   assert 71 == 3                                                            [gw5]

tests/sync/tracker/test_saas_client_origin.py:261: in test_429_retries_then_raises
    mock_sleep.assert_called_once_with(2.0)
E   AssertionError: Expected 'sleep' to be called once. Called 556 times.     [gw2]
```

The wrong node propagated from the issue into `spec.md`, `WP06-sleep-attribution.md`, all ten of
WP06's floor selections, and every orchestrator brief. **No layer of review caught it, because every
layer inherited it from the layer above and nobody re-opened the log.** One of the real victims sits
123 lines above the docstring WP06 wrote in its own owned file.

## The producer, named

**CPython's `subprocess.Popen._wait(timeout)` POSIX busy-wait.**

```python
delay = 0.0005                              # 500 us -> initial delay of 1 ms
delay = min(delay * 2, remaining, .05)
time.sleep(delay)
```

CI's `556 = 1 + 6 + 549` is **one** `Popen.wait(timeout=…)` caught in flight: the victim's own
`call(2.0)`, one complete six-term ramp `0.001 → 0.032`, then the loop saturated at its cap for the
rest of the patch window. Reproduced independently by both the implementer and the reviewer with
probes containing **no repo code**, and verified identical on Python 3.12 — the family CI runs.

### The structural error that made it look unattributable

Round 2 read the fingerprint as **two** producers — an unfound doubling backoff, plus a flat `0.05`
poll loop attributed by literal match to `restart.py:147` and `daemon.py:1382`.

**It is one producer.** A geometric ramp that flattens is a single loop whose delay saturated; the
`0.05` is not a poll-interval literal, it is that loop's **cap**. The correct search key was never
"a doubling backoff" but **"a doubling backoff capped at 0.05"** — and there is precisely one such
loop in any Python process.

`restart.py:147` and `daemon.py:1382` are **falsified**: they emit a flat `0.05` with no ramp and
cannot produce the observed prefix.

### The scope that excluded the answer

Round 2's grep covered `src/` and `tests/`. The answer is in the **standard library** — which is
where it had to be, because FR-005's own stated mechanism is that the patch target resolves to the
*stdlib* `time` module and therefore records *any* stdlib caller. **The scope that made the search
tractable is the scope that made it wrong.**

## A new instance of rot mode #5, in a third-party library

**`psutil.Process.wait` is invisible to `@patch("…time.sleep")`.** `psutil._psposix.wait_pid_posix`
binds `_sleep=time.sleep` as a **function-default value** at psutil's import time:

```
(pid, timeout=None, _waitpid=<built-in function waitpid>, _timer=<built-in function monotonic>,
 _min=<built-in function min>, _sleep=<built-in function sleep>, _pid_exists=<function pid_exists>)
```

The default is already a concrete object, not a deferred lookup. A later patch rebinds the attribute
on the `time` module; the default still holds the original. Measured: **0** recorded calls versus
thousands for a real `Popen.wait` under the identical patch.

This prunes `daemon.py:1000-1032 _kill_and_cleanup` and `dashboard/lifecycle.py:_terminate_by_pid` —
both of which were on the reviewer's own shortlist — as producers of **any** mock inflation, not
merely of this fingerprint.

**It survives rot mode #4** (a branch dead locally and live on CI). The empirical control only
exercised `wait_pid_posix`, because `can_use_pidfd_open()` and `can_use_kqueue()` are both `False`
here. On a host where pidfd is available — plausibly CI's `blacksmith-4vcpu-ubuntu-2404` — the call
goes to `wait_pid_pidfd_open`, which uses `select.poll()` and contains **no sleep at all**. Both
branches exclude psutil, so the exclusion is environment-independent.

## Why the negative is legitimate — the closure argument

The recorder is installed as `side_effect` on the **same mock object** whose `call_count` raises the
failure. So **any producer that inflates the count necessarily passes through the recorder.** Every
evasion class runs the other way — psutil's default binding, `from time import sleep` rebinding, a C
extension sleeping below the Python attribute, a different OS process — each evades the *mock*, and
therefore cannot inflate `call_count` at all.

**The instrument's blind spots are a subset of the failure's blind spots.**

One real exception exists and was measured: if a test *reassigns* `side_effect` on the sleep mock
after patch entry, the recorder is silently displaced while `call_count` keeps incrementing.
`grep -rn "sleep\.side_effect\s*=" tests/sync/` → **0**. The class is empty here.

## The instrument was proven before its silence was trusted

`traceback.extract_stack()` capture added to the recorder (5 samples per `(site, thread)`, modal
signature reported). Two independent positive controls:

- **Synthetic**: a standalone `Popen.wait` leak attributed to `subprocess.py:2047 in _wait`, reached
  independently by implementer and reviewer with different probes.
- **Real**: the full serial cone run caught a live, stack-named leak at `sync/batch.py:674` via
  `background.py`'s final-sync thread — WP04's E24/E25 and issue **#3130**'s leaks 1–2, whose
  existence was established elsewhere.

Then: a targeted 291-test selection covering every genuine `subprocess.Popen.wait` site reachable
from `tests/sync/` (`280 passed, 11 skipped`, 12 calls, all `MainThread`), and the full cone
(`2370 passed, 18 skipped`, still 12 calls on the FR-005 site). **Zero pollution on either victim,
measured by an instrument that demonstrably sees leaks when they are present.**

## The floor (T020) — F-b, could not reproduce locally

**Ten** selections, all passing, all with collected counts (WP06's record and issue #3136 both say
"eleven"; the enumeration resolves to ten — corrected here at mission close, flagged by WP14's
reviewer): single test (1); whole file (53); tracker
cone serial and `-n auto` (468); full `tests/sync` at `-n auto` (2388) and serial (2388);
daemon-siblings + victim serial and `-n 2` (171); CI-replica at `-n auto` and `-n 4` (2108 + 11
skipped). The true victims were inside 9 of the 10 and passed.

## What was not attempted, and why that is the right residual

**A live CPU-contention reproduction matching CI's 4-vCPU runner.** It was the right hypothesis for
*why a thread outlives its join*, but it cannot name a producer — and the producer is now named
without it.

The reviewer's own probe supplied the evidence for leaving it: its first attempt **did not fire**,
because the probe thread had not yet entered the wait loop when the sub-millisecond test body ran. A
spawn race. That is direct evidence for the negative — the intruder must be *actively inside* a
sleep loop during a very narrow window, so missing it is the default outcome, and contention is
simply what makes hitting it likelier. **The negative is consistent with the mechanism rather than
in tension with it.**

## Carried into WP14

A named producer construct; a candidate set with psutil-backed waits excluded by construction and
`restart.py:147`/`daemon.py:1382` falsified; the corrected victim node-ids; and one honest gap — the
contention reproduction — handed forward rather than spent.
