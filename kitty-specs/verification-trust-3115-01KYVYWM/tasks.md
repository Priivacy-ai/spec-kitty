# Tasks: Verification Trust — make our own verification honest (#3115, #3113, #3030)

**Mission**: `verification-trust-3115-01KYVYWM` · **Branch**: `feat/verification-trust-3115`
**Topology**: `lanes` · **Base commit for every baseline**: `bb2020fea9`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Rules**: [standing-rules.md](./standing-rules.md)

> ### The thesis
>
> **Our own verification lies to us.** Four defects, one shape: the mechanism that is supposed to tell
> us whether the code is correct returns an answer that is not about the code. An 80-column console
> folds a uuid and a substring assertion reads as *"the report is dropping projects"*. A `@patch` of
> `saas_client.time.sleep` lands on the **stdlib** module object and counts every thread in the
> worker. An egress guard's negative control only tests the shape its author thought of. A
> non-terminating loop hangs a job instead of failing it. **The deliverable is not "make CI green
> once"** — it is a committed reproducer, a render surface pinned at one owner with a guard, a sync
> half diagnosed on its own evidence, an egress guard measured in *shapes*, and a loop that reds by
> name and by count.
>
> ### The critical path
>
> ```
> WP01 ──► WP02 ──┬─► WP03 ──► WP13
>                 └─► WP07 ──► WP13
> ```
>
> **`WP01 → WP02 → (WP03 ∥ WP07) → WP13` — four sequential packages.** WP03 and WP07 are co-equal
> branches of the same length; **WP07 is the heavier one** (it gained the retired WP08's applying
> half, it carries the strictest mutant self-proof in the mission, and it is the package that closes
> `#3030`'s matrix row). Neither can start before WP02. The second chain is
> **`WP11 → WP12 → WP13`**, and WP11→WP12 is the plan's single hardest sequencing constraint: **once a
> global timeout exists, WP11's red-first becomes unobservable**, because a non-terminating loop reds
> on the timeout and `Failed: Timeout (>Ns) from pytest-timeout` is explicitly **not** an acceptable
> red. **Four** lanes can start immediately — WP01, WP09, WP10, WP11. **WP04 was the fifth and is no
> longer**: it now owns `docs/development/3-2-docs-retrieval-index.yaml` and is blocked by WP01,
> whose appended `##` section drifts that index (see "Lanes").
>
> ### What still lands if the sync-half investigation stalls
>
> FR-010 gives the sync half a budget (**6 agent-hours, 3 candidate mechanisms**). **Only WP06 and
> WP14 are affected. Everything else lands.** WP01/WP02/WP03 — the CLI half's cause is *measured* and
> has nothing to do with globals. WP04 is the **map**, not the answer; it survives a failed hunt and
> WP14 outcome B inherits it. WP05 is scoped to WP04's inventory, **not** to WP06's answer. WP07 is
> driven by the width falsifier, so `#3030`'s row resolves regardless. WP09, WP10, WP11, WP12 are
> independent. WP13 reports node-id 13 (`test_429_respects_retry_after`) red or green — its colour is
> FR-010's business, not a reason to withhold the shard result. **WP06 lands either way**: its
> negative result, above the recorded floor, is a deliverable. **WP14 changes shape** (outcome A
> remedy, or outcome B `deferred-with-followup` + successor issue). What is **never** permitted is
> closing the sync half on a green shard while the cause is unidentified.
>
> ### WP08 is retired
>
> **FR-008 / WP08 (`_isolated_home` convergence) was CUT by operator decision after the post-plan
> adversarial squad.** The number is retired and **not reused** — the sequence runs WP01…WP07,
> WP09…WP14 and the gap is a decision, not an accident. Three lenses independently measured the 22
> `_isolated_home` definitions and converged: **a name collision, not a duplicated seam.** No work
> package in this mission adds, moves or removes an `_isolated_home` definition; `grep -c "def
> _isolated_home" tests/` reports **22 before and 22 after**, and a diff that changes that count is a
> scope violation. It is first on the out-of-scope list because it is the single most likely thing a
> well-meaning implementer would do on WP07's file set.

## Traps an implementer must not walk into

1. **`PYTHONPATH` alone does not load a pytest plugin.** Every mutant in this mission is
   `PYTHONPATH=scripts/mutants pytest -p <module> …`, **and the `-p` flag is quoted in the evidence.**
   A `PYTHONPATH`-only mutant binds nothing and its green run reads as a passing gate — the exact rot
   mode this mission exists to stop. (C-003, corrected; probed by the post-plan squad.)
2. **A same-named fixture defined in a plugin loses to a conftest fixture.** Neutralise at **hook
   level** (`pytest_configure` for import-time and session-level seams, `pytest_fixture_setup` to
   intercept a named fixture's setup) — never by re-defining the fixture. The hook form produced a
   named red (`AssertionError: seam was off`); the fixture form did not bind at all.
3. **No verdict may be drawn from a run whose mutant suppressed zero calls.** A zero suppressed
   count is a finding about the **mutant**, not about the code. This is what makes a *null* result
   ("not load-bearing", "the counter did not bind") falsifiable rather than automatic. Every mutant
   asserts its own binding, reports the **per-site split** across every name the symbol is reachable
   by, and **fails loudly if the symbol it patched was never called**.
4. **`COLUMNS` is not a fix, and it is also not dead.** `Console.size`'s `COLUMNS` read sits *below*
   the `if self.is_dumb_terminal:` early return, so on the failing path it is never consulted — the
   victim files already set it and it never fired. But under `CliRunner` in the default environment
   `is_terminal` is False, the early return does not fire, and `COLUMNS` **is** read:
   `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111` passes `COLUMNS=240` and is
   **live today**. Consequences: **the pinned width must be ≥ 240**, and the three existing `COLUMNS`
   sets are **left exactly as they are**. No work package removes or annotates them.
5. **`width=` alone still returns `(80, 25)`.** Rich's explicit-size early return needs
   `self._width is not None and self._height is not None`. A width-only pin is the single most likely
   way this fix ships broken and green.
6. **A blanket `size = (W, H)` walk over `CliConsole._instances` breaks three deliberately-sized
   consoles** — `charter/list_cmd.py:26` (200), `glossary.py:46` (120), `docs.py:43` (120, stated
   load-bearing at `docs.py:40-42`). Pin the **singletons only** (`console.py:126-127`), or exempt any
   instance constructed with an explicit `width=`.
7. **A non-zero inspected count is not a positive control.** `_instances` is a `WeakSet` that also
   holds those three specials, so a count of 3 is satisfiable with both singletons absent. The guard
   asserts by **object identity** that it saw `specify_cli.cli.console.console` and
   `specify_cli.cli.console.err_console`.
8. **Two consoles the seam structurally cannot reach are a *stated* gap, not a hidden one** —
   `src/specify_cli/cli/helpers.py:234` and `src/specify_cli/cli/logging_bootstrap.py:92`, both
   constructed *inside functions*, i.e. after the seam's setup-time walk.
9. **`Queue 0 event(s)` is not a red.** It renders unconditionally from `OfflineQueue().size()`
   (`sync.py:5182-5185`) and appears on the **green** path. Struck from every red-first clause.
10. **The four-test count line belongs to the *status* file.** `test_sync_status_per_project_3030.py`
    collects **4**; `test_sync_doctor_per_project_3030.py` collects **12**. Every count line is quoted
    beside its file's collected count; one that does not reconcile is not evidence, and is re-measured
    rather than argued about.
11. **`tests/sync/conftest.py:242-259` is off limits.** The filename-token consent-grant guard
    (`protected = ("consent", "capture_gate")`) is **armed** — replacing the token guard with a marker
    reds three `test_runtime.py` tests whose natural remedy would undo `#3030`'s T028. Do not read,
    edit, refactor or "improve" it. It needs its own mission.
12. **`fast-tests-cli` treats an empty collection as a green job** (`|| test $? -eq 5`,
    `ci-quality.yml:1545`), and **`fast-tests-sync` is path-filtered** (`ci-quality.yml:1101`) and was
    *skipped* on run `30622853036`. Every claim names the **job**, its **conclusion** and its
    **collected count**. A workflow conclusion is not evidence.
13. **Never pipe a suite whose exit status you intend to trust**, and **an empty output file is no
    measurement**. Write to a file, read the tail of the file. Quote the count line **with its
    assertion text**, never "exit 0".
14. **Never run `tests/sync` and `tests/cli` sessions concurrently on one machine** — 16 recorded
    false reds. Fan out the coding, serialise the sweeps.
15. **`git add <paths>`, never `git add -A`.** 13 files were lost to a shared index on `#3030`.
    **`ruff format` is not run** (`line-length = 164`, the repo is not clean under it); only
    `ruff check` is meaningful.
16. **`-p no:randomly` is a no-op on this tree.** `pytest-randomly` is **not installed** at
    `bb2020fea9`. **C-005 is struck.** Repetition alone therefore cannot carry a determinism claim —
    WP01's node-id-alone re-run is the clause that can go the other way.

## Subtask Index

The **Parallel** column marks subtasks in a lane whose `parallel_group` is 0 with no upstream
dependency — **WP01, WP09, WP10 and WP11** can all start immediately. **WP04's `Y` marks were removed
post-tasks**: it acquired `docs/development/3-2-docs-retrieval-index.yaml` and a `WP01` dependency, so
`lane-d` is `parallel_group` **1**, not 0.

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Commit `scripts/repro_3115_render_width.sh` and its section in `docs/development/testing-parallel.md`: `TERM=dumb FORCE_COLOR=1`, **one file, one process, no xdist**, documented command is **one line**, wall clock under 2 minutes (NFR-005, C-004) | WP01 | Y |
| T002 | **Red first at `bb2020fea9`**, output to a **file** and the tail of the file read (NFR-003): `tests/cli/commands/test_sync_status_per_project_3030.py` quotes `1 failed, 3 passed` beside collected count **4**, and the assertion text must be the per-file assertion text quoted verbatim from source — ``<uuid> is in the journal but `status` did not name it`` (backticks, `test_sync_status_per_project_3030.py:154`) or `<uuid> is in the journal but doctor did not name it` (no delimiters, `test_sync_doctor_per_project_3030.py:174`); they differ, and neither is normalised. Repeated independently for `test_sync_doctor_per_project_3030.py`: `1 failed, 11 passed` beside collected count **12** — **not** `1 failed, 3 passed`. A `TypeError`, fixture error, collection error or **empty output file** satisfies nothing; `Queue 0 event(s)` is excluded | WP01 | Y |
| T003 | **Determinism, reported as two clauses.** (a) *stability, no longer load-bearing*: three consecutive runs, same node-id, **same assertion text byte-for-byte**, same collected count, all three quoted, plus the run's own `plugins:` header line. (b) **the falsifiable clause**: the red reproduces with the failing case selected **alone by node-id**, same assertion text, **collected count 1**. A red that needs its file-siblings is order-dependent and fails C-004. **(b) is what the determinism claim rests on** | WP01 | Y |
| T004 | **Control**: the same command `+ TTY_COMPATIBLE=0` on `bb2020fea9` quotes `4 passed` (status, /4) and `12 passed` (doctor, /12). This is what separates "the width is the cause" from "this file is broken" | WP01 | Y |
| T005 | Extend `_plain_cli_console_seam` (`tests/conftest.py:307-329`) to pin the render surface as well as the colour: **both `width` and `height`** (or `TTY_COMPATIBLE=0`, or `force_terminal=False`), set → `yield` → restore in `finally` (C-002). **Never `COLUMNS`** (C-012). **Width ≥ 240** (F2). **Singletons only** — pin `console` / `err_console` (`console.py:126-127`) or walk `_instances` skipping any instance constructed with an explicit `width=`; state which it chose and why (F1) | WP02 | |
| T006 | `scripts/mutants/disable_render_seam_3115.py` under the **corrected mutant contract**: `PYTHONPATH=scripts/mutants` **and `-p disable_render_seam_3115`, the flag quoted in the evidence**; neutralising at **hook level** (`pytest_fixture_setup` intercepting the seam, or `pytest_configure` unsetting the pin), **never** a same-named fixture; asserting its own binding; reporting the **per-site split**; **failing loudly if the seam was never invoked** | WP02 | |
| T007 | **Both directions on one commit**: WP01's falsifier greens (`4 passed`/4, `12 passed`/12) and the same command with the seam disabled by the plugin reds with WP01's exact assertion text (`1 failed, 3 passed`/4, `1 failed, 11 passed`/12). Seam docstring records the four measured `Console.size` values verbatim, the **shipped** value and why it is ≥ 240, cites `_help_snapshot.py`, names the victim files, and **names the two consoles it does not reach**. Blast radius (golden `--help`, `test_doctor_cli_surface_golden.py`, `test_activation_layout.py`) run before/after with **collected counts** | WP02 | |
| T008 | `tests/architectural/test_cli_console_render_width.py` — **red first** with WP02's seam disabled by the plugin (loaded with `-p`, hook-level, **non-zero** suppressed count): the guard reds naming **the console, its measured `size.width`, and the identifier length** it compared against | WP03 | |
| T009 | FR-003 positive control — **named singletons, not a count**: with the seam in place the guard passes **and asserts by object identity that it saw `specify_cli.cli.console.console` and `specify_cli.cli.console.err_console`**. Alongside it prints the inspected count, the longest asserted identifier length, the **exempted** specials by `module:line` with widths (`list_cmd.py:26` 200, `glossary.py:46` 120, `docs.py:43` 120), and the two function-constructed consoles (`helpers.py:234`, `logging_bootstrap.py:92`) as a **named gap** — **printed on the passing path**. Rot control: a renamed/moved/deleted `_instances` or seam fails loudly. **Detects and fails; does not repair** (H8) | WP03 | |
| T010 | Commit the two captures under `tests/cli/commands/fixtures/render_width_3115/` with **provenance sidecars** (`*.provenance.json`): the exact command, the commit (`bb2020fea9`), the `TERM`/`FORCE_COLOR`/`TTY_COMPATIBLE`/`COLUMNS` values in force, and the **observed `Console.size` tuple**. A meta-assertion reds if a capture exists without its sidecar | WP03 | |
| T011 | `tests/cli/commands/test_render_fold_not_repairable_3115.py`: after **full** whitespace collapse (`re.sub(r"\s+", " ", out)`) of the 80-column capture the uuid is **still** not a substring, and the test **reports the interleaved character count**. Plus the **in-file positive anchor**, three separate assertions each with its own message: (i) both uuid fragments **are** present; (ii) their concatenation **equals** the uuid; (iii) the interleaved count is **> 0**. The identical substring assertion against the pinned-width control capture **finds** the uuid | WP03 | |
| T012 | Register the new arch file in `tests/_arch_shard_map.py` (`test_arch_shard_marker_completeness.py` proves the arch partition is total). State which **live CI gate** selects each of the two new test files and under which **marker**, with that gate's selection **collected count before and after** the files land (R6, NFR-008). Never widen `_gate_coverage_baseline.json` — it is on the nobody-may-edit list | WP03 | |
| T013 | Inventory the **`tests/sync/` cone only** (the CLI cone is excluded — its failure has a measured non-global cause). Each entry carries the **four mandatory values**: (1) module and symbol; (2) `reset seam: <name>` / `no reset seam` / `not reachable`; (3) who calls that seam, or `nobody`; (4) whether `test_429_respects_retry_after`'s outcome **depends** on it — `depends` / `does not depend` / `undetermined`, with the evidence | WP04 | |
| T014 | State the **count of modules scanned** and a **per-bucket count** for each of the four values (e.g. "31 modules scanned; 12 `no reset seam`; 4 `depends`; 9 `undetermined`"). **A grep-shaped deliverable with no dependence column does not close this WP.** This is the map; it needs no culprit and survives a failed hunt — WP14 outcome B inherits it | WP04 | |
| T015 | Docs plumbing for the new page — **four files, not three**: frontmatter (`title`/`description`/`doc_status`/`updated`/`type`/`related`, per `docs/development/testing-parallel.md:1-13`; `doc_status`/`updated` are enforced at `tests/docs/test_docs_structural_lint.py:144`), a `docs/development/toc.yml` nav entry, a **regeneration** of `docs/development/3-2-page-inventory.yaml` via `scripts/docs/inventory_lockfile.py`, **and a regeneration of `docs/development/3-2-docs-retrieval-index.yaml`** via `PYTHONPATH=. uv run python scripts/docs/docs_index.py --write`. Both lockfiles are **generated, never hand-edited** (R7). **The retrieval index is regenerated AFTER WP01's `##` section lands** — it is built from body headings (`scripts/docs/docs_index.py:93` `scan_headings`), so WP01's append drifts it too, and there is one owner and one regeneration. Verified by re-running `scripts/docs/check_docs_freshness.py` read-only and quoting that neither `INVENTORY-INCOMPLETE` nor `DOCS-INDEX-DRIFT` appears, **with the number of pages checked** (NFR-008) | WP04 | |
| T016 | Autouse guard in `tests/sync/conftest.py` snapshotting the globals **and the live-thread set** WP04's inventory marks reachable, failing **the test that leaves them dirty** — naming the symbol (or the thread's `name` and target) and the node-id. Restore, do not clear (C-002). **`tests/sync/conftest.py:242-259` is off limits** | WP05 | |
| T017 | **The designated control-your-diagnostic case runs FIRST**, before the guard's verdict on anything else is trusted: point the guard at `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture — the known `reset_adapters()` leak, whose answer is already known — and **quote the outcome**. A guard that does not flag the known leak is an invalid probe, and **every later verdict from it is void** | WP05 | |
| T018 | **Red first — the order of preference is binding.** (1) Bite a **real inventoried leak** from WP04: an existing `tests/sync/` test the inventory marks as leaving an inventoried entry dirty, **named by node-id**, failed by the guard **on that test**; the probe file is then a harness, not a leaker. (2) **Only if** WP04's inventory surfaces no such test may a synthetic probe be used, and then the limitation is written verbatim in WP10's exact voice — *"the only demonstrated bite is the synthetic case"* — in the probe's docstring **and** the transition note. Either way the probe mutates **exactly one** inventoried entry and the **probe** carries the failure | WP05 | |
| T019 | Positive control: a clean selection is **not** flagged, and the guard reports how many tests it inspected **and which inventory entries it did not watch, with the reason** (H8, NFR-008) — including a run where **nothing leaks and nothing is flagged** (R10). Rot control: a renamed/moved/deleted watched symbol fails loudly. NFR-006: added wall clock over `fast-tests-sync` before/after at the same worker count and coverage state; over 5% changes the guard's **implementation**, never its reach. NFR-004: probe runs sequential or partitioned by `SPEC_KITTY_HOME` and port range | WP05 | |
| T020 | **Record the FLOOR before any of the 6 hours are counted** — one of: **(F-a)** the symptom **observed red locally**, failure text quoted verbatim (`AssertionError: Expected 'sleep' to be called once. Called <n> times.`), the exact selection, and that selection's **collected count**; or **(F-b)** an explicit written statement that it **could not be reproduced locally**, enumerating every selection tried with each one's **collected count** and outcome — file-level, cone-level, with and without `-n auto --dist loadfile`, with and without the daemon-spawning siblings. **Neither branch closes without one of these two on the record** | WP06 | |
| T021 | Attribution naming **(i)** a leaked live thread and its start site **or (ii)** a specific other mechanism, supported by a reproduction that **shows the call count moving** — count before and count after, both quoted with their assertion texts (NFR-007). **Each excluded mechanism carries a named exclusion measurement** — the command run, the collected count, and the observed `sleep` call count — not an argument from structure. Candidate source: `src/specify_cli/sync/daemon.py` (threads `:587`, `:767`, `:828`; sleep loops `:584`, `:1382`) | WP06 | |
| T022 | Report **hours spent and mechanisms tried** (budget: at most **6 agent-hours**, at most **3 candidate mechanisms**, measured after WP04's inventory and after the floor). Record the finding **at the site** in the victim file's docstring, in the voice `_advancing_clock`'s docstring already uses (`tests/sync/tracker/test_saas_client.py:32-50`). **Permitted**: "the two symptoms have two different causes." **Forbidden**: adopting the issue's *"common shape"* sentence as the finding; funding the module-global-backoff leg (structurally impossible) or `_poll_operation` threading (nothing in the tree threads it) | WP06 | |
| T023 | `scripts/mutants/neutralise_reset_token_manager_3115.py` under the corrected contract in full: `PYTHONPATH=scripts/mutants` **and `-p neutralise_reset_token_manager_3115`, the flag quoted**; neutralising at **hook level** in `pytest_configure`, **never** a same-named fixture; asserting its own binding; failing loudly if the patched symbol was never called | WP07 | |
| T024 | With the reset neutralised by the plugin, run **(a)** WP01's falsifier and **(b)** the same file at the pinned width. **All four count lines, each beside its file's collected count, and all four assertion texts are quoted** | WP07 | |
| T025 | **Per-site split, mandatory.** All five `578a659162` files import `reset_token_manager` **function-locally inside the fixture body** from `specify_cli.auth.manager` (`…doctor_per_project…:62`, `…status…:73`, `…migrate…:57`, `…purge…:83`, `…health…:70`), so patching the defining module binds at all five. **Two other sites bind eagerly by value via the package name** — `tests/auth/integration/conftest.py:22` and `tests/auth/test_websocket_provisioning.py:28` — and are **deliberately unpatched**; the report must **name them as deliberately-unpatched, never report them as zero**. An aggregate suppressed count is rejected. **The null verdict needs a non-zero suppressed count across the five patched sites** — a null drawn from a zero-suppression run is a finding about the mutant and is **void** | WP07 | |
| T026 | **Apply the verdict itself** (WP08 was the applying half; it is retired): write the corrected docstring at **each of the five sites** — defence-in-depth, not the fix — quoting the measurement that produced the verdict. Deletion only if shown inert **and** WP04's inventory shows nothing reads the singleton on that path. **Collected counts before and after for each of the five files, quoted**; the change is a docstring edit, so any moved count is a defect in the edit and is reconciled, not absorbed. **This closes `#3030`'s matrix row** | WP07 | |
| T027 | Add a **filesystem-independent** pin: force the resolution seam to yield "unresolvable" and assert `is_sync_enabled_for_checkout()` is `False`, so a hostile machine cannot silently remove coverage of the invariant. It passes in **both** environments | WP09 | Y |
| T028 | `tests/sync/test_sync_consent_default_deny.py:127-152` keeps its cwd-based form and gains an **asserted precondition** reporting the first ancestor carrying a `.git`/`.kittify` marker **and the value of `SPECIFY_REPO_ROOT`** (today it `delenv`s only `SPEC_KITTY_HOME` and never asserts `SPECIFY_REPO_ROOT`, which is tier-1 authoritative in `core/paths.py`). **Red first**: with a marker planted above the tmp root the current test fails on the **bare consent assertion**; after the change it fails **naming the offending ancestor**. **C-001 binds: no production routing change** | WP09 | Y |
| T029 | FR-013: grow the module docstring's completeness-limits list from **7** to exactly **8** — the all-positional / no-`headers=` transport call, in the same voice as its neighbours. **Both counts stated.** A meta-test asserts the entry exists so a future docstring trim reds. The cross-reference to `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md` is **one-directional**; that closed mission's dossier is **not edited** (C-010) | WP10 | Y |
| T030 | FR-014 **red first**: add **two** positional cases to `test_scanner_detects_each_sink_shape` (`:933`) — **(A)** `def go(poster, url, body, hdrs): return poster(url, body, hdrs)` and **(B)** `def relay(post, u, payload, meta): return post(u, payload, meta)`. On `bb2020fea9` **both** fail with `scanner went blind to transport-call` (`:938`) and **each failure text is quoted**. **Case (B) is the adoption gate** — a matcher that passes (A) and fails (B) is blind in exactly the way `#3113` is about, because `_attr_tail` (`:266-272`) returns `node.id` verbatim for a bare `Name` and `url` is already in `_URL_ARG_NAMES` (`:197`) | WP10 | Y |
| T031 | **ORDER IS BINDING**: take the `src/`-wide false-positive count **FIRST, before any matcher edit**, against the *candidate* structural predicate (callee is a bare `ast.Name` whose `id` resolves to a **parameter of the enclosing `FunctionDef`**). **The command that produced the count and the count itself are both quoted.** Sites the tightening **newly adds** are reported **separately** from pre-existing ones. If the WP's own count differs from the recorded **5 FPs / 211 candidate sites / 13 files** (four named enclosing functions: `resolve_workspace_for_wp`, `locate_work_package`, `behind_commits_touch_only_planning_artifacts`, `get_wp_lane`), the discrepancy is **named and reconciled**, not silently preferred | WP10 | Y |
| T032 | **The scanner restructure is funded only if the count returns zero.** It is a restructure, not a branch edit: `_classify(node: ast.Call)` (`:309`) is reached from a flat `ast.walk(tree)` (`:347`) that discards the enclosing `FunctionDef`, so adoption means threading the parameter set through the walk. **Expected outcome: no tightening, two `xfail(..., strict=True)` (C-011), row `#3113` closed.** A zero delta is written down verbatim as *"the only demonstrated bite is the synthetic case"*. Any moved count in `tests/architectural/_baselines.yaml` (`egress_allowlist_files: 28` at `:368`, `known_ungated_files: 0` at `:375`) is reconciled in the same change. C-006: a tightening needing an author-chosen identifier — **including `_URL_ARG_NAMES`** — is rejected **regardless of its false-positive count** | WP10 | Y |
| T033 | Both loop-driving tests in `tests/delivery/test_dispatch_window_consent_3030.py` (`:157`, `:218`, driving `_RecordingIngress` `:68`) gain a hard cap on the recorded batch count that reds **naming the count**, mirroring `DISPATCH_CALL_CAP = 25` (`tests/delivery/test_nfr002_loop_permanence_3030.py:69`, asserted `:154-157`) | WP11 | Y |
| T034 | **Red first is a consequence, not a threshold flip**: `scripts/mutants/nonterminating_dispatch_3115.py` under the corrected contract — `PYTHONPATH=scripts/mutants` **and `-p nonterminating_dispatch_3115`, the flag quoted**; hook-level in `pytest_configure`, never a same-named fixture; asserting its own binding; reporting the **per-site split**; **failing loudly if the patched symbol was never called** — makes `_run_dispatch_batches` fail to make progress, and each test reds **on the counter, naming the count**, and specifically **not** on `Failed: Timeout (>Ns) from pytest-timeout`. A red whose text is the timeout means the counter did not bind | WP11 | Y |
| T035 | **Both measurements reported**: the threshold-flip one (proves the assertion fires) **and** the mutant one (proves it fires *on the defect*). **The mutant one is the acceptance.** Record the rule in the file: *any assertion about termination needs a counter; the timeout is a backstop for the harness, not a substitute for the pin.* **Measured on a tree with NO global timeout** — this is the reason for the WP11 → WP12 ordering constraint | WP11 | Y |
| T036 | Choose derivation **(a)** `addopts` in `pytest.ini` or **(b)** the flag scoped to the fast job command lines in `.github/workflows/ci-quality.yml`, and **state which**. (a) is permissible only if `--durations` is actually collected over **every** selection that inherits the ini (`testpaths = tests`); otherwise (b), whose blast radius is the enumerated job list. State the **chosen value, chosen method, chosen derivation, coverage state and the measured maximum unmarked-test duration**, with a floor of **4×** that maximum. `--cov` is on for both fast shards (`ci-quality.yml:1132`, `:1543`) and **inflates** `--durations`; if the value was derived with coverage on, say so and justify against the coverage-on numbers | WP12 | |
| T037 | **Red first** via `scripts/mutants/hang_a_fast_test_3115.py` under the corrected contract — loaded with `-p hang_a_fast_test_3115` (flag quoted), collecting/injecting at hook level, asserting its own binding, and **failing loudly if the injected test was never collected** ("the selection ended fine" from a run that never collected the hanging test is not a measurement). Green after: the same selection **ends and prints a summary line naming that test**; a run ending with **empty output does not satisfy this**. Carry forward the probe that `pytest-timeout`'s `signal` method works under `xdist` on Linux (`--timeout=3 --timeout-method=signal -n 2` → `Failed: Timeout (>3.0s) from pytest-timeout`) — and **quote the summary line, never "the output was clean"**, because the same run also emitted an `execnet gateway_base._thread_receiver` traceback. `ci-windows.yml` has no `SIGALRM`: **state what method it gets and what its failure mode is** | WP12 | |
| T038 | State the blast radius because `testpaths = tests`: **46** `slow` tests (ini definition: ">30 seconds") against **~15** `@pytest.mark.timeout` sites, and the opt-in selections that run them are ones FR-017's regression clause structurally **cannot** observe. Existing explicit marks **override** the ini default. **No new pytest marker** — `timeout` is already registered in `pytest.ini`, WP12 is the sole owner of that file, and no other WP may add a marker there | WP12 | |
| T039 | **Regression clause, enumerated not aggregate**: the first full CI run after the change lists **every job that inherited the new default** with its conclusion and **collected count**, and separately **every selection that did not run at all** with the reason. Zero tests newly red attributable to the timeout; any that are, listed with their durations and either marked or the value raised. ***"Nothing newly red" over a set that did not run is not a result.*** WP12 is the **last code-changing WP merged**; every lane cut before it re-merges the mission branch before its next measurement (NFR-009) | WP12 | |
| T040 | Quote the shard's distribution in full (NFR-001): worker count **from the run's own xdist `gw0..gwN` header**, never inferred from the runner label; `--dist loadfile`; `-m "fast and not windows_ci"`; the exact file and `--ignore` selection copied from `ci-quality.yml:1124-1133` / `:1540-1546`; whether `--cov` was on; and the **collected test count**. `tests/sync` and `tests/cli` sessions are **not** run in parallel on one machine (NFR-004) | WP13 | |
| T041 | **Quote each of the 13 enumerated node-ids' outcome from the run's own report**, and discharge the **three reconciliation obligations the plan records as unresolved**: (i) `test_sync_doctor_consent_health_3030.py` — the issue says 4 param cases; at `bb2020fea9` the only parametrised test collects **3**; name which, and either identify the fourth node-id or record its absence as a **named exclusion with the reason** ("3 of 4 passed" without saying which is missing does not close this); (ii) `test_sync_purge_3030.py::TestPurgeAll` — the issue says 2, the class collects **7**; name **which two**, or run all seven and say so, quoting each outcome; (iii) `test_consent_write_refusal_3030.py` — confirm the 3-wide `[opt-in]`/`[opt-out]`/`[server]` identification against the collected set (**file total 29**, including two 8-wide parametrisations), or name the three it ran and why. **Corrected post-tasks**: this row and `tasks/WP13-shard-proof.md` both said **69**, which was an aggregate across more than one file; re-measured with `pytest --collect-only -q` on that single file, it is **`29 tests collected`**. **Do not invent node-ids to make a flat list of 13** | WP13 | |
| T042 | **Any enumerated node-id absent from the collected set is named and explained** — marker-deselected, swallowed by one of the four `--ignore`s, or renamed since the issue was written — and an absence is closable **only** by naming it as a deliberate exclusion with its reason. **All 13 pass, run twice** (SC-009), each run's collected count quoted. Any CI claim names the **job** (`fast-tests-cli`, `fast-tests-sync`), its **conclusion** (`success`/`skipped`/`failure`) and its **collected count**; a claim that `fast-tests-sync` passed is rejected if that job's conclusion was `skipped`. **A shard-level `N passed` with no per-node-id reconciliation does not satisfy this**, because `\|\| test $? -eq 5` makes an empty collection a green job | WP13 | |
| T043 | **Expected gate no-op, stated in advance**: WP13 owns **one non-test file** (`scripts/verify_shard_3115.sh`), so `_mt_resolve_pre_review_workspace` **does** resolve (`tasks_move_task.py:937-962`) and the `no_coverage` arrives instead by the **changed-file** route (`:965-980`) mapping a shell script to zero test targets — the pre-review gate still prints `no_coverage — skipping the gate cheaply`. **That line is expected and is not evidence of anything** — the `for_review` transition note says so **in those words**, states **which of the two routes produced it**, and **names the manual evidence standing in for the gate**: the two shard runs with their job names, conclusions and collected counts. Re-measure at the merge commit if **WP12, WP06 or WP14** lands after the first pass (WP06/WP14 own the file carrying node-id 13); WP13 is deliberately **not** blocked on WP06/WP14, but a pass taken before they land **states the commit it was taken at** and node-id 13 is re-quoted afterwards | WP13 | |
| T044 | **Outcome A — cause identified**: the remedy lands in the **declared** file `tests/sync/tracker/test_saas_client.py`, with a **both-directions** reproduction. If the attribution names a thread-owning fixture in **another** file, that file is **not** taken over — the remedy is expressed at the declared file and the other file's change is raised as a successor, because **ownership may not be invented after planning**. On outcome A the pre-review gate should run normally; if it prints `no_coverage` **that is a defect to investigate, not to absorb** | WP14 | |
| T045 | **Outcome B — budget exhausted**: the declared file is **left untouched** (an owned file with no diff is legal and is what keeps the lane entry valid). Deliverable: the successor issue filed against `Priivacy-ai/spec-kitty`, inheriting WP04's inventory **and the harness's negative result** — which mechanisms were excluded and by what measurement — plus the `deferred-with-followup` verdict and the successor number on `#3115`'s matrix row. Outcome B produces **no diff**, so `tasks_move_task.py:965-980` returns an empty tuple and the gate folds to `no_coverage` anyway: the transition note **states that the printed line is expected** and names the manual evidence — the successor issue number, WP06's recorded floor, and the enumerated exclusion measurements. **"Recorded as unproven" plus a green shard is not a permitted closure** — that is the exact path that produced `578a659162` | WP14 | |

## Test-file ownership — the friction that lost `#3030` a red-first

The lane guard's record is unambiguous: **no WP in the predecessor mission declared any test file**, so
every red-first commit tripped `ACTIVE_WP_SCOPE_VIOLATION`. Every test module this mission writes or
edits is declared in its WP's `owned_files` — `tests/conftest.py` (WP02), the two new test files and
the capture glob (WP03), `tests/sync/conftest.py` and the probe (WP05),
`tests/sync/tracker/test_saas_client.py` (WP06, then WP14), the five `578a659162` files (WP07),
`tests/sync/test_sync_consent_default_deny.py` (WP09),
`tests/architectural/test_egress_consent_boundary.py` (WP10),
`tests/delivery/test_dispatch_window_consent_3030.py` (WP11). The mutants under `scripts/mutants/`
are **not** test files — they live outside `testpaths` deliberately, because
`tests/conftest.py:245`'s `_fail_on_wall_clock_assertions` walks the whole `tests/` tree at collection
and raises `pytest.UsageError`, so a sleep-shaped mutant under `tests/` risks failing collection of
the entire suite.

## `create_intent` — eleven new literal paths, verified against the tree

`validate_glob_matches` (`src/specify_cli/ownership/validation.py:418-448`) treats a literal
`owned_files` path with **zero repo matches** as a **hard error**, raised at
`mission_finalize.py:998-1006` with `typer.Exit(1)`. Globs degrade to a soft warning; literal paths do
not. Every declared path was checked against the tree; these eleven do not exist yet and each carries a
`create_intent` entry in its WP's frontmatter:

| Path | WP |
|---|---|
| `scripts/repro_3115_render_width.sh` | WP01 |
| `scripts/mutants/disable_render_seam_3115.py` | WP02 |
| `tests/architectural/test_cli_console_render_width.py` | WP03 |
| `tests/cli/commands/test_render_fold_not_repairable_3115.py` | WP03 |
| `docs/development/process-global-inventory-3115.md` | WP04 |
| `tests/sync/test_leak_guard_probe_3115.py` | WP05 |
| `scripts/mutants/attribute_sleep_count_3115.py` | WP06 |
| `scripts/mutants/neutralise_reset_token_manager_3115.py` | WP07 |
| `scripts/mutants/nonterminating_dispatch_3115.py` | WP11 |
| `scripts/mutants/hang_a_fast_test_3115.py` | WP12 |
| `scripts/verify_shard_3115.sh` | WP13 |

`tests/cli/commands/fixtures/render_width_3115/**` is declared as a **glob** in WP03's `owned_files`
(the directory does not exist; a literal directory path with zero matches is the same hard error),
with the four concrete capture/provenance files listed in `create_intent` so the intent is a
commitment rather than a directory-shaped promise.

## Lanes — derived from ownership, not authored beside it

`compute_lanes` derives lanes **solely from `owned_files` glob overlap**
(`src/specify_cli/lanes/compute.py:1-11`); a hand-authored lane table is an **intent statement, not an
input**. Ordering is carried by `blocked_by`, which becomes `depends_on_lanes`. No two WPs share an
`owned_files` entry **except WP06/WP14** (deliberately — WP14 declares
`tests/sync/tracker/test_saas_client.py` at planning time, which is the only thing that puts the two
in one lane and makes outcome A a within-lane transfer). **Twelve lanes, thirteen WPs.**

| Lane | WPs | Write scope | depends_on_lanes | parallel_group |
|---|---|---|---|---|
| `lane-a` | WP01 | `scripts/repro_3115_render_width.sh`, `docs/development/testing-parallel.md` | — | 0 |
| `lane-b` | WP02 | `tests/conftest.py`, `scripts/mutants/disable_render_seam_3115.py` | `lane-a` | 1 |
| `lane-c` | WP03 | `tests/architectural/…`, `tests/cli/commands/…`, the capture glob, `tests/_arch_shard_map.py` | `lane-a`, `lane-b` | 2 |
| `lane-d` | WP04 | `docs/development/process-global-inventory-3115.md`, `toc.yml`, `3-2-page-inventory.yaml`, **`3-2-docs-retrieval-index.yaml`** | **`lane-a`** | **1** |
| `lane-e` | WP05 | `tests/sync/conftest.py`, `tests/sync/test_leak_guard_probe_3115.py` | `lane-d` | **2** |
| `lane-f` | WP06 → WP14 | `tests/sync/tracker/test_saas_client.py`, `scripts/mutants/attribute_sleep_count_3115.py` | `lane-d` | **2** |
| `lane-g` | WP07 | the five `578a659162` files, `scripts/mutants/neutralise_reset_token_manager_3115.py` | `lane-a`, `lane-b` | 2 |
| `lane-h` | WP09 | `tests/sync/test_sync_consent_default_deny.py` | — | 0 |
| `lane-i` | WP10 | `tests/architectural/test_egress_consent_boundary.py`, `tests/architectural/_baselines.yaml` | — | 0 |
| `lane-j` | WP11 | `tests/delivery/test_dispatch_window_consent_3030.py`, `scripts/mutants/nonterminating_dispatch_3115.py` | — | 0 |
| `lane-k` | WP12 | `pytest.ini`, `.github/workflows/ci-quality.yml`, `scripts/mutants/hang_a_fast_test_3115.py` | `lane-j` | 1 |
| `lane-l` | WP13 | **`scripts/verify_shard_3115.sh`** | `lane-c`, `lane-e`, `lane-g`, `lane-k` | 3 |

> ### Both ownership defects in this table are now resolved — and `lanes.json` on disk is stale
>
> **`lane-l` / WP13 — resolved.** The plan gave WP13 `owned_files: none` and still assigned it a lane.
> Measured against the code, that is a **hard error, not the singleton lane the post-plan squad's M4
> finding assumed**: `build_wp_manifests` (`src/specify_cli/ownership/validation.py:354-358`) builds a
> manifest only `if fm.execution_mode and fm.owned_files`, so a WP owning nothing gets **no manifest**,
> and `compute_lanes` (`src/specify_cli/lanes/compute.py:331-336`) then raises
> `LaneComputationError: Executable WP 'WP13' has no ownership manifest.` — uncaught on both the
> dry-run path (`mission_finalize.py:1062-1073`) and the write path (`:1236`).
> **WP13 now owns `scripts/verify_shard_3115.sh`.** The post-tasks pass first gave it
> `docs/development/shard-proof-3115.md`; **that was wrong and is withdrawn** — a new page under
> `docs/` obliges frontmatter, a `toc.yml` entry, and regeneration of **two** generated artefacts, all
> of which are `lane-d`'s write scope, in `parallel_group` 1, against a page that would arrive in
> group 3. Nothing under `scripts/` is walked by any docs ruler (each of them roots at `docs/`), which
> is why WP01's `scripts/repro_3115_render_width.sh` carries no docs obligation either.
>
> **`lane-d` / WP04 — the third generated artefact had no owner.**
> `docs/development/3-2-docs-retrieval-index.yaml` is regenerated from frontmatter **and body
> headings** (`scripts/docs/docs_index.py:93` `scan_headings`), and its drift is an **error**
> (`DOCS-INDEX-DRIFT`, `check_docs_freshness.py:767-812`), blocking on every PR via
> `.github/workflows/docs-freshness.yml`. **Two** changes in this mission drift it — WP01's appended
> `##` section and WP04's new page — and **nothing in the dossier named the file at all.** It is now
> WP04's, alongside the two artefacts WP04 already owned, and **WP04 is blocked by WP01** so the
> regeneration happens **once, after both changes**. That edge is what moves `lane-d` to
> `parallel_group` 1, and `lane-e` / `lane-f` with it to 2.
>
> **`lanes.json` was regenerated on 2026-07-31 and now matches this table exactly — zero divergence.**
> It was stale for a window, and that window is worth recording because nothing in the workflow closes
> it for you: `lanes.json` is computed by `/spec-kitty.tasks` from `owned_files` **at the moment it is
> run**, and the post-tasks remediation changed WP04's ownership and WP13's artefact *afterwards*.
> Nothing recomputes it. The stale file still pointed `lane-l` at `docs/development/shard-proof-3115.md`
> — a path no WP owned and which does not exist — and left `lane-d` at `parallel_group` 0 with no
> `lane-a` edge, so WP04's worktree would not have contained WP01's appended section and its
> regeneration would have left blocking `DOCS-INDEX-DRIFT` with no owner. Caught by the `/analyze`
> gate as its single HIGH, not by any lane check. **The rule that survives: any edit to a WP's
> `owned_files` or `dependencies` after finalisation invalidates `lanes.json`, and `spec-kitty tasks`
> must be re-run before the next dispatch.** Verified after regeneration (`a9899eb85a`, which touches
> `lanes.json` and nothing else): all 13 WP frontmatters intact, and the graph hand-checked acyclic.
> **If the computed grouping ever differs from this table, the computed grouping wins and the
> divergence is reported** (rule 5 below, risk R16).

**Acyclicity checked by hand, because the tooling will not check it for you.** `compute.py:618-630`
calls cycle detection "best-effort" and defers to caller validation that **does not exist** anywhere in
`src/specify_cli/lanes/`; a cyclic lane graph deadlocks at dispatch and allocates from the wrong merge
base, silently. Edges: `b←a`, `c←a,b`, **`d←a`**, `e←d`, `f←d`, `g←a,b`, `k←j`, `l←c,e,g,k`, plus one
intra-lane edge (WP14 ← WP06 inside `lane-f`, which `compute_lanes` sees as a depth-0 anchor).
**Re-checked after the `d←a` edge was added.** Sources: `a`, `h`, `i`, `j`. Depth 1: `b`, `d`, `k`.
Depth 2: `c`, `g`, `e`, `f`. Depth 3: `l`. Every edge runs strictly from a lower depth to a higher one,
so **no edge points backwards and there is no cycle.** If `/spec-kitty.tasks` produces a different
grouping, **the computed grouping wins and the divergence is reported**, because it means an
`owned_files` entry overlaps in a way the plan did not intend.

## Ordering rules that bind the orchestrator, not just the lanes

1. **WP11 before WP12** — hard, non-negotiable, carried by `blocked_by: [WP11]`. Their `owned_files`
   are disjoint so `compute_lanes` will **not** merge them; the plan's earlier "structural, not
   conventional" claim rested on a lane co-location the tooling would never have produced.
2. **WP12 is the last code-changing WP merged.** Any lane cut before it merges the mission branch into
   its worktree **before its next measurement** and states the commit it measured at (NFR-009).
3. **Lane `for_review` transitions are taken ONE AT A TIME** (NFR-010). The pre-review gate's
   serialisation lock degrades to **no lock after 5 seconds**
   (`src/specify_cli/review/pre_review_gate.py:256`) and gate runs here take ~2 minutes, so a second
   lane transitioning concurrently runs its suite anyway — recreating the 16 recorded false reds. Any
   gate red is **re-measured serially before it is believed**.
4. **Every lane merges the mission branch into its worktree before its first measurement** and states
   its merge-base (NFR-009). A baseline whose commit is unstated is **void** and is re-taken, not
   argued about. This mission's own orchestrator already reproduced this friction once by creating the
   mission at `9189cf2b36`, 7 commits behind.
5. **Pre-authorised**: the pre-review gate's 300s cap is below the runtime of the suites this mission
   touches, so `--force` on the `for_review` transition is permitted **with the reasoning recorded in
   the transition note** and the equivalent evidence measured manually and quoted (count lines, not
   exit codes). The reasoning must state the check was *inapplicable or unable to complete*, never
   merely inconvenient (R2).
6. **Expect `--acknowledge-not-bulk-edit`** on lane allocation: the spec still uses "converge" and
   "hoist" in the FR-008 tombstone and the scope-cut note. The many-file edit the heuristic reacts to
   (WP08, 22 files) **no longer exists**; the largest remaining multi-file change is WP07's five-file
   docstring edit (R14).
7. **WPs park at `approved`.** `--to done` requires every issue row to hold a terminal verdict, so the
   matrix resolves at mission close. Expected, not a defect to fight (R13).

## Serial dispatch sequence — named per group, not left to a rule

**A `parallel_group` is a permission, not an instruction.** `lanes.json` has **no field** for dispatch
order within a group, and NFR-004 — *never run `tests/sync` and `tests/cli` sessions concurrently on
one machine* — binds **the orchestrator, not the lanes**. A lane cannot honour it: it does not know
what its siblings are doing. So the order is named here, per group, as a sequence rather than as a
principle. **The 16 recorded false reds are what a group dispatched "in parallel because the field said
0" produces.**

**The sequences bind the *sweeps* — every pytest session, red-first, positive control, blast-radius
run and `for_review` gate. They do not bind the coding.** Fan out the writing; serialise the running.

| Group | Named dispatch sequence | Why this order |
|---|---|---|
| **0** | `lane-a` → `lane-h` → `lane-i` → `lane-j` | `lane-a` (WP01) measures over `tests/cli`; `lane-h` (WP09) measures over `tests/sync`. **Those two must never overlap**, and `lane-a` goes first because it is the critical path's head and everything in the CLI half is unfalsifiable without it. `lane-i` (`tests/architectural`) and `lane-j` (`tests/delivery`) spawn no daemons, but they follow rather than straddle, so a red anywhere in the group has an unambiguous window |
| **1** | `lane-b` → `lane-k`, with `lane-d` free to overlap either | `lane-b` (WP02) is the root-conftest seam and its blast-radius runs are `tests/cli` selections; `lane-k` (WP12) is repo-wide (`testpaths = tests`) and will touch both cones, so it may not straddle `lane-b`. **`lane-d` (WP04) is the exception and is stated as one**: its work is a static read of `tests/sync/` modules plus the docs rulers, and it starts **no** pytest session over either cone. **Post-remediation this group no longer contains the collision the squad flagged** — `lane-e` and `lane-f` moved to group 2 when `lane-d` acquired its `lane-a` dependency |
| **2** | `lane-c` → `lane-g` → `lane-e` → `lane-f` | **This is now the collision group.** `lane-c` (WP03) and `lane-g` (WP07) are both `tests/cli/commands/`; `lane-e` (WP05) and `lane-f` (WP06 → WP14) are both `tests/sync/`. The order runs **both CLI lanes to completion before either sync lane starts**, so no `tests/cli` session is ever live while a `tests/sync` session is. `lane-c` precedes `lane-g` because WP03's width guard is the only thing that would catch a change to the victim files' render surface; `lane-e` precedes `lane-f` because WP05's guard is the instrument WP06's attribution reads |
| **3** | `lane-l` alone | `scripts/verify_shard_3115.sh` runs the sync shard and the cli shard **one after the other, inside the script**. Nothing else is dispatched while it runs — a shard proof taken beside a live sibling session is measuring the sibling |

**Every `for_review` transition note names the wall-clock window its measurements ran in** — start and
end, with the timezone, for each quoted run. Not "it ran serially": the **window**. A false red from a
sibling session is only diagnosable after the fact if the windows are on the record and can be laid
against each other; without them, "we serialised it" is exactly the kind of unverifiable
self-assertion this mission exists to stop, and the 16 false reds are what it costs when it turns out
not to have been true.

**Any gate red is re-measured serially, in a window with nothing else dispatched, before it is
believed** (rule 3 above). A red whose window overlaps another lane's is **no measurement** — neither a
pass nor a fail — and is re-run narrowed rather than explained.

## The three WPs that will legitimately close on `no_coverage`

**WP07, WP13 and WP14-outcome-B** will print `Pre-review regression gate: no_coverage — skipping the
gate cheaply`, by design, because their changed-file sets map to zero test targets. Pre-allocation
closes only **one** of the two paths to that outcome (`tasks_move_task.py:937-962` — workspace
resolution — versus `:965-980` — changed files). **Each states in its transition note that the printed
line is expected and names the manual evidence standing in for it.** A transition note that lets the
`no_coverage` line stand unremarked is the *"mechanism reporting success for having done nothing"*
shape, one layer up — the exact thing this mission exists to stop.

## Files nobody owns, and nobody may edit

`tests/architectural/_gate_coverage_baseline.json` (R6 — the correct response to a newly-ungated test
file is to **gate it**, never to widen the baseline); `kitty-specs/journal-project-consent-3030-01KYKWQS/**`
(C-010, a closed mission's dossier); `src/**` (no production change is required by any FR);
`src/specify_cli/cli/commands/sync.py` (C-009 protects `overflow="fold"`); **the 22 `_isolated_home`
definition sites** (FR-008 is cut; the count stays at 22); and
**`tests/specify_cli/cli/commands/charter/test_activation_layout.py`** — its `COLUMNS=240` at `:111`
is **live** and it is WP02's blast-radius *subject*, not its write scope.

## Work packages

### WP01 — The reproducer

Subtasks: T001–T004. Dependencies: none. Lane `lane-a`. `execution_mode: code_change`. Requirements:
FR-001. Two environment variables, one file, one process. **Cheap enough that nothing downstream is
hostage to it.** Forbidden: editing any test file; `COLUMNS`; xdist. (`-p no:randomly` is pointless
rather than forbidden — C-005 is struck; if any run uses it, say so and state why, but it changes
nothing on this tree.)

### WP02 — The render seam

Subtasks: T005–T007. Dependencies: WP01. Lane `lane-b`. `execution_mode: code_change`. Requirements:
FR-002. Extends the **existing** `_plain_cli_console_seam` rather than adding a second autouse fixture
— one owner, one `finally`, one docstring that already explains half the problem. `tests/conftest.py`
now has **exactly one owner**; the sequential-handoff risk on the root conftest disappeared with WP08.
**The `COLUMNS` note the earlier draft passed forward to WP08 is withdrawn** — F2 measured those sets
**live** on the non-dumb path. WP02 records the *correct* finding (inert on the failing path, consulted
on the passing one) in the seam's docstring, and **no work package removes or annotates them**.

### WP03 — Width guard + the forbidden remedy proved forbidden

Subtasks: T008–T012. Dependencies: WP01, WP02. Lane `lane-c`. `execution_mode: code_change`.
Requirements: FR-003, FR-004. Owns `tests/_arch_shard_map.py` outright because it is the only WP
adding a file under `tests/architectural/`, and
`tests/architectural/test_arch_shard_marker_completeness.py` proves the arch shard partition is
**total** — a new file with no assignment row reds that guard.

### WP04 — The `tests/sync/` process-global inventory

Subtasks: T013–T015. Dependencies: **WP01**. Lane `lane-d`, `parallel_group` **1**.
`execution_mode: code_change`. Requirements: FR-006. **This is the map, not the answer.** It needs no
culprit, survives a failed hunt, and both WP05 and WP14-outcome-B inherit it.

**Owns all four docs files** because it is the only WP adding a page: the new page,
`docs/development/toc.yml`, `docs/development/3-2-page-inventory.yaml`, and — **added post-tasks** —
`docs/development/3-2-docs-retrieval-index.yaml`. That third generated artefact had **no owner in the
dossier at all**, and its drift is a blocking **error** (`DOCS-INDEX-DRIFT`,
`scripts/docs/check_docs_freshness.py:767-812`, run on every PR by
`.github/workflows/docs-freshness.yml`).

**Why WP04 is blocked by WP01**: the retrieval index is regenerated from **body headings**
(`scripts/docs/docs_index.py:93` `scan_headings`, level-2/3 ATX), so **WP01's appended `##` section
drifts it** just as WP04's new page does. WP01 appends to an existing page and **owns none of the four
files**; the dependency edge exists so that **one** regeneration, taken after both changes, closes both
drifts. Without it WP04 would regenerate in `parallel_group` 0 and WP01's heading would land
afterwards, leaving drift on the branch with no owner left to fix it.

### WP05 — The sync leak guard

Subtasks: T016–T019. Dependencies: WP04. Lane `lane-e`. `execution_mode: code_change`. Requirements:
FR-007. Scoped to WP04's inventory, **not** to WP06's answer — it ships whether or not the attribution
converges. **Explicit prohibition, in these words**: *do not read, edit, refactor or "improve" the
filename-token consent-grant fixture at `tests/sync/conftest.py:242-259`
(`protected = ("consent", "capture_gate")`). It is out of scope, it is **armed** — replacing the token
guard with a marker reds three `test_runtime.py` tests whose natural remedy would undo `#3030`'s T028 —
and it needs its own mission.*

### WP06 — The `sleep`-count attribution

Subtasks: T020–T022. Dependencies: WP04. Lane `lane-f`. `execution_mode: code_change`. Requirements:
FR-005. The patch-target mechanism is **settled and must not be re-derived**: `saas_client.py:19` is a
bare `import time`, the module has exactly two module-level names (`:36`, `:39`), and the backoff is
local variables at `:466-468` — a module-global backoff leak is structurally impossible and is not
funded. What remains open is **which live thread is sleeping inside the patch window**. Narrative goes
to the PR body and to `notes/` **via the orchestrator on the mission branch**; a lane may not write
`kitty-specs/` (C-010).

### WP07 — The token-manager verdict

Subtasks: T023–T026. Dependencies: WP01, WP02. Lane `lane-g`. `execution_mode: code_change`.
Requirements: FR-009. **Re-scoped by the cut**: WP07 previously owned no test file — it measured and
WP08 applied. WP08 is retired, so **WP07 now measures *and* applies**, and is the sole owner of the
five `578a659162` files. Still one live agent in those files (C-007); simply the same one twice.
**Two hard prohibitions, stated in the brief in these words**: *Edit the `reset_token_manager()` call
sites' surrounding docstring/comment and nothing else. Do not remove, weaken, move or annotate the
`monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)` lines at `test_sync_status_per_project_3030.py:83` and
`test_sync_doctor_per_project_3030.py:72`.* And: *Do not touch these files' `_isolated_home` fixtures.*
**This WP closes `#3030`'s matrix row.**

### ~~WP08~~ — RETIRED

**Cut from scope by operator decision, 2026-07-31, after the post-plan adversarial squad. The number
is retired and is not reused.** No file exists for it. Every obligation it carried is re-homed
visibly: the five-file docstring application moved into **WP07**; the three "provably dead" `COLUMNS`
sets are **dropped outright and deliberately NOT reassigned** (F2 measured them live), leaving WP02
with the one constraint that follows — the pinned width must be **≥ 240**; `tests/conftest.py`'s second
owner is gone; and WP13's `blocked_by` swaps WP08 → WP07. The hoist itself goes to a follow-up issue
against `Priivacy-ai/spec-kitty` carrying the measured equivalence-class evidence in
`notes/post-plan-squad-findings.md`. One inherited sequencing note travels with it: **WP03's width
guard must precede any such convergence**, because it is the only guard that would catch a hoist
changing the victim files' render surface.

### WP09 — The `/tmp` root-walk artifact

Subtasks: T027–T028. Dependencies: none. Lane `lane-h`. `execution_mode: code_change`. Requirements:
FR-012. Independent of everything. **C-001 is absolute**: no change to `locate_project_root` /
`resolve_checkout_sync_routing_readonly`, and none to `SPECIFY_REPO_ROOT`'s precedence.

### WP10 — The egress guard

Subtasks: T029–T032. Dependencies: none. Lane `lane-i`. `execution_mode: code_change`. Requirements:
FR-013, FR-014, FR-015. **One WP because all three FRs edit the same file** (C-007); three WPs on one
file is the shared-index failure that lost 13 files on `#3030`. It also owns
`tests/architectural/_baselines.yaml` because the FR-015 measurement is the only thing in this mission
that can move `egress_allowlist_files: 28` or `known_ungated_files: 0`, and that reconciliation must
land in the same change as the matcher edit. **No other WP may edit `_baselines.yaml`.** The WP starts
from the **non-adoption expectation** — but it still re-runs and quotes its **own** count, because a
planning paragraph is not a measurement.

### WP11 — The counter pin

Subtasks: T033–T035. Dependencies: none. Lane `lane-j`. `execution_mode: code_change`. Requirements:
FR-018. **Measured on a tree with NO global timeout**, which is the whole reason WP12 is blocked on it.

### WP12 — The timeout default

Subtasks: T036–T039. Dependencies: **WP11 (hard)**. Lane `lane-k`. `execution_mode: code_change`.
Requirements: FR-016, FR-017. **The mission's only repo-wide package, and the last code-changing WP
merged.** With a global timeout in place WP11's mutant reds on the timeout and the missing pin becomes
unobservable — this is the plan's single hardest sequencing constraint and it is not negotiable.

### WP13 — The shard proof

Subtasks: T040–T043. Dependencies: WP03, WP05, **WP07** (was WP08), WP12. Lane `lane-l`.
`execution_mode: code_change`. Requirements: FR-011.

**Owns exactly one file: `scripts/verify_shard_3115.sh`** — a committed, re-runnable script that
performs the shard proof, plus its recorded output. **It does not own zero files** (that is a hard
`LaneComputationError`, not a singleton lane) **and it does not own a page under `docs/`** (that
obliges frontmatter, a `toc.yml` entry and **two** generated-artefact regenerations, all of them
`lane-d`'s write scope in an earlier `parallel_group` — the post-tasks squad's single CRITICAL). Every
docs ruler in this repo roots at `docs/`, so **nothing under `scripts/` carries a docs obligation**;
WP01's `scripts/repro_3115_render_width.sh` is the precedent. **The prose evidence goes into the
mission dossier, written by the orchestrator on the mission branch** — `kitty-specs/` may not be
written from a lane (`commit_guard.py:84-89`, C-010) — and so does `issue-matrix.json`.

Deliberately **not** blocked on WP06/WP14: FR-010's budget must not hold the shard proof hostage.
**Every obligation WP13 carried before the move it carries after it**: enumerated node-ids with
per-case outcomes, worker count quoted from the run's own `gw` header, `--dist`, marker selection, the
four `--ignore`s, `--cov`, the collected count, and the **job** conclusion — never the workflow's.

### WP14 — PLACEHOLDER: the sync half's terminal state

Subtasks: T044–T045. Dependencies: WP06. Lane `lane-f` (same lane as WP06 **by construction**).
`execution_mode: code_change`. Requirements: FR-010. **Why it exists now**: the friction record's
*"WPs created after planning have no lane, so two gates silently no-op"* — a WP added later defaults to
`lane-a`, makes the lane-staleness gate fire inapplicably (advising a rebase of somebody else's
approved lane), and makes the pre-review regression gate print `no_coverage` on work that received no
gate at all. **Pre-allocating the lane entry is the whole fix**, and ownership is fixed **at planning
time, not at dispatch** — lane membership is computed solely from `owned_files` overlap
(`compute.py:1-11`), so a placeholder with empty ownership would land in its own singleton lane and
outcome A would then write a file another lane's worktree owns.

## Mission-close checklist — the items no gate will raise for you

**WPs park at `approved`** and the matrix resolves at mission close (rule 7). These are the closure
obligations that are **not enforced by any check**, listed because "nothing complained" is the exact
failure mode this mission was opened about.

1. **WP09's and WP10's pre-review gate baselines measured nothing — both approvals rest entirely on
   reviewer evidence, and that must be confirmed at accept.** Each WP's committed
   `baseline-tests.json` records `total: 1, failed: 1` with `<gate-coverage-junit>: no JUnit XML
   artifact produced by the scoped run`, so the regression comparison behind both had a **null
   "before" side**. Neither WP is among the three pre-authorised to close without gate coverage
   (WP07, WP13, WP14-outcome-B), so this is a real gap, not a sanctioned one. **Why it is carried
   rather than re-run**: both approvals were established independently of the gate — WP09's reviewer
   ran two mutation experiments proving the fail-closed pin would pass against a stub that never
   reaches routing, and WP10's reviewer re-derived every figure from source, including a two-arm
   probe showing `strict=True` is the only thing keeping that run honest. The gate's own output on
   this mission has been unreliable in **both** directions: it printed `no new failures` in 7 seconds
   for a file that takes 51 seconds merely to collect (WP09), and an honest
   `no_coverage — excluded scope — unverified` (WP10). **At accept, confirm both approvals cite
   reviewer measurements and not the gate line**, and treat any `baseline-tests.json` whose JUnit
   artifact is absent as *no measurement* rather than as a clean baseline.

1. **SC-017 and SC-018 are the orchestrator's, and no work package carries them.** Both are PR-body
   criteria and neither id appears in any of the 13 WP files — correctly, because a lane cannot write
   a PR body. Recorded here because that is the only place the obligation is discharged from, and an
   unowned criterion with no home is indistinguishable from a forgotten one. **SC-018 is the one that
   matters**: the PR's limits section must state the mission's **principal known unknown** — *what
   makes rich's `is_terminal` true on the CI runner is unidentified*. The workflow sets no
   `FORCE_COLOR`, `TERM` or `TTY_COMPATIBLE`; `is_dumb_terminal` is the only surviving route to a
   width of exactly 80 (the sole explicit width assignment in the repo is monkeypatch-scoped and sets
   10 000), but the trigger was never named. Nothing was tested under xdist. **State it as plainly as
   what was proved** — a PR that reports the fix without the gap is the same shape as a gate that
   prints like a pass.

1. **`evidence_ref` must be a commit SHA or a PR/comment URL — never the scaffold placeholder
   `<link or commit>`. No gate will say so.** Probed: a row at verdict `fixed` carrying that literal
   placeholder returns **`None`** from `_issue_matrix_approval_blocker`
   (`src/specify_cli/cli/commands/agent/tasks_parsing_validation.py:151`) — it passes the `done` gate
   silently, because that blocker adjudicates **verdicts**, never the content of `evidence_ref`. The
   only check on the field is an emptiness check (`_issue_matrix.py`,
   `ISSUE_MATRIX_EVIDENCE_REF_EMPTY`), which fires on an **empty** string, and `<link or commit>` is
   not empty. All three rows (`#3030`, `#3113`, `#3115`) carry the placeholder today. **Every one is replaced with a real handle before `--to done`, and the handle is
   checked by opening it**, not by looking at it.
2. **A `deferred-with-followup` verdict needs its handle in `evidence_ref` ITSELF.** The check
   (`_issue_matrix.py:349-359`) searches `evidence_ref` for `#\d+` or the substring `Follow-up:`.
   **It does not read `scope`, it does not read a WP note, and it does not read `notes/`.** A successor
   number recorded anywhere else reds the row.
3. **Every issue row holds a terminal verdict**, or `--to done` refuses (R13). `in-mission` is not
   terminal.
4. **The acceptance matrix's `overall_verdict` moves off `pending`** only when every criterion carries
   real evidence — and a criterion whose `proof_type` is `automated_test` names the **node-id** and its
   **collected count**, not "the suite is green".
5. **`lanes.json` is re-run after ANY post-finalisation change to a WP's `owned_files` or
   `dependencies`** — and confirmed against the lane table above, **reporting the divergence if there
   is one** rather than adopting it silently. This is a standing obligation, not a one-off: it already
   fired once on this mission. The post-tasks remediation changed WP04's ownership and WP13's artefact
   *after* finalisation, nothing recomputed the file, and the stale copy pointed `lane-l` at a path no
   WP owned while leaving `lane-d` without its `lane-a` edge. Regenerated at `a9899eb85a`; the note at
   the lane table records the full window and its consequence. **Caught by `/analyze`, not by any lane
   check** — no gate compares `lanes.json` against the frontmatter it was computed from, so this item
   is the only thing standing between a stale grouping and a dispatch against it.

### Follow-up candidates raised post-tasks

- **`evidence_ref` accepts its own scaffold placeholder** — `<link or commit>` passes the approval
  blocker at any verdict, because the only check on the field is non-emptiness. **This is the same
  vacuity class as `|| test $? -eq 5`** (an empty collection reads as a green job) **and as
  `no_coverage — skipping the gate cheaply`** (a gate with zero inputs reads as a pass): in all three,
  a mechanism reports success for having done nothing, and the report is indistinguishable from the
  real thing at the point it is read. **Candidate remedy**: reject the scaffold sentinel explicitly, or
  require `evidence_ref` to match a SHA or URL shape at terminal verdicts. Raise against
  `Priivacy-ai/spec-kitty`. It is **not** in this mission's scope — no FR covers the review tooling —
  and it is recorded here rather than absorbed.
