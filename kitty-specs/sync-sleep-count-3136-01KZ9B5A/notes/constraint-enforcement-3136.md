# Constraint-enforcement transcripts — WP07 (`SC-016`)

Mission `sync-sleep-count-3136-01KZ9B5A`. **This file has exactly one writer: WP07.**

It records the enforcement evidence for `C-002`, `C-004`, `C-008`, `C-010` and `NFR-006` / `SC-012`,
plus the T042 filings register and the `C-006` not-re-opened register.

> **Measurement convention — binding on this file.** Where a number is *about this file itself*
> (its line count, a `grep -c` over its own directory), the number is true only at the instant it was
> written and is false the moment the file grows. **This file therefore states the reproducing command
> and never freezes such a figure.** That defect — a self-measuring block — caused three WP01
> rejections and one WP05 rejection in this mission; it is not re-committed here.

---

## §0 — Toolchain (written FIRST, so this file is non-empty before any grep runs against it)

`~/.local/bin/*` resolves to an unrelated checkout, so every path below is resolved, not assumed.
`PATH` was prefixed with `$PWD/.venv/bin` for the whole session.

```
$ date -u '+%Y-%m-%dT%H:%M:%SZ'
2026-08-07T06:16:26Z

$ command -v python pytest ruff mypy spec-kitty
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/python
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/pytest
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/ruff
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/mypy
/home/jeroennouws/dev/sk-missions/3136/.venv/bin/spec-kitty

$ python -V; pytest --version; ruff --version; mypy --version
Python 3.12.13
pytest 9.0.3
ruff 0.15.12
mypy 1.20.2 (compiled: yes)

$ grep -rl 'sk-missions/3136/src' .venv/lib/python3.12/site-packages/*.pth
.venv/lib/python3.12/site-packages/_editable_impl_spec_kitty_cli.pth
```

Editable `.pth` → root `src`, intact. **No bare `uv run` and no bare `uv sync` was issued at any
point in this WP** — the two destructive forms named in the prompt and in `RL-004` / `RL-006` /
`RL-013` / `RL-017` / `RL-050`. Recovery form, recorded but **not run** (nothing needed recovering):
`uv sync --python 3.12 --extra test --extra lint`.

### The two gate-emitted destructive instructions this WP was given and refused

| Source | What it instructs | Disposition |
|---|---|---|
| `scripts/docs/check_docs_freshness.py` remediation hint (`RL-017` / `RL-050`) | a bare `uv run …` | **Read, not obeyed.** The lockfiles were regenerated with `./.venv/bin/python` (§4). |
| `move-task` success/《error》 hint (`RL-033`) | `git restore --source … --worktree -- kitty-specs/` | **Read, not obeyed.** It destroys uncommitted work; this WP's notes were uncommitted at the time. |

---

## §1 — Where these measurements were taken, and why the base ref matters

This WP measures on the **composed mission tree**, not on `feat/sync-sleep-count-3136`.

**Finding (structural, and it changes how `C-004` / `C-008` must be read).** At the time WP07 opened,
`feat/sync-sleep-count-3136` carried **none** of the mission's code. The seven work packages' output
sits on the lane branches; lane consolidation had not run. Reproduce:

```bash
git diff --stat feat/sync-sleep-count-3136..kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-b -- src/ tests/
grep -c '^_sleep = time.sleep' src/specify_cli/tracker/saas_client.py    # on feat: 0
```

Consequence for measurement: `git diff 98198e980 -- src/specify_cli/tracker/saas_client.py` on `feat`
returns **empty** — which under `C-004`'s R-2 phrasing would read as "the file did not change", the
exact false-pass `C-004` was rewritten to exclude. Every transcript below is therefore taken on the
composed tree at `pr/sync-sleep-count-3136`, whose composition is recorded in §7.

### The `98198e980` base is no longer the right diff base for `C-008` — measured, not assumed

`98198e980` is the mission's diff base **on `feat`** (`RL-002`), and it is also the merge-base of
`feat` and `upstream/main`:

```bash
git merge-base feat/sync-sleep-count-3136 upstream/main      # -> 98198e980
git merge-base --is-ancestor 98198e980 upstream/main; echo $? # -> 0
```

`upstream/main` has since moved **70 commits** past it, and one of those commits edits
`.github/workflows/ci-quality.yml`. So on a PR branch built from current `upstream/main`, the
prompt's literal `C-008` command produces a **large non-empty silent half** — a false failure that
says nothing about this mission. This is recorded as **`RL-049`**.

---

## §2 — `C-008`: the CI shard composition is unchanged (silent half + loud sibling, one invocation)

**Both halves from a single invocation**, redirected, per the prompt.

### 2a — attribution: is the `98198e980` delta upstream's own, in full?

```
$ git diff 98198e980 upstream/main -- .github/workflows/ci-quality.yml | wc -c
8769
$ git diff 98198e980 -- .github/workflows/ci-quality.yml | wc -c        # PR tree
8769
$ diff <(git diff 98198e980 upstream/main -- .github/workflows/ci-quality.yml) \
       <(git diff 98198e980 -- .github/workflows/ci-quality.yml)
IDENTICAL — every byte is upstream's
```

The two diffs are **byte-identical**, so the mission contributed **zero** bytes to that file. The
upstream change is a sweep removing `needs.<job>.result != 'failure'` / `== 'success'` guards from
`if:` conditions across the shard graph — an upstream workflow change, not a shard-composition change
made by this mission.

### 2b — `C-008` proper, against the PR branch's own base

```
### C-008 — silent half (must be EMPTY)
$ git diff upstream/main -- .github/workflows/ci-quality.yml
                                        <-- no output
### C-008 — LOUD sibling, same invocation (must be NON-EMPTY)
$ git diff --stat upstream/main -- src/specify_cli/tracker/saas_client.py
 src/specify_cli/tracker/saas_client.py | 42 ++++++++++++++++++++++++++--------
 1 file changed, 32 insertions(+), 10 deletions(-)
```

| Half | Lines | Required | Verdict |
|---|---|---|---|
| silent — `.github/workflows/ci-quality.yml` | **0** | empty | **PASS** |
| loud sibling — `saas_client.py` (same invocation) | **2** | non-empty | **PASS** — the ref resolves |

