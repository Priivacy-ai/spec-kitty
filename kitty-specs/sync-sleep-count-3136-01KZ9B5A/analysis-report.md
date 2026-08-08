# Post-spec adversarial squad — findings, rulings, remediation directive

**Mission**: `sync-sleep-count-3136-01KZ9B5A` · **Point-cut**: post-spec · **Date**: 2026-08-05
**Squad**: live-evidence (`debugger-debbie`), anti-laziness (`reviewer-renata`), seam/structure
(`architect-alphonso`) — three profile-loaded lenses on one framed question, each told not to
duplicate the others. Run through the canonical `adversarial-squad` skill.

**Verdict: the static census is sound and the injection guard is genuinely non-vacuous; the live
evidence is not.** Two blockers converged on independently, plus a criterion set in which 6 of 13
criteria could be satisfied while the defect survived.

---

## Operator rulings (2026-08-05)

| # | Question | Ruling |
|---|---|---|
| **R-1** | Test-side assertion hardening vs a product-side module-local alias | **Product-side module-local alias.** Add `_sleep` / `_monotonic` / `_randbelow` at module scope in `saas_client.py` and route the call sites through them, so `@patch("…saas_client._sleep")` binds a **module-local** attribute that structurally cannot observe another thread's `time.sleep`. Conditions: an ADR recording it as a deliberate testability seam; the gate keyed on the mechanism and asserting the seam's own call-site routing; and `_poll_jitter_multiplier` (dead, `:104-106`) deleted or promoted to sole authority in the same change. |
| **R-2** | Scope, now that the class is measurably live outside `tests/sync/tracker/` | **Widen the predicate, keep the enforced scope at `tests/sync/`.** Key the gate on the **mechanism** — refuse any `@patch("a.b.c.attr")` whose penultimate segment resolves at import to a `ModuleType` when the resulting mock is then read by a count or equality assertion — and enforce over `tests/sync/` (which contains the newly-found instances) but not `tests/cli`, which `C-001` forbids this mission from even running. The "confined to `tests/sync/tracker/`" claim is struck. |

**R-1 dissolves several findings rather than requiring them to be fixed.** A module-local alias makes
**every existing assertion correct unchanged** — including `:787`'s `mock_randbelow.call_count == 3`
and `:804`'s `[0.0, 301.0]` — so `FR-006` and `FR-007` retire as work items, and the `FR-006`
position analysis below becomes moot. Recorded anyway, because the reasoning is what justifies the
ruling.

---

## BLOCKER-1 — the reproduction is not composition-dependent, and pristine `main` is **not** green in the full shard

**The spec claimed** (`spec.md:442-448`, `:74`, `SC-006` at `:259-270`) that on PR #3209's branch the
class reddens in the full shard while the nodes pass narrow, that pristine `main` is **green** in the
full shard (`2116 passed, 11 skipped, 271 deselected`, `EXIT=0`), and therefore that the failure is a
**composition** dependence rather than a contention race — with `SC-006` Arm B as the mission's only
discriminating arm.

**Measured, from CI's own logs:** pristine `main` reddens on this class in **11 of 18** consecutive
`fast-tests-sync` jobs (**61%**), including at **`98198e980`** — the spec's own baseline:

```
job 92278529393 (main @ 98198e980):
  3 failed, 2113 passed, 11 skipped, 2 warnings in 100.79s
  assert 174 == 3 ; Called 153 times. ; Called 507 times.
```

`2113 + 3 = 2116` — **the same selection** as the local `2116 passed` run. So the variable is
**topology (parallel vs serial) plus timing**, not composition.

**And it is nondeterministic at a fixed commit.** Three of six same-SHA run pairs disagree:
`abca7ec96` reddened two nodes in job 91883621718 and was clean in 91677177124; `bb2020fea9` produced
*different victim sets with different magnitudes on identical commits* (71 vs 115 on the same node).

**Consequences.** `SC-006` discriminates nothing: pre-fix, a single full-shard run shows zero class
failures 39% of the time, so "Arm B green ⇒ fixed" commits exactly the error the spec's own
adversarial table forbids. `SC-006`'s command is also **serial**, while CI runs
`-n auto --dist loadfile` (`ci-quality.yml:1163-1171`) — running the "full-shard composition" arm
serially is a different experiment from the one CI fails. And Arm B's quoted transcript is from a
**superseded** head (`783c137d7`, job 92227080191); on the then-current head the backoff node
**passes**.

**Remediation.** Withdraw "deterministic / composition-dependent"; restate the defect as
**topology-and-timing dependent with composition as a probability modifier**. Either rebuild `SC-006`
as *repeated parallel* runs with a stated pre-fix red rate, or delete it and rest the mission on the
injection guard, which is the sound part. Pin PR #3209's head SHA rather than its branch name — the
branch has already moved twice during this mission.

---

## BLOCKER-2 — the class is not confined to `tests/sync/tracker/`, and the census structurally cannot see the instances

Two lenses found this independently, by different routes.

**The sixth corruptible assertion**, `tests/sync/test_final_sync_diagnostics.py:309`:

```python
assert sleeps == [FINAL_SYNC_RETRY_BACKOFF_SECONDS, FINAL_SYNC_RETRY_BACKOFF_SECONDS]
```

fed at `:303` by `patch("specify_cli.sync.batch.time.sleep", side_effect=sleeps.append)`, with
`src/specify_cli/sync/batch.py:11` a **bare `import time`** and `pytestmark = pytest.mark.fast` at
`:27` — so it is inside `-m "fast and not windows_ci"`. Structurally identical to
`test_saas_client.py:786`: a whole-list equality over an unfiltered process-global recorder.

