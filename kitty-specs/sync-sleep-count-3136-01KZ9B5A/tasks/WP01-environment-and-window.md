---
work_package_id: WP01
title: Interpreter provisioning, the C-001 tests/sync window handshake, and the NFR-005 baseline
dependencies: []
requirement_refs:
- NFR-005
- C-001
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
history: []
agent_profile: debugger-debbie
authoritative_surface: .python-version
create_intent: []
execution_mode: code_change
owned_files:
- .python-version
- uv.lock
role: investigator
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Interpreter provisioning, the C-001 `tests/sync` window handshake, and the NFR-005 baseline

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `investigator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this
work package's task type and `authoritative_surface`.

**Start command** (this is the only supported way to prepare the workspace):

```bash
spec-kitty implement WP01
```

Do **not** use `spec-kitty agent action implement` — that command only *displays* the prompt; it does
not claim the WP or prepare a workspace.

---

## Objective

WP01 is the mission's **environment and resource gate**. It is the head of Lane A and the head of the
critical path `WP01 → WP02 → WP05 → WP07` (`plan.md:1256-1265`). Nothing else in the mission can
produce evidence until this WP has produced its three artifacts, and **none of the three is code**:

1. **The pinned toolchain**, recorded as a transcript of `command -v python pytest ruff mypy spec-kitty`
   plus each `--version`, proving every tool resolves **inside this tree** and not in `~/.local/bin`.
   It is the mission's first artifact because every later criterion's commands depend on it, and a
   transcript missing the `command -v` line is not evidence (`spec.md:433-438`, `plan.md:172-177`).
2. **The `C-001` `tests/sync` window handshake** — acquisition recorded, scope recorded, release
   assigned. `tests/sync` and `tests/cli` must never run concurrently here, and **a sibling mission may
   hold the window**: a cross-mission resource that per-mission lane computation structurally cannot
   see (`spec.md:480`). The post-plan squad found it owned by nothing and called it "the single most
   likely place for the mission to stall" (`analysis-report.md:481-483`). Acquisition and release are
   **real deliverables**, not a note.
3. **The `NFR-005` baseline arm**, captured with the interpreter pinned and `python -V` quoted, in the
   same held window as the comparison it will be measured against (`spec.md:472`, SC-014 at
   `spec.md:899-905`).

**What this WP does not do**: change a single tracked file. See the ownership note below — that is the
point, not an omission.

---

## Context

### The environment hazard — the mission's most-repeated failure, and it has already bitten the orchestrator

**NEVER run a bare `uv run` (or a bare `uv sync`) anywhere in this tree.** A bare invocation re-solves
against the tracked `.python-version` (`3.11.15`), **destroys `.venv`**, and recreates it *without*
`pytest`, `ruff`, or `mypy` — so it both strips the toolchain **and** silently downgrades the
interpreter two minor versions away from CI.

This has happened **three times in this mission**, the third time to the orchestrator immediately after
it had committed the warning. It is not a hypothetical and it is not a style preference: a bare
`uv run` in an implementation transcript is a **defect** (`spec.md:433-438`, `plan.md:172-177`).

The proof, non-destructive, recorded once so no WP re-discovers it (`plan.md:136-149`,
`spec.md:396-419`):

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

$ uv sync --dry-run --python 3.12 --extra test --extra lint
Would make no changes                      # ← the extras are what save it
```

The cause is structural: `pytest` / `ruff` / `mypy` live **only** in
`[project.optional-dependencies]`; `[dependency-groups] dev` carries type stubs only; there is no
`[tool.uv]` block. CI never trips this because every job runs `uv sync --frozen --all-extras` first.

**The two sanctioned forms — one of these, never the bare form** (`plan.md:163-170`):

```bash
# Form 1 (preferred) — direct, no resolver involvement.
./.venv/bin/python -m pytest …
./.venv/bin/ruff check .

# Form 2 — uv-driven, extras pinned so the toolchain survives the resolve.
uv run --python 3.12 --extra test --extra lint python -m …
```

**Recovery**, if the venv is destroyed anyway — then re-verify `./.venv/bin/pytest --version` after
*any* `uv` invocation whatsoever, `--dry-run` included:

