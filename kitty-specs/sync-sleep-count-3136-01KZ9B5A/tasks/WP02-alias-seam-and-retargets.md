---
work_package_id: WP02
title: Guard first (red), then the module-local alias seam, the 24 patch-target retargets, the dead seam and the false docstring
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-003
- FR-004
- FR-006
- FR-007
- FR-010
- FR-012
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-004
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
- T013
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/saas_client.py
create_intent:
- tests/sync/tracker/test_sleep_attribution_guard_3136.py
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/saas_client.py
- tests/sync/tracker/test_saas_client.py
- tests/sync/tracker/test_saas_client_origin.py
- tests/sync/tracker/test_sleep_attribution_guard_3136.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Guard first (red), then the module-local alias seam, the 24 patch-target retargets, the dead seam and the false docstring

> **NOTE: This WP is 820 lines, over the 700-line ceiling — and it is NOT to be split.**
> The natural split is to lift the corruptibility guard (T005) out into its own WP.
> `plan.md`'s BLOCKER-4 forbids exactly that: the guard is the red-first proof for the
> seam change in the same WP, and separating them lets the seam land without a live
> red-then-green. The overage is a deliberate, recorded trade, not an oversight —
> the sizing rule loses to the red-first rule. If a future reader wants to shrink
> this file, compress prose; do not move T005.

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter — `agent_profile: python-pedro`, `role: implementer`, `agent: claude` —
and behave according to its guidance before parsing the rest of this prompt.

If the skill cannot resolve the profile, run `spec-kitty agent profile list` and
select the best match for this work package's `role` and `authoritative_surface`
(`src/specify_cli/tracker/saas_client.py` — a Python production module).

---

## Objective

Start with:

```
spec-kitty implement WP02
```

Make the sleep-count assertions in `tests/sync/tracker/` structurally unable to observe another
thread's `time.sleep`, by giving `src/specify_cli/tracker/saas_client.py` three **module-scope
aliases bound by assignment** — `_sleep = time.sleep`, `_monotonic = time.monotonic`,
`_randbelow = secrets.randbelow` — rerouting the five call sites through them, and **retargeting
the 24 existing `patch()` decorators onto the aliases**. Resolve the dead `_poll_jitter_multiplier`
seam in the same change, and correct the false docstring claim at `test_saas_client.py:55-57`.

The ATDD guard (`tests/sync/tracker/test_sleep_attribution_guard_3136.py`) is this WP's **first
commit**, and it is **RED on `98198e980`**. Everything else follows it. This is the mission's largest
work package and it **must not be split** — see `## Context`.

## Context

Read before starting: `plan.md` `### IC-02`, `## Project Structure`, `### Atomicity couplings`,
`## Technical Context`; `spec.md` `### The 24 patch-target retargets`, `### Charter red-on-base`,
`FR-010`, `FR-012`, `C-004`, `SC-003`–`SC-005`, `SC-007`, `SC-013`; `analysis-report.md`'s
**post-plan `BLOCKER-1`** — that finding is why this WP has the shape it has. Load
`.kittify/charter/charter.md`.

### The trap that defines this WP, and why the form is ASSIGNMENT

`_sleep = time.sleep` at module scope binds the **function object at import time**. Therefore
`@patch("specify_cli.tracker.saas_client.time.sleep")` — which rebinds the attribute on the shared
stdlib `time` **module object** — **cannot reach `saas_client._sleep`**. The property that makes the
seam work is the same one that makes every existing decorator miss it.

**So the 24 retargets are the fix, not housekeeping.** Without them the seam does nothing: the
recorder each assertion reads is still the process-global one. `analysis-report.md`'s post-plan
BLOCKER-1 found that in all three lenses independently — the edit that *constitutes* the fix had no
owner, because operator ruling R-1 was recorded as *"makes every existing assertion correct
unchanged"*: true of the assertion **text**, false of the patch **target**.

| Alias form | Decorator target | Recorder sees | Verdict |
|---|---|---|---|
| assignment (`_sleep = time.sleep`) | `…_sleep` (retargeted) | `3` | **immune — this is the fix** |
| assignment | `…time.sleep` (un-retargeted) | **`0`** | **fails LOUDLY** — cannot be shipped |
| wrapper (`def _sleep(s): time.sleep(s)`) | `…_sleep` (retargeted) | `3` | immune at runtime, live `time.sleep` lookup retained |
| wrapper | `…time.sleep` (un-retargeted) | **`3`** | **passes SILENTLY, defect 100% intact** |

Under assignment, skipping the retargets is **impossible to ship**; under a wrapper it is
**invisible**. Be precise about *why* the wrapper is refused: a wrapper **with all 24 retargets
complete is genuinely runtime-immune**. It is refused because it (i) keeps a live `time.sleep` lookup
inside the module, re-admitting the reach-through the moment any future code or missed decorator reads
it, and (ii) destroys the self-enforcing property above. The refusal is structural (`SC-007` arm
**4b**: `ast.Assign`, not `ast.FunctionDef`) by necessity, not preference.

### The inventory — re-derived this session, every line opened

Derived with `grep -oEn 'patch\("specify_cli\.tracker\.saas_client\.[^"]+"' <both files>` and then
opening each line. The `secrets.randbelow` site does **not** appear in that grep because its `@patch(`
opens on `:498` and the target string is on `:499`.

All targets are prefixed `specify_cli.tracker.saas_client.`; the table drops the prefix.

| File | Pre-fix → post-fix | Live | Lines |
|---|---|---|---|
| `test_saas_client.py` | `time.sleep` → `_sleep` | **13** | `:385`, `:412`, `:467`, `:502`, `:789`, `:809`, `:899`, `:939`, `:959`, `:1087`, `:1128`, `:1152`, `:1319` |
| `test_saas_client.py` | `time.monotonic` → `_monotonic` | **9** | `:386`, `:413`, `:468`, `:503`, `:790`, `:810`, `:1088`, `:1129`, `:1153` |
| `test_saas_client.py` | `secrets.randbelow` → `_randbelow` | **1** | `:499` — the **target string**; the `@patch(` spans `:498`–`:501` |
| `test_saas_client_origin.py` | `time.sleep` → `_sleep` | **1** | `:229` |

**Prose, NOT a retarget — TWO occurrences, not one.** `test_saas_client.py` carries the pre-fix string
at **`:559` AND `:715`**, both inside the `:513`–`:762` docstring of
`test_exponential_backoff_intervals` (boundary lines and both occurrences opened this session).
`:715` carries the bare dotted string with **no `patch("` prefix**, which is why the spec's own
re-derivation command — anchored on `patch\("` — cannot see it, and why every inherited count in this
mission was one short. Update **both**; neither is one of the 24 and neither may be counted by any
decorator-count arm.

