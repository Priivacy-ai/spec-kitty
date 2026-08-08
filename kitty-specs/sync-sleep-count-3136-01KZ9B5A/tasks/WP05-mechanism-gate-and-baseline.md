---
work_package_id: WP05
title: The mechanism-keyed gate, its two-sided seam arm, and the frozen baseline made non-inert
dependencies:
- WP02
- WP03
requirement_refs:
- FR-005
- FR-010
- FR-012
- C-009
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
- T029
- T030
- T031
- T032
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_shared_module_object_patches.py
execution_mode: code_change
owned_files:
- tests/architectural/test_shared_module_object_patches.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_ratchet_baselines.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 – The mechanism-keyed gate, its two-sided seam arm, and the frozen baseline made non-inert

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this
work package's task type and `authoritative_surface`.

**Start command** (this is the only supported way to prepare the workspace):

```bash
spec-kitty implement WP05
```

Do **not** use `spec-kitty agent action implement` — that command only *displays* the prompt; it does
not claim the WP or prepare a workspace.

---

## Objective

WP05 closes the defect class **by construction**. It ships three things, and the third is why this WP
owns three files rather than two:

1. **The gate** — `tests/architectural/test_shared_module_object_patches.py`, a static AST reader over
   test source that refuses any `patch("a.b.c.attr")` whose penultimate segment resolves to a *foreign*
   module object reached through a first-party one, **when the resulting mock is read by a count or
   equality assertion** (FR-005, SC-007 items 1–3).
2. **The two-sided seam arm** — four parts (4a/4b/4c/4d) asserting WP02's alias seam is real on the
   product side *and* actually routed on the test side (FR-010 condition ii, FR-012, SC-007 item 4).
3. **The frozen shrink-only baseline, made non-inert** — one new top-level key in
   `tests/architectural/_baselines.yaml` **plus the four edits to `test_ratchet_baselines.py` without
   which that key is read by nothing** (SC-007 item 5, charter Burn-down Policy §a).

**The central risk of this WP is shipping a baseline nothing reads.** That is not a hypothesis. It is
the measured default outcome, and it is why `test_ratchet_baselines.py` is an owned file.

---

## Context

### ENVIRONMENT — read before typing a single command

**NEVER run a bare `uv run` or a bare `uv sync` in this tree.** A bare invocation re-solves against the
tracked `.python-version` (`3.11.15`), **destroys `.venv`**, and recreates it *without* `pytest`,
`ruff` or `mypy`. This has happened **three times in this mission**. Proof, non-destructive, re-run
while this prompt was written:

```
$ uv sync --dry-run --python 3.12
Would uninstall 70 packages     # pytest==9.0.3, ruff==0.15.12, mypy==1.20.2, pytest-xdist, pytest-cov …
```

The two sanctioned forms, and nothing else:

```bash
./.venv/bin/python -m pytest …            # preferred: no solve at all
./.venv/bin/ruff check …
uv run --python 3.12 --extra test --extra lint python -m pytest …
```

Recovery, if it happens anyway — and **record that it happened**:

```bash
uv sync --python 3.12 --extra test --extra lint
```

**PATH hazard, re-verified this session.** `command -v pytest` → `/home/jeroennouws/.local/bin/pytest`,
whose shebang is `#!/usr/bin/python` — an **unrelated checkout on the system interpreter**, not this
tree. `command -v python` → `/usr/bin/python`. Prepend `<repo>/.venv/bin` to `PATH`, and **quote
`command -v` output** before trusting any `--version`. Measured divergence to record, not to fix:
`.python-version` reads `3.11.15`; `./.venv/bin/python -V` reads `Python 3.12.13`.

### The ratchet is inert today — measured, and it must be re-derived in this WP

Every number below was re-derived by opening the file, not by trusting a citation. **Re-derive them
again at implementation time**; if any has moved, the moved value is the truth and this prompt is stale.

| Fact | Value | How |
|---|---|---|
| top-level keys in `_baselines.yaml` | **12** | `yaml.safe_load` |
| keys in `_REQUIRED_TOP_LEVEL_KEYS` (`test_ratchet_baselines.py:123-136`) | **11**, a hand-written `frozenset` | read the literal |
| keys read by **any** comparison (`data["…"]`) | **10** | `grep -oE 'data\["[a-z_0-9]+"\]'` |
| in YAML, read by nothing | **2** — `test_all_declarations_required`, `test_no_dead_symbols` | set difference |
| the missing-key check | `:214` — `missing = _REQUIRED_TOP_LEVEL_KEYS - set(data.keys())` — **missing only, never extra** | read the line |
| growth comparison list | `single_baselines` at `:274`, a hardcoded literal list | read it |
| shrinkage comparison list | `single_baselines` at `:420`, a **second** hardcoded literal list | read it |
| the suite is green with both keys inert | `pytest tests/architectural/test_ratchet_baselines.py -q` → 3 tests | `grep -n '^def test_'` → `:205`, `:238`, `:381` |

**The two inert keys have different causes, and therefore need different edits. This is the part R2 and
the plan both leave open, and this session measured it:**

- **`test_no_dead_symbols`** — in the YAML with **7** sub-keys, absent from `_REQUIRED`, absent from both
  comparison lists. It *does* publish importable module-scope frozensets
  (`_CATEGORY_A_SLICE_F_DEFERRED`, `_CATEGORY_B_GRANDFATHERED_LEGACY`, and five `_CATEGORY_C_*`), so it
  **can** be registered. And its recorded numbers have already drifted, unnoticed, because nothing reads
  them: YAML records `category_a_slice_f_deferred: 12` against a live `len(...)` of **9**, and
  `category_b_grandfathered_legacy: 193` against a live **189**. Both are *shrinkages*, so registering
  the key in both lists is **green-safe today** — growth passes, shrinkage warns. That is measured, not
  assumed. It is also the gate the charter's `__all__` Declaration Convention names as binding — heading
  at `charter.md:494`, body at `charter.md:496-500`, re-measured this session — so it is not an
  abandoned key.
