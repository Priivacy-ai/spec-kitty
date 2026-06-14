# WP02 Review — Cycle 1 (paula-patterns, reviewer)

**Verdict: REJECTED** — one load-bearing defect in T007. The other three helpers are excellent and require no changes.

## Summary of what passed

- `tests/_support/coverage_safety` + the home guard run green: **24 passed, 1 skipped** (`uv run pytest`).
- Coverage **98%** overall; every module ≥93% (≥90% floor met). The 4 uncovered lines in `ratchet.py` are the real-pytest `default_pytest_runner` body, correctly excluded by the injectable-runner design.
- `uv run ruff check` and `uv run mypy` on the changed files: **clean** (0 issues, 8 source files).
- Scope is clean: only owned files changed (`tests/_support/__init__.py`, `tests/_support/coverage_safety/**`, the one architectural guard). No `src/` signature changes; nothing under `tests/_support/git_template/` (WP06's territory).
- **T005 (collection-equivalence)**: non-vacuous. `assert_equivalent` diffs nodeid *sets* and raises `CollectionEquivalenceError` naming the symmetric difference; `test_assert_equivalent_different_selectors_raises_with_diff` proves the missing nodeid is named. Good.
- **T006 (ratchet)**: accepts only on N consecutive greens, stops early on first red, injectable `runner` keeps unit tests off real suites, CLI `main()` returns 0/1 for CI gating. Mirrors the run-twice ratchet convention. Good.
- **T008 (mutation / anti-vacuity)**: `assert_mutation_caught` proves the check passes on good data AND fails on a planted mutation; `test_vacuous_test_is_detected` proves it raises `MutationNotCaughtError` when the check ignores the mutated edge. Deep-copies good data. Genuinely anti-vacuous. Good.

## BLOCKING — T007 home guard is a permanent no-op (vacuous safeguard)

**Failing criterion:** T007 / C-ISO / SC-006 — "the detection must be decoupled from WP04 so it will actually *bite* once isolation lands (not a permanent skip)." It does not. The guard `test_no_real_home_mutation_under_xdist` will skip on **every** invocation, forever, regardless of whether WP04's isolation fixture is present. It therefore provides **zero** protection for the real-home-mutation guarantee it exists to enforce.

**Root cause:** `_isolation_is_active()` detects the worker home by having a probe `print("PROBE_HOME=" + str(Path.home()))` under `-n auto` and parsing the parent process's captured stdout. **Under pytest-xdist, worker `print()` output is not forwarded to the parent's captured stdout** — not with `-s`, not with `-n 1`, `-n 2`, or `-n auto`. xdist intercepts worker stdout and only relays it on a *failing* test, via a different path. So `reported` is **always** `[]`, `_isolation_is_active()` **always** returns `False`, and the guard **always** hits `pytest.skip(_SKIP_PRE_WP04)`.

**Reproduction (run from the lane worktree):**
```
# Current mechanism — PROBE_HOME never reaches the parent under xdist:
python - <<'PY'
import subprocess, sys, tempfile
from pathlib import Path
body = 'def test_probe():\n    print("PROBE_HOME=" + str(Path.home()))'
with tempfile.TemporaryDirectory() as tmp:
    m = Path(tmp)/'test_home_probe.py'
    m.write_text('from pathlib import Path\n\n\n'+body+'\n')
    r = subprocess.run([sys.executable,'-m','pytest',str(m),'-q','-s','-p','no:cacheprovider','-n','auto','--dist','loadfile'],capture_output=True,text=True)
    print('RC', r.returncode)  # 0
    print('PROBE_HOME lines:', [l for l in r.stdout.splitlines() if 'PROBE_HOME=' in l])  # []  <-- empty, always
PY
```
Result: `RC 0`, `PROBE_HOME lines: []`. The guard's own test run in this review confirms the skip (`... s` in the pytest output).

**Why this is critical (not cosmetic):** The home guard is the single executable enforcement of SC-006 / C-ISO and the stated purpose of WP02 is to make every later flip *provably* safe. A safeguard that can never transition from "skip" to "assert" is indistinguishable from no safeguard. When WP04 lands and (hypothetically) regresses, this guard stays green-by-skipping and lets the regression through — the exact opposite of "bite once WP04 lands."

**Required change:** Replace the stdout/`print()` transport with one that survives the xdist worker→parent boundary. Concretely:
- Have the probe **write `str(Path.home())` to a file** in a parent-supplied shared temp dir (e.g. `OUT / str(os.getpid())`), then read those files back in `_isolation_is_active()` (and in the mutation probe).
- This was verified to work under `-n 2 --dist loadfile`: the worker's `Path.home()` is surfaced to the parent via the file, so the real-vs-isolated comparison becomes real.
- Add a unit/integration assertion that pins the transport itself: e.g. a test proving the detection helper actually observes the worker-reported home under `-n auto` (so a future regression back to stdout-only is caught). Without such a test, the guard's skip path is untested and this exact defect recurs.
- Keep the clean pre-WP04 skip semantics, but make the skip *contingent on a working detection* (worker homes observed AND equal to real home), distinct from "detection produced nothing" — today both collapse to the same silent skip.

**Secondary (same file, please address while here):** `_isolation_is_active()` currently treats "probe produced no output" identically to "isolation absent" and skips. With the file transport, "probe produced no homes at all" should be a hard failure or an explicit, differently-worded skip — not silently conflated with "isolation not yet active" — otherwise a future breakage of the transport silently disarms the guard again.

## What to re-verify on resubmit
- The guard, run under a *simulated* isolated home (a probe whose `Path.home()` differs from real), **fails** the mutation assertion when the sentinel is written to the real home, and **passes** when isolation redirects it — i.e. demonstrate it is non-vacuous, the same bar T008 sets for collapsed tests.
- `uv run pytest tests/_support/coverage_safety tests/architectural/test_real_home_isolation_guard.py -q`, coverage ≥90%, `ruff`/`mypy` clean.