**Arithmetic:** `13 + 9 + 1 = 23` live in `test_saas_client.py`, `+ 1` in `test_saas_client_origin.py`
= **24 live retargets**, plus **2** prose occurrences = **26 string occurrences**.

**Anticipate the naive count.** `grep -c 'saas_client\.time\.sleep' tests/sync/tracker/test_saas_client.py`
returns **15**, not 13 — `:559` and `:715` (re-measured; `grep -n` prints both). That is exactly why
`SC-007` arm **4c** counts from AST `patch()` call nodes. **Arm 4c's post-fix `_sleep` figure is
`13 + 1 = 14`, where `13` is `test_saas_client.py`'s decorators and `+ 1` is
`test_saas_client_origin.py:229` — both AST, docstrings excluded.** Same reading as `WP03` T020 step 4
and `WP05` T027 step 1 / T028 step 2; **there is no third meaning of `14` in this mission**. The two
prose occurrences belong to the *string* total and to **neither** decorator total. Do not reconcile
the string and decorator numbers by editing prose to satisfy a numeric gate — that is the failure mode
this mission has already hit three times.

### The guard goes FIRST — and it CANNOT be its own work package

`charter.md:504` opens `## ATDD-First Discipline (binding per C-011)`; `:509` prescribes the ATDD test
as *"a separate commit (often the first commit of the lane) **BEFORE** any implementation commits"*;
`:512-513` reads *"The reviewer verifies red→green: the test was RED on the WP's
`planning_base_branch` AND GREEN on the WP's final commit."* (all opened this session).

A guard-only WP's final commit is red by construction, so it never reaches `approved`; and
`_SATISFYING_DEPENDENCY_LANES` (`src/specify_cli/core/dependency_graph.py`) is
`(Lane.APPROVED, Lane.DONE)`, so the alias WP could never be claimed. That is `plan.md`'s BLOCKER-4
deadlock. **Coupling E** is the mission's only genuine commit-level constraint; its verifier is a
human reading `git log`.

### The guard commit reddens a SECOND enforced gate — name it so nobody reads it as breakage

`scripts/check_patch_targets.py` runs at `ci-quality.yml:883-884` as `[ENFORCED] Validate patch()
target strings (closes #394)`, invoked **with no arguments** — and `main(argv)` (`:126-127`) defaults
its roots to `[Path("tests")]`, so it scans **every** `patch()` target string under `tests/`. On the
base tree `_mock_importer` (`:80`) returns
`(None, "no attribute '_sleep' in 'specify_cli.tracker.saas_client'")` — likewise `_monotonic` and
`_randbelow` — while `…saas_client.time.sleep` still resolves to `<built-in function sleep>` (the
control). So the guard commit reds **the lint job as well as the sync shard** for the whole window
between it and the alias commit. Both reds are **expected, attributable and positive evidence**: a
retarget that did not change the resolved object would not move this gate. Record both in the WP notes.
`[UNVERIFIED]` The exact `AttributeError` text `unittest.mock.patch` raises at setup on `98198e980` —
the *fact* of the red is structural, the message string is not. **Record the observed text.**

### ⚠️ ENVIRONMENT — read before running anything

**NEVER run a bare `uv run`.** It re-solves against the tracked `.python-version` (`3.11.15`),
**destroys `.venv`**, and drops `pytest` / `ruff` / `mypy`. **Three occurrences in this mission.**
Proof: `uv sync --dry-run --python 3.12` → `Would uninstall 70 packages`; the same command
`--extra test --extra lint` → `Would make no changes`. Root cause: those tools live only in
`[project.optional-dependencies]` (`pyproject.toml:100`) and in **two different extras** — `pytest` in
`test` (`:101-115`), `ruff` and `mypy` in the separate `lint` group (`:116-125`; `ruff` **`:117`**,
`mypy` **`:118`**). **Both** extras are required; one alone strips half the toolchain. CI survives only
because every job runs `uv sync --frozen --all-extras` first (`ci-quality.yml:1145`).

```bash
./.venv/bin/python -m pytest … ; ./.venv/bin/ruff check …    # Form 1 (preferred) — no resolve
uv run --python 3.12 --extra test --extra lint python -m …   # Form 2 — extras pinned
uv sync --python 3.12 --extra test --extra lint              # RECOVERY if .venv is destroyed
export PATH="$PWD/.venv/bin:$PATH"   # ~/.local/bin/* is an UNRELATED checkout and comes first
command -v python pytest ruff mypy   # all four must be under <repo>/.venv/bin
```

**A transcript without the `command -v` line is not evidence.** Verified healthy when this WP was
written: 3.12.13 / 9.0.3 / 0.15.12 / 1.20.2, all resolving inside `.venv`.

### This WP's notes file — named, and its OWN