- **`test_all_declarations_required`** — in `_REQUIRED` (so `missing` passes) but read by nothing, and
  it **structurally cannot** join `single_baselines`: the module is 105 lines with **no module-scope
  frozenset at all**, only two parametrized zero-tolerance tests, and its sub-keys are
  `charter_without_all: 0` / `kernel_without_all: 0` — pins, not allowlists. `_import_module_attr`
  (`:172`) does `importlib.import_module(...)` then `getattr(module, attr_name)` and takes `len()`; there
  is nothing there to take the length of.

**Consequence for this WP: a 13th key added naively joins them — read by nothing, growth fails nothing.**
Four edits are required (T030, T031), not one.

**Consequence for the gate module: it must publish a module-scope `frozenset` under a named attribute
whose `len()` is the allowlist size, importable as `tests.architectural.test_shared_module_object_patches`.**
That is the only shape `_import_module_attr` can read. A dict, a list, a local, or a value computed
inside a test function cannot be registered.

### The honest-ratchet precedent to copy

`tests/architectural/_inert_slots_baseline.yaml` + `tests/architectural/test_no_inert_schema_slots.py`
(+ its helper `tests/architectural/_inert_slots.py`). Every line number below was opened and verified:

| Mechanism | Where | Why copy it |
|---|---|---|
| Permanently-empty allowlist, pinned by its own arm | `_inert_slots.py:73` `ALLOWLIST: frozenset[str] = frozenset()`; `test_no_inert_schema_slots.py:989` `test_allowlist_is_empty` → `assert frozenset() == ALLOWLIST` | The **baseline** is the mutable surface; the allowlist never grows. Note the assertion is a **frozenset equality**, not a length. |
| Per-row `owner:` and `disposition:` from a closed vocabulary | `_inert_slots.py:425-427` `DISPOSITIONS = frozenset({"wire-the-producer", "delete-the-declaration", "fix-the-lint-definition"})`, with `:423-424` stating there is deliberately **no** `accepted` / `wont-fix` / `by-design` | A row cannot be excused — only fixed, deleted, or reclassified as a checker defect. |
| Owner-completion arm | `test_no_inert_schema_slots.py:680` `test_a_baseline_entry_does_not_survive_its_owner`, with its own non-vacuity twin named in the docstring | This is what stops a frozen baseline becoming permanent. |
| Owner-resolution arm | `:871` `test_every_named_owner_resolves` | `WP42` / `mission:typo` reads as "never complete" exactly like `unassigned`. |
| Ratchet-registration arm | `:971` `test_the_baseline_size_is_registered_with_the_charter_ratchet` (plus siblings at `:928`, `:948`) — reads `_baselines.yaml` and asserts `recorded == len(BASELINE_SLOTS)` | **This is precisely the arm whose absence is BLOCKER-3.** The precedent already knows a baseline must assert its own registration. |
| Registered in **both** comparison lists | `test_ratchet_baselines.py:318-323` (growth) and `:464-469` (shrinkage) — same 4-tuple, twice; both spans re-measured by opening the file | The precedent is *itself* registered twice. That is the shape T030 copies. |
| Header cites the policy and the tactic by name | `_inert_slots_baseline.yaml:8` — *"Ratchet semantics (charter Burn-down Policy §a, `frozen-baseline-shrink-only-ratchet`)"* | This mission's baseline entry must cite both too. |

The **`frozen-baseline-shrink-only-ratchet` tactic** (charter.md:77) additionally requires a **stated
shrink rate** and a **target-zero release**, and names *"entries accumulate indefinitely with no stated
target"* as a failure mode. The baseline entry must carry both. `_baselines.yaml`'s own per-PR edit
policy (`:12-17`) requires a `# justification:` comment on any growing line.

### The gate's predicate — narrowed, and measured

The **naive** form ("penultimate segment resolves to a `ModuleType`") flags **649 of 664** `patch()`
string-target sites under `tests/sync/` — because patching an attribute of a module is the *ordinary*
case. Measured this session by resolving every target with `importlib`.

The **narrowed** predicate WP03 ships — *resolved module `__name__` ≠ the dotted path, **or** the module
is not first-party* — flags **293**. (The plan says ~292; the delta is the choice of first-party root
set. Re-derive it against WP03's shipped analyzer and report the number you get; do not carry either
figure forward unchecked.) Top contributors, measured:

| flagged | target |
|---:|---|
| 130 | `specify_cli.tracker.saas_client.httpx.Client` |
| 65 | `specify_cli.sync.batch.requests.post` |
| 30 | `specify_cli.sync.git_metadata.subprocess.run` |
| 14 | `specify_cli.tracker.saas_client.time.sleep` |
| 9 | `specify_cli.tracker.saas_client.time.monotonic` |
| 1 | `specify_cli.tracker.saas_client.secrets.randbelow` |

