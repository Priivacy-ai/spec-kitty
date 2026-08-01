# Standing rules — carried into every subagent brief on this mission

Every rule here comes from a measurement that lied during the `#3030` mission. The full
record is `kitty-specs/journal-project-consent-3030-01KYKWQS/tracer-tooling-friction.md`.
Quoted entries are cited by their heading there.

## Measurement

- **Never pipe a suite whose exit status you intend to trust.**
  > "`uv run pytest … 2>&1 | tail -18` reports **`tail`'s** exit status, not pytest's. So
  > 'exit code 0' from such a pipeline is **not evidence of a pass**… The `N passed` line is
  > the evidence; the exit code is noise."
  > — *`pytest | tail` throws away pytest's exit status*

  Write full output to a file and read the tail of the file, or check `${PIPESTATUS[0]}`.
  **An empty output file is no measurement** — `tail` buffers until the pipeline ends.

- **A killed run is neither a pass nor a fail. Re-run it narrowed; do not explain it.**
  > "`exit 143` on a `timeout N ... | tail` pipeline is **triply ambiguous** — the timeout
  > firing, an external kill, or `tail` being signalled. None of the three is a test failure…
  > A run that was killed was not 'a run that failed', and it was also not 'a run that passed
  > under contention'. It is *no measurement*."
  > — *Attributing a killed run to contention is itself an unverified attribution*

  Check elapsed time against the `timeout` value to attribute. **Narrow the scope instead of
  raising the timeout.**

- **Measure in a `git worktree` pinned to a commit — AND set `PYTHONPATH=$WT/src` or use a
  dedicated venv.**
  > "`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` contains the
  > **absolute path of the main checkout**… So pytest run *inside* a throwaway worktree, using
  > the main `.venv`, imports the **live tree**, not the worktree's source. **This makes the
  > failure worse than no isolation at all**, because the isolation *looks* performed."
  > — *CRITICAL ADDENDUM: an editable install defeats worktree isolation silently*

  A before/after across two pinned worktrees without this reports "identical" as a tautology.
  Sameness conclusions are the ones this defect manufactures; difference conclusions are safe.

- **Pin the interpreter, not just the source path.** `PYTHONPATH=$WT/src` fixes which *source* is
  imported. It says nothing about which *interpreter* runs or which *plugins* load. Two interpreters
  are reachable here and they are not interchangeable — measured by enumerating each one's `pytest11`
  entry points, which is the registry that actually produces the `plugins:` header:

  | Interpreter | pytest | `pytest11` registry |
  |---|---|---|
  | `.venv/bin/python` | **9.0.3** | anyio, asyncio, base_url, playwright, pytest_cov, respx, **timeout**, **xdist**, xdist.looponfail |
  | `/usr/bin/python3` (bare `python3`, user-site) | 9.1.1 | anyio, respx |

  **Use `.venv/bin/python -m pytest`.** Not a preference: `pytest-timeout` and `xdist` exist **only**
  in the venv (`import pytest_timeout` under `python3` raises `ModuleNotFoundError`), so any WP whose
  requirement is a timeout backstop or a shard is not merely better measured there — it is
  **unmeasurable** anywhere else. The venv is also the CI-representative environment; the system
  interpreter is the degraded one.

  **Quote `sys.executable` alongside the `plugins:` header** whenever a result is load-bearing.
  On this mission the header is the only reason the substrate was recoverable at all: WP01's
  implementer quoted eight plugin names and its reviewer quoted two, same file and same commit, and
  the mismatch sat unnoticed until someone enumerated the registries. Read correctly it is a
  **cross-environment replication** — the same red, the same counts, on both interpreters.

  **A corrected diagnosis, recorded because the first one was wrong and briefs are copied verbatim.**
  This rule was first written claiming *every* measurement had run on the system interpreter, on the
  strength of `which python3`. That conclusion was **inverted**: `which python3` says what a bare
  `python3` resolves to, not what any agent actually invoked, and the plugin headers disprove it when
  read the right way round. The implementers ran the venv; the reviewers ran the system interpreter.
  So the side to re-measure, if any, is the **reviewer** side — the opposite of what the first version
  of this rule implied. Caught at the `/analyze` gate, which blocked on it.

  **What it explains, still true under the corrected reading**: `typer` resolves from user-site for
  `/usr/bin/python3`, so a test isolating `HOME` breaks that resolution and its subprocess dies with
  `ModuleNotFoundError: No module named 'typer'`. Under the venv `typer` is inside the venv and
  isolation cannot reach it. A full `tests/architectural` run showed **19 failed / 26 errors** on that
  basis — a **harness artefact of the degraded interpreter, not pre-existing failures**, and not an
  issue to file. The earlier attribution to a hardcoded `/usr/bin/python` in the tree was also wrong:
  those literals are mock fixture strings, the subprocesses launch `sys.executable`, and **a `PATH`
  change cannot alter an already-running interpreter's `sys.executable`** — so the control that was
  run could not have discriminated. The control that does is printing `sys.executable` and
  `sys.prefix` from inside the run.