Every "record it in the WP notes" in this prompt means exactly one path:

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/alias-seam-3136.md
```

It is a **declared out-of-map planning write** (`wps.yaml`'s WP02 block) — `owned_files` may not carry
any path under `kitty-specs/`. **Create it before the first command runs**, writing the `command -v` /
`--version` block into it first so it is non-empty by construction.

**Do NOT write into `notes/constraint-enforcement-3136.md`.** An earlier revision routed T012's
determinism transcripts there; that file is **WP07's**, has exactly one writer, and **WP07 runs after
WP02** — so WP02's evidence had no home at WP02 time. WP07 T037 reads `alias-seam-3136.md` and may
quote it into the constraint register. The write direction is one-way.

### Discipline (binding for every subtask)

- **Do NOT run `tests/sync` or `tests/cli` as sweeps.** WP01 owns the C-001 `tests/sync` window and
  the handshake; run **targeted node ids only** and name which ones you ran.
- **Redirect suite output, never pipe** (piping loses the exit code): `… -q -ra > /tmp/x.txt`, then
  quote the `N passed` line and print the selected count. Use `-ra`, **never** `-rf`.
- **`ruff check` only. Never `ruff format`.** A reformat shows up as a large touched-line count in
  files you had no reason to touch, and fails the diff-shape arm.
- **Complexity ceiling 15** (`pyproject.toml:287`, `max-complexity = 15`). Run
  `./.venv/bin/ruff check --select C901 <file>` **pre and post** for each touched file. Measured
  today across all three existing files: `All checks passed!`.
- **`C-004` permits an enumerated set of hunks in `saas_client.py`** — the alias definitions, the five
  call-site reroutes, and the `_poll_jitter_multiplier` resolution. The diff must show **only** those.
  Retry **behaviour** — delay values, call cardinality, raise conditions — unchanged.
- **A cited `file:line` is not evidence that the line says what the citation claims.** Open every one
  before acting on it.

---

### Subtask T005 — FIRST COMMIT: author the guard, red on `98198e980`

**Purpose.** Ship the red-first evidence as a live command rather than a transcript (FR-003), and
establish the base-branch red the reviewer verifies (`charter.md:512-513`). This commit precedes
every implementation commit (coupling E).

**Steps.**
1. Create `tests/sync/tracker/test_sleep_attribution_guard_3136.py` with module-level
   `pytestmark = [pytest.mark.fast]`. **The marker is load-bearing twice**: without `fast` the guard
   never runs in CI's `fast-tests-sync` (`-m "fast and not windows_ci"`, `ci-quality.yml:1161-1172`),
   **and** it becomes a gate-coverage orphan against `_gate_coverage_baseline.json`, whose
   `orphan_files` is `[]` and `orphan_test_count` is `0` (both re-measured), so `test_gate_coverage.py`
   reds on any new orphan file.
2. **Arm (a) × 5 — invariance.** For each census assertion, the hardened assertion's verdict is
   unchanged while a probe thread is inside a `time.sleep` loop.
3. **Arm (b) × 5 — the literal pre-fix expression**, evaluated against the **stdlib `time.sleep` mock
   patched in the same window as the alias mock** (step 4's `stdlib_mock`), raises `AssertionError`.
   **Not** against arm (a)'s alias recorder — post-fix that recorder sees exactly `3 / 1 / 1 / 1`, so
   every arm-(b) expression would **pass rather than raise** and the arm would grade nothing.
   `spec.md:667-668` is the binding half: *"arm (b) evaluates the pre-fix expression against the
   **stdlib**-polluted view"*. It must be the literal pre-fix form, diffable against `98198e980`,
   never a paraphrase:

   | # | Census assertion | Arm (b) expression |
   |---|---|---|
   | 1 | `test_saas_client.py:784` `assert len(sleep_calls) == 3` | `len(mock.call_args_list) == 3` |
   | 2 | `test_saas_client.py:786` `assert delays == [0.9, 2.0, 4.4]` | `[c.args[0] for c in mock.call_args_list] == [0.9, 2.0, 4.4]` |
   | 3 | `test_saas_client.py:937` `mock_sleep.assert_called_once_with(3.0)` | `mock.assert_called_once_with(3.0)` |
   | 4 | `test_saas_client.py:957` `mock_sleep.assert_called_once_with(5.0)` | `mock.assert_called_once_with(5.0)` |
   | 5 | `test_saas_client_origin.py:261` `mock_sleep.assert_called_once_with(2.0)` | `mock.assert_called_once_with(2.0)` |

   All five lines opened and confirmed this session. Row 2 is the one R1 omitted, and it is the member
   most likely to be "hardened" while still reading the unfiltered recorder.

   **State the mutual dependency with step 4 in a comment on the arm.** Arm (b) raises *because* the
   probe polluted the stdlib view — so **a probe landing 0 calls makes arm (b) pass instead of raise,
   which reddens the guard** (`spec.md:668-669`). That is what makes a vacuous probe structurally
   impossible rather than merely discouraged. Arm (b) and step 4's floor are one instrument.
4. **SC-005's two probes — two mocks in ONE window.** Patch **both** stdlib `time.sleep` **and**
   `specify_cli.tracker.saas_client._sleep` inside a single window, run the production call plus the
   probe thread, then assert in the same body: `stdlib_mock.call_count >= 100` (the probe's volume,
   read off a **recorder**, not a self-report — NFR-001; 100 is 4× below the predecessor's observed
   399 and `100/28 = 3.57×` above the smallest observed CI recorder total); and
   `alias_mock.call_count == <expected>` (the exact attributed cardinality, `3 / 1 / 1 / 1` across
   SC-004's five rows, read off the recorder the assertion actually uses).

   **State the scope honestly in a comment.** This catches **incomplete-retarget** trees: an
   un-retargeted decorator patches the shared `time` module, so the probe's foreign calls land on the
   very recorder the assertion reads and `alias_mock.call_count` reports the injected volume instead of
   `<expected>`. It does **not** catch a **fully-retargeted wrapper**, which is runtime-immune. **Arm 4b
   is the wrapper defence; the two are not interchangeable** — an earlier draft claimed otherwise and
   was wrong.
5. Gate every probe spawn on a `threading.Event` set after the probe's first recorded call, and
   **join every probe in a `finally`** (NFR-004). Print the per-row `stdlib` and `alias` counts, the
   probe thread name, and the five row identifiers so a reviewer can count them.
6. **Commit the guard alone.** Then record both reds on `98198e980`:
   - the sync shard — `patch("…saas_client._sleep")` cannot be set up; **record the observed
     `AttributeError` text**;
   - `./.venv/bin/python scripts/check_patch_targets.py` — `no attribute '_sleep'` for all three
     alias targets.

**Files.** `tests/sync/tracker/test_sleep_attribution_guard_3136.py` (new).

**Validation.**
```
./.venv/bin/ruff check tests/sync/tracker/test_sleep_attribution_guard_3136.py
./.venv/bin/ruff check --select C901 tests/sync/tracker/test_sleep_attribution_guard_3136.py
```

**Reach the base tree with a THROWAWAY DETACHED WORKTREE — never by checking out in place.**
`git stash && git checkout 98198e980 -- .` materialises base content over the **entire** worktree —
`kitty-specs/`, all seven prompts, every lane file — and nothing restores it. Copy WP01 T003's idiom
exactly:

```bash
R=/home/jeroennouws/dev/sk-missions/3136 ; B=/tmp/wp02-base-98198e9
git -C "$R" worktree add --detach "$B" 98198e980
git -C "$B" rev-parse HEAD                      # must print 98198e980045752a…
cp "$R"/tests/sync/tracker/test_sleep_attribution_guard_3136.py "$B"/tests/sync/tracker/
cd "$B"
PYTHONPATH="$B/src" "$R"/.venv/bin/python -c "import specify_cli; print(specify_cli.__file__)"
PYTHONPATH="$B/src" "$R"/.venv/bin/python -m pytest \
  tests/sync/tracker/test_sleep_attribution_guard_3136.py -q -ra -p no:cacheprovider \
  > /tmp/wp02-t005-base.txt 2>&1 ; echo "EXIT=$?"
PYTHONPATH="$B/src" "$R"/.venv/bin/python scripts/check_patch_targets.py \
  > /tmp/wp02-t005-targets-base.txt 2>&1 ; echo "EXIT=$?"
cd "$R" && git worktree remove --force "$B" && git worktree list   # ALWAYS clean up
```

As in WP01 R5: if `specify_cli.__file__` does not sit under `$B/src`, the arm is **invalid** — record
that and resolve it before reporting a number.

Expected on base: guard **RED** (`AttributeError` at patch setup — text recorded verbatim) and
`check_patch_targets.py` **non-zero exit** naming all three alias targets. Quote both, and quote the
`git worktree list` line proving the throwaway was removed.

---

### Subtask T006 — the three module-scope aliases, by assignment

**Purpose.** Give `saas_client.py` a module-local attribute surface that `patch()` can bind and that
another thread structurally cannot reach (FR-010 conditions i–iv, `SC-007` arm 4b).

**Steps.**
1. `saas_client.py:18` is `import secrets` and `:19` is `import time` (both opened). Add, at module
   scope, near the imports and **above** `_poll_jitter_multiplier` at `:104`:
   ```python
   _sleep = time.sleep
   _monotonic = time.monotonic
   _randbelow = secrets.randbelow
   ```
2. **By assignment. Never `def _sleep(s): time.sleep(s)`.** See `## Context`. Arm 4b asserts the
   module-scope statement is an `ast.Assign` whose value resolves to that attribute, **not** an
   `ast.FunctionDef`.
