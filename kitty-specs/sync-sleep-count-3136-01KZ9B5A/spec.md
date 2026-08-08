# Mission Specification: Sleep-count assertions survive concurrent sleepers

**Mission Branch**: `feat/sync-sleep-count-3136`
**Created**: 2026-08-05
**Status**: Draft
**Input**: Upstream issue [`Priivacy-ai/spec-kitty#3136`](https://github.com/Priivacy-ai/spec-kitty/issues/3136) plus its two comments (2026-08-01 close-of-mission corrections; 2026-08-05 PR #3209 blocking evidence). Base `upstream/main` @ `98198e980` (verified: `git rev-parse upstream/main` = `98198e980045752a1f5ce0ba75796d3e5dddadf1` — **criteria pin the SHA, not the moving ref**). Predecessor record: `kitty-specs/verification-trust-3115-01KYVYWM/notes/sleep-count-attribution.md`.
**Revision R2** (2026-08-05): revised against [`analysis-report.md`](analysis-report.md) — the post-spec adversarial squad's findings and the operator's two rulings (**R-1** product-side module-local alias; **R-2** mechanism-keyed predicate over `tests/sync/`). That report is the authoritative directive for this revision. Its measured corrections supersede the R1 text wherever they disagree; every superseded claim is retained with its correction rather than deleted.

---

## Problem

`tests/sync/` contains assertions whose truth value is a function of a **process-global**
call counter. `src/specify_cli/tracker/saas_client.py:19` is a bare `import time`, so
`@patch("specify_cli.tracker.saas_client.time.sleep")` rebinds the `sleep` attribute **on the stdlib
`time` module object**. For the whole patch window the mock's recorder counts `time.sleep` calls from
**any live thread in the pytest-xdist worker process**, stdlib callers included.

**The mechanism is the bare import, not the attribute.** `@patch("a.b.c.attr")` where `a.b.c` resolves
at import to a `ModuleType` always patches that shared module object. `time`, `secrets`, `subprocess`,
`random` and `os` are all reachable this way, and all five appear in `tests/sync/` today. Keying on
`time.sleep` closes one instance of a class that is one predicate wide (**R-2**).

The defect is therefore **"this assertion is corruptible by any concurrent sleeper"** — *not* "CI has
an intruder thread". The intruder is incidental; the counter is shared by construction. This framing
is binding and is deliberately **independent of `#3130`**: `#3136` itself records that whether fixing
`#3130`'s leaks eliminates the intruder population is **not established**, and any *future* thread
reintroduces the failure regardless.

**The fix is product-side (R-1), not test-side.** `saas_client.py` gains module-scope aliases `_sleep`
/ `_monotonic` / `_randbelow` and routes its call sites (`:439`, `:481`, `:484`, `:515`, `:518`)
through them. `@patch("…saas_client._sleep")` then binds a **module-local** attribute that
structurally cannot observe another thread's `time.sleep`. This is the operator's ruling and it is
binding; it is the reason this spec names a seam at all (see FR-010, and the note on scope discipline
in `## Corrections to the incoming brief` #5).

**Key on the class, never on an enumeration of node-ids.** A wrong node-id inherited from `#3115`
survived three review rounds and eleven analysis passes. `#3136`'s own "key on these two node-ids"
instruction is already stale — a third victim appeared in run `30681941495`, and a fourth in the
PR #3209 shard.

### Observed victims — the union closes on this mission's `time.sleep` census

| Observation | Victim node(s) | Failure text |
|---|---|---|
| run `30621215287`, job `91126025663`, `bb2020fea9` | `TestPolling::test_exponential_backoff_intervals` | `assert 71 == 3` |
| same run, `[gw2]` | `test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises` | `Expected 'sleep' to be called once. Called 556 times.` |
| run `30681941495`, `bb2020fea9` | `test_exponential_backoff_intervals`, `TestRetryBehaviors::test_429_defaults_to_5s_when_missing` | (per issue comment 1) |
| PR #3209 branch, CI selection, `96494e5ec` base | `test_exponential_backoff_intervals` (`assert 48 == 3`), `TestRetryBehaviors::test_429_respects_retry_after` (`Called 149 times.`) | (per issue comment 2) |
| **job `92278529393`, pristine `main` @ `98198e980`** — the spec's own baseline | three census nodes simultaneously | `3 failed, 2113 passed, 11 skipped, 2 warnings in 100.79s`; `assert 174 == 3`; `Called 153 times.`; `Called 507 times.` |
| **run `de66c4960`** | **all four census nodes simultaneously** | (per analysis-report; supersedes the union-over-runs argument) |

Four distinct victim nodes have been observed on the `time.sleep` mechanism. **The `time.sleep` census
below finds exactly four nodes.** The observed-victim set and that census set are identical, which is
the only reason an enumeration is safe to *state* — it must never be what the fix keys on. Under **R-2**
the class is wider than the `time.sleep` census: see `### The class is not confined to
tests/sync/tracker/`.

### The defect is topology-and-timing dependent, not deterministic and not composition-dependent

**R1 of this spec claimed** the class reddens on PR #3209's composition while pristine `main` is green
in the full shard, and therefore that the dependence is on **composition**. **Withdrawn.** Measured
from CI's own logs (analysis-report, BLOCKER-1):

- Pristine `main` reddens on this class in **11 of 18** consecutive `fast-tests-sync` jobs (**61%**),
  **including at `98198e980`** — this spec's own baseline (job `92278529393`, above).
  `2113 + 3 = 2116` — the **same selection** as the local `2116 passed` run this spec quoted as
  evidence that main is green. Same selection, opposite verdict.
- It is **nondeterministic at a fixed commit**. Three of six same-SHA run pairs disagree: `abca7ec96`
  reddened two nodes in job `91883621718` and was clean in `91677177124`; `bb2020fea9` produced
  *different victim sets with different magnitudes on identical commits* (71 vs 115 on the same node).

**Binding restatement**: the failure is **topology-and-timing dependent** — parallel-vs-serial topology
and thread-arrival timing are the variables — **with composition as a probability modifier**, because a
composition that keeps more leaked threads alive in a worker raises the hit rate. It is **not**
deterministic and **not** composition-dependent.

**Consequence for the criterion set**: a single full-shard run is clean **39%** of the time *pre-fix*,
so "the full shard is green" cannot discriminate a fix from no fix. That is why SC-006 is retired (see
its entry) and why every surviving acceptance arm is an **injection** or a **static** measurement.

**Where PR #3209 is referenced, its head SHA is pinned**: `5e98c2bb752f9ef6484eafc6411afedfd395f957`
(`5e98c2bb7`), branch `pr/batch-drain-retirement-3167`, verified `2026-08-05` via
`gh pr view 3209 --repo Priivacy-ai/spec-kitty --json headRefOid`. The branch has moved twice during
this mission (`96494e5ec` → `783c137d7` → `5e98c2bb7`), so the branch name is not a reproducible
handle. Arm B's superseded transcript in R1 was taken at `783c137d7`; on the then-current head the
backoff node **passes**.

### The class is not confined to `tests/sync/tracker/`

R1 claimed (in Verification Provenance) that running the census over all of `tests/sync/` returns the
same 4 nodes and 5 assertions, and therefore "the class is confined to `tests/sync/tracker/`".
**That claim is struck.** It was an artifact of two blind spots in this mission's own instruments, both
of which are census defects rather than facts about the tree:

1. **The census inspected `@patch` decorators only** — it cannot see a context-manager `patch(...)`
   call.
2. **The predecessor's closure grep is `sleep\.side_effect\s*=`** — it matches *attribute assignment*
   only, so it cannot see the `side_effect=` **kwarg** form.

Nine further instances of the same mechanism, all inside CI's `-m "fast and not windows_ci"` selection
(`pytestmark = [pytest.mark.fast]` at `test_final_sync_diagnostics.py:27` and
`test_git_metadata.py:28`), verified line by line on `98198e980`:

| `file:line` | Assertion | Patch site | Bare import |
|---|---|---|---|
| `tests/sync/test_final_sync_diagnostics.py:309` | `assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]` | `:303` context-manager `patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append)` | `src/specify_cli/sync/batch.py:11` |
| `tests/sync/test_git_metadata.py:226`, `:249`, `:281`, `:471`, `:530` | `assert mock_run.call_count == N` (3/5/3/2/5) | `@patch("specify_cli.sync.git_metadata.subprocess.run")` | `src/specify_cli/sync/git_metadata.py:13` |
| `tests/sync/test_git_metadata.py:218`, `:242`, `:274` | `mock_time.side_effect = [1.0, 2.0]` / `[1.0, 4.0]` / `[1.0, 2.99]` — exact-list clock couplings | same nodes | `src/specify_cli/sync/git_metadata.py:14` |

`test_final_sync_diagnostics.py:309` is structurally identical to `test_saas_client.py:786`: a
whole-list equality over an unfiltered process-global recorder. The `git_metadata` producer population
is **stronger** than the `secrets` one — `git_metadata` is called from sync background threads and
`#3130`'s leaked threads shell out to git.

**R-2 ruling**: key the gate on the **mechanism** — refuse any `@patch("a.b.c.attr")` whose penultimate
segment resolves at import to a `ModuleType` when the resulting mock is then read by a count or
equality assertion — and **enforce over `tests/sync/`**. Not `tests/cli`, which `C-001` forbids this
mission from running. One statically-decidable rule closes `time` / `secrets` / `subprocess` /
`random` / `os` in one construction.

### The 24 patch-target retargets — the edit that *constitutes* the fix (FR-012)

**The mechanism, and this spec already knew it.** `### Established, reused, not re-derived` records that
`psutil._psposix.wait_pid_posix` is **invisible** to `@patch("…time.sleep")` because it binds
`_sleep=time.sleep` **at import time**. R-1's seam is that same construction, deliberately: `_sleep =
time.sleep` at module scope binds the *function object* when `saas_client` is imported.
`@patch("specify_cli.tracker.saas_client.time.sleep")` rebinds the attribute on the **stdlib `time`
module object** and therefore **cannot reach `saas_client._sleep`**. The property that makes the seam
work is the same one that makes every existing decorator miss it.

**Consequence — simulated across all four states, in a quiet process (no intruder thread), asking what
the *existing* `== 3` assertion sees:**

| Alias form | Decorator target | Recorder sees | Verdict |
|---|---|---|---|
| assignment (`_sleep = time.sleep`) | `…_sleep` **(retargeted)** | `3` | **immune — this is the fix** |
| assignment | `…time.sleep` (un-retargeted) | **`0`** | **FAILS loudly** — production calls the import-time binding, which the mock never replaced |
| **wrapper** (`def _sleep(s): time.sleep(s)`) | `…_sleep` (retargeted) | `3` | immune at runtime, but the module retains a live `time.sleep` lookup |
| **wrapper** | `…time.sleep` (un-retargeted) | **`3`** | **PASSES SILENTLY — and the defect is 100% intact** |

**So the alias form is binding: assignment, never a wrapper — and the reason is that the assignment form
is *self-enforcing*.** Under assignment, skipping the retargets is **impossible to ship**: the census
assertions see 0 attributed calls and go red even in a quiet process, so the seam cannot land without its
retargets. Under the wrapper form, skipping the retargets is **invisible**: every node stays green
because the wrapper preserves exactly the `time.sleep` reach-through the un-retargeted decorator patches,
and the recorder goes on counting any concurrent thread's calls. **The wrapper is the single most
attractive way to satisfy every criterion in this spec while changing nothing about the defect**, and it
is attractive precisely because it makes the 24-decorator edit look optional.

Refused on both sides: `SC-007` arm **4b** pins the assignment form structurally
(`ast.Assign`, not `ast.FunctionDef`), and arm **4c** pins the retargets by count — either alone leaves a
hole, which is why both exist.

**Inventory, re-derived this session** (not carried from the directive) with:

```
$ grep -oE 'patch\("specify_cli\.tracker\.saas_client\.[^"]+"' \
    tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py \
  | sort | uniq -c
```

| File | Pre-fix target string | Post-fix target string | Count | Lines |
|---|---|---|---|---|
| `test_saas_client.py` | `specify_cli.tracker.saas_client.time.sleep` | `specify_cli.tracker.saas_client._sleep` | **13** live | `:385`, `:412`, `:467`, `:502`, `:789`, `:809`, `:899`, `:939`, `:959`, `:1087`, `:1128`, `:1152`, `:1319` |
| `test_saas_client.py` | `specify_cli.tracker.saas_client.time.monotonic` | `specify_cli.tracker.saas_client._monotonic` | **9** | `:386`, `:413`, `:468`, `:503`, `:790`, `:810`, `:1088`, `:1129`, `:1153` |
| `test_saas_client.py` | `specify_cli.tracker.saas_client.secrets.randbelow` | `specify_cli.tracker.saas_client._randbelow` | **1** | `:499` (the target string; the `@patch(` opens at `:498` and closes at `:501`) |
| `test_saas_client_origin.py` | `specify_cli.tracker.saas_client.time.sleep` | `specify_cli.tracker.saas_client._sleep` | **1** | `:229` |
| **live decorator retargets** | | | **24** | |
| `test_saas_client.py` | same `…time.sleep` string **in prose** | update for consistency; **not** a decorator | 2 | `:559` **and `:715`**, both inside the `:513-762` docstring |

Arithmetic: `grep -c 'saas_client\.time\.sleep' tests/sync/tracker/test_saas_client.py` reports **15**,
of which **two** are docstring occurrences — `:559` and `:715` — → **13 live**. `13 + 9 + 1 = 23` live
in `test_saas_client.py`, `+ 1` in `test_saas_client_origin.py` = **24 live retargets**, plus **2**
prose occurrences = **26 string occurrences**. Docstring span `:513`–`:762` confirmed by opening both
boundary lines.

**`:715` is invisible to this spec's own re-derivation command.** It carries the bare dotted string
with **no `patch("` prefix** (*"Neither run put any extra call on
`specify_cli.tracker.saas_client.time.sleep` (still 12, still all `MainThread`)"*), so any probe
anchored on `patch\("` misses it. Every count in this mission that read `14`-as-a-string-total was one
short for this reason. The **AST decorator answer is unchanged at 13**; only the string arithmetic moves.

**`test_saas_client_origin.py` appears nowhere in R2's `plan.md` `## Project Structure`.** It carries
census assertion #5 (`:261`) *and* a required retarget (`:229`), so a plan that does not own it cannot
deliver the fix. It is now owned (see `plan.md` `## Project Structure`, IC-02).

**Not in scope, but measured so the next reader is not surprised**: the same reach-through mechanism
covers `patch("specify_cli.tracker.saas_client.httpx.Client")` — **130** sites under `tests/sync/`
(`grep -rhoE 'patch\("specify_cli\.tracker\.saas_client\.httpx\.Client"' tests/sync/ | wc -l` → 130),
the largest single contributor to the 286 reach-through total. `httpx.Client` is patched for
*substitution*, not for *counting*, so no assertion's verdict depends on a foreign call count and it is
outside the R-2 predicate's read-side condition. The gate will nonetheless flag it unless the read-side
condition is enforced — which is precisely why the predicate has two halves, not one.

### Established, reused, not re-derived

- Producer: CPython `subprocess.Popen._wait(timeout)` POSIX busy-wait, `delay = min(delay * 2, remaining, .05)`, base `0.0005`. CI's `556 = 1 + 6 + 549` is **one** loop caught in flight (the victim's own `call(2.0)`, one six-term geometric ramp, then saturation at the `0.05` cap) — not two producers. Independently reproduced by two parties.
- `psutil.Process.wait` is **invisible** to this patch: `psutil._psposix.wait_pid_posix` binds `_sleep=time.sleep` as a **function default at import time**. Prunes `daemon.py:1000-1032` and `dashboard/lifecycle.py:_terminate_by_pid`. Holds on CI: the `pidfd` branch uses `select.poll()` and has no sleep at all.
- `restart.py:147` and `daemon.py:1382` are **falsified**: flat `0.05`, no ramp.
- `docs/development/process-global-inventory-3115.md`'s verdict column (53 `E`-rows, verified count) was derived against `test_429_respects_retry_after`, and is **falsified in the direction that matters** — that node now exhibits the failure (PR #3209 shard).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A red build on these nodes means the backoff contract broke (Priority: P1)

A developer or CI reader opens a red `fast-tests-sync` shard and sees
`tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals` failed.
Today that tells them nothing: the assertion may have fired because the retry schedule changed, or
because an unrelated thread in the same worker happened to be inside a `subprocess.Popen.wait`
busy-loop. They must fetch the log, decompose the recorded delay list, and reason about which calls
belong to the code under test. After this mission, the red is attributable on sight: the assertion
only observes sleeps issued by the code under test, so a red means the retry contract changed.

**Why this priority**: this is the whole defect. It currently blocks PR #3209 (`#3167`), which
inverted the programme's planned order so this mission goes first.

**Independent Test**: run the four census nodes with a probe thread deliberately sleeping inside
the patch window. Pre-fix, they go red; post-fix, they stay green while the probe's calls are still
demonstrably landing on the **stdlib** `time.sleep` recorder, patched in the same window as the
assertion's `_sleep` recorder.

**Acceptance Scenarios**:

1. **Given** a probe thread inside a `time.sleep` loop for the duration of a census node's patch window, **When** the node's assertion is evaluated, **Then** its verdict is identical to the verdict with no probe running, **and** the probe's recorded call count on the **stdlib** `time.sleep` mock — patched in the same window as the assertion's `_sleep` mock — is ≥ 100, while the `_sleep` mock's count equals the expected value (3/1/1/1).
2. **Given** the same probe, **When** the *pre-fix* form of that assertion (`assert_called_once_with(2.0)` / `len(call_args_list) == 3`) is evaluated against the **stdlib**-polluted recorder in the same window, **Then** it raises `AssertionError` — the red-first proof, kept live rather than transcribed.
3. **Given** the mission head, **When** the guard runs on `98198e980` (the `planning_base_branch`), **Then** it goes **red** — the R-1 alias it patches does not exist there — and green on the mission head. This is the charter's red-on-base arm; see `### Charter red-on-base — the exception, named`.

**Retired scenario** (was #3, R1): *"Given the pristine `upstream/main` shard composition and the PR
#3209 shard composition, when CI's selection runs in each, then no census node appears as `FAILED` in
either."* Withdrawn — pristine `main` is not green in the full shard (11 of 18 jobs red, including at
`98198e980`), so the pristine arm is not a control, and a single clean run is the pre-fix outcome 39%
of the time. Kept visible rather than deleted so a successor does not re-derive it.

---

### User Story 2 - The assertion still catches a genuinely wrong backoff (Priority: P1)

The same developer changes `_poll_operation`'s backoff base or the 429 retry-after handling. The
hardened assertions must go red. An assertion that cannot be corrupted is worthless if it also
cannot be violated — and the cheapest way to satisfy Story 1 is to delete the assertions.

**Why this priority**: co-equal with Story 1. The previous mission in this programme was found by a
four-lens squad to have 9 of 11 success criteria satisfiable while the defect survived; the failure
mode was criteria with no exception path. The delay sequence **is** the backoff contract.

**Independent Test**: mutate the production schedule at a named line, run the affected census nodes,
require a specific failure; revert, require green. **Three mutation kinds, not two**: a wrong *value*,
a wrong *cardinality*, and a wrong *per-call* value. The cardinality kind is the one R1 omitted and it
is the sharpest hole in the criterion set (see `### Adversarial Analysis`, the cardinality row).

**Acceptance Scenarios**:

1. **Given** `src/specify_cli/tracker/saas_client.py:478` changed from `delay = 1.0` to `delay = 1.5`, **When** `test_exponential_backoff_intervals` runs, **Then** it fails with observed delays `[1.35, 3.0, 6.6000000000000005]` against expected `[0.9, 2.0, 4.4]`. *(The third element is `6.6000000000000005`, not `6.6` — computed against production: `1.5*0.9, 3.0*1.0, 6.0*1.1`. `[0.9, 2.0, 4.4]` at `delay = 1.0` **is** exact, which is why the unmutated test passes. A criterion pinning the literal `6.6` is unsatisfiable.)*
2. **Given** the 429 sleep call at `saas_client.py:439` (post-R-1: `_sleep(float(wait_seconds))`) changed to `… * 2`, **When** the three 429 census nodes run, **Then** all three fail on the delay value (`6.0`/`10.0`/`4.0` against `3.0`/`5.0`/`2.0`).
3. **Given** the 429 sleep call at `saas_client.py:439` **duplicated** (two calls, same value) and a fourth `pending` response added for the backoff node, **When** the affected census nodes run, **Then** each fails on the **call count** — not on any delay value. This is the arm that refuses the `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]` rewrite.
4. **Given** all mutations reverted, **When** the four census nodes run, **Then** all four pass.

---

### User Story 3 - A successor cannot silently reintroduce the class (Priority: P2)

A future author adds a new retry test anywhere under `tests/sync/` and reaches for
`mock_sleep.assert_called_once_with(...)`, or `assert mock_run.call_count == 3`, because that is the
shape every neighbour uses. Nothing in the tree refuses it, and the shard becomes timing-dependent
again on a run nobody attributes.

**Why this priority**: charter standing order 5 — close defect classes by construction with a
non-vacuous call-site gate. Lower than P1 because Stories 1–2 deliver a trustworthy suite on their
own; without Story 3 the class returns.

**Independent Test**: feed the gate a synthetic module containing a corruptible form **not present in
the tree today** (`assert mock_sleep.call_count == 1`) and require it flagged; feed it the post-fix
tree and require it clean; require it to **name** the files and patch sites it scanned, not merely
count them.

**Acceptance Scenarios**:

1. **Given** the post-fix tree, **When** the gate runs over `tests/sync/`, **Then** it passes and its output **names** the files it opened — including `tests/sync/tracker/test_saas_client.py`, `tests/sync/tracker/test_saas_client_origin.py`, `tests/sync/test_final_sync_diagnostics.py`, `tests/sync/test_git_metadata.py` — with the `13 + 1` patch-site split for the two tracker files and the four census node-ids.
2. **Given** a synthetic module with `assert mock_sleep.call_count == 1` under a module-object patch, **When** the gate's analyzer runs against it, **Then** it reports that assertion as corruptible — and the same for `assert mock_run.call_count == 1` under `@patch("pkg.mod.subprocess.run")`, proving the predicate is keyed on the **mechanism** and not on `time.sleep`.
3. **Given** a synthetic module whose corruptible assertion is fed by a **context-manager** `patch(...)` with a `side_effect=` kwarg, **When** the analyzer runs, **Then** it reports it — the two blind spots that hid `test_final_sync_diagnostics.py:309`.
4. **Given** the gate's own source, **When** its baseline is inspected, **Then** it is frozen shrink-only, every row carries an `owner:` and a `disposition:`, and **the baseline is registered in `test_ratchet_baselines.py`** — an unregistered key is read by nothing and fails nothing.
5. **Given** the post-fix tree, **When** the gate runs, **Then** it asserts the R-1 seam on **both sides**: (a) `saas_client.py` contains **no call whose callee resolves** to `time.sleep` / `time.monotonic` / `secrets.randbelow` — resolved against the module's own import bindings, with **no "outside the alias definitions" carve-out**, because that carve-out admits the wrapper form; (b) the three module-scope names are **assignments** to those attributes, not wrapper functions; and (c) **the test-side target strings have actually moved** — 0 occurrences of the three pre-fix targets and `14`/`9`/`1` of the post-fix ones. Displacing the seam, wrapping it, **or leaving the decorators untouched** turns the gate red rather than turning it vacuous.
6. **Given** a `saas_client.py` that reaches the stdlib through an aliased import (`import time as t; t.sleep(x)`), a `from time import sleep`, or `getattr(time, "sleep")(x)`, **When** the gate runs, **Then** it still reports the call — the negative is resolution-based, not textual.

---

### User Story 4 - The next investigator inherits verified ground, not "probably survives" (Priority: P3)

A successor opens `#3130`, `#3193`, or a future sleep-count issue and reaches for
`docs/development/process-global-inventory-3115.md` because `#3136`'s body points at it. Its verdict
column was derived against a node that has since failed, so its verdicts are verdicts about a
falsified premise.

**Why this priority**: pure carry-forward hygiene; no test depends on it. But this is the exact
failure mode that produced this programme — a stale handle inherited layer by layer.

**Independent Test**: the doc carries a machine-greppable unverified stamp naming `#3136`, and names
by `E`-number the rows this mission's fix depends on (possibly the empty set, with reasoning).

**Acceptance Scenarios**:

1. **Given** the merged tree, **When** the inventory is read, **Then** its verdict column carries an unverified stamp citing `#3136` and the PR #3209 falsification of `test_429_respects_retry_after`.
2. **Given** this mission's plan and test rationale, **When** searched for inventory citations, **Then** either none appear, or every cited `E`-row carries a re-derivation verdict against the four census nodes.

---

### Edge Cases

- **`-n auto --dist loadfile` vs serial.** `gw2`/`gw5` are separate OS processes and cannot share a mock's state, so the two `30621215287` victims were independently polluted, each inside its own worker. `loadfile` keeps a file on one worker, so a worker accumulates a whole file's leaked threads; serial accumulates the *entire* cone's. Neither topology is safe and the fix must not depend on which is used — the hardened assertions must produce identical verdicts under `-n0` and `-n auto --dist loadfile`.
- **Narrow runs prove nothing — and neither does a full shard.** Both PR #3209 victims pass narrow on both arms (`2 passed in 73.00s`). A green single-node run is the default outcome, not evidence. **A green *full-shard* run is also the pre-fix outcome 39% of the time** (11-of-18 red on pristine main), so "full-shard composition" is not the escape from this that R1 assumed. Every acceptance arm must therefore be an *injection* or a *static* measurement, never a pass of any breadth.
- **The fix's own seam is patched by another test.** The R-1 alias (`_sleep` / `_monotonic` / `_randbelow` at `saas_client.py` module scope) **is** an observable seam; a sibling test that patches or replaces it, or a future production edit that calls `time.sleep` directly again, silently disables the hardening and the class returns invisible. Its presence **and its call-site routing** must be asserted by the gate itself (Story 3 scenario 5), so displacing it turns the gate red rather than turning it vacuous.
  - **`_poll_jitter_multiplier` is the precedent for how this rots, and it must be resolved in the same change.** `saas_client.py:104-106` defines `_poll_jitter_multiplier()` returning `0.8 + (secrets.randbelow(4001) / 10000.0)`. Verified: **zero callers** in `src/` or `tests/` (`grep -rn '_poll_jitter_multiplier' src/ tests/` → one hit, the definition). It **disagrees with the live inline jitter** at `:515-516` (`secrets.randbelow(4000)`, `0.8 + basis/10000`): max multiplier **1.2** vs **1.1999**. A dead seam that drifted from the live code is exactly what the new alias must not become. **Delete it, or promote it to sole authority (both `:515-516` and the tests routing through it), in the same change** — R-1 condition (iii).
  - **The predecessor's closure grep is retired as evidence.** R1 cited `grep -rn "sleep\.side_effect\s*=" tests/sync/` → **0 hits** as closing the `side_effect`-displacement hazard. The pattern matches *attribute assignment* only; the `side_effect=` **kwarg** form is invisible to it, and that is precisely how `test_final_sync_diagnostics.py:303` feeds `:309`. The **0 hits** is true of the pattern and **false of the hazard**. The claim is withdrawn; the hazard is re-closed by the mechanism-keyed predicate (R-2), which reads the `patch()` call's arguments rather than grepping for one spelling.
- **The retry implementation legitimately changes.** If `_poll_operation`'s schedule or the 429 handler changes on purpose, the delay assertions *should* go red — that is Story 2. The expected values must live in one obvious place per node so the intended update is a one-line edit, and the failure text must show observed-vs-expected delay sequences, not a bare count.
- **Pollution absent.** If the injection probe fails to land calls (a spawn race — the predecessor's first probe missed because the thread had not entered its wait loop when the sub-millisecond test body ran), the corruptibility guard passes vacuously. The guard must assert the pollution floor as a first-class arm (SC-005), not assume it.
- **`time.monotonic` carries the same mechanism with a different failure shape — and R1 mis-read its assertion.** Nine `@patch("specify_cli.tracker.saas_client.time.monotonic")` decorators exist. Eight feed `_advancing_clock()` (unbounded — deliberately hardened by the predecessor, `test_saas_client.py:32-62`). One, `test_saas_client.py:804`, still feeds an exact list `[0.0, 301.0]`; a concurrent `time.monotonic()` consumes an element and the test dies of `StopIteration`. **R1 recorded that `301.0` "IS its assertion" and therefore that the fix was blocked. That is false**, verified by opening `test_saas_client.py:804-807`:
  ```python
  mock_monotonic.side_effect = [0.0, 301.0]          # :804 — a side_effect *stimulus*

  with pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes"):   # :806 — the only assertion
      client._poll_operation("op-timeout")            # :807
  ```
  The only assertion is the `pytest.raises` match. `itertools.chain([0.0], itertools.repeat(301.0))` is unbounded and preserves **both** the exact stimulus and the exact raise (production reads the clock twice, `:481` then `:484`). **The false claim originates in a docstring** — `_advancing_clock`'s own text at `test_saas_client.py:55-57`: *"there the second value **is** the assertion"* — and propagated into R1 and then into the operator briefing. **The docstring must be corrected in the same change** (FR-010), or the next reader inherits the same false blocker. Under R-1 the whole coupling is moot: `_monotonic` is module-local, so no other thread can consume an element.
- **`secrets.randbelow` at `test_saas_client.py:787`.** `import secrets` at `saas_client.py:18` is also bare, and `assert mock_randbelow.call_count == 3` sits **inside** a census node (two lines below `:786`), under a 3-element `side_effect`. Under **R-1** this needs no change to the assertion *expression*: `@patch("…saas_client._randbelow")` is module-local, so the assertion becomes correct with its text unchanged — but the decorator at `:499` **must be retargeted** (FR-012). FR-006 retires as a work item; the reasoning is retained here because it is what justifies the ruling.
- **`#3130` / `#3193` teardown errors travel with these reds.** The PR #3209 shard showed two leak-guard teardown `ERROR`s alongside the two sleep reds. They are not this mission's scope and may remain red; a measurement that counts them as this mission's failures is misattributing. Count `^ERROR tests/`, not `^ERROR ` (a captured log record at level ERROR begins with the latter), and use `-ra` — `-rf` suppresses the error summary entirely.
- **`FR-007` collides with the predecessor's `FR-007` (`DIR-032`).** This spec's `FR-007` was the `time.monotonic` disposition (now retired). The **inherited** `#3115 FR-007` is the `tests/sync/` leak guard, and it is **baked into printed strings** at `tests/sync/conftest.py:485` and `:494` (`"[FR-007 leak guard] inspected … test(s)"`) — strings that SC-008's positive twin greps for. Any prose in this mission's artifacts referring to "FR-007" must be qualified as either **`#3115 FR-007` (leak guard)** or **this mission's FR-007 (retired)**. NFR-004 in this spec already means the inherited one; it is now labelled so.

### Charter red-on-base — the exception, named

The charter's ATDD-First Discipline (`.kittify/charter/charter.md:504-513`, binding per its `C-011`)
requires the reviewer to verify the ATDD test was **RED on the WP's `planning_base_branch`** and GREEN
on the final commit. R1 addressed this nowhere: `grep -c 'ATDD\|planning_base_branch' spec.md` → **0**.
**Injection-red is not base-branch-red** — the guard's arm (b) is *designed* to raise `AssertionError`
and be caught, on any branch.

**Under R-1 a genuine base-branch red exists, and it is structural.** Named explicitly:

| Arm | Behaviour on `98198e980` | Behaviour on the mission head |
|---|---|---|
| Corruptibility guard, arm (a) | **RED** — `AttributeError: <module 'specify_cli.tracker.saas_client'> does not have the attribute '_sleep'`, raised by `unittest.mock.patch` at setup. The R-1 alias does not exist on base, so the arm cannot even be set up. | green |
| Mechanism gate (SC-007) | **RED** — the base tree's 5 `time.sleep` assertions plus the 9 `tests/sync/` instances above are all flagged corruptible. | green (0 flagged) |
| Seam-routing arm (Story 3 scenario 5) | **RED** — `saas_client.py` on base calls `time.sleep(` directly at `:439` and `:518`. | green |

`[UNVERIFIED]` The exact `AttributeError` text — this session ran no test bodies (see `### Environment`).
The *fact* of the red is structural (the attribute provably does not exist on `98198e980`); only the
message string is unverified. The implementing WP must record the observed text.

**The red-first commit reddens a SECOND `[ENFORCED]` CI gate, and R2 named neither it nor an owner.**
`scripts/check_patch_targets.py` runs at `.github/workflows/ci-quality.yml:883-884` as
`[ENFORCED] Validate patch() target strings (closes #394)`, invoked **with no arguments**, so it scans
every `patch()` target string under `tests/`. Verified against the current (base-equivalent) tree by
calling its own resolver directly:

```
$ ./.venv/bin/python -c "…; from scripts.check_patch_targets import _mock_importer; …"
specify_cli.tracker.saas_client._sleep      -> (None, "no attribute '_sleep' in 'specify_cli.tracker.saas_client'")
specify_cli.tracker.saas_client._monotonic  -> (None, "no attribute '_monotonic' in …")
specify_cli.tracker.saas_client._randbelow  -> (None, "no attribute '_randbelow' in …")
specify_cli.tracker.saas_client.time.sleep  -> (<built-in function sleep>, None)   # control: resolves today
```

So the guard-and-retarget commit reds the **lint job** as well as the sync shard, for the whole window
between it and the alias commit. This is a *second* structural red, it is expected, and it is the
strongest available evidence that the retargets are real rather than cosmetic — a retarget that did not
change the resolved object would not move this gate. **Consequence for sequencing**: it is one more
reason the guard and the alias must be one work package (see `plan.md`, IC-02, and the merge of IC-05
into it) — CI cannot be left red across a work-package boundary, because a WP whose final commit is red
can never reach `approved`.

### Environment — every R1 success-criterion command was unrunnable here, and the R2 replacement was destructive

**Superseded twice.** R1's `python3 -m pytest …` resolved to an interpreter without the project's
dependencies. R2 replaced it with `uv run --python 3.12 python …`, which the post-plan squad then
proved **removes the test runner it is about to invoke**. Both corrections are recorded here so no WP
re-discovers either.

Measured in the post-plan session (`<repo>/.venv/bin` prepended to `PATH`, `command -v` verified before
each value was trusted):

| Fact | Value | How |
|---|---|---|
| `.venv/bin/python -V` | **3.12.13** | run — matches CI's `fast-tests-sync` interpreter |
| `.venv/bin/pytest --version` | **9.0.3** | run |
| `.venv/bin/ruff --version` | **0.15.12** | run |
| `.venv/bin/mypy --version` | **1.20.2** | run |
| `.python-version` | `3.11.15` | **diverges from the venv and from CI**; out of `C-004`'s permitted set — record, do not "fix" |
| ambient `python3 -V` | **3.14.4** | three interpreters from CI |
| CI (`ci-quality.yml`, `fast-tests-sync`) | Python **3.12**, `uv run python -m pytest` | `:1161-1172` |
| CI (`docs-freshness.yml`) | Python **3.11** | `uv python install 3.11` at `:17` — a *different* interpreter from `fast-tests-sync`; the `IC-03` docs commands run there |
| `uv` | `0.10.12` at `/usr/bin/uv` | `command -v uv` |
| `~/.local/bin/{pytest,ruff,mypy,spec-kitty}` | resolve to an **unrelated checkout** | first on the unmodified `PATH` — verified all four |

**The destructive form, and the proof.** `uv run --python 3.12 …` with **no extras** resolves the
project's default dependency set, which does not include the test or lint toolchain: `pytest` / `ruff` /
`mypy` live only in `[project.optional-dependencies]` (`pyproject.toml:100-115`), `[dependency-groups]
dev` carries type stubs only, and there is no `[tool.uv]` block. Proved non-destructively this session:

```
$ uv sync --dry-run --python 3.12
Would use project environment at: .venv
Resolved 126 packages in 0.98ms
Found up-to-date lockfile at: uv.lock
Would uninstall 70 packages
 - mypy==1.20.2
 - pytest==9.0.3
 - ruff==0.15.12
 … (67 more, incl. pytest-xdist, pytest-cov, bandit, build)
```

`--dry-run` is itself non-destructive — `./.venv/bin/pytest --version` still reported `9.0.3`
afterwards. CI never trips this because every job runs `uv sync --frozen --all-extras` first
(`ci-quality.yml:1145`). **This is also what destroyed the venv during planning**: the form R2 adopted
as "safe because pinned" was the destructive one.

**The sanctioned forms — one of these two, never the bare form.** Confirmed by dry-run:
`uv sync --dry-run --python 3.12 --extra test --extra lint` → `Would make no changes`.

```
# Form 1 — direct, no resolver involvement. Preferred inside a provisioned tree.
./.venv/bin/python -m pytest …
./.venv/bin/python -m ruff check .        # or ./.venv/bin/ruff check .

# Form 2 — uv-driven, extras pinned so the toolchain survives the resolve.
uv run --python 3.12 --extra test --extra lint python -m pytest …

# Provisioning (once), after which Form 1 is valid:
uv sync --python 3.12 --extra test --extra lint
```

**Binding**: every criterion command in this spec is written in a sanctioned form. **A bare
`uv run --python 3.12 …` anywhere in an implementation transcript is a defect, not a style
preference** — it uninstalls 70 packages and then fails. The first implementation work package
prepends `<repo>/.venv/bin` to `PATH`, records `command -v python pytest ruff mypy` **and** the four
`--version` lines before any acceptance arm runs, and a transcript missing the `command -v` line is not
evidence. A WP must not discover any of this at acceptance time.

Good news, measured by the squad: the named producer loop `delay = min(delay * 2, remaining, .05)` **is**
still present in CPython 3.14's `subprocess.Popen._wait`, so the mechanism reproduces locally.

---

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Corruptibility eliminated by class | As a CI reader, I want every assertion under `tests/sync/` whose verdict depends on a **process-global module attribute** counter — `time.sleep`, `time.monotonic`, `secrets.randbelow`, `subprocess.run`, or any other attribute of a shared `ModuleType` — to observe only calls issued by the code under test, so that a red is attributable without reading a log. Scope is the **class**, defined by the R-2 mechanism predicate and derived by a committed census — never an enumeration of node-ids. Enforced over `tests/sync/`, **not** `tests/cli` (C-001). | High | Open |
| FR-002 | Delay-sequence contract preserved, values **and** cardinalities | As a maintainer, I want the backoff contract still asserted with the same expected values and cardinalities — `[0.9, 2.0, 4.4]`/n=3, `3.0`/n=1, `5.0`/n=1, `2.0`/n=1 — so that hardening cannot be achieved by deletion or weakening. **This does not conflict with FR-001**: FR-001 forbids depending on a count of *every* sleep in the process; FR-002 requires a count of the sleeps *the code under test issued*. The cardinality is preserved; only its denominator changes from process-wide to attributed. **Cardinality is measured, not merely required in prose**: `<census>` reports `sleep_assertions: 5` (an assertion-count denominator, not only a node count), and SC-003 Arm 3 mutates the *count* and requires red. Without both, `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]` satisfies every other criterion while dropping cardinality silently. | High | Open |
| FR-003 | Red-first proof kept live | As a reviewer, I want the pre-fix assertion shape evaluated against a deliberately polluted recorder inside the shipped test suite, raising `AssertionError`, so that the red-first evidence is a command and not a transcript. The predecessor's probe (`{MainThread: 1, probe: 399}`, 400 recorded against 1 expected) is the correct red for **this** defect — it was rejected as evidence that *the CI intruder is the one named*, which it is not, but it is exactly the right red for the assertion-class defect. | High | Open |
| FR-004 | Instrument proven in the positive direction | As a reviewer, I want a named mutation of the production schedule that the hardened assertions demonstrably catch, so that a broken (vacuous) instrument cannot satisfy FR-001. | High | Open |
| FR-005 | Class closed by a **mechanism-keyed** non-vacuous gate | As a maintainer, I want a call-site gate that refuses any `@patch("a.b.c.attr")` — decorator **or** context-manager `patch()` call, `side_effect=` kwarg included — whose penultimate segment `a.b.c` resolves at import to a `ModuleType`, when the resulting mock is then read by a count or equality assertion. Enforced over `tests/sync/`. It must **name** the files and patch sites it scanned (not just count them), carry a self-mutation arm on a form absent from the tree today, assert the R-1 seam **on both the product and the test side** (SC-007 item 4, four parts), and carry a **frozen shrink-only baseline that is registered in `test_ratchet_baselines.py`** — R2 said "shrink-only (empty at merge)", which is (a) incompatible with the measured residue and (b) irrelevant if the baseline is registered nowhere, since an unregistered key is read by no comparison and its growth fails nothing. One statically-decidable rule closes `time` / `secrets` / `subprocess` / `random` / `os` together. | High | Open |
| FR-006 | ~~Co-located `secrets.randbelow` counter hardened~~ | **RETIRED as a work item under R-1** (2026-08-05). Retained, not renumbered, so no successor reads a gap. Rationale: with `_randbelow` a module-scope alias in `saas_client.py`, `@patch("…saas_client._randbelow")` binds a module-local attribute, and `test_saas_client.py:787`'s `assert mock_randbelow.call_count == 3` becomes correct **with its assertion text unchanged** — no weakening. **Its decorator target does change** (`:499`, FR-012); "unchanged" was never true of the target. The substance folds into **FR-010**. The exposure analysis is preserved in `### Edge Cases`. | — | Retired (R-1) |
| FR-007 | ~~`time.monotonic` sibling exposure disposed of explicitly~~ | **RETIRED as a work item under R-1** (2026-08-05). Retained, not renumbered. Rationale: `_monotonic` as a module-local alias makes `test_saas_client.py:804`'s `[0.0, 301.0]` un-consumable by another thread, so the exposure closes with no test change. Its supposed blocker was in any case **false** — `301.0` is a `side_effect` stimulus, not an assertion (`:804` vs the `pytest.raises` at `:806`). The substance folds into **FR-010**, which also carries the docstring correction at `test_saas_client.py:55-57`. **Do not confuse with `#3115 FR-007`** (the `tests/sync/` leak guard, printed at `tests/sync/conftest.py:485`, `:494`) — that one is live and inherited (`DIR-032`). | — | Retired (R-1) |
| FR-008 | Inventory verdict column stamped and scoped | As a successor, I want `docs/development/process-global-inventory-3115.md`'s verdict column stamped unverified against the real victims, with only the rows this fix depends on re-derived and named by `E`-number. | Low | Open |
| FR-009 | Non-goal recorded with its reasoning | As a successor, I want the CPU-contention reproduction recorded as a deliberate exclusion **with its three reasons**, so that it is not re-derived at the cost of another agent-day. | Medium | Open |
| FR-010 | Module-local alias seam, recorded as canonical (**R-1**) | As a maintainer, I want `src/specify_cli/tracker/saas_client.py` to define module-scope `_sleep` / `_monotonic` / `_randbelow` aliases **by assignment** (`_sleep = time.sleep`) and route **every** call site through them (`:439`, `:481`, `:484`, `:515`, `:518`), so that `@patch("…saas_client._sleep")` binds a **module-local** attribute that structurally cannot observe another thread's `time.sleep`. **The assertion *text* is unchanged; the patch *target* is not** — see the correction below, which is binding and supersedes R-1's recorded wording. Four binding conditions, all four: **(i)** an **ADR** under `docs/adr/3.x/` recording the alias as a deliberate testability seam **and adjudicating the idiom, not the instance** (see FR-011); **(ii)** the gate (FR-005) keyed on the mechanism **and** asserting the seam's own call-site routing **and the test-side target strings**; **(iii)** `_poll_jitter_multiplier` (`:104-106`, zero callers, max `1.2` against the live inline `1.1999` at `:515-516`) **deleted or promoted to sole authority in the same change** — it is the precedent for how a seam rots, and the new alias must not join it; **(iv)** the **24 patch-target retargets of FR-012**, without which the seam is inert. Also corrects the false docstring claim at `test_saas_client.py:55-57`. | High | Open |
| FR-011 | The seam adjudicates the **idiom**, not the instance | As a maintainer, I want the ADR of FR-010 condition (i) to state a **precedence rule** between the two seam styles now present in this cone, so the mission does not institutionalise a second idiom with no rule for choosing. Measured: `src/specify_cli/sync/batch.py:628-631` **already** exposes `run_final_sync_with_retries(…, *, sleep: Callable[[float], None] \| None = None)`; `:641` is `sleeper = time.sleep if sleep is None else sleep`, threaded through `:648`, `:655`, `:669`, `:674`, `:681`, `:684`, `:693`, `:700`; and **three tests already use it** (`test_final_sync_diagnostics.py:180`, `:207`, `:239`, all `sleep=sleeps.append`). **Binding rule**: *where a module already exposes a call-site injection point, thread it; introduce a module-local alias only where the stdlib call has no threadable caller.* Relate explicitly to `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md`, which decided seam + AST call-site gate + curated allowlist *against* full DI. `saas_client.py` earns an alias under this rule (its calls are internal to `_request_with_retry` / `_poll_operation`, with no injectable caller); `batch.py` does **not**. | High | Open |
| FR-012 | The 24 patch-target retargets — the edit that *constitutes* the fix | As a maintainer, I want every existing `patch()` decorator that reaches through `saas_client`'s `time` / `secrets` modules **retargeted to the alias**, because `_sleep = time.sleep` binds the function object **at import** and `@patch("specify_cli.tracker.saas_client.time.sleep")` mutates the stdlib `time` module's attribute, which **cannot reach that binding**. Without the retargets the seam changes nothing: the recorder the assertion reads is still the process-global one. **24 live decorator retargets**, re-derived this session and enumerated in `### The 24 patch-target retargets` — 23 in `tests/sync/tracker/test_saas_client.py` (13 live `time.sleep`, 9 `time.monotonic`, 1 `secrets.randbelow` at `:499`) and 1 in `tests/sync/tracker/test_saas_client_origin.py:229`, plus **2** prose occurrences at `test_saas_client.py:559` **and `:715`**, both inside the `:513-762` docstring (`:715` carries the bare dotted string with no `patch("` prefix, which is why a `patch\("`-anchored re-derivation misses it). This is **not** a "test-side edit" of the kind R-1 excluded: the assertion expressions are untouched, only the decorator target strings move. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Injection magnitude floor | The corruptibility guard's probe must land **≥ 100** recorded calls on the **stdlib `time.sleep` mock**, patched in the same window as the assertion's `_sleep` mock (whose count must equal the expected 3/1/1/1) — both asserted in-test and printed. *Post-R-1 the probe structurally cannot reach the `_sleep` recorder; that is the fix working, and it is why the floor is read off the stdlib view — see SC-005.* **Corrected derivation** (R1's was false): the predecessor's probe landed **399** of 400, so 100 is a **4×** margin below the observed injection magnitude; the **smallest observed CI recorder *total* on a census node is 28** (analysis-report's CI-log survey — *not* 48, which is a mid-range observation), so 100 is **`100/28 = 3.57×`** above the smallest observed total. *Note the distinction the R1 text lost*: a **total** of 28 on the `n=3` node implies an **inflation** of 25 intruder calls, so `3.57×` is the ratio against the total and `100/25 = 4.0×` the ratio against the inflation — both above 1, which is all the floor needs. R1's "**33×** above the smallest observed CI inflation (`48`)" is wrong three ways: `33.3` is `100/3`, computed against the *expected* count rather than any observed figure; `100/48` is `2.08`; and `48` is not the smallest observation. The floor value **100** is unchanged and defensible; only its justification is corrected. | Reliability | High | Open |
| NFR-002 | Red-first determinism | The FR-003 self-mutation arm must raise `AssertionError` in **10 of 10** consecutive runs (`pytest <guard> -q` repeated 10×, 10 passes) — it is a deliberate injection, not a race, so anything below 10/10 means the probe is racing the test body and the arm is not a proof. | Reliability | High | Open |
| NFR-003 | Topology invariance | The four census nodes must produce identical verdicts under `-n0` and under `-n auto --dist loadfile`, across 3 consecutive runs of each (6 runs, 6 identical pass sets). | Reliability | High | Open |
| NFR-004 | No new leaked threads | The guard's probe threads must be joined. With the **`#3115 FR-007`** `tests/sync/conftest.py` leak guard active over the changed modules, `^ERROR tests/` count must be **0**, and `git diff 98198e980 -- tests/sync/_leak_guard.py` must add **0** pin-registry entries. Criterion: SC-008 (which pins the entry count at **12**, AST-measured, rather than grepping a token that never appears on an added line). | Reliability | High | Open |
| NFR-005 | Runtime budget | The census nodes plus the new guard module must add **≤ 5.0 s** wall clock to a serial `tests/sync/tracker/` run. **The baseline must be captured in the same session as the comparison** — this spec has no measured baseline, because C-001 forbade running `tests/sync` here. Both arms: `./.venv/bin/python -m pytest tests/sync/tracker/ -m "fast and not windows_ci" -n0 -q -p no:cacheprovider`, once on `98198e980` and once on the mission head, reporting both wall-clock totals **and the resolved `python -V` for each** (the two arms must be the same interpreter — see `### Environment`). No individual test may exceed **60 s** (CI runs `--timeout=240 --timeout-method=signal`; 60 s leaves 4× headroom on a 4-vCPU runner). **Criterion: SC-014.** | Performance | Medium | Open |
| NFR-006 | Lint cleanliness without suppression | `ruff check` reports **0** findings on the changed files, and the diff against `98198e980` adds **0** lines containing `# noqa` or `# type: ignore`, **and no added `per-file-ignores` entry or widened `exclude`** in `ruff.toml` / `pyproject.toml` (both files already carry a `per-file-ignores` block, so the check must be diff-shaped, not existence-shaped). Exact commands in SC-012. | Maintainability | High | Open |
| NFR-007 | Census reproducibility | The committed census must be machine-derived (AST, not text matching) and must exclude docstrings, comments, and string literals. **The control fixture is committed as a test with its ground truth pinned in-test**, not described in prose — `<census>` is the sole instrument for SC-001, SC-002 and SC-013, and nothing else forces it to be trustworthy. The fixture must include the context-manager `patch()` and `side_effect=`-kwarg forms that R1's census could not see. **Criterion: SC-015.** | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `tests/sync` and `tests/cli` never concurrent | These two cones must never run concurrently on one machine, and a sibling mission may hold the `tests/sync` window. Check the window holder before any sweep; lane computation is per-mission and cannot see this constraint. | Technical | High | Open |
| C-002 | `ruff check` only | Never run `ruff format`. **Enforcement**: `git diff --stat 98198e980 -- src/ tests/` must show no file whose diff is import-reordering or whitespace-only, and the WP's command log (`kitty-ops/` or the WP notes) must contain **0** occurrences of `ruff format` — `grep -rc 'ruff format' <wp-notes>` = `0`. A reformat shows up as a large touched-line count in files the WP has no reason to touch. | Technical | High | Open |
| C-003 | `#3130`'s leaks are out of scope | Do not fix the process-global/live-thread leaks. Their teardown `ERROR`s may remain red and must not be counted as this mission's failures. `#3193` (leak-guard attribution race) likewise out of scope. **Count reconciled**: R1 said "11 confirmed leaks"; the registry holds **12** — `tests/sync/_leak_guard.py:333` is `_PINNED_LEAKS: tuple[_PinnedLeak, ...]` with **12** `_PinnedLeak(...)` elements (AST-measured this session; `grep -c '_PinnedLeak('` also 12). SC-008 pins **12**, and the WP must state which reading of "11" was wrong — a pin that is not a `#3130` leak, or a miscount — rather than leaving two numbers in the tree. | Technical | High | Open |
| C-004 | Production retry **behaviour** unchanged; `saas_client.py` changed **only** by the declared seam | **Restated under R-1.** R1's form ("no change to `saas_client.py`") is now false by construction, and its implied check (`git diff … saas_client.py` empty) would fail on the required fix. Binding form: `src/specify_cli/tracker/saas_client.py` may change **only** by (a) the FR-010 alias definitions and the call-site rerouting at `:439`, `:481`, `:484`, `:515`, `:518`, and (b) the `_poll_jitter_multiplier` resolution (`:104-106`). The retry **behaviour** — delay values, call cardinality, raise conditions — is unchanged. Mutations under FR-004 are applied and reverted, never committed. **Criterion: SC-016**, which can actually fail: it enumerates the permitted hunks and fails on any other changed line. | Technical | High | Open |
| C-005 | CPU-contention reproduction is a recorded non-goal | Do not attempt a live 4-vCPU contention reproduction. Three reasons, recorded so they are not re-derived: (1) the producer is already named — `subprocess.Popen._wait`'s capped doubling loop — and a contention reproduction cannot name a producer, only make an existing one likelier to be caught; (2) for a narrow-window race a local pass is the default outcome, so a negative result is uninformative by construction (the predecessor's probe missed only because the thread had not entered its wait loop when the sub-millisecond test body ran); (3) the operator decision is that the lever is the assertion class, not the intruder, so the intruder's identity is not on this mission's critical path. | Technical | High | Open |
| C-006 | Do not re-litigate the root cause | The mechanism, the named producer, the psutil structural exclusion, and the `restart.py:147` / `daemon.py:1382` falsifications are established. Verify the two code facts (`saas_client.py:19`; the patch-decorator census) and move on. | Process | High | Open |
| C-007 | Inventory verdicts are unverified input | `docs/development/process-global-inventory-3115.md`'s verdict column must not be relied on without re-derivation against the four census nodes. Its 53 verdicts were derived against `test_429_respects_retry_after`, which the PR #3209 shard has now falsified in the direction that matters. | Process | High | Open |
| C-008 | CI shard composition unchanged | No change to `.github/workflows/ci-quality.yml`'s `fast-tests-sync` selection, `--ignore` set, marker expression, or `-n auto --dist loadfile` topology (`:1161-1172`). The fix must survive the existing composition, not be enabled by changing it. **Enforcement**: `git diff 98198e980 -- .github/workflows/ci-quality.yml` produces **no output** — reported as part of SC-016. | Technical | High | Open |
| C-009 | Do not own `scripts/mutants/**` by directory glob | Own mutation/probe plugins by exact filename. A directory glob on `scripts/mutants/**` overlaps every file beneath it and collapses every proof-carrying work package into one lane. | Process | Medium | Open |
| C-010 | Documentation-only prose touches need the terminology guard | If FR-008 / FR-009 / FR-010's ADR edit `docs/` or doctrine prose, run the terminology guard before pushing — it runs only in CI's `integration-tests-core-misc` job, not in `fast-tests-*`. **Enforcement**: `./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` → `EXIT=0`, output recorded in the WP notes. The file exists (`tests/architectural/test_no_legacy_terminology.py`, verified). Reported as part of SC-016. | Process | Medium | Open |

### Key Entities

- **Mechanism predicate (R-2 — the class definition)**: a `patch` target string `"a.b.c.attr"` — supplied by a decorator **or** a context-manager `patch()` call — whose penultimate segment `a.b.c` **resolves at import to a `ModuleType`**, where the resulting mock is subsequently read by a **count or equality** assertion (including via a `side_effect=` sink such as `side_effect=sleeps.append`). Statically decidable; one rule closes `time` / `secrets` / `subprocess` / `random` / `os`. This, not `time.sleep`, is what the gate keys on.
- **`E15` is invalidated by this mission's own fix, and must be updated rather than merely stamped.**
  `docs/development/process-global-inventory-3115.md:296` enumerates `saas_client.py`'s module-level
  surface as exactly **two** names — `_SESSION_EXPIRED_MESSAGE` (`:36`) and `_UNAUTHENTICATED_CATEGORY`
  (`:39`) — and rests its `not reachable` verdict on that enumeration. `FR-010` adds **three** more
  (`_sleep`, `_monotonic`, `_randbelow`), so the row's premise stops holding the moment the seam lands.
  `E22`, the inventory's single `depends` row, `monkeypatch.setattr`s attributes on that same module
  object (`tests/sync/tracker/conftest.py:106-108`, `:172`) and must be adjudicated too. So the
  "re-derive only the load-bearing rows, and the set is probably empty" framing is **not safe**: at
  least these two are live candidates and each must be adjudicated individually, not assumed away.

- **Census (the derived instance list)**: the machine-derived set of `(file:line, node-id, assertion form, patch form, module, attribute)` tuples under `tests/sync/` satisfying the mechanism predicate. A *derived artifact*, regenerated by command; the fix keys on the predicate, never on a transcribed list. Measured on `98198e980` for the `time.sleep`-on-`saas_client` slice: **14 live** `*.time.sleep` patch sites — 13 in `test_saas_client.py` plus **1 in `test_saas_client_origin.py:229`** — with the docstring occurrence at `test_saas_client.py:559` **excluded**, since `NFR-007` requires the AST to skip docstrings. (The earlier "13 live + 1 docstring" composition was wrong and would land an implementer on 13 or 15.) 4 nodes bearing assertions, 5 corruptible assertions. **Files-scanned is scope-dependent and `[NEEDS RATIFICATION]`** — 141 under `tests/sync/`, 22 in the `tests/sync/tracker/` subtree; see SC-001. R1's census could not see context-manager `patch()` or `side_effect=` kwargs and therefore **missed 9 further instances** under `tests/sync/` — the two blind spots and the nine instances are enumerated in `### The class is not confined to tests/sync/tracker/`.
- **Corruptible assertion**: an assertion whose verdict changes when an unrelated thread calls the patched module attribute during the patch window. Includes pure call-count forms (`assert_called_once_with`, `call_count`, `len(call_args_list) == N`), whole-list value equalities derived from the unfiltered recorder (`delays == [...]`, `sleeps == [...]`), and exact-list `side_effect` stimuli that a concurrent caller can exhaust into `StopIteration`. **Explicitly *not* a fix**: `assert <value> in [c.args[0] for c in mock.call_args_list]` — non-corruptible and value-checking, but it silently drops cardinality, and FR-002 / SC-003 Arm 3 exist to refuse it.
- **Delay-sequence contract**: the ordered list of delay arguments the code under test is required to issue — `[0.9, 2.0, 4.4]` for the poll backoff (jitter factors 0.9/1.0/1.1 from `secrets.randbelow` side effects 1000/2000/3000), and the single 429 waits `3.0`, `5.0`, `2.0`. This is the *intent* FR-002 preserves; the current expression of it is corruptible, the contract itself is not.
- **Corruptibility guard**: the shipped test module carrying, per **census assertion** (five, not four — one per assertion, not one per node), the invariance arm (SC-004a), the pre-fix red arm (SC-004b), and the pollution-floor arm (SC-005). It is simultaneously the red-first proof and the permanent regression instrument, and under R-1 it is also the **base-branch red**: on `98198e980` its `patch("…saas_client._sleep")` cannot be set up.
- **R-1 alias seam**: module-scope `_sleep` / `_monotonic` / `_randbelow` in `saas_client.py`, **bound by assignment** (`_sleep = time.sleep`, never a wrapper `def`), with every call site routed through them **and every existing patch decorator retargeted onto them** (FR-012 — 24 sites; without this the seam is inert). A **declared, ADR-recorded** testability seam — the distinction from an incidental one is the ADR plus the gate arm asserting its routing (FR-010 conditions i, ii and iv).
- **Call-site injection point (the competing idiom)**: a keyword parameter on the function that performs the stdlib call, defaulting to the stdlib callable — `run_final_sync_with_retries(…, *, sleep=None)` at `batch.py:628-631`, `sleeper = time.sleep if sleep is None else sleep` at `:641`. **Distinct from the alias seam and preferred where it already exists** (FR-011). Patched by *passing an argument*, not by `patch()` at all, so it is immune to the mechanism by construction and never appears in the census.
- **~~Composition arms~~** — **retired.** R1 defined **Arm A** = pristine `upstream/main` as a green control and **Arm B** = the PR #3209 composition as the only discriminating arm. Both premises are false: pristine `main` reddens on this class in 11 of 18 jobs including at `98198e980`, so Arm A is not a control; and a single run is clean 39% of the time pre-fix, so Arm B does not discriminate either. See the SC-006 entry for the retirement and what replaces it.

---

## Success Criteria *(mandatory)*

Every criterion below is stated as a command plus its expected output. `<census>`, `<guard>` and
`<gate>` denote repo-committed artifacts whose paths `plan.md` chooses — the criterion pins the
**output**, not the path. All commands run from the repo root, output **redirected, never piped**
(piping loses the exit code).

**Interpreter and runner are pinned** (see `### Environment`, which is binding and carries the proof):
every command below is `./.venv/bin/python …` — the direct form, with **no resolver involvement**. It is
valid because the tree is provisioned once by
`uv sync --python 3.12 --extra test --extra lint`, and the WP verifies `command -v` first.
The equivalent uv-driven form, where one is preferred, is
`uv run --python 3.12 --extra test --extra lint python -m …`.

**Neither `python3 -m pytest` (R1's form) nor `uv run --python 3.12 python …` (R2's form) may be used.**
The first is 3.14.4 here with no project dependencies. The second **uninstalls 70 packages including
`pytest`, `ruff` and `mypy`** and then fails — proved by `uv sync --dry-run --python 3.12`, and observed
twice: once during planning, and once again during this post-plan pass, where a bare `uv run` reached the
shell by accident and **recreated `.venv` at 3.11.15** (it honours `.python-version`, which still reads
`3.11.15` while CI and the venv are 3.12 — so the destructive path also silently downgrades the
interpreter two minor versions away from CI). Recovery is
`uv sync --python 3.12 --extra test --extra lint`, verified to restore 3.12.13 / pytest 9.0.3 /
ruff 0.15.12 / mypy 1.20.2.

**Baseline is pinned by SHA** — `98198e980`, not
the moving ref `upstream/main` (they are equal today; that is a coincidence, not a guarantee).

**Criterion count: 14 delivery criteria** — `SC-001`–`SC-005`, `SC-007`–`SC-010`, `SC-012`–`SC-016`.
Two IDs are not delivery criteria and are retained rather than renumbered: **`SC-006` is retired**
(no discriminating full-shard arm exists) and **`SC-011` is demoted to a spec self-check** (it was
already green before any work began, so it graded the spec, not the implementation). Both entries
state why, in place.

### Measurable Outcomes

- **SC-001 — the class closes to zero, on the same denominators, with the assertion count pinned.**
  `./.venv/bin/python <census> tests/sync --json > /tmp/c.json` →
  `nodes_with_sleep_assertions: 4`, **`sleep_assertions: 5`**,
  **`corruptible_assertions: 0`** (pre-fix value on `98198e980`: `5`).
  These three denominators must not move; only `corruptible_assertions` may.
  `sleep_assertions: 5` is new and load-bearing: R1 pinned **nodes** only, so an implementation could
  collapse the five assertions into fewer and still report `nodes_with_sleep_assertions: 4`.
  The scan scope is `tests/sync/` (R-2). The three denominators above are the
  `saas_client` slice; the report must **additionally** list the 9 non-tracker instances by
  `file:line` and show each `disposition: hardened|out-of-class` with a reason.

  **Two counters removed from the pinned set — both were unsatisfiable, for different reasons.**
  - **`sleep_patch_sites: 14` cannot survive FR-012.** The `14` counts occurrences of the string
    `specify_cli.tracker.saas_client.time.sleep`; after the retargets, **0** sites match it. Pinning
    `14` would make the criterion fail *because* the fix landed. Restated so it is invariant across the
    change: the census reports **`sleep_seam_patch_sites`** = the number of patch sites targeting the
    module's sleep seam **in whichever state the tree is in** — i.e. matching
    `…saas_client.time.sleep` **or** `…saas_client._sleep` — which is **14** pre-fix (13 in
    `test_saas_client.py` + 1 in `…_origin.py:229`, per `:504`) and **14** post-fix. A criterion phrased on one target string only is a criterion that
    grades the tree's *state*, not its *correctness*.
  - **`files_scanned: 22` is `[NEEDS RATIFICATION]`, bundled with the counter above.** Measured:
    `find tests/sync -name '*.py' | wc -l` → **141**; `ls tests/sync/tracker/*.py | wc -l` → **22**. The
    scan scope is `tests/sync/` (141), so `22` is the *tracker subtree*, not the scanned set — the
    criterion as R2 wrote it is unsatisfiable by the scan it mandates. The census must report
    `files_scanned` **per scope**, labelled, and the operator ratifies which is pinned. Do not pick one
    silently: `22` is the number a narrowed scope would produce, and a narrowed scope is BLOCKER-2's
    exact failure.

- **SC-002 — the delay contract is still asserted, from live AST assertion nodes.**
  `./.venv/bin/python <census> tests/sync --contract` → exactly four lines, in file order:
  ```
  test_saas_client.py::TestPolling::test_exponential_backoff_intervals            n=3  delays=[0.9, 2.0, 4.4]
  test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after          n=1  delays=[3.0]
  test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing   n=1  delays=[5.0]
  test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises      n=1  delays=[2.0]
  ```
  Derived from `ast.Assert` / assert-method-call nodes **inside** the named functions. Docstrings,
  comments and string literals must not contribute (NFR-007, criterion SC-015).
  `n=` must be derived from the assertion's own **cardinality expression**, not from the length of the
  printed delay list — otherwise `assert 3.0 in [...]` prints `n=1  delays=[3.0]` honestly while
  asserting no cardinality at all.

- **SC-003 — the instrument catches a wrong backoff, in all three mutation kinds (positive twin for SC-001).**
  Arm 1 (**wrong value**): `sed -i 's/^        delay = 1.0$/        delay = 1.5/' src/specify_cli/tracker/saas_client.py`
  (line 478), then
  `./.venv/bin/python -m pytest "tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals" -q -ra -p no:cacheprovider`
  → `1 failed`, failure text showing observed `[1.35, 3.0, 6.6000000000000005]` against expected
  `[0.9, 2.0, 4.4]`. **The literal is `6.6000000000000005`** — production computes `6.0 * 1.1`;
  `6.6` is unsatisfiable as a pinned string. A criterion accepting `pytest.approx` must say so
  explicitly and then cannot pin the text at all; the exact literal is preferred.
  Arm 2 (**wrong per-call value**): revert; change the 429 sleep call at `saas_client.py:439`
  (post-R-1 `_sleep(float(wait_seconds))`) to `… * 2`, run the three 429 census nodes → `3 failed`,
  each naming the doubled value (`6.0`, `10.0`, `4.0`).
  Arm 3 (**wrong cardinality — the arm R1 omitted**): revert; **duplicate** the `_sleep(...)` call at
  `saas_client.py:439` (two calls, same value) and add a fourth `pending` response to the backoff
  node's fixture, run the four census nodes → **`4 failed`, each failing on the call count**, and the
  failure text must name the observed-vs-expected **counts** (`4 != 3`, `2 != 1`), not a delay value.
  This is the arm that refuses `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]`: that
  rewrite is genuinely non-corruptible, honestly value-checking, and passes Arms 1–2 — and is green
  here.
  Arm 4: `git checkout -- src/specify_cli/tracker/saas_client.py` **and the fixture**, run all four →
  `4 passed`. Report `git status --porcelain src/ tests/` as empty.

- **SC-004 — red-first, kept live, five arms — one per census assertion.**
  `./.venv/bin/python -m pytest <guard> -q -ra -p no:cacheprovider` → all pass, with
  **two sub-arms for each of the five census assertions** (R1 covered four of five: `:786`'s
  `assert delays == [0.9, 2.0, 4.4]` had no pre-fix red arm, and it is the member most likely to be
  "hardened" while still reading the unfiltered recorder):

  | # | Census assertion | Arm (b) — the literal pre-fix form (`mock` = the **stdlib** `time.sleep` recorder, not `_sleep`) |
  |---|---|---|
  | 1 | `test_saas_client.py:784` `assert len(sleep_calls) == 3` | `len(mock.call_args_list) == 3` |
  | 2 | `test_saas_client.py:786` `assert delays == [0.9, 2.0, 4.4]` | `[c.args[0] for c in mock.call_args_list] == [0.9, 2.0, 4.4]` |
  | 3 | `test_saas_client.py:937` `mock_sleep.assert_called_once_with(3.0)` | `mock.assert_called_once_with(3.0)` |
  | 4 | `test_saas_client.py:957` `mock_sleep.assert_called_once_with(5.0)` | `mock.assert_called_once_with(5.0)` |
  | 5 | `test_saas_client_origin.py:261` `mock_sleep.assert_called_once_with(2.0)` | `mock.assert_called_once_with(2.0)` |

  Arm (a) per row: the hardened assertion's verdict is unchanged while a probe thread is inside a
  `time.sleep` loop. Arm (b) per row: the **pre-fix expression form**, evaluated against the
  **stdlib-polluted recorder**, patched in the **same window** as the assertion's `_sleep` mock,
  raises `AssertionError`. *Not the `_sleep` mock: post-fix that recorder sees exactly 3/1/1/1, so
  arm (b) would pass instead of raise — see SC-005.* Arm (b) is the defect's red; it must
  be the literal pre-fix form, diffable against `98198e980`, not a paraphrase.
  The guard's output must print the five row identifiers so a reviewer can count them.

- **SC-005 — the injection instrument is proven to be firing (positive twin for SC-004).**
  **Restated. R2's construction became a tautology the moment R-1 landed**, and the restatement is
  strictly stronger. R2 required `polluted_calls=<N>`, `N ≥ 100`, *"counted on the **same mock object**
  the hardened assertion reads"*. Post-R-1 that is impossible by construction: the hardened assertion
  reads the `_sleep` recorder and a thread calling stdlib `time.sleep` **structurally cannot reach it** —
  that is the fix working. The two-probe patch R2's `plan.md` proposed in response is worse, not better:
  `alias_recorder_calls_from_probe == 0` is **unfalsifiable** post-fix (it is green on a tree where the
  fix is 5% done, and green on a tree where the probe body is `pass`), and its twin
  `stdlib_probe_calls >= 100` is a counter **the probe increments about itself** — a probe whose body is
  `counter += 1` satisfies both while sleeping zero times.

  **Binding construction: two mocks in one window, both numbers read off recorders.**
  Inside a single patch window, patch **both** stdlib `time.sleep` **and**
  `specify_cli.tracker.saas_client._sleep`. Run the production call plus the probe thread. Then assert,
  in the same test body:
  - `stdlib_mock.call_count >= 100` — the probe's volume, read off a **recorder**, not a self-report;
  - `alias_mock.call_count == <expected>` — the exact attributed cardinality (3 / 1 / 1 / 1 per SC-004's
    five rows), read off the recorder the assertion actually uses;
  - and the two must therefore **disagree by exactly the injected volume**, which is the immunity
    statement, made falsifiable.

  **What this catches, stated exactly — simulated, not assumed.** A probe that never sleeps fails the
  first assertion. **Any tree where the *reroutes* are incomplete fails the second**: a production call
  site still calling `time.sleep` directly lands on `stdlib_mock`, so `alias_mock.call_count` falls
  *below* its equality and the arm reds. That is `T007`'s failure mode.

  **CORRECTED 2026-08-07 (WP02 review, disproved by construction).** This paragraph previously claimed
  *"Any tree where the **retargets** are incomplete fails the second… That is BLOCKER-1's failure mode,
  and it is the criterion's main power."* **That is false.** The guard binds `_sleep` **by name in its
  own `patch()` window** and drives production directly; it never reads the census files' decorators, so
  the state of those 24 decorators is invisible to it. Measured on `e652ff9fa` — the real intermediate
  commit where the aliases are present and **0 of 24** decorators are retargeted, i.e. maximal
  incompleteness — the guard returns `5 passed`, `EXIT=0`. **Incomplete retargets are owned solely by
  `SC-007` arm 4c**, and by the census files' own assertions (which report `assert 0 == 3` there). Do not
  read this criterion as covering them.
  **What it does *not* catch**: a wrapper-form alias **with** the retargets complete is genuinely
  runtime-immune and passes — verified. So this criterion is *not* the wrapper defense; `SC-007` arm 4b
  is, and the two are not interchangeable. **This construction does prove the load-bearing property
  nothing else in this spec asserts**: that `_sleep` is bound **at import**, since only an import-time
  binding makes `stdlib_mock` and `alias_mock` count different things at all.

  The per-row `stdlib` and `alias` counts, and the probe thread name, are printed (NFR-001).
  **The mutual dependency with SC-004 survives**: arm (b) evaluates the pre-fix expression against the
  *stdlib*-polluted view, so a probe landing 0 calls makes arm (b) pass instead of raise, and the guard
  goes red. A vacuous probe remains impossible rather than merely discouraged.

- **SC-006 — RETIRED. No full-shard arm discriminates a fix from no fix.**
  **Not a delivery criterion.** R1 defined Arm A (pristine `upstream/main`, "green control") and Arm B
  (the PR #3209 composition, "the only discriminating arm"). Both premises are measured false:
  pristine `main` reddens on this class in **11 of 18** consecutive `fast-tests-sync` jobs including
  at `98198e980`, so Arm A is not a control; and a single run is clean **39%** of the time pre-fix, so
  a green Arm B commits exactly the error the adversarial table forbids — treating a pass as evidence.
  Rebuilding it as *repeated parallel* runs was considered and rejected: the 61% red rate is measured
  on CI's 4-vCPU runner topology across differing commits and does not transfer to a repetition count
  on any other machine; `C-001` forbids this mission from running `tests/sync` at all in this window;
  and the environment has no `pytest`. **No repetition count can be justified, so the criterion is
  retired rather than weakened.** The mission rests on the injection guard (SC-004/SC-005), the
  mechanism gate (SC-007), and the base-branch red (`### Charter red-on-base`) — all of which are
  structural rather than probabilistic.
  **Replaced by a non-gating observation** (reported, never a pass/fail gate): record the mission PR's
  `fast-tests-sync` outcome with its head SHA and the pre-fix rate `11/18` alongside it, labelled
  *non-discriminating*. Any command that survives here must carry `-n auto --dist loadfile` and CI's
  four `--ignore=` entries, because a serial run is a different experiment from the one CI fails.
  Where PR #3209 is referenced, its **head SHA** `5e98c2bb7` is used, never the branch name.
  R1's Arm A pass/skip split (`2116 passed, 11 skipped`) was unattributed and unmarked; the verifiable
  halves are `2127/2398` selected with `271 deselected` and `2116 + 11 = 2127`. Had the arm survived,
  its assertion would have been `selected == 2127`, `FAILED == 0`, `ERROR tests/ == 0` — robust to the
  split — rather than a pass/skip pair.

- **SC-007 — the gate is mechanism-keyed and non-vacuous, and it names what it scanned.**
  `./.venv/bin/python -m pytest <gate> -q -ra -p no:cacheprovider` → passes, and its output:
  1. **Names the files it opened**, not a count. R1's `scanned_files >= 22` is satisfied by globbing
     any 22+ files under `tests/` while never opening `tests/sync/tracker/`. The named set must
     include `tests/sync/tracker/test_saas_client.py`, `tests/sync/tracker/test_saas_client_origin.py`,
     `tests/sync/test_final_sync_diagnostics.py`, `tests/sync/test_git_metadata.py`.
  2. Reports the patch-site split **`13` in `test_saas_client.py` + `1` at
     `test_saas_client_origin.py:229` = 14**, and the **four census node-ids** verbatim
     (`TestPolling::test_exponential_backoff_intervals`,
     `TestRetryBehaviors::test_429_respects_retry_after`,
     `TestRetryBehaviors::test_429_defaults_to_5s_when_missing`,
     `TestSearchIssues::test_429_retries_then_raises`).
  3. Passes a self-mutation arm on **each of three** synthetic in-memory modules, none of whose forms
     exist in the tree today: (a) `assert mock_sleep.call_count == 1` under a decorator patch;
     (b) `assert mock_run.call_count == 1` under `@patch("pkg.mod.subprocess.run")` — proving the
     predicate is keyed on the **mechanism**, not on `time.sleep`; (c) a **context-manager** `patch()`
     with a `side_effect=` kwarg feeding a list-equality assertion — the two blind spots that hid
     `test_final_sync_diagnostics.py:309`.
  4. **Asserts the R-1 seam on BOTH sides — product call sites and test target strings.** R2's arm 4
     asserted only the product side, and did so with a carve-out that admitted the wrapper cheat.
     Restated in four parts, all required:

     **(4a) Product side — zero *resolved* reach-through calls, no carve-out.**
     `src/specify_cli/tracker/saas_client.py` contains **0** calls whose callee **resolves** to
     `time.sleep` / `time.monotonic` / `secrets.randbelow`. **The "outside the three alias definitions"
     carve-out of R2 is struck** — under the wrapper form the only `time.sleep(` *is* inside the alias
     definition, so the carve-out made the negative true while the defect was fully intact.
     Resolution is by reading the module's **own AST import bindings** (`ast.Import` / `ast.ImportFrom`,
     including `asname` aliases), so all of `import time as t; t.sleep(x)`,
     `from time import sleep; sleep(x)`, and `getattr(time, "sleep")(x)` are caught. Copy the AST shape
     from `tests/architectural/test_protection_resolver_call_sites.py:90-109` (`ast.parse` →
     `ast.walk` → `isinstance(node, ast.Call)` → resolve `node.func`), which is the repo's existing
     precedent for exactly this check.

     **(4b) Product side — the three names are bound to the right objects, by assignment.**
     Assert the three module-scope names `_sleep` / `_monotonic` / `_randbelow` are each bound **by
     assignment** to exactly `time.sleep` / `time.monotonic` / `secrets.randbelow` — i.e. the
     module-scope statement is an `ast.Assign` whose value resolves to that attribute, **not** an
     `ast.FunctionDef`.

     **This is the only arm that refuses the wrapper form, and it is a *structural* arm on purpose.** A
     wrapper alias with all 24 retargets complete is runtime-immune and passes every behavioural arm in
     this spec (verified by simulation) — so no runtime criterion can catch it, and 4b must be static.
     Its justification is that the wrapper keeps a live `time.sleep` lookup inside the module, which (i)
     re-admits the reach-through the seam exists to remove the moment any future code or any missed
     decorator reads it, and (ii) removes the property that makes this seam safe to maintain: under
     assignment, an un-retargeted decorator fails **loudly and immediately** (recorder sees `0`), whereas
     under the wrapper it passes **silently** with the defect intact. 4b preserves the self-enforcing
     property; it is not merely a style preference.

     **(4c) Test side — the target strings actually moved (FR-012).** Assert, over
     `tests/sync/tracker/test_saas_client.py` and `tests/sync/tracker/test_saas_client_origin.py`:
     **0** `patch()` target strings equal to `specify_cli.tracker.saas_client.time.sleep`,
     `specify_cli.tracker.saas_client.time.monotonic`, or
     `specify_cli.tracker.saas_client.secrets.randbelow`, **and**
     `13 + 1 = 14` targeting `…_sleep`, `9` targeting `…_monotonic`, `1` targeting `…_randbelow`.

     **Counted from AST `patch()` call nodes, never by `grep`** — and the distinction is load-bearing
     here, not pedantic. `test_saas_client.py:559` carries the string
     `specify_cli.tracker.saas_client.time.sleep` **inside the `:513-762` docstring**. A grep-based arm
     would count it and report `1` where the correct answer is `0`, and the natural "fix" would be to
     edit prose to satisfy a numeric gate — which is the failure mode this mission has now hit three
     times. The two docstring occurrences (`:559` and `:715`) should be updated for consistency (they are
     two of the 26 string occurrences), but they are **not** among the 24 retargets and **must not** be counted by this arm.
     NFR-007's AST requirement already binds the census; it binds this arm too.

     Without this part the entire seam can land inert — which is BLOCKER-1. A product-side-only arm
     passes on a tree where not one decorator moved.

     **(4d) Positive twin** (an AST checker that resolves nothing also reports 0): the same check
     reports the **3** alias definitions found by name and the **5** rerouted call sites by line
     (`:439`, `:481`, `:484`, `:515`, `:518` as they land post-fix), so a checker that silently parses
     the wrong file, or parses nothing, fails loudly instead of passing quietly.
  5. Allowlist **frozen shrink-only, not empty at merge** — see the documented exception in
     `plan.md` `## Complexity Tracking`, and the ratchet-registration requirement in its IC-06. A
     baseline key that no ratchet reads is not a baseline; registration is part of this item.
  Enforced over `tests/sync/`. **Not `tests/cli`** — `C-001` forbids this mission from running it.

- **SC-008 — leak-neutral, with a pin check that can actually fail.**
  `./.venv/bin/python -m pytest <guard> tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py -q -ra -p no:cacheprovider -n0 > /tmp/l.txt`
  → `grep -c '^ERROR tests/' /tmp/l.txt` = `0`, and **both** pin checks:
  - `git diff 98198e980 -- tests/sync/_leak_guard.py | grep -cE '^\+\s*_PinnedLeak\('` = `0`.
    R1's pattern was `'^\+.*_PINNED_LEAKS'`, which is **structurally inert**: the entries are
    `_PinnedLeak(...)` calls, and the token `_PINNED_LEAKS` appears only at the declaration
    (`_leak_guard.py:333`) and the derived dict (`:424`), so a diff adding a real entry matches
    **nothing**. Proved on a synthetic diff by the squad.
  - An **AST count** of `_PINNED_LEAKS`' elements pinned at **12** — measured this session:
    `_leak_guard.py:333` is `_PINNED_LEAKS: tuple[_PinnedLeak, ...]` with 12 `_PinnedLeak(...)`
    elements. A grep on a diff only catches *added* lines; the AST count also catches a rewrite that
    adds an entry while restructuring the tuple. **This 12 must be reconciled with `C-003`'s "11
    confirmed leaks"** — the two numbers disagree, and the WP states which is wrong and why.
  **Positive twin** (a leak guard that is inert also reports 0 errors): the same output must contain
  `[FR-007 leak guard] inspected <N> test(s) under tests/sync/.` with **N ≥ 73** — the two census
  files alone collect 73 nodes (`pytest --collect-only -q`, measured on `98198e980`).
  **The twin is serial-only, and the command above pins `-n0` for that reason.** Under xdist the
  controller prints a *different* line (`tests/sync/conftest.py:483-492`): `"inspected {N} test(s) IN
  THIS PROCESS … xdist is active"`, and `conftest.py:467-468` documents a real `-n 4 --dist loadfile`
  run over 2122 tests printing **`inspected 0 test(s)`**. Grepping the serial string under xdist
  matches nothing; grepping `inspected` and reading the number under xdist yields `0` and fails a
  sound guard. `#3115 FR-007`, not this spec's retired FR-007.

- **SC-009 — topology and determinism.**
  `for i in 1 2 3; do ./.venv/bin/python -m pytest tests/sync/tracker/ -m "fast and not windows_ci" -n0 -q; done`
  and the same with `-n auto --dist loadfile`, then `<guard>` alone repeated 10×
  → 6 identical pass sets across the topology runs (NFR-003) and 10/10 passes for the guard
  (NFR-002). Report the observed pass/fail counts per run, not a summary verdict.

- **SC-010 — inventory stamped and scoped.**
  Four separate commands, each with a single comparable value (R1's fourth clause was a **malformed
  command**: `grep -cE … file1 file2` prints one count *per file*, so `= 0` had no single value to
  compare — demonstrated this session):
  1. `grep -c '3136' docs/development/process-global-inventory-3115.md` ≥ `1`.
  2. The doc's verdict column carries an unverified stamp naming the PR #3209 (`5e98c2bb7`)
     falsification of `test_429_respects_retry_after`.
  3. `grep -cE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' plan.md` = `0` **and** the same over
     `<guard-rationale>` = `0`. **The pattern must be bounded to the real id range `E1`–`E53`.** An
     unbounded `\bE[0-9]+\b` is **red on `plan.md` today** — it matches `# noqa: E402` at `plan.md:354`,
     a lint code, not a row id. `plan.md`'s own IC-07 risk asserts "this plan contains none,
     deliberately"; that claim is false as committed, and the criterion, not the plan, is what was
     wrong
     — two commands, two single values. (Equivalently one aggregated command:
     `grep -hoE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' plan.md <guard-rationale> | wc -l` = `0`.) If the depended-on `E`-row
     set is non-empty, this criterion inverts: the doc names each row and each carries a
     re-derivation verdict against the four census nodes.
  4. **Positive twin** (a grep that matches nothing satisfies the negative silently): the identical
     pattern against the inventory itself,
     `grep -cE '^\| E[0-9]+ \|' docs/development/process-global-inventory-3115.md`, must return
     **53** — the measured row count on `98198e980`.

- **SC-011 — DEMOTED to a spec self-check. Not a delivery criterion.**
  R1 stated it as three greps over `spec.md` for the C-005 reasons. Measured against the spec **as
  committed, before any implementation work**: `3 / 3 / 5` — already green. It graded the spec's own
  prose, not the delivered work, so no implementation could ever fail it. **Removed from the criterion
  count.** The underlying requirement (FR-009: the non-goal is recorded with all three reasons) is
  satisfied and verifiable by the same three greps, retained here as an authoring self-check:
  `grep -c 'producer is already named' spec.md` ≥ `1`;
  `grep -c 'cannot .*name a producer' spec.md` ≥ `1`;
  `grep -c 'default outcome' spec.md` ≥ `1`.
  Converting it into something the delivered work can fail was considered and rejected: every
  candidate form still grades prose, and prose-grading is what made it vacuous.

- **SC-012 — lint clean without suppression, config included.**
  `./.venv/bin/ruff check .` → `All checks passed!`, and
  `git diff -U0 98198e980 | grep -cE '^\+.*(# noqa|# type: ignore)'` → `0`, **and**
  `git diff 98198e980 -- ruff.toml pyproject.toml` shows **no added `per-file-ignores` entry and no
  widened `exclude`** — reported as the diff text, not a count, so a reviewer can read it.
  Both files already carry a `per-file-ignores` block (verified: `grep -c per-file-ignores ruff.toml`
  = 1, `pyproject.toml` = 1), so an existence check proves nothing and R1's criterion had a config
  escape hatch: adding an ignore entry or widening `exclude` satisfies "0 added `# noqa`" while
  achieving exactly what `CLAUDE.md` prohibits.

- **SC-013 — the R-1 seam is canonical, and the dead seam is resolved.**
  Restated: under R-1 the sibling *hardening* work retires (FR-006, FR-007), so R1's SC-013 — a
  self-reported string `hardened` / `filed:#<issue>` from `<census> --siblings` — measures nothing
  that remains. What remains is **measured, not self-reported**:
  1. `./.venv/bin/python <census> tests/sync --siblings` reports
     `test_saas_client.py:787` (`secrets.randbelow` count) and `test_saas_client.py:804` (exact-list
     `time.monotonic`) as **`correct-by-alias`**, and the census **verifies** it by deriving the
     disposition. A printed literal is not acceptable. `undisposed` in either slot fails.

     **Restated — R2's derivation was unsatisfiable in both tree states.** R2 required *"resolving each
     patch target's penultimate segment and asserting it is **not** a `ModuleType`"*. For
     `patch("…saas_client._randbelow")` the penultimate segment **is** `saas_client`, which **is** a
     module — so the assertion is false post-fix, and it was equally false pre-fix for
     `…saas_client.secrets.randbelow` (penultimate `secrets`, also a module). It is the identical
     97.7%-over-broad formulation this spec spent three paragraphs correcting for R-2, carried into a
     different criterion unnoticed. **Binding derivation — the narrowed own-module-vs-reach-through
     discriminator, the same one the census uses everywhere else**: resolve the penultimate segment and
     assert the resolved module's `__name__` **equals** the dotted module path — i.e. the patched
     attribute is the module-under-test's **own** attribute, not a reach-through into a shared module.
     `specify_cli.tracker.saas_client._randbelow` → penultimate resolves to
     `specify_cli.tracker.saas_client`, `__name__` matches the path → **own-module → `correct-by-alias`**.
     `specify_cli.tracker.saas_client.secrets.randbelow` → penultimate resolves to `secrets`,
     `__name__` (`secrets`) ≠ path (`specify_cli.tracker.saas_client.secrets`) → **reach-through →
     corruptible**. This discriminates the two states, which is the whole point of the sub-criterion.
  2. **The ADR exists** (FR-010 condition i): a file under `docs/adr/3.x/` naming the alias seam,
     `saas_client.py`, and `#3136`. `grep -rl '_sleep' docs/adr/3.x/ | wc -l` ≥ `1` with the file
     naming all three.
  3. **`_poll_jitter_multiplier` is resolved** (condition iii):
     `grep -rc '_poll_jitter_multiplier' src/ tests/` is either **0** (deleted) or **≥ 2** with a
     caller at the poll site (promoted to sole authority) — and in the promoted case
     `saas_client.py:515-516`'s inline duplicate is gone, so the `1.2`-vs-`1.1999` disagreement cannot
     persist in either outcome. Exactly `1` (definition only, zero callers) **fails** — that is the
     state today.
  4. **The false docstring is corrected.** **Re-anchored — R2's grep was already green on the base tree,
     so the criterion graded nothing.** R2 pinned
     `grep -c 'is the assertion' … → 0` and asserted *"it is `1` today"*. Measured this session, on both
     HEAD and `98198e980`: **0**, exit status 1. The docstring reads
     `there the second value *is* the assertion` — **RST emphasis around `is`**, so the plain-text
     pattern never matched. The line was opened by three reviewers; the grep was never run. This is the
     spec's own named failure mode recurring *inside the criterion written to stop it*.
     **Binding form**, which is `1` today and must become `0`:
     `grep -cE 'is\*? the assertion' tests/sync/tracker/test_saas_client.py` → **0**
     (verified `1` at HEAD, `1` at `98198e980`).
     **Positive twin** (a grep satisfied by deleting the whole
     docstring): `grep -c 'side_effect stimulus' tests/sync/tracker/test_saas_client.py` → **≥ 1**, and
     the replacement text must name the `pytest.raises` at `:806` as the node's only assertion — so the
     correction is a correction, not a deletion.
     **Authoring note for every future grep criterion in this mission**: run it against both trees
     before pinning its expected value, and prefer `-E` with optional-markup tolerance
     (`\*?`, `` `? ``) over plain-text patterns, because this repo's docstrings are RST.
  5. Any `filed:#<issue>` disposition that does survive must be **resolved**:
     `gh issue view <n> --json body,title` contains the node-id and the mechanism. A bare issue number
     is not a disposition.

- **SC-014 — runtime budget, measured on one interpreter (criterion for NFR-005).**
  R1 left NFR-005 with no criterion. Both arms, same command, same interpreter:
  `./.venv/bin/python -m pytest tests/sync/tracker/ -m "fast and not windows_ci" -n0 -q -p no:cacheprovider`,
  once at `98198e980` and once at the mission head → report both wall-clock totals, their delta
  (**≤ 5.0 s**), the slowest individual test from `--durations=10` (**≤ 60 s**), and
  `./.venv/bin/python -V` for each arm (**must be identical**, and must be 3.12.x). A delta
  measured across two interpreters is not a measurement.

- **SC-015 — the census is trustworthy (criterion for NFR-007).**
  R1 described the control fixture in Verification Provenance and commanded it nowhere, while
  `<census>` is the sole instrument for SC-001, SC-002 and SC-013 — so a hardcoded output table
  satisfied all three. The control fixture is **committed as a test** with its ground truth pinned
  in-test: `./.venv/bin/python -m pytest <census-control> -q` → passes, and its output prints
  observed-vs-ground-truth for every count. Ground truth pinned in the fixture:
  3 sleep-patched functions, 1 monotonic-only function that must **not** count, 2 corruptible
  assertions, 1 delay-sequence assertion, 3 decoys ignored (a docstring quoting
  `mock_sleep.assert_called_once_with(9.9)`, a comment `# mock_sleep.call_count == 42`, a string
  literal `'specify_cli.tracker.saas_client.time.sleep'`), **plus two new positive cases R1's census
  could not see**: a context-manager `patch(...)` and a `side_effect=` kwarg sink, each feeding a
  corruptible assertion, both of which must be reported. Plus a **census self-mutation arm**: narrow
  the analyzer to today's five forms and require the control fixture to fail.

- **SC-016 — the constraints with no enforcement are enforced (C-002, C-004, C-008, C-010).**
  R1 left four constraints, two of them High, checked by nothing. One command each, all reported
  together:
  - **C-004** — `git diff 98198e980 -- src/specify_cli/tracker/saas_client.py` and confirm every hunk
    falls inside the two permitted regions: the FR-010 alias definitions plus call-site rerouting at
    `:439`, `:481`, `:484`, `:515`, `:518`; and the `_poll_jitter_multiplier` resolution at
    `:104-106`. **Any other changed line fails the criterion.** This is a criterion that can fail —
    R1's implied form (diff empty) is now false by construction, and its stated form (a
    `git checkout --` revert) is satisfied by a clean revert even if a different line shipped changed.
    Behaviour-side twin: SC-003 Arms 1–3 red and Arm 4 `4 passed` prove the delay values, call
    cardinality and raise conditions are unchanged.
  - **C-008** — `git diff 98198e980 -- .github/workflows/ci-quality.yml` → **no output**.
    **Positive twin** (a `git diff` against a bad ref, or from the wrong directory, is also silent):
    the same report must include `git diff --stat 98198e980 -- src/specify_cli/tracker/saas_client.py`
    showing **non-empty** output, proving the ref resolves and the command is wired up. A silent diff
    is only evidence when a sibling diff from the same invocation is loud.
  - **C-002** — `grep -rc 'ruff format' <wp-notes>` = `0`, and
    `git diff --stat 98198e980 -- src/ tests/` shows no whitespace-or-import-reorder-only file.
  - **C-010** — `./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q`
    → `EXIT=0`, transcript recorded.

### Adversarial Analysis of Success Criteria

Charter-mandated for this programme. The predecessor mission's four-lens squad found **9 of 11**
criteria satisfiable while the defect survived; **R1 of this spec was found at 6 of 13** by a
three-lens post-spec squad. For every criterion, the adversarial implementation that satisfies it
*without fixing anything*, and how it was closed. Rows marked **[R2]** are the cheats the post-spec
squad found and this revision closes; rows marked **[R2-open]** are cheats acknowledged as not fully
closed, with the residual risk stated. Rows marked **[R3]** are the cheats the **post-plan** squad found
— including three that R2's own closures *introduced* — and this revision closes; its vacuity lens
scored **18 sound / 13 passes-while-broken**.

**The pattern worth naming, because it has now happened three times.** Every **[R3]** row below is a
case of a *closure* that was never executed against the tree: a grep pinned without running it
(`SC-013` sub-4), a derivation asserted without resolving it (`SC-013` sub-1), a floor asserted about a
counter that reports on itself (`SC-005`), a negative whose carve-out admitted the thing it forbade
(`SC-007` arm 4). **A cited `file:line` is not evidence that the line asserts anything.** Open it, and
run the command.

| SC | The cheat that satisfies it without a fix | How it was closed |
|----|------------------------------------------|-------------------|
| SC-001 | **Delete the five assertions.** `corruptible_assertions: 0` is trivially true with no assertions at all. | Denominators pinned (`nodes_with_sleep_assertions: 4`, `sleep_assertions: 5`, `sleep_seam_patch_sites: 14`) so the nodes cannot vanish; SC-002 requires the same four contracts at the same values; SC-003 requires them to still fail on a wrong backoff. |
| SC-001 | **[R3] Let the fix itself fail the criterion.** R2 pinned `sleep_patch_sites: 14` counting the string `…saas_client.time.sleep`. After FR-012's retargets **0** sites match it, so a correct implementation reports `0` and fails — the predictable response being to skip the retargets, i.e. ship the inert seam. | Restated as `sleep_seam_patch_sites`, matching `…time.sleep` **or** `…_sleep` — **14** in either tree state. A denominator must grade correctness, not which state the tree happens to be in. |
| SC-001 | **[R3] Satisfy `files_scanned: 22` by scanning only `tests/sync/tracker/`** — which is the narrowed scope BLOCKER-2 exists to forbid, and R2's own criterion mandated it while also mandating a `tests/sync/` scan (141 files). Unsatisfiable as written; the cheap resolution is the harmful one. | Marked `[NEEDS RATIFICATION]` and bundled for one operator decision. The census reports `files_scanned` **per scope**, labelled (141 / 22). Neither number is silently pinned. |
| SC-001 | **[R2] Rewrite each assertion as `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]`.** Genuinely non-corruptible (an intruder's extra call does not change the verdict), so `corruptible_assertions: 0` is *honestly* true; the 22/14/4 denominators are untouched; SC-002 emits `n=1 delays=[3.0]` from a live `ast.Assert` node; SC-003 Arms 1–2 still redden it; SC-004 arm (b) still raises. **Every R1 criterion green — and the test no longer detects a production change that issues two attributed sleeps instead of one.** | Two independent closures. **(1)** `sleep_assertions: 5` added as a denominator — R1 pinned *nodes* only, so five assertions could collapse into fewer. **(2)** SC-003 **Arm 3**, a cardinality mutation (duplicate the `_sleep(...)` call at `saas_client.py:439`; add a fourth `pending` response for the backoff node) requiring red **on the count**, with the failure text naming observed-vs-expected counts. The `in`-form is green on Arm 3 and therefore fails the criterion set. FR-002 now *measures* cardinality instead of requiring it in prose. |
| SC-001 | Make the census stop looking at the corruptible forms (narrow the analyzer). | SC-007's self-mutation arms use three forms **absent from the tree**, and SC-015 adds a **census** self-mutation arm: narrow the analyzer to today's five forms and the control fixture must fail. |
| SC-001 | **[R2]** Report `corruptible_assertions: 0` while the class is open elsewhere in the same shard — R1's census could not see context-manager `patch()` or `side_effect=` kwargs, so the 9 `tests/sync/` instances were invisible to it. | Scope widened to `tests/sync/` (R-2); the predicate is mechanism-keyed; SC-001 must additionally list the 9 non-tracker instances with a disposition; SC-015's control fixture carries both previously-invisible forms as positive cases. |
| SC-002 | Keep the literals in a **docstring** or dead code and delete the live assertions. | Contract lines derived from `ast.Assert` / assert-method-call nodes inside the named functions (NFR-007), with the control fixture proving docstring/comment/literal decoys are excluded — **now a committed test with pinned ground truth (SC-015)**, not prose. |
| SC-002 | Assert a *subset* — e.g. only `delays[0] == 0.9` — and still print `delays=[0.9, 2.0, 4.4]`. | The criterion pins `n=3` alongside the sequence, **and `n=` must be derived from the assertion's own cardinality expression, not from the printed list's length** — otherwise the `in`-form prints `n=1 delays=[3.0]` honestly while asserting no cardinality. |
| SC-003 | Pick a mutation the assertion does not cover (e.g. `cap = 30.0`, never reached in 3 polls) and report green as "no regression". | The mutation is named to the exact line and the exact expected observed sequence. A green there is a criterion failure. |
| SC-003 | **[R2]** The pinned failure text `[1.35, 3.0, 6.6]` is **unsatisfiable**, so the arm can never be reported as satisfied and gets quietly downgraded to "close enough". | Corrected to `[1.35, 3.0, 6.6000000000000005]` (computed against production: `6.0 * 1.1`). The unmutated `[0.9, 2.0, 4.4]` *is* exact, which is why the current test passes. `pytest.approx` is permitted only if stated, and then the text cannot be pinned. |
| SC-003 | Commit the mutation's revert incorrectly and leave the tree changed. | Arm 4 requires `git checkout --` on **the source and the fixture**, `4 passed`, and `git status --porcelain src/ tests/` empty. C-004 (restated) plus SC-016 bound what may differ from `98198e980` at all. |
| SC-004 | Write the "pre-fix form" arm as something trivially false (`assert False`, `assert_called_once_with(999.0)`). | The arm must use the **literal pre-fix expression** against the **stdlib-polluted recorder** in the **same window**. A reviewer diffs arm (b) against `98198e980`'s assertion text. |
| SC-004 | Let the probe never actually sleep, so arm (a) passes vacuously. | SC-005's floor (≥ 100 landed calls, printed) plus the mutual dependency: with no pollution, arm (b) **passes** instead of raising, which fails the guard. |
| SC-004 | **[R2] Harden four of five and leave `:786` reading the unfiltered recorder.** R1's arm (b) enumerated `assert_called_once_with(<value>)` for the three 429 nodes and `len(call_args_list) == 3` for the backoff node — **four forms for five assertions**. `assert delays == [0.9, 2.0, 4.4]` had no pre-fix red arm, and it is the member most likely to be "hardened" cosmetically. | SC-004 is now **five rows, one per census assertion**, each with its literal pre-fix form tabulated, and the guard prints the five row identifiers so a reviewer can count them. |
| SC-005 | Assert `polluted_calls >= 0`. | Threshold fixed at ≥ 100 (NFR-001), **with its derivation corrected**: 4× below the predecessor's observed 399, and `100/28 = 3.57×` above the smallest observed CI inflation. R1's "33× above 48" was arithmetically impossible (`100/3`). |
| SC-005 | ~~Count the probe's calls on a *different* mock than the one the assertion reads.~~ **SUPERSEDED** — reading the two recorders separately (`stdlib_mock` vs `alias_mock`) is now the sanctioned binding construction, not an attack. | The per-thread split must name the probe thread. The mutual dependency with SC-004 arm (b) makes a vacuous probe self-defeating. *(R2 called this "the best-built criterion in the set". The post-plan squad defeated it — see the next two rows. The claim is struck.)* |
| SC-005 | **[R3] A probe whose body is `counter += 1; pass`.** R2's own closure required `stdlib_probe_calls >= 100` — a counter **the probe increments about itself**, not a recorder — so a probe that never sleeps satisfies the floor. | Both numbers now read off **mocks**: `stdlib_mock.call_count >= 100`, where `stdlib_mock` is a `patch` of stdlib `time.sleep`. A self-report is no longer accepted as a measurement anywhere in this criterion. |
| SC-005 | **[R3] `alias_recorder_calls == 0` is unfalsifiable.** R2's Probe A asserted the alias recorder sees **0** probe calls. Post-fix that is structurally guaranteed — it is green on a tree where the fix is 5% done, green where the retargets never happened, and green where the probe body is `pass`. It measures the *language*, not the *mission*. | Replaced by `alias_mock.call_count == <expected>` (3/1/1/1) — an **equality on a positive number**, in the **same window** as `stdlib_mock.call_count >= 100`. The two must disagree by exactly the injected volume, so **any incomplete-retarget tree fails** (the foreign calls land on the recorder the assertion reads). **Scope stated honestly**: this does *not* catch a wrapper-form alias whose retargets are complete — that state is runtime-immune and passes. `SC-007` arm 4b is the wrapper defense; the two criteria are not interchangeable. |
| SC-006 | **[R2] Run Arm A only and declare victory** — R1 called pristine main a green control. | **Retired.** Pristine main is *not* green: 11 of 18 jobs red on this class, including at `98198e980` (`3 failed, 2113 passed, 11 skipped`; `2113 + 3 = 2116` — the same selection R1 quoted as green). Arm A was never a control. |
| SC-006 | **[R2] Run Arm B once, see green, declare the fix proved.** A single pre-fix run is clean **39%** of the time, so a green Arm B commits exactly the error this spec's own adversarial table forbids. | **Retired.** No repetition count is justifiable: the 61% rate is CI-topology-specific, `C-001` forbids running `tests/sync` here, and the environment has no `pytest`. Replaced by a *non-gating* observation. The mission rests on structural arms (SC-004/005/007 and the base-branch red) rather than probabilistic ones. |
| SC-006 | **[R2] Point Arm B at "PR #3209's branch"** — the branch moved twice during this mission (`96494e5ec` → `783c137d7` → `5e98c2bb7`), so the arm is not reproducible and R1's quoted transcript is from a superseded head on which the backoff node **passes**. | Head SHA pinned wherever PR #3209 is referenced: `5e98c2bb7`. |
| SC-006 | **[R2] Run the arm serially** while CI runs `-n auto --dist loadfile` (`ci-quality.yml:1161-1172`) — a different experiment from the one CI fails. | Any surviving command must carry `-n auto --dist loadfile` **and** CI's four `--ignore=` entries. |
| SC-006 | Count the `#3130` leak-guard `ERROR`s as failures and "fix" them. | C-003 puts them out of scope; `^ERROR tests/` (not `^ERROR `) and `-ra` (not `-rf`), redirected not piped. Retained for whatever full-shard reporting survives. |
| SC-007 | Ship a gate that scans an empty file list, or hardcodes a pass. | Self-mutation arms on three synthetic modules, plus the named-file requirement below. |
| SC-007 | **[R2] Point the gate's glob at `tests/**`** — reports `scanned_files: 300 >= 22`, `patch_sites: 131 >= 14`, passes its self-mutation arm, and **never opens `tests/sync/tracker/`**. R1's floor is a **count**, not a membership set. | The gate must **name** the files it opened (four named explicitly), report the `13 + 1` patch-site split, and print the four census node-ids verbatim. A count floor is no longer sufficient. |
| SC-007 | **[R2] Key the gate on `time.sleep`** — as R1 specified it refuses corruptible *sleep* assertions, so nothing stops `mock_randbelow.call_count == 1` (three lines from a census assertion) or `mock_run.call_count == 2`. | R-2: the predicate is the **mechanism** (penultimate segment resolves to a `ModuleType`), and self-mutation arm (b) uses `subprocess.run` specifically to prove the gate is not `time.sleep`-shaped. |
| SC-007 | **[R2] Inspect decorators only**, so a context-manager `patch()` with a `side_effect=` kwarg walks past — exactly how `test_final_sync_diagnostics.py:309` hid from R1's census. | Self-mutation arm (c) is that form; SC-015's control fixture carries it as a positive case. |
| SC-007 | Allowlist the five existing assertions instead of fixing them. | Frozen shrink-only baseline with a `file:line` + target + assertion-form triple per entry; SC-001 independently requires `corruptible_assertions: 0`. |
| SC-007 | **[R2]** Ship the alias, then let a later edit call `time.sleep` directly again — the gate stays green and the hardening silently evaporates. | Gate arm 4a asserts the **seam's own call-site routing**: 0 calls in `saas_client.py` whose callee *resolves* to `time.sleep` / `time.monotonic` / `secrets.randbelow`, AST-checked. FR-010 condition (ii). |
| SC-007 | **[R3] Use the wrapper form `def _sleep(s): time.sleep(s)` and skip all 24 retargets.** R2's arm 4 said "0 direct calls **outside the three alias definitions**" — under the wrapper the only `time.sleep(` **is** inside the alias definition, so the carve-out excludes it and arm 4 passes. And the wrapper *preserves* what the un-retargeted decorator patches, so **every node stays green in a quiet process while the recorder goes on counting any concurrent thread's calls** — verified by simulation: recorder sees `3`, defect 100% intact. Under the assignment form the same shortcut sees `0` and fails loudly, which is exactly why the wrapper is the attractive one: **it makes the 24-decorator edit look optional.** | The carve-out is **struck** (arm 4a). Arm **4b** asserts each of the three names is an `ast.Assign` resolving to the stdlib attribute — **not** an `ast.FunctionDef` — which preserves the self-enforcing property. Arm **4c** independently pins the retargets by count. **Both are required**: 4b alone permits a correct-but-fragile wrapper tree, 4c alone permits a wrapper tree that is immune today and re-corrupts the moment a decorator is reverted. |
| SC-007 | **[R3] Evade arm 4's negative by aliasing the import.** `import time as t; t.sleep(x)`, `from time import sleep; sleep(x)`, and `getattr(time, "sleep")(x)` all leave "0 direct `time.sleep(` calls" true. | Arm 4a resolves the module's **own** `ast.Import` / `ast.ImportFrom` bindings (including `asname`) and asserts zero calls whose callee **resolves** to the three attributes — not zero textual matches. Shape copied from `tests/architectural/test_protection_resolver_call_sites.py:90-109`. |
| SC-007 | **[R3] Land the whole seam and never move one decorator.** R2's arm 4 checked the **product** side only. A tree with all three aliases, all five call sites rerouted, the ADR written and the gate green — and all 24 decorators still targeting `…time.sleep` — satisfies every product-side arm while the assertions read the process-global recorder exactly as before. **This is BLOCKER-1, and it was the default outcome of R2's plan.** | Arm **4c** asserts the **test-side target strings**: 0 occurrences of the three pre-fix targets, and `14` / `9` / `1` occurrences of the three post-fix targets, across both tracker files. FR-012 makes the retargets a numbered requirement rather than an implied consequence. |
| SC-008 | Pin the guard's own leaked probe thread in `_PINNED_LEAKS` and call it clean. | Two checks, not one — see the next row. |
| SC-008 | **[R2] Add a real pin entry.** R1's check is `git diff … \| grep -cE '^\+.*_PINNED_LEAKS'` = 0, which is **structurally inert**: entries are `_PinnedLeak(...)` calls and the token appears only at the declaration (`_leak_guard.py:333`) and the derived dict (`:424`), so a diff adding a real entry matches **nothing** — proved on a synthetic diff. | `^\+\s*_PinnedLeak\(` **plus** an AST count of the tuple's elements pinned at **12** (measured), which also catches a rewrite that adds an entry while restructuring. The 12 must be reconciled against `C-003`'s "11 confirmed leaks" — the WP states which number is wrong. |
| SC-008 | **[R2] Run the positive twin under xdist.** R1's twin greps `[FR-007 leak guard] inspected <N> test(s)` for `N >= 73`, but that exact string is printed **only serially**; under xdist `conftest.py:483-492` prints a different line, and `conftest.py:467-468` documents a real `-n 4` run over 2122 tests printing `inspected 0 test(s)`. Grepping `inspected` under xdist yields `0` and fails a sound guard. | The command pins `-n0`, and the criterion states the serial-only property with the two conftest citations so nobody "fixes" a false red. |
| SC-009 | Run once, get green, call it deterministic. | Explicit repetition counts (3× per topology, 10× for the guard) with per-run counts reported. |
| SC-010 | Stamp the doc "unverified" and stop. | The doc must name the depended-on `E`-rows; if empty, plan and guard rationale must cite **zero** `E`-numbers, making "we depend on none of it" falsifiable. |
| SC-010 | **[R2]** Report the `E`-number clause as satisfied from a **malformed command** — `grep -cE … plan.md <guard-rationale>` prints one count *per file*, so `= 0` has no single value to compare (demonstrated this session). | Split into two single-value commands, with an aggregating alternative (`grep -hoE … \| wc -l`) offered explicitly. |
| SC-010 | Satisfy the negative with a grep that matches nothing. | Positive twin: the identical pattern against the inventory must return **53**. |
| SC-011 | Write "CPU-contention repro: out of scope." | All three reasons must be present, enumerated in C-005. |
| SC-011 | **[R2] Do nothing at all.** Measured against the spec **as committed, before any work**: `3 / 3 / 5` — already green. It grades the spec's prose, not the implementation, so no implementation can fail it. | **Demoted out of the criterion count** to an authoring self-check. Conversion into a delivery criterion was considered and rejected: every candidate form still grades prose, which is the defect. FR-009's substance is unaffected. |
| SC-012 | Add `# noqa` to silence ruff. | Diff-level count of added `# noqa` / `# type: ignore` must be 0 (NFR-006). |
| SC-012 | **[R2] Add a `per-file-ignores` entry or widen `exclude`** — `ruff check .` clean, zero added inline suppressions, and exactly what `CLAUDE.md` prohibits. Both `ruff.toml` and `pyproject.toml` already carry a `per-file-ignores` block, so an existence check proves nothing. | `git diff 98198e980 -- ruff.toml pyproject.toml` reported **as diff text**, showing no added entry and no widened `exclude`. |
| SC-013 | Harden the sleep assertion and leave `mock_randbelow.call_count == 3` two lines below it. | Moot under R-1 — the alias leaves `:787`'s assertion text correct — but only once `:499` is retargeted (FR-012), and the census must still *derive* the disposition (see next row). |
| SC-013 | **[R2] Print the string `hardened`.** R1's criterion is a **self-reported string**; nothing measured `:787` (no `secrets.randbelow` probe existed) and nothing resolved `filed:#<issue>`. | Restated as five measured sub-criteria: the census **derives** `correct-by-alias` rather than printing it; the **ADR exists**; `_poll_jitter_multiplier` is `0` or `≥ 2` occurrences (exactly `1` — today's state — fails); the false docstring at `test_saas_client.py:55-57` is gone; and any surviving `filed:#<issue>` is resolved by `gh issue view <n>` containing the node-id and mechanism. |
| SC-013 | **[R3] sub-4 is green on the base tree, so it grades nothing.** R2 pinned `grep -c 'is the assertion' → 0` and asserted "it is `1` today". Measured: **0** today, and **0** at `98198e980` — the docstring reads `*is*` with RST emphasis. A criterion already satisfied before any work began is satisfied by doing nothing. **This is the third time in this programme docstring prose became a load-bearing constraint — and the first time it happened *inside the criterion written to stop it*.** | Re-anchored on `grep -cE 'is\*? the assertion'` → **verified `1` at HEAD and `1` at `98198e980`**, required `0` post-fix. The positive twin (`side_effect stimulus`) verified **0** pre-fix, so it genuinely moves. Authoring rule added: run every grep against both trees before pinning its value, and tolerate RST markup. |
| SC-013 | **[R3] sub-1's derivation is unsatisfiable in both tree states.** R2 required "resolving each patch target's penultimate segment and asserting it is **not** a `ModuleType`". For `patch("…saas_client._randbelow")` the penultimate segment **is** `saas_client` — a module. It is false post-fix, and equally false pre-fix (penultimate `secrets`, also a module). It is the same 97.7%-over-broad formulation this spec corrected for R-2, re-imported into a different criterion. | Restated on the **narrowed own-module-vs-reach-through** discriminator already used everywhere else in the census: assert the resolved module's `__name__` **equals** the dotted module path. Own-module → `correct-by-alias`; `__name__` ≠ path → reach-through → corruptible. This distinguishes the two states, which the criterion requires. |
| SC-014 | **[R2]** Measure the NFR-005 delta across two different interpreters, or not at all — R1 gave NFR-005 no criterion. | SC-014 requires both arms on the same sanctioned interpreter, prints `python -V` per arm, and requires them identical. |
| SC-014 | **[R3] Run the measurement with the R2 command and uninstall the runner.** Every SC command in R2 was `uv run --python 3.12 python -m pytest …`, which removes `pytest` (70 packages) and then fails — so no timing arm could ever be taken, and the natural workaround is the foreign `~/.local/bin/pytest` on a different tree. | Every command rewritten to a sanctioned form (`./.venv/bin/python -m …`, or `uv run --python 3.12 --extra test --extra lint python -m …`). `### Environment` carries the `uv sync --dry-run` proof and the recovery command, so no WP re-discovers it. |
| SC-015 | **[R2] Hardcode `<census>`'s output table.** R1 described the control fixture in Verification Provenance and commanded it nowhere, while `<census>` is the sole instrument for SC-001, SC-002 and SC-013. | The control fixture is a **committed test** with ground truth pinned in-test, extended with the two forms R1's census could not see, plus a census self-mutation arm. |
| SC-016 | **[R2] Change `saas_client.py` freely** — R1's C-004 rested on a `git checkout --` revert, which a clean revert satisfies even if a different line shipped changed; and under R-1 its implied `git diff … empty` check is false by construction. | SC-016 enumerates the **permitted hunks** and fails on any other changed line, with SC-003 Arms 1–4 as the behaviour-side twin. C-002, C-008 and C-010 get one command each — R1 left all four unenforced, two of them High. |
| **All** | **[R2] Satisfy every criterion on a run where no intruder appears — which is most runs, at *any* breadth.** R1's answer was "every arm is an injection or a full-shard composition"; the full-shard half of that answer is now known to be worthless, since a clean full shard is the pre-fix outcome 39% of the time. | Every surviving acceptance arm is an **injection** (SC-003/004/005), a **static** measurement (SC-001/002/007/008/010/012/013/015/016), or a **repetition-counted determinism** arm (SC-009). The one probabilistic criterion (SC-006) is retired rather than weakened. Additionally, under R-1 the guard is **red on `98198e980`** for a structural reason (the alias does not exist there), which is the charter's red-on-base arm and cannot be satisfied by a lucky run. |
| **All** | **[R2-open]** Ship the alias, satisfy every static criterion, and have the fix be wrong in a way no arm reaches — e.g. `_poll_operation` routed through `_sleep` but `_request_with_retry` still calling `time.sleep` on a path no census node exercises. | **Not fully closed.** SC-007 arm 4 (0 direct calls in `saas_client.py`, AST-checked) is the closest instrument and it covers this specific case; a call added to a *different* module in the same cone is not covered. Residual risk accepted: the gate's scope is `tests/sync/` for tests and `saas_client.py` for the seam, and widening the seam check to all of `src/specify_cli/` is left to a successor. Recorded rather than hidden. |

### Verification Provenance

Everything numeric in this spec came from a command run on `98198e980`. What was run, and what was
deliberately not.

**Code facts verified directly:**

- `src/specify_cli/tracker/saas_client.py:19` is a bare `import time`. Module-level names are only `_SESSION_EXPIRED_MESSAGE` (`:36`) and `_UNAUTHENTICATED_CATEGORY` (`:39`); the backoff lives in locals `delay`/`cap`/`total_timeout` at `:478-480`. Two production sleep sites: `:439` (429 retry-after, exactly one call) and `:518` (poll backoff, one per iteration). Two clock reads: `:481`, `:484`. `import secrets` at `:18` is likewise bare; `secrets.randbelow` has exactly two callers in `src/`, both inside `saas_client.py` (`:106`, `:515`).
- **`_poll_jitter_multiplier` (`:104-106`) has zero callers** — `grep -rn '_poll_jitter_multiplier' src/ tests/` returns exactly one hit, the definition at `:104`. It returns `0.8 + (secrets.randbelow(4001) / 10000.0)` (max **1.2**) while the live inline jitter at `:515-516` is `secrets.randbelow(4000)` / `0.8 + (basis / 10000)` (max **1.1999**). A dead seam that has drifted from the live code. FR-010 condition (iii) resolves it.
- ~~`grep -rn "sleep\.side_effect\s*=" tests/sync/` → **0 hits**, so the predecessor's closure argument still holds.~~ **Retired as evidence.** The pattern matches attribute assignment only; the `side_effect=` **kwarg** form is invisible to it, and that is how `test_final_sync_diagnostics.py:303` feeds `:309`. The 0 hits is true of the pattern and false of the hazard. Re-closed by the mechanism-keyed predicate (R-2), which reads the `patch()` call's arguments.
- Both tracker census files carry `pytestmark = [pytest.mark.fast]` (`test_saas_client.py:24`, `test_saas_client_origin.py:22`), **and so do the two newly-found files** (`test_final_sync_diagnostics.py:27`, `test_git_metadata.py:28`), so all of them are inside CI's `-m "fast and not windows_ci"` selection. CI job: `fast-tests-sync`, `blacksmith-4vcpu-ubuntu-2404`, Python 3.12, `uv run python -m pytest`, `-n auto --dist loadfile`, `--timeout=240 --timeout-method=signal` (`.github/workflows/ci-quality.yml:1161-1172`).
- **CI's four `--ignore=` entries are selection-neutral under the marker expression**, verified this session so a successor does not re-derive it: `test_orphan_sweep.py:33` is `pytestmark = [pytest.mark.unit]`; `test_daemon_orphan_classification.py:45`, `test_daemon_cleanup_boundary.py:838` and `test_issue_1071_singleton_reconfirmation.py:51` are all `[pytest.mark.integration]`. None is `fast`, so `-m "fast and not windows_ci"` already excludes all four — which is why a local run without the `--ignore` flags selects the same set CI does. `ci-quality.yml:1155-1160` says the same in a comment.
- **`upstream/main` currently resolves to `98198e980`** (`git rev-parse upstream/main` = `98198e980045752a1f5ce0ba75796d3e5dddadf1`). That is a coincidence of timing, not a guarantee: every criterion pins the **SHA**. R1 used `upstream/main` in SC-008, SC-012 and NFR-004/006; all are now SHA-pinned.
- **`_PINNED_LEAKS` holds 12 entries.** `tests/sync/_leak_guard.py:333` is `_PINNED_LEAKS: tuple[_PinnedLeak, ...] = (…)` with **12** `_PinnedLeak(...)` elements (AST-measured: `ast.AnnAssign` → `ast.Tuple` → 12 `ast.Call` nodes to `_PinnedLeak`; `grep -c '_PinnedLeak('` agrees at 12). The token `_PINNED_LEAKS` itself appears only at `:333` and `:424` (the derived `_PINNED_LEAKS_BY_NODE_ID` dict), which is why R1's SC-008 grep was inert. **This 12 contradicts `C-003`'s "11 confirmed leaks"** and the WP must reconcile it.
- **The `#3115 FR-007` leak-guard coverage line is serial-only.** `tests/sync/conftest.py:483-492` prints `"[FR-007 leak guard] inspected {N} test(s) IN THIS PROCESS … xdist is active"` under an xdist controller and `:494` prints `"[FR-007 leak guard] inspected {N} test(s) under tests/sync/."` serially. `conftest.py:467-468` documents a real `-n 4 --dist loadfile` run over 2122 tests printing `inspected 0 test(s)`. SC-008's positive twin therefore pins `-n0`.
- **The `301.0` "assertion" does not exist.** `test_saas_client.py:804` is `mock_monotonic.side_effect = [0.0, 301.0]` — a stimulus. The only assertion in `test_timeout_after_5_minutes` is the `pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes")` at `:806`. The false claim originates in `_advancing_clock`'s docstring at `:55-57`. Opened and read, not inferred from a line number.
- `docs/development/process-global-inventory-3115.md` carries **53** `E`-numbered rows (`grep -cE '^\| E[0-9]+ \|'` = 53), matching the "53 verdicts" figure in issue comment 1, and carries **no** unverified stamp today (`grep -c unverified` = 0).

**The census, and its control.** The census is AST-based (`ast.parse`, decorator inspection, one level
of alias resolution through `sleep_calls = mock.call_args_list` and
`delays = [c.args[0] for c in sleep_calls]`). A naive text search over-counts, with the **commands
actually run** this session:

| Claim | Command | Result |
|---|---|---|
| naive `time.sleep` over-count | `grep -c 'time\.sleep' tests/sync/tracker/test_saas_client.py` | **28** against **13** real patch sites in that file |
| 15 grep hits vs 14 real decorators | `grep -rc 'patch("specify_cli.tracker.saas_client\.time\.sleep")' tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py` | **14 + 1 = 15** hits; **14** real decorators — the extra is `test_saas_client.py:559`, inside the docstring spanning `:513-762` |

**R1's quoted provenance command was wrong and is replaced.** R1 wrote
`grep -c 'patch("specify_cli.tracker.saas_client\.'` for the 15-vs-14 pair; that command returns
**68** (verified), because it matches every `saas_client.*` patch target, not just `time.sleep`. The
correct command is the one tabulated above. This matters because the checklist asserts every count
traces to a command run in the session — a number with the wrong command attached is indistinguishable
from an invented one.

Two of the four `assert_called_once_with` / `len(sleep_calls)` lines a naive grep reports
(`test_saas_client.py:532`, `:550`) are quoted CI failure text inside
`test_exponential_backoff_intervals`'s docstring — **confirmed inside the span `:513-762`** by opening
`:513` (the opening `"""`) and `:762` (the closing `"""`), not assumed. Nine `monotonic.side_effect`
lines are real out of ten grep hits (`:35` is docstring prose).

The probe was controlled against a fixture with a hand-counted ground truth: 3 sleep-patched test
functions, 1 monotonic-only function that must **not** count, 2 corruptible assertions, 1
delay-sequence assertion, plus three decoys (a docstring quoting
`mock_sleep.assert_called_once_with(9.9)`, a comment `# mock_sleep.call_count == 42`, and a string
literal `'specify_cli.tracker.saas_client.time.sleep'`). The probe reported exactly 3 / 2 / 1 and
ignored all three decoys; naive `grep -c 'time\.sleep'` on the same fixture returned 6 against a
ground truth of 3.

**That control is not sufficient, and SC-015 makes it a committed test.** Two gaps: it was described
here and commanded nowhere, so a hardcoded output table satisfied SC-001, SC-002 and SC-013; and its
positive cases were all decorator-shaped, which is exactly why the census missed the nine
context-manager / `side_effect=`-kwarg instances under `tests/sync/`. SC-015 requires the fixture
committed as a test with the ground truth pinned in-test, extended with both previously-invisible
forms, plus a census self-mutation arm.

Second, independent control: `pytest --collect-only -q` on the two census files (**73 tests
collected**) confirms all four census node-ids exist with the class names this spec cites —
`TestPolling::test_exponential_backoff_intervals`, `TestRetryBehaviors::test_429_respects_retry_after`,
`TestRetryBehaviors::test_429_defaults_to_5s_when_missing`,
`TestSearchIssues::test_429_retries_then_raises`. Pytest's own collector and the AST walker agree.

**The census result on `98198e980`:**

| # | `file:line` | Node | Assertion | Kind |
|---|---|---|---|---|
| 1 | `tests/sync/tracker/test_saas_client.py:784` | `TestPolling::test_exponential_backoff_intervals` | `assert len(sleep_calls) == 3` | call-count |
| 2 | `tests/sync/tracker/test_saas_client.py:786` | same node | `assert delays == [0.9, 2.0, 4.4]` | delay-sequence, **also count-dependent** |
| 3 | `tests/sync/tracker/test_saas_client.py:937` | `TestRetryBehaviors::test_429_respects_retry_after` | `mock_sleep.assert_called_once_with(3.0)` | call-count + value |
| 4 | `tests/sync/tracker/test_saas_client.py:957` | `TestRetryBehaviors::test_429_defaults_to_5s_when_missing` | `mock_sleep.assert_called_once_with(5.0)` | call-count + value |
| 5 | `tests/sync/tracker/test_saas_client_origin.py:261` | `TestSearchIssues::test_429_retries_then_raises` | `mock_sleep.assert_called_once_with(2.0)` | call-count + value |

Sibling couplings (same mechanism, different attribute — both **`correct-by-alias` under R-1**, both
originally FR-006 / FR-007, both now folded into FR-010):

| `file:line` | Assertion / binding | Mechanism | Under R-1 |
|---|---|---|---|
| `tests/sync/tracker/test_saas_client.py:787` | `assert mock_randbelow.call_count == 3` | bare `import secrets` at `saas_client.py:18`; 3-element `side_effect` | assertion text unchanged once `_randbelow` is module-local; **decorator target retargeted at `:499`** (FR-012) |
| `tests/sync/tracker/test_saas_client.py:804` | `mock_monotonic.side_effect = [0.0, 301.0]` — a **stimulus**, not an assertion (`:806` carries the only assertion) | bare `import time`; a concurrent `time.monotonic()` consumes an element → `StopIteration` | stimulus text unchanged once `_monotonic` is module-local; **decorator target retargeted at `:810`** (FR-012) |

Totals for the `time.sleep`-on-`saas_client` slice: **22** files scanned, **14** `*.time.sleep` patch
decorators (13 in `test_saas_client.py`, 1 at `test_saas_client_origin.py:229`), all resolving to the
single target `specify_cli.tracker.saas_client.time.sleep`; **10** of the 14 never read the mock
(neutralisation-only — not in the class); **4** nodes bear assertions; **5** corruptible assertions.

~~Running the same census over all of `tests/sync/` returns the **same 4 nodes and 5 assertions** — the
class is confined to `tests/sync/tracker/`.~~ **Struck.** That was a statement about R1's census, not
about the tree: the census inspected decorators only and could not match a `side_effect=` kwarg, so
nine further instances were invisible to it. They are enumerated in `### The class is not confined to
tests/sync/tracker/` and every one was opened and read. **A cited line number is not evidence that the
line asserts anything.**

**Not run, deliberately:** no `tests/sync` or `tests/cli` suite execution — a sibling mission may hold
that window (C-001), and in any case this environment has no `pytest` (see `### Environment`). Only
static analysis, AST measurement and one `--collect-only` pass (which imports modules but executes no
test body) were performed. SC-003, SC-004, SC-005, SC-009 and SC-014 are therefore acceptance arms for
the implementing work packages, not results reported here.

## Out of scope — explicitly

Recorded with reasoning so a successor does not re-derive them.

- **A live CPU-contention reproduction on a 4-vCPU profile.** Three reasons, per C-005: the producer is already named (`subprocess.Popen._wait`'s capped doubling loop); a contention reproduction cannot name a producer, only make an existing one likelier to be caught; and for a narrow-window race a local pass is the default outcome, so a negative result is uninformative by construction. The predecessor's own probe supplies the evidence for leaving it — its first attempt missed because the thread had not entered its wait loop when the sub-millisecond test body ran.
- **A full-shard composition acceptance arm of any kind (was SC-006).** Retired, not merely descoped: pristine `main` reddens on this class in 11 of 18 consecutive `fast-tests-sync` jobs including at `98198e980`, so a clean full shard is the **pre-fix outcome 39% of the time** and cannot discriminate. Rebuilding it as repeated parallel runs was considered and rejected — the 61% rate is CI-topology-specific, `C-001` forbids running `tests/sync` in this window, and this environment has no `pytest`. The mission rests on the injection guard, the mechanism gate, and the base-branch red instead. Reasoning recorded in full in the SC-006 entry.
- **Fixing `#3130`'s process-global / live-thread leaks**, and `#3193`'s leak-guard attribution race. Their teardown `ERROR`s travel with these reds in the same shard and may remain (C-003). *(Their count is `11` per C-003 and `12` per the registry — reconciled by SC-008, not by this mission's scope.)*
- **Re-deriving `docs/development/process-global-inventory-3115.md`'s 53 verdicts.** Only the rows this fix's correctness actually depends on are re-derived (FR-008); the rest are stamped unverified and left.
- **Establishing whether fixing `#3130` eliminates the intruder population.** `#3136` records this as not established. It is orthogonal: the counter is process-global by construction, so any future thread reintroduces the failure regardless.
- **Any change to production retry *behaviour*** in `saas_client.py` — delay values, call cardinality, raise conditions — and any change to CI shard composition (C-004 as restated, C-008). The FR-010 alias seam and the `_poll_jitter_multiplier` resolution are **in** scope and are the only permitted changes to that file.
- **Widening the R-1 seam check beyond `saas_client.py`**, and widening the gate beyond `tests/sync/` (notably to `tests/cli`, which `C-001` forbids this mission from running). Recorded as the one acknowledged residual in the adversarial table's final row.
- **Identifying *which* thread polluted any specific historical CI run.** The lever is the assertion class, not the intruder.

## Corrections to the incoming brief

Recorded so the plan does not inherit them. Items 1, 3 and 4 are from the original brief; items 2 and 5
record where **this spec's own R1** was wrong, since R1 is now itself an incoming artifact.

1. **The delay-vs-count distinction does not partition the census cleanly.** The brief asks to
   distinguish call-count assertions from delay-value assertions "because the delay sequence IS the
   backoff contract". Correct as intent, but there is **no purely delay-valued assertion in the
   tree**: the only one (`test_saas_client.py:786`, `delays == [0.9, 2.0, 4.4]`) is a whole-list
   equality built from the *unfiltered* recorder, so an extra call from another thread lengthens
   `delays` and breaks the equality too — verified by simulation: one extra call yields
   `delays=[0.9, 2.0, 4.4, 0.001]`. All 5 assertions are corruptible. FR-002 therefore preserves
   the contract's *values and cardinalities*, not its current expression — **and now measures both**,
   because a form that preserves values while dropping cardinality (`assert 3.0 in [...]`) satisfied
   every R1 criterion.
2. **R1's "deterministic, non-contention reproduction" is withdrawn.** R1 read issue comment 2 as
   establishing a **composition** dependence: the class reddens on PR #3209's shard while the nodes
   pass narrow, and pristine main is green in the full shard (`2116 passed, 11 skipped, 271
   deselected`, `EXIT=0`). **The second half is false.** Pristine main reddens on this class in 11 of
   18 consecutive jobs, including at `98198e980` with `2113 + 3 = 2116` — *the same selection*. And the
   failure is nondeterministic at a fixed commit (three of six same-SHA pairs disagree; `bb2020fea9`
   produced different victim sets with different magnitudes on identical commits). The correct framing
   is **topology-and-timing dependent with composition as a probability modifier**. This does not
   disturb operator decision 2 (the contention repro stays a non-goal, C-005), but it removes the
   acceptance arm R1 built on it (SC-006) rather than strengthening it. Full derivation:
   `### The defect is topology-and-timing dependent`.
3. **The brief's line list is patch sites, not assertions.** `:385, :412, :467, :502, :789, :809, :899, …`
   enumerates `@patch` decorators; 10 of the 14 carry no assertion on the mock at all. The answer to
   "how many distinct assertions are keyed on a process-global sleep counter" is **5, across 4 nodes**
   for the `saas_client` `time.sleep` slice — **plus 9 more under `tests/sync/` on `subprocess.run`,
   `time.sleep` in `sync/batch.py`, and `time.time` in `sync/git_metadata.py`.**
4. **Two sibling couplings sit inside the census nodes** and are not in the brief: the
   `secrets.randbelow` count assertion two lines below the backoff node's sleep assertion
   (`:787`), and the last exact-list `time.monotonic` **stimulus** (`:804`). R1 folded them in as
   FR-006 / FR-007 / SC-013. **Under R-1 both retire as work items** — a module-local alias leaves each
   *text* correct, though both decorators retarget under FR-012 — and their substance moves to FR-010.
   R1's claim that the `:804` fix was
   *blocked* because `301.0` "IS its assertion" was **false**; the only assertion is the
   `pytest.raises` at `:806`, and `itertools.chain([0.0], itertools.repeat(301.0))` preserves both the
   stimulus and the raise.
5. **R1 prescribed no seam, and that is now a deliberate exception.** R1's checklist recorded
   CHK026 ("the spec says WHAT and WHY; no code seam is prescribed") as passing, and it did. **R-1
   overrides it**: the operator has ruled the product-side module-local alias, so this spec names
   `_sleep` / `_monotonic` / `_randbelow`, their call sites, the ADR, and the
   `_poll_jitter_multiplier` resolution. This is an operator ruling recorded as such, not scope creep,
   and it is bounded — FR-010 names the seam and nothing else about the implementation. The reason a
   seam has to be named at spec level is that its three conditions (ADR, gate arm, dead-seam
   resolution) are what stop it becoming the next `_poll_jitter_multiplier`, and none of those is a
   plan-level choice.
6. **Docstring prose was treated as a load-bearing constraint, for the third time in this programme.**
   `test_saas_client.py:55-57` (`_advancing_clock`'s own docstring) says of `[0.0, 301.0]`: *"there the
   second value **is** the assertion"*. That sentence, not any assertion, is what blocked FR-007 in R1
   and what reached the operator briefing. The same failure mode produced
   `tests/integration/test_coord_loop_workspace.py:611` in the sibling mission. **The rule this
   programme now applies: a cited line number is not evidence that the line asserts anything — open
   the file.** The docstring is corrected under FR-010, measured by SC-013 sub-criterion 4.

## Unverified

- `[UNVERIFIED]` **The exact `AttributeError` text the guard raises on `98198e980`.** The *fact* of the
  base-branch red is structural — `saas_client._sleep` provably does not exist at that SHA — but this
  session ran no test bodies, so the message string is unverified. The implementing WP records it.
  See `### Charter red-on-base`.
- `[UNVERIFIED]` **The `selected == 2127` figure for a full `tests/sync` `fast` selection.** Its
  verifiable halves check out (`2127/2398` with `271 deselected`; `2116 + 11 = 2127`) and the four
  CI `--ignore=` entries are selection-neutral (verified), but no criterion in this revision depends on
  it now that SC-006 is retired. Retained for a successor, not relied on.
- `[UNVERIFIED]` **`28` as the smallest observed CI recorder total on a census node.** Sourced from the
  post-spec squad's CI-log survey (`analysis-report.md`, Arithmetic and provenance corrections). This
  session did not re-fetch the logs. NFR-001's floor of **100** does not depend on the exact value —
  it is above every observed inflation and 4× below the predecessor's measured 399 — but the `3.57×`
  ratio does.
- `[UNVERIFIED]` **The `11/18` (61%) pre-fix red rate and the `39%` clean-run rate.** Same source, same
  caveat: fetched from CI logs by the squad, not reproduced here. They are load-bearing for SC-006's
  *retirement* (a decision to remove a criterion, which fails safe) and for the non-gating observation,
  and for nothing that gates the mission.
- `[UNVERIFIED]` **The exact pre-fix `corruptible_assertions` count that `<census>` will report**, since
  `<census>` does not exist yet. The number `5` for the `saas_client` `time.sleep` slice is this spec's
  own AST measurement; the committed census must reproduce it on `98198e980` before it is trusted as
  SC-001's baseline. The **9** further `tests/sync/` instances were each opened and read this session,
  so they are verified as *instances* but not as a census *total* — the committed census's own total
  over `tests/sync/` is unverified.
- `[UNVERIFIED]` **Whether any live thread in the `fast-tests-sync` shard calls `secrets.randbelow`.**
  Only two callers exist in `src/`, both inside `saas_client.py`, so the realistic producer population
  is a leaked thread doing tracker polling. Not measured (would require a shard run — C-001). Now moot
  as a *scoping* question: under R-1 `:787` is correct-by-alias whether or not a producer exists.
- `[NEEDS RATIFICATION]` **`files_scanned` — `141` (`tests/sync/`) or `22` (`tests/sync/tracker/`).**
  Both re-measured this session. Bundled with the `sleep_patch_sites` restatement (SC-001) as **one**
  operator decision, because both are R2 denominators that the mandated scan cannot produce. Not
  `[UNVERIFIED]` — the numbers are certain; which one the criterion pins is a decision, not a
  measurement.
- `[UNVERIFIED]` **The post-fix line numbers of the 24 retargeted decorators.** The pre-fix lines are
  enumerated in `### The 24 patch-target retargets` and were each derived this session. Retargeting is
  in-place and length-preserving per line, so the test-file line numbers should not move — but adding
  three module-scope definitions to `saas_client.py` shifts every later line **there**, which is what
  SC-007 arm 4d's five call-site lines refer to. The implementing WP supplies both sets.
- `[UNVERIFIED]` **The exact `check_patch_targets.py` CI failure output** for the three alias targets
  during the red window. The *resolver's* verdict was reproduced directly this session (`no attribute
  '_sleep' in 'specify_cli.tracker.saas_client'`), but the script's own aggregate report and exit code
  were not — that would scan all of `tests/`, and no test bodies were run under C-001.

## Open questions

**All three R1 markers are settled by the operator's rulings.** They are recorded here with their
resolutions rather than deleted, so a successor can see that they were decided and on what basis.
**Zero open clarification markers remain**: all three appear struck (`~~…~~`) with a recorded
resolution, and the bracketed marker form appears nowhere in this file — deliberately not stated as a
grep, because any command quoting the marker string matches its own quotation and reports a false
positive. The three operator decisions carried in the original
brief (the lever is the assertion class; the contention reproduction is a non-goal; the inventory's
verdict column is unverified) remain settled and are not re-opened.

1. **~~Should FR-005's gate cover all of `tests/` rather than only `tests/sync/tracker/`?~~**
   **Settled by R-2**: widen the **predicate** to the mechanism, keep the **enforced scope** at
   `tests/sync/` — which contains the newly-found instances — and **not** `tests/cli`, which `C-001`
   forbids this mission from even running. The middle position R1 could not find is that breadth of
   *predicate* and breadth of *enforcement* are separate decisions.
2. **~~Is hardening `test_saas_client.py:804`'s exact-list `time.monotonic` in scope, or filed upstream?~~**
   **Moot under R-1** — a module-local `_monotonic` leaves its stimulus text correct, once the decorator
   at `:810` is retargeted (FR-012). The marker also carried
   a **false blocker** (`301.0` "IS its assertion"), which is struck: `:804` is a `side_effect`
   stimulus and `:806` carries the only assertion. Deferring on a non-existent blocker would not have
   been a legitimate operator decision. The docstring that produced the false claim is corrected under
   FR-010.
3. **~~If PR #3209's branch is rebased or closed before SC-006 Arm B runs, is a synthetic composition acceptable?~~**
   **Moot** — SC-006 is retired, so no arm depends on that branch. Where PR #3209 is referenced at all,
   its head SHA `5e98c2bb7` is pinned rather than its branch name, because the branch moved twice
   during this mission.