> **Measured in LINES, not bytes — cycle 1 reported "129 bytes" and that figure is not reproducible.**
> `git diff --stat` pads its histogram to the terminal width, so the byte count of the loud half varies
> with `COLUMNS`: **123** @72, **131** @80, **139** @100. A reviewer re-running it in a different
> terminal gets a different number and cannot tell a real change from a resize. The **line count (2) is
> width-independent**, and the substantive claim — *non-empty* — is unaffected either way. Pin the width
> explicitly if a byte count is ever wanted: `git diff --stat=80 …`.

**The loud half is non-empty, so the silent half is a real absence** and not a bad ref, a wrong
working directory or a mistyped path. Reproduce both halves:

```bash
{ echo "### silent"; git diff upstream/main -- .github/workflows/ci-quality.yml
  echo "### loud";   git diff --stat upstream/main -- src/specify_cli/tracker/saas_client.py; } 2>&1
```

The shard facts `C-008` names — the `fast-tests-sync` selection, its four `--ignore=` entries, the
marker expression, and `-n auto --dist loadfile` — are inside that unchanged file and are therefore
unchanged by this mission.

---

## §3 — `C-004`: `saas_client.py` changed ONLY by the alias seam and the jitter resolution

Both candidate bases agree here, so the verdict does not depend on the §1 base question:

```
$ git diff --stat 98198e980 upstream/main -- src/specify_cli/tracker/saas_client.py
                                        <-- empty: upstream never touched this file since the base
```

Full diff: `git diff 98198e980 -- src/specify_cli/tracker/saas_client.py` — **85 lines, 5 hunks**.

### 3a — per-hunk verdict, with pre-fix AND post-fix line numbers

Three new module-scope definitions shift every later line, so the prompt's `:439`/`:481`/`:484`/
`:515`/`:518` are **pre-fix** anchors. Both sets are stated. Derived mechanically by replaying the
hunk headers, not read off by eye.

| # | Pre-fix | Post-fix | Change | Permitted region | Verdict |
|---|---|---|---|---|---|
| 1 | — | `:36-62` | seam comment block + the three alias bindings at **`:58-60`** | (a) FR-010 alias definitions | **PERMITTED** |
| 2 | `:104-108` | — | `_poll_jitter_multiplier()` def removed (3 body lines + 2 separator lines) | (b) jitter resolution | **PERMITTED** |
| 3 | `:439` | `:461` | `time.sleep(float(wait_seconds))` → `_sleep(...)` | (a) call-site rerouting | **PERMITTED** |
| 4 | `:481` | `:503` | `start = time.monotonic()` → `_monotonic()` | (a) call-site rerouting | **PERMITTED** |
| 4 | `:484` | `:506` | `elapsed = time.monotonic() - start` → `_monotonic()` | (a) call-site rerouting | **PERMITTED** |
| 5 | `:515` | `:537` | `secrets.randbelow(4000)` → `_randbelow(4000)` | (a) call-site rerouting | **PERMITTED** |
| 5 | `:518` | `:540` | `time.sleep(jittered_delay)` → `_sleep(...)` | (a) call-site rerouting | **PERMITTED** |

**All five pre-fix anchors named in the constraint — `:439`, `:481`, `:484`, `:515`, `:518` — are
present and accounted for. Changed lines outside the two permitted regions: ZERO.** `C-004` **PASSES**.

The prompt states the jitter resolution as `:104-106`. Measured, the removal is `:104-108`: `:104-106`
is the `def` + docstring + `return`, and `:107-108` are the two blank separator lines PEP 8 requires
between top-level definitions. The prompt names the definition; the diff removes the definition and
its separators. Not a discrepancy of substance — recorded so a reviewer re-deriving it is not surprised.

### 3b — the alias form is `ast.Assign`, never `ast.FunctionDef` (opened, not cited)

The `SC-007` arm-4b refusal is *static*, so the node type is the load-bearing fact. Derived from the
AST of the shipped file, not from a grep:

```
line 58: _sleep     -> node=Assign, value=time.sleep
line 59: _monotonic -> node=Assign, value=time.monotonic
line 60: _randbelow -> node=Assign, value=secrets.randbelow
any FunctionDef named _sleep/_monotonic/_randbelow: []
```

Reproduce:

```bash
./.venv/bin/python - <<'PY'
import ast
src=open('src/specify_cli/tracker/saas_client.py').read()
for n in ast.parse(src).body:
    for t in getattr(n,'targets',[]):
        if isinstance(t,ast.Name) and t.id in {'_sleep','_monotonic','_randbelow'}:
            print(n.lineno, t.id, type(n).__name__, ast.unparse(n.value))
PY
```

This confirms the mission's central structural claim at the shipped tree: the aliases are
**import-bound assignments at `:58-60`**.

### 3c — the removed `_poll_jitter_multiplier` was dead, with its control

```
$ grep -rn "_poll_jitter_multiplier" --include=*.py --include=*.md src/ tests/ scripts/
                                        <-- no output
$ grep -c "_randbelow" src/specify_cli/tracker/saas_client.py     # CONTROL: same grep, live name
2
```

The control is non-zero, so the empty result is a real absence and not an unwired grep. Removing an
unreferenced definition changes no behaviour.

### 3d — behaviour half: delay values, cardinality and raise conditions unchanged

Read off the §3 diff directly — every one of these is a **context** line (unprefixed), i.e. present
identically on both sides:

| Quantity | Value | Status in the diff |
|---|---|---|
| retry-after fallback | `wait_seconds = 5` | context — unchanged |
| backoff seed / cap / budget | `delay = 1.0`, `cap = 30.0`, `total_timeout = 300.0` | context — unchanged |
| backoff step | `delay = min(delay * 2, cap)` | context — unchanged |
| jitter factor | `0.8 + (jitter_basis_points / 10000)` | context — unchanged |
| jitter draw width | `randbelow(4000)` → `_randbelow(4000)` | **argument unchanged**; only the callee name is rebound |
| raise conditions | `raise SaaSTrackerClientError(...)` × 3 | context — unchanged |