```bash
uv sync --python 3.12 --extra test --extra lint
```

### The PATH hazard

`~/.local/bin/{spec-kitty,pytest,ruff,mypy}` are **first on the unmodified `PATH`** and resolve to an
**unrelated checkout** (all four verified in the plan session; `pytest` re-verified while this prompt
was written — `command -v pytest` → `/home/jeroennouws/.local/bin/pytest`). Prepend
`<repo>/.venv/bin` to `PATH` and quote `command -v` before trusting any version number.

### Current venv, as measured (re-verified while this prompt was written)

| Tool | Value |
|---|---|
| `./.venv/bin/python -V` | **Python 3.12.13** — matches CI's `fast-tests-sync` |
| `./.venv/bin/pytest --version` | **pytest 9.0.3** |
| `./.venv/bin/ruff --version` | **ruff 0.15.12** |
| `./.venv/bin/mypy --version` | **mypy 1.20.2** |
| `.python-version` | **3.11.15** — diverges from the venv and from CI |

### Ownership note — `owned_files` are owned because their *invariance* is the deliverable

`owned_files` are `.python-version` and `uv.lock`. **This WP does not edit either of them.** They are
owned because proving they are unchanged is part of what WP01 delivers:

- **`.python-version` reads `3.11.15`** while CI pins `3.12` in three places and the venv is 3.12.13.
  `plan.md:126` and IC-01 risk (c) (`plan.md:574-576`) make **recording and not fixing** that
  divergence this WP's job — changing a tracked interpreter pin is a repo-wide decision outside this
  mission's constraint set. It is also *why* an accidental bare `uv run` downgrades rather than merely
  strips.
- **`uv.lock`** is the frozen lockfile that the `uv sync --dry-run` proof resolves against. If it moves,
  the proof above stops describing this tree. It must show **no diff**.

**Expect a non-fatal validation warning**: `code_change WP does not own any files under src/ or
tests/`. It is deliberate. Flipping `execution_mode` to `planning_artifact` would sweep this WP into
the `lane-planning` lane and pull it out of the plan's Lane A, contradicting `plan.md:1273-1278`. Do
**not** "fix" the warning.

This WP's `notes/` deliverables are declared **out-of-map planning writes** under `kitty-specs/`,
because `owned_files` may not contain `kitty-specs/` paths:

- `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md` (T001, T003)
- `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md` (T002, T004 — **ACQUIRE half
  only**; the RELEASE half is WP07's)

### Discipline this WP must impose on itself

- **Never pipe a suite whose exit status you need.** Redirect to a file, then quote the `N passed`
  line and print the selected count. A pipe replaces pytest's exit status with the tail command's.
- **`-ra`, never `-rf`.** `-rf` hides errors, skips, and xfails.
- **Count `^ERROR tests/`, not `^ERROR `** — the latter matches unrelated log lines.
- **Do NOT run `tests/sync` or `tests/cli`** beyond exactly what T003's single sanctioned baseline
  command requires, and **never both**.
- **A killed or timed-out run is neither a pass nor a fail.** Say exactly that; do not re-run to a
  verdict and report the second run as though it were the first.
- **Report distributions, not scalars**, for anything that varies between runs.
- **A cited `file:line` is not evidence that the line says what the citation claims — open it.** This
  mission has already had docstring prose become a load-bearing constraint twice, and a fixture claimed
  to reach a site it structurally cannot. Open every line before quoting it.
- A pre-existing failure needs a GitHub issue before you treat it as accepted baseline — the charter's
  **Pre-existing Failure Reporting Rule** (`.kittify/charter/charter.md:395`).

---

### Subtask T001 — Pin and prove the toolchain before any other arm runs

**Purpose.** Every later criterion in this mission is a command, and every command's meaning depends on
which interpreter and which runner executed it. R2's plan pinned one of nine commands; the other eight
resolved to the foreign `~/.local/bin` checkout, and the one that *was* pinned was pinned to the
destructive form (`plan.md:172-177`). T001 makes the resolution explicit, once, in a transcript that
every later WP cites instead of re-deriving.

**Steps.**

```bash
cd /home/jeroennouws/dev/sk-missions/3136
export PATH="$PWD/.venv/bin:$PATH"

date -u "+%Y-%m-%dT%H:%M:%SZ"
command -v python pytest ruff mypy spec-kitty
python -V
pytest --version
ruff --version
mypy --version
uv --version
```

Then record the divergence **without touching it**:

```bash
cat .python-version                                  # expect: 3.11.15
git status --porcelain -- .python-version uv.lock    # expect: NO output
git diff --stat -- .python-version uv.lock           # expect: NO output
```

A silent `git diff` is only evidence when a **loud sibling diff from the same invocation** proves the
command is wired up — the positive-twin idiom this spec uses for C-008 (`spec.md:932-936`). Pair it:

```bash
git diff --stat 98198e980 -- kitty-specs/ | tail -3   # expect: NON-EMPTY
```

Write the transcript to `notes/environment-3136.md`: the five `command -v` lines verbatim, the five
`--version` lines verbatim, the `.python-version` value, an explicit sentence that the divergence is
**recorded and deliberately not fixed**, and both sanctioned command forms copied in full so no later
WP has to go and find them.

**Files.** `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md` (create). Read-only
against `.python-version`, `uv.lock`, `pyproject.toml`.

**Validation.**
- Every `command -v` line resolves under `/home/jeroennouws/dev/sk-missions/3136/.venv/bin` — **except**
  `spec-kitty`, which may legitimately resolve elsewhere; if it does, say so explicitly and name the
  path rather than leaving it ambiguous.
- The four versions read `3.12.13` / `9.0.3` / `0.15.12` / `1.20.2`. Any other value means the venv was
  disturbed: stop, run the recovery command, re-verify, and record that it happened.
- `git status --porcelain -- .python-version uv.lock` is empty, reported next to the loud sibling diff.
- `grep -c 'uv run' notes/environment-3136.md` — every hit must carry `--python 3.12 --extra test
  --extra lint`. A bare form in your own notes is the same defect as a bare form in a command.

---

### Subtask T002 — Acquire the C-001 `tests/sync` window, with a recorded handshake

**Purpose.** `C-001` says `tests/sync` and `tests/cli` must never run concurrently on one machine, and
that **a sibling mission may hold the window** (`spec.md:480`). Lane computation is per-mission and
cannot see this. Acquisition is therefore a deliverable with a recorded holder, not an assumption.

**A single `pgrep` sample is not evidence that a sweep has finished.** That mistake was already made in
this programme and sent an implementer hunting a completion that had not happened. Require **≥ 3
spaced, timestamped samples**, all quiet, before declaring the window free.

**Steps.**

1. **Enumerate the sibling checkouts** that could hold the window:

```bash
ls -d /home/jeroennouws/dev/sk-missions/*/ | wc -l
git worktree list
```

2. **Look for an unreleased acquisition record** in any sibling mission. The handshake file *is* the
   lock; there is no other registry:

```bash
grep -rl 'c001-window' /home/jeroennouws/dev/sk-missions/*/kitty-specs/*/notes/ 2>/dev/null
```

For each hit, open the file and check whether it has a **release** half. An acquire without a release
means the window is held — do not proceed; record the holder and escalate.

3. **Take ≥ 3 spaced, timestamped samples** of running test processes, ≥ 60 s apart. Attribute each
   match to a checkout — a bare `pgrep` line does not tell you whose run it is:

```bash
for i in 1 2 3; do
  date -u "+%Y-%m-%dT%H:%M:%SZ"
  for p in $(pgrep -f 'pytest' | grep -v "^$$\$"); do
    printf '  pid=%s cwd=%s\n' "$p" "$(readlink -f /proc/$p/cwd 2>/dev/null)"
    tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null; echo
  done
  sleep 60
done
```

**`pgrep -af pytest` matches its own wrapper shell** — a naive sample self-matches and reports a false
positive. Filter your own PID and attribute by `/proc/<pid>/cwd`, as above.

**If your harness blocks a foreground `sleep`**, run the loop as one backgrounded script redirecting to
a scratch file and read the file afterwards. Do not collapse the three samples into one because the
loop was inconvenient.

**This hazard is live.** While this prompt was written, sibling mission `3162` had a shell parked on
`until ! pgrep -f 'pytest tests/next tests/runtime'; do sleep 20; done` — another mission actively
waiting on a test cone on this machine. Expect neighbours.

4. **Write the ACQUIRE half** of `notes/c001-window-3136.md`, containing:

| Field | Content |
|---|---|
| Holder | `WP01`, mission `sync-sleep-count-3136-01KZ9B5A`, agent id |
| Acquired at | ISO-8601 UTC, from `date -u "+%Y-%m-%dT%H:%M:%SZ"` |
| Siblings checked | the sibling-checkout count and the result of the `c001-window` grep, verbatim |
| Samples | all three timestamps and their full output, including the quiet ones |
| Scope | filled by T004 |
| Released at | **left explicitly `PENDING — WP07 (T043)`**, never blank |

**Files.** `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md` (create, ACQUIRE half
only).

**Validation.**
- Three distinct timestamps, ≥ 60 s apart, each with its own output block. Two samples is a fail.
- Every `pytest` match is attributed to a checkout path, or the sample is explicitly recorded as quiet.
- The `Released at` row exists and reads `PENDING — WP07`. A missing row lets a reader assume release.
- If the window is **not** free: record the holder, do **not** run T003, and move WP01 to `blocked`
  with the holder named. Waiting is correct; running anyway is a C-001 violation.

---

### Subtask T003 — Capture the NFR-005 baseline arm on `98198e980`, interpreter quoted

**Purpose.** NFR-005 budgets **≤ 5.0 s** added wall clock on a serial `tests/sync/tracker/` run, and
SC-014 requires **both arms on the same interpreter with `python -V` printed per arm** — "a delta
measured across two interpreters is not a measurement" (`spec.md:899-905`). WP01 takes the **base**
arm. It must be taken **inside T002's window** and with the interpreter from T001.

**Steps.**

1. Materialise the base tree. `98198e980` is the mission's merge-base and resolves (verified:
   `git cat-file -t 98198e980` → `commit`). Create a **throwaway detached worktree** rather than
   checking out in place:

```bash
cd /home/jeroennouws/dev/sk-missions/3136
git worktree add --detach /tmp/wp01-base-98198e9 98198e980
git -C /tmp/wp01-base-98198e9 rev-parse HEAD    # must print 98198e980045752a…
```

The mission's coord worktree also sits at exactly `98198e980`. **Do not run the suite there** — it is
the coordination surface, not a scratch tree. Its existence is corroboration that the ref resolves,
nothing more.

2. Run the arm — **one command, once**, with the mission venv's interpreter and the base tree's
   sources. Redirect; do not pipe:

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

3. **Prove the sources came from the base tree, do not assume it.** The venv may hold an editable
   install pointing at the mission checkout, which would silently make this arm measure the *head*
   tree:

```bash
PYTHONPATH=/tmp/wp01-base-98198e9/src \
  /home/jeroennouws/dev/sk-missions/3136/.venv/bin/python -c \
  "import specify_cli, sys; print(specify_cli.__file__); print(sys.version)"
```

If `specify_cli.__file__` does not sit under `/tmp/wp01-base-98198e9/src`, **the arm is invalid** —
record that, and resolve it before reporting a number.

4. Extract, quoting exact lines from the redirect:

```bash
grep -E '^[0-9]+ (passed|failed)|[0-9]+ passed' /tmp/wp01-base-arm.txt | tail -3
grep -c '^ERROR tests/' /tmp/wp01-base-arm.txt
grep -A11 'slowest' /tmp/wp01-base-arm.txt
```

Record in `notes/environment-3136.md`: the resolved `python -V`, the full pytest summary line, the
**selected test count**, wall-clock total, the slowest individual test from `--durations=10`, the
`^ERROR tests/` count, and `EXIT=`.

5. **Clean up**: `git worktree remove /tmp/wp01-base-98198e9`.

**Files.** `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md` (append).

