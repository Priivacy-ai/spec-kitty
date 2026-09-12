# Environment transcript and NFR-005 baseline arm — Mission `sync-sleep-count-3136-01KZ9B5A`

**Produced by**: WP01 (T001, T003), agent `claude` / profile `python-pedro`
**Checkout**: `/home/jeroennouws/dev/sk-missions/3136`, branch `feat/sync-sleep-count-3136`
**HEAD at capture**: `91255f6daed06e7a6fdc32c8f9c094af2e427235`
**Captured**: 2026-08-06T22:44:42Z (UTC)

This file is the mission's single toolchain-resolution record. Every later WP cites it instead of
re-deriving it (`plan.md:172-177` — *"The first WP re-asserts the environment and records `command -v
python pytest ruff mypy` plus the four `--version` lines before any acceptance arm runs"*).

---

## T001 — Pinned toolchain

### PATH preparation

```bash
cd /home/jeroennouws/dev/sk-missions/3136
export PATH="$PWD/.venv/bin:$PATH"
```

### `command -v` — verbatim, all five tools

```
$ date -u "+%Y-%m-%dT%H:%M:%SZ"
2026-08-06T22:44:42Z

$ command -v python pytest ruff mypy spec-kitty
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/pytest
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/mypy
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/spec-kitty
```

All **five** resolve under `/home/jeroennouws/dev/sk-missions/3136/.venv/bin`, `spec-kitty` included.
The WP prompt allowed `spec-kitty` to resolve elsewhere provided the path was named; with the prepend
in place it does **not** resolve elsewhere, so there is nothing to exempt.

### `--version` — verbatim, five lines

```
$ python -V
Python 3.12.13

$ pytest --version
pytest 9.0.3

$ ruff --version
ruff 0.15.12

$ mypy --version
mypy 1.20.2 (compiled: yes)

$ uv --version
uv 0.10.12 (x86_64-unknown-linux-gnu)
```

All four gate values match the expected set exactly: `3.12.13` / `9.0.3` / `0.15.12` / `1.20.2`.
**The venv was not disturbed at any point during WP01, and no recovery was needed.** No `uv sync` and
no `uv` subcommand other than `uv --version` was executed by this WP.

### R2 (PATH shadowing) — confirmed live, with a control

The hazard is not historical. Measured this session, on the **unmodified** inherited `PATH`
(i.e. before the prepend above):

```
$ command -v pytest ruff mypy spec-kitty python      # inherited PATH, no prepend
/home/jeroennouws/.local/bin/pytest
/home/jeroennouws/.local/bin/ruff
/home/jeroennouws/.local/bin/mypy
/home/jeroennouws/.local/bin/spec-kitty
/usr/bin/python
```

All four of `pytest` / `ruff` / `mypy` / `spec-kitty` resolve to `~/.local/bin`, an **unrelated
checkout**, and `python` resolves to the ambient `/usr/bin/python`. This is the control that makes the
prepended transcript above meaningful: the two resolutions differ, so the prepend is doing work.

---

## The two sanctioned command forms — copied in full so no later WP has to go and find them

Reproduced verbatim from `plan.md:163-170` and `spec.md:420-431`, so that no successor WP needs to
open either file to obtain them.

```bash
# Form 1 (preferred) — direct, no resolver involvement. Valid inside a provisioned tree.
./.venv/bin/python -m pytest …
./.venv/bin/ruff check .

# Form 2 — uv-driven, extras pinned so the toolchain survives the resolve.
uv run --python 3.12 --extra test --extra lint python -m …

# Provisioning / recovery (only if the venv has been destroyed), after which Form 1 is valid again:
uv sync --python 3.12 --extra test --extra lint
```

### Why the bare form is a defect and not a style preference

`pytest` / `ruff` / `mypy` live **only** in `[project.optional-dependencies]`; `[dependency-groups]
dev` carries type stubs only; there is no `[tool.uv]` block. A `uv` invocation **without** the extras
therefore resolves the default dependency set and uninstalls the whole toolchain — and, because a bare
invocation honours the tracked `.python-version` (`3.11.15`), it **also** silently downgrades the
interpreter two minor versions away from CI. This has been observed **three times** in this mission,
the third time immediately after the warning was committed.

WP01 did **not** re-run the `uv sync --dry-run` proof: it is already recorded at `plan.md:136-149` and
`spec.md:396-419`, and re-running any `uv` subcommand only re-exposes the tree to the hazard for no new
information. The proof is cited, not repeated.

---

## The `.python-version` divergence — recorded, and deliberately not fixed

```
$ cat .python-version
3.11.15
```

The tracked pin reads **`3.11.15`** while the venv is **3.12.13** and CI's `fast-tests-sync` job pins
**3.12**. **This divergence is recorded and deliberately not fixed by this mission.** Changing a
tracked interpreter pin is a repo-wide decision outside this mission's permitted change set
(`plan.md:126` — *"`.python-version` | `3.11.15` | **diverges from venv and CI** — record, do not fix
(outside C-004)"*; IC-01 risk (c) at `plan.md:574-576`). It is also precisely *why* an accidental bare
`uv run` **downgrades** the interpreter rather than merely stripping the toolchain.

### Invariance proof for the two owned files

```
$ git status --porcelain -- .python-version uv.lock
                                       # (no output)

$ git diff --stat -- .python-version uv.lock
                                       # (no output)
```

**Positive twin from the same invocation** — a silent `git diff` is only evidence when a loud sibling
diff proves the command is wired up (`spec.md:932-936`):

**PRE-EDIT** — measured at T001, before WP01 committed either note file:

```
$ git diff --stat 98198e980 -- kitty-specs/ | tail -3
 .../tasks/WP07-transcripts-pr-and-filings.md       |  651 ++++++++++
 .../sync-sleep-count-3136-01KZ9B5A/wps.yaml        |  855 +++++++++++++
 19 files changed, 9020 insertions(+)
```

**POST-EDIT** — re-measured against the **committed** state, in the same invocation as the three
silent diffs below. The numbers moved because WP01 added its own note files; both readings are
recorded rather than the stale one being left to look current:

```
$ git status --porcelain -- .python-version uv.lock
                                       # (no output)
$ git diff --stat -- .python-version uv.lock
                                       # (no output)
$ git diff --stat 98198e980 -- .python-version uv.lock
                                       # (no output)  ← also silent against the diff base
$ git diff --stat 98198e980 HEAD -- kitty-specs/ | tail -2
 .../sync-sleep-count-3136-01KZ9B5A/wps.yaml        |  855 +++++++++++++
 22 files changed, 10314 insertions(+)
```

The twin is **loud** in both readings (19 files / 9020 insertions pre-edit; 22 files / 10314
insertions post-edit) from the same shell invocation as the silent diffs. `.python-version` and
`uv.lock` are therefore genuinely unmodified — silent against the working tree **and** against
`98198e980`.

> **⚠️ CORRECTED (WP01 remediation, cycle 3) — this POST-EDIT reading is itself self-measuring, and it
> had gone stale.** It previously read `21 files changed, 9671 insertions(+)`. That figure was captured
> from the **working tree** part-way through the edit, before every note file was staged, and **no
> committed state of this branch has ever matched it** — `98198e980..332b45c0f` was already
> `22 files / 9924`. The reason is structural: `environment-3136.md` lives **inside** `kitty-specs/`,
> so this block counts lines that include its own. Every append to this file increments the insertion
> total, exactly as § *Definition-of-Done item 5* describes, one level of indirection out. Two things
> changed: the figures are re-measured against the committed tree, and the command is **pinned to
> `HEAD`** so it no longer silently reports a dirty worktree. **Anyone who appends to any file under
> `kitty-specs/` MUST re-run it and update both figures in the same commit.**

---

## Base-ref correction — `98198e980` is the mission's diff base, **not** `git merge-base HEAD main`

The WP01 prompt (T003 step 1) asserts *"`98198e980` is the mission's merge-base"*. **That description
is wrong and is recorded here as a prompt defect.** Re-derived this session:

```
$ git merge-base HEAD main
1aed89411b50203c8dbd9b284d70cc8fefbf32fa      # ← the actual merge base with main

$ git merge-base --is-ancestor 98198e980 HEAD  ; echo $?
0                                              # 98198e980 IS an ancestor of HEAD

$ git merge-base --is-ancestor 98198e980 main  ; echo $?
1                                              # but it is NOT on main

$ git merge-base --is-ancestor 1aed89411 98198e980 ; echo $?
0                                              # 98198e980 is a DESCENDANT of the real merge base

$ git rev-list --count 98198e980..HEAD
32
```

So `98198e980` sits **on the mission branch**, 32 commits behind `HEAD` and ahead of the true merge
base. It is the mission's **diff base / pre-mission baseline commit**, which is exactly what NFR-005,
SC-014, C-002, C-004, C-008 and NFR-006 all use it for. **The substance of every `git diff 98198e980`
command in this mission is unaffected**; only the word "merge-base" is wrong. The ref resolves
(`git cat-file -t 98198e980` → `commit`) and is an ancestor of `HEAD`, so all worktree and diff
operations keyed on it are valid.

Successor WPs: when a prompt says "the merge base", use `98198e980` for **mission-diff** purposes and
`1aed89411b50203c8dbd9b284d70cc8fefbf32fa` when you actually need the merge base with `main` (for
example, when attributing a red as pre-existing relative to `main`).

---

## T003 — NFR-005 baseline arm on `98198e980`

Taken **inside** the C-001 window acquired by T002 (see `notes/c001-window-3136.md`), with the
interpreter pinned by T001.

### Base tree materialisation

```
$ git worktree add --detach /tmp/wp01-base-98198e9 98198e980
Preparing worktree (detached HEAD 98198e980)
HEAD is now at 98198e980 test(landing): pin SPECIFY_REPO_ROOT in charter interview/generate tests lacking an early .kittify marker

$ git -C /tmp/wp01-base-98198e9 rev-parse HEAD
98198e980045752a1f5ce0ba75796d3e5dddadf1
```

A throwaway detached worktree, as required. The mission's coord worktree
(`/home/jeroennouws/dev/sk-missions/3136/.worktrees/sync-sleep-count-3136-01KZ9B5A-coord`) was **not**
used to run anything.

### R5 — the editable install is real, and the `PYTHONPATH` pin defeats it

R5 is **not** hypothetical in this tree. The venv carries an editable-install path file pointing at the
**mission head**:

```
$ cat .venv/lib/python3.12/site-packages/_editable_impl_spec_kitty_cli.pth
/home/jeroennouws/dev/sk-missions/3136/src
… (7 identical lines)

$ ./.venv/bin/python -c "import specify_cli; print(specify_cli.__file__)"      # UNPINNED
/home/jeroennouws/dev/sk-missions/3136/src/specify_cli/__init__.py             # ← the HEAD tree
```

An unpinned arm would therefore have silently measured the **head** tree. Because the `.pth` is a
plain path-entry file (site-packages append) rather than a meta-path finder, `PYTHONPATH` takes
precedence — verified, not assumed:

```
$ PYTHONPATH=/tmp/wp01-base-98198e9/src \
    /home/jeroennouws/dev/sk-missions/3136/.venv/bin/python -c \
    "import specify_cli, sys; print('RESOLVED:', specify_cli.__file__); print('PYVER:', sys.version)"
RESOLVED: /tmp/wp01-base-98198e9/src/specify_cli/__init__.py
PYVER: 3.12.13 (main, Mar 10 2026, 18:17:25) [Clang 21.1.4 ]
```

`specify_cli.__file__` sits under `/tmp/wp01-base-98198e9/src`. **The arm is valid.**

### The arm — one command, once

Run inside the C-001 window held since `2026-08-06T22:46:46Z`. Output **redirected**, never piped —
a pipe would replace pytest's exit status with the tail command's.

```bash
cd /tmp/wp01-base-98198e9

PYTHONPATH=/tmp/wp01-base-98198e9/src \
  /home/jeroennouws/dev/sk-missions/3136/.venv/bin/python -V

PYTHONPATH=/tmp/wp01-base-98198e9/src \
  /home/jeroennouws/dev/sk-missions/3136/.venv/bin/python -m pytest \
  tests/sync/tracker/ -m "fast and not windows_ci" -n0 -q -p no:cacheprovider \
  -ra --durations=10 > /tmp/wp01-base-arm.txt 2>&1
echo "EXIT=$?"
```

```
ARM-START 2026-08-06T22:49:28Z
Python 3.12.13
EXIT=0
ARM-END   2026-08-06T22:50:38Z
```

### Results — NFR-005 **base** arm

| Field | Value |
|---|---|
| **Ref** | `98198e980045752a1f5ce0ba75796d3e5dddadf1` (mission diff base) |
| **Resolved `python -V`** | **`Python 3.12.13`** — identical to T001's pinned interpreter |
| **`specify_cli.__file__`** | `/tmp/wp01-base-98198e9/src/specify_cli/__init__.py` (base tree — verified, see R5 above) |
| **Summary line (quoted verbatim)** | `461 passed, 11 deselected, 1 warning in 66.54s (0:01:06)` |
| **Selected count** | **461** selected (461 passed, 0 failed, 0 skipped, 0 xfailed); **11 deselected** by `-m "fast and not windows_ci"`; **472 collected — `[DERIVED]`, not quoted** (see note below) |
| **Wall clock (pytest-reported, the SC-014 figure)** | **66.54 s** |
| **Wall clock (outer envelope, incl. the separate `python -V` process)** | 70 s (`22:49:28Z` → `22:50:38Z`) |
| **Slowest individual test** | **`12.72s setup tests/sync/tracker/test_config.py::test_project_slug_roundtrip`** — well under the 60 s ceiling (4.7× headroom) |
| **`^ERROR tests/` count** | **0** |
| **`EXIT=`** | **0** |
| **Killed / timed out?** | **No.** The run completed and reported an exit status. |
| **`tests/cli` run?** | **No. `tests/cli` was not run at any point by WP01.** |

**Provenance of `472 collected` — it is derived, and the row above now says so.** Every other figure in
that table is lifted verbatim from the summary line or from `--durations=10`. `472` is **not**: the run
used `-q`, which **suppresses** pytest's `collected N items` line. `472` is `461 selected + 11
deselected`, which is arithmetically sound and is the right number — but it is a computation this note
performed, not a string pytest printed. It sits beside genuinely quoted figures, so it is labelled
`[DERIVED]` to keep the two classes distinguishable. Anyone wanting it quoted must re-run without
`-q`; WP01 did not, and does not re-run for this.

> **⚠️ CORRECTED (WP01 remediation, cycle 3) — the suppression claim said the line was "absent from
> **both** arm files", and only one arm was ever taken.** The claim is re-derivable for the base arm
> and is now scoped to it, with the path named:
>
> ```
> $ test -s /tmp/wp01-base-arm.txt && echo "NON-EMPTY: $(wc -l < /tmp/wp01-base-arm.txt) lines"
> NON-EMPTY: 39 lines
> $ grep -c 'collected' /tmp/wp01-base-arm.txt
> 0
> ```
>
> The reviewer's independent re-run of the same arm left a second file, `/tmp/renata-base-arm.txt`
> (39 lines, `grep -c 'collected'` → `0`) — observation 2 in the table further down — so the base arm
> is corroborated twice. **The other arm the word "both" implied is WP07's mission-ref run, which has
> not been taken; there is no file to check and never was.** Asserting absence from it claimed more
> than WP01 could see, and that half is withdrawn. Both paths are volatile `/tmp` scratch rather than
> committed artifacts, so they may already be gone: **WP07 MUST re-derive `collected` against its own
> arm file rather than inherit this result.**

**No pre-existing failures were encountered.** The base arm is fully green (461/461), so the charter's
*Pre-existing Failure Reporting Rule* has no trigger in WP01 — there is nothing to report and nothing
accepted as baseline red. (The governance conflict that rule creates with the operator's bar on
`gh issue create` is nonetheless recorded, latent, at `residual-ledger.md` RL-005.)

### `--durations=10`, verbatim

```
============================= slowest 10 durations =============================
12.72s setup    tests/sync/tracker/test_config.py::test_project_slug_roundtrip
1.88s call     tests/sync/tracker/test_saas_client_consent_gate_3030.py::test_every_production_construction_site_attributes_its_project
0.06s setup    tests/sync/tracker/test_saas_client_routing.py::TestStatusRouting::test_status_with_binding_ref
0.06s setup    tests/sync/tracker/test_local_service.py::TestSyncOperations::test_sync_run_delegates_to_connector
0.04s call     tests/sync/tracker/test_store.py::test_issue_persistence_across_instances
0.03s call     tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals
0.03s call     tests/sync/tracker/test_saas_client_consent_gate_3030.py::test_mission_creation_bind_transmits_for_a_consenting_project
0.02s call     tests/sync/tracker/test_saas_client.py::TestRun::test_run_202_polls_until_completed
0.02s call     tests/sync/tracker/test_saas_client.py::TestPolling::test_pending_then_running_then_completed
0.02s call     tests/sync/tracker/test_origin_integration.py::TestOfflineEventQueuing::test_event_queued_when_no_websocket
```

### BINDING instruction for WP07's comparison arm

The profile is extremely top-heavy. A single fixture setup (`test_project_slug_roundtrip`, 12.72 s) is
**19 %** of the whole 66.54 s, and the entire remaining top-10 sums to under 2.2 s. The NFR-005 budget
is **≤ 5.0 s** added wall clock.

**This is no longer a one-sample inference.** There are now two independent observations of the *same
tree*, and they disagree by most of the budget:

| # | Observer | Ref / tree | Summary wall clock | `test_project_slug_roundtrip` setup |
|---|---|---|---|---|
| 1 | WP01 (this note, base arm above) | `98198e980` | **66.54 s** | **12.72 s** |
| 2 | WP01 reviewer, independently | unchanged tree | **70.53 s** | **19.02 s** |

- Run-to-run spread on an **unchanged** tree: **70.53 − 66.54 = 3.99 s**.
- That is **79.8 % of the entire 5.0 s NFR-005 budget, consumed purely as noise.**
- The single fixture swung **19.02 − 12.72 = 6.30 s** — **larger than the whole budget on its own.**

A measurement whose noise floor is 80 % of the threshold it is being compared against cannot decide
that threshold from one sample per ref. Accordingly, the earlier advisory wording ("WP07 *should* take
repeated arms") is **superseded**. The following is **binding on WP07**:

1. **WP07 MUST take at least `n = 5` timed arms per ref** (≥ 5 on base, ≥ 5 on the mission ref),
   interleaved base/mission rather than run as two blocks, so drift in machine load does not land
   entirely on one side. Five is the minimum that makes a median meaningful against a spread already
   observed at 3.99 s; it is a floor, not a target.
2. **WP07 MUST report the distribution, not a point estimate.** For each ref: **all `n` raw summary
   wall clocks, plus median, min, max, and max−min spread.** A bare pair of numbers is not an
   acceptable NFR-005 result and MUST be rejected at review.
3. **WP07 MUST judge the delta on medians**, and MUST state the observed spread alongside it.
4. **The `[UNRESOLVABLE BY THIS INSTRUMENT]` band is DERIVED from WP07's own measurements — it is not
   a constant frozen here.** Let `S` be the larger of the two per-ref `max − min` spreads WP07 reports
   under item 2. A median delta is `[UNRESOLVABLE BY THIS INSTRUMENT]` **iff
   `|median_mission − median_base| ≤ S`.** Inside that band the result MUST NOT be reported as a pass
   and MUST NOT be reported as a fail — it is a statement that the instrument is too coarse for the
   question. Only a delta **strictly greater than `S`** may be called either way. `S` is the single
   acceptance test; nothing else governs.
   **`±4 s` is a prior expectation, not the test.** Its provenance is exactly the two observations in
   the table above — `70.53 − 66.54 = 3.99 s` on an unchanged tree, `n = 2` — and it is recorded so
   WP07 can see whether its own `S` lands in family. **If `S` and `±4 s` disagree, `S` wins**, because
   `S` comes from `n ≥ 5` on the refs actually under test while `±4 s` comes from two samples on one
   of them. WP07 MUST report the divergence when it occurs rather than silently picking a side. (This
   supersedes the earlier wording, which fixed an absolute `±4 s` band and then required the delta to
   be *"clearly outside the observed spread"* — two different acceptance tests in one MUST. An 8 s
   measured spread with a 5 s median delta satisfies one and fails the other, and WP07 was not told
   which governed. It is now `S`.)
5. If WP07 needs a verdict at finer resolution than `S`, it MUST first reduce the noise floor —
   pin or stub the `test_project_slug_roundtrip` fixture, or measure a subset excluding it — and MUST
   say so explicitly rather than reporting a tighter number from the same noisy instrument. Reducing
   the noise floor shrinks `S` on the next run; re-deriving `S` from the quieter instrument is the
   sanctioned route to a finer verdict, and asserting one without re-deriving `S` is not.

**Both observations above are cited, and neither is discarded.** Observation 2 is the reviewer's and
was taken on a tree identical to observation 1's; the disagreement is instrument noise, not a
regression, and it is the direct evidence for every "MUST" in this list.

### The `^ERROR tests/` probe, controlled against a known answer

A `0` from a grep is only evidence if the grep works. Control fixture with a **known** answer of
`3` for `^ERROR tests/` and `4` for the over-matching `^ERROR ` — the latter is why the WP prompt
requires the anchored form:

```
$ cat /tmp/wp01-grep-control.txt
ERROR tests/sync/tracker/test_alpha.py::test_one
ERROR tests/sync/tracker/test_beta.py::test_two
ERROR    some unrelated log line from a library
2026-01-01 ERROR tests/ not at line start
ERROR tests/cli/test_gamma.py::test_three

$ grep -c '^ERROR tests/' /tmp/wp01-grep-control.txt
3                                       # known answer 3 — probe correct
$ grep -c '^ERROR ' /tmp/wp01-grep-control.txt
4                                       # known answer 4 — over-matches, as documented
```

Applied to the real arm output, with a non-emptiness check and a same-file twin so a `0` cannot be a
missing-file artefact:

```
$ test -s /tmp/wp01-base-arm.txt && echo YES
YES
$ wc -l < /tmp/wp01-base-arm.txt
39
$ grep -c 'passed' /tmp/wp01-base-arm.txt
1                                       # twin >= 1: the file really is a pytest run
$ grep -c '^ERROR tests/' /tmp/wp01-base-arm.txt
0                                       # a real zero
```

On this particular run `^ERROR ` **also** returns `0`, so this arm does **not** by itself demonstrate
the difference between the two patterns — the control fixture above is what does. Stated rather than
glossed.

### Cleanup

```
$ git worktree remove /tmp/wp01-base-98198e9
$ git worktree list
```

Result recorded in the § *Worktree cleanup* block appended below.

## Worktree cleanup, and the venv re-verified after everything

```
$ git worktree remove /tmp/wp01-base-98198e9
                                       # exit 0

$ git worktree list
/home/jeroennouws/dev/sk-missions/3136                                                 912da814c [feat/sync-sleep-count-3136]
/home/jeroennouws/dev/sk-missions/3136/.worktrees/sync-sleep-count-3136-01KZ9B5A-coord ae29d54c5 [kitty/mission-sync-sleep-count-3136-01KZ9B5A]

$ ls -d /tmp/wp01-base-98198e9
ls: cannot access '/tmp/wp01-base-98198e9': No such file or directory
```

The throwaway base worktree is gone; only the mission checkout and the coord worktree remain.

**Venv re-verified after every command WP01 ran** (the discipline the R1 hazard demands — re-check
after *any* `uv` invocation, and WP01's only one was `uv --version`):

```
$ ./.venv/bin/python -V   →  Python 3.12.13
$ ./.venv/bin/pytest --version   →  pytest 9.0.3
$ ./.venv/bin/ruff --version   →  ruff 0.15.12
$ ./.venv/bin/mypy --version   →  mypy 1.20.2 (compiled: yes)
```

Unchanged from the T001 transcript. **The venv was never destroyed during WP01 and no recovery was
performed.** There is no cleaned-up transcript here to hide.

---

## Definition-of-Done item 5 — the `uv run` negative, with its positive twin, per file

The trap this closes: on an **absent** file `grep -c` prints no count and exits `2`, which a reader
scores as "0 hits — satisfied". So: `test -s`, a line count, and a same-file twin that must be `≥ 1`,
**before** the negative.

### `notes/environment-3136.md`

The four prescribed commands, reproducibly:

```
$ F=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md
$ test -s "$F" && echo "NON-EMPTY: $(wc -l < "$F") lines"
NON-EMPTY: 636 lines
$ grep -c 'command -v' "$F"      # twin, must be >= 1
7
$ grep -c 'uv run' "$F"          # the negative
12
```

> **⚠️ CORRECTED (WP01 remediation). The figures this block previously carried were stale, and the
> sentence asserting otherwise was false.** It reported `426 lines` and `grep -c 'uv run' → 6` under
> the claim *"These are the POST-EDIT counts, measured after this section was appended"* — but the
> counts were taken when the file stood at 426 lines, and roughly 42 further lines were appended
> **below** this block afterwards (the RL-003 discussion and the `c001-window` subsection). The block
> was never re-measured, so the claim was untrue of the committed artifact. The figures above are
> **re-measured against the final committed state of this file**, after every append this remediation
> makes. **The substantive conclusion did not change and was never in doubt — see the table below:
> there is still no bare form.** What was wrong was the evidence, not the answer.
>
> **The trap, stated so it is not re-sprung:** a block that measures the file it lives in is only true
> at the instant it is written. **Any** later append to this file — by WP05, WP07, or a reviewer —
> invalidates `636`, `7` and `12` again. Whoever appends **MUST** re-run the four
> commands above and update these numbers in the same commit. Do not trust these counts against a
> tree whose `wc -l` disagrees; re-run instead. **Cycle 3 is the second commit to re-run them** — the
> cycle-2 remediation's own appends moved every figure here, exactly as this paragraph predicts.

These counts are **inflated by this block's own self-description**: writing down "`grep -c 'uv run'`"
puts the token `uv run` into the file being grepped. The `12` above therefore counts **lines
mentioning the token — emphatically not 12 commands.** The classification below is the
load-bearing evidence.

Line-by-line, from a fresh `grep -n 'uv run\|uv sync' notes/environment-3136.md` against the same
final state — **`16` hits total** (`12` for `uv run`, `6` for `uv sync`, two lines
carrying both — `:535` and `:536`):

| Line | Kind | Carries the extras? |
|---|---|---|
| `:95` `uv run --python 3.12 --extra test --extra lint python -m …` | **the only actual `uv run` command form in this file** — sanctioned Form 2 | **Yes**, in full |
| `:98` `uv sync --python 3.12 --extra test --extra lint` | the only `uv sync` command form — recovery/provisioning, sanctioned | **Yes**, in full |
| `:61`, `:110`, `:128` | **prose** — warning about, or naming, the bare form | n/a — not commands |
| `:493`, `:509`, `:514`, `:530`, `:531`, `:535`, `:536`, `:541`, `:542`, `:564`, `:568` | **meta** (`11` lines) — this block and its neighbours quoting the tokens, reporting their own greps, or captioning the table | n/a — not commands |

**Every hit that is a command carries `--python 3.12 --extra test --extra lint`. There is no bare
form.** And **WP01 executed neither**: the only `uv` subcommand WP01 ran in this entire work package
was `uv --version`.

**Note on the reviewer check as literally written.** Reviewer Guidance item 2 says *"every hit must
carry `--python 3.12 --extra test --extra lint`"*. Taken literally that fails any document which
**warns** about the bare form — including WP01's own prompt, which contains bare-form prose at
`tasks/WP01-environment-and-window.md:83`, `:90`, `:157`, `:497`, `:510`. The rule's intent is clearly
"no bare **command**", and that is what is evidenced above. Recorded at `residual-ledger.md` RL-003.

### `notes/c001-window-3136.md`

```
== kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md
NON-EMPTY: 265 lines
grep -c 'command -v'  → 0     ← the prescribed twin CANNOT be satisfied on this file
grep -c 'PENDING'     → 3     (substitute twin, >= 1 ✓)
grep -c 'Released at' → 2     (discriminating twin — see the correction below)
grep -c 'uv run'      → 0     ← a REAL zero: the file is proven non-empty and proven to be
                                the window file by the twins above it
```

`0` `uv run` hits in the window file, and the file is proven present (`265` lines) and
proven to be the right file **before** that `0` is read. That is the whole point of the twin idiom.

> **⚠️ CORRECTED (WP01 remediation, cycle 3) — `PENDING` alone is a weaker twin than this note
> claimed, and the cycle-2 block that said so measured itself before it existed.** The substitute twin
> was justified as proving *file identity*. It does not, and did not: at the moment the note relied on
> `PENDING`, the token stood at **3** in `c001-window-3136.md` and **3** in `environment-3136.md`, so a
> `PENDING → 3` result was equally consistent with having grepped the wrong one of the two files. It
> proved **non-emptiness**, not **identity**. That much was right. What follows is what cycle 2 got
> wrong.
>
> ```
> $ for T in 'PENDING' 'Released at' 'ACQUIRE'; do
>     printf '%-14s c001=%s  env=%s\n' "$T" "$(grep -c "$T" …/c001-window-3136.md)" "$(grep -c "$T" …/environment-3136.md)"
>   done
> PENDING        c001=3  env=10     ← discriminates
> Released at    c001=2  env=8     ← discriminates
> ACQUIRE        c001=4  env=4     ← COLLIDES — does NOT discriminate
> ```
>
> **Read the `env` column as a warning, not as a result — and note that cycle 2 printed `3` / `0` / `0`
> there.** Those were the counts *before* this block was written; they were committed as though they
> described the file that contains them. They do not. Every `env` hit for all three tokens now sits in
> this correction block, in the transcript immediately above it, or in the closing prose below it
> — the block **discusses** the three tokens, so it **contains** them. Before cycle 2 authored it,
> `Released at` and `ACQUIRE` genuinely were `0` in this file. They are not now, and the cycle-2
> conclusion drawn from that — that they are **"absent from the toolchain transcript"** — is **false
> and is withdrawn.** So is the annotation cycle 2 put on the `PENDING` row, *"does NOT
> discriminate"*: `3` against `10` plainly does.
>
> **The three verdicts above have all moved since cycle 2, and two of them inverted.** That is not a
> quirk of this file; it is the finding. The test a discriminator must pass is that the two counts
> **differ** — *absence* was never the property, and cannot be, in a file that names the token in order
> to reason about it. Against cycle 2's `env=3` / `env=0` / `env=0`:
>
> - **`PENDING`** was useless when it was chosen (`3` vs `3`) and discriminates now (`3` vs `10`)
>   **only because the correction machinery kept writing the word down.**
> - **`ACQUIRE`** was recommended on the strength of `env=0`, and **writing that recommendation down is
>   what moved the count**; it now stands at `4` vs `4`. **It is withdrawn as a discriminator
>   whatever today's figure happens to be** — a token whose count you change by recommending it is not
>   an instrument.
> - **`Released at`** (`2` vs `8`) is the one this note still relies on, and it is relied on
>   because the counts **differ**, not because it is absent.
>
> **That is the proof of the rule: a token a note writes *about* is not a stable discriminator of that
> note.** Every `env` figure here is self-measuring, carries every fragility § *Definition-of-Done
> item 5* documents, and **will move again on the next append**. **Whoever edits this file MUST re-run
> the loop above and update the `env` column and the three verdicts in the same commit** — or, better,
> discriminate on `c001-window-3136.md`'s counts alone, which no edit to *this* file can perturb.
>
> **The conclusion is unaffected, and the correction to it is the point.** The existence half of the
> twin's job was already carried independently by `test -s` plus the line count; identity is carried by
> `Released at`, on the strength of `2` ≠ `8` rather than the withdrawn claim of absence. The `0`
> is still a real zero.

**The prescribed twin is wrong for this file, and that is recorded rather than worked around.**
`command -v` is a toolchain-transcript token; the window handshake is built from `ls`, `pgrep`,
`/proc/<pid>/cwd` and `git worktree list` and has no legitimate reason to contain it. Pasting one in
to satisfy a grep would be gaming the check. The twin's *intent* — prove the file exists and is the
right file before believing a `0` — is honoured by **three** measurements rather than one: `test -s`
plus the line count for **existence**, `PENDING` (a token DoD item 2 independently requires this file
to carry) for **non-emptiness of the expected content**, and `Released at` for **identity**, since
`PENDING` did not discriminate between the two note files when the twin was chosen and discriminates
now only by the self-inflation recorded above. Filed as `residual-ledger.md`
**RL-003**, with a successor note for WP05 and WP07, whose prompts carry the same loop shape.

All results per file are reported in the WP01 handoff, both `0`s included — four for
`environment-3136.md`, five for `c001-window-3136.md` (the added `Released at` discriminator).