- **Read the failure text, not the tally.** A tally moving 2 → 3 can be progress; reds that are
  `TypeError`s from a changed signature are not evidence of the defect under test.

- **Print the input count alongside any "all checks passed".** A gate that ran on zero files
  passes vacuously.
  > "Both WP11 and WP12 transitioned with `Pre-review regression gate: no_coverage — no changed
  > files detected for this WP — skipping the gate cheaply`… a mechanism reporting success for
  > having done nothing."
  > — *WPs created after planning have no lane, so two gates silently no-op*

## Proof

- **Red first**, and make the red the *consequence*, not a boolean. A fix that cannot be shown
  to fail before it is applied is not a fix.

- **Include a positive control that must pass**, or you cannot distinguish "nothing broke" from
  "the harness never ran the code".

- **Any assertion of absence must establish why the thing would otherwise have happened.**
  > "Both tests were asserting *absence of an effect*, and a new refusal produces that absence
  > just as well as the behaviour under test… **Any test whose assertion is 'X did not happen'
  > needs to state why X would otherwise have happened**, or a new short-circuit upstream
  > silently adopts it."
  > — *A fake green that only surfaced when the gate arrived*

- **Control your diagnostic**: run any probe against a case whose answer you already know
  before trusting what it says.
  > "The answer was **0 gates** — which… reads as a serious finding… Before reporting it, the
  > agent ran the identical probe against [a file] definitely covered. **Also 0.** The probe
  > was invalid; the file was fine."
  > — *Control your diagnostic, not just your test*

- **Mutations as pytest plugins loaded via `PYTHONPATH`, never source edits**, and never source
  edits during a verification run.

## Five recorded ways a mutation silently lies — check each

1. **The architecture moved and the patched gate became a redundant second** → all-green, reads
   as "your pin is fine".
2. **The reds are `TypeError`s from a changed signature**, not assertion failures.
3. **The mutant hard-codes a value the tests vary** → no-ops for exactly the tests most likely
   to catch the defect.
4. **The branch is unreachable on the local interpreter and live on CI's** (3.11/3.12 vs 3.14).
   Zero binds means *your environment differs*, not *the code is dead*.
5. **`from X import f` rebinds by value** → patching the defining module leaves the *deciding*
   module inert.
   > "The preflight mutant reported **34 binds — but split `owner=20, preflight=14`**. That
   > split is the finding… **Rule: patch every name the symbol is reachable by, and report the
   > per-site split.** A single aggregate count cannot distinguish 'both sites mutated' from
   > 'one site mutated, the other inert'."
   > — *Fifth rot mode*

Also: **assert the mutation took effect** — a plugin patching a renamed or relocated symbol
silently does nothing, and a no-op mutation reads as a passing gate.

## Hygiene

- **Explicit-path staging. `git add <paths>`, never `git add -A`.**
  > "The orchestrator ran `git add -A && git commit` for a dossier-only change while one of them
  > had uncommitted source edits in flight. Result: commit `2e6aa1d78f`, whose message describes
  > un-marking T004/T005, actually carries eight source files plus a test."
  > — *Concurrent implementers in one working tree*

  13 files were lost this way. Also: `git status --short` before every commit; never `reset`,
  `checkout --`, `stash` or `rebase` on a shared branch — report instead.

- **`ruff format` is NOT clean on this repo** (`line-length = 164`); running it reflows other
  people's committed work. **Only `ruff check` is meaningful.**

- **One live agent per file.** Each brief names the paths other agents hold.

- **Do not parallelise `tests/sync` and `tests/cli` pytest sessions on one machine** — they spawn
  real daemons and `pgrep`/port-scan, so sibling sessions reap each other's. 16 false reds.
  **Fan out the coding, serialise the sweeps.**

## Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green

- `tests/architectural/test_tid251_enforcement.py` (4 tests, proven pre-existing on `origin/main`
  in a pinned worktree)
- `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`
- two `test_safe_commit_cmd::…_3033`
- `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`
- `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load)
- Subprocess daemon tests reporting `ModuleNotFoundError: No module named 'typer'` — a user-site
  install interacting with `HOME` isolation. Environmental.