**The `httpx.Client` bucket is the whole ballgame, and this session resolved it.** All **130** sites bind
their mock to `mock_cls` (114), `mock_http_cls` (13) or `mock_httpx_client_cls` (3), and **0** of those
bound mocks are read by `.call_count`, `.assert_called*` or `.call_args*` anywhere under `tests/sync/`.
So they fall out — **but only through the read-side half of the predicate, never through the mechanism
half.** The mechanism predicate alone flags all 130. That is why the read-side condition must be
*enforced in code*, not documented in a docstring: without it the gate demands a 130-row baseline and is
unshippable. T032 re-measures this against the real gate; `[UNVERIFIED-D]` (`plan.md` item 12) closes
there or nowhere.

### The baseline is ~29 rows, and that is the honest number

The class spans **≥ 29 in-class instances across ≥ 10 files**, all outside R-1's seam and therefore
frozen rather than fixed in this mission. A coarse function-scope probe run this session found candidate
sites in **14** files, which brackets the claim from above. Named contributors, each `file:line` opened:

- `tests/sync/test_git_metadata.py` — `:226`, `:249`, `:281`, `:471`, `:530` (`mock_run.call_count`), plus
  four `time.monotonic` clock couplings **including the context-manager form at `:522`** that a
  decorator-only census cannot see, plus `:398` (`mock_run.call_args.kwargs`, a **last-call** read).
- `tests/sync/test_final_sync_diagnostics.py:309` — under the context-manager `patch(...)` at `:303`
  with a `side_effect=` kwarg. This is the form that hid from R1's census entirely.
- `tests/sync/test_runtime.py:673` and `:710` — bare stdlib target `patch("asyncio.run_coroutine_threadsafe")`.
- **9** `mock_post` / `mock_get` count-or-equality reads under bare `import requests`, across
  `test_batch_sync.py`, `test_batch_error_surfacing.py`, `test_batch_retry_hygiene.py`,
  `test_body_transport.py`, `test_batch_400_no_details_poison_2736.py`.