**Two blind spots let it hide, and both are in the mission's own instruments:**

1. **The census inspects decorators only** — this is a **context-manager** `patch(...)` call.
2. **The predecessor's closure grep is `sleep\.side_effect\s*=`** — this is the **kwarg** form
   (`side_effect=sleeps.append`), which that pattern cannot match. So `spec.md:362`'s "**0 hits** …
   the predecessor's closure argument still holds" is true of the *pattern* and false of the *hazard*.

**Plus five more in the same shard**, under `@patch("specify_cli.sync.git_metadata.subprocess.run")`
with bare `import subprocess` at `git_metadata.py:13` — `tests/sync/test_git_metadata.py:226`, `:249`,
`:281`, `:471`, `:530`, all `assert mock_run.call_count == N`, plus three exact-list clock couplings
at `:218`, `:242`, `:274` under bare `import time` at `git_metadata.py:14`. The producer population is
**stronger** there than for `secrets`: `git_metadata` is called from sync background threads, and
`#3130`'s leaked threads shell out to git.

**Remediation (R-2).** Widen the census to context-manager `patch()` calls **and** `side_effect=`
kwargs. Strike the confinement claim. Key the gate on the mechanism, not the attribute — as specified
it refuses corruptible *sleep* assertions, so nothing stops `mock_randbelow.call_count == 1` (three
lines from a census assertion) or `mock_run.call_count == 2`. Without this, `SC-001` can report
`corruptible_assertions: 0` while the class is open in this mission's own window.

---

## The criterion set — 6 of 13 satisfiable while the defect survives

Better than the predecessor mission's 9 of 11, but the two criteria carrying the entire fix fall to
the **same one-line rewrite**.

**The cardinality hole (BLOCKER).** Rewrite each 429 assertion as:

```python
assert 3.0 in [c.args[0] for c in mock_sleep.call_args_list]
```

This is *genuinely* non-corruptible — an intruder's extra call does not change the verdict — so
`corruptible_assertions: 0` is honestly true; the 22/14/4 denominators are untouched; `SC-002` can
emit `n=1  delays=[3.0]` from that live `ast.Assert` node; `SC-003`'s value mutation still reddens it;
`SC-004` arm (b) still raises. **Every criterion green — and the test no longer detects a production
change that issues two attributed sleeps instead of one.** `FR-002` forbids this in prose and measures
it nowhere; `SC-001` pins *nodes* but has no `sleep_assertions: 5` denominator.

Fix: add a **cardinality** mutation arm (duplicate the `time.sleep(...)` call at `saas_client.py:439`;
add a fourth `pending` response for the backoff node) requiring red on the **count**, not the value.