**Validation.**
- `python -V` printed for the arm and equal to `Python 3.12.13`.
- The summary line is **quoted**, not paraphrased, and the selected count is stated.
- `^ERROR tests/` count reported even when zero.
- No individual test exceeds **60 s** (CI runs `--timeout=240`; 60 s leaves 4× headroom).
- If the run is killed or times out: report it as **neither pass nor fail**, in those words, and do not
  substitute a re-run's number for it.
- `tests/cli` was not run. Say so explicitly.

---

### Subtask T004 — Record the window's scope and assign its release

**Purpose.** A window with no recorded scope is a window nobody can safely release. IC-01 makes the
release edge explicit: the window spans the whole critical path and is released only after the last
consumer (`plan.md:563-565`, `plan.md:1280-1283`).

**Steps.** Complete the `Scope` section of `notes/c001-window-3136.md` with all four rows below —
checked against `plan.md`, not copied from this prompt. Open the lines.

| Consumer | Needs the window? | Why |
|---|---|---|
| **WP02** (guard red→green, determinism arms) | **Yes** | collects `tests/sync/tracker/` |
| **WP07** (constraint transcripts, CI observation) | **Yes** | and owns the **RELEASE** half |
| **WP03, WP04, WP05, WP06** | **No** | the census and the gate are static AST readers that never collect `tests/sync` — which is also why the gate does not violate C-001 (`analysis-report.md:517`) |
| **This WP (WP01)** | **Yes**, for T003's single base arm only | |

Then state, in the file:

- The **release is WP07's (T043)**, not WP01's. WP01 must not release.
- **A `tests/sync` result reported by any WP with no corresponding acquisition record in this file is
  not evidence** (`plan.md:565`) — write that sentence into the file, because it is the rule reviewers
  will apply.
- The one honest ambiguity, named rather than papered over: NFR-005 says the baseline must be captured
  "in the same session as the comparison", but the comparison arm cannot exist until WP02 has landed
  and WP01 must reach `approved` before WP02 can be claimed. Record that **"same session" is
  operationalised as "the same held C-001 window, the same interpreter, `python -V` printed on both
  arms"** — which is what SC-014 actually checks — and that the window spanning the critical path is
  what makes that legitimate.

**Files.** `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md` (complete).

**Validation.**
- All seven WPs appear in the scope table with a yes/no and a reason.
- The release owner is named as WP07 and the `Released at` row still reads `PENDING`.
- The "same session" reconciliation is written down, not assumed.

---

## Definition of Done

Evidence for this WP is a **`spec-kitty agent tasks mark-status` record per subtask**, not a ticked box
in this file:

```bash
spec-kitty agent tasks mark-status T001 --status done
spec-kitty agent tasks mark-status T002 --status done
spec-kitty agent tasks mark-status T003 --status done
spec-kitty agent tasks mark-status T004 --status done
```

A subtask is done only when all of the following hold:

1. `notes/environment-3136.md` exists and carries the `command -v` line for all five tools, the five
   `--version` lines, the `.python-version` divergence recorded-and-not-fixed, and both sanctioned
   command forms.
2. `notes/c001-window-3136.md` exists with holder, acquired-at, siblings-checked, **≥ 3 spaced
   timestamped samples**, the full scope table, and `Released at: PENDING — WP07`.
3. The NFR-005 base arm is recorded with a quoted summary line, the selected count, wall clock, the
   slowest test, the `^ERROR tests/` count, `EXIT=`, and the resolved `python -V`.
4. `git status --porcelain -- .python-version uv.lock` is **empty**, reported next to a loud sibling
   diff from the same invocation.
5. **The `uv run` negative is reported with its positive twin, per file.** A bare
   `grep -c 'uv run' notes/*.md` is the trap WP07 T037 names and closes: on an **absent** file
   `grep -c` prints no count and exits `2`, which a reader scores as satisfied. Run `test -s`, a line
   count, and a same-file twin that must be `≥ 1` **before** the negative, once per note file:
   ```bash
   for NOTES in kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md \
                kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md; do
     echo "== $NOTES"
     test -s "$NOTES" && echo "NON-EMPTY: $(wc -l < "$NOTES") lines" || echo "MISSING OR EMPTY — FAIL"
     grep -c 'command -v' "$NOTES"    # twin: must be >= 1
     grep -c 'uv run' "$NOTES"        # every hit carries --python 3.12 --extra test --extra lint
   done
   ```
   Record all four results per file. A `0` with no `test -s` and no twin above it is **not** evidence.
