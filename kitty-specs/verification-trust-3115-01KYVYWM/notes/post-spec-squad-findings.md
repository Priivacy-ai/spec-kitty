# Post-specify adversarial squad — findings and dispositions

Point-cut: immediately after `specify`, before `plan`. Four lenses, dispatched in parallel,
profile-loaded, read-only, all on `opus`. Question: *does this spec, implemented exactly as
written, actually make the verification trustworthy?*

| Lens | Profile | Verdict |
|---|---|---|
| Anti-laziness / fakeable criteria | `reviewer-renata` | REJECT |
| Structure / seams / layering | `architect-alphonso` | REQUEST CHANGES |
| Scope / sequencing / tracker hygiene | `planner-priti` | REQUEST CHANGES |
| Live evidence / technical truth | `debugger-debbie` | REJECT AS FRAMED |

## The finding that re-shaped the mission

**`#3115`'s CLI half is a console render-width defect, not global-state pollution.** Raised by
`debugger-debbie` from the live CI log (run `30622853036`, job `fast-tests-cli`), then
adjudicated by a dedicated measurement pass before any spec change was made.

Measured on base `bb2020fea9`, single file, single process, no xdist, no ordering:

| Run | Env | Count line |
|---|---|---|
| baseline | none | `4 passed in 54.45s` |
| falsifier | `TERM=dumb FORCE_COLOR=1` | `1 failed, 3 passed in 57.54s` (×3, deterministic) |
| control | `+ TTY_COMPATIBLE=0` | `4 passed in 52.78s` |
| discriminator | `TERM=dumb` alone | `4 passed` — so `FORCE_COLOR` is required |

Mechanism: `rich.console.Console.size` returns `ConsoleDimensions(80, 25)` from the
`if self.is_dumb_terminal:` branch, which sits **above** the `COLUMNS` read. `is_terminal` is
true whenever `FORCE_COLOR` is set non-empty. The tests set `COLUMNS` to 220/240 and it is
never consulted. The Project column is `overflow="fold"` (`sync.py:1440`, deliberately, so
identities are never ellipsized), so a 36-char uuid folds across two lines and stops being a
contiguous substring.

**Decisive evidence:** the local falsifier's assertion repr is **byte-identical to CI's**, 240
chars, for both victim files. CI's own rendered `Queue` row measures exactly 80 characters.
This is measurement, not inference.

**The journal is populated** — 14 events retained, all four rows present, counts 7/4/2/1. The
issue's "reads an EMPTY journal" premise is falsified.

Two corrections to the reviewer's own framing, both load-bearing:
- **Stripping newlines does not repair the assertion.** The fold puts the rest of the row
  between the two uuid fragments, so no whitespace normalisation rejoins them. A
  "flatten the output" fix does not work.
- `SILENT`/`OPTED_OUT` pass at width 80 only **incidentally**, via an un-tabled warning
  paragraph. `CONSENTED` has no such paragraph, which is why exactly one of three loop
  iterations fails, and always the first.

**Still open, stated plainly:** what makes rich's `is_terminal` true on the runner. The
workflow sets no `FORCE_COLOR`/`TERM`/`TTY_COMPATIBLE`. `is_dumb_terminal` is the only
surviving route to exactly 80 (the only explicit width assignment in the repo is
monkeypatch-scoped and sets 10 000), but the trigger is unidentified. Nothing was tested
under xdist.

**Operator decision:** re-scope the `#3115` CLI half to the measured cause. Keep a narrowed
isolation requirement for the sync half. `#3113` and the timeout work unchanged.

## Retracted during the squad — recorded so it is not re-derived

**"Commit `4f8e4ca78` does not exist."** It does: `4f8e4ca78172288ac57664a0479ba30a61c17629`,
"harden #3030 sync CLI tests against cross-worker scope-cache pollution", touching all five CLI
test files. It lives on PR #3098's branch (`origin-pr/3098`), not on `main`; the fold-merge
landed the same content as `578a659162`. The claim arose from a local repo that had not
fetched PR refs — the same failure shape as the stale base below. **The issue's citation is
sound and its premise is properly grounded.**

This sharpens rather than weakens the width finding: `4f8e4ca781` hardened the token-manager
global, CI stayed red on the same tests, and the width mechanism explains why — the reset was
aimed at a global that was never the cause.

## Base-commit correction

The mission was created and first measured at `9189cf2b36`, which was **7 commits behind**
`Priivacy-ai/main`. Fast-forwarded to `bb2020fea9`. The 7 commits are charter-pack and
`context.py` decomposition work and touch **none** of this mission's files (egress guard,
`_baselines.yaml`, `pytest.ini`, `console.py`, `sync.py`, all seven victim test files are
byte-identical across the gap; `rich` unchanged). The falsifier was **re-run** on the new base
rather than inferred to still hold.

This is the friction record's first entry — *"cut from a commit predating the mission's own
acceptance pins, so the lane reported a clean 0-failure baseline"* — reproduced by this
mission's own orchestrator. Hence NFR-009 below.