| SC | Verdict | The cheat |
|---|---|---|
| `SC-001` | **passes-while-broken** | the `in`-form rewrite; no assertion-count denominator |
| `SC-002` | **passes-while-broken** | same rewrite yields `n=1` honestly; also `<census>` has no self-mutation arm and `NFR-007`'s control fixture has no criterion, so a hardcoded table satisfies it |
| `SC-007` | **passes-while-broken** | point the gate's glob at `tests/**`: reports `scanned_files: 300 >= 22`, `patch_sites: 131 >= 14`, passes its self-mutation arm, never opens `tests/sync/tracker/`. The floor is a count, not a membership set |
| `SC-008` | **passes-while-broken** | `_PINNED_LEAKS` entries are `_PinnedLeak(...)` calls; the token appears only at the declaration (`_leak_guard.py:333`) and the derived dict (`:424`), so `grep -cE '^\+.*_PINNED_LEAKS'` on a diff adding a real entry returns **0** — proved on a synthetic diff. Use `^\+\s*_PinnedLeak\(` plus an AST count pinned at **12** (which also contradicts `C-003`'s "11 confirmed leaks") |
| `SC-011` | **vacuous** | already green before any work: 3 / 3 / 5 measured against the spec as committed. It grades the spec, not the implementation |
| `SC-013` | **passes-while-broken** | print the string `hardened`; nothing measures `:787` (no `secrets.randbelow` probe exists) and nothing resolves `filed:#<issue>` |

`SC-005` survived — both lenses tried and failed. Its mutual dependency with `SC-004` arm (b) makes a
vacuous probe self-defeating. It is the best-built criterion in the set.

`SC-004` covers **4** of the 5 census assertions: `assert delays == [0.9, 2.0, 4.4]` (`:786`) — the
subtle member, most likely to be "hardened" while still reading the unfiltered recorder — has no
pre-fix red arm.

---

## The false blocker — docstring prose as a load-bearing constraint, for the third time in this programme

`[NEEDS CLARIFICATION]` #2 states the `time.monotonic` fix is "blocked because
`test_timeout_after_5_minutes`' exact `301.0` value **IS** its assertion." **It is not.**
`test_saas_client.py:804-811`:

```python
mock_monotonic.side_effect = [0.0, 301.0]
with pytest.raises(SaaSTrackerClientError, match="timed out after 5 minutes"):
    client._poll_operation("op-timeout")
```

`301.0` is a **side_effect stimulus**; the only assertion is the `pytest.raises` match. And the fix is
not blocked: `itertools.chain([0.0], itertools.repeat(301.0))` is unbounded and preserves both the
exact stimulus and the exact raise (production reads the clock twice, `:479` then `:484`).

**The claim originates in a docstring** — `test_saas_client.py:56-57`, `_advancing_clock`'s own text:
*"there the second value is the assertion"* — and propagated into the spec, then into the operator
briefing. Deferring on a non-existent blocker is not a legitimate operator decision. Strike the
blocker clause; correct the docstring in the same breath. **This is the same failure mode as
`tests/integration/test_coord_loop_workspace.py:611` in the sibling mission: a cited line treated as
an assertion without opening it.**

---

## Arithmetic and provenance corrections

- **`NFR-001`'s floor derivation is false.** "4× margin below … and **33×** above the smallest
  observed CI inflation (`48`)". The smallest observed recorder total on a census node is **28**, not
  48; `100/48 = 2.08×`, `100/28 = 3.57×`. The `33.3×` figure is `100/3` — computed against the
  *expected* count, not the observed inflation the prose names. The floor value 100 is defensible;
  its justification is not.
- **`spec.md:370-371`'s quoted provenance command does not produce its quoted number.** As written
  `grep -c 'patch("specify_cli.tracker.saas_client\.'` returns **68**, not 15. The 15-vs-14 pair is
  reproducible from a different command. This matters because the checklist asserts every count traces
  to a command run in the session.
- **`SC-003`'s pinned failure text `[1.35, 3.0, 6.6]` is unsatisfiable as literal.** Computed against
  production: `[1.35, 3.0, 6.6000000000000005]`. The unmutated `[0.9, 2.0, 4.4]` *is* exact, which is
  why the current test passes.
- **`SC-006` Arm A's `2116 passed, 11 skipped` split is unattributed** and not marked `[UNVERIFIED]`.
  The verifiable halves check out — `--collect-only` gives `2127/2398 (271 deselected)` and
  `2116 + 11 = 2127` — so the total and deselected count are sound; only the pass/skip split has no
  provenance. Restate the arm as `selected == 2127`, `FAILED == 0`, `ERROR tests/ == 0`.
- **`SC-010`'s `E`-number clause is a malformed command** — `grep -cE … file1 file2` prints per-file
  counts, so `= 0` has no single value to compare.

---

## Unenforced constraints and traceability gaps

- **`C-002`, `C-004`, `C-008`, `C-010` have no enforcement anywhere**, two of them High. `C-004`
  (production retry behaviour unchanged) rests on a `git checkout --` revert that a clean revert
  satisfies even if a different line shipped changed. One-line fixes exist:
  `git diff upstream/main -- src/specify_cli/tracker/saas_client.py` empty (**note: R-1 changes this —
  the criterion must now be "changed only by the declared alias seam"**), the same for
  `.github/workflows/ci-quality.yml`, and one `tests/architectural/test_no_legacy_terminology.py` arm.
- **`NFR-005` has no criterion** — the only NFR without one.
- **`NFR-007`'s control-fixture clause has no criterion.** The one thing that would make `<census>`
  trustworthy is described in Verification Provenance and commanded nowhere — and `<census>` is the
  sole instrument for `SC-001`, `SC-002` and `SC-013`.
- **`SC-012` has a config escape hatch**: `ruff check .` clean plus zero added inline `# noqa` is
  satisfied by adding `per-file-ignores` or widening `exclude`, which `CLAUDE.md` prohibits and no
  criterion detects.
- **`SC-006` maps to no `FR`/`NFR` ID** — the only criterion with no requirement anchor.
- **`FR-007` has two live meanings** (`DIR-032`): this spec's `time.monotonic` disposition, and the
  **predecessor's** `#3115` FR-007 baked into printed strings at `tests/sync/conftest.py:485`, `:494`.
  Qualify the inherited one.

---

## Environment — every SC command is unrunnable as written

`/home/jeroennouws/dev/sk-missions/3136/.venv` contains **no `pytest`** and **no `ruff`**
(`.venv/bin/python -m pytest` → `No module named pytest`), and the ambient interpreter is **3.14.4**
while CI pins **3.12**. `NFR-005` requires a baseline "captured in the same session as the comparison"
using the mission venv — that combination does not exist. Pin the interpreter and runner explicitly
(`uv run --python 3.12 python -m pytest`) or add a provisioning task, so a work package does not
discover this at acceptance time.

Good news, measured: the named producer loop `delay = min(delay * 2, remaining, .05)` **is** still
present in CPython 3.14's `subprocess.Popen._wait`, so the mechanism reproduces locally.

---

## What survived scrutiny

The **static census is correct**, independently re-derived by AST twice: 22 files, 14 sleep patch
decorators (13 + 1, all resolving to one target), 10 neutralisation-only, 4 nodes, 5 corruptible
assertions. Every cited line resolves. `:532` and `:550` are confirmed **inside** a docstring spanning
`513-762` — checked rather than assumed.

**All five assertions are corruptible, including the delay-sequence one** — verified by simulation: a
single extra call breaks `delays == [0.9, 2.0, 4.4]` (`delays=[0.9, 2.0, 4.4, 0.001]`). So there is no
purely-delay-valued assertion to preserve, and `FR-002` must preserve the contract's *values and
cardinalities* rather than its current expression.

**The closure claim on the census nodes is strengthened, not weakened**: over 20 jobs the union of
CI-observed victims is exactly those 4 nodes, and run `de66c4960` reddened **all four simultaneously**
— better evidence than the union-over-runs argument the spec uses.

**The root cause is confirmed on Python 3.12 and 3.14**, serial and `-n2`:
`stdlib_time_sleep_is_mock: true` in every arm.

**A tail-slice hardening would be unsound** (`last3_are_tail` was `False, True, False` across three
runs) — the fix must attribute by **thread**, not by position. And a `main_thread()` filter is
topology-invariant: the test body is `MainThread` under both serial and `-n2`.

---

## Process note

All three lenses were **profile-loaded** — each ran `spec-kitty agent profile show <id>` and
`spec-kitty charter context --action specify --json` and reported which directives and tactics it
applied. Earlier squads in this programme were dispatched by persona name only, which is the
`adversarial-squad` invariant they were violating: loading the profile, not naming it, is the point.

Each lens also conceded its limits explicitly. The evidence lens could not run either composition arm
(`C-001`) and rests its refutation on CI logs it fetched but did not produce; its "fixed composition"
claim is really "fixed commit", since it did not verify worker→file assignment. The falsifiability lens
ran no test bodies and did not cost its headline cheat against the chosen seam. The seam lens named
three of its five answers as operator judgement rather than architectural fact. Those concessions are
why the convergent findings are trustworthy.

---

# Post-plan adversarial squad — findings, adjudication, remediation directive

**Point-cut**: post-plan · **Date**: 2026-08-06 · via the canonical `adversarial-squad` skill.
**Squad**: seam/structure (`architect-alphonso`), gate-vacuity (`reviewer-renata`), sequencing
(`planner-priti`) — three profile-loaded lenses. **All three verdicts: not sound enough to decompose.**
Score from the vacuity lens: **18 criteria sound / 13 passes-while-broken**.

---

## BLOCKER-1 — the edit that *constitutes* the fix has no owner (all three lenses, independently)

`_sleep = time.sleep` at module scope binds the **function object at import**. `@patch("specify_cli.tracker.saas_client.time.sleep")` mutates the `time` module's attribute and **cannot reach that binding**. So every existing decorator must be **retargeted** or R-1 does nothing.

Measured inventory:

```
grep -oE 'patch\("specify_cli\.tracker\.saas_client\.[^"]+"' \
  tests/sync/tracker/test_saas_client.py tests/sync/tracker/test_saas_client_origin.py | sort | uniq -c
  14 test_saas_client.py …saas_client.time.sleep        (13 live + 1 in the :513-762 docstring)
   9 test_saas_client.py …saas_client.time.monotonic
   1 test_saas_client.py …saas_client.secrets.randbelow  (:499)
   1 test_saas_client_origin.py …saas_client.time.sleep
```

**23 edits in `test_saas_client.py`** — a file `plan.md:237` restricts to *"docstring correction at
`:55-57` **ONLY**"* — plus **1 in `tests/sync/tracker/test_saas_client_origin.py`**, which appears
**nowhere** in `## Project Structure`.

**Simulated, both alias forms**, one production call plus a 200-call intruder thread:

```
[assignment] patch('prod.time.sleep')      -> prod_calls_seen=200   (production calls seen: 0; test slept 3.00s real)
[wrapper   ] patch('prod_wrap.time.sleep') -> prod_calls_seen=201   (fully corrupted — defect intact)
[assignment] patch('prod._sleep')          -> prod_calls_seen=1     (immune)
[wrapper   ] patch('prod_wrap._sleep')     -> prod_calls_seen=1     (immune)
```

So R-1 as owned today has exactly two outcomes: **assignment** → the five census assertions see 0 calls,
go red, and gain real wall-clock (blowing `NFR-005`); **wrapper** → every node stays green **and the
recorder still counts 201 foreign calls** — the mission ships and the class survives untouched.

**Provenance, which matters more than the defect.** Operator ruling R-1 was recorded as *"makes every
existing assertion correct **unchanged**"*, and that phrasing propagated into `spec.md:317` and
`plan.md:30`. It is true of the assertion **text** and false of the patch **target**. The orchestrator
wrote it; three lenses had to open the decorators to catch it.

**Applied.** Add `test_saas_client_origin.py` to the map under IC-02. Restate `test_saas_client.py`'s
permitted change as "the `:55-57` docstring **plus the 24 enumerated patch-target retargets**", with every
target string listed pre/post. **Bind the alias form to assignment, not wrapper** — the wrapper form is
the cheat. Make arm 4 assert the **test-side** target strings, not only product-side call sites. And
re-ratify `sleep_patch_sites: 14`, which cannot survive the retarget (post-fix there are **0** sites
matching the pre-fix string).

---

## BLOCKER-2 — `uv run --python 3.12` uninstalls its own test runner

`pytest`/`ruff`/`mypy` live only in `[project.optional-dependencies]` (`pyproject.toml:100-115`);
`[dependency-groups] dev` carries type stubs only; there is no `[tool.uv]` block. Proved
non-destructively:

```
uv sync --dry-run --python 3.12
→ "Would uninstall 70 packages"  … pytest==9.0.3, ruff==0.15.12, mypy==1.20.2, pytest-xdist, pytest-cov …
```

So `plan.md:190`'s C-010 command and `spec.md:327`'s NFR-005 both-arms command remove pytest and then
fail. CI only works because every job runs `uv sync --frozen --all-extras` first (`ci-quality.yml:1145`).
**This also explains the venv destruction observed during planning** — the "safe" pinned form was the
destructive one.

**Applied.** The single sanctioned form is
`uv run --python 3.12 --extra test --extra lint python -m …`, or `uv sync --python 3.12 --extra test
--extra lint` once followed by `./.venv/bin/python -m …`. Every command in the plan is rewritten to it —
only one of nine was pinned at all; the rest resolve to the foreign `~/.local/bin` checkout.

---

## BLOCKER-3 — the frozen shrink-only baseline is governed by nothing (seam + vacuity + sequencing)

`tests/architectural/test_ratchet_baselines.py:123` `_REQUIRED_TOP_LEVEL_KEYS` is a hand-written
frozenset; `:214` computes `_REQUIRED - set(data.keys())` — **missing** keys only, never **extra**; and
both comparisons run off hardcoded literal lists (`:274` growth, `:420` shrinkage).

Measured, and it is the default outcome rather than a hypothesis:

```
YAML keys: 12
YAML keys NEVER read by the ratchet: ['test_all_declarations_required', 'test_no_dead_symbols']
pytest tests/architectural/test_ratchet_baselines.py -q → 3 passed in 60.47s   (green with both inert)
```

Two of twelve existing keys are **already** inert — one of them even in the *required* set while the
growth check never reads it. A 13th key added by IC-06 joins them: read by nothing, growth fails nothing.
`plan.md:202`'s Charter row 17 grades this **Pass** on *"growth FAILS CI"*; `plan.md:688-693`'s coupling D
claims the meta-test catches an orphan key. Both are false. `test_ratchet_baselines.py` appears in no IC's
surfaces.

**Applied.** IC-06 owns `test_ratchet_baselines.py`, with the three required edits enumerated
(`_REQUIRED_TOP_LEVEL_KEYS` **and both** `single_baselines` lists), plus a **reverse-containment arm**
(`set(data) - _REQUIRED == ∅`) so the next inert key is caught. Row 17 becomes
`Pass only if registered`. The honest-ratchet precedent to copy is
`tests/architectural/_inert_slots_baseline.yaml` + `test_no_inert_schema_slots.py` — permanently-empty
allowlist pinned by an arm, per-row `owner:`/`disposition:`, an owner-completion arm, and a
ratchet-registration arm — none of which the plan cites, while Charter row 10 claims Pass on canonical
sources.

---

## BLOCKER-4 — IC-05 before IC-02 deadlocks the dependency gate

The charter's ATDD rule is **per work package**: RED on the WP's `planning_base_branch` **and GREEN on the
WP's final commit** (`charter.md:506-513`). If IC-05 and IC-02 are separate WPs, WP(IC-05)'s final commit
is red **by construction**, so it cannot pass review → cannot reach `approved` → and
`dependency_readiness_for_wp` (`core/dependency_graph.py:50-77`,
`_SATISFYING_DEPENDENCY_LANES = {approved, done}`) blocks WP(IC-02) from ever being claimed. Dependencies
here are **WP-level and lane-gated**, never commit-level — so coupling E's "depends on IC-05's guard
*commit*" is not expressible.

**Applied.** **Merge IC-05 into IC-02** as one WP with the guard as its first commit. That is exactly the
shape `charter.md:509` prescribes, and it turns coupling E into an intra-WP commit order instead of an
inter-WP inversion. No cycle existed topologically — `finalize-tasks` would have passed it and the
deadlock would have surfaced at `implement`.

---

## BLOCKER-5 — the ADR forces a generated-lockfile regen that no IC owns, and a blocking job checks it

`scripts/docs/freshen_adr_inventory.py` writes a row into `docs/development/3-2-page-inventory.yaml` — its
own docstring calls it *"a generated lockfile"* (111 KB, exists) — plus an era-README row.
`.github/workflows/docs-freshness.yml:3-4` runs on **every** `pull_request` with no path filter, and
`:53-58` runs `check_docs_freshness.py --ci`, whose `INVENTORY-LOCKFILE-DRIFT` finding is error-severity.
A new ADR without its regenerated row reds that job.

**Applied.** `docs/development/3-2-page-inventory.yaml` joins IC-03's owned paths, with the regen command
named. The ADR's frontmatter contract (`title`, `date`, plus `description_length_check --strict`,
`related_validator --strict`, `relative_link_fixer --check`) is stated, and the template named
(`docs/architecture/adr-template.md`).