3. Give each a one-line comment naming it a **declared testability seam for `#3136`**, in the words a
   future dead-symbol sweep would grep — the names are `_`-prefixed and will otherwise read as private
   and removable. The ADR (WP04) is the other half of that defence.
4. Do **not** annotate them in a way that changes their runtime identity (no wrapping, no
   `functools.partial`, no `cast` that produces a new object). `mypy --strict` runs in T013.

**Files.** `src/specify_cli/tracker/saas_client.py`.

**Validation.**
```
./.venv/bin/python -c "import specify_cli.tracker.saas_client as m, time, secrets; print(m._sleep is time.sleep, m._monotonic is time.monotonic, m._randbelow is secrets.randbelow)"
```
Expected: `True True True`. Then `./.venv/bin/ruff check --select C901 src/specify_cli/tracker/saas_client.py` → `All checks passed!`.

---

### Subtask T007 — reroute the five call sites, as ONE indivisible edit

**Purpose.** Make the aliases load-bearing. Aliases without rerouting leave `SC-007` arm 4a false;
rerouting four of five leaves it false. No intermediate tree is green (coupling A).

**Steps.** All five lines opened this session; the pre-fix text is exactly as shown:

| Pre-fix line | Pre-fix text | Post-fix |
|---|---|---|
| `:439` | `time.sleep(float(wait_seconds))` | `_sleep(float(wait_seconds))` |
| `:481` | `start = time.monotonic()` | `start = _monotonic()` |
| `:484` | `elapsed = time.monotonic() - start` | `elapsed = _monotonic() - start` |
| `:515` | `jitter_basis_points = secrets.randbelow(4000)` | `jitter_basis_points = _randbelow(4000)` |
| `:518` | `time.sleep(jittered_delay)` | `_sleep(jittered_delay)` |

`:439` is inside `SaaSTrackerClient._request_with_retry`; `:481`, `:484`, `:515`, `:518` are inside
`SaaSTrackerClient._poll_operation`. Branch delta for both: **0** — name substitution only.

**State the POST-FIX line numbers alongside the pre-fix ones in the WP notes.** Three new module-scope
definitions shift every later line, so `C-004`'s line-enumerated permitted-hunk set must be read
**semantically**, and `SC-007` arm 4d pins the five rerouted sites *as they land post-fix*.

Leave everything else in the file alone. In particular do not touch `delay = 1.0` (`:478`) or
`cap = 30.0` (`:479`) — `SC-003` Arm 1 mutates `:478` in T013 and reverts it.

**Files.** `src/specify_cli/tracker/saas_client.py`.

**Validation.**
```
./.venv/bin/ruff check --select C901 src/specify_cli/tracker/saas_client.py
git diff 98198e980 -- src/specify_cli/tracker/saas_client.py > /tmp/wp02-t007-diff.txt
```
The diff must contain **only** the alias definitions and the five substitutions (plus T008's jitter
hunk once that lands). Zero calls left in the module whose callee resolves to `time.sleep` or
`time.monotonic`.

**The `secrets.randbelow` half is NOT checkable at the end of T007 and is deliberately not asserted
here** — `_poll_jitter_multiplier:106` still holds `secrets.randbelow(4001)` until **T008** resolves
it. Do **not** "fix" that inside T007; it is T008's decision and it has to be priced. The arm lives
in T008's validation.

---

### Subtask T008 — resolve `_poll_jitter_multiplier`, and price the choice

**Purpose.** Remove the precedent for how a seam rots, so the new alias does not join it (FR-010
condition iii, SC-013 sub-3).

**Measured state.** `saas_client.py:104-106` (opened) defines
`def _poll_jitter_multiplier() -> float:` returning `0.8 + (secrets.randbelow(4001) / 10000.0)`.
`grep -rn '_poll_jitter_multiplier' src/ tests/` returns **exactly 1** hit — the definition, **zero
callers**. It disagrees with the live inline jitter at `:515-516` (`_randbelow(4000)` →
`0.8 + bp/10000`, upper bound **1.1999**) on the upper bound: **1.2 vs 1.1999**. `SC-013` sub-3 names
exactly `1` as the **failing** value.

**Two acceptable outcomes. Say which you took, and price it.**

- **(A) Delete — RECOMMENDED.** `grep -rc '_poll_jitter_multiplier' src/ tests/` → **0**. Removes a
  `C901` subject and the 1.2-vs-1.1999 disagreement, and leaves `C-004`'s "delay values unchanged"
  clause trivially satisfied because the reachable delay set does not move.
- **(B) Promote to sole authority.** `grep -rc … src/ tests/` → **≥ 2**, with a caller at the poll
  site and the inline duplicate at `:515-516` **gone**. Three consequences you must price:
  1. **The helper's own `secrets.randbelow` must itself route through `_randbelow`** — arm 4a admits
     **zero** resolved `secrets.randbelow` calls anywhere in the module, the helper included. The body
     becomes `return 0.8 + (_randbelow(4001) / 10000.0)`.
  2. **The rerouted-site count drops 5 → 4** (`:439`, `:481`, `:484`, `:518`; `:515` collapses into a
     call to the helper). **`SC-007` arm 4d's pinned number must move with it** and **WP05 must be
     told**. Branch delta for `_poll_operation`: **−1**.
  3. **`C-004` tension.** The reachable multiplier's upper bound moves `1.1999 → 1.2`. No test asserts
     `randbelow`'s *argument* (`:787` asserts `call_count == 3` only, and `side_effect=[1000, 2000,
     3000]` at `:500` yields the same `0.9 / 1.0 / 1.1` factors under either formula), so the pinned
     delays `[0.9, 2.0, 4.4]` survive — but the reachable **delay-value set** changes, which `C-004`
     says is unchanged. **That is the reason to prefer (A).** Under (B), additionally show `:786` and
     `:787` passing with **zero diff to those two lines**.

**Files.** `src/specify_cli/tracker/saas_client.py`.

**Validation.**
```
grep -rc '_poll_jitter_multiplier' src/ tests/ ; echo "EXIT=$?"
./.venv/bin/ruff check --select C901 src/specify_cli/tracker/saas_client.py
```
Expected: **0** (deleted) or **≥ 2** (promoted). **`1` fails.**

**The `secrets.randbelow` half of T007's arm closes HERE, not in T007.** Only after this subtask can
the module hold **zero** calls whose callee resolves to `secrets.randbelow` — under (A) because the
helper is gone, under (B) because its body became `_randbelow(4001)` (step B.1). Assert all three now,
as `SC-007` arm 4a will:

```bash
./.venv/bin/python -c "
import ast, pathlib
t = ast.parse(pathlib.Path('src/specify_cli/tracker/saas_client.py').read_text())
print([(n.lineno, ast.unparse(n.func)) for n in ast.walk(t) if isinstance(n, ast.Call)
       and ast.unparse(n.func) in {'time.sleep','time.monotonic','secrets.randbelow'}])"