## Confirmed findings and dispositions

### Convergent (two or more lenses, independently)

**C1 — the mandated bite-test certifies a blind matcher.** (`renata` + `alphonso`)
`poster(url, body, hdrs)` passes because the parameter is *literally named* `url`, already in
`_URL_ARG_NAMES` (`test_egress_consent_boundary.py:197`); `_attr_tail` returns `node.id` for a
bare `Name` (`:266-272`). Rename to `u`/`target` and the matcher goes blind while the bite-test
stays green — `#3113`'s own defect reproduced inside its own fix.
→ **Accepted.** At least two positional cases, one with a `_URL_ARG_NAMES` identifier and one
outside it; the adoption gate is the **second**.

**C2 — the tightening is keyed on the wrong property.** (`alphonso`, supported by `renata`)
"≥3 positional args whose first looks like a URL" keys on the identifier the author chose.
C-006 forbids the guard being *callee*-name-shaped; this is the same failure in a different
subject. A sink-shaped alternative exists: **"transport injected as a parameter"** is a
structural AST property — the callee is a bare `Name` resolving to a parameter of the enclosing
`FunctionDef` — decidable without any author-chosen word, and `_classify` already has the
bare-`Name` branch to hang it on (`:316`).
→ **Accepted.** Structural rule measured first; a tightening that cannot be expressed without
consulting an author-chosen identifier is rejected regardless of its false-positive count.

### Critical, single-lens, confirmed

**C3 — the isolation seam already exists 22 times.** (`alphonso`)
`grep -c "def _isolated_home" tests/` = 22 separate definitions. Ten call
`reset_journal_cache()`, three call `reset_token_manager()`, the rest neither. `578a659162`
copied its hardening into five files rather than one owner. FR-005 added a detector on top of
the pile; FR-007 offered keep / keep-with-docstring / delete with **no hoist-to-one-owner
branch**.
→ **Accepted.** A convergence FR with a counted acceptance (N definitions before, M after).
House precedent is root-scoped and already in the tree: `tests/conftest.py:253`
(`_isolated_worker_home`, autouse, per-worker) and `:307-329` (`_plain_cli_console_seam` —
set/yield/restore in `finally`, C-002 already implemented).

**C4 — the issue-matrix will gate the wrong issue.** (`priti`)
`detect_issue_references` (`issue_matrix.py:88-95`) requires `^`, whitespace, `(` or `[` before
the `#`. Every `#3115`/`#3113` in the spec is inside backticks. The sole detected reference is
`#3030`, in a quoted commit message — so the mission's own issues get no row and no
completeness gate, while `#3030` gets a row that must be terminal at `done`, which is exactly
the verdict FR-007 says cannot yet be given. Also: `issue-matrix.json` is canonical now
(`issue_matrix.py:9-11`); no `.md` is emitted.
→ **Accepted.** Bare unbackticked references added; three rows hand-authored; the timeout work
rides `#3115`'s row with `evidence_ref` naming the timeout FRs — no synthetic row.

**C5 — no stall policy; bounded work is hostage to an open-ended investigation.** (`priti`)
If the hunt does not converge, `#3115` stays `in-mission`, which is rejected at `done`, and the
finished `#3113` and timeout work cannot land either.
→ **Accepted.** Stated search budget; on exhaustion `#3115` resolves `deferred-with-followup`
against a narrowed successor issue inheriting the inventory and the harness's negative result.

**C6 — FR-001's polluter was unconstrained.** (`renata`)
A purpose-written probe file satisfied every clause. FR-003 already owns the synthetic probe,
so both were closable with one artefact and one then proved nothing.
→ **Largely superseded by the re-scope** (the reproducer is now two environment variables), but
the constraint is retained for the sync half.

**C7 — victory was declarable without identifying the cause.** (`renata`)
FR-003 permitted "recorded as unproven" while FR-008/SC-005 supplied a green shard — the exact
path that produced `578a659162`.
→ **Accepted.** Explicit blocking exit clause.

**C8 — `xfail` is non-strict.** (`renata`)
`pytest.ini` sets no `xfail_strict` and `pyproject.toml:185-189` forbids a
`[tool.pytest.ini_options]` block. A "pinned" hole that starts passing reports `XPASS` and the
run stays green — the FR's stated mechanism does not exist.
→ **Accepted.** `strict=True` required explicitly.

**C9 — `Queue 0 event(s)` cannot discriminate a red.** (`debbie`, verified independently)
Rendered unconditionally from `OfflineQueue().size()` (`sync.py:5182-5185`); these tests seed
the journal, never the offline queue, so it appears on the green path. FR-001 accepted a
non-discriminating string as "CI's own failure text".
→ **Accepted.** Struck from FR-001, the edge case, and SC-001.

### High, accepted