---

## MAJOR — the seam institutionalises a *second* idiom, because the class's largest residue module already has a working one

`src/specify_cli/sync/batch.py:628-631` already exposes
`run_final_sync_with_retries(..., *, sleep: Callable[[float], None] | None = None)`; `:641` is
`sleeper = time.sleep if sleep is None else sleep`, threaded down through `:667-700`. **Three tests in the
very file the plan freezes already use it** (`test_final_sync_diagnostics.py:180`, `:207`, `:239`,
`sleep=sleeps.append`). The frozen row (`:303`/`:309`) reaches through the shared `time` module **only**
because its entry point `service.stop()` → `background.py:467` is the one caller that does not thread the
existing seam. `grep -in 'inject|sleep=|dependency'` over all three mission documents → **zero hits**.

Consequences: IC-03's ADR declares an alias canonical for one module while adjudicating nothing about the
competing idiom, so the class ends with two seam styles and no precedence rule; IC-09's ticket text
("requires alias seams in four more product modules") is **false for `batch.py`**, where the row is
closable by threading one keyword argument; and the repo already has the governing precedent —
`docs/adr/3.x/2026-06-26-1-single-authority-seam-and-call-site-gate.md`, which decided seam + AST
call-site gate + curated allowlist *against* full DI.

**Applied.** IC-03's ADR must adjudicate the **idiom**, not the instance: where a module already exposes a
call-site injection point, thread it; introduce a module-local alias only where the stdlib call has no
threadable caller. Relate it to the 2026-06-26 ADR explicitly. Rewrite the `batch.py` baseline row's
justification accordingly.