```
Expected: `[]`. A non-empty list at the end of T008 means the seam is not load-bearing yet.

---

### Subtask T009 — the 23 retargets in `test_saas_client.py`

**Purpose.** FR-012. Without this the seam is inert and the mission ships with the defect intact.

**Steps.**
1. Rewrite the **23** target strings enumerated in `## Context` → `### The inventory` —
   **13** `…time.sleep` → `…_sleep`, **9** `…time.monotonic` → `…_monotonic`, **1**
   `…secrets.randbelow` → `…_randbelow`. Every line number is in that table; do not re-derive it, but
   **do** open each line before editing it. **The `randbelow` target string is on `:499`, not `:498`**
   — the `@patch(` opens at `:498` and closes at `:501`, so a line-anchored edit aimed at `:498`
   misses.
2. Update **both prose occurrences — `:559` AND `:715`** (both inside the `:513`–`:762` docstring of
   `test_exponential_backoff_intervals`) for consistency. `:559` reads
   ``@patch("specify_cli.tracker.saas_client.time.sleep")``; `:715` reads the bare dotted string
   `specify_cli.tracker.saas_client.time.sleep` with no `patch("` prefix, inside the run narrative
   ("*Neither run put any extra call on …*"). Open both before editing.
   **Neither is a retarget** and neither may be counted by arm 4c.

   **`:715` may legitimately be frozen — but only explicitly.** It is a *historical measurement
   record*, and rewriting a past observation to name a target that did not exist when it was taken
   falsifies the record. Either outcome is acceptable; **exactly one is not**: leaving `:715`
   unmentioned. **Update both** → `grep -c 'saas_client\.time\.sleep' …test_saas_client.py` falls
   **15 → 0**. **Update `:559`, freeze `:715` with a one-clause "measured pre-fix" note** → **15 → 1**,
   and you must say so and say why, in the WP notes and in T013's diff-shape arm. Report the measured
   pre- and post-edit counts either way; do not silently land a number the DoD does not predict.
3. **Cross-lane note — say it in the WP notes, because WP03 cannot see your tree.** `:559`'s
   **target string moves** in this step, and `WP03` T019 **arm F** pins that exact site as one of
   four regex-only docstring exceptions. WP03 keys its pin on `(file, line)` for precisely this
   reason; if you find it keyed on `(file, line, target)` at consolidation, **that** is the break, not
   your edit. Flag `:559`'s move in the review handoff so WP03's reviewer sees it.
4. **No assertion EXPRESSION may change.** Only the decorator target strings move. That is what
   preserves R-1's actual guarantee, and it is what makes this *not* the "test-side edit" R-1
   excluded.
5. Leave `_advancing_clock`'s docstring at `:36-40` alone. It reads *"…patches the attribute on the
   shared :mod:`time` module rather than a module-local alias"* — past-tense history that becomes
   **more** accurate after the fix, and touching it would fail the diff-shape arm.

**Files.** `tests/sync/tracker/test_saas_client.py`.

**Validation.** Run the four census nodes plus the two backoff nodes by id — never a `tests/sync`
sweep:
```
./.venv/bin/python -m pytest \
  "tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals" \
  "tests/sync/tracker/test_saas_client.py::TestPolling::test_timeout_after_5_minutes" \
  "tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after" \
  "tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_defaults_to_5s_when_missing" \
  -q -ra -p no:cacheprovider > /tmp/wp02-t009.txt
```
Quote the `N passed` line and print the selected count.

---

### Subtask T010 — the 1 retarget in `test_saas_client_origin.py`

**Purpose.** This file was **absent from R2's ownership map entirely** while carrying census
assertion #5 (`:261`, `mock_sleep.assert_called_once_with(2.0)` — opened) *and* the retarget at
`:229`. A plan that does not own it cannot deliver the fix.

**Steps.** Rewrite the single `patch()` target at `:229` from
`specify_cli.tracker.saas_client.time.sleep` to `specify_cli.tracker.saas_client._sleep`. Nothing
else in the file changes — the twenty-two `httpx.Client` patches and the two `_force_refresh_sync`
patches stay exactly as they are.

**Files.** `tests/sync/tracker/test_saas_client_origin.py`.

**Validation.**
```
./.venv/bin/python -m pytest \
  "tests/sync/tracker/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises" \
  -q -ra -p no:cacheprovider > /tmp/wp02-t010.txt
git diff 98198e980 -- tests/sync/tracker/test_saas_client_origin.py
```
Expected: `1 passed`, and a one-line diff.

**Then run the AST decorator counter — this is DoD 5's instrument, and this is the ONLY place in
WP02 it runs.** Do not substitute a `grep`: greps see the `:559` / `:715` docstring occurrences and
report numbers the DoD does not predict. (WP05 T027 arm 4c is the *shipped* gate for the same fact;
this is WP02 proving its own edit before handing it over.)

```bash
./.venv/bin/python -c "
import ast, collections, pathlib
c = collections.Counter()
for f in ['tests/sync/tracker/test_saas_client.py','tests/sync/tracker/test_saas_client_origin.py']:
    for n in ast.walk(ast.parse(pathlib.Path(f).read_text())):
        if not (isinstance(n, ast.Call) and n.args): continue
        if (n.func.id if isinstance(n.func, ast.Name) else getattr(n.func,'attr',None)) != 'patch': continue
        a = n.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str) and 'saas_client' in a.value:
            c[(f, a.value)] += 1
[print(f'{v:3d}  {k[0]}  {k[1]}') for k, v in sorted(c.items())]"
```

Expected post-fix, from AST `patch()` call nodes only:

| Target | `test_saas_client.py` | `test_saas_client_origin.py` | Total |
|---|---:|---:|---:|
| `…saas_client._sleep` | **13** | **1** | **14** |
| `…saas_client._monotonic` | **9** | 0 | **9** |
| `…saas_client._randbelow` | **1** | 0 | **1** |
| `…saas_client.time.sleep` / `.time.monotonic` / `.secrets.randbelow` | **0** | **0** | **0** |

---

### Subtask T011 — correct the false docstring at `test_saas_client.py:55-57`