- **H1** (`priti`) — **stale-base rule missing.** NFR-002 closes the import-path trap;
  the base-commit version was unguarded. → **NFR-009**: every baseline states the commit it was
  taken at and its lane's merge-base; a lane merges the mission branch before its first
  measurement.
- **H2** (`priti`) — **two required artefact writes land in `kitty-specs/`**, which
  `commit_guard.py:86-88` forbids from lane branches, and FR-010's target is a *closed*
  mission's dossier. → Inventory relocated out of the dossier; the cross-reference made
  one-directional.
- **H3** (`priti`) — **critical path stated backwards.** FR-001's reproducer *is* FR-002's
  output. → Chain restated FR-004 → FR-002 → FR-001 → FR-003.
- **H4** (`priti`) — **FR-005 coupled to the least certain FR.** Scoped to FR-004's inventory it
  needs no culprit and survives a failed hunt. → Re-scoped.
- **H5** (`priti`) — **the pre-review gate's serialisation lock degrades to none after 5s**
  (`pre_review_gate.py:256`, "fallback-to-run"). Gate runs here take ~2 min, so the second lane
  to transition runs anyway, recreating the 16 recorded false reds. → Lane `for_review`
  transitions taken one at a time by the orchestrator; any gate red re-measured serially.
- **H6** (`renata`) — **FR-015's red-first is a threshold flip**, not a consequence. → Red-first
  is a non-terminating-loop plugin mutant; the test must red **on the counter, naming the
  count**, and specifically not on `Failed: Timeout`.
- **H7** (`renata`) — **FR-004's acceptance dropped the dependence column**, leaving it closable
  by grep. → Fourth mandatory value per entry, with per-bucket counts.
- **H8** (`renata`/`alphonso`) — **FR-005 detect-vs-repair ambiguous**; the repair reading makes
  the guard silence what it guards. → Guard **detects and fails; it does not repair**.
- **H9** (`alphonso`) — **FR-012's FP-only acceptance** admits a rule that flags nothing. →
  Report new sites added by the tightening separately from pre-existing; a zero delta is
  written down as "only demonstrated bite is the synthetic case".
- **H10** (`debbie`) — **`--cov` omitted from the distribution enumeration.** Both shard
  commands carry it (`ci-quality.yml:1132`, `:1543`); it installs a per-thread trace function,
  changing thread scheduling, and inflates the `--durations` output FR-013 derives its value
  from. → Added to NFR-001; FR-013 must state whether coverage was on.
- **H11** (`alphonso`/`renata`) — **timeout blast radius.** `testpaths = tests` means an
  `addopts` default caps every invocation of this ini. 46 tests are marked `slow` (defined as
  ">30 seconds") against only 15 `@pytest.mark.timeout` sites, and the opt-in selections are
  ones FR-014's regression clause structurally cannot observe. → Value derived from every
  selection that inherits the ini, or the flag scoped to the fast job command lines; FR-014
  enumerates which jobs inherited it and which did not run, with collected counts.
- **H12** (`debbie`) — **the sync shard may not run at all.** `fast-tests-sync` was *skipped* on
  run `30622853036` (path filter `needs.changes.outputs.sync`). A test-only branch gets a green
  `fast-tests-cli` and no sync shard. → SC must quote the job conclusion, not the workflow's.

### Medium, accepted without further comment

`renata` M1–M8, `alphonso` M6–M7, `priti` M6–M7: NFR-006 inverted so coverage is the invariant
and cost changes shape; guard reports what it did not watch; deliverable-vs-FR width mismatch
resolved; artefact paths named in the spec; worker count quoted from CI's own xdist header
rather than inferred from the runner label; `#3115` scope additions recorded as operator
decisions; branch name corrected to the `lanes` topology form.

## Deliberately not accepted

- **`renata` NOTE on `_baselines.yaml:368`** — `egress_allowlist_files: 28` is count-anchored,
  so a substitution passes silently. Real, **pre-existing**, out of scope. Follow-up candidate.
- **Running the full enumerated pairwise search anyway** — offered to the operator as an option
  and declined in favour of the measured cause. The null result it would produce is not worth
  the wall-clock.
- **Chasing the `is_terminal` trigger as mission scope** — offered and not selected. Recorded
  as the mission's principal known unknown and carried into the PR's limits section.

## Where the spec was already right — conceded by the lenses

- FR-001's explicit exclusion list (a `TypeError`, fixture error, collection error or empty
  output file do not satisfy it) directly implements the standing rules.
- FR-002's requirement to run the harness against the **known** `reset_adapters()` pair first —
  "control your diagnostic", applied unprompted.
- C-005 forbidding `-p no:randomly` for *either* colour — the reason `#3030`'s sweep missed the
  `reset_adapters()` leak.
- Refusing to name a favourite culprit global. That discipline is what left room for the width
  finding to be heard instead of pattern-matched onto a leaked global.
- `#3113`'s three FRs map one-to-one onto the issue's three Done-when clauses, nothing added,
  nothing dropped.
