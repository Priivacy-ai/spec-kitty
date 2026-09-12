# Implementation Plan: Sleep-count assertions survive concurrent sleepers

**Branch**: `feat/sync-sleep-count-3136` | **Date**: 2026-08-06 | **Spec**: [`spec.md`](spec.md)
**Input**: Feature specification from `/kitty-specs/sync-sleep-count-3136-01KZ9B5A/spec.md`
**Also binding**: [`analysis-report.md`](analysis-report.md) — the post-spec squad's findings and the two
operator rulings (**R-1** product-side module-local alias, **R-2** mechanism-keyed predicate).
**Base**: `98198e980045752a1f5ce0ba75796d3e5dddadf1` (verified this session:
`git rev-parse upstream/main` → `98198e980045752a1f5ce0ba75796d3e5dddadf1`; `git rev-parse --abbrev-ref HEAD`
→ `feat/sync-sleep-count-3136`).

Every number below traces to a command run in this session, shown with its input count and, where a
known answer exists, a control. Values that remain open are marked `[UNVERIFIED]` and re-listed at the
end. **No test bodies under `tests/sync/` or `tests/cli` were executed** (C-001 — a sibling mission may
hold that window). What was run: `ruff check`, `git rev-parse`/`git diff`, `grep`, `ls`/`find`, three
purpose-written AST probes, and one import-resolution pass reusing the repository's own
`scripts/check_patch_targets.py::_mock_importer`. Static analysis and targeted resolution only.

---

## Summary

The defect is that an assertion's truth value is a function of a **process-global** call counter.
`src/specify_cli/tracker/saas_client.py:19` is a bare `import time`, so
`@patch("specify_cli.tracker.saas_client.time.sleep")` rebinds `sleep` **on the stdlib `time` module
object**; for the whole patch window the mock's recorder counts calls from any live thread in the
pytest-xdist worker.

**R-1** fixes it product-side: `saas_client.py` gains module-scope `_sleep` / `_monotonic` /
`_randbelow` — **bound by assignment (`_sleep = time.sleep`), never by a wrapper `def`** — and routes
its five call sites (`:439`, `:481`, `:484`, `:515`, `:518` — all five opened and confirmed) through
them, so `@patch("…saas_client._sleep")` binds a **module-local** attribute.