**Purpose.** SC-013 sub-4. The file currently states the fix is blocked while the fix has landed.

**Measured state.** `:55-57` sits inside the `_advancing_clock` docstring (`def` at `:32`, docstring
`:33-58`) and reads: *"``test_timeout_after_5_minutes`` deliberately keeps its exact ``[0.0, 301.0]``:
there the second value \*is\* the assertion, and it never reaches ``_request``."*

**The claim is false.** `:804` is `mock_monotonic.side_effect = [0.0, 301.0]` — a **side_effect
stimulus**. The only assertion in `test_timeout_after_5_minutes` is the `pytest.raises` at `:806`,
with the call at `:807` (all three opened).

**Anchor the criterion on the right pattern.** The text carries **RST emphasis** (`*is*`), which is
why `grep -c 'is the assertion'` returns **0**, not 1 — verified `0` on HEAD and on `98198e980`, so
R2's plain-text pin graded nothing. The binding form is:

```
grep -cE 'is\*? the assertion' tests/sync/tracker/test_saas_client.py   # 1 today → must become 0
grep -c 'side_effect stimulus' tests/sync/tracker/test_saas_client.py   # 0 today → must become >= 1
```

**Steps.** Replace the three lines with text that (a) names `[0.0, 301.0]` as a **side_effect
stimulus**, and (b) names the `pytest.raises` at `:806` as the node's **only** assertion. It must be a
correction, not a deletion — the positive twin exists to refuse deleting the whole docstring.

**Files.** `tests/sync/tracker/test_saas_client.py`.

**Validation.** Both greps above, with their exit codes recorded.

---

### Subtask T012 — turn both reds green, then the determinism arms

**Purpose.** Close the WP's final commit green on every instrument (`charter.md:512-513`), and prove
the guard is deterministic rather than racing (NFR-002/003/004).

**Steps.**
1. **Both reds green.** Guard passes; `./.venv/bin/python scripts/check_patch_targets.py` exits `0`.
2. **NFR-002 — 10 of 10.** `./.venv/bin/python -m pytest <guard> -q -ra -p no:cacheprovider` × **10**,
   **10 passes**. Below 10/10 means the probe is racing the test body and the arm is not a proof.
   Report per-run counts, never a summary verdict.
3. **NFR-003 — topology invariance.** The four census nodes produce **identical verdicts** under `-n0`
   and under `-n auto --dist loadfile`, **3 consecutive runs of each** = 6 runs, 6 identical pass sets.
   Report per-run counts.
4. **NFR-004 / SC-008 — leak neutrality, with `-n0` PINNED.**
   ```
   ./.venv/bin/python -m pytest <guard> \
     tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py \
     -q -ra -p no:cacheprovider -n0 > /tmp/wp02-leak.txt
   grep -c '^ERROR tests/' /tmp/wp02-leak.txt          # 0
   git diff 98198e980 -- tests/sync/_leak_guard.py | grep -cE '^\+\s*_PinnedLeak\('   # 0
   ```
   **`-n0` is pinned deliberately**: under xdist the controller prints a different line, and a real
   `-n 4` run printed `inspected 0 test(s)`. Do **not** "fix" that false red.
   AST-count `_PINNED_LEAKS`' elements at `tests/sync/_leak_guard.py:333` → **12**. **That statement is
   an `ast.AnnAssign`, not an `ast.Assign`** — it reads `_PINNED_LEAKS: tuple[_PinnedLeak, ...] = (`
   (opened this session), so a walk filtering on `ast.Assign` returns **zero** hits. Filter on
   `ast.AnnAssign` and read `node.value.elts`. Then reconcile `12` against `C-003`'s "11 confirmed
   leaks" by naming **which reading is wrong** (a pin that is not a `#3130` leak, or a miscount). Do
   not leave two numbers in the tree.
5. All of this runs **inside WP01's C-001 window**, on targeted node ids. Name the node ids used.

**Files.** No source edits — transcripts only, into **this WP's own** `notes/alias-seam-3136.md`,
**not** `notes/constraint-enforcement-3136.md` (WP07's, one writer, and WP07 runs *after* WP02 — see
`### This WP's notes file`).

**Validation.** All four blocks above, output redirected, `N passed` quoted per run.

---

### Subtask T013 — FR-004 / SC-003 mutations (applied and reverted), then lint and types

**Purpose.** Prove the instrument in the positive direction — a vacuous instrument satisfies FR-001
trivially — and close `NFR-006` / `SC-012`.

**Steps.**
1. **Arm 1 — wrong value.** `sed -i 's/^        delay = 1.0$/        delay = 1.5/' src/specify_cli/tracker/saas_client.py`
   (line `:478`, opened and confirmed), then run
   `…::TestPolling::test_exponential_backoff_intervals` → **`1 failed`**, failure text showing observed
   `[1.35, 3.0, 6.6000000000000005]` against expected `[0.9, 2.0, 4.4]`. **The literal is
   `6.6000000000000005`** — production computes `6.0 * 1.1`; `6.6` is unsatisfiable as a pinned string.
2. **Arm 2 — wrong per-call value.** Revert. Change the 429 sleep at `:439` (post-fix
   `_sleep(float(wait_seconds))`) to `… * 2`, run the three 429 census nodes → **`3 failed`**, each
   naming the doubled value (`6.0`, `10.0`, `4.0`).
3. **Arm 3 — wrong cardinality.** Revert. **Duplicate** the `_sleep(...)` call at `:439` and add a
   fourth `pending` response to the backoff node's fixture, run the four census nodes → **`4 failed`,
   each failing on the call count**, with the failure text naming observed-vs-expected **counts**
   (`4 != 3`, `2 != 1`), not a delay value. This is the arm that refuses
   `assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]`.
4. **Arm 4 — revert everything.** `git checkout -- src/specify_cli/tracker/saas_client.py` **and the
   fixture**, run all four → **`4 passed`**. Report `git status --porcelain src/ tests/` **empty**.
   `C-004`: mutations are applied and reverted, **never committed**.
