---
work_package_id: WP03
title: The AST patch-seam census, the shared resolver export, and the committed control fixture
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-005
- NFR-007
- C-009
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
history: []
agent_profile: python-pedro
authoritative_surface: scripts/
create_intent:
- scripts/patch_seam_census.py
- tests/architectural/test_patch_seam_census_control.py
execution_mode: code_change
owned_files:
- scripts/patch_seam_census.py
- scripts/check_patch_targets.py
- tests/architectural/test_patch_seam_census_control.py
- tests/architectural/_fixtures/patch_seam_control/**
role: implementer
tags: []
tracker_refs: []
---

# WP03 — The AST patch-seam census, the shared resolver export, and the committed control fixture

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent**: `claude`

If `/ad-hoc-profile-load` is unavailable, invoke the canonical skill
`spk-doctrine-profile-load` with the same profile name. If neither resolves, list the
available profiles (`spec-kitty charter profiles`, or the doctrine profile directory
under `.kittify/charter/`) and load `python-pedro` from that listing. Do not proceed
on the generic assistant identity.

Also load `.kittify/charter/charter.md` first. Standing orders 5 (architectural gate
discipline: non-vacuity, self-mutation arm, shrink-only allowlist), 6 (single
canonical authority) and 9 (never green-wash a red) bind here.

---

## Objective

Build the mission's **instrument**: one AST census classifying every `patch()` target
string under `tests/sync/`, a **single** resolver exported from the script that already
owns that logic, and a **committed control fixture** proving the census is not lying.

`<census>` (`scripts/patch_seam_census.py`) is the sole instrument for **SC-001**,
**SC-002** and **SC-013** — a census emitting a hardcoded table would satisfy all
three. **SC-015** exists to defeat that, and the control fixture is this WP's strongest
deliverable.

Written against the **pre-fix tree** on purpose (`dependencies: ["WP01"]`, deliberately
not WP02): the pre-fix numbers must be measurable, which is what makes the post-fix
delta mean anything.

**Start command:** `spec-kitty implement WP03`

---

## Context

### ENVIRONMENT

**NEVER run a bare `uv run`.** It re-solves against the tracked `.python-version`
(`3.11.15`), **destroys `.venv`**, and drops `pytest`/`ruff`/`mypy`. Three occurrences
in this mission. Proof, in this checkout:

```
uv sync --dry-run --python 3.12
# → Would use project environment at: .venv
#   Resolved 126 packages in 2ms
#   Would uninstall 70 packages
```

Use only `./.venv/bin/<tool>` or `uv run --python 3.12 --extra test --extra lint …`.
Recover with `uv sync --python 3.12 --extra test --extra lint`.

`~/.local/bin/*` resolves to an **unrelated checkout** — verified: `command -v pytest`
→ `/home/jeroennouws/.local/bin/pytest`. Prepend `./.venv/bin` to `PATH`, and **quote**
any `command -v` you record as evidence. Verified here: `./.venv/bin/python -V` →
`Python 3.12.13`.

### DISCIPLINE — do not run `tests/sync` or `tests/cli`

**C-001** (`spec.md:480`) forbids these two cones running concurrently on one machine,
and a sibling mission may hold the window. **WP03 never needs it.** The census is a
**static AST reader** over `tests/sync/` source — it `ast.parse()`s the files, never
collects or executes them. Every number below was produced that way. Do not acquire the
C-001 window; say so in your evidence.

One caveat: `_mock_importer` **imports** the module prefix a target names. Over
`tests/sync/` today every resolved prefix is `specify_cli.*` or stdlib — measured, no
target resolves into a `tests.*` module — so nothing under `tests/sync/` is imported.
Re-check if you widen the scan.

Test conventions: redirect suite output to a file and quote the `N passed` line; print
the **selected** count; use `-ra`, never `-rf`; `ruff check` only, **never
`ruff format`**.

### The resolver already exists — reuse it

`scripts/check_patch_targets.py` is `[ENFORCED]` in CI:

```
ci-quality.yml:883  - name: "[ENFORCED] Validate patch() target strings (closes #394)"
ci-quality.yml:884    run: uv run python scripts/check_patch_targets.py
```

Its `_mock_importer` (`:80-106`) already performs the progressive-import-then-`getattr`
walk `unittest.mock._get_target` performs. Verified:
`_mock_importer("specify_cli.tracker.saas_client.time")` → `(<module 'time' (built-in)>, None)`.

Neither `spec.md` nor `plan.md` knew this file existed until the squad found it
(`analysis-report.md:466`). A parallel resolver breaches **single canonical
authority**. Export it — do not copy it.

### The discriminator, and why the obvious predicate is unshippable

FR-005 as worded refuses any `@patch("a.b.c.attr")` whose penultimate segment resolves
to a `ModuleType`. **Measured, that flags 649 of 664 sites (97.7%)** — because that is
how `unittest.mock._get_target` works. The decomposition:

| Bucket | Count | What it is |
|---|---:|---|
| own-module, first-party | **357** | `patch("specify_cli.sync.client.WebSocketClient")` — the **correct** idiom |
| reach-through | **286** | `patch("specify_cli.tracker.saas_client.time.sleep")` — the defect class |
| direct foreign | **6** | `patch("subprocess.run")` ×4, `patch("asyncio.run_coroutine_threadsafe")` ×2 |
| penultimate **not** a module | **15** | class-attribute patches, e.g. `patch("…sync.runtime.SyncRuntime.start")` |
| unresolvable | **0** | none on this tree, in this environment |
| **total `patch(<str literal>)` sites** | **664** | |

Built to the letter the gate is unshippable, and the natural reaction is a hardcoded
exclusion list — **the exact vacuity the gate exists to prevent**.

**The correct discriminator:** resolved module `__name__` **≠** the dotted module path
(reach-through), **or** the resolved module is not first-party (direct foreign).

`plan.md:838` proposes pinning `356 / 286 / 7`. An independent probe this session
reproduced **357 / 286 / 6 / 15** — the boundary moves by one in each direction
depending on where "first-party" is drawn. **It is a definitional choice and must be
declared, not assumed.** T019 pins what the shipped analyzer emits, not the plan's
numbers.

### Two import forms that cannot both work — resolved here

`scripts/` has **no** `__init__.py` (only `scripts/docs/` does), so `scripts` is an
implicit namespace package. `pytest.ini:2-9` **deliberately** excludes `.` from
`pythonpath` (`pythonpath = src`), with a comment explaining the double-import hazard it
prevents. Under `python scripts/patch_seam_census.py …`, `sys.path[0]` is `scripts/` and
the repo root is absent; under `import scripts.patch_seam_census` from
`tests/architectural/`, the reverse holds. The shipped precedent for the workaround is
`test_docs_cli_reference_parity.py:51-56` — `_REPO_ROOT` at `:51`, the `sys.path.insert`
guard at `:52-53`, the imports with `# noqa: E402` at `:55-56`. (`plan.md` cites
`:52-56`, omitting the `_REPO_ROOT` assignment the block depends on.)

**Decision, binding — both halves:**

1. **`scripts/patch_seam_census.py` uses the repo-root `sys.path` insertion and imports
   its sibling under its canonical name** — `from scripts.check_patch_targets import
   resolve_patch_target  # noqa: E402` — so the resolver has exactly one module identity
   regardless of entry point. Verified working via the namespace package.
2. **`test_patch_seam_census_control.py` consumes the census only through its CLI, via
   `subprocess`.** This makes SC-001's own invocation the single front door, deletes the
   dual-import problem, and means the control test needs **no** `sys.path` insertion and
   **no** `# noqa: E402`. IC-04's surface correction (iii) does not apply to the test.

### The control fixture can red an enforced lint — decided here

`check_patch_targets.py:127` defaults its roots to `[Path("tests")]` and `:131` rglobs
**every** `*.py` beneath them, fixture directories included. Its extractor is a **regex
over raw source** (`:32-34`), so it sees `patch("…")` inside docstrings and comments
too. A committed fixture whose target does not resolve makes the `[ENFORCED]` job print
`::error::Broken patch() targets` and exit **1** — reproduced this session on a
throwaway file. Baseline today: `All 5052 patch() targets valid.`, exit **0**. And **no
existing file under `tests/**` whose path contains "fixture" carries a `patch(` literal**
— this would be the first.

**Decision, binding:**

- **Every literal `patch("…")` target in a committed fixture module — including ones
  quoted inside a docstring decoy — must resolve on this tree.** Prefer
  `specify_cli.tracker.saas_client.time.sleep`, which resolves pre-fix and post-fix
  (`saas_client.py` keeps its bare `import time`; C-004 permits only the alias
  definitions and call-site rerouting).
- **The unresolvable and direct-foreign cases are built in-memory** — written under
  `tmp_path` by the control test and fed to the census CLI as a path argument, the same
  technique the gate's own self-mutation arms already require. They never land under
  `tests/`, so they can never red the enforced lint.

### Fixture location, naming, markers

Fixtures live under **`tests/architectural/_fixtures/patch_seam_control/`**. The parent
`_fixtures/` **already exists** (`bad_adapter.py`, `org_packs/`); `plan.md` correction 6
is right that R2's `fixtures/` does not. Two precision points the plan states loosely:

- A leading underscore on a **directory** does **not** stop pytest collecting it —
  `_fixtures` is not in pytest's `norecursedirs` and this repo sets no override. What
  protects you is **non-`test_` module names** (pytest's default `python_files` is
  `test_*.py`/`*_test.py`), so the fixture modules are never collected, never fail, and
  never pollute `tests/architectural/_gate_coverage_baseline.json` (`orphan_files: []`,
  `orphan_test_count: 0`).
- For the same reason the fixture modules are **exempt from the `pytestmark`
  convention**: `test_pytest_marker_convention.py:72` globs `test_*.py` only.

`test_patch_seam_census_control.py` needs `pytestmark = [pytest.mark.architectural]` —
the convention across 165 siblings; the precedent form is at
`test_no_inert_schema_slots.py:300` (`plan.md` cites `:53`; the actual line is `:300`).
**Arch shard registration is not needed**: `tests/_arch_shard_map.py:381` sets
`default_fallback=True`, so a new arch file is hash-bucketed automatically.

**C-009** requires ownership by exact filename once the names are chosen; `wps.yaml`
carries the glob only because they were undecided (`wps.yaml:792`). **T018 fixes them;
report them.**

### Lint and complexity

CI runs `ruff check src tests` (`ci-quality.yml:820`) — **`scripts/` is outside that
scope**, while being exempted only from `TID251` (`pyproject.toml:269`). So `scripts/`
lint is *your* job; check it explicitly. Complexity ceiling **15**
(`pyproject.toml:286-287`). A sibling mission just refactored a script from 25 to 12 for
exactly this — build the classifier as small composed functions from the start.

**`len(x) == N` is effectively BANNED in `test_patch_seam_census_control.py`, and it is
harder than a preference.** `test_golden_count_ban.py` ratchets non-escaped
`convert`-classified `len(x) == <int>` sites per directory;
`tests/architectural/_golden_count_baseline.json:6` freezes
`"tests/architectural": 25`, and the live non-escaped count measured this session is
**25**. **The bucket is at 25/25 — zero headroom.** One new `assert len(sites) == 4` in
the control test reds `test_golden_count_ban.py` on arrival, and this WP's control test
is the **likeliest place in the mission** for a cardinality assertion to appear (six
arms, every one of them about a count). Assert the **set**
(`assert expected_frozenset == observed_frozenset`) throughout — stronger contract, names
the delta on failure, and classified `keep` when the compared literal is empty. The
escape marker, only for a genuinely cardinality-only site, is
`# golden-count: cardinality-is-contract` on the assertion's own physical line — never as
a workaround for a set assertion you did not want to write. WP05 is told this three
times because it also touches this directory; WP03 lands here first.

**A cited `file:line` is not evidence that the line says what the citation claims — open
every one.** Three citations inherited from `plan.md`/`spec.md` are off; they were found
by opening them.

### This WP's notes file — named

Every "record it in your WP evidence / the WP notes" in this prompt means exactly one path:

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/census-3136.md
```

It is a **declared out-of-map planning write** (`wps.yaml`'s WP03 block) — `owned_files` may not
carry any path under `kitty-specs/`, so it is named there instead. **Create it before the first
command runs** and write the `command -v` / `--version` block into it first, so it is non-empty by
construction; a `grep -c` negative over an absent file prints no count and exits `2`, which reads as
satisfied.

---

## Subtasks

### Subtask T014 — Export the resolver from `scripts/check_patch_targets.py`

**Purpose.** One patch-target resolver with **one** named verdict vocabulary, owned by
the script CI already enforces.

**Steps.**

1. Read the file end to end (150 lines): `_mock_importer` `:80-106`, `validate()`
   `:109-124`, `_should_skip()` `:62-64`; note `_SKIP_MODULE_PREFIXES` (`:39-59`)
   short-circuits stdlib **top-level** targets.
2. Add **one** public function:
   `resolve_patch_target(target: str, *, first_party_roots: frozenset[str]) -> PatchTargetVerdict`.
   It splits on the last dot exactly as `unittest.mock._get_target` does, calls
   `_mock_importer` on the module part, and returns a **named verdict** — a frozen
   dataclass or `StrEnum` + payload with exactly these outcomes:
   - `own_module` — a `ModuleType` whose `__name__` **equals** the dotted path, root first-party
   - `reach_through` — a `ModuleType` whose `__name__` **differs** from the dotted path
   - `foreign` — a `ModuleType`, `__name__` equals the path, root **not** first-party
   - `not_a_module` — resolved, but the penultimate segment is not a `ModuleType`
   - `unresolvable` — `_mock_importer` errored, or the target has no dot

   Carry the resolved `__name__`, the dotted path and the attribute on the verdict so
   callers never re-derive them.
3. **No behaviour change to the CLI.** `main()`, `validate()`, `extract_targets()` and
   the exit codes stay equivalent in effect. Re-express `validate()` via the helper
   **only if** its return values are unchanged for every input.
4. This module now **owns the shared vocabulary**. The census and (later) WP05's gate
   consume these names; neither redefines them.

**Files.** `scripts/check_patch_targets.py` (edit).

**Validation.** Run `scripts/check_patch_targets.py` (capture output and `exit=$?`),
then `ruff check` and `mypy` on the file. Quote `All N patch() targets valid.` and
`exit=0`. **N must equal 5052** until T018 adds fixture targets; a drop means you
changed extraction behaviour.

---

### Subtask T015 — The census target classifier

**Purpose.** Classify every `patch()` target under a scanned tree with the **narrowed**
discriminator, and make the first-party boundary explicit, printed and overridable.

**Steps.**

1. Create `scripts/patch_seam_census.py`. Compute `_REPO_ROOT` from `__file__`, insert
   under the `test_docs_cli_reference_parity.py:51-53` guard, then
   `from scripts.check_patch_targets import resolve_patch_target  # noqa: E402`. That is
   the one inherited, narrowly-justified suppression — add no others.
2. Declare the first-party root set **explicitly and visibly**:
   - Derive the base set from the directory names under `src/` — today `charter`,
     `doctrine`, `glossary`, `kernel`, `mission_runtime`, `runtime`, `specify_cli`.
   - Union with a declared extras frozenset `{"tests", "spec_kitty_events",
     "spec_kitty_tracker"}` (installed distributions, not `src/` subdirectories).
   - Expose `--first-party-roots a,b,c` to override, and **echo the resolved set into
     the `--json` payload** under `first_party_roots`, so every report carries the
     definitional choice that produced its buckets.
   - Verified: all seven of the plan's roots import cleanly here, and the `tests/sync/`
     bucket counts are **invariant** between that 7-name set and the wider derived one
     — the 6 direct-foreign targets are `subprocess.run` and
     `asyncio.run_coroutine_threadsafe`, foreign under either.
3. Build the classifier as a **lookup-then-classify pair**, not one nested `if`: one
   function resolves (delegating to T014), one maps verdict → bucket. Ceiling **15**.
4. Extract sites with `ast`, never text matching (**NFR-007**). Walk `ast.Call` nodes
   whose callee is named `patch` (bare `patch(...)`, `@patch(...)`, and the
   `mock.patch(...)` attribute form) with a first positional `ast.Constant` string.
   Docstrings, comments and bare string literals contribute **nothing**.

**Files.** `scripts/patch_seam_census.py` (new).

**Validation.** `./.venv/bin/python scripts/patch_seam_census.py tests/sync --json`,
then `ruff check` on the file. Expected on the pre-fix tree, reproduced this session:
`total 664`, `own_module 357`, `reach_through 286`, `foreign 6`, `not_a_module 15`,
`unresolvable 0`. Also print the literal-predicate count (**649**) as a labelled
comparison so the 97.7% over-breadth stays visible in every report.

---

### Subtask T016 — The read-side matcher

**Purpose.** Decide which patched mocks are actually **read** by a count or equality
assertion — the half of the predicate that turns a patch site into a *corruptible
assertion*.

**Steps.**

1. Implement **per-form recognisers**, one small function each, dispatched from a
   table — never one growing `visit_Compare`: `assert_called*` method calls,
   `.call_count` comparisons, `len(<mock>.call_args_list) == N`, `.call_args` reads,
   and whole-list equality against a literal list.
2. **One level of alias resolution is load-bearing.** The canonical shape, opened and
   confirmed at `tests/sync/tracker/test_saas_client.py:783-786`:

   ```
   783    sleep_calls = mock_sleep.call_args_list
   784    assert len(sleep_calls) == 3
   785    delays = [c.args[0] for c in sleep_calls]
   786    assert delays == [0.9, 2.0, 4.4]
   ```

   Without it a probe misses `:784` and `:786` **entirely** — measured; the planner's
   own probe did exactly that.
3. **`side_effect=` sink tracking.** Confirmed at
   `tests/sync/test_final_sync_diagnostics.py:303` —
   `patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append)` — feeding
   the corruptible assertion at `:309`
   (`assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, …]`). Note `plan.md` and
   `spec.md` both cite `:309` as the *patch site*; `:309` is the **assertion**, the
   patch is at `:303`. Report both, keyed on the assertion line.
4. **`n=` must be read from the assertion's own cardinality expression**, never from
   the printed delay list's length — otherwise
   `assert 3.0 in [c.args[0] for c in mock.call_args_list]` prints `n=1 delays=[3.0]`
   *honestly* while asserting no cardinality. The `in`-form must report **`n=0`**.

**Files.** `scripts/patch_seam_census.py` (edit).

**Validation.** `./.venv/bin/python scripts/patch_seam_census.py tests/sync --contract`
— statically, without running `tests/sync`. Exactly the four SC-002 lines, in file
order, derived from live `ast.Assert` / assert-method-call nodes inside the named
functions.

---

### Subtask T017 — The CLI: three front doors, one analysis pass

**Purpose.** Make SC-001's invocation the documented, single entry point so the control
test consumes the census by subprocess and nothing needs to import it.

**Steps.**

1. Accept one or more path arguments (so `tmp_path` fixtures can be scanned) plus the
   mutually-exclusive modes `--json`, `--contract`, `--siblings`.
2. **One** analysis pass produces one in-memory result; the three modes are three
   renderers **dispatched via a dict**, not an `if/elif` chain.
3. The `--json` payload carries at minimum: `first_party_roots`, `buckets` (all five,
   `unresolvable` **included**), `literal_predicate_flagged`, `files_scanned` **per
   scope** (T020), `nodes_with_sleep_assertions`, `sleep_assertions`,
   `corruptible_assertions`, `sleep_seam_patch_sites`, and the full site list as
   `(file, line, node_id, patch_form, assertion_form, module, attr, verdict)` tuples.
   **FR-005 requires the gate to name what it scanned, not just count it.**
4. `--siblings` **derives** `correct-by-alias` / `corruptible` / `undisposed` from the
   resolver verdict. A printed literal is not acceptable (SC-013 sub-1).
5. Exit `0` on a successful analysis regardless of the buckets — this is a *reporter*,
   not the gate. WP05 owns the gate.

**Files.** `scripts/patch_seam_census.py` (edit).

**Validation.** Run all three modes plus `ruff check` on the file. `--siblings` must
report `test_saas_client.py:787` (`assert mock_randbelow.call_count == 3` — opened and
confirmed) and `:804` (`mock_monotonic.side_effect = [0.0, 301.0]` — opened and
confirmed), each with a **derived** disposition. `undisposed` in either slot fails.

---

### Subtask T018 — The committed control fixture modules

**Purpose.** Give the census a hand-derived ground truth with decoys a naive `grep`
over-counts and the AST does not. This is what makes NFR-007 checkable.

**Steps.**

1. Create `tests/architectural/_fixtures/patch_seam_control/` with **exactly these four
   modules** (non-`test_` names; **no `__init__.py`** — `_fixtures/org_packs/` has none
   either):

   | Filename | Contents |
   |---|---|
   | `seam_decorator_cases.py` | decorator `@patch(...)` positives: an `assert_called_once_with`, a `.call_count` comparison, and the one-level-alias whole-list equality shape from `test_saas_client.py:783-786` |
   | `seam_contextmanager_cases.py` | the two forms R1's census could not see — a `with patch(...)` context manager feeding a corruptible assertion, and a `side_effect=` kwarg sink feeding one |
   | `seam_negative_cases.py` | an own-module patch that must **not** be flagged; a monotonic-only function that must **not** count as a sleep node; and the `assert <value> in [c.args[0] for c in mock.call_args_list]` form, which must report **`n=0`** |
   | `seam_decoy_cases.py` | the three SC-015 decoys — a **docstring** quoting `mock_sleep.assert_called_once_with(9.9)`, a **comment** `# mock_sleep.call_count == 42`, and a bare **string literal** `'specify_cli.tracker.saas_client.time.sleep'` |

2. **Every literal `patch("…")` target in these four files must resolve** — including
   any quoted inside the docstring decoy, because `check_patch_targets.py`'s extractor
   is a regex over raw source. Use targets the fixture also patches live, so their
   resolvability is required by something other than the decoy.
3. Hand-derive the ground truth as you write and record it for T019 — do **not**
   transcribe it from `spec.md`. SC-015's prose truth (3 sleep-patched functions, 1
   monotonic-only, 2 corruptible assertions, 1 delay-sequence assertion, 3 decoys
   ignored, plus the 2 previously-invisible positives) is the **floor**, not the ceiling.
4. Confirm a naive `grep -c 'patch(' <fixture dir>` **over-counts** relative to the
   census, and record both numbers. That gap is the point of the fixture.

**Files.** the four modules above (new).

**Validation.** Run `scripts/check_patch_targets.py` (capture `exit=$?`), `ruff check`
over the fixture directory, the census `--json` over it, and
`pytest tests/architectural/_fixtures/ --collect-only -q`. `exit=0` is **mandatory** —
non-zero means you reddened an `[ENFORCED]` CI job. The new total must be
`5052 + <patch literals you added>`; state that arithmetic. `--collect-only` must
collect **0** tests.

---

### Subtask T019 — The control test

**Purpose.** Pin the ground truth **in-test**, prove the census is not emitting a
hardcoded table, and prove the two extractors over one tree have not silently
diverged. This subtask is the reason WP03 exists.

**Steps.**

1. Create `tests/architectural/test_patch_seam_census_control.py` with
   `pytestmark = [pytest.mark.architectural]`. Consume the census **only via
   subprocess** over its CLI — no `sys.path` insertion, no `# noqa: E402`.
2. **Arm A — fixture ground truth.** Run the census over the fixture directory and
   compare against T018's hand-derived truth. **Assert `frozenset` equality on the site
   sets**, not `len(x) == N`. Print observed-vs-ground-truth for every count (SC-015).
3. **Arm B — decoys defeated.** Assert the three decoys contribute nothing, and that
   `grep`'s count over the same directory is strictly greater than the census's. Report
   both numbers in the failure text.
4. **Arm C — the `in`-form reports `n=0`.** If it reports `n=1`, SC-002 is fakeable.
5. **Arm D — bucket counts over `tests/sync/`.** Pin `own_module / reach_through /
   foreign / not_a_module / **unresolvable**` as a frozenset of `(bucket, count)` pairs.
   **Pin `unresolvable` too** — classification runs through import success, so a thinner
   environment would otherwise shrink the flagged set for free.
   **Derive these by running your shipped analyzer and pin what it emits.** Do **not**
   copy `plan.md:838`'s `356 / 286 / 7`: an independent probe reproduced
   `357 / 286 / 6 / 15`, so two of the plan's three numbers would be **red on arrival**.
   Record the delta and the reason in your evidence.
6. **Arm E — self-mutation (SC-015).** Narrow the analyzer to today's five forms (drop
   context-manager `patch()` and `side_effect=` sink tracking) and require the control
   fixture to **fail**. Drive the narrowing through an injected parameter or a
   monkeypatched form table — never by editing the shipped file.
7. **Arm F — cross-check against `check_patch_targets.py`.** `plan.md:846-847` words
   this as "the AST site set over `tests/sync/` is a **superset** of the regex script's,
   non-empty difference in the other direction fails". **That arm is false on the base
   tree and would be red on arrival.** Measured: AST **664**, regex **667**, with
   **4 regex-only** and **1 AST-only** site:

   | Direction | Site | Why |
   |---|---|---|
   | regex-only | `test_sync_doctor.py:33` | inside a docstring |
   | regex-only | `test_saas_client.py:559` | inside a docstring |
   | regex-only | `test_saas_client.py:659`, `:669` | inside a docstring |
   | AST-only | `test_dossier_trigger.py:54` | a comment sits between `patch(` and the target string, so the regex's `\s*` cannot bridge it |

   All four regex-only hits are **docstrings — which NFR-007 requires the AST to
   exclude**. Restate the arm so it grades correctness rather than the extractors' known
   asymmetry: **the AST site set must be a superset of the regex set after removing
   regex hits falling inside a string-literal or comment span**, and the removed set
   must equal a pinned, named frozenset of those four sites. Print the difference in
   both directions. A *new* regex-only hit outside the pinned set fails; an AST-only hit
   is reported, not failed.

   **⚠ KEY THE PIN ON `(file, line)` ONLY — never on `(file, line, target)`.** WP02
   T009 step 2 **rewrites** `test_saas_client.py:559`'s target string from
   `specify_cli.tracker.saas_client.time.sleep` to `…saas_client._sleep`. WP03 and WP02
   both depend only on WP01, so both lanes are green in isolation and a
   target-keyed frozenset **breaks only at consolidation** — the worst possible place
   to discover it. The *line* is what this arm is actually about (a docstring the AST
   correctly excludes and the regex cannot); the *target* it happens to quote is not.
   Risk 4 flags a **different** WP02 coupling; this one is its own.
8. Every failure message names observed vs expected **and names the sites** — never a
   bare count.

**Files.** `tests/architectural/test_patch_seam_census_control.py` (new).

**Validation.** Run the control test with `-q -ra -p no:cacheprovider` redirected to a
file, plus `--collect-only -q`; then re-run `test_pytest_marker_convention.py`,
`test_golden_count_ban.py` and `test_gate_coverage.py` the same way. Quote the
`N passed` line **and** the collected count for both runs.

---

### Subtask T020 — Run the census on both trees; flag the two unratifiable counters

**Purpose.** Produce the pre-fix baseline later WPs compare against, and refuse to
silently pick a number where the criterion is unsatisfiable as written.

**Steps.**

1. Run the census on `98198e980` and on the pre-fix mission head, both with
   `./.venv/bin/python`, and **print `./.venv/bin/python -V` for each** — a delta
   measured across two interpreters is not a measurement.
2. Report `files_scanned` **per scope, labelled**: `tests/sync/` recursive = **141**
   (`find tests/sync -name '*.py' | wc -l`) and `tests/sync/tracker/*.py` = **22**, kept
   as an explicitly labelled sub-denominator.
3. **Flag SC-001's `files_scanned: 22` for operator ratification.** The criterion
   mandates a `tests/sync/` scan while pinning the number a *narrowed* scan produces —
   and a narrowed scope is BLOCKER-2's exact failure. Do not pick one silently.
4. **Flag `sleep_patch_sites: 14` in the same ratification.** It counts occurrences of
   `specify_cli.tracker.saas_client.time.sleep`; after FR-012's retargets **0** match,
   so a correct implementation reports `0` and fails. Restated as
   `sleep_seam_patch_sites`, matching `…saas_client.time.sleep` **or**
   `…saas_client._sleep` — **14** in either tree state. **The composition is already
   settled in `spec.md` — do not re-adjudicate it, and do not edit the spec.**
   `spec.md:504` records **14 live** occurrences (13 in `test_saas_client.py`, 1 in
   `test_saas_client_origin.py:229`) with the docstring at `test_saas_client.py:559`
   **excluded**, as NFR-007 requires, and explicitly retires the earlier
   "13 live + 1 docstring" reading as wrong. `analysis-report.md:231` agrees
   ("13 + 1, all resolving to one target"). Measure and report against that composition.
   One stale restatement of the retired parenthetical survives at `spec.md:566-567`;
   it is outside this WP's change set — record it, do not fix it.
5. List the **9** non-tracker `tests/sync/` instances by `file:line` with a
   `disposition: hardened|out-of-class` and a reason, per SC-001.
6. Record all of this in your WP evidence. Do **not** edit `spec.md`, `plan.md`,
   `analysis-report.md`, `wps.yaml`, or another WP's task file.

**Files.** none (measurement and evidence only).

**Validation.** `git rev-parse HEAD`, `./.venv/bin/python -V`,
`find tests/sync -name '*.py' | wc -l` (→ 141), `ls tests/sync/tracker/*.py | wc -l`
(→ 22). Prefer `git worktree add` over stashing this checkout — the C-001 window and the
`.venv` both live here.

---

## Definition of Done

Mark each subtask with `spec-kitty mark-status` only when its evidence line is in the
WP notes. **Evidence is quoted command output, not a claim.**

```
spec-kitty mark-status WP03 T014 done --evidence "<paste>"
…
spec-kitty mark-status WP03 done
```

| # | Evidence required |
|---|---|
| T014 | `All N patch() targets valid.` with `exit=0`, `N == 5052`; `ruff check` and `mypy` clean on the file |
| T015 | `--json` bucket dict quoted showing all five buckets **and** `first_party_roots`; the literal-predicate figure (649/664) printed alongside |
| T016 | `--contract` output quoted — exactly four lines, file order, `n=` from the cardinality expression; a note confirming the `in`-form reports `n=0` |
| T017 | all three modes run and quoted; `--siblings` shows a **derived** disposition for `test_saas_client.py:787` and `:804` |
| T018 | the four fixture filenames listed; `check_patch_targets.py` `exit=0` with the new total and the `5052 + k` arithmetic stated; `--collect-only` over `_fixtures/` → `0` tests; `ruff check` clean |
| T019 | control test `N passed` **and** collected count quoted; six arms named; the pinned bucket frozenset quoted; the cross-check difference printed in both directions; marker-convention / golden-count / gate-coverage suites still green |
| T020 | both `python -V` lines; `files_scanned` per scope (141 / 22); the ratification flag for `files_scanned: 22` **and** `sleep_patch_sites: 14` with the corrected `14 live` composition; the 9 non-tracker instances with dispositions |

For the WP as a whole:

- `./.venv/bin/ruff check scripts/ tests/architectural/` clean — **`ruff check` only,
  never `ruff format`**. `scripts/` is outside CI's `ruff check src tests` scope, so
  this is the only place it gets checked.
- No function in either script exceeds complexity **15**.
- `git diff --stat` touches only the four `owned_files` entries.
- `tests/sync` and `tests/cli` were **never run** — state this explicitly.

---

## Risks

1. **The plan's bucket numbers are red on arrival.** `plan.md:838` says `356 / 286 / 7`;
   measured `357 / 286 / 6`. *Mitigation:* T019 pins what the shipped analyzer emits and
   records the delta. Never transcribe a number you have not reproduced.
2. **The plan's cross-check arm is false on the base tree.** *Mitigation:* T019 arm F
   restates it against a pinned docstring-exception set and reports both directions.
3. **The fixture can red an `[ENFORCED]` CI job.** *Mitigation:* T018's binding rule —
   committed fixture targets resolve; hazardous cases go in `tmp_path`. The `exit=0`
   check is in the DoD.
4. **Latent coupling to WP02.** The fixture's targets resolve because `saas_client.py`
   keeps its bare `import time`. C-004 permits only the alias definitions and call-site
   rerouting, so this holds — but if WP02 removes `import time`, this fixture reds the
   enforced lint. Note the dependency so WP02's reviewer sees it.

   **The SECOND WP02 coupling, and the one that reds only at consolidation.**
   **WP02 T009 step 2 rewrites `test_saas_client.py:559`'s target string** (and `:715`'s)
   from `…time.sleep` to `…_sleep`. WP03 and WP02 share only WP01 as an ancestor, so
   both lanes are green alone and arm F's pinned docstring-exception set breaks **only
   when they land together** — if and only if it is keyed on the target. *Mitigation:*
   T019 arm F keys the pin on `(file, line)`. Do not re-introduce the target into the
   key "for precision".
5. **Double-import of the resolver.** Two module identities (`check_patch_targets` vs
   `scripts.check_patch_targets`) give two verdict enums that fail `is`/`==` across the
   boundary — the exact hazard `pytest.ini:2-9` documents. *Mitigation:* the census
   always imports under the `scripts.` name; the test never imports at all.
6. **`_mock_importer` executes module-level code.** Over `tests/sync/` today it reaches
   only `specify_cli.*` and stdlib — verified. Re-check before widening the scan.
7. **Complexity creep.** Five outcomes × several assertion forms trends toward one
   nested `if`. *Mitigation:* lookup-then-classify pair (T015), per-form recogniser
   table (T016), dict-dispatched renderers (T017).
8. **`len(x) == N` in the control test trips the golden-count ratchet.** The
   `tests/architectural` bucket is at **25/25 — zero headroom**
   (`_golden_count_baseline.json:6` freezes `25`; the live non-escaped count measured
   this session is `25`). **One** new `len(x) == N` reds `test_golden_count_ban.py`, and
   the six-arm control test is where a cardinality assertion is most likely to appear.
   *Mitigation:* frozenset equality throughout; the DoD re-runs
   `test_golden_count_ban.py`.

---

## Reviewer Guidance

Verify these, in order:

1. **There is exactly one resolver.** `grep -rn "importlib.import_module" scripts/` —
   `patch_seam_census.py` must not contain its own progressive-import walk. A second
   resolver is a single-canonical-authority breach and grounds for rejection.
2. **The discriminator is the narrowed one.** Confirm the census does not flag the 357
   own-module sites, and that there is **no hardcoded exclusion list** in
   `patch_seam_census.py` — search for literal `file:line` strings, node-id lists or
   filename allowlists. Any of these is the vacuity the instrument exists to prevent.
3. **The first-party root set is declared and printed** in the `--json` payload. A
   hidden constant makes the own/foreign boundary unauditable.
4. **`unresolvable` is pinned.** Absent from the pinned frozenset, a thinner environment
   shrinks the flagged set for free.
5. **Arm E actually reddens.** Run it yourself: narrow the analyzer, confirm the fixture
   fails. If it passes, SC-015 is decoration.
6. **Every fixture `patch()` target resolves** — `scripts/check_patch_targets.py` exits
   `0` — and **the fixture is not collected** —
   `pytest tests/architectural/_fixtures/ --collect-only -q` → 0 tests.
7. **`tests/sync` was not run.** Check the evidence for any `pytest tests/sync`
   invocation. The census is static; running the cone would breach C-001 and is needed
   for no claim here.
8. **Open every `file:line` the implementer cites.** Three inherited from
   `plan.md`/`spec.md` are off — assume nothing.
9. **Confirm the fixture filenames were reported** so `wps.yaml`'s C-009 glob can be
   replaced with exact names. Shipping the fixture without naming it leaves the manifest
   in the state C-009 forbids.