**Freezing this is a documented exception, not a pass** (SC-007 item 5 says "shrink-only, *not* empty at
merge"; the exception lives in `plan.md` `## Complexity Tracking`). Narrowing the *enforced scope*
instead of freezing the residue is verbatim BLOCKER-2 and is refused. Each row carries a named owner
whose **completion** fails the row.

### The seam arm needs a positive twin

A negative assertion ("**0** reach-through calls") is satisfied by a checker that parses the wrong file,
or parses nothing at all. Arm 4d is not optional garnish: it reports the **3** alias definitions **by
name** and the **5** rerouted call sites **by line**, so a broken checker fails loudly instead of passing
quietly. Same reasoning applies to the seam-routing arm as a whole — it needs a fixture where the seam
*is* bypassed and which **must be flagged**.

### Amend the gate's self-description

The existing inline-gate header states that it performs no call-graph resolution. **This gate resolves
imports** — arm 4a walks the module's own `ast.Import` / `ast.ImportFrom` bindings including `asname`.
Correct the docstring in the same change. Do not leave a self-description that misleads the next author;
that is the exact failure mode (`test_saas_client.py:55-57`) that produced this mission.

### Conventions this WP must satisfy

- **`pytestmark = [pytest.mark.architectural]`** at module scope on the new file.
  `test_pytest_marker_convention.py`'s `_module_has_pytestmark` accepts both the singleton and the list
  form; the two nearest siblings both use the **list** form — `test_ratchet_baselines.py:47` and
  `test_no_inert_schema_slots.py:300`, both `pytestmark = [pytest.mark.architectural]`. Prefer the list
  form to match. *(Note: `plan.md` cites this precedent at `test_no_inert_schema_slots.py:53`; the actual
  line is `:300`. Verified.)*
- **Arch shard registration is NOT needed.** `tests/_arch_shard_map.py:381` sets `default_fallback=True`,
  so a new architectural file is auto-covered.
- **`tests/architectural/` entries in `owned_files` are file-level, never a `**` glob** (C-009). WP03 owns
  `test_patch_seam_census_control.py` and `_fixtures/patch_seam_control/` in this same directory; a glob
  would union the two lanes into one.
- **Importing WP03's analyzer from `scripts/`** needs the canonical `sys.path` insertion — the in-repo
  shape is `tests/architectural/test_docs_cli_reference_parity.py:50-56`:
  `_REPO_ROOT = Path(__file__).resolve().parents[2]`, `if str(_REPO_ROOT) not in sys.path: sys.path.insert(0, str(_REPO_ROOT))`,
  then `from scripts.… import …  # noqa: E402`. That `noqa` is inherited, not invented.
- **`len(x) == N` is effectively banned here, and it is harder than a preference.**
  `tests/architectural/_golden_count_baseline.json:6` freezes `"tests/architectural": 25`, and the live
  non-escaped `convert` count measured this session is **25**. **Zero headroom.** One new
  `assert len(something) == 3` in either owned file reds `test_golden_count_ban.py`. Assert the **set**
  (`assert expected == actual_frozenset`) — stronger contract, names the delta on failure, and
  classified `keep` when the compared literal is empty. The escape marker, if a site is genuinely
  cardinality-only, is `# golden-count: cardinality-is-contract` on the assertion's own physical line.
- `ruff check` only — **never** `ruff format`. Complexity ceiling **15**: the seam arm has four parts, so
  write **four functions**, not one.

### Discipline

- **Do NOT run `tests/sync` or `tests/cli`.** C-001 forbids it, and this gate is a **static AST reader
  over that source** — it never collects those modules. If you find yourself needing to run them, the
  gate is wrong.
- Redirect suite output to a file, then **quote the `N passed` line verbatim** and print the selected
  count. Use `-ra`, never `-rf`.
- **A cited `file:line` is not evidence that the line says what the citation claims — open every one.**
  Citations in the incoming artifacts were already wrong — **including one of the *corrections*** (see
  Reviewer Guidance).

### This WP's notes file — named, replacing the `<wp-notes>` placeholder

Every "recorded in the WP notes" in this prompt, and DoD item 11's former literal `<wp-notes>`
placeholder, means exactly one path:

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/mechanism-gate-3136.md
```

It is a **declared out-of-map planning write** (`wps.yaml`'s WP05 block) — `owned_files` may not
carry any path under `kitty-specs/`, so it is named there instead. **Create it before the first
command runs** and write the `command -v` / `--version` block into it first, so it is non-empty by
construction; a `grep -c` negative over an absent file prints no count and exits `2`, which reads as
satisfied. A DoD graded against a placeholder is graded against nothing.

---

### Subtask T025 — Author the gate module and state the `_leak_guard` split in one sentence

**Purpose.** Create the gate file with the marker, the analyzer import, and a docstring that prevents the
next author from breaking a different guard.

**Steps.**
1. Create `tests/architectural/test_shared_module_object_patches.py` with
   `pytestmark = [pytest.mark.architectural]` at module scope.
2. Import WP03's analyzer (`scripts/patch_seam_census.py`) via the `test_docs_cli_reference_parity.py:50-56`
   `sys.path` shape. **Do not re-implement the predicate** — a second implementation is the duplicate
   authority the charter's Standing order 6 forbids, and it is why this WP depends on WP03.
3. Write the module docstring. It **must** contain one sentence stating the split from
   `tests/sync/_leak_guard.py`: that module snapshots a global's **value** across a test node and reports
   **teardown residue** (`_WATCHED_GLOBALS` at `:101`, **17** elements — verified as `2 + 1 + 14` from
   `_WATCHED_SINGLETONS` `:58`, `_WATCHED_CARRY_FORWARD` `:71`, `_WATCHED_FIXTURE_DATA` `:84`); this gate
   is a **static AST reader over test source that never runs a test**. Without that sentence the next
   author adds `time.sleep` to `_WATCHED_GLOBALS` and gets a guard that cannot fire — `time.sleep` is
   correctly absent there because `patch`'s own teardown restores it.
4. Reuse `_leak_guard.py`'s `(module_path, attr_path, description)` vocabulary in the baseline row shape.
   One authority for the vocabulary, two enforcement points.
5. **Amend the inline-gate self-description** that claims no call-graph resolution (see Context).

**Files.** `tests/architectural/test_shared_module_object_patches.py` (create).

**Validation.** `./.venv/bin/python -m pytest tests/architectural/test_pytest_marker_convention.py -q -ra`
→ quote the `N passed` line. `./.venv/bin/ruff check tests/architectural/test_shared_module_object_patches.py`
→ `EXIT=0`. `grep -c '_leak_guard' tests/architectural/test_shared_module_object_patches.py` ≥ 1.

---

### Subtask T026 — Arms 4a and 4b (product side), as two separate functions

**Purpose.** Refuse the reach-through *and* refuse the wrapper form. These are the only arms that make
WP02's seam structurally safe rather than incidentally green.

**Steps.**
1. **4a — zero *resolved* reach-through calls, no carve-out.** Assert
   `src/specify_cli/tracker/saas_client.py` contains **0** calls whose callee **resolves** to
   `time.sleep` / `time.monotonic` / `secrets.randbelow`. Resolve against the module's **own**
   `ast.Import` / `ast.ImportFrom` bindings **including `asname`**, so `import time as t; t.sleep(x)`,
   `from time import sleep; sleep(x)` and `getattr(time, "sleep")(x)` are all caught. Shape:
   `tests/architectural/test_protection_resolver_call_sites.py:90-109` — `ast.parse` → `ast.walk` →
   `isinstance(node, ast.Call)` → resolve `node.func`. `def _find_bare_protected_branches_calls` is at
   **`:90`**; its `ast.walk` comprehension runs **`:103-109`**. `plan.md` cites `:90-109` in all five
   places (`:264`, `:521`, `:1020`, and `spec.md:724`, `:992`) and is correct — re-measured by opening
   the file this session.
   **R2's "outside the three alias definitions" carve-out is STRUCK** — under the wrapper form the only
   `time.sleep(` *is* inside the alias definition, so the carve-out made the negative true while the
   defect was fully intact.
2. **4b — the three names are bound by assignment.** Assert each of `_sleep` / `_monotonic` /
   `_randbelow` is a module-scope `ast.Assign` whose value resolves to exactly `time.sleep` /
   `time.monotonic` / `secrets.randbelow` — **not** an `ast.FunctionDef`. This is a *structural* arm on
   purpose: a wrapper alias with all 24 retargets complete is runtime-immune and passes every behavioural
   criterion in the spec, so no runtime arm can catch it.
3. Two functions, not one (complexity ceiling 15).

**Files.** `tests/architectural/test_shared_module_object_patches.py`.

**Validation.** Both arms green on the WP's final tree. Report **why 4b is not a style preference**: under
assignment an un-retargeted decorator fails loudly (recorder sees `0`); under the wrapper it passes
silently with the defect intact.

---

### Subtask T027 — Arms 4c and 4d (test side, and the positive twin)

**Purpose.** Without 4c the whole seam lands **inert** — that is BLOCKER-1, and it was the default
outcome of R2's plan. Without 4d a checker that parses nothing passes.

**Steps.**
1. **4c — the target strings actually moved (FR-012).** Over
   `tests/sync/tracker/test_saas_client.py` and `tests/sync/tracker/test_saas_client_origin.py`, assert:
   **0** `patch()` targets equal to `specify_cli.tracker.saas_client.time.sleep`,
   `…time.monotonic`, or `…secrets.randbelow`; and post-fix **`13 + 1 = 14`** targeting `…_sleep`,
   **9** targeting `…_monotonic`, **1** targeting `…_randbelow`. Re-derived this session by AST:
   `test_saas_client.py` carries 13 sleep + 9 monotonic + 1 randbelow, `test_saas_client_origin.py`
   carries 1 sleep — **24 total**, matching FR-012 exactly.
2. **Count from AST `patch()` call nodes, NEVER from `grep`.** `test_saas_client.py:559` carries the
   pre-fix string `specify_cli.tracker.saas_client.time.sleep` **inside the `:513-762` docstring**. A
   grep-based arm counts it and reports `1` where the correct answer is `0`, and the natural "fix" is to
   edit prose to satisfy a numeric gate — the failure mode this mission has now hit three times. The
   docstring occurrence should be updated for consistency by WP02, but it is **not** one of the 24 and
   **must not** be counted here.
3. **4d — the positive twin.** Report the **3** alias definitions **by name** and the **5** rerouted call
   sites **by line**. The pre-fix lines are `:439`, `:481`, `:484`, `:515`, `:518`; adding three
   module-scope definitions shifts every later line, so **take the post-fix numbers from WP02's landed
   tree** (`plan.md` `[UNVERIFIED]` item 8) and record them. Test-file line numbers do not move —
   retargeting is in place.

**Files.** `tests/architectural/test_shared_module_object_patches.py`.

**Validation.** Both arms green. Print the 4d report. Then prove 4c is non-vacuous by pointing it at a
synthetic pre-fix copy and showing it reds — a `14/9/1` arm that passes on a pre-fix tree is broken.

---

### Subtask T028 — Non-vacuity: name what was scanned, and self-mutate on absent forms

**Purpose.** SC-007 items 1–3. A count floor is satisfiable without ever opening the files that matter.

**Steps.**
1. **Name the files opened**, not a count. The named set must include
   `tests/sync/tracker/test_saas_client.py`, `tests/sync/tracker/test_saas_client_origin.py`,
   `tests/sync/test_final_sync_diagnostics.py`, `tests/sync/test_git_metadata.py`. R1's
   `scanned_files >= 22` is satisfied by globbing any 22 files under `tests/` while never opening
   `tests/sync/tracker/` — the squad's named cheat.
2. Report the patch-site split **`13` + `1` = `14`** and the **four census node-ids verbatim**:
   `TestPolling::test_exponential_backoff_intervals`,
   `TestRetryBehaviors::test_429_respects_retry_after`,
   `TestRetryBehaviors::test_429_defaults_to_5s_when_missing`,
   `TestSearchIssues::test_429_retries_then_raises`.
3. **Three self-mutation arms**, each on a synthetic in-memory module whose form is **absent from the
   tree today**:
   (a) `assert mock_sleep.call_count == 1` under a decorator patch;
   (b) `assert mock_run.call_count == 1` under `@patch("pkg.mod.subprocess.run")` — proving the predicate
   is keyed on the **mechanism**, not on `time.sleep`;
   (c) a **context-manager** `patch()` with a `side_effect=` kwarg feeding a list-equality assertion —
   the two blind spots that hid `test_final_sync_diagnostics.py:309`.
4. **The seam-routing positive twin.** A fixture in which the seam *is* bypassed must be **flagged**. A
   negative-only seam arm is satisfied by a checker that resolves nothing.
5. **Frozenset equality everywhere a collection is pinned.** `tests/architectural` sits at **25/25**
   against the golden-count ceiling — a single `len(x) == N` reds `test_golden_count_ban.py`.

**Files.** `tests/architectural/test_shared_module_object_patches.py`.

**Validation.**
```bash
./.venv/bin/python -m pytest tests/architectural/test_shared_module_object_patches.py -q -ra -p no:cacheprovider > /tmp/wp05-gate.txt
./.venv/bin/python -m pytest tests/architectural/test_golden_count_ban.py -q -ra
```
Quote the `N passed` line from each, print the selected count, and paste the gate's own named-file and
node-id output verbatim.

---

### Subtask T029 — The frozen shrink-only baseline key

**Purpose.** Freeze the ~29-row residue as **debt with owners**, not as an allowlist of excuses.

**Steps.**
1. Add **one** new top-level key to `tests/architectural/_baselines.yaml`.
2. **Every row is a `file:line` + patch target + assertion-form triple**, so the baseline cannot be
   widened by restatement. Reuse `_leak_guard.py`'s `(module_path, attr_path, description)` vocabulary
   plus the `#3115` inventory row-id column where one exists.
3. **Per-row `owner:` and `disposition:`.** Disposition is restricted to exactly three structural values
   modelled on `_inert_slots.py:425-427`; there is deliberately **no** `accepted`, no `wont-fix`, no
   `by-design`. Every named owner must resolve to a real WP or mission.
4. `# justification:` comment per the per-PR policy at `_baselines.yaml:12-17`, citing the charter's
   **Burn-down Policy §a** (`charter.md:481-489`) and the **`frozen-baseline-shrink-only-ratchet`**
   tactic **by name**.
5. **State a shrink rate and a target-zero release.** The tactic names *"entries accumulate indefinitely
   with no stated target"* as a failure mode; **`charter.md:487-488`** (Burn-down Policy §b,
   re-measured this session) shows the in-repo form — *"`test_no_dead_modules._CATEGORY_7_GRANDFATHERED`
   (Cat-7) shrinks by ≥2 entries per major release; **target 0 by 4.0**"*. `:490` is §c, a
   target-without-a-rate form; copy §b's shape, which carries both.
6. Record this as a **documented exception** against R2's SC-007 item 5 ("empty at merge"), which is
   incompatible with the measured residue. Narrowing the enforced scope instead is BLOCKER-2 — refused.
7. Publish the module-scope `frozenset` in the gate module whose `len()` **is** this baseline's size, so
   T030 can register it.

**Files.** `tests/architectural/_baselines.yaml`, `tests/architectural/test_shared_module_object_patches.py`.

**Validation.** `./.venv/bin/python -c "import yaml,pathlib; print(len(yaml.safe_load(pathlib.Path('tests/architectural/_baselines.yaml').read_text())))"`
→ **13**. Report the row count and confirm the frozenset is importable:
`./.venv/bin/python -c "import tests.architectural.test_shared_module_object_patches as m; print(len(m.<ATTR>))"`.

---

### Subtask T030 — Register the key: three edits, because there are two lists

**Purpose.** An unregistered key is read by nothing and its growth fails nothing. This is BLOCKER-3.

**Steps.**
1. Add the new key to **`_REQUIRED_TOP_LEVEL_KEYS`** (`test_ratchet_baselines.py:123-136`).
2. Add it to the **growth** `single_baselines` list (`:274`).
3. Add it to the **shrinkage** `single_baselines` list (`:420`). *(R2's plan named neither list. The
   directive's "both `single_baselines` lists" is why this is two edits, not one.)*
4. The 4-tuple shape is `(label, module_dotted, attr_name, data[key][subkey])` — copy
   `test_no_inert_schema_slots`'s registration verbatim from **`test_ratchet_baselines.py:318-323`**
   (growth; the tuple opens at `:318` and its closing `),` is `:323` — `:324` is the *next* entry's
   comment) and **`:464-469`** (shrinkage). Both re-measured by opening the file this session.
   `module_dotted` is `tests.architectural.test_shared_module_object_patches`; `attr_name` is the
   frozenset from T029.
5. **Re-derive the counts first** and record them: 12 YAML keys → 13; 11 required → 12; 10 read → 11.

**Files.** `tests/architectural/test_ratchet_baselines.py`.

**Validation.**
```bash
./.venv/bin/python -m pytest tests/architectural/test_ratchet_baselines.py -q -ra -p no:cacheprovider
```
Quote the `N passed` line. Then prove registration **bites**: bump the YAML number down by one, show
`test_growing_an_allowlist_above_baseline_fails` **reds**, and restore. A registration that cannot be
made to fail is not registered.

---

### Subtask T031 — The fourth edit: reverse containment, plus the owner arms

**Purpose.** So the *next* inert key is caught at the moment it is added, instead of sitting green for
years the way two already have.

**Steps.**
1. Add a **reverse-containment arm**: `set(data) - _REQUIRED_TOP_LEVEL_KEYS == ∅`. Prefer set equality
   over any count (golden-count ceiling, and the failure message names the delta).
2. **This arm is RED on today's tree** because of `test_no_dead_symbols` — which is exactly the proof it
   is non-vacuous. Do not delete the arm to make it green. **Pick a disposition explicitly:**
   - register `test_no_dead_symbols` in **both** comparison lists — measured safe: its live sizes are
     **below** the recorded numbers (A: 9 vs 12, B: 189 vs 193), both shrinkages, which **warn**, never
     fail; **or**
   - remove it from the YAML.
   - **Adding it to `_REQUIRED` alone is not an option** — that reproduces
     `test_all_declarations_required`'s defect (required, never read).
   - `test_all_declarations_required` needs a **different** answer: it publishes no importable frozenset,
     so it cannot join `single_baselines` as-is. Either give it a bespoke pin arm reading its two
     zero-tolerance sub-keys, or drop it from `_REQUIRED`. Do not conflate the two keys.
   - **`[UNVERIFIED]`** (`plan.md` item 10): which disposition is *correct* needs the owner of the gate
     each key governs, and is out of this mission's scope to decide unilaterally. **Do not silently
     pick.** If unresolvable in-mission: scope the arm to keys added from this mission forward, file the
     pre-existing pair as a tracked gap, and say so in the WP notes.
3. Add the **owner-completion arm** copied from `test_no_inert_schema_slots.py:680`, **with its own
   anti-weasel self-mutation twin** — the precedent's own docstring notes that as of today no owner has
   completed, so the assertion passes without exercising anything unless a twin forces it.
4. Add the **owner-resolution arm** from `:871`.
5. Add the **registration arm** modelled on `:971` — `recorded == len(<the gate's frozenset>)` — so the
   registration cannot drift into a number nobody compares against anything.

**Files.** `tests/architectural/test_ratchet_baselines.py`,
`tests/architectural/test_shared_module_object_patches.py`.

**Validation.** Full arch-suite run for the two owned test modules, `-ra`, output redirected, `N passed`
quoted. Then demonstrate each new arm can red: add a throwaway 14th YAML key → reverse containment reds;
revert. Record the disposition chosen for `test_no_dead_symbols` **and the reason**, or record the
scoped-arm fallback and the filed gap.

---

### Subtask T032 — Run the gate against the 130 `httpx.Client` sites and report

**Purpose.** Close `[UNVERIFIED-D]` — *"the largest single unmeasured risk to the gate's shippability"*
(`plan.md` item 12) — by measurement, not assumption.

**Steps.**
1. Run the shipped gate over `tests/sync/` and report whether it **excludes** all **130**
   `patch("specify_cli.tracker.saas_client.httpx.Client")` sites or flags them.
2. Report **which half of the predicate** does the excluding. Measured this session: the mechanism half
   flags all 130 (`httpx` is a foreign module reached through a first-party one); the **read-side** half
   is what drops them, because **0** of the bound mocks (`mock_cls` ×114, `mock_http_cls` ×13,
   `mock_httpx_client_cls` ×3) are read by `.call_count` / `.assert_called*` / `.call_args*` anywhere
   under `tests/sync/`. If the shipped gate disagrees with that, **the shipped gate is the truth** — say
   so and re-derive.
3. Report the total flagged-site count against the measured **293** narrowed / **649** naive / **664**
   total, and confirm the baseline matches the gate's own flagged set **by frozenset equality, not by
   count** — `frozenset(baseline_rows) == frozenset(gate_flagged_sites)`, printing the symmetric
   difference on failure. Equal counts over unequal sets is a hand-maintained list that has drifted;
   worse, a baseline row with no corresponding flagged site is **frozen in forever** by the
   shrink-only ratchet and nothing can ever remove it.
4. If the gate *does* flag the 130, **do not add 130 baseline rows.** That is the unshippable outcome;
   fix the read-side condition instead and say what was wrong with it.

**Files.** No file edits beyond fixes this measurement forces.

**Validation.** Paste the gate's flagged-site report. State the three numbers (total / naive / narrowed /
flagged) and the `httpx.Client` verdict in one line each.

---

## Definition of Done

Evidence for this WP is a **`spec-kitty agent tasks mark-status` record per subtask**, not a ticked box
in this file:

```bash
spec-kitty agent tasks mark-status T025 --status done
spec-kitty agent tasks mark-status T026 --status done
spec-kitty agent tasks mark-status T027 --status done
spec-kitty agent tasks mark-status T028 --status done
spec-kitty agent tasks mark-status T029 --status done
spec-kitty agent tasks mark-status T030 --status done
spec-kitty agent tasks mark-status T031 --status done
spec-kitty agent tasks mark-status T032 --status done
```

A subtask is done only when all of the following hold:

1. `tests/architectural/test_shared_module_object_patches.py` exists, carries
   `pytestmark = [pytest.mark.architectural]`, consumes WP03's analyzer rather than re-implementing the
   predicate, and its docstring carries the one-sentence `_leak_guard.py` split.
2. All four seam-arm parts exist as **separate functions**, and 4c has been shown to **red** on a
   synthetic pre-fix copy.
3. The three self-mutation arms and the seam-routing positive twin all fire on forms absent from the
   tree today.
4. `_baselines.yaml` has **13** top-level keys, and the new key's rows each carry a
   `file:line` + target + assertion-form triple, an `owner:`, a `disposition:` from the closed
   three-value vocabulary, a `# justification:` comment, a stated shrink rate and a target-zero release.
5. `test_ratchet_baselines.py` carries **all four** edits: `_REQUIRED_TOP_LEVEL_KEYS`, the growth list
   (`:274`), the shrinkage list (`:420`), and the reverse-containment arm — plus the owner-completion,
   owner-resolution and registration arms.
6. Registration has been **proved to bite**: a deliberate one-line YAML perturbation reds the growth
   test, and is reverted.
7. The `test_no_dead_symbols` disposition is recorded **explicitly** with its reason, or the scoped-arm
   fallback is recorded with the pre-existing pair filed as a tracked gap. Silently deleting the arm is
   a rejection.
8. `./.venv/bin/ruff check tests/architectural/` → `EXIT=0`. `ruff format` was never run.
9. `./.venv/bin/python -m pytest tests/architectural/test_golden_count_ban.py tests/architectural/test_pytest_marker_convention.py -q -ra`
   → `N passed`, quoted. The `tests/architectural` golden-count bucket is **≤ 25**.
10. `tests/sync` and `tests/cli` were **never run** by this WP.
11. **The WP notes exist, are non-empty, and the `uv run` negative has a positive twin.** The bare
    negative alone is the trap WP07 T037 names and closes: on an **absent** file `grep -c` prints no
    count and exits `2`, which reads as satisfied. Copy T037's construction — `test -s`, a line count,
    a same-file twin that must be `≥ 1`, *then* the negative:
    ```bash
    NOTES=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/mechanism-gate-3136.md
    test -s "$NOTES" && echo "NON-EMPTY: $(wc -l < "$NOTES") lines"   # must print a line count
    grep -c 'command -v' "$NOTES"                                     # twin: must be >= 1
    grep -c 'uv run' "$NOTES"                                         # every hit carries
                                                                      # --python 3.12 --extra test --extra lint
    ```
    Record all four results. A bare `0` from the last command with no `test -s` and no twin above it
    is **not** evidence.
12. **T032's `httpx.Client` verdict is recorded with the four counts — AND the baseline is graded by
    SET EQUALITY, not by count.** `assert frozenset(baseline_rows) == frozenset(gate_flagged_sites)`,
    with the symmetric difference printed on failure. A count-only check passes on a baseline that is
    **too large** — rows for sites the gate does not flag — and because the ratchet is shrink-only,
    those rows are then frozen in forever and nothing can ever remove them. Equality is the only arm
    that catches a baseline row with no corresponding flagged site.

If a subtask cannot be completed, mark it `blocked` with the reason named — never `done` with a caveat
in prose.

---

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **The baseline key is added and nothing reads it** — it joins the two already-inert keys, growth fails nothing, and the WP looks complete. This is BLOCKER-3 and it is the *default* outcome. | Four edits (T030, T031), and T030's validation **proves registration bites** by making the growth test red on purpose. A registration that cannot be made to fail is not registered. |
| R2 | **The reverse-containment arm is deleted because it is red on the base tree.** | Its redness is the proof of non-vacuity. T031 requires an explicit disposition or a scoped-arm fallback with the gap filed. Deletion is a rejection. |
| R3 | **The gate flags all 130 `httpx.Client` sites** and the response is a 130-row baseline. | The read-side condition must be **enforced in code**. Measured: 0 of the 130 bound mocks are read by count/equality, so a correct gate excludes them. T032 measures it; if the gate flags them, fix the gate, not the baseline. |
| R4 | **The gate globs `tests/**`, reports a count floor, and never opens `tests/sync/tracker/`.** | SC-007 item 1 requires **named** files (four named); item 2 the `13 + 1 = 14` split and four node-ids verbatim. A count floor is insufficient by construction. |
| R5 | **Arm 4 passes on a tree where not one decorator moved** — the whole seam lands inert (BLOCKER-1). | Arm 4c pins the **test-side** target strings: 0 pre-fix, 14/9/1 post-fix, counted from AST nodes. Product-side arms alone cannot catch this. |
| R6 | **The wrapper form `def _sleep(s): time.sleep(s)` makes the 24 retargets look optional** — and it is runtime-immune, passing every behavioural criterion. | Arm 4b is structural: `ast.Assign` resolving to the stdlib attribute, **not** `ast.FunctionDef`. No runtime arm can catch this; 4b must be static. |
| R7 | **Arm 4's negative is satisfied by a checker that parses nothing.** | Arm 4d, the positive twin: 3 aliases by name, 5 call sites by line. Same for the seam-routing arm's bypass fixture. |
| R8 | **A `len(x) == N` reds the golden-count ban.** The bucket is at **25/25** — zero headroom. | Frozenset equality throughout. Escape hatch `# golden-count: cardinality-is-contract` only for a genuinely cardinality-only site, never as a workaround. |
| R9 | **A `tests/architectural/**` glob in `owned_files` unions WP03's lane** (C-009). | File-level entries only. WP03 owns `test_patch_seam_census_control.py` and `_fixtures/patch_seam_control/` in the same directory. |
| R10 | **A bare `uv run` destroys `.venv`.** Three occurrences in this mission. | Only the two sanctioned forms. Re-verify `./.venv/bin/pytest --version` after **any** `uv` invocation, `--dry-run` included. Recover with `uv sync --python 3.12 --extra test --extra lint` and record it. |
| R11 | **A grep-based 4c counts `test_saas_client.py:559`'s docstring occurrence** and reports `1` where the answer is `0`, prompting a prose edit to satisfy a numeric gate. | AST `patch()` call nodes only. NFR-007's AST requirement binds this arm. |
| R12 | **A second implementation of the predicate lands here** instead of consuming WP03's analyzer — the duplicate authority the charter forbids. | T025 imports from `scripts/patch_seam_census.py`. Reviewer checks for a second resolver. |
| R13 | **The gate's docstring keeps the inline-gate claim that it does no call-graph resolution.** It does. | T025 step 5. A misleading self-description is exactly what produced this mission (`test_saas_client.py:55-57`). |

---

## Reviewer Guidance

**Verify the four ratchet edits by opening the file, not by reading the diff summary.** The failure this
WP exists to prevent is a key that *looks* registered. Concretely:

- `grep -c '<new-key>' tests/architectural/test_ratchet_baselines.py` must be **≥ 3** (required set,
  growth list `:274`, shrinkage list `:420`). Two is a defect, not a shortcut.
- Re-derive the counts yourself: 13 YAML keys, 12 required, 11 read by `data["…"]`. If any is off by
  one, find out which edit is missing.
- Ask for the **deliberate-red transcript** from T030 and T031. A ratchet nobody has seen fail is a
  ratchet nobody has tested.

**Verify arm 4c reds on a pre-fix tree.** A `14/9/1` assertion that passes before the retargets landed is
measuring nothing. Ask for that transcript.

**Verify the gate names files rather than counting them,** and that the four node-ids appear verbatim in
its output.

**Do not accept a silent disposition for `test_no_dead_symbols`.** It must be an explicit choice with a
reason, or an explicitly scoped arm plus a filed gap.

**One citation defect found in the incoming artifacts while this prompt was written** — check whether
it propagated into the implementation:

1. `plan.md`'s `pytestmark` table cites `test_no_inert_schema_slots.py:53` as the precedent form. The
   actual `pytestmark = [pytest.mark.architectural]` is at **`:300`**. Line 53 is inside the module
   docstring.

**And one "correction" that was itself wrong, struck here — this is the worked example.** An earlier
draft of this prompt asserted, marked *Verified*, that `plan.md` cited
`test_protection_resolver_call_sites.py:93-110` and that the enclosing function begins at `:88` with
its comprehension at `:101-108`. **All three halves were wrong.** Measured by opening the file:
`def _find_bare_protected_branches_calls` is at **`:90`**, the `ast.walk` comprehension runs
**`:103-109`**, and `plan.md` cites **`:90-109`** in all five places — it was corrected in
`f08748d9a` and the parenthetical had gone stale. The mis-cited-AST-span defect re-entered this
prompt in the *opposite* direction, inside the WP whose own guidance says "open every one".

That is the lesson, not a footnote: **a cited `file:line` is not evidence that the line says what the
citation claims — and neither is a correction to one.** Open every citation this WP adds, including
any that arrive labelled *Verified*.

**Finally: confirm `tests/sync` and `tests/cli` were never run.** This gate is a static AST reader over
that source. If a transcript shows either suite collected, the WP has broken C-001 and the gate is
probably wrong as well.