---

## MAJOR — three criteria are already green on the base tree, or unsatisfiable in both states

- **`SC-013` sub-4's negative is green before any work.** The spec pins
  `grep -c 'is the assertion' … → 0` and says *"it is 1 today"*. Measured: **0** today — the docstring
  reads `there the second value *is* the assertion` with RST emphasis. `git show 98198e980:…| grep` exits
  1. **The line was opened; the grep was never run.** This is the `301.0` failure mode recurring *inside
  the plan written to stop it.* Re-anchor on `grep -cE 'is\*? the assertion'`.
- **`SC-005` Probe A is a tautology.** `alias_recorder_calls_from_probe == 0` is structurally
  unfalsifiable post-fix under either alias form, green on a tree where the fix is 5% done; and its twin
  `stdlib_probe_calls >= 100` is a counter the probe increments **about itself**. A probe whose body is
  `counter += 1; pass` satisfies both. **Applied:** two mocks in one window — patch stdlib `time.sleep`
  *and* `_sleep`, assert `stdlib_mock.call_count >= 100` **and** `alias_mock.call_count == expected`, so
  both numbers are read off recorders and must disagree by exactly the injected volume. This also proves
  the load-bearing property nothing else asserts: `_sleep` is bound **at import**.
- **`SC-013` sub-1 is unsatisfiable in both states.** It requires resolving *"each patch target's
  penultimate segment and asserting it is **not** a `ModuleType`"* — for `patch("…saas_client._sleep")`
  the penultimate segment **is** `saas_client`, a module. It is the identical 97.7%-over-broad formulation
  the plan spent three paragraphs correcting for R-2, carried into a different criterion unnoticed.