5. **Lint and types.**
   ```
   ./.venv/bin/ruff check src/specify_cli/tracker/saas_client.py tests/sync/tracker/test_saas_client.py \
     tests/sync/tracker/test_saas_client_origin.py tests/sync/tracker/test_sleep_attribution_guard_3136.py
   ./.venv/bin/ruff check --select C901 <same four files>
   git diff 98198e980 -- src/ tests/ | grep -cE '^\+.*(# noqa|# type: ignore)'    # 0
   git diff 98198e980 -- ruff.toml pyproject.toml                                  # report as DIFF TEXT
   ./.venv/bin/mypy --strict src/specify_cli/tracker/saas_client.py
   ```
   **Run `mypy --strict` explicitly.** CI's mypy is advisory and the `[[tool.mypy.overrides]]` block
   at `pyproject.toml:296-301` sets `follow_imports = "skip"` for `specify_cli.*` (`module =` on
   `:300`, the directive on **`:301`**), so **CI will not catch a typing regression in the aliases.**

   **⚠ `mypy --strict` is ALREADY RED on this file — a pre-existing baseline, not your regression.**
   Re-measured this session, verbatim:

   ```
   $ ./.venv/bin/mypy --strict src/specify_cli/tracker/saas_client.py
   src/specify_cli/tracker/saas_client.py:162: error: Returning Any from function declared to return "str | None"  [no-any-return]
   src/specify_cli/tracker/saas_client.py:163: error: Returning Any from function declared to return "str | None"  [no-any-return]
   Found 2 errors in 1 file (checked 1 source file)
   ```

   `:162-163` sit **outside** `C-004`'s permitted-hunk set. **Do not fix them** (breaches `C-004`) and
   **do not silence them** with `# type: ignore` (the `grep -cE '^\+.*(# noqa|# type: ignore)'` above
   reds on it; `CLAUDE.md` forbids it). **The criterion is "no NEW findings", not "clean":**
   (1) re-run the command yourself and quote the output verbatim — if it has moved, the measurement is
   the truth and this prompt is not; (2) record the two `no-any-return` errors as this file's
   **pre-existing baseline**, by line and error code, in the WP notes; (3) **file them per the
   charter's Pre-existing Failure Reporting Rule** — an issue must exist before a red counts as
   accepted baseline — and hand the number to WP07 T042, which owns the filings register; (4) the DoD
   is satisfied when the post-WP output carries **exactly these two findings and no others**. Any
   third finding is yours.
6. **Produce the diff-shape acceptance arm** (this is how `C-004`'s line-level restriction is expressed
   over a file-granular ownership mechanism):
   ```
   git diff 98198e980 -- tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py
   ```
   Every changed line must be **either** (a) inside the `:55-57` docstring correction, **or** (b) a line
   whose only change is a `patch()` target string moving from one of the three pre-fix strings to its
   post-fix counterpart, **or** (c) the `:559` / `:715` docstring occurrences (T009 step 2 — state
   whether `:715` was updated or explicitly frozen). **Any other changed line fails the criterion** —
   in particular, **no assertion expression may change**.

**Files.** `src/specify_cli/tracker/saas_client.py` (mutated and reverted — final diff unchanged from
T007/T008).

**Validation.** Arms 1–4 with their exact expected outputs; `ruff check` 0 findings; the four
suppression/config checks; `mypy --strict`; the diff-shape arm.

---

## Definition of Done

Every item below is evidenced by a redirected transcript with its `N passed` line quoted and its exit
code recorded. Mark each subtask with `spec-kitty agent tasks mark-status <Txxx> --status done`.

1. **T005** — guard committed **first**, RED on `98198e980` on **both** counts (sync shard with the
   observed `AttributeError` text recorded; `check_patch_targets.py` naming all three alias targets),
   `pytestmark = [pytest.mark.fast]` present. The base-tree arm was taken in a **throwaway detached
   worktree**, and `git worktree list` after cleanup shows it gone.

   **Items 1a–1e grade the guard's CONTENTS — `SC-004`, `SC-005`, `NFR-001`, `NFR-004`, none of which
   any other item here reaches. Without them a guard whose entire body is
   `with patch("specify_cli.tracker.saas_client._sleep"): pass` is genuinely red on `98198e980`, green
   on head, passes 10/10 and 6/6, adds zero `^ERROR tests/` — and satisfies every other item on this
   list.** That was the post-tasks squad's named cheat, and this is the mission's only *runtime*
   evidence that the seam is import-bound and pollution-immune (WP05 grades it **statically**, WP07
   grades constraints).

   1a. **`SC-004` — ten arms: five rows × two.** Five arm-(a) invariance arms and five arm-(b) raise
       arms, one pair per census assertion, the five rows matching `SC-004`'s table (`spec.md:618-624`,
       reproduced in T005 step 3). **Count them: ten, not four, not "a loop."**
   1b. **Arm (b) is the LITERAL pre-fix form, read off the STDLIB mock.** Each expression is diffed
       against `98198e980`'s own assertion text (quote the `git show 98198e980:<file>` excerpt per row)
       and shown to be a literal, not a paraphrase. Each reads the **stdlib `time.sleep` recorder**,
       never arm (a)'s alias recorder — which post-fix sees exactly `3/1/1/1` and therefore cannot
       raise. **An arm (b) that passes on head is a failed arm, not a green one.**
   1c. **`SC-005` / `NFR-001` — both numbers read off recorders, printed per row.** Per row the guard
       prints `stdlib_mock.call_count` (asserted `>= 100`) and `alias_mock.call_count` (an
       **equality**: `3` for rows 1–2, which share the backoff node; `1` for rows 3–5 — `3 / 1 / 1 / 1`
       across the four census nodes). **Both are `patch()` recorders in ONE window; neither may be a
       counter the probe increments about itself.** Paste the printed block.
   1d. **The five row identifiers and the probe thread name are printed**, so a reviewer can count the
       rows without reading the source and an unattributable probe thread is visible.
   1e. **`NFR-004` — every probe joined in a `finally`**, every spawn gated on a `threading.Event` set
       after the probe's **first recorded call**. Show both in the diff; an unjoined probe leaks into
       the next node and reds `SC-008`.
2. **T006** — `m._sleep is time.sleep`, `m._monotonic is time.monotonic`,
   `m._randbelow is secrets.randbelow` all `True`; all three are `ast.Assign`, none is an
   `ast.FunctionDef`.
3. **T007** — five call sites rerouted; **post-fix line numbers stated**; zero calls in the module
   whose callee resolves to `time.sleep` / `time.monotonic`. (The `secrets.randbelow` half belongs to
   T008 — `_poll_jitter_multiplier:106` still holds `secrets.randbelow(4001)` at the end of T007.)
4. **T008** — `grep -rc '_poll_jitter_multiplier' src/ tests/` is **0** or **≥ 2** (never `1`); the
   choice is stated and priced; if promoted, the arm-4d count change (5 → 4) is flagged for WP05 and
   `:786`/`:787` pass with zero diff. **Plus the deferred half of T007's arm**: the AST probe prints
   `[]` — zero calls in the module whose callee resolves to `secrets.randbelow`.
5. **T009 + T010** — **24** decorator retargets landed, **0** `patch()` target strings equal to any of
   the three pre-fix strings, `13 + 1 = 14` `_sleep` / `9` `_monotonic` / `1` `_randbelow`, **counted
   from AST `patch()` nodes (T010's counter), never by grep**; **both** prose occurrences (`:559`,
   `:715`) updated — or `:715` explicitly frozen with its reason — and **excluded** from the decorator
   count; **no assertion expression changed**.