6. `tests/cli` was never run, and `tests/sync` was run exactly once (T003's single arm).

If a subtask cannot be completed, mark it `blocked` with the reason named — never `done` with a caveat
in prose.

---

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **A bare `uv run`/`uv sync` destroys `.venv`** — observed three times in this mission, once immediately after the warning was committed. | Only the two sanctioned forms. Re-verify `./.venv/bin/pytest --version` after *any* `uv` invocation, `--dry-run` included. Recover with `uv sync --python 3.12 --extra test --extra lint`, and **record that it happened**. |
| R2 | **`~/.local/bin` shadows the toolchain** — all four binaries resolve to an unrelated checkout. | Prepend `<repo>/.venv/bin`; quote `command -v` before trusting any version. |
| R3 | **The window is already held by a sibling mission**, invisible to lane computation. | The ≥ 3-sample sweep plus the sibling `c001-window` grep. If held: block, name the holder, wait. Do not run T003. |
| R4 | **A single quiet `pgrep` read as "the sweep finished."** Already made in this programme; it sent an implementer chasing a completion that had not happened. | ≥ 3 spaced timestamped samples, each attributed via `/proc/<pid>/cwd`, own PID filtered out. |
| R5 | **The base arm silently measures the head tree** via an editable install in the venv. | Print `specify_cli.__file__` under the same `PYTHONPATH` and assert it sits under the base worktree. If it does not, the arm is invalid — say so. |
| R6 | **`.python-version` gets "fixed."** It reads `3.11.15` and looks like a bug. | It is out of the mission's permitted change set (`plan.md:126`, `plan.md:574-576`). Record, never edit. It is also what makes an accidental bare `uv run` downgrade rather than merely strip. |
| R7 | **The `code_change` ownership warning gets "fixed"** by flipping to `planning_artifact`. | That sweeps WP01 into `lane-planning` and out of Lane A, contradicting `plan.md:1273-1278`. The warning is deliberate. |
| R8 | **A killed or timed-out arm gets re-run and the second number reported as the first.** | A killed run is neither pass nor fail. Report it as such, then decide. |

---

## Reviewer Guidance

Reject on any of these; each is a one-command check.

1. **No `command -v` line** in `notes/environment-3136.md`, or a version that is not
   `3.12.13` / `9.0.3` / `0.15.12` / `1.20.2` with no explanation. A transcript without `command -v` is
   not evidence.
2. **A bare `uv run` or `uv sync` anywhere** in the transcript or the notes:
   `grep -n 'uv run\|uv sync' kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/*.md` — every hit must
   carry `--python 3.12 --extra test --extra lint`.
3. **Fewer than three window samples**, samples not spaced, samples without timestamps, or samples that
   do not attribute a matched PID to a checkout. Count the `date -u` lines.
4. **A `tests/sync` result with no acquisition record**, or any `tests/cli` invocation at all.
5. **`.python-version` or `uv.lock` modified**: `git diff --stat -- .python-version uv.lock` must be
   silent, and the WP must have reported it next to a **loud** sibling diff. A silent diff alone proves
   nothing — the command may not have been wired up.
6. **The NFR-005 arm without `python -V`**, without a quoted summary line, or without the selected
   count. A wall-clock number with no interpreter beside it is not a measurement (SC-014).
7. **`Released at` blank rather than `PENDING — WP07`**, or WP01 releasing the window itself.
8. **Any `file:line` citation in the notes that does not say what the note claims.** Open two of them
   at random. This mission has had docstring prose become a load-bearing constraint twice, and a
   fixture claimed to reach a site it structurally cannot — spot-checking citations is not pedantry
   here, it is the failure mode.
9. **A cleaned-up transcript.** If the venv was destroyed and recovered mid-WP, that belongs in the
   notes. A tidy transcript that hides a recovery is worse than a messy one that records it.