---

## MAJOR — arm 4's carve-out admits the wrapper cheat, and the red-first commit reddens a second ENFORCED gate

Arm 4 asserts *"0 direct `time.sleep(` … calls **outside the three alias definitions**"*. Under the wrapper
form the only `time.sleep(` **is** inside the alias definition — excluded by the carve-out, arm 4 passes,
defect intact. It is also alias-evadable: `import time as t; t.sleep(x)`, `from time import sleep`, and
`getattr(time, "sleep")(x)` all leave the negative true. **Applied:** resolve import bindings in the
module's own AST and assert zero calls whose callee *resolves* to those three attributes, plus assert the
three module-scope names are still bound to exactly `time.sleep`/`time.monotonic`/`secrets.randbelow`.
Copy the shape from `test_protection_resolver_call_sites.py:93-110`.

Separately: `scripts/check_patch_targets.py` is `[ENFORCED]` at `ci-quality.yml:884` with no args, so it
scans every `patch()` string under `tests/`. Verified against the base tree, all three alias targets
return `"has no attribute '_sleep'"` etc. So the guard-before-alias commit reds the **lint job** too — a
second red that coupling E does not name and no IC owns.

---

## Ownership and sequencing corrections

- **`notes/constraint-enforcement-3136.md` has one declared owner and three writers** (IC-01, IC-08,
  IC-09), and IC-01→IC-08 is not a declared edge. Split IC-01's transcript into
  `notes/environment-3136.md`.
- **Five of six couplings assert *commit* atomicity while every named instrument evaluates the working
  tree at CI time.** Coupling A's instrument is a file IC-06 authors *after* IC-02 commits. Relabel
  A/B/C/D/F as **same-work-package** constraints; keep "one commit" only for E, whose verifier is a human.
- **Nothing owns the `C-001` `tests/sync` window** that three concerns and two criteria require — the
  single most likely place for the mission to stall. Make acquisition/release an explicit deliverable with
  a recorded handshake, and a dependency edge.
- **Nothing owns the draft PR**, yet IC-08's CI observation is defined in terms of its head SHA.
- **No concern owns the pytest markers** the three new test files need.
  `test_pytest_marker_convention.py` requires a module-level `pytestmark`; without `pytest.mark.fast` the
  guard never runs in `fast-tests-sync` **and** becomes a gate-coverage orphan against
  `_gate_coverage_baseline.json` (`"orphan_files": []`).
- **`IC-09` owns no repository artifact**, so it can carry no evidence and cannot be reviewed — fold into
  IC-08.
- **`files_scanned: 22` remains unresolved.** `find tests/sync -name '*.py'` → **141**;
  `tests/sync/tracker/*.py` → **22**. Bundle with `sleep_patch_sites: 14` for one ratification.

## Corrected graph (7 WPs, acyclic, critical path WP01→WP02→WP05→WP07)

```
WP01 env + C-001 window + NFR-005 baseline          (IC-01)         deps: —
WP02 guard[red] → alias seam + 24 retargets         (IC-05+IC-02)   deps: WP01
WP03 census + resolver export + control fixture     (IC-04)         deps: WP01
WP04 ADR + README row + page-inventory regen        (IC-03)         deps: WP02
WP05 gate + baseline key + ratchet registration     (IC-06)         deps: WP02, WP03
WP06 inventory verdict stamp + non-goal record      (IC-07)         deps: WP01
WP07 constraint transcripts + CI observation + filings (IC-08+09)   deps: WP02..WP05
```

Lanes A (`WP01→WP02→WP04`) / B (`WP03`) / C (`WP06`) share no file; WP05 joins A and B. The only
cross-lane hazard is docs — WP04 regenerates the page-inventory lockfile from all frontmatter, so WP06
must stay body-only (it is: a verdict-column stamp).

## What survived scrutiny