6. **T011** — `grep -cE 'is\*? the assertion' …` → **0**; `grep -c 'side_effect stimulus' …` → **≥ 1**
   naming `:806`.
7. **T012** — both reds green; **`SC-009`** — NFR-002 **10/10**; NFR-003 **6 runs, 6 identical pass sets**;
   NFR-004/SC-008 `^ERROR tests/` = 0, 0 added `_PinnedLeak(` entries, `12` reconciled against C-003's
   "11".
8. **T013** — SC-003 Arms 1–3 red with the exact pinned texts, Arm 4 `4 passed` with
   `git status --porcelain src/ tests/` empty; `ruff check` 0 findings; 0 added `# noqa` /
   `# type: ignore`; `ruff.toml` / `pyproject.toml` diffs reported as text; **no *new*
   `mypy --strict` findings** on `saas_client.py` — the two pre-existing `no-any-return` errors at
   `:162-163` are recorded as baseline and **filed** per the charter's Pre-existing Failure Reporting
   Rule, with the issue number in the WP notes; the diff-shape arm satisfied.
9. **WP-level** — the WP's **final commit is GREEN** on the guard, on `check_patch_targets.py`, and on
   the four census node ids. `git log` shows the guard commit **before** any implementation commit
   (coupling E, verified by a human).

## Risks

- **A partial reroute** leaves a direct `time.sleep(` in the module, turning `SC-007` arm 4a red
  rather than merely reducing coverage. *Mitigation*: arm 4a is a whole-file AST assertion — treat the
  five sites as one indivisible edit (T007).
- **A partial retarget is the more likely failure and it is SILENT.** *Mitigation*: arm 4c pins the
  post-fix counts (`14 / 9 / 1`) and pre-fix counts (`0`); `SC-005`'s `alias_mock.call_count ==
  <expected>` fails on any incomplete-retarget tree.
- **A vacuous guard.** Ten arms reduced to a `pass` body is red-on-base, green-on-head and satisfies
  every count in this prompt. *Mitigation*: DoD items 1a–1e grade the guard's contents directly.
- **The wrapper cheat.** A wrapper with all 24 retargets passes every behavioural arm. *Mitigation*:
  arm 4b is static. Nothing at runtime catches it — do not expect `SC-005` to.
- **Promoting `_poll_jitter_multiplier`** changes what `:499`'s `@patch("…_randbelow")` reaches, moves
  the arm-4d rerouted-site count 5 → 4, and shifts the reachable bound `1.1999 → 1.2`. *Mitigation*:
  prefer deletion; if promoted, show `:786`/`:787` with **zero** diff and notify WP05.
- **The alias names are `_`-prefixed** and read as private and removable to a future dead-symbol
  sweep. *Mitigation*: T006's comment, WP04's ADR, and arm 4a.
- **`C-004`'s permitted-hunk set is enumerated by line number**, and three new module-scope definitions
  shift every later line. *Mitigation*: state the post-fix line numbers; `SC-016`'s reviewer reads the
  hunks semantically.
- **`mypy --strict` is advisory in CI (`follow_imports = "skip"`) AND already red here** on two
  pre-existing `no-any-return` errors outside `C-004`'s permitted set. *Mitigation*: T013 — run it
  explicitly, grade "no *new* findings", and file the baseline.
- **The venv.** A bare `uv run` anywhere in this WP destroys the toolchain and silently downgrades the
  interpreter to 3.11.15. *Mitigation*: Form 1 or Form 2 only; `command -v` before trusting anything.

## Reviewer Guidance

1. **Verify the commit order first.** `git log --oneline` must show
   `test_sleep_attribution_guard_3136.py` landing **before** any change to `saas_client.py`. This is
   coupling E and its verifier is you, reading `git log`.
2. **Verify the red on `98198e980`, on both gates**, that it was taken in a **throwaway worktree**
   (not `git checkout … -- .`), and that the WP recorded the **observed** `AttributeError` text rather
   than restating the `[UNVERIFIED]` placeholder. Then verify green on the final commit.
3. **Open the guard and count its arms — this is the item most likely to be skipped.** Ten
   (five arm-(a), five arm-(b)), the five rows matching `SC-004`'s table, arm (b) reading the
   **stdlib** recorder and diffable against `98198e980`, `stdlib_mock.call_count >= 100` and
   `alias_mock.call_count` equalities printed per row, the probe thread named, every probe joined in a
   `finally`. **A guard that passes 10/10 and 6/6 while asserting nothing satisfies every other item
   here.** DoD 1a–1e is the checklist.
4. **Do not read the lint-job red in the guard-commit window as breakage.** It is
   `scripts/check_patch_targets.py` (`ci-quality.yml:883-884`, no args) correctly reporting that
   `_sleep` / `_monotonic` / `_randbelow` do not exist yet — expected, attributable, positive evidence.
5. **Count the retargets from AST, not grep.** A grep of `test_saas_client.py` for the pre-fix
   `time.sleep` string returns **15** pre-fix and would return **2** post-fix if the `:559` **and**
   `:715` prose occurrences were both left alone — the correct decorator answer is **13** pre-fix and
   **0** post-fix. **Both prose lines sit inside the `:513-762` docstring; `:715` has no `patch("`
   prefix**, so a re-derivation anchored on `patch\("` will not show it to you — run the bare
   `grep -c 'saas_client\.time\.sleep'` yourself. If the WP reconciled grep and AST by editing prose to
   satisfy a numeric gate, reject. Freezing `:715` as a historical record is acceptable **only** with
   the explicit statement T009 step 2 requires.
6. **Check the alias form structurally.** `ast.Assign`, not `ast.FunctionDef`. A wrapper passes every
   behavioural arm in this mission — if you only run tests, you will not catch it.
7. **Run the diff-shape arm yourself** (`git diff 98198e980 -- <the two test files>`). Every changed
   line is the `:55-57` correction, a `patch()` target string move, or the `:559` / `:715` docstring
   occurrences. **Any changed assertion expression is a rejection.**
8. **Check `_poll_jitter_multiplier` is 0 or ≥ 2, never 1**, and that the choice was priced — the
   arm-4d count change and the `1.1999 → 1.2` bound shift if promoted.
9. **Check the greps are the `-E` forms.** `grep -c 'is the assertion'` is `0` on both trees and grades
   nothing; the binding form is `grep -cE 'is\*? the assertion'`.
10. **Check the `mypy --strict` result is graded as "no NEW findings"** against the two pre-existing
    `no-any-return` errors at `saas_client.py:162-163`, and that those were **filed**, not fixed and
    not `# type: ignore`d. A claim of "clean" is wrong on this file and means the command was not run.
11. **Check no sweep was run** (`tests/sync` / `tests/cli` are forbidden — C-001, WP01 owns the
    window), that `ruff format` appears nowhere, and that `ruff.toml` / `pyproject.toml` diffs were
    reported as diff **text** rather than as a count.