Every edit is a **one-for-one callee substitution**: no call was added, removed, duplicated or moved
across a branch, so call cardinality (`n=3`, `n=1`, `n=1`, `n=1` as WP02 recorded) is preserved by the
shape of the diff itself. WP02's delay-value evidence (`[0.9, 2.0, 4.4]`, `3.0`, `5.0`, `2.0`) is in
`notes/alias-seam-3136.md`.

### 3e — the load-bearing property, re-derived by construction (not transcribed)

The mission's central claim — and the one an earlier ADR draft **stated backwards**, costing two
review cycles — is *why the assignment form is required when a wrapper is not*. It was re-derived
this session with a two-module experiment rather than quoted:

```
=== WINDOW A — stdlib-only patch  (patch 'time.sleep') ===
  ASSIGNMENT form -> stdlib recorder call_count = 150
  WRAPPER    form -> stdlib recorder call_count = 153
  DISTINGUISHABLE? YES   (delta = 3)

=== WINDOW B — both-patched: patch the module's own '_sleep' ===
  ASSIGNMENT form -> alias recorder call_count = 3
  WRAPPER    form -> alias recorder call_count = 3
  DISTINGUISHABLE? NO   (delta = 0)
```

**Read this in the right direction.** In the **both-patched** window the two forms are
**indistinguishable** — patching `_sleep` replaces the wrapper *object*, so a wrapper's body never
runs and it behaves exactly like a rebound assignment. The difference appears **only** under a
**stdlib-only** patch, where the wrapper re-enters a live `time.sleep` lookup and **leaks the
module's own 3 sleeps into the foreign recorder** (153 vs 150). That is why the wrapper refusal
cannot be a runtime arm and must be static (`SC-007` arm 4b) — which is exactly what WP02's guard
docstring says of itself:

> *"It does **not** catch a `def`-based wrapper seam — a wrapper with every decorator retargeted is
> runtime-immune and passes every arm here; that refusal is *static* (`SC-007` arm 4b: `ast.Assign`,
> never `ast.FunctionDef`)."*
> — `tests/sync/tracker/test_sleep_attribution_guard_3136.py:40-45`, opened and read.

Note also that `_PROBE_CALLS = 150` in that guard is a **configured constant**
(`test_sleep_attribution_guard_3136.py:83`), not a measured outcome; the 150/153/3 figures above are
this session's own measurements from the experiment, which is why they were re-derived rather than
copied.

---

## §4 — `NFR-006` / `SC-012`: lint clean, and the config escape hatch closed

### 4a — `ruff check` on the composed tree

```
$ ./.venv/bin/ruff check . > /tmp/ruff-composed.txt 2>&1; echo "EXIT=$?"
EXIT=0
$ tail -1 /tmp/ruff-composed.txt
All checks passed!
```

`ruff 0.15.12`. **`All checks passed!`, `EXIT=0`.** Only `ruff check` was run; the `ruff` **formatter**
subcommand was not invoked at any point in this WP (see §5).

### 4b — added inline suppressions, WITH the positive control — **the prompt's expected `0` is WRONG**

A `0` from an unwired grep is indistinguishable from a `0` from a clean diff, so both numbers are shown:

**The diff must be PATH-SCOPED, and this is the fifth instance of the probe-contamination class.**
Unscoped, the probe reads its own report: the mission dossier under `kitty-specs/` quotes `# noqa`
many times — including §4b's own enumeration table below — and every quotation counts as an added
suppression. Measured on the shipped head, both forms:

```
# UNSCOPED — WRONG. Counts the dossier, i.e. this very file.
$ git diff -U0 upstream/main | grep -cE '^\+.*(# noqa|# type: ignore)'
49                      <-- 43 of these are WP07's own dossier prose
$ git diff -U0 upstream/main | grep -c -e '^+'
20203

# PATH-SCOPED — the correct probe. Product surfaces only.
$ git diff -U0 upstream/main -- src/ tests/ scripts/ docs/ | grep -cE '^\+.*(# noqa|# type: ignore)'
6                       <-- NOT the 0 the WP prompt predicts
$ git diff -U0 upstream/main -- src/ tests/ scripts/ docs/ | grep -c -e '^+'
4404                    <-- CONTROL: large non-zero, the probe is wired
```

Confirm the 43-hit gap is entirely dossier: `git diff -U0 upstream/main -- kitty-specs/ | grep -cE
'^\+.*(# noqa|# type: ignore)'` → **43**. `49 − 43 = 6`, the path-scoped figure.

> **`RL-048` generalises this class and this file documents it — and still shipped the unscoped form
> in cycle 1.** Documenting a failure mode does not apply it. The rule earned here: **a probe run over
> a repository that contains its own report must exclude the report**, and *"every probe must be
> re-run after the report that quotes it is written"* has to be executed, not merely written down.

The WP07 prompt (T038 step 2) states this count is **"expected 0"**. **Measured, it is 6.** The
prediction was not transcribed; it was measured, and it is wrong. Enumerated — every one opened:

Line numbers below were exact at anchor `b0312a438` and have since moved (`bf68b101b` added 10 lines
to the gate's docstring). **Locate them by command, not by the frozen number** — same discipline as the
rest of this file:

```bash
grep -nE '#\s*(noqa|type: ignore)' tests/architectural/test_shared_module_object_patches.py \
     scripts/patch_seam_census.py tests/architectural/test_patch_seam_census_control.py
```

| # | File | Rule | `@b0312a438` | on HEAD | Real suppression? |
|---|---|---|---|---|---|
| 1 | `scripts/patch_seam_census.py` | `E402` | `:68` | `:68` | **yes** |
| 2 | `tests/architectural/test_shared_module_object_patches.py` | `E402` | `:71` | `:81` | **yes** |
| 3 | `tests/architectural/test_shared_module_object_patches.py` | `E402` | `:72` | `:82` | **yes** |
| 4 | `tests/architectural/test_shared_module_object_patches.py` | `E402` | `:817` | `:827` | **yes** |
| 5 | `tests/architectural/test_shared_module_object_patches.py` | `PLC0415` | `:977` | `:987` | **yes** |
| 6 | `tests/architectural/test_patch_seam_census_control.py` | — | `:30` | `:30` | **NO — docstring prose** |

Cycle 1 recorded row 1 as `:~64`; measured, it is **`:68`** — the `~` was a guess and guesses do not
belong in a transcript. Rows 2–5 are `+10` on HEAD; row 6 and row 1 are unmoved.

**Row 6 is a false positive of the naive grep**, and it is this programme's own signature defect
(*"docstring prose cited as a pinning assertion through eight references"*). The line reads:

> ``…so: no ``sys.path`` insertion and no ``# noqa: E402`` anywhere in this file.``

It is prose asserting the **absence** of a suppression, and the assertion is **true** — confirmed:

```
$ grep -nE '^\s*[^#\s].*#\s*noqa' tests/architectural/test_patch_seam_census_control.py
                                        <-- no code-line hits; the only match is the docstring
```

**So the honest count is 5 added inline suppressions, not 6 and not 0.**

**Why this is nevertheless NOT an `SC-012` failure.** `SC-012`'s escape hatch is adding a
`per-file-ignores` entry or widening `exclude` **instead of** an inline `# noqa` — a *config*
suppression that `ruff check .` cannot see. Here the opposite happened: the implementers used the
**inline** form, which is the sanctioned direction, and the config half (§4c) is a **0-line diff**.
All five are narrow, rule-specific and individually justified — four are the identical
`sys.path`-bootstrap idiom the prompt itself names as legitimate and pre-existing (§4d), and the
fifth carries its rationale in the docstring directly above it:

```python
def _completed_owner() -> str:
    """A real owner token that `owner_is_complete` answers True for.

    Derived from the event log rather than hardcoded: a hardcoded WP id stops
    being complete the moment the mission is renumbered, and the twin would then
    silently stop testing anything.
    """
    from tests.architectural._inert_slots import (  # noqa: PLC0415
```

This satisfies `CLAUDE.md`'s rule verbatim — *"Narrowly-scoped, individually-justified suppressions
are allowed only when the check is genuinely wrong about correct code, and must carry an inline
rationale."* Filed as **`RL-049`** so the discrepancy between the prompt's prediction and the shipped
tree is on the record rather than silently reconciled.

### 4c — the config half, as diff TEXT (the escape hatch `SC-012` closes)

An existence check proves nothing here: both files **already carry** a `per-file-ignores` block before
this mission. The check must be diff-shaped:

```
$ git diff upstream/main -- ruff.toml pyproject.toml > /tmp/c012-config.diff 2>&1; wc -l /tmp/c012-config.diff
0 /tmp/c012-config.diff
```

The diff is **empty — zero lines**. Stated explicitly, as the two clauses the criterion requires:

1. **No `per-file-ignores` entry was added** to `ruff.toml` or to `pyproject.toml`.
2. **No `exclude` list was widened** in `ruff.toml` or in `pyproject.toml`.

Neither file is modified by this mission at all, so green lint is not being bought with a config
suppression. Both are `owned_files` of WP07 and their **invariance is the deliverable**.

### 4d — the legitimate inherited suppression — **the prompt's citation is wrong on path AND lines**

The prompt names `test_docs_cli_reference_parity.py:52-56` under `tests/docs/`. **Opened, per the
"open every line you cite" rule — it is not there.** The file lives under `tests/architectural/`, and
the suppressions are at `:55-56`, not `:52-56`:

```
$ find . -name test_docs_cli_reference_parity.py -not -path './.git/*'
./tests/architectural/test_docs_cli_reference_parity.py
```

`tests/architectural/test_docs_cli_reference_parity.py:50-58`, read this session, verbatim:

```python
# Ensure scripts/docs is importable (matches tests/docs/conftest.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs._typer_walker import walk  # noqa: E402
from scripts.docs.check_cli_reference_freshness import (  # noqa: E402
    extract_referenced_paths,
)
```

Pre-existing and load-bearing: the `sys.path` insertion must execute before the `scripts.` import can
resolve, which is exactly the ordering `E402` flags. **WP03 and WP05 copy this idiom** — the four
`E402` rows in §4b are the same three-line shape (`_REPO_ROOT` → `if not in sys.path` → `insert`, then
the import) — rather than introducing a new class of suppression. The prompt's claim about the *idiom*
is correct; only its `file:line` is wrong. Filed as **`RL-049`**.

### 4e — `mypy --strict` on the changed source file, with its pre-existing baseline control

```
$ ./.venv/bin/mypy --strict src/specify_cli/tracker/saas_client.py   # composed tree
src/specify_cli/tracker/saas_client.py:184: error: Returning Any from function declared to return "str | None"  [no-any-return]
src/specify_cli/tracker/saas_client.py:185: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)
EXIT=1
```

**CONTROL — the same check on the pre-mission file from `upstream/main`:**

```
$ git show upstream/main:src/specify_cli/tracker/saas_client.py > /tmp/mypyctl/base_saas_client.py
$ ./.venv/bin/mypy --strict /tmp/mypyctl/base_saas_client.py
/tmp/mypyctl/base_saas_client.py:162: error: Returning Any from function declared to return "str | None"  [no-any-return]
/tmp/mypyctl/base_saas_client.py:163: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)
```

Same count, same rule, same two adjacent returns — at `:162-163` pre-fix and `:184-185` post-fix. The
**22-line shift is exactly the seam block's height**, which is itself corroboration that nothing else
moved. **Pre-existing, not introduced; classified, not retried-to-green.** Already filed as `RL-015`;
not re-filed.

---

## §5 — `C-002`: the formatter was never run, with the twin that makes the proof non-vacuous

`grep -rc '<formatter invocation>' <notes>` returning `0` is **satisfied by writing no notes at all** —
an absent or empty file passes. The twin closes that.

```
$ NOTES=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/constraint-enforcement-3136.md
$ test -s "$NOTES" && echo "NON-EMPTY: $(wc -l < "$NOTES") lines"
$ grep -c 'command -v' "$NOTES"                                              # twin: must be >= 1
$ grep -rc 'ruff for''mat' kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/  # must be 0
```

**Per this file's measurement convention (top of file), the `wc -l` and `grep -c` results are NOT
frozen here** — they are about this file and would be false the moment it grew. Run the block above;
the criterion is:

| Check | Required | How it is guaranteed |
|---|---|---|
| `test -s "$NOTES"` | true, with a line count | §0 was written **first**, before any grep ran — non-empty by construction |
| `grep -c 'command -v' "$NOTES"` | **≥ 1** | §0 contains the literal `command -v` invocation |
| `grep -rc 'ruff for''mat' notes/` | **expected 0** | **MEASURED 3 — see §5b.** This file's own count is `0`; the three hits are other WPs' prose asserting the formatter was never run. The criterion is self-defeating as written |

> **Why the pattern is written `'ruff for''mat'` above.** The literal two-word string is the thing being
> searched for; writing it out in this file would make the mission's own notes match the probe and
> turn a real `0` into a spurious `1`. The shell concatenates the two quoted fragments into the exact
> literal at run time, so the command as written searches for the true pattern without this file
> containing it. This is a *probe-contamination* guard, not an evasion — and it is the same class of
> defect as the self-measuring block the convention at the top of this file forbids.

### 5b — MEASURED: the directory-wide grep is **3**, not 0 — and the criterion is self-defeating

Run for real, the criterion **does not pass**, and the reason is not that the formatter was run:

```
$ grep -rn 'ruff for''mat' kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/
notes/mechanism-gate-3136.md:218:  `ruff·format` was never run. The 2 skips (...)
notes/adr-and-lockfile-3136.md:388: ... so no `ruff` / `mypy` run applies. `ruff·format` was never
notes/alias-seam-3136.md:745:      `ruff·format` was **never** run, in this WP or anywhere near it.
                                     ^^^^^^^^^^^
     (the three quoted lines carry a MIDDLE DOT in place of the space, deliberately — see below)
$ grep -r 'ruff for''mat' <notes>/ | wc -l
3
$ grep -r 'ruff check' <notes>/ | wc -l
12                                  # CONTROL: the probe is wired
```

**All three hits are prose asserting the formatter was NEVER run** — WP02, WP04 and WP05 each wrote
that sentence into their own notes. **This file's own count is `0`.**

> **And keeping it at `0` took a second correction, which is worth recording.** The three lines above
> were first pasted **verbatim**, which put the literal into *this* file and silently falsified the
> very claim in the sentence before them — `grep -rl` then listed
> `constraint-enforcement-3136.md` alongside the other three. Caught by re-running the probe after
> writing, not by reading. They are now quoted with a **middle dot** (`·`) in place of the space, so
> the quotation is legible without matching the pattern. **This is the fourth instance of the same
> probe-contamination class in this one work package** (`RL-048`: the gate matching a docstring;
> `RL-049` item 4: the suppression grep counting a docstring; `RL-049` item 10: `C-002` matching three
> WPs' prose; and now this file matching its own quotation of them). The generalisation — *every
> text-matching probe needs an is-this-code predicate, and every probe must be re-run after the
> report that quotes it is written* — is the useful output, not any single fix.

**`C-002` as literally written is self-defeating.** It was rewritten to close a *vacuity* hole (an
absent or empty notes file passes). The rewrite introduced the mirror hole: **a WP that honestly
documents the constraint fails the check, and a WP that stays silent passes.** Both failure modes now
live in the same criterion.

**The substantive claim is nevertheless TRUE, and it is established by §5a rather than by the grep**:
the formatter was not run, evidenced by the touched-line distribution, which a reformat could not
produce. Filed as **`RL-049`** item 10. The criterion needs restating as, e.g., *"no notes file
records having **invoked** the formatter"* — a check on invocation transcripts, not on the string.

### 5a — the reformat check: touched-line counts, per file, against the declared work

```
$ git diff --stat upstream/main -- src/ tests/ > /tmp/c002-stat.txt 2>&1
```

| File | ± | Explicable by the declared work? |
|---|---|---|
| `src/specify_cli/tracker/saas_client.py` | +32 −10 | **Yes** — 27-line seam block, 5 removed jitter-def lines, 7 one-for-one call-site substitutions (§3) |
| `tests/sync/tracker/test_saas_client.py` | +48 −35 | **Yes** — the patch-target retargets; edited lines only |
| `tests/sync/tracker/test_saas_client_origin.py` | +1 −1 | **Yes** — a single retarget |
| `tests/sync/tracker/test_sleep_attribution_guard_3136.py` | +428 −0 | **Yes** — new file (WP02 guard) |
| `tests/architectural/test_shared_module_object_patches.py` | **+1020 −0** | **Yes** — new file (WP05 gate); `+1010` at anchor `b0312a438`, `+1020` on HEAD after `bf68b101b`'s 10-line docstring note |
| `tests/architectural/test_patch_seam_census_control.py` | +593 −0 | **Yes** — new file (WP03 control fixture) |
| `tests/architectural/_fixtures/patch_seam_control/*.py` (4 files) | +174 −0 | **Yes** — new control fixtures |
| `tests/architectural/_baselines.yaml` | +266 −0 | **Yes** — WP05's frozen baseline, appended |
| `tests/architectural/test_ratchet_baselines.py` | +90 −0 | **Yes** — WP05 ratchet registration |

**No file shows a large touched-line count without a reason to change**, and — the reformat signature —
**no file is touched that has no declared reason to be touched at all**. Every `−` line above belongs to
a file the mission declares it edits; the four largest entries are `−0`, i.e. pure additions. A
repo-wide reformat would have produced hundreds of `±` files here; the set is closed at the declared
surface. **`C-002` PASSES.**

---

## §6 — `C-010`: the terminology guard, run BEFORE push

The guard runs only in CI's `integration-tests-core-misc` job — **not** in any `fast-tests-*` shard. A
forbidden-term regression in WP04's ADR or WP06's inventory stamp therefore passes every local
doctrine run and reddens only at CI, after the PR is open. Run here **before** push, on the composed
tree, redirected with the exit status captured separately:

```
$ ./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q -ra -p no:cacheprovider
EXIT=0
$ tail -3 /tmp/c010.txt
..........                                                               [100%]
10 passed in 44.60s
```

**`EXIT=0`; `10 passed` quoted verbatim from the redirected file.** Not paraphrased as "it passed".

### Prose surfaces this guard covers on the composed tree

| Surface | Path |
|---|---|
| WP04's ADR | `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` |
| WP04's era index row | `docs/adr/3.x/README.md` |
| WP04's generated indexes | `docs/development/3-2-page-inventory.yaml`, `docs/development/3-2-docs-retrieval-index.yaml` |
| WP06's inventory verdict stamp | `docs/development/process-global-inventory-3115.md` |
| WP02's guard docstring | `tests/sync/tracker/test_sleep_attribution_guard_3136.py` |
| this mission's `AGENTS.md` / `ui-e2e.md` remediations | `AGENTS.md`, `docs/development/ui-e2e.md` |

Canonical terms this prose is most likely to trip: **`Mission`** not `feature`; **`status commit`**
not `ceremony`. The ADR's own body uses "the precedent this **Mission** had to clear first" — the
canonical form — which is one of the surfaces the guard passes over.

---

## §7 — How the composed tree under measurement was built

`spec-kitty merge` (lane consolidation) has **NOT** been run: it is the mission's terminus step, gated
behind WP07's own approval, and it deletes lane branches and worktrees. Running it from inside WP07
would consolidate a mission whose final WP is still in flight. Instead the PR branch was composed per
the canonical pr-landing recipe — branch from `upstream/main`, take content by slice:

| Source | Paths |
|---|---|
| `…-lane-b` (WP02) | `src/specify_cli/tracker/saas_client.py`, `tests/sync/tracker/{test_saas_client,test_saas_client_origin,test_sleep_attribution_guard_3136}.py` |
| `…-lane-c` (WP03) | `scripts/{check_patch_targets,patch_seam_census}.py`, `tests/architectural/_fixtures/patch_seam_control/**`, `tests/architectural/test_patch_seam_census_control.py` |
| `…-lane-d` (WP04) | `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` (ADR body only) |
| `…-lane-e` (WP05) | `tests/architectural/{test_ratchet_baselines,test_shared_module_object_patches}.py` |
| `…-lane-f` (WP06) | `docs/development/process-global-inventory-3115.md` |
| `feat/…` | `AGENTS.md`, `docs/development/ui-e2e.md` (the `RL-004` / `RL-013` remediations) |

**The lanes agree byte-for-byte on every shared file**, so the composition is unambiguous rather than
a choice between versions:

```bash
for l in b d e; do git rev-parse "kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-$l:src/specify_cli/tracker/saas_client.py"; done
# -> the same blob sha three times
```

### Three files were NOT taken wholesale, because upstream had moved them

Taking the lane copy would have **silently deleted upstream's own additions** — the exact
silent-clobber failure mode this mission exists to close. Each was integrated instead:

| File | Why | How |
|---|---|---|
| `tests/architectural/_baselines.yaml` | upstream added a `test_verdict_seam_census` section (+59/−3) | 3-way merge (`git merge-file`), one append/append conflict resolved by keeping **both** sections; result is **+266/−0** vs upstream — pure addition, nothing of upstream's dropped |
| `docs/adr/3.x/README.md` | upstream added two ADR rows | 3-way merge; result **+1/−0** — WP04's row only |
| `docs/development/3-2-page-inventory.yaml`, `…/3-2-docs-retrieval-index.yaml` | generated lockfiles; upstream regenerated them | **regenerated against the new base** with the canonical generators, not re-applied: `scripts/docs/inventory_lockfile.py --write`, `scripts/docs/docs_index.py --write`. Results **+6/−0** and **+22/−0** — exactly the one new ADR |

Docs gate on the result:

```
$ ./.venv/bin/python scripts/docs/check_docs_freshness.py --ci
check_docs_freshness: exit=0 findings=3 errors=0 warnings=3      # EXIT=0; 3 warnings are link-health network probes
```

---

## §8 — Full-suite classification: `tests/architectural/` on the composed tree

```
$ ./.venv/bin/python -m pytest tests/architectural/ -q -ra -p no:cacheprovider -n auto --dist loadfile
ARCH_EXIT=1
2 failed, 1778 passed, 5 skipped, 2 xfailed, 1 warning in 769.03s (0:12:49)
```

**Neither failure is retried-to-green. Both are classified.**

### 8a — `test_inline_meta_read_gate.py::test_routed_load_meta_floor` — category (a), PRE-EXISTING

```
E   AssertionError: ROUTED_LOAD_META_FLOOR (128) is more than ROUTED_LOAD_META_FLOOR_MARGIN (4)
    below the live routed count (133); tighten the floor.
```

**Reproduced on a pristine `upstream/main` worktree** (the attribution step `CLAUDE.md` mandates):

```
$ git worktree add --detach <scratch>/pristine upstream/main      # 709a59534
$ PYTHONPATH=<scratch>/pristine/src ./.venv/bin/python -m pytest \
    tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor -q -ra
PRISTINE_EXIT=1
FAILED tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor
1 failed in 66.42s
```

**Red on the base, red on the branch ⇒ not this mission's.** Corroboration: this mission does not
touch the file (`git diff upstream/main -- tests/architectural/test_inline_meta_read_gate.py` is
empty) and every routed site in the failure's own list is under `src/mission_runtime/` or
`src/runtime/next/`, cones this mission never edits. Filed as **`RL-047`**. **Not fixed here** — an
upstream floor is the upstream owner's to tighten.

### 8b — `test_ratchet_baselines.py::test_no_unregistered_baseline_keys_are_added` — a genuine INTEGRATION CROSSING

```
E   AssertionError: `_baselines.yaml` carries top-level key(s) no comparison reads:
    ['test_verdict_seam_census'].
```

This is neither a WP05 defect nor an upstream defect. It exists **only in composition**, and it is
precisely what WP07 is for. Both halves measured on the pristine base:

```
$ grep -c "test_no_unregistered_baseline_keys_are_added" <pristine>/tests/architectural/test_ratchet_baselines.py
0        # the guard is WP05's — it does not exist upstream
$ grep -c "^test_verdict_seam_census:" <pristine>/tests/architectural/_baselines.yaml
1        # the key is upstream's — WP05 never saw it
```

WP05 built a guard that refuses any `_baselines.yaml` top-level key no comparison reads; upstream then
added exactly such a key, from mission `review-cycle-verdict-seam-rebuild-01KZ2W7W`. Composition puts
them in the same tree for the first time.

**WP07 deliberately does NOT resolve this, and the reason is WP05's own recorded reasoning.** The two
available moves are both refused here:

1. **Register it** in `_REQUIRED_TOP_LEVEL_KEYS` and both `single_baselines` lists. That makes *this*
   mission's gate start enforcing a ratchet **owned by another mission**. WP05 already faced this
   question for `test_no_dead_symbols` and recorded the answer at
   `tests/architectural/test_ratchet_baselines.py:142-148`, opened and quoted:

   > *"choosing between its two honest dispositions … needs the owner of the gate it governs, which is
   > outside mission `sync-sleep-count-3136-01KZ9B5A`'s scope to decide unilaterally."*

   That reasoning applies verbatim to `test_verdict_seam_census`.
2. **Grandfather it** into `_GRANDFATHERED_UNREGISTERED_KEYS`. Structurally refused by WP05's design:
   the set is pinned by **frozenset equality** at `:579`, declared CLOSED and shrink-only, so widening
   it fails the assertion immediately above the one being worked around.

Filed as **`RL-046`** with both dispositions and their owners. It is surfaced in the PR body as a
**known red requiring the gate owner's ruling**, not hidden and not worked around. Per `DIR-041`, an
`xfail` or a widened tolerance here would mask a real defect and is refused.

### 8c — the rest of the board

`5 skipped`, `2 xfailed`, `1 warning` — all pre-existing and self-documenting (the two `xfail`s carry
`#3113`'s FR-015 non-adoption rationale in their own reason strings; one skip is WP05's anti-weasel
twin, which self-reports *"re-run once a dependency is approved"*). None is this mission's to act on.

---

## §9 — `C-001` window arms taken by WP07 (all BEFORE the release in T043)

`^ERROR tests/` — **not** `^ERROR ` — is the counted pattern, and `-ra` is used, never `-rf`.

### 9a — `NFR-005` comparison arm (`SC-014`: same command, same interpreter)

| Arm | Ref | Command | Result | Interpreter |
|---|---|---|---|---|
| **base** (WP01 · T003) | `98198e980` | `tests/sync/tracker/ -m "fast and not windows_ci" -n0 -q -p no:cacheprovider` | `461 passed, 11 deselected, 1 warning in 66.54s`, `EXIT=0` | `Python 3.12.13` |
| **comparison** (WP07) | composed tree | same | `466 passed, 11 deselected, 1 warning in 50.17s`, `EXIT=0` | `Python 3.12.13` |

**Both interpreters `3.12.13` — identical, as `SC-014` requires.** `^ERROR tests/` = **0** on the
comparison arm.

**The `+5` delta is fully accounted for**, not hand-waved: WP02's guard file contributes exactly five
nodes, measured directly rather than inferred —

```
$ ./.venv/bin/python -m pytest tests/sync/tracker/test_sleep_attribution_guard_3136.py \
    -m "fast and not windows_ci" -n0 -q -ra -p no:cacheprovider
GUARD_EXIT=0
5 passed in 47.35s
```

461 + 5 = 466. (The file's docstring describes *ten arms, five rows × two*: five test **functions**,
each carrying an (a) and a (b) arm.)

### 9b — the four targeted nodes, INDIVIDUALLY (kept separate from any job aggregate)

| Node | `EXIT` | Result |
|---|---|---|
| `test_saas_client.py::TestPolling::test_exponential_backoff_intervals` | 0 | `1 passed in 44.91s` |
| `test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` | 0 | `1 passed in 57.81s` |
| `test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing` | 0 | `1 passed in 46.25s` |
| `test_saas_client.py::TestPolling::test_timeout_after_5_minutes` (the **census** node) | 0 | `1 passed in 46.26s` |
| `test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises` (the CI victim) | 0 | `1 passed in 58.77s` |

The census node is `TestPolling::test_timeout_after_5_minutes`, whose exact-list stimulus
`mock_monotonic.side_effect = [0.0, 301.0]` sits at **`:817`** on the composed tree — **not `:804`**,
which is the pre-retarget line number the WP07 prompt cites (`RL-049`; same class as `RL-011`).

### 9c — `C-003`: the out-of-scope leak `ERROR`s

The `#3130` / `#3193` leak `ERROR`s are **pre-existing and excluded**; they are **not** this mission's
failures and were not "fixed". On the comparison arm they surface not as errors at all but as **12
nodes pinned in `tests/sync/conftest.py`**, which the leak guard prints as *"a TEMPORARY pin on a
verified defect, not a permanent exemption"*. `grep -c '^ERROR tests/'` on that run = **0**.

### 9d — no `tests/cli` run overlapped

**WP07 did not run `tests/cli` at any point.** Every `tests/sync` selection above is either the single
`tests/sync/tracker/` cone arm or a targeted node-id / single-file selection. `tests/sync/test_orphan_sweep.py`
(ports 9400–9449) was never selected.

### 8d — `check_patch_targets.py` reddens on WP05's docstring — category (d), THIS MISSION'S

This did not appear in the `tests/architectural/` run above because the gate is a **standalone CI
step**, not a pytest node: `.github/workflows/ci-quality.yml:884` runs
`uv run python scripts/check_patch_targets.py`, which defaults to scanning `tests/`.

**Control first — pristine `upstream/main` is green:**

```
$ PYTHONPATH=<pristine>/src:<pristine> ./.venv/bin/python scripts/check_patch_targets.py tests
All 5065 patch() targets valid.                    EXIT=0
```

**Composed tree is red:**

```
$ PYTHONPATH=<prwt>/src:<prwt> ./.venv/bin/python scripts/check_patch_targets.py tests
::error::Broken patch() targets (1 of 5087 checked):
  tests/architectural/test_shared_module_object_patches.py:5: cannot import any prefix of 'a.b.c'
EXIT=1
```

The "target" is **docstring prose** at `:4-5` explaining the mechanism (``patch("a.b.c.attr")``), and
`extract_targets` is a **regex over raw source** (`scripts/check_patch_targets.py:70-80`) with no AST
awareness. The file is new in this mission, so this is **attributable to this diff**. Filed as
**`RL-048`** with both fix shapes and their owners; **not fixed here** — both files are other WPs'
approved `owned_files`, and choosing between a gate change and a prose change is a design decision.

> **The `PYTHONPATH` ordering matters and is itself a classification trap.** Run as
> `PYTHONPATH=<prwt>` (without `/src` first), the gate reports **five** failures of the form
> `'specify_cli.tracker.saas_client' has no attribute '_sleep'` — because the repo-root editable
> `.pth` wins and `specify_cli` resolves to the **feat** tree, which has no alias. That is a
> **category (c) stale-install false red**, not a defect. Verified:
> ```
> PYTHONPATH=<prwt>      -> /home/jeroennouws/dev/sk-missions/3136/src/specify_cli   # WRONG tree
> PYTHONPATH=<prwt>/src:<prwt> -> <prwt>/src/specify_cli                             # RIGHT tree
> ```

---

## §10 — T042: the filings register

**`gh issue create` is BARRED** for this programme by operator direction (2026-08-06), and the
orchestrator's ruling at the head of `residual-ledger.md` settles `DIR-013` against it: the directive
is **satisfied, not waived**, by an `RL-###` entry carrying what the issue body would have carried.
**No issue number is invented, guessed or reserved anywhere in this WP.**

Every filing below is verified by its `RL-###` id **and its heading line quoted from
`residual-ledger.md`** — the substitute the amended T042 prescribes for the `gh issue view` quote.
Ids come from WP07's **reserved block `RL-040`…`RL-049`**, never from the running maximum.

| Filing | Id | Heading line, quoted from `residual-ledger.md` |
|---|---|---|
| **1** — seam displacement | `RL-040` | `## RL-040 — seam displacement: an in-body `mock.side_effect` reassignment is structurally outside the shipped predicate (2026-08-07)` |
| **2** — the `batch.py` residue | `RL-041` | `## RL-041 — the `batch.py` residue: thread the EXISTING keyword argument; do NOT add an alias seam (2026-08-07)` |
| **3** — exact-list clock stimuli | `RL-042` | `## RL-042 — exact-list clock stimuli: a `StopIteration` sub-class the read-side predicate does not reach (2026-08-07)` |
| **4** — residue outside arm 4's scope | `RL-043` | `## RL-043 — the residue outside arm 4's `saas_client.py`-only scope; widen the seam check to all of `src/specify_cli/` (2026-08-07)` |
| **5** — newly-found untracked instances | `RL-044` | `## RL-044 — newly-found process-global instances with no tracker item (2026-08-07)` |

WP07's own findings, same block:

| Id | Heading line, quoted from `residual-ledger.md` |
|---|---|
| `RL-045` | `## RL-045 — the mission's code was not on `feat/`; lane consolidation had not run when WP07 opened (2026-08-07)` |
| `RL-046` | `## RL-046 — integration crossing: upstream's `test_verdict_seam_census` key vs WP05's closed registration guard (2026-08-07)` |
| `RL-047` | `## RL-047 — pre-existing upstream red: `test_routed_load_meta_floor` (2026-08-07)` |
| `RL-048` | `## RL-048 — `check_patch_targets.py` reddens on WP05's DOCSTRING: a mission-attributable CI regression (2026-08-07)` |
| `RL-049` | `## RL-049 — WP07 prompt figures and citations that do not survive measurement (2026-08-07)` |

Reproduce the register and its no-duplicate property:

```bash
grep -nE '^## RL-04[0-9]' kitty-specs/sync-sleep-count-3136-01KZ9B5A/residual-ledger.md
grep -oE '^## RL-[0-9]+' kitty-specs/sync-sleep-count-3136-01KZ9B5A/residual-ledger.md | sort | uniq -d   # empty
```

**Filing 2's required wording, present verbatim in `RL-041`:** *"THE FIX IS TO THREAD THE EXISTING
PARAMETER at `background.py:467` — NOT to add an alias seam."* `RL-041` does **not** propose an alias
seam anywhere.

**Filing 1's `N`-in / `M`-out is in `RL-040`** with the predicate printed beside the number, the
`N−M` drop enumerated by recorder name, the per-file breakdown, and a reproduction shape.

---

## §11 — `C-006`: the register of what is SETTLED and NOT re-opened

The following are **settled**. WP07 does not re-litigate them, and a successor reading this file
should not either:

| Settled item | Status |
|---|---|
| **The mechanism** — `patch("<module>.<stdlib>.<attr>")` rebinds the attribute on the **shared stdlib module object**, so the recorder is process-global | **SETTLED** — not re-opened |
| **The named producer** — `subprocess.Popen._wait`'s capped doubling loop | **SETTLED** — not re-opened |
| **The psutil structural exclusion** | **SETTLED** — not re-opened |
| **The `restart.py:147` / `daemon.py:1382` falsifications** | **SETTLED** — not re-opened |

**Exactly two code facts were re-verified, and nothing else** — both because the shipped tree is the
one that must carry them, not the tree the claim was first made against:

1. `saas_client.py:19` — the bare `import time` that makes the reach-through possible. Confirmed
   present on the composed tree (§0 of `notes/alias-seam-3136.md` is WP02's record; WP07 re-read the
   import block at `:15-25`).
2. **The patch-decorator census** — re-derived via the shipped gate and the AST, not restated: the
   aliases are `ast.Assign` at `:58-60` (§3b), and the gate's flagged set is the 22-row baseline
   broken down in `RL-043`.

**What IS newly opened** is exactly the ten entries in §10 — five T042 filings and five WP07 findings —
each by `RL-###` id, none by an invented issue number.