The plan's **measurements are honest** — 141 / 22 / 53 inventory rows / 12 `_PinnedLeak(` /
17 `_WatchedGlobal(` / 98 ADRs / 165 arch tests / `_poll_jitter_multiplier` = 1 all re-derived and matched,
and `conftest.py:494`'s serial-only string is exact. The narrowed R-2 predicate **does not under-flag**:
all 29 known instances are caught. The control fixture (IC-04/`SC-015`) is the strongest construction in
the set and genuinely defeats the hardcoded-table cheat. 18 of 31 criteria are load-bearing. The gate does
**not** violate `C-001` — it is a static AST reader that never collects `tests/sync`. And
`_leak_guard.py`'s boundary is correctly drawn: it diffs a global's *value* at teardown, `patch` restores
`time.sleep`, so its absence from `_WATCHED_GLOBALS` is right.

**It over-flags in a direction nobody measured:** the largest single contributor to the 286 reach-throughs
is `patch("specify_cli.tracker.saas_client.httpx.Client")` (~100+ sites), same mechanism, named in no
artifact. The gate ships flagging ~292 sites.

---

# Post-tasks squad — anti-laziness lens (recorded, NOT yet remediated)

**M3 is parked at `tasks` until M2 reaches a PR.** These findings are recorded so nothing is lost;
remediation happens in one pass when the mission resumes, together with the feasibility lens.

**Verdict: WP03, WP05 and WP07 are handable as they stand. WP02 must be fixed first.**

## BLOCKER — WP02's DoD omits `SC-004`, `SC-005` and `NFR-001` entirely

`grep -n 'SC-00\|NFR-00'` over WP02's DoD block returns `SC-003`, `SC-008`, `SC-012`,
`NFR-002/003/004` — and nothing else. The guard's ten arms, the `stdlib_mock.call_count >= 100` floor,
the `alias_mock.call_count == <expected>` twin and the `finally`-joined probe are all **prescribed in
T005 and graded by no DoD line**.

**The cheat:** a guard whose entire body is `with patch("specify_cli.tracker.saas_client._sleep"): pass`.
It is genuinely `AttributeError`-red on `98198e980`, green on head, passes 10/10 and 6/6, adds zero
`^ERROR tests/` — and satisfies every DoD item. The mission's only **runtime** evidence that the seam is
import-bound and pollution-immune becomes decoration. No sibling covers it: WP05 grades the seam
statically, WP07 grades constraints.

The *fix* still lands (the assignment form plus DoD 5 plus WP05 arm 4c force it), so the defect does
close — but it would ship with no live proof that it did.

## BLOCKER — arm (b) is pointed at the wrong recorder

WP02 T005 step 3 says the pre-fix expression is evaluated "against the **same mock object**", whose only
antecedent is arm (a)'s **alias** recorder. Post-fix that recorder sees exactly 3/1/1/1 calls, so
`len(mock.call_args_list) == 3` **passes and cannot raise**. `spec.md:657-658` has it right — arm (b)
must evaluate against the **stdlib-polluted** view — but WP02 never carries that half. The implementer
is handed a self-contradictory arm whose cheapest resolution is the one `SC-004`'s own adversarial row
forbids.

## MAJOR — the prose-occurrence count is off by one, and Reviewer Guidance hands wrong expected values

There are **two** docstring occurrences, not one: `:559` **and `:715`**, both inside the `:513-762`
docstring. `:715` is invisible to the spec's own re-derivation command because it lacks the `patch("`
prefix. So the string-occurrence arithmetic is **26**, not 25; T009 step 4 would leave `:715` stale; and
**Reviewer Guidance #4 states 14 → 1 where the truth is 15 → 2**. A reviewer applying it literally sees
a mismatch and reaches for this mission's own named failure mode — editing prose to satisfy a numeric
gate. Same class as commit `38183fc1c`, one layer down. (The AST answer is unchanged: 13 → 0.)

## MAJOR — three WPs grade their DoD against a notes file none of them owns

`wps.yaml` declares five out-of-map notes writes. `grep -ohE 'notes/[a-z0-9-]+\.md'` over WP03, WP04 and
WP05 returns **nothing** — WP05 DoD 11 grades a literal `<wp-notes>` placeholder. Worse, WP02 routes its
T012 determinism transcripts into `constraint-enforcement-3136.md`, which "has exactly one writer" —
**WP07, which runs after WP02**. So WP02's determinism evidence has no home at WP02 time.

## MAJOR — the empty-notes negative WP07 explicitly closed is left open in WP05 and WP01

WP07 T037 names the trap and closes it with `test -s` + a line count + a twin grep. WP05 DoD 11 and WP01
DoD 5 carry the identical shape with no twin and no path — and on an absent file `grep -c` returns no
count and `exit=2`, which reads as satisfied.

## MAJOR — a citation "correction" that is wrong on both halves, asserted as *Verified*

WP05:308 claims the plan cites `:93-110` and that the function starts at `:88`. Measured: the plan cites
**`:90-109`** in all five places (corrected in `f08748d9a`), and the function starts at **`:90`**. Only
the `:101-108` half holds. The mis-cited-AST-span defect re-entering the tree in the opposite direction,
inside the WP whose own Reviewer Guidance says "open every one".

## Sound, and worth not re-deriving

Every load-bearing measurement re-checked exactly: `_baselines.yaml` 12 keys / 11 required / 10 read;
the two inert keys; `:214` missing-only; both hardcoded lists; and the drift (`12` vs live **9**, `193`
vs **189**). Also `_PinnedLeak(` = 12, inventory `E`-rows = 53, bounded-vs-unbounded `E` pattern 0 vs 1,
golden-count ceiling 25, `orphan_files` 0, `background.py:467` with no `sleep=`, all five `saas_client.py`
call sites, and all five `create_intent` paths absent. The **`14` collision** is correctly resolved in
WP03 T020.