**The assertion *text* is unchanged. The patch *target* is not — and that distinction is the whole
mission.** R-1 was recorded as making every existing assertion "correct **unchanged**", and this plan's
first revision propagated that phrasing. It is true of the assertion **expression** and **false of the
decorator target**: `_sleep = time.sleep` binds the function object **at import**, so
`@patch("specify_cli.tracker.saas_client.time.sleep")` mutates the stdlib `time` module's attribute and
**cannot reach it**. Landing the seam without retargeting produces one of two outcomes, both failures:
the five census assertions see 0 attributed calls and go red (and sleep for real, blowing NFR-005), or —
under the wrapper form — **every node stays green while the recorder still counts foreign calls**, and
the mission ships with the defect intact. So the fix is the seam **plus** **24 patch-target retargets**
(`FR-012`; 23 in `test_saas_client.py`, 1 in `test_saas_client_origin.py` — enumerated per-line in
`## Project Structure` below and in `spec.md`'s `### The 24 patch-target retargets`).

With that, all five census assertions plus `:787`'s `mock_randbelow.call_count == 3` and `:804`'s
`[0.0, 301.0]` are correct **with their text unchanged**, under four binding conditions: an ADR that
adjudicates the **idiom** rather than the instance, a gate keyed on the mechanism and asserting the
seam's routing **on both the product and the test side**, `_poll_jitter_multiplier` resolved, and the 24
retargets.

**R-2** closes the class: refuse a `patch()` target whose penultimate segment resolves to a shared
module object when the resulting mock is read by a count or equality assertion, enforced over
`tests/sync/`.

**Three measurements taken this session change the shape of the work, and the plan is built on them
rather than on the spec's counts:**

1. **R-2's predicate as literally worded is over-broad by two orders of magnitude.** Of **664** dotted
   `patch()` sites under `tests/sync/` (two independent AST probes agree: probe 1 reported
   `total_patch_sites=664`; probe 3's buckets sum to `649 + 15 = 664`), **649 (97.7%)** have a
   penultimate segment that resolves to a `ModuleType`. That is not a finding about this cone — it is
   how `unittest.mock._get_target` works: it splits the last segment off and imports the rest, so the
   penultimate segment is *normally* a module. Of the 649, **356 are a module's own attribute**
   (`patch("specify_cli.sync.client.WebSocketClient")` — the ordinary, correct idiom, not the hazard),
   **286 are reach-through aliases** (`__name__` ≠ the dotted path — `saas_client.time.sleep` resolving
   to the stdlib `time`), and **7 are direct foreign-module targets** (bare `patch("subprocess.run")`,
   `patch("asyncio.run_coroutine_threadsafe")`). The discriminating property is not "penultimate is a
   `ModuleType`" but **"the patched object is a module whose identity is shared outside the module under
   test"**, decided as: the resolved module's `__name__` differs from the dotted module path (reach-through)
   **or** the resolved module is not first-party. The plan implements that formulation and records it as a
   correction to R-2's wording, not a narrowing of its intent.
2. **The class under `tests/sync/` is ≥ 29 instances across ≥ 10 files, not 14 across 4.** The spec's
   "9 further instances" is an undercount by its own two blind spots plus a third the spec did not
   identify: it never left `test_final_sync_diagnostics.py` and `test_git_metadata.py`. Newly found and
   opened this session — `test_git_metadata.py:398`, `test_git_metadata.py:522`,
   `test_runtime.py:673`, `test_runtime.py:710`, and **9** `mock_post.call_count` reads under
   `specify_cli.sync.batch.requests.post` / `specify_cli.sync.body_transport.requests.post`
   (bare `import requests` at `batch.py:19` and `body_transport.py:17`). All in `fast`-marked files, so
   all inside CI's `-m "fast and not windows_ci"` selection.
3. **Consequence: "allowlist empty at merge" (R2's SC-007 item 5) and "enforced over `tests/sync/`"
   (FR-005) cannot both hold in this mission.** The mission hardens the `saas_client` slice by the R-1
   alias. The remaining ≥ 22 instances need a seam in **three** further product modules plus a
   **threaded keyword argument** in a fourth — `batch.py` already exposes
   `run_final_sync_with_retries(…, *, sleep=None)` at `:628-631`, so its row closes at
   `background.py:467` with no new seam at all (see `### The competing idiom`). The plan therefore
   ships the gate with a **frozen, shrink-only baseline in `tests/architectural/_baselines.yaml`** — the
   charter's own canonical home for a mutable architectural allowlist (Burn-down Policy (a)) and the
   mechanism standing order 2 names for exactly this case ("freeze current offenders as a baseline when
   a litter class cannot be cleared in-mission"). **And the baseline must be *registered* in
   `test_ratchet_baselines.py`, or it governs nothing**: measured, that meta-test checks only for
   *missing* keys and runs both comparisons off hardcoded lists, so two of its twelve existing keys are
   already inert with the suite green (BLOCKER-3, IC-06). This is recorded as a **documented exception**
   against R2's SC-007 item 5, not resolved silently; `spec.md`'s item 5 is restated to the charter's
   shrink-only-plus-registered form.

A fourth measurement removes a duplicate authority before it is created: **`scripts/check_patch_targets.py`
already exists**, is `[ENFORCED]` in CI (`.github/workflows/ci-quality.yml:884`), and its `_mock_importer`
(`:80-106`) already performs exactly the progressive-import-plus-`getattr` resolution R-2's predicate
needs. Neither `spec.md` nor `analysis-report.md` mentions it. The new analyzer consumes that resolver
rather than reimplementing it.

---

## Technical Context

**Language/Version**: Python 3.12 for every command. **Pinned, and the pin is load-bearing**: CI's
`fast-tests-sync` job runs Python 3.12 (`.github/workflows/ci-quality.yml:1161-1172`,
`uv run python -m pytest` — CI is safe because every job runs `uv sync --frozen --all-extras` first at
`:1145`), the ambient interpreter on this machine is 3.14.x, and
`~/.local/bin/{spec-kitty,pytest,ruff,mypy}` are first on `PATH` and resolve to an
unrelated checkout (all four verified). Every command in every WP prepends `<repo>/.venv/bin` to `PATH`
**and** verifies `command -v` before trusting a result.

**Environment as measured** (this supersedes `spec.md`'s original `### Environment` table, which
recorded 3.11.15 with no `pytest` and no `ruff`; `spec.md`'s `### Environment` is now the canonical
statement and carries the same evidence):

| Fact | Value | How |
|---|---|---|
| `.venv/bin/python -V` | **3.12.13** | run — matches CI |
| `.venv/bin/pytest --version` | **9.0.3** | run |
| `.venv/bin/ruff --version` | **0.15.12** | run |
| `.venv/bin/mypy --version` | **1.20.2** | run |
| `ruff check .` repo-wide at HEAD | `All checks passed!` `EXIT=0` | run |
| `uv` | **0.10.12** at `/usr/bin/uv` | `command -v uv` |
| `.python-version` | `3.11.15` | **diverges from venv and CI** — record, do not fix (outside C-004) |
| `docs-freshness.yml` interpreter | **3.11** | `uv python install 3.11` at `:17` — IC-03's docs commands run there, *not* on 3.12 |

### `uv run --python 3.12 …` uninstalls the test runner — the evidence, recorded once so no WP re-discovers it

**This is BLOCKER-2, and it is the reason the venv was destroyed twice.** `pytest` / `ruff` / `mypy` live
only in `[project.optional-dependencies]` (`pyproject.toml:100-115`); `[dependency-groups] dev` carries
type stubs only; there is no `[tool.uv]` block. So a `uv run`/`uv sync` **without extras** resolves the
default set and removes the toolchain. Proved non-destructively:

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

**Observed twice, not hypothesised.** Once during planning (3.11.15 → 3.12.13, tools dropped). Once
again during the post-plan pass, where a bare `uv run` reached the shell by accident and **recreated
`.venv` at 3.11.15** — because a bare `uv run` honours `.python-version`, so the destructive path *also*
silently downgrades the interpreter two minor versions away from CI, in addition to removing the runner.
Recovery, verified to restore 3.12.13 / pytest 9.0.3 / ruff 0.15.12 / mypy 1.20.2:

```
uv sync --python 3.12 --extra test --extra lint
```

**The two sanctioned command forms. Every command in this plan and in `spec.md` uses one of them.**

```
# Form 1 (preferred) — direct, no resolver involvement.
./.venv/bin/python -m pytest …
./.venv/bin/ruff check .

# Form 2 — uv-driven, extras pinned so the toolchain survives the resolve.
uv run --python 3.12 --extra test --extra lint python -m …
```

**A bare `uv run --python 3.12 …` in any WP transcript is a defect, not a style preference.** R2's plan
pinned only one of its nine commands at all — the other eight resolved to the foreign `~/.local/bin`
checkout — and the one that *was* pinned was pinned to the destructive form. The first WP re-asserts the
environment and records `command -v python pytest ruff mypy` plus the four `--version` lines before any
acceptance arm runs (NFR-005, SC-014 — both arms must be the same interpreter). **A transcript without
the `command -v` line is not evidence.**

**Primary dependencies**: `unittest.mock` (`patch`, `_get_target` semantics), `ast`, `importlib`,
`pytest` (+ `pytest-xdist`), `ruff`, and the in-repo `scripts/check_patch_targets.py`.

**Storage**: N/A. The only persisted state the mission adds is one YAML key in
`tests/architectural/_baselines.yaml`.

**Testing**: pytest. Enforced scope for the gate is `tests/sync/`, **never `tests/cli`** (C-001 forbids
this mission from running it). Acceptance arms are injections (SC-003/004/005), static measurements
(SC-001/002/007/008/010/012/013/015/016), or repetition-counted determinism (SC-009). No arm is a pass
of any breadth — a clean full shard is the pre-fix outcome ~39% of the time.

**Target platform**: Linux CI runner (`blacksmith-4vcpu-ubuntu-2404`), `-n auto --dist loadfile`,
`--timeout=240 --timeout-method=signal`.

**Project type**: single Python project (`src/` + `tests/` + `scripts/`).

**Performance goals**: NFR-005 — the census nodes plus the new guard module add **≤ 5.0 s** wall clock
to a serial `tests/sync/tracker/` run; no individual test exceeds **60 s**. Both arms on the same
3.12.x interpreter, both `python -V` printed.

**Constraints**: C-001 through C-010 as restated in `spec.md`. Structurally binding here:
`saas_client.py` may change only by the declared seam and the jitter resolution (C-004);
`ci-quality.yml` must not change at all (C-008); `ruff format` is never run (C-002); mutation/probe
plugins are owned by **exact filename**, never by a `scripts/mutants/**` glob (C-009).

**Scale/scope of the measured surface** (all commands run this session):

| Denominator | Value | Command | Control |
|---|---|---|---|
| `.py` files under `tests/sync/` (recursive) | **141** | `find tests/sync -name '*.py' \| wc -l` | `ls tests/sync/*.py \| wc -l` = 119; `+ 22` tracker = 141 |
| `.py` files in `tests/sync/tracker/` | **22** | `ls tests/sync/tracker/*.py \| wc -l` | this is `spec.md`'s `files_scanned: 22` — see the SC-001 defect below |
| dotted `patch()` sites under `tests/sync/` | **664** | AST probe 1 | AST probe 3 buckets sum `649 + 15 = 664` |
| … penultimate resolves to a `ModuleType` | **649** | AST probe 3 (`_mock_importer`) | — |
| … own-module attribute (**not** the hazard) | **356** | AST probe 3 | — |
| … reach-through alias (`__name__` ≠ path) | **286** | AST probe 3 | includes all 14 `saas_client.time.sleep` sites |
| … direct foreign-module target | **7** | AST probe 3 | bare `subprocess.run` ×4, `asyncio.run_coroutine_threadsafe` ×2, +1 |
| `saas_client.time.sleep` patch decorators | **13 + 1 = 14** | `grep -c 'patch("specify_cli.tracker.saas_client\.time\.sleep")'` → `14` in `test_saas_client.py`, `1` in `…_origin.py` = 15 hits; `:559` is inside the docstring spanning `:513`–`:762` (both opened) | naive `grep -c 'time\.sleep' tests/sync/tracker/test_saas_client.py` = **28** against 13 real sites — the spec's named trap, reproduced |
| the spec's wrong provenance command | **68** | `grep -rc 'patch("specify_cli.tracker.saas_client\.' tests/sync/tracker/test_saas_client.py` | matches the analysis-report's stated 68 — control against a known answer |
| `_poll_jitter_multiplier` occurrences in `src/` + `tests/` | **1** (definition only) | `grep -rc '_poll_jitter_multiplier' src/ tests/` | SC-013 sub-3 states exactly `1` fails — reproduced |
| `_PinnedLeak(` elements in `_leak_guard.py` | **12** | `grep -c '_PinnedLeak(' tests/sync/_leak_guard.py`; declaration at `:333` | `_WatchedGlobal(` = 17, a different registry — see IC-06 |
| inventory row-id rows | **53** | `grep -cE '^\| E[0-9]+ \|' docs/development/process-global-inventory-3115.md` | matches the "53 verdicts" figure in the issue |
| inventory unverified stamps today | **0** | `grep -c unverified <inventory>` | `grep -c '3136' <inventory>` = **0** |
| `per-file-ignores` blocks | `ruff.toml` **1**, `pyproject.toml` **1** | `grep -c per-file-ignores ruff.toml pyproject.toml` | confirms SC-012's point that an existence check proves nothing |
| `docs/adr/3.x/` entries | **98** | `ls docs/adr/3.x/ \| wc -l` | naming `YYYY-MM-DD-N-slug.md` per its `README.md` |
| `tests/architectural/*.py` | **165** | `ls tests/architectural/*.py \| wc -l` | `_baselines.yaml` carries **12** top-level gate keys |
| ruff complexity ceiling | **15** | `grep -n 'max-complexity' pyproject.toml` → `:287` | `ruff check --select C901 src/specify_cli/tracker/saas_client.py` → `All checks passed!` |

**The stdlib-attribute slice, measured by AST across `tests/sync/`** — 80 sites in 8 files, versus the
4 files `spec.md` names:

| Target attribute | Sites | Files |
|---|---|---|
| `subprocess.run` | 34 | `test_git_metadata.py` (30), `test_project_identity.py` (4, **bare** `patch("subprocess.run")`) |
| `time.sleep` | 16 | `test_saas_client.py` (13), `test_saas_client_origin.py` (1), `test_final_sync_diagnostics.py` (2) |
| `time.monotonic` | 14 | `test_saas_client.py` (9), `test_git_metadata.py` (5) |
| `asyncio.sleep` | 8 | `test_reconnection.py` |
| `random.uniform` | 3 | `test_reconnection.py` |
| `asyncio.run_coroutine_threadsafe` | 2 | `test_runtime.py` (**bare** target) |
| `threading.Thread` | 2 | `test_final_sync_diagnostics.py`, `test_issue_598_hang_fixes.py` |
| `secrets.randbelow` | 1 | `test_saas_client.py:498` |

Form split across those 80: **57 decorator / 23 context-manager**. The context-manager share is 29% —
the blind spot the spec identified is not an edge case in this cone.

---

## Charter Check

*GATE: must pass before implementation. Re-checked after the concern map below.*

Every `Pass` here is one the charter would actually grant on the evidence cited. Where it would not,
the row reads `Partial` or `Documented exception` with the reason, so the post-plan squad withdraws
nothing.

| # | Charter rule | Status | Basis / reason |
|---|---|---|---|
| 1 | **Single canonical authority** (Governing Principles; `DIRECTIVE_044`) | **Partial** | Reconciled in three places: the target-resolution authority stays `scripts/check_patch_targets.py::_mock_importer` (`:80-106`) and the new analyzer imports it; the mutable allowlist goes in `tests/architectural/_baselines.yaml`, the charter's declared home (Burn-down Policy (a)), governed by `tests/architectural/test_ratchet_baselines.py`; the census and the gate are **one analyzer with two front doors**, not two implementations. Still `Partial`: `check_patch_targets.py` extracts targets by **regex** (`_PATCH_TARGET_RE`, `:33-35`) while NFR-007 requires the census be AST-based, so two extractors will coexist over the same tree and can silently disagree on the site inventory. Closed by a cross-check arm (IC-04), not by unification. Full unification (porting the CI lint to AST) is out of scope and named as a follow-up. |
| 2 | **Architectural alignment** (`DIRECTIVE_001`) | **Pass** | The alias seam is three module-scope names inside the module that already owns the calls; no boundary crossed. The gate lands in `tests/architectural/`, the existing home for 165 architectural gates. No change to shared-package boundaries. |
| 3 | **DDD + tiered rigour** | **Pass** | Core-domain rigour (the alias seam, the predicate) gets ADR + gate + control fixture; glue (the inventory stamp, the non-goal record) gets prose with a grep criterion. |
| 4 | **ATDD-first** (binding per `C-011`, charter `:504-517`) | **Documented exception** | Templated in Complexity Tracking. The base-branch red exists and is structural — `patch("…saas_client._sleep")` cannot be set up on `98198e980` because the attribute provably does not exist there — but an `AttributeError` at patch **setup** does not "pin the user-observable behaviour the WP delivers" in the charter's sense. The behaviour-pinning red (the pre-fix expression form raising `AssertionError` against a polluted recorder) is an **injection** that raises on any branch, which the spec itself says is not base-branch red. Both are shipped; the exception is that the ATDD arm's redness on base is structural rather than assertional. |
| 5 | **Glossary & terminology adherence** | **Pass** | C-010's command is an owned deliverable (IC-08): `./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q` → `EXIT=0`, transcript recorded. The file exists (verified). The ADR and the inventory stamp are the prose touches that need it. |
| 6 | **Standing order 1 — adversarial squad cadence** | **Pass** | A post-plan squad is expected before `/spec-kitty.tasks`; advisory, never a gate. The post-spec squad's output is `analysis-report.md` and is treated as binding input here. |
| 7 | **Standing order 2 — campsite cleaning / incremental debt paydown** | **Partial** | The domain-matched clean is real and in-scope: `_poll_jitter_multiplier` (`saas_client.py:104-106`, **1** occurrence measured, zero callers, max multiplier `1.2` against the live inline `1.1999` at `:515-516`) is resolved in the same change as the seam it is the cautionary precedent for. `Partial` because the ≥ 22 sibling instances are **frozen at baseline, not cleared** — which is the charter's own prescribed response ("freeze current offenders as a baseline when a litter class cannot be cleared in-mission") but is not a clean pass. |
| 8 | **Standing order 4 — test remediation / red-first, live evidence, never retry-to-green** | **Pass** | The red is kept live as a shipped guard (FR-003), not transcribed. The probe's magnitude floor is asserted in-test and printed (NFR-001). SC-009 pins repetition counts (3× per topology, 10× for the guard) with per-run counts reported rather than a summary verdict. |
| 9 | **Standing order 5 — architectural gate discipline: non-vacuous gate, concrete floor, self-mutation test, shrink-only allowlist** | **Documented exception** | The charter grants **shrink-only**; R2's `spec.md` SC-007 item 5 demanded **empty at merge**. Measured, those are incompatible: ≥ 22 in-class instances under `tests/sync/` are outside R-1's seam, and an empty allowlist over that scope forces either a red gate or a narrowed scope — and a narrowed scope is exactly BLOCKER-2's failure ("`corruptible_assertions: 0` while the class is open in this mission's own window"). **`spec.md` SC-007 item 5 is now restated to the charter's shrink-only form**, so this is a documented exception against R2's own criterion rather than a live contradiction between the two documents. Templated in Complexity Tracking. The three non-vacuity requirements are met in full: concrete floor (named files + the `13 + 1` split + four node-ids), three self-mutation arms on forms absent from the tree, and the baseline is shrink-only and ratchet-governed — **the last of which is true only after IC-06's four edits to `test_ratchet_baselines.py`; see row 17, downgraded to `Pass only if registered`.** |
| 10 | **Standing order 6 — canonical sources, never improvise** | **Pass** | Plan authored from `packs/built-in/missions/software-dev/templates/plan-template.md` (section order followed exactly). Existing surfaces reused rather than re-created: `check_patch_targets.py`'s resolver, `_baselines.yaml`, `tests/architectural/`, `docs/adr/3.x/` + `scripts/docs/freshen_adr_inventory.py`. **Four canonical precedents R2 did not cite, now cited and copied rather than re-invented**: (a) the honest-ratchet shape — `tests/architectural/_inert_slots_baseline.yaml` + `test_no_inert_schema_slots.py` (permanently-empty `ALLOWLIST` pinned by `test_allowlist_is_empty`, per-row `owner:`/`disposition:`, owner-completion arm `test_a_baseline_entry_does_not_survive_its_owner`, registration arms `test_the_baseline_size_is_registered_with_the_charter_ratchet`), cited by IC-06; (b) the AST call-site resolution shape — `test_protection_resolver_call_sites.py:90-109`, cited by IC-06's arm 4; (c) the in-test `sys.path` insertion for importing a `scripts/` module — `test_docs_cli_reference_parity.py:52-56`, cited by IC-04/IC-06; (d) the existing **call-site injection** idiom — `batch.py:628-641`, which IC-03's ADR must adjudicate against rather than ignore. The `frozen-baseline-shrink-only-ratchet` tactic is named explicitly by IC-06. |
| 11 | **Standing order 7 — git & workflow discipline** | **Pass** | No commit from this planning step; draft PR first; the operator merges. C-009's exact-filename ownership is honoured in the file map below — no path is owned by a directory glob. |
| 12 | **Standing order 8 — mission hygiene, reviewer ≠ implementer, one owner per path** | **Pass** | `## Project Structure` assigns exactly one concern per path; no path appears twice. |
| 13 | **Standing order 9 — red-main discipline; Pre-existing Failure Reporting Rule** | **Partial** | The base is honestly red on this class (`11 of 18` `fast-tests-sync` jobs on pristine `main`, including at `98198e980`). The charter's Pre-existing Failure Reporting Rule requires a GitHub issue before treating that as accepted baseline; `#3136` itself is that issue for the sleep-count nodes, but the **newly found** instances (`requests.post`, `asyncio.run_coroutine_threadsafe`, `test_git_metadata.py:398`) have no ticket. **IC-08** owns filing them (IC-09 folded into it). `Partial` until filed. |
| 14 | **Testing Requirements — 90%+ coverage for new code** | **Partial** | Not verifiable pre-implementation. The new surfaces are analyzer + gate + guard, all of which are themselves tests or directly exercised by tests, so the structural odds are good; the WP must report `--cov` on the changed files rather than assert it here. |
| 15 | **Technical Standards — `mypy --strict` must pass** | **Partial** | CI runs mypy **advisory**, over `src/specify_cli src/charter src/doctrine` only (`ci-quality.yml:845-851`, `[INFO] Run mypy report (advisory)`). The mission's new code lands under `scripts/` and `tests/`, i.e. **outside** the CI mypy scope, so "mypy --strict passes" is not machine-enforced for these paths. The WP runs `mypy --strict` on them explicitly and records the result; `Partial` because CI will not catch a regression there. |
| 16 | **Quality Gates — required pytest surface passes** | **Pass, deferred** | C-001 defers the `tests/sync` arms to the implementing WP, which must hold the window. Nothing in this plan claims a suite result. |
| 17 | **Burn-down Policy (a) — every mutable architectural allowlist has a baseline in `tests/architectural/_baselines.yaml`; growth FAILS CI** | **Pass only if registered** | **Downgraded from `Pass`. R2 graded this on "growth FAILS CI", which is false for a merely-added key.** Adding a 13th top-level key to `_baselines.yaml` does **not** by itself make growth fail anything — the ratchet's comparisons run off **hardcoded lists**, so an unregistered key is read by nothing. Measured: 12 YAML keys, 11 in `_REQUIRED_TOP_LEVEL_KEYS`, and only **10** read by any comparison (`data["…"]` subscript). `test_all_declarations_required` is in the *required* set yet is read by no comparison; `test_no_dead_symbols` is in the YAML, in neither the required set nor any comparison. `pytest tests/architectural/test_ratchet_baselines.py -q` is **green with both inert**. So a 13th key joins two existing inert keys unless IC-06 *registers* it in `test_ratchet_baselines.py`. The row passes **only** on the three enumerated edits plus the reverse-containment arm in IC-06 — otherwise the baseline is decoration. `test_ratchet_baselines.py` appeared in **no** IC's surfaces in R2. |
| 18 | **Code Quality — new code passes ruff with zero suppressions** | **Pass** | `ruff check .` is green repo-wide at HEAD (`All checks passed!`, `EXIT=0`), so the mission inherits a clean baseline and SC-012's diff-shaped checks are meaningful. Complexity ceiling 15 registered below. |

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/
├── spec.md                # input (NOT edited by this plan)
├── analysis-report.md     # input (NOT edited by this plan)
├── plan.md                # this file
└── tasks/                 # /spec-kitty.tasks output — NOT created here
```

### Source and test surfaces — one owner per path

No path appears twice. Ownership is by **exact filename** throughout (C-009): there is no
`scripts/mutants/**` glob, and the two probe/mutant files below are named individually.

```
src/specify_cli/tracker/saas_client.py                     ← IC-02  (alias seam by assignment + jitter resolution)
docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md ← IC-03  (new; ADR — adjudicates the IDIOM)
docs/adr/3.x/README.md                                      ← IC-03  (index row only)
docs/development/3-2-page-inventory.yaml                    ← IC-03  (GENERATED lockfile — regen, never hand-edit)

scripts/check_patch_targets.py                              ← IC-04  (resolver export; no behaviour change)
scripts/patch_seam_census.py                                ← IC-04  (new; <census> — the sole analyzer)

tests/architectural/test_shared_module_object_patches.py    ← IC-06  (new; <gate>)
tests/architectural/_baselines.yaml                         ← IC-06  (new top-level key only)
tests/architectural/test_ratchet_baselines.py               ← IC-06  (register the new key + reverse-containment arm)
tests/architectural/test_patch_seam_census_control.py       ← IC-04  (new; <census-control>)
tests/architectural/_fixtures/patch_seam_control/           ← IC-04  (new; control fixture modules)

tests/sync/tracker/test_saas_client.py                      ← IC-02  (:55-57 docstring + 23 patch-target retargets)
tests/sync/tracker/test_saas_client_origin.py               ← IC-02  (1 patch-target retarget at :229)
tests/sync/tracker/test_sleep_attribution_guard_3136.py     ← IC-02  (new; <guard> — merged from IC-05)

docs/development/process-global-inventory-3115.md           ← IC-07  (verdict-column stamp; BODY ONLY, no frontmatter)
kitty-specs/.../notes/non-goals-3136.md                     ← IC-07  (<guard-rationale>; C-005 reasons)
kitty-specs/.../notes/environment-3136.md                   ← IC-01  (interpreter transcript; command -v + versions)
kitty-specs/.../notes/constraint-enforcement-3136.md        ← IC-08  (SC-016 transcripts, <wp-notes>)
kitty-specs/.../notes/ci-observation-3136.md                ← IC-08  (non-gating CI observation)
kitty-specs/.../notes/c001-window-3136.md                   ← IC-01  (C-001 window handshake — acquire/release)
```

**Six ownership corrections against R2's map, each a defect that would have surfaced at `implement`:**

1. **`tests/sync/tracker/test_saas_client_origin.py` was absent from the map entirely** — while carrying
   census assertion #5 (`:261`) *and* a required retarget (`:229`). A plan that does not own it cannot
   deliver the fix. Now owned by IC-02.
2. **`test_saas_client.py`'s permitted change was "docstring at `:55-57` **ONLY**"** — which forbids the
   23 retargets that constitute the fix. Restated as **the `:55-57` docstring plus the enumerated
   patch-target retargets**. Because `owned_files` is file-granular and cannot express "these lines
   only", the restriction is expressed as an **acceptance arm on the diff shape** — see IC-02.
3. **`tests/architectural/test_ratchet_baselines.py` appeared in no IC's surfaces**, so the new baseline
   key would have been read by nothing (Charter row 17). Now owned by IC-06.
4. **`docs/development/3-2-page-inventory.yaml` was unowned** while `docs-freshness.yml` reds every PR
   without it. Now owned by IC-03 (BLOCKER-5).
5. **`notes/constraint-enforcement-3136.md` had one declared owner and three writers** (IC-01, IC-08,
   IC-09), with IC-01→IC-08 not a declared edge. IC-01's transcript is split into
   `notes/environment-3136.md`; IC-09 is folded into IC-08, so the file now has exactly one writer.
6. **`tests/architectural/fixtures/` does not exist** — the directory is `_fixtures/` (verified:
   `ls -d tests/architectural/_fixtures` succeeds, `.../fixtures` does not). Corrected, and the fixture
   modules must use **non-`test_` names** so pytest does not collect them as tests.

**`pytestmark` — no concern owned it in R2, and its absence is two failures, not one.**
`tests/architectural/test_pytest_marker_convention.py` requires a module-level `pytestmark` (`:89-95`).
Per new file:

| New file | Required `pytestmark` | Why this marker |
|---|---|---|
| `tests/sync/tracker/test_sleep_attribution_guard_3136.py` | `pytest.mark.fast` | **Two failures without it**: (a) it never runs in `fast-tests-sync`, whose selection is `-m "fast and not windows_ci"` — so the guard is shipped but never executed; and (b) it becomes a **gate-coverage orphan** against `tests/architectural/_gate_coverage_baseline.json`, whose `orphan_files` is `[]` and `orphan_test_count` is `0` (both verified), so `test_gate_coverage.py` reds on any new orphan file. |
| `tests/architectural/test_shared_module_object_patches.py` | `pytest.mark.architectural` | matches the 165 siblings; `test_no_inert_schema_slots.py:300` is the precedent form (`pytestmark = [pytest.mark.architectural]`). |
| `tests/architectural/test_patch_seam_census_control.py` | `pytest.mark.architectural` | same. |

**Importing `scripts/` modules from a test** (IC-04's resolver reuse, IC-06's `check_patch_targets`
cross-check) needs an explicit `sys.path` insertion — the canonical in-repo shape is
`test_docs_cli_reference_parity.py:52-56`:
`if str(_REPO_ROOT) not in sys.path: sys.path.insert(0, str(_REPO_ROOT))`, then
`from scripts.… import …  # noqa: E402`. The `noqa: E402` there is pre-existing and load-bearing (module
import not at top of file); it is the one narrowly-justified suppression this mission inherits rather
than adds.

**Paths deliberately NOT changed, and why** — each is a claim a reviewer can falsify with one command:

| Path | Why untouched | Check |
|---|---|---|
| `.github/workflows/ci-quality.yml` | C-008: the fix must survive the existing composition, not be enabled by changing it | `git diff 98198e980 -- .github/workflows/ci-quality.yml` → **no output**, reported next to a **loud** sibling diff on `saas_client.py` (SC-016's positive twin) |
| `tests/sync/_leak_guard.py` | It owns **teardown residue**, not in-window observation. `time.sleep` is correctly absent from `_WATCHED_GLOBALS` (`:101`) | `git diff 98198e980 -- tests/sync/_leak_guard.py \| grep -cE '^\+\s*_PinnedLeak\('` = **0**, plus an AST count of `_PINNED_LEAKS`' elements pinned at **12** |
| `tests/sync/conftest.py` | The `#3115 FR-007` leak guard is inherited and live; its printed strings at `:485`/`:494` are what SC-008's positive twin greps | no diff |
| `ruff.toml`, `pyproject.toml` | SC-012: no added `per-file-ignores` entry, no widened `exclude` | `git diff 98198e980 -- ruff.toml pyproject.toml` reported **as diff text**, not a count |
| `src/specify_cli/sync/git_metadata.py`, `body_transport.py`, `client.py` | Their instances are **frozen at baseline**, not hardened — see IC-06 and the residue table | each appears in the baseline entry with a `file:line` + target + assertion-form triple |
| `src/specify_cli/sync/batch.py`, `background.py` | Frozen at baseline **for this mission**, but the justification R2 gave was wrong and is corrected below — this row is closable by **threading one keyword argument**, not by a new alias seam | `background.py:467` is `run_final_sync_with_retries(self._perform_sync)` — the one caller that does not thread the seam that already exists |

### The competing idiom — `batch.py` already has a working seam, and R2's plan never saw it

**This is the MAJOR the post-plan squad's seam lens found, and it changes what IC-03's ADR must say.**
`grep -in 'inject\|sleep=\|dependency'` over all three mission documents returned **zero hits** in R2 —
the plan proposed an alias seam as though no seam existed anywhere in the cone. Measured, every line
opened:

| Fact | Evidence |
|---|---|
| `batch.py` already exposes a **call-site injection point** | `:628-631` — `def run_final_sync_with_retries(sync_operation, *, sleep: Callable[[float], None] \| None = None)` |
| …with a stdlib default | `:641` — `sleeper = time.sleep if sleep is None else sleep` |
| …threaded all the way down | `:648`, `:655`, `:669`, `:674`, `:681`, `:684`, `:693`, `:700` |
| **Three tests in the very file this plan freezes already use it** | `test_final_sync_diagnostics.py:180`, `:207`, `:239` — all `sleep=sleeps.append` |
| The frozen row reaches through `time` for **one** reason | `background.py:467` — `run_final_sync_with_retries(self._perform_sync)`, the sole caller that does not thread the parameter that already exists |

**Two consequences, both of which R2 got wrong.**

1. **The `batch.py` baseline row's justification is corrected.** R2's IC-09 ticket text said the residue
   "requires alias seams in four more product modules". That is **false for `batch.py`**: the row at
   `test_final_sync_diagnostics.py:309` is closable by passing `sleep=` at `background.py:467` — one
   keyword argument, no new seam, no new idiom, and the three sibling tests in the same file already
   demonstrate the pattern. It stays frozen in this mission only because `background.py` is outside
   C-004's permitted-hunk set; the **filed issue must say "thread the existing parameter", not "add an
   alias"**, or a successor will institutionalise a second seam in a module that already has one.
2. **IC-03's ADR must adjudicate the *idiom*, not the instance.** Otherwise the mission ships two seam
   styles with no precedence rule — which is the "single canonical authority" failure the charter's
   Standing order 6 exists to prevent, and it would be introduced *by* the ADR meant to establish
   canonicity. The binding rule, now `FR-011`:

   > **Where a module already exposes a call-site injection point, thread it. Introduce a module-local
   > alias only where the stdlib call has no threadable caller.**

   Under that rule `saas_client.py` earns an alias — its `time.sleep` calls sit inside
   `_request_with_retry` / `_poll_operation`, invoked from `SaaSTrackerClient`'s public methods with no
   injectable seam and no caller positioned to supply one — and `batch.py` does **not**. The ADR must
   state this as a rule with both worked examples, and **relate itself explicitly** to
   `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md` (verified present), which
   already decided seam + AST call-site gate + curated allowlist **against** full dependency injection.
   This mission is a second instance of that decision, not a new one.

**The five sites `saas_client.py` reroutes** — every one opened and read this session, not inferred
from the spec's line list:

| Line | Today | After R-1 | Module-qualified symbol |
|---|---|---|---|
| `:439` | `time.sleep(float(wait_seconds))` | `_sleep(float(wait_seconds))` | `specify_cli.tracker.saas_client.SaaSTrackerClient._request_with_retry` |
| `:481` | `start = time.monotonic()` | `start = _monotonic()` | `specify_cli.tracker.saas_client.SaaSTrackerClient._poll_operation` |
| `:484` | `elapsed = time.monotonic() - start` | `elapsed = _monotonic() - start` | same |
| `:515` | `jitter_basis_points = secrets.randbelow(4000)` | `… = _randbelow(4000)` | same |
| `:518` | `time.sleep(jittered_delay)` | `_sleep(jittered_delay)` | same |

**The dead seam, and why it is the precedent** — `specify_cli.tracker.saas_client._poll_jitter_multiplier`
at `:104-106` returns `0.8 + (secrets.randbelow(4001) / 10000.0)`, maximum multiplier **1.2**. The live
inline jitter at `:515-516` is `secrets.randbelow(4000)` / `0.8 + (jitter_basis_points / 10000)`,
maximum **1.1999**. Measured: `grep -rc '_poll_jitter_multiplier' src/ tests/` → **1** — the definition,
zero callers. SC-013 sub-3 states that exactly `1` **fails**; the two acceptable outcomes are `0`
(deleted) or `≥ 2` (promoted to sole authority, with the inline duplicate at `:515-516` gone).
**Recommendation: delete.** Promotion would put a `secrets.randbelow` call behind a helper, and then
`test_saas_client.py:498`'s `@patch("…_randbelow")` with its 3-element `side_effect` — which produces
the `[0.9, 2.0, 4.4]` contract via factors 1000/2000/3000 — would need the helper patched instead,
changing an assertion R-1 exists specifically to leave **unchanged**. Deletion resolves the
`1.2`/`1.1999` disagreement in the direction that keeps the live code the only authority and touches no
test. If the implementing WP promotes instead, it must show `:787` and `:786` still pass unmodified.

**The nine census / sibling assertions in the `saas_client` slice** — every `file:line` opened:

| # | `file:line` | Node (module-qualified) | Text as it reads today | Kind |
|---|---|---|---|---|
| 1 | `tests/sync/tracker/test_saas_client.py:784` | `TestPolling.test_exponential_backoff_intervals` (def `:505`, decorators `:498`/`:502`/`:503`, docstring `:513-762`) | `assert len(sleep_calls) == 3` | count, via alias `sleep_calls = mock_sleep.call_args_list` (`:783`) |
| 2 | `…test_saas_client.py:786` | same | `assert delays == [0.9, 2.0, 4.4]` | list equality, via alias `delays = [c.args[0] for c in sleep_calls]` (`:785`) — **also** count-dependent |
| 3 | `…test_saas_client.py:787` | same | `assert mock_randbelow.call_count == 3` | count; `secrets.randbelow` |
| 4 | `…test_saas_client.py:937` | `TestRetryBehaviors.test_429_respects_retry_after` (def `:901`, decorator `:899`) | `mock_sleep.assert_called_once_with(3.0)` | count + value |
| 5 | `…test_saas_client.py:957` | `TestRetryBehaviors.test_429_defaults_to_5s_when_missing` (decorator `:939`) | `mock_sleep.assert_called_once_with(5.0)` | count + value |
| 6 | `tests/sync/tracker/test_saas_client_origin.py:261` | `TestSearchIssues.test_429_retries_then_raises` (decorator `:229`) | `mock_sleep.assert_called_once_with(2.0)` | count + value |
| 7 | `…test_saas_client.py:804` | `test_timeout_after_5_minutes` | `mock_monotonic.side_effect = [0.0, 301.0]` | **stimulus, not an assertion** — the only assertion is the `pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes")` at `:806`, with the call at `:807`. Confirmed by opening `:800-812`. |
| 8 | `…test_saas_client.py:55-57` | `_advancing_clock` docstring (def `:32`) | *"there the second value **is** the assertion"* | the false claim; corrected under IC-02 |
| 9 | `…test_saas_client.py:532`, `:550` | inside `test_exponential_backoff_intervals`' docstring | quoted CI failure text | **not** live assertions — confirmed inside the span by opening `:513` and `:762` |

**The residue — in-class under the R-2 mechanism, outside R-1's seam, frozen at baseline.** Every
`file:line` opened this session. The `[new]` rows appear in **neither** `spec.md` nor
`analysis-report.md`:

| `file:line` | Assertion as it reads | Patch site & form | Shared module |
|---|---|---|---|
| `tests/sync/test_final_sync_diagnostics.py:309` | `assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]` | `:303` **context-manager** `patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append)` | `time` (`batch.py:11`) |
| `tests/sync/test_git_metadata.py:226` | `assert mock_run.call_count == 3` | `:209` decorator | `subprocess` (`git_metadata.py:13`) |
| `…test_git_metadata.py:249` | `assert mock_run.call_count == 5` | `:231` decorator | `subprocess` |
| `…test_git_metadata.py:281` | `assert mock_run.call_count == 3` | `:265` decorator | `subprocess` |
| `…test_git_metadata.py:398` **[new]** | `assert mock_run.call_args.kwargs.get("cwd") == tmp_path` | `:392` decorator | `subprocess` — reads `call_args`, i.e. the **last** call; a concurrent `subprocess.run` replaces it |
| `…test_git_metadata.py:471` | `assert mock_run.call_count == 2` | `:458` decorator | `subprocess` |
| `…test_git_metadata.py:530` | `assert mock_run.call_count == 5` | `:510` decorator | `subprocess` |
| `…test_git_metadata.py:218`, `:242`, `:274` | `mock_time.side_effect = [1.0, 2.0]` / `[1.0, 4.0]` / `[1.0, 2.99]` | `:208`, `:230`, `:264` decorators | `time.monotonic` — exact-list stimuli, `StopIteration` exposure |
| `…test_git_metadata.py:522` **[new]** | `side_effect=[1.0, 10.0]` feeding `:530` | `:522` **context-manager** `patch("specify_cli.sync.git_metadata.time.monotonic", side_effect=[1.0, 10.0])` | `time.monotonic` — the **fourth** clock coupling, invisible to a decorator-only census |
| `tests/sync/test_runtime.py:673` **[new]** | `mock_run_coroutine_threadsafe.assert_called_once_with(mock_connect_coro, runtime._async_loop)` | `:662` context-manager `patch("asyncio.run_coroutine_threadsafe")` — **bare stdlib target** | `asyncio` |
| `tests/sync/test_runtime.py:710` **[new]** | same form | `:700` context-manager, bare target | `asyncio` |
| `tests/sync/test_batch_sync.py:647`, `:741`, `:1080`, `:1122`, `:1330`, `:1362`, `:1407`, `:1485` **[new]** | `assert mock_post.call_count == {2,1,3,1,1,0,1,0}` | decorator/ctxmgr `patch("specify_cli.sync.batch.requests.post")` | `requests` (`batch.py:19`) |
| plus 1 further `mock_post`/`mock_get` count read across `test_batch_error_surfacing.py` / `test_batch_retry_hygiene.py` / `test_body_transport.py` / `test_batch_400_no_details_poison_2736.py` **[new]** | count/equality on the `requests` recorder | same | `requests` (`body_transport.py:17`) |

Measured: the `mock_post`/`mock_get` count-or-equality read count across those five files is **9**
(`grep -rn 'mock_post\.call_count\|mock_post\.assert_called\|mock_get\.call_count\|mock_get\.assert_called\|len(mock_post\.call_args_list)' … \| wc -l` → 9). All five files carry
`pytestmark = [pytest.mark.fast]` (verified per file), as do `test_runtime.py:14`,
`test_git_metadata.py:28`, `test_final_sync_diagnostics.py:27`, `test_saas_client.py:24` and
`test_saas_client_origin.py:22`. Every instance above is therefore inside CI's
`-m "fast and not windows_ci"` selection and in the same worker population as the census nodes.

**Structure decision.** Four real directories, chosen for one reason each rather than by convention:

- `src/specify_cli/tracker/saas_client.py` — the seam belongs in the module that owns the calls; that
  is what makes it module-**local**. Nothing else in `src/` changes.
- `scripts/` — `<census>` must be runnable as `python <census> tests/sync --json` (SC-001) and must
  share the resolution authority with the CI lint that already lives there. A `src/` home would drag
  it into the mypy-advisory and packaging surfaces for no benefit.
- `tests/architectural/` — the gate and the control fixture are architectural gates; 165 siblings and
  the ratchet meta-test already live there, and `_baselines.yaml` is the charter's declared home for
  the frozen allowlist.
- `tests/sync/tracker/` — `<guard>` must sit inside the `#3115 FR-007` leak-guard's scope (NFR-004
  requires it active over the changed modules) and inside the `fast-tests-sync` shard, next to the
  nodes it protects.

**One naming trap.** `spec.md`'s "Corrections to the incoming brief" item 3 says the `git_metadata`
clock coupling is `time.time`. It is **`time.monotonic`** — five sites, verified by AST and by
`grep -n 'patch(' tests/sync/test_git_metadata.py` (`:208`, `:230`, `:255`, `:264`, `:522`). Any WP
grepping for `time.time` in that file finds nothing and may conclude the instance is absent.

---

## Complexity Tracking

### Charter violations that must be justified

Each is templated: what is violated, why the mission needs it, and the simpler alternative with the
reason it was rejected.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| **`C-011` ATDD-First: the base-branch red is structural, not assertional.** Charter `:504-517` requires a failing-first test that "pins the user-observable behaviour the WP delivers", verified RED on `planning_base_branch` and GREEN on the final commit. `<guard>`'s arm (a) is RED on `98198e980` with an `AttributeError` raised by `unittest.mock.patch` at **setup** — `specify_cli.tracker.saas_client._sleep` provably does not exist at that SHA — which is a red about a missing attribute, not about the behaviour. | The behaviour-pinning red is arm (b): the literal pre-fix expression form evaluated against a deliberately polluted recorder, raising `AssertionError`. That arm is an **injection** and raises on *any* branch, so it is not base-branch red, as `spec.md` itself states. There is no third construction: the defect's user-observable symptom is a nondeterministic CI failure with a measured 39% clean rate pre-fix, so it cannot be pinned by a deterministic assertion on either branch. Both reds ship; the exception is that neither is simultaneously assertional **and** base-differentiating. | (i) *Assert the observable symptom directly* — rejected: a criterion that requires the nondeterministic failure to appear is satisfied 61% of the time and is exactly the "treat a run as evidence" error the spec's adversarial table forbids. (ii) *Land the alias first, then write the test* — rejected: that is the red-after-green order the charter exists to prevent, and the reviewer's red→green verification would have nothing to verify. (iii) *Make arm (b) refuse to import on base* — rejected: it would be red on base for the same structural reason as arm (a), duplicating the exception rather than removing it. |
| **Standing order 5 / SC-007 item 5: the gate's allowlist is NOT empty at merge.** The charter grants a *shrink-only* allowlist; `spec.md` SC-007 item 5 demands *empty at merge*. Measured, ≥ 22 in-class instances under `tests/sync/` lie outside R-1's seam (residue table above), across four further product modules (`sync/batch.py`, `sync/git_metadata.py`, `sync/body_transport.py`, plus the `asyncio` reach in `sync/runtime.py`'s test). | Enforced scope must stay `tests/sync/` per **R-2**, and the frozen baseline is the only construction that keeps the gate honest over that scope while the mission's hardening is bounded to the seam the operator ruled. It lands in `tests/architectural/_baselines.yaml` — the charter's declared canonical home — **and is registered in `test_ratchet_baselines.py` by IC-06's four edits, without which growth fails nothing** (BLOCKER-3: `:214` checks missing keys only, both comparisons run off hardcoded lists at `:274`/`:420`, and two of the twelve existing keys are already inert with the suite green). Once registered, growth **FAILS CI** and shrinkage warns. Every frozen entry carries a `file:line` + target + assertion-form triple so it cannot be widened by restatement, plus a per-row `owner:` / `disposition:` and an **owner-completion arm** copied from `test_no_inert_schema_slots.py:680`, so a row cannot outlive the work that was supposed to remove it. Standing order 2 and the `frozen-baseline-shrink-only-ratchet` tactic name this response explicitly. | (i) *Narrow the enforced scope to the files this mission hardens* — rejected: that is verbatim BLOCKER-2 ("`SC-001` can report `corruptible_assertions: 0` while the class is open in this mission's own window"), and it is the cheat the squad found in `SC-007`. (ii) *Harden all ≥ 29 instances in this mission* — rejected: it changes `C-004`'s permitted-hunk set and puts `requests.post` behaviour in scope; the operator ruled R-1's seam, not a five-module sweep. **R2's wording here said this "requires alias seams in four more product modules", which is false for `batch.py`** — that module already exposes `run_final_sync_with_retries(…, *, sleep=None)` (`:628-631`) and its row closes by threading one keyword argument at `background.py:467`. The rejection stands on scope, not on difficulty. (iii) *Ship the gate as advisory* — rejected: a non-gating gate is the vacuous gate standing order 5 forbids. |

### Ceiling-15 register — every function that gains branches

`max-complexity = 15` (`pyproject.toml:287`, aligned with Sonar `S3776`).
`ruff check --select C901 src/specify_cli/tracker/saas_client.py` → `All checks passed!` today, so both
touched production functions are already ≤ 15.

| Function (module-qualified) | Change | Branch delta | Register |
|---|---|---|---|
| `specify_cli.tracker.saas_client.SaaSTrackerClient._request_with_retry` | `:439` `time.sleep(` → `_sleep(` | **0** — name substitution, no branch | no action; `C901` re-run in the WP |
| `specify_cli.tracker.saas_client.SaaSTrackerClient._poll_operation` | `:481`, `:484`, `:515`, `:518` substituted | **0** | if `_poll_jitter_multiplier` is *promoted*, `:515-516` collapses to one call: delta **−1** |
| `specify_cli.tracker.saas_client._poll_jitter_multiplier` | deleted (recommended) | **−1 function** | removes a `C901` subject |
| `scripts/patch_seam_census.py` — the target classifier | new | **must be built ≤ 15** | it decides five outcomes (unresolvable / not-a-module / own-module / reach-through / foreign). Build it as a lookup-then-classify pair, not one nested `if`: one function resolves, one maps a resolved module to a verdict. |
| `scripts/patch_seam_census.py` — the read-side matcher | new | **must be built ≤ 15** | it must handle `assert_called*` methods, `.call_count`, `len(.call_args_list)`, `.call_args`, whole-list equality, **one level of alias** (`sleep_calls = mock.call_args_list` then `delays = [c.args[0] for c in sleep_calls]`), and `side_effect=` sinks. Extract per-form recognisers; do not grow one `visit_Compare`. |
| `scripts/patch_seam_census.py` — the CLI (`--json` / `--contract` / `--siblings`) | new | **must be built ≤ 15** | three front doors over one analysis pass; dispatch via a dict, not a chain. |
| `tests/architectural/test_shared_module_object_patches.py` — the two-sided seam arm | new | **must be built ≤ 15** | **four parts, so build it as four functions, not one** (R2 said "two functions"; arm 4 has grown): **4a** zero calls in `saas_client.py` whose callee *resolves* to `time.sleep` / `time.monotonic` / `secrets.randbelow`, resolved against the module's own `ast.Import`/`ast.ImportFrom` bindings — **no carve-out**; **4b** the three module-scope names are `ast.Assign` to those attributes, not `ast.FunctionDef` (refuses the wrapper); **4c** the **test-side** target strings — 0 pre-fix, `14`/`9`/`1` post-fix, from AST `patch()` nodes not `grep`; **4d** the positive twin, reporting the **3** alias definitions by name and the **5** rerouted call sites by line, so a checker that parses nothing fails loudly. Resolution helper shared with 4a; copy `test_protection_resolver_call_sites.py:90-109`. |

Every new branch and helper ships with a focused test in the same commit (Sonar expectation: new-code
coverage dominates the gate; extracting helpers without tests moves the failure rather than fixing it).

---

## Implementation Concern Map

> Implementation concerns are NOT work packages and are NOT executable units. `/spec-kitty.tasks`
> translates these into WPs — one concern may become several, several may merge into one.

Sequenced so **the alias lands before anything that depends on it**, and so **the gate cannot be
authored before the shape it must refuse exists**.

**Two structural changes against R2's map, both forced by the dependency gate rather than by preference:**

- **IC-05 is MERGED INTO IC-02.** R2 made IC-05's guard commit precede IC-02's alias commit *across a
  work-package boundary*, which **deadlocks** (BLOCKER-4, detailed under IC-02). Coupling E becomes an
  intra-WP commit order.
- **IC-09 is FOLDED INTO IC-08.** IC-09 owned no repository artifact, so it could carry no evidence and
  could not be reviewed.

**IDs are retained rather than renumbered**, matching this mission's own convention for FR-006 / FR-007 /
SC-006 / SC-011, so no successor reads a gap. Seven concerns remain live: IC-01, IC-02, IC-03, IC-04,
IC-06, IC-07, IC-08.

### IC-01 — Interpreter provisioning, the C-001 window, and the NFR-005 baseline

- **Purpose**: make every later command reproducible on CI's interpreter, **acquire and hold the C-001
  `tests/sync` window**, and capture the NFR-005 baseline in the same session as the comparison, so no
  WP discovers the environment at acceptance time.
- **Requirements**: NFR-005, SC-014, C-001, and the `### Environment` correction above.
- **Surfaces**: `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/environment-3136.md` (new — the
  interpreter transcript, **split out of `notes/constraint-enforcement-3136.md`**, which R2 gave one
  declared owner and three writers) and `notes/c001-window-3136.md` (new — the window handshake).
- **Depends on**: none.
- **The C-001 window is now an owned deliverable with a recorded handshake.** R2 left it owned by
  nothing while three concerns and two criteria require it — the single most likely place for the
  mission to stall, because a WP that cannot run `tests/sync` cannot take either NFR-005 arm and cannot
  green the guard. `notes/c001-window-3136.md` records, as an explicit acquire/release pair: who holds
  the window, the timestamp of acquisition, the sibling mission checked against, the arms taken inside
  it, and the release. **Dependency edge**: every concern needing the window (IC-02's guard arms,
  IC-08's transcripts) depends on IC-01, and the window is released only after the last of them. A WP
  that reports a `tests/sync` result with no corresponding acquisition record has not produced evidence.
- **Risks**: (a) `~/.local/bin/{pytest,ruff,mypy,spec-kitty}` are first on `PATH` and
  resolve to an unrelated checkout (all four verified) — **mitigation**: every command prepends
  `<repo>/.venv/bin` and the WP records `command -v python pytest ruff mypy` output before the first
  arm; a transcript without that line is not evidence. (b) **A bare `uv run` removes and recreates
  `.venv`** — observed twice (planning: 3.11.15 → 3.12.13 with dev tools dropped; post-plan: recreated
  at **3.11.15**, because a bare `uv run` honours `.python-version`) — **mitigation**: use only the two
  sanctioned forms in `## Technical Context`; re-provision with `uv sync --python 3.12 --extra test
  --extra lint`; re-verify `pytest --version` after any `uv` invocation whatsoever. (c)
  `.python-version` still reads `3.11.15` while the venv and CI are 3.12 — **mitigation**: do not
  "fix" it in this mission (out of C-004's permitted set); record the divergence, and note that it is
  what makes an accidental bare `uv run` downgrade rather than merely strip. (d) The NFR-005 baseline
  arm requires running `tests/sync/tracker/` on `98198e980` — **mitigation**: acquire the C-001 window
  first and take both arms back-to-back; a delta measured across two sessions or two interpreters is
  not a measurement.

### IC-02 — The guard (red first), the alias seam, the 24 retargets, the dead seam, and the false docstring

> **IC-05 is merged into this concern.** One work package, with the guard as its **first commit**.

- **Purpose**: make the mock's recorder structurally unreachable from another thread — seam **and**
  retargets, which are one deliverable — ship the red-first evidence as a live command rather than a
  transcript, and remove the rotted sibling seam in the same change so the new one does not join it.
- **Requirements**: FR-010 (conditions i–iv), **FR-012**, FR-001, FR-003, NFR-001, NFR-002, NFR-004,
  C-004, SC-004 (five rows), SC-005, SC-008, SC-009, SC-013 sub-3, SC-013 sub-4, SC-016, and the
  `### Charter red-on-base` arms.
- **Surfaces**: `src/specify_cli/tracker/saas_client.py` (three module-scope aliases **by assignment**;
  the five call-site substitutions at `:439`, `:481`, `:484`, `:515`, `:518`; `_poll_jitter_multiplier`
  at `:104-106` deleted or promoted); `tests/sync/tracker/test_saas_client.py` (**the `:55-57` docstring
  correction plus the 23 enumerated patch-target retargets**);
  `tests/sync/tracker/test_saas_client_origin.py` (**1 retarget at `:229`**);
  `tests/sync/tracker/test_sleep_attribution_guard_3136.py` (new — `<guard>`, `pytest.mark.fast`).
- **Depends on**: IC-01 (interpreter **and** the C-001 window).

#### Why IC-05 had to merge in — the deadlock (BLOCKER-4)

R2 made IC-05 a separate concern whose guard commit precedes IC-02's alias commit. **Across a
work-package boundary that cannot be built.** The charter's ATDD rule is **per work package**: RED on the
WP's `planning_base_branch` **and GREEN on the WP's final commit** (`charter.md:504-517`, verified —
"The reviewer verifies red→green: the test was RED on the WP's `planning_base_branch` AND GREEN on the
WP's final commit"). So:

1. WP(IC-05)'s final commit is red **by construction** — the alias it patches does not exist yet.
2. A red final commit cannot pass review → the WP cannot reach `approved`.
3. `dependency_readiness_for_wp` (`core/dependency_graph.py:50-77`) gates on
   `_SATISFYING_DEPENDENCY_LANES` (`:34`), which is `(Lane.APPROVED, Lane.DONE)` — verified.
4. Therefore WP(IC-02) could **never be claimed**. Dependencies here are **WP-level and lane-gated**,
   never commit-level, so R2's coupling E ("depends on IC-05's guard *commit*") is not expressible at
   all.

`finalize-tasks` would have passed this — no topological cycle exists — and the deadlock would have
surfaced at `implement`, with the mission unable to proceed and no obvious cause.

**Resolution**: one WP, guard first. `charter.md:509` prescribes exactly this shape ("committed as a
separate commit (often the first commit of the lane) **BEFORE** any implementation commits"). Coupling E
becomes an intra-WP commit order, which is where it was always expressible.

**The red window reddens TWO enforced gates, and both are expected.** (i) The sync shard, because
`patch("…saas_client._sleep")` cannot be set up on `98198e980`. (ii) **`scripts/check_patch_targets.py`,
`[ENFORCED]` at `ci-quality.yml:883-884` with no arguments** — so it scans every `patch()` target under
`tests/`, and all three alias targets fail resolution today. Verified via its own resolver:

```
_mock_importer("specify_cli.tracker.saas_client._sleep")     -> (None, "no attribute '_sleep' in 'specify_cli.tracker.saas_client'")
_mock_importer("specify_cli.tracker.saas_client._monotonic") -> (None, "no attribute '_monotonic' in …")
_mock_importer("specify_cli.tracker.saas_client._randbelow") -> (None, "no attribute '_randbelow' in …")
_mock_importer("specify_cli.tracker.saas_client.time.sleep") -> (<built-in function sleep>, None)   # control
```

R2 named neither this second red nor an owner for it. It is now named, owned by this concern, and is
**positive evidence**: a retarget that did not change the resolved object would not move this gate.
Because both reds must close inside one WP, this is a second independent reason the merge is mandatory.

#### The 24 retargets — the edit that *constitutes* the fix (FR-012)

Re-derived this session with
`grep -oE 'patch\("specify_cli\.tracker\.saas_client\.[^"]+"' <both files> | sort | uniq -c`, then every
line opened:

| File | Pre-fix target string | → Post-fix | N | Lines |
|---|---|---|---|---|
| `test_saas_client.py` | `…saas_client.time.sleep` | `…saas_client._sleep` | **13** live | `:385`, `:412`, `:467`, `:502`, `:789`, `:809`, `:899`, `:939`, `:959`, `:1087`, `:1128`, `:1152`, `:1319` |
| `test_saas_client.py` | `…saas_client.time.monotonic` | `…saas_client._monotonic` | **9** | `:386`, `:413`, `:468`, `:503`, `:790`, `:810`, `:1088`, `:1129`, `:1153` |
| `test_saas_client.py` | `…saas_client.secrets.randbelow` | `…saas_client._randbelow` | **1** | `:499` (string; `@patch(` spans `:498-501`) |
| `test_saas_client_origin.py` | `…saas_client.time.sleep` | `…saas_client._sleep` | **1** | `:229` |
| | | **live total** | **24** | |
| `test_saas_client.py` | same string **in prose** | update for consistency | **2** | `:559` and `:715`, both inside the `:513-762` docstring — **not** decorators |

`grep -c` reports `15` `time.sleep` in `test_saas_client.py`; `:559` **and `:715`** are the two docstring
occurrences, so **13 live**. *(An earlier revision recorded `14` / one docstring occurrence; the second
prose occurrence at `:715` is not matched by a `patch("`-anchored command, which is how it was missed.)* `13 + 9 + 1 = 23` live in `test_saas_client.py`, `+1` in `test_saas_client_origin.py` =
**24**. Docstring span `:513`–`:762` confirmed by opening both boundaries. Note R2's `plan.md:169` cited
the randbelow decorator as `:498`; the **target string** is on `:499` — the distinction matters to any
line-anchored check.

**The alias form is binding: assignment, never a wrapper — because the assignment form is
*self-enforcing*.** `_sleep = time.sleep` at module scope, not `def _sleep(s): time.sleep(s)`. Simulated
across all four states in a quiet process, asking what the *existing* `== 3` assertion sees:

| Alias form | Decorator target | Recorder sees | Verdict |
|---|---|---|---|
| assignment | `…_sleep` (retargeted) | `3` | **immune — the fix** |
| assignment | `…time.sleep` (un-retargeted) | **`0`** | **fails loudly** — cannot be shipped |
| wrapper | `…_sleep` (retargeted) | `3` | immune at runtime, but retains a live `time.sleep` lookup |
| wrapper | `…time.sleep` (un-retargeted) | **`3`** | **passes silently, defect 100% intact** |

Under assignment, **skipping the retargets is impossible to ship** — production calls the import-time
binding the mock never replaced, so the assertions see 0. Under the wrapper, **skipping them is
invisible**, because the wrapper preserves exactly the `time.sleep` reach-through the un-retargeted
decorator patches. That is what makes the wrapper the attractive cheat: it makes the 24-decorator edit
look optional. Refused by IC-06's arm **4b** (`ast.Assign`, not `ast.FunctionDef`) *and* arm **4c** (the
retargets pinned by count) — **both are needed**; 4b alone permits a correct-but-fragile wrapper tree, 4c
alone permits a wrapper tree that re-corrupts the moment one decorator is reverted. **Note for the WP**:
SC-005's two-mock construction catches every *incomplete-retarget* tree but **not** a fully-retargeted
wrapper, which is runtime-immune; the wrapper defense is static (4b) by necessity, not by preference.

The repo already documents this exact mechanism working in the opposite direction:
`psutil._psposix.wait_pid_posix` is invisible to `@patch("…time.sleep")` **because** it binds
`_sleep=time.sleep` at import (`spec.md` `### Established, reused, not re-derived`).

#### The acceptance arm on diff shape — because `owned_files` is file-granular

R2 restricted `test_saas_client.py` to "the docstring at `:55-57` **ONLY**", which forbids the very edit
that constitutes the fix. But the ownership mechanism cannot express "these lines only" — `owned_files`
is per-file. So the restriction is expressed as an **acceptance arm on the shape of the diff**, which a
reviewer can run:

```
./.venv/bin/python -m pytest <gate> -q          # arm 4c: target strings moved, counts 14/9/1
git diff 98198e980 -- tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py
```

Every changed line in those two files must be **either** (a) inside the `:55-57` docstring correction,
**or** (b) a line whose only change is a `patch()` target string moving from one of the three pre-fix
strings to its post-fix counterpart, **or** (c) the `:559` **and `:715`** docstring occurrences of the same string.
**Any other changed line fails the criterion** — in particular, no assertion expression may change, which
is what preserves R-1's actual guarantee. This is stronger than "docstring ONLY" and, unlike it,
satisfiable.

- **Risks**: (a) A partial reroute leaves a direct `time.sleep(` in the file, which turns the gate's
  arm 4 red rather than merely reducing coverage — **mitigation**: the arm is a whole-file AST
  assertion, so treat the five sites as one indivisible edit (see Atomicity, coupling A). (a2) **A
  partial *retarget* is the more likely failure and is silent** — a tree with the seam landed and some
  decorators still on `…time.sleep` has assertions reading a mixed population, green on the arms R2
  specified — **mitigation**: arm 4c pins the post-fix counts at `14 / 9 / 1` and the pre-fix counts at
  `0`, so a partial retarget fails on a number. (b)
  Promoting `_poll_jitter_multiplier` instead of deleting it changes what `test_saas_client.py:498`'s
  `@patch("…_randbelow")` must target and can break `:786`/`:787` — the two assertions R-1 exists to
  leave unchanged — **mitigation**: prefer deletion; if promoted, show `:786` and `:787` passing with
  **zero** diff to those lines. (c) The alias names are `_`-prefixed and could be read as private and
  removable by a future dead-symbol sweep — **mitigation**: the ADR (IC-03) plus the gate's arm 4 make
  them load-bearing by construction, and the ADR must say so in the words a sweep author would grep.
  (d) C-004's permitted-hunk set is enumerated by line number, and adding three module-scope
  definitions **shifts every later line** — **mitigation**: SC-016's reviewer must read the hunks
  semantically, and the WP must state the post-fix line numbers of the five call sites alongside the
  pre-fix ones (SC-007 item 4's positive twin already requires the post-fix lines). (e) `mypy
  --strict` on this file is advisory in CI and its `[[tool.mypy.overrides]]` sets `follow_imports =
  "skip"` for `specify_cli.*` — **mitigation**: run `mypy --strict` on the file explicitly and record
  it; do not rely on CI to catch a typing regression in the alias signatures.

### IC-03 — The ADR that adjudicates the idiom, plus the generated lockfile it forces

- **Purpose**: record the alias as a deliberate testability seam so the next reader treats it as a
  contract — which is the whole difference between this seam and `_poll_jitter_multiplier` — **and settle
  the precedence between the alias idiom and the call-site-injection idiom that already exists in this
  cone**, so the mission does not ship two seam styles with no rule for choosing.
- **Requirements**: FR-010 condition (i), **FR-011**, SC-013 sub-2, C-010.
- **Surfaces**: `docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md` (new), the index row
  in `docs/adr/3.x/README.md`, and **`docs/development/3-2-page-inventory.yaml`** (a generated lockfile —
  regenerated, never hand-edited).
- **Depends on**: IC-02 (the ADR describes the shape that landed, including which
  `_poll_jitter_multiplier` outcome was chosen).

#### The ADR must state a rule, not describe an instance (FR-011)

An ADR that records only "`saas_client.py` gets three aliases" leaves the next author with two working
idioms and no precedence, which is the "single canonical authority" failure the charter's Standing order 6
exists to prevent — introduced by the document meant to establish canonicity. Binding content:

- **The rule**: *where a module already exposes a call-site injection point, thread it; introduce a
  module-local alias only where the stdlib call has no threadable caller.*
- **Both worked examples**, with evidence: `saas_client.py` earns an alias (calls internal to
  `_request_with_retry` / `_poll_operation`, no injectable caller); `batch.py` does **not** — it already
  has `run_final_sync_with_retries(…, *, sleep=None)` at `:628-631`, `sleeper = time.sleep if sleep is
  None else sleep` at `:641`, threaded through `:648`–`:700`, and three tests already using it
  (`test_final_sync_diagnostics.py:180`, `:207`, `:239`). Its one reach-through row exists solely because
  `background.py:467` does not thread it.
- **Relate to `docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md`** (verified
  present), which already decided seam + AST call-site gate + curated allowlist **against** full DI. This
  mission is a second application of that decision; the ADR must say so rather than re-deciding it.
- **State that the three `_`-prefixed names are load-bearing**, in the words a dead-symbol sweep author
  would grep, and cite the gate's node-id so a reader who believes the ADR can run it.

#### The generated lockfile — BLOCKER-5, and it reds every PR

`scripts/docs/freshen_adr_inventory.py` writes **two** index updates that `docs-freshness` enforces: a
row in `docs/development/3-2-page-inventory.yaml` and a table row in the era `README.md`. Its own
docstring calls the former *"a **generated lockfile**, regenerated from every page's frontmatter"*
(verified; the file exists, 111 KB). And the job is unconditional:

| Fact | Evidence |
|---|---|
| `docs-freshness.yml` runs on **every** PR, **no path filter** | `:2-4` — `on: pull_request` (there is a label escape at `:10` for `pr:deferred` / `pr:skip-ci`, which is not a path filter and must not be used to dodge this) |
| It runs `check_docs_freshness.py --ci` | `:53-58` |
| `INVENTORY-LOCKFILE-DRIFT` is **error**-severity, blocking, default-on | `check_docs_freshness.py:743-752` — `severity="error"`; `:12-15` and `:328-333` record it as blocking since Mission B, with the opt-in guard deliberately removed |
| It runs on Python **3.11**, not 3.12 | `docs-freshness.yml:17` — `uv python install 3.11` |

So **a new ADR without its regenerated lockfile row reds a blocking job on this mission's PR**, and R2
owned neither the file nor the command. The regen command (single source of truth for both updates):

```
./.venv/bin/python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md
```

Then commit the resulting `docs/development/3-2-page-inventory.yaml` **and** `docs/adr/3.x/README.md`
diffs. **Never hand-edit the lockfile** — it is regenerated from frontmatter, so a hand-edit drifts on the
next run.

#### The ADR frontmatter contract

Because the lockfile is generated *from frontmatter*, the frontmatter is the real input and a missing
field fails the gate rather than the file. Template: **`docs/architecture/adr-template.md`** (verified
present). Required, and each checked by its own sub-check:

| Requirement | Checked by |
|---|---|
| `title` in frontmatter | inventory generation (a missing title yields no row) |
| `date` in frontmatter | same, plus the era `README.md` row format `\| YYYY-MM-DD \| [Title](file.md) \|` |
| description length | `description_length_check --strict` |
| related-links validity | `related_validator --strict` |
| relative links resolve | `relative_link_fixer --check` |

- **Risks**: (a) The ADR is prose and prose has propagated as a load-bearing constraint three times in
  this programme — **mitigation**: state the mechanism as the executable predicate the gate
  implements, and cite the gate's node-id, so a reader who believes the ADR can run it. **The rule of
  FR-011 must likewise be stated as a rule with two worked examples, not as a description of what
  landed.** (b) The lockfile regen is forgotten, or hand-edited — **mitigation**: it is an owned surface
  with a named command; the WP shows the `git diff --stat` for both generated files. (c)
  Touching `docs/` triggers C-010's terminology guard, which runs only in CI's
  `integration-tests-core-misc` job — **mitigation**: IC-08 owns that command; it must run before push,
  not at acceptance. (d) **The docs job runs on 3.11 while every other command in this mission is
  pinned to 3.12** — **mitigation**: recorded here so a WP does not "fix" a 3.11-only result by forcing
  3.12, and does not conclude its 3.12-local pass transfers; run the docs checks the way the job does.
  (e) IC-07 also touches `docs/` — **mitigation**: IC-07 is **body-only** (a verdict-column stamp) and
  touches no frontmatter, so it cannot change the lockfile; that is what keeps the two lanes
  non-conflicting (see the WP graph).

### IC-04 — The census analyzer and its control fixture

- **Purpose**: build one AST instrument that derives the class from the mechanism, and make it
  trustworthy — it is the sole instrument for SC-001, SC-002 and SC-013, so nothing else forces it to
  be honest.
- **Requirements**: FR-001, FR-002, FR-005, NFR-007, SC-001, SC-002, SC-013 sub-1, SC-015.
- **Surfaces**: `scripts/patch_seam_census.py` (new — `<census>`),
  `scripts/check_patch_targets.py` (export `_mock_importer` as a public helper; **no behaviour
  change**), `tests/architectural/test_patch_seam_census_control.py` (new — `<census-control>`,
  `pytestmark = [pytest.mark.architectural]`),
  **`tests/architectural/_fixtures/patch_seam_control/`** (new — the fixture modules).
- **Three surface corrections against R2**: (i) the directory is **`_fixtures/`**, which already exists —
  R2 wrote `fixtures/`, which does not (verified: `ls -d tests/architectural/_fixtures` succeeds,
  `.../fixtures` fails), so the fixture would have landed in a new sibling directory that no convention
  covers; (ii) the fixture modules must have **non-`test_` names** so pytest does not collect them as
  tests — they are *input* to the analyzer, and a collected fixture module containing deliberately
  corruptible assertions would both fail and pollute the gate-coverage baseline; (iii) importing
  `scripts.check_patch_targets` from a test needs the `sys.path` insertion shape at
  `test_docs_cli_reference_parity.py:52-56`.
- **Depends on**: IC-01. **Not** IC-02 — the analyzer is written against the pre-fix tree so its
  pre-fix numbers are measurable, which is what makes the post-fix delta meaningful.
- **Risks**: (a) **The predicate as worded in R-2 flags 649 of 664 sites (97.7%), including 356
  ordinary own-module patches** — an analyzer built to the letter is unshippable, and the natural
  reaction is to hardcode an exclusion list, which is the vacuity the gate exists to prevent —
  **mitigation**: implement the discriminator as *resolved module `__name__` ≠ dotted module path*
  (reach-through) *or* resolved module not first-party (direct foreign), and pin the three bucket
  counts (356 / 286 / 7) as an in-test control so a regression toward the literal predicate shows up as
  a number, not as a flood. (b) **`spec.md` SC-001 pins `files_scanned: 22` while declaring the scan
  scope `tests/sync/`** — measured, `tests/sync/tracker/*.py` is 22 and `tests/sync/**/*.py` is 141, so
  the criterion as written is unsatisfiable by a `tests/sync/` scan — **mitigation**: report
  `files_scanned` per scope (`tests/sync/` = 141) and keep `22` as an explicitly labelled
  tracker-subtree sub-denominator; flag the criterion for operator ratification rather than picking a
  number silently. (c) Two extractors over one tree — the new AST one and `check_patch_targets.py`'s
  regex — can disagree and the disagreement is invisible — **mitigation**: a cross-check arm asserting
  the AST site set over `tests/sync/` is a **superset** of the regex script's, with the difference
  printed; a non-empty difference in the other direction fails. (d) The one-level alias resolution is
  load-bearing and easy to under-build: a probe without it misses `:784` and `:786` entirely (measured
  — my own read-side probe missed both for exactly this reason, and missed `:309` for want of
  `side_effect=` sink tracking) — **mitigation**: the control fixture pins both forms as positive
  cases, and the census self-mutation arm narrows the analyzer to today's five forms and requires the
  fixture to fail. (e) `n=` derived from the printed delay list's length rather than from the
  assertion's own cardinality expression makes `assert 3.0 in [...]` print `n=1 delays=[3.0]` honestly
  while asserting no cardinality — **mitigation**: SC-002's wording is binding; the `n=` extractor must
  read the cardinality expression, and the control fixture must contain the `in`-form as a **negative**
  case that reports `n=0`.

### IC-05 — MERGED INTO IC-02. Retained, not renumbered, so no successor reads a gap.

**Why**: R2 placed IC-05's guard commit before IC-02's alias commit **across a work-package boundary**,
which deadlocks the dependency gate — WP(IC-05)'s final commit is red by construction, a red WP cannot
reach `approved`, and `_SATISFYING_DEPENDENCY_LANES` is `(APPROVED, DONE)`, so WP(IC-02) could never be
claimed. Full derivation with citations under **IC-02 → "Why IC-05 had to merge in"**. The guard is now
IC-02's **first commit**, which is the shape `charter.md:509` prescribes, and coupling E becomes an
intra-WP commit order.

The risk register below is retained in full because every entry still binds — it simply binds IC-02 now.

- **Risks**: (a) **SC-005 as written was unsatisfiable under R-1 with a single probe, and R2's two-probe
  replacement was a tautology.** The original required ≥ 100 calls "on the same mock object the hardened
  assertion reads" — post-R-1 the hardened assertion reads the `_sleep` recorder and a thread calling
  `time.sleep` **structurally cannot** reach it. That is the fix working. R2 answered with Probe A
  (`stdlib_probe_calls ≥ 100` **and** `alias_recorder_calls_from_probe == 0`) and Probe B. **Both halves
  of Probe A are defective**: `alias_recorder_calls == 0` is **unfalsifiable** post-fix — green on a tree
  where the fix is 5% done, green where no decorator moved, green where the probe body is `pass` — and
  `stdlib_probe_calls ≥ 100` is a counter **the probe increments about itself**, so a body of
  `counter += 1` satisfies it without sleeping. **Mitigation — the binding construction is two mocks in
  one window** (`spec.md` SC-005, restated): inside a single patch window patch **both** stdlib
  `time.sleep` **and** `…saas_client._sleep`, then assert `stdlib_mock.call_count >= 100` **and**
  `alias_mock.call_count == <expected>` (3/1/1/1 per SC-004's five rows). Both numbers are read off
  **recorders**, not self-reports; they must disagree by exactly the injected volume. This fails a
  vacuous probe (first assertion) and **every incomplete-retarget tree** (second — the un-retargeted
  decorator patches the shared `time` module, so the probe's foreign calls land on the recorder the
  assertion reads). **Stated honestly, it does *not* fail a fully-retargeted wrapper alias**, which is
  runtime-immune and passes; that state is refused statically by arm 4b, and the two are not
  interchangeable. It also proves the property nothing else asserts: that
  `_sleep` is bound **at import**, since only an import-time binding makes the two counts differ.
  **No operator ratification is needed** — unlike R2's version this does not weaken SC-005's floor or
  change what it measures; it makes the same claim falsifiable. (b) A spawn race makes the
  probe miss — the predecessor's first attempt missed because the thread had not entered its wait loop
  when the sub-millisecond test body ran — **mitigation**: gate the body on a `threading.Event` the
  probe sets *after* its first recorded call; NFR-002's 10-of-10 requirement is the check that the gate
  worked. (c) The guard's own threads leak and get pinned — **mitigation**: join every probe in a
  `finally`; SC-008's two checks (the corrected `^\+\s*_PinnedLeak\(` diff grep **and** the AST count
  pinned at **12**) are the evidence, and the WP must reconcile that measured 12 against C-003's "11
  confirmed leaks" by naming which reading is wrong. (d) SC-008's positive twin greps the serial-only
  string `[FR-007 leak guard] inspected <N> test(s) under tests/sync/.` (`conftest.py:494`); under
  xdist the controller prints a different line (`:483-492`) and a real `-n 4` run over 2122 tests
  printed `inspected 0 test(s)` (documented at `conftest.py:464-475`) — **mitigation**: the command
  pins `-n0`; do not "fix" the resulting false red. (e) Arm (b) must be the **literal** pre-fix
  expression, diffable against `98198e980`, not a paraphrase — the cheat the squad named —
  **mitigation**: all five rows tabulated in SC-004 with their exact text, and the guard prints the
  five row identifiers so a reviewer can count them; row 2 (`assert delays == [0.9, 2.0, 4.4]`) is the
  one R1 omitted and the one most likely to be cosmetically hardened.

### IC-06 — The mechanism gate, its two-sided seam arm, and the frozen baseline *made non-inert*

- **Purpose**: close the class by construction with a gate keyed on the mechanism, stop the seam
  from silently evaporating, and **register the baseline in the ratchet that is supposed to govern it** —
  without which the baseline is decoration.
- **Requirements**: FR-005, FR-010 condition (ii), **FR-012** (arm 4c), SC-007 (all five items), and the
  frozen-baseline exception.
- **Surfaces**: `tests/architectural/test_shared_module_object_patches.py` (new — `<gate>`,
  `pytestmark = [pytest.mark.architectural]`), one new top-level key in
  `tests/architectural/_baselines.yaml`, and **`tests/architectural/test_ratchet_baselines.py`**
  (three enumerated edits plus one new arm).
- **Depends on**: **IC-02** (arm 4 asserts the post-fix routing **and the post-fix test-side target
  strings** — it cannot be authored before the shape it must refuse and the shape it must confirm both
  exist) and **IC-04** (it consumes the analyzer; a second implementation here would be the duplicate
  authority the charter forbids).

#### The ratchet is inert, and a new key joins two that already are (BLOCKER-3)

R2's Charter row 17 graded this `Pass` on *"growth FAILS CI"*, and its coupling D claimed the meta-test
catches an orphan key. **Both are false**, and `test_ratchet_baselines.py` appeared in no IC's surfaces.
Measured this session:

| Fact | Value | Evidence |
|---|---|---|
| top-level keys in `_baselines.yaml` | **12** | `yaml.safe_load` |
| keys in `_REQUIRED_TOP_LEVEL_KEYS` | **11** | `test_ratchet_baselines.py:123-136`, a **hand-written** `frozenset` |
| keys read by **any** comparison (`data["…"]`) | **10** | `grep -oE 'data\["[a-z_0-9]+"\]'` |
| in YAML but read by nothing | **2** — `test_all_declarations_required`, `test_no_dead_symbols` | set difference |
| in the **required** set yet read by nothing | **1** — `test_all_declarations_required` | so `missing` passes while no comparison exists |
| in YAML but **not** required and not read | **1** — `test_no_dead_symbols` | the extra-key case nothing catches |
| the suite is green with both inert | `3 passed in 60.47s` | recorded by the squad |

Three structural causes, each with its own edit:

1. **`_REQUIRED_TOP_LEVEL_KEYS` is hand-written** (`:123-136`), so a key exists in the ratchet's mind only
   if an author remembers to add it.
2. **`:214` checks only for *missing* keys** — `missing = _REQUIRED_TOP_LEVEL_KEYS - set(data.keys())` —
   and **never for extra** ones. `test_no_dead_symbols` has been unnoticed in the YAML for exactly this
   reason.
3. **Both comparisons run off hardcoded literal lists** — `single_baselines: list[tuple[...]]` at `:274`
   (growth) and `:420` (shrinkage). A key absent from both lists is read by nothing, so its "growth"
   fails nothing.

**The four required edits, enumerated:**

- **(1)** Add the new gate's key to `_REQUIRED_TOP_LEVEL_KEYS` (`:123-136`).
- **(2)** Add it to the **growth** `single_baselines` list (`:274`).
- **(3)** Add it to the **shrinkage** `single_baselines` list (`:420`). *(R2's plan named neither list;
  the directive's "both `single_baselines` lists" is why this is two edits, not one.)*
- **(4)** Add a **reverse-containment arm**: `set(data) - _REQUIRED_TOP_LEVEL_KEYS == ∅`, so the next
  unregistered key fails immediately instead of sitting inert. **This arm is red on the tree today**
  because of `test_no_dead_symbols`, which is itself the proof that the arm is non-vacuous. Two honest
  dispositions, and the WP must pick one explicitly rather than deleting the arm: either register
  `test_no_dead_symbols` in the comparison lists, or remove it from the YAML — **not** add it to
  `_REQUIRED` alone, which would reproduce `test_all_declarations_required`'s defect (required, never
  read). `[UNVERIFIED]` which disposition is correct — it needs the owner of whatever gate that key was
  meant to govern, and is out of this mission's scope to decide unilaterally; if it cannot be resolved,
  scope the arm to keys added from this mission forward and file the pre-existing pair.

**The honest-ratchet precedent to copy, which R2 cited nowhere while Charter row 10 claimed `Pass` on
canonical sources**: `tests/architectural/_inert_slots_baseline.yaml` +
`tests/architectural/test_no_inert_schema_slots.py` (both verified present). Its shape, and every element
is worth copying:

- A **permanently-empty allowlist pinned by its own arm** — `ALLOWLIST` stays `frozenset()`, pinned by
  `test_allowlist_is_empty` (`:989`). The baseline is the mutable surface; the allowlist never grows.
- **Per-row `owner:` and `disposition:`**, with `disposition` restricted to exactly three values and
  deliberately **no** `accepted` / `wont-fix` / `by-design` — so a row cannot be excused, only fixed,
  deleted, or reclassified as a lint defect.
- An **owner-completion arm** — `test_a_baseline_entry_does_not_survive_its_owner` (`:680`) fails the
  moment the named owner completes with the entry still present. This is what stops a frozen baseline
  becoming permanent, and it is strictly stronger than IC-08's tracker issues.
- An **owner-resolution arm** — `test_every_named_owner_resolves` (`:871`), because `WP42` or
  `mission:typo` reads as "never complete" exactly like `unassigned`.
- **Ratchet-registration arms** — `test_the_baseline_size_is_registered_with_the_charter_ratchet`
  (`:971`) and two siblings (`:928`, `:948`). **This is precisely the arm whose absence is BLOCKER-3**:
  the precedent already knows a baseline must assert its own registration, and R2 did not carry it over.
- Its header states the ratchet semantics and cites the charter's Burn-down Policy §a **and the
  `frozen-baseline-shrink-only-ratchet` tactic by name** — which this mission's baseline entry must also
  cite, and R2 did not.

The new baseline entry adopts all of it: per-row `owner:` / `disposition:`, an owner-completion arm, an
explicit registration arm, and a `# justification:` comment per `_baselines.yaml:12-18`.
- **Risks**: (a) **Two registries for "process-global symbol" in one cone.** `tests/sync/_leak_guard.py`
  already carries `_WatchedGlobal(inventory_id, module_path, attr_path, description)` with
  `_WATCHED_GLOBALS` at `:101` (17 `_WatchedGlobal(` elements measured), and `conftest.py:495-499`
  already prints `watched <N> process-global symbol(s)`. **Judgment: do not extend it, and do not
  create a parallel registry either.** They own different things — `_leak_guard` snapshots a global's
  *value* across a test node and reports **teardown residue**; the gate is a **static** analyzer over
  test *source* that never runs a test. `time.sleep` is correctly absent from `_WATCHED_GLOBALS`
  because it is restored by `patch`'s own teardown. Putting a static AST gate inside a runtime pytest
  hook module consumed by `conftest.py` would couple a lint to the sync suite's import graph. The
  reconciliation is at the **vocabulary** level: the gate's baseline entries reuse the same
  `(module_path, attr_path, description)` triple shape plus the inventory's row-id column where one
  exists, and the gate's docstring names `_leak_guard.py` as the runtime half of one concept with two
  enforcement points. That is one authority for the vocabulary and two for enforcement — which is what
  the charter's reconcile-don't-duplicate rule asks for, unlike two registries of the same kind.
  **Mitigation for the residual**: the gate's docstring must state the split in one sentence, or the
  next author adds `time.sleep` to `_WATCHED_GLOBALS` and gets a guard that cannot fire.
  (b) The gate's glob points at `tests/**`, reports a count floor, and never opens
  `tests/sync/tracker/` — the squad's named cheat — **mitigation**: SC-007 item 1 requires **named**
  files (four named explicitly), item 2 the `13 + 1 = 14` split and the four node-ids verbatim; a count
  floor is insufficient by construction. (c) Arm 4's negative ("**0** direct calls") is satisfied by a
  checker that parses the wrong file or nothing at all — **mitigation**: the positive twin (arm 4d)
  reports the **3** alias definitions by name and the **5** rerouted call sites by line.
  **(c2) Arm 4's carve-out admitted the wrapper cheat, and the arm was product-side only.** R2 worded it
  "0 direct `time.sleep(` … calls **outside the three alias definitions**" — under the wrapper form the
  only `time.sleep(` **is** inside the alias definition, so the carve-out excluded it and the arm passed
  with the defect intact. It was also alias-evadable (`import time as t; t.sleep(x)`,
  `from time import sleep`, `getattr(time, "sleep")(x)` all leave the negative true). And being
  product-side only, it passed on a tree where **not one decorator moved** — BLOCKER-1.
  **Mitigation — arm 4 is now four parts** (`spec.md` SC-007 item 4): **4a** the carve-out is struck and
  the check resolves the module's own `ast.Import` / `ast.ImportFrom` bindings (including `asname`),
  asserting zero calls whose callee *resolves* to the three attributes — shape copied from
  `tests/architectural/test_protection_resolver_call_sites.py:90-109`; **4b** each of the three
  module-scope names is an `ast.Assign` resolving to the stdlib attribute, **not** an `ast.FunctionDef`,
  which refuses the wrapper directly; **4c** the **test-side** target strings, `0` pre-fix and
  `14 / 9 / 1` post-fix, counted from AST `patch()` nodes (**never `grep`** — `test_saas_client.py:559` and `:715`
  carry the pre-fix string inside a docstring, and a grep-based arm would demand a prose edit to
  satisfy a numeric gate); **4d** the positive twin. (d) The
  frozen baseline is written as a count and then grows by restatement — **mitigation**: every entry is
  a `file:line` + patch target + assertion-form triple, and the `_baselines.yaml` per-PR policy
  (`:12-18`) requires a `# justification:` comment on any growing line. **Note the correction**: R2 added
  "`test_ratchet_baselines.py` fails CI on growth", which is **false for an unregistered key** — see
  BLOCKER-3 above. It fails CI on growth **only after** the four enumerated edits land. (e) A future
  author adds a *new* in-class assertion and grows the baseline
  instead of fixing it — **mitigation**: shrink-only is enforced by the ratchet **once registered**, and
  every residue row carries a per-row `owner:` plus an **owner-completion arm** copied from
  `test_no_inert_schema_slots.py:680`, so the entry fails the moment its owner completes with the row
  still present. The tracker issues (IC-08) are the human half; the arm is the machine half, and R2 had
  only the human half. (f) **Prefer frozenset-equality over `len(x) == N`** anywhere the gate or the
  ratchet pins a collection — a length check is a golden-count ratchet that passes when one member is
  swapped for another, and it forces a mechanical edit on every legitimate change without ever naming
  what changed. Assert the **set**, so the failure message names the delta.

### IC-07 — Inventory verdict stamp and the recorded non-goal

- **Purpose**: stop a falsified verdict column being inherited layer by layer, which is the failure
  mode that produced this programme.
- **Requirements**: FR-008, FR-009, C-005, C-007, SC-010 (four commands), SC-011 (authoring
  self-check).
- **Surfaces**: `docs/development/process-global-inventory-3115.md` (verdict-column stamp — **body only,
  no frontmatter**) and
  `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md` (new — `<guard-rationale>`).
- **Depends on**: IC-01 only (parallel with IC-02 through IC-06).
- **Body-only is now a stated constraint, not an incidental property.** IC-03 regenerates
  `docs/development/3-2-page-inventory.yaml` **from every page's frontmatter**, and this concern edits a
  page under `docs/`. If IC-07 touched frontmatter, the two concerns would race on a generated lockfile
  across lane boundaries. A verdict-column stamp is body-only by nature, which is what makes the two docs
  lanes non-conflicting — see the WP graph. **If a stamp turns out to need a frontmatter field, IC-07
  gains a dependency on IC-03 and loses its parallelism**; it does not silently edit frontmatter.
- **Risks**: (a) The verdicts were derived against `test_429_respects_retry_after`, and the PR #3209
  shard (head `5e98c2bb7`) shows that node **failing** — so they are falsified, not merely unverified,
  and a stamp reading "unverified" understates it — **mitigation**: the stamp must name the
  falsification and the node, per SC-010 sub-2; measured today, the doc has **0** occurrences of
  `unverified` and **0** of `3136`. (b) SC-010 sub-3 requires **zero** row-id tokens in `plan.md` and
  in `<guard-rationale>` — **mitigation**: this plan contains none, deliberately, and refers to the
  column by description; the WP must re-run the grep on the final `plan.md` **and** on
  `notes/non-goals-3136.md`, as two single-value commands (`grep -cE … file1 file2` prints one count
  per file and has no single value to compare). (c) The negative is satisfied by a grep that matches
  nothing — **mitigation**: SC-010 sub-4's positive twin, the identical pattern against the inventory
  itself, must return **53** (measured this session). (d) `_leak_guard.py`'s `_WatchedGlobal` entries
  carry the inventory's row-id column as their `inventory_id` field, so the inventory is **live input**
  to a running guard, not dead documentation — **mitigation**: the stamp must not invalidate rows the
  leak guard consumes; scope the stamp to the *verdict* column and say so, and name the depended-on row
  set as empty with reasoning if it is empty.

### IC-08 — Constraint enforcement, the retired-SC-006 observation, the draft PR, and the carried gaps

> **IC-09 is folded into this concern.** It owned no repository artifact, so it could carry no evidence
> and could not be reviewed.

- **Purpose**: give the four unenforced constraints a command each, give the "CI red is gone"
  claim an explicit owner, **own the draft PR**, and file the gaps this mission's instruments do not
  cover so the next reader inherits a filed gap rather than a silent one.
- **Requirements**: C-002, C-004, C-008, C-010, SC-016, SC-006's replacement observation, **FR-005's
  stated boundary, C-003, the charter's Pre-existing Failure Reporting Rule, and the adversarial table's
  `[R2-open]` row** (the four inherited from IC-09).
- **Surfaces**: `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/constraint-enforcement-3136.md`
  (new — the `<wp-notes>` C-002 greps; **now with exactly one writer**, IC-01's transcript having moved to
  `notes/environment-3136.md`), `notes/ci-observation-3136.md` (new), the **draft PR** itself, and tracker
  issues.
- **Depends on**: IC-02, IC-03, IC-04, IC-06 (it reports on what they landed, and the filed gaps are
  defined relative to what the shipped predicate covers).
- **The draft PR now has an owner.** R2 left it unowned while IC-08's CI observation is *defined in terms
  of its head SHA* — an observation about an artifact nobody was responsible for creating. This concern
  opens the draft PR (charter: draft-PR-first, the operator merges), records its number and head SHA in
  `notes/ci-observation-3136.md`, and is the only concern that may mark it ready for review. It never
  merges.
- **Risks**: (a) **`SC-006`'s retirement split one claim into two and only one is measured.** "The
  assertion class can no longer be corrupted" is measured by SC-001/004/005/007. **"The CI red is
  gone" is measured by nothing** — and it cannot be, because a clean full shard is the pre-fix outcome
  ~39% of the time, so no repetition count on any other machine transfers from CI's 4-vCPU topology.
  **Owner: this concern, as a non-gating observation, and the plan states plainly that the second
  claim is out of scope with the reason.** The observation records the mission PR's `fast-tests-sync`
  outcome, its head SHA, and the pre-fix rate `11/18` alongside it, labelled *non-discriminating*. It
  must never be cited as a pass. **Mitigation for the real risk** — that a reviewer or a successor
  reads a green shard as the mission's proof: the note's first line must say it is not evidence, and
  the WP must not list it among the acceptance arms. (b) C-008's `git diff … → no output` is also
  silent for a bad ref or a wrong working directory — **mitigation**: SC-016's positive twin requires
  a **loud** `git diff --stat 98198e980 -- src/specify_cli/tracker/saas_client.py` from the same
  invocation. (c) C-002's `grep -rc 'ruff format' <wp-notes>` = 0 is satisfied by writing no notes at
  all — **mitigation**: the same file is where IC-01's `command -v` transcript and IC-08's SC-016
  transcripts live, so it is non-empty by construction and its absence fails other criteria first.
  (d) C-010's terminology guard runs only in CI's `integration-tests-core-misc` job, so a
  forbidden-term regression in the ADR passes every local doctrine run — **mitigation**: run it before
  push, not at acceptance; `EXIT=0` recorded.

### IC-09 — FOLDED INTO IC-08. Retained, not renumbered, so no successor reads a gap.

**Why**: it owned **no repository artifact** — tracker issues only — so it could carry no evidence, could
not be reviewed, and could not satisfy the charter's reviewer≠implementer discipline in any observable
way. Its requirements, surfaces and risk register move to IC-08, whose `<wp-notes>` file is where its
filings were already going to be referenced from. Folding also removes the third writer from
`notes/constraint-enforcement-3136.md`.

**One filing text is corrected in the move** (see `### The competing idiom` above): R2's ticket text said
the residue "requires alias seams in four more product modules". That is **false for `batch.py`**, whose
row is closable by threading `sleep=` at `background.py:467` into the parameter `batch.py:628-631` already
exposes. The filing must say "thread the existing parameter", or a successor adds a redundant second seam
to a module that already has one.

The risk register below is retained in full because every entry still binds — it binds IC-08 now.

- **Risks**: (a) **Seam displacement is now closed by nothing.** The predecessor's
  `grep -rn 'sleep\.side_effect\s*=' tests/sync/` → 0 hits was closing a *different* hazard from the
  one R-2 closes: a test reassigning `mock.side_effect` **in-body**, displacing a recorder while
  `call_count` keeps incrementing. R-2's predicate reads the `patch()` call's **arguments**, so in-body
  reassignment is outside it — and the grep is retired as evidence because it matches attribute
  assignment only. **Owner: file it**, with the pattern, the reason the grep was inert, and the reason
  the new predicate does not reach it. Building it into the gate is rejected here: it needs
  intra-function dataflow, which is a different analysis from target resolution and would push the
  read-side matcher past the complexity ceiling. **Mitigation**: the filed issue must carry a
  reproduction shape, or it will be re-derived as "already closed by R-2". (b) The `[R2-open]`
  residual — a direct `time.sleep` added to a *different* module in the same cone is not covered by
  arm 4, whose scope is `saas_client.py` — **owner: filed**, with widening the seam check to all of
  `src/specify_cli/` named as the follow-up. (c) The ≥ 22 frozen residue rows have no burn-down owner
  unless ticketed, and an unowned frozen baseline becomes permanent — **owner: one issue per product
  module** (`sync/batch.py`, `sync/git_metadata.py`, `sync/body_transport.py`, and the `asyncio` reach
  under `test_runtime.py`), each naming its `file:line` set and the seam shape that would close it.
  **The `sync/batch.py` issue must name the correct shape**: thread `sleep=` at `background.py:467` into
  the parameter `batch.py:628-631` **already** exposes — *not* add an alias seam. R2's text said the
  residue "requires alias seams in four more product modules", which is false for this module and would
  produce a redundant second seam. Per FR-011 an alias is introduced only where no threadable caller
  exists; `batch.py` has one, and three tests in the frozen file already use it
  (`test_final_sync_diagnostics.py:180`, `:207`, `:239`). **The per-row `owner:` plus the
  owner-completion arm (IC-06) is the machine half of this mitigation**; the tracker issue is the human
  half, and R2 had only the human half.
  (d) The exact-list clock stimuli (`test_git_metadata.py:218`, `:242`, `:274`, `:522`;
  `test_saas_client.py:804`) are a **`StopIteration`** exposure, not a count or equality assertion, so
  R-2's predicate — which requires "the resulting mock is then read by a count or equality assertion" —
  **does not reach them**. `:804` closes incidentally under R-1 because `_monotonic` is module-local;
  the four in `test_git_metadata.py` do not. **Owner: filed** as a named sub-class of the mechanism
  with its own read-side form, so a successor does not read `corruptible_assertions: 0` as covering it.

### Atomicity couplings — five are same-**work-package**, one is same-**commit**

Named tests are given by node-id; every cited line was opened this session.

**Relabelled, and the distinction is not cosmetic.** R2 asserted **commit** atomicity for six couplings.
For five of them that is unenforceable and therefore misleading: **every named instrument evaluates the
working tree at CI time**, not a commit boundary. A gate cannot observe that two edits arrived in one
commit; it observes only the tree it is handed. Worse, coupling A's instrument is a file **IC-06 authors
*after* IC-02 commits** — so at the moment A's commit lands, the thing said to enforce its atomicity does
not exist. Stating commit-atomicity where only WP-atomicity is checkable invites a reviewer to accept "it
was one commit" as evidence, and to reject a correct two-commit sequence as a violation.

So: **A / B / C / D / F are same-work-package constraints** — all parts land in one WP, and the WP's
**final commit** is what every instrument sees (which is also exactly what the charter's ATDD rule
verifies: RED on base, GREEN on *the WP's final commit*). **Only E is one commit**, and only because its
verifier is a human reading `git log`.

**A. IC-02's parts land in one work package.** The three alias definitions, the five call-site
substitutions (`:439`, `:481`, `:484`, `:515`, `:518`), the **24 patch-target retargets**, and the
`_poll_jitter_multiplier` resolution (`:104-106`). **What makes them inseparable is that no intermediate
tree is green**: aliases without rerouting leaves arm 4a false; rerouting four of five leaves it false;
rerouting all five without retargeting leaves arm **4c** false *and* the five census assertions reading 0
attributed calls; retargeting without the alias fails `check_patch_targets.py` (`[ENFORCED]`,
`ci-quality.yml:884`); all of it without resolving `_poll_jitter_multiplier` leaves it at exactly **1**
occurrence, which SC-013 sub-3 names as the failing value. **Enforced at the WP's final commit**, by:
`tests/architectural/test_shared_module_object_patches.py` (arms 4a–4d — *authored by IC-06, which is why
this is not a commit-level constraint*), `scripts/check_patch_targets.py`, and
`tests/sync/tracker/test_saas_client.py::TestPolling::test_exponential_backoff_intervals`,
`::TestRetryBehaviors::test_429_respects_retry_after`,
`::TestRetryBehaviors::test_429_defaults_to_5s_when_missing`,
`tests/sync/tracker/test_saas_client_origin.py::TestSearchIssues::test_429_retries_then_raises`.

**B. The docstring correction rides in IC-02's work package.** `test_saas_client.py:55-57` says
of `[0.0, 301.0]` that *"there the second value `*is*` the assertion"* — opened and confirmed; the
only assertion in `test_timeout_after_5_minutes` is the `pytest.raises` at `:806`, with the call at
`:807`. SC-013 sub-4 requires
`grep -cE 'is\*? the assertion' tests/sync/tracker/test_saas_client.py` → **0**
(**verified `1` at HEAD and `1` at `98198e980`** — R2 pinned the plain-text pattern, which is **0** on
both trees, so its criterion was green before any work began) with the twin
`grep -c 'side_effect stimulus'` → **≥ 1** naming `:806` (**verified `0` pre-fix**, so it genuinely
moves). Splitting it from the alias work leaves a window in which the file states the fix is blocked
while the fix has landed — which is precisely how this claim reached the operator briefing.

**C. IC-04's analyzer and its control fixture land in one work package.**
`scripts/patch_seam_census.py` plus `tests/architectural/test_patch_seam_census_control.py` plus
**`tests/architectural/_fixtures/patch_seam_control/`**. **The criterion makes them inseparable**: SC-015
requires a census self-mutation arm — narrow the analyzer to today's five forms and the control fixture
must fail — which is only expressible when both exist. An analyzer landing without its control is
exactly the hardcoded-output-table cheat the squad found against SC-002 and SC-013.
Verified by: `tests/architectural/test_patch_seam_census_control.py` (all arms, including the two
previously-invisible positive cases — a context-manager `patch(...)` and a `side_effect=` kwarg sink —
and the `assert <value> in [...]` **negative** case that must report `n=0`).

**D. IC-06's gate, its `_baselines.yaml` key, AND its ratchet registration land in one work package.**
**R2's claim here was false and is corrected.** It said "a key landing without its gate is an orphan the
meta-test also fails" — the meta-test does **not** fail on an orphan key: `:214` checks only for
**missing** keys, never extra, and both comparisons run off hardcoded lists (`:274`, `:420`). Measured,
`test_no_dead_symbols` is exactly such an orphan and the suite is **green**. So the ratchet does **not**
make them atomic; **the four enumerated edits to `test_ratchet_baselines.py` are what make it true**
(see IC-06). Until those land, gate and key are independent and the baseline is decoration.
Verified by: `tests/architectural/test_ratchet_baselines.py` (including the **new reverse-containment
arm**) and `tests/architectural/test_shared_module_object_patches.py`.

**E. The guard commit precedes the alias commit — one commit boundary, inside IC-02.** **This is the only
genuine commit-level constraint, and R2 expressed it across a WP boundary where it deadlocks** (see
IC-02). The guard is IC-02's first commit and is RED on `98198e980` on two counts: the sync shard,
because `patch("…saas_client._sleep")` cannot be set up there; and **`scripts/check_patch_targets.py`,
a second `[ENFORCED]` gate** (`ci-quality.yml:883-884`, no args, so it scans all of `tests/`) which
reports `no attribute '_sleep'` for all three alias targets — verified via its own `_mock_importer`.
The alias-plus-retarget commit turns both GREEN. Inverting the order destroys the only
base-differentiating red the mission has and leaves the reviewer's red→green verification
(`charter.md:512-513`) with nothing to verify. **Verifier: a human reading `git log`** — which is why this
one stays "one commit" while the other five do not.
Verified by: `tests/sync/tracker/test_sleep_attribution_guard_3136.py` (arms (a) and (b) × five rows,
plus the two-mock pollution floors of SC-005).

**F. IC-03's ADR, its index row, and the lockfile regen land in one work package.**
`docs/adr/3.x/README.md`'s own `## Naming` section requires
`./.venv/bin/python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<file>` after adding an ADR, which
freshens **both** the era `README.md` row and `docs/development/3-2-page-inventory.yaml`. An ADR without
them reds `docs-freshness` on **every** PR (`on: pull_request`, no path filter;
`INVENTORY-LOCKFILE-DRIFT` is error-severity) and is invisible to the next reader — which is the failure
the ADR exists to prevent.

**Not coupled, deliberately**: IC-07 (inventory stamp, non-goal record) is independent of IC-02
through IC-06 and can land in any order; coupling it would serialise a prose edit behind a code change
for no gate reason. **Its one hazard is the docs lockfile**, and it is avoided by scope rather than by
sequencing: IC-07 is **body-only**, so it cannot change the frontmatter IC-03's regen reads.

### The resulting work-package graph — 7 WPs, acyclic, no lane-gated inversion

`/spec-kitty.tasks` owns the translation; this is the shape the concern map implies after the two merges,
recorded so the deadlock cannot be reintroduced.

```
WP01  env + C-001 window + NFR-005 baseline               (IC-01)         deps: —
WP02  guard[red] → alias seam + 24 retargets              (IC-02, was IC-05+IC-02)  deps: WP01
WP03  census + resolver export + control fixture          (IC-04)         deps: WP01
WP04  ADR + README row + page-inventory regen             (IC-03)         deps: WP02
WP05  gate + baseline key + ratchet registration          (IC-06)         deps: WP02, WP03
WP06  inventory verdict stamp + non-goal record           (IC-07)         deps: WP01
WP07  constraint transcripts + CI observation + filings   (IC-08, was IC-08+IC-09)  deps: WP02..WP05
```

**Critical path**: `WP01 → WP02 → WP05 → WP07`.

**Why it is acyclic now.** Every edge points from a WP that can reach `approved` to one that depends on
it. R2's graph had `WP(IC-05) → WP(IC-02)` where the source WP's final commit was red by construction, so
the source could never reach `approved` and the target could never be claimed — a **lane-gated** inversion
invisible to topological validation. Merging IC-05 into IC-02 removes the edge entirely rather than
reordering it.

**Parallelism, and the one cross-lane hazard.** Lane A is `WP01 → WP02 → WP04`, lane B is `WP03`, lane C
is `WP06`; they share no file. `WP05` joins A and B. The only cross-lane hazard is **docs**: WP04
regenerates `docs/development/3-2-page-inventory.yaml` from *all* page frontmatter, so a concurrent
frontmatter edit anywhere under `docs/` would drift the lockfile. WP06 also touches `docs/` — and stays
safe **only because it is body-only** (a verdict-column stamp). That is a constraint on WP06, recorded in
IC-07, not a coincidence to be rediscovered.

**One sequencing note the graph does not show**: WP01 acquires the C-001 `tests/sync` window and WP07
releases it, so the window spans the whole critical path. WP02 and WP07 both need it; WP03, WP04, WP05 and
WP06 do not (the census and the gate are static AST readers that never collect `tests/sync`, which is also
why the gate does not violate C-001).

---

## `[UNVERIFIED]` items

Carried from `spec.md` and re-checked here, plus items this session opened:

1. `[UNVERIFIED]` **The exact `AttributeError` text `<guard>` raises on `98198e980`.** The *fact* of
   the red is structural — `specify_cli.tracker.saas_client._sleep` provably does not exist at that
   SHA (verified: the module's only module-level names are `_SESSION_EXPIRED_MESSAGE` at `:36`,
   `_UNAUTHENTICATED_CATEGORY` at `:39`, and the function definitions). No test body was executed
   here, so the message string is unverified. The implementing WP records it.
2. `[UNVERIFIED]` **`sleep_assertions: 5` and `corruptible_assertions: 5` as `<census>`'s pre-fix
   output.** The **5** is `spec.md`'s AST measurement and this session re-derived the five `file:line`
   sites by opening each, but `<census>` does not exist, so its own total is unverified until it
   reproduces the number on `98198e980`.
3. `[UNVERIFIED]` **The exact residue total.** This session measured **≥ 29** in-class instances across
   **≥ 10** files by opening every cited line, but the read-side matching was done by two
   deliberately-approximate probes (one over-inclusive, one lacking alias resolution), not by the
   shipped analyzer. The **9** `mock_post`/`mock_get` count-read figure is a `grep -c` over five named
   files and is a lower bound: it does not cover alias forms. The committed census's total over
   `tests/sync/` is the authority and does not exist yet.
4. `[UNVERIFIED]` **`73` collected tests across the two census files** (SC-008's `N ≥ 73` twin) and the
   `selected == 2127` full-selection figure. Both require `pytest --collect-only`, which imports the
   modules; not run here under C-001. Inherited from `spec.md`.
5. `[UNVERIFIED]` **`28` as the smallest observed CI recorder total**, and the **`11/18`** (61%) pre-fix
   red rate with its **39%** clean-run corollary. All three come from the squad's CI-log survey
   (`analysis-report.md`); this session did not re-fetch the logs. NFR-001's floor of **100** does not
   depend on the exact value, but the `3.57×` ratio does.
6. `[UNVERIFIED]` **PR #3209's head SHA `5e98c2bb752f9ef6484eafc6411afedfd395f957`.** Not re-verified
   here (no network call made). The branch moved twice during this mission, so the SHA is the only
   reproducible handle.
7. `[UNVERIFIED]` **Whether any live thread in the `fast-tests-sync` shard calls `secrets.randbelow`.**
   Only two callers exist in `src/`, both inside `saas_client.py` (`:106`, `:515` — verified). Moot as
   a scoping question under R-1.
8. `[UNVERIFIED]` **Post-fix line numbers for the five rerouted call sites.** Adding three module-scope
   definitions shifts every later line; SC-007 item 4d requires the post-fix lines, which only the
   implementing WP can supply. The **pre-fix** lines of all 24 retargets are verified (each opened);
   retargeting is in-place, so the *test*-file line numbers should not move — only `saas_client.py`'s.
9. `[NEEDS RATIFICATION]` **`files_scanned` — `141` (`tests/sync/`) or `22` (`tests/sync/tracker/`) —
   bundled with `sleep_patch_sites`.** Both numbers are certain (`find tests/sync -name '*.py' | wc -l`
   → 141; `ls tests/sync/tracker/*.py | wc -l` → 22); which one SC-001 pins is an operator decision, not
   a measurement. `sleep_patch_sites: 14` is restated as `sleep_seam_patch_sites` (matching either target
   string) because the literal `14` **cannot survive the retargets** — post-fix, 0 sites match the
   pre-fix string. **One decision covers both.** Not `[UNVERIFIED]`.
10. `[UNVERIFIED]` **The correct disposition of `test_no_dead_symbols` in `_baselines.yaml`.** Measured:
    it is present in the YAML, absent from `_REQUIRED_TOP_LEVEL_KEYS`, and read by **no** comparison — so
    IC-06's new reverse-containment arm is **red on today's tree**, which is what proves the arm
    non-vacuous. Resolving it needs the owner of whatever gate that key was meant to govern, which is
    outside this mission. Two honest options (register it in both comparison lists, or remove it from the
    YAML); adding it to `_REQUIRED` alone is **not** an option, as that reproduces
    `test_all_declarations_required`'s defect — required, never read. If unresolvable in-mission, scope
    the arm to keys added from this mission forward and file the pre-existing pair.
11. `[UNVERIFIED]` **`scripts/check_patch_targets.py`'s aggregate report and exit code during the red
    window.** Its *resolver's* verdict on the three alias targets was reproduced directly this session
    (`no attribute '_sleep' in 'specify_cli.tracker.saas_client'`, with `…time.sleep` resolving as a
    control), but the script's whole-`tests/` run was not executed. The *fact* of the second red is
    structural; its output text is not.
12. `[UNVERIFIED]` **Whether the `130` `httpx.Client` reach-through sites trip the shipped gate.**
    Measured **130** under `tests/sync/` (`grep -rhoE 'patch\("specify_cli\.tracker\.saas_client\.httpx\.Client"' tests/sync/ | wc -l`),
    and **0** of them are read by a count-or-equality assertion (verified: no `mock_cls.call_count` /
    `mock_cls.assert_called*` anywhere in `tests/sync/`), so they should fall outside the R-2 predicate's
    read-side half. But the gate does not exist yet, so whether it correctly excludes all 130 — rather
    than flagging them and forcing a 130-row baseline — is unverified until IC-06 runs it. **This is the
    largest single unmeasured risk to the gate's shippability**, and it is why the read-side condition
    must be enforced rather than treated as documentation.