## The lens's own concession, which is the most useful line in the report

> I verified perhaps thirty of the several hundred `file:line` citations across 3,994 lines of WP
> prompts. **Two of the ones I opened were wrong.** That hit rate does not license extrapolation in
> either direction, but it does mean my "verified sound" list is a sample, not a clearance.

## Post-tasks squad — feasibility lens (recorded, NOT remediated)

**WP01 and WP04 shippable today, WP03 nearly so. WP02 cannot be executed as written.**

### BLOCKER — a destructive command with no restore step

`WP02:293` prescribes `git stash && git checkout 98198e980 -- .` to reach the base tree. That
materialises base content over the **entire worktree** — `kitty-specs/`, all seven prompts, every lane
file — and **no subsequent step restores it**. The lens said it would refuse to run it. WP01 T003
already ships the correct idiom: `git worktree add --detach /tmp/wp01-base-98198e9 98198e980`. This is
the one finding here that is a safety issue rather than a quality one.

### BLOCKER — `mypy --strict` is already red on the authoritative surface, and `C-004` forbids the fix

```
$ ./.venv/bin/mypy --strict src/specify_cli/tracker/saas_client.py
:162: error: Returning Any from function declared to return "str | None"  [no-any-return]
:163: error: Returning Any from function declared to return "str | None"
Found 2 errors in 1 file
```

DoD item 8 requires "clean"; `:162-163` sit **outside** `C-004`'s enumerated permitted-hunk set. The
implementer is deadlocked — satisfy the DoD by breaching `C-004`, or fail the DoD. The likely escape is
a silent `# type: ignore`, which the same subtask's `grep -cE '^\+.*(# noqa|# type: ignore)'` then reds.
Fix: record the two as a pre-existing baseline, restate as "no **new** findings", and file per the
charter's Pre-existing Failure Reporting Rule.

### BLOCKER — `:715` confirmed independently by both lenses

`grep -c 'saas_client\.time\.sleep' test_saas_client.py` → **15**, not 14. Two prose occurrences inside
the same `:513-762` docstring — `:559` **and `:715`** — and `:715` is named **nowhere** in `spec.md`,
`plan.md`, `analysis-report.md` or any of the seven prompts. Follow T009 step 4 literally and the file
ships still claiming the pre-fix mechanism; notice `:715` and update it and you land 15 and fail the
DoD's stated 14.

### MAJOR — a cross-lane time bomb that reds only at consolidation

WP03 arm F pins four regex-only sites keyed on `(file, line, target)`, one of which is
`test_saas_client.py:559` with the **pre-fix** target. WP02 T009 step 4 rewrites that exact target. Both
WPs are green in their own lanes (both depend only on WP01); the frozenset breaks only when they land
together. WP03's Risk 4 flags a *different* WP02 coupling, not this one. Fix: key the pin on
`(file, line)`.

### MAJOR — the rest, each a wrong number that costs an implementer an hour

- **`WP05:307-309`'s "Verified" citation correction is itself wrong** — claims `:88` and `:101-108`;
  measured `:90` and `:103-110`. It is repeated in Reviewer Guidance as a worked example of *why you
  must open citations*.
- **Two different quantities both called `14`** (again): `WP02:128` counts the `:559` prose into the
  string total; `WP03:516` and `WP05:337/:370` count the origin file's `:229` by AST. WP02's own DoD 5
  contradicts `WP02:128`.
- **`WP06:159` budgets `test_no_legacy_terminology.py` at ~0.1 s; it runs 69 s** — and `WP04:185`
  already corrected this to 75–90 s. The implementer watches a healthy gate for 70 s and starts
  debugging it. `CLAUDE.md` is the source of the wrong figure.
- **`WP07:413`'s "state the magnitude: 46 sites" is unreproducible** — the prompt's own command prints
  **52**, and its own Risk 6 lists 45/46/52. No predicate in the prompt yields 46.
- **`WP07:332` cannot be run** — `<fork-owner>` is never resolved.
- **`WP02:367`'s zero-calls assertion is false at the end of T007** — `_poll_jitter_multiplier:106`
  still holds `secrets.randbelow(4001)` until T008. An implementer may "fix" it outside T007's scope.
- Four `charter.md` ranges and four `pyproject.toml`/`docs-freshness.yml` line cites are off by 1–3.
- `_PINNED_LEAKS` at `_leak_guard.py:333` is an `ast.AnnAssign`, not `ast.Assign` — an implementer
  primed by T006's language writes the wrong walk and gets zero hits.

### Verified sound, and worth not re-deriving

`98198e980` **is** the merge-base. All 24 retarget lines exact, including the `randbelow` trap
(`@patch(` `:498`, target `:499`). All five reroute sites and both do-not-touch lines exact. Every
census assertion exact. `_gate_coverage_baseline.json` 0/0, golden-count ceiling 25, `_PINNED_LEAKS` 12,
`_WATCHED_GLOBALS` 17 = 2+1+14, `check_patch_targets.py` → `All 5052 patch() targets valid.` in 5.08 s.
All of WP04's docs-gate citations. Guard-first ordering is unambiguous from six separate statements, and
the second (lint) red is correctly named as expected and attributable.

### The two lenses agreed on `:715` and on the `14` collision, and disagreed on nothing

Where they overlap they converge. The feasibility lens also caught two things the anti-laziness lens
could not: the destructive command, and the already-red `mypy` gate — both only visible by running
something.
