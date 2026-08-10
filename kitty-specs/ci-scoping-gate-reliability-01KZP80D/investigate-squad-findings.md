# Tracer: Pre-Implementation Investigate-Squad Findings (2026-08-10)

Authoritative pre-implement remediation record. Three profile-loaded investigators (opus) ran the
high-risk CI-config pass on the plan + WP prompts + the ACTUAL workflow files. `/spec-kitty.implement`
and reviewers MUST honor these. They supersede any conflicting guidance in the WP prompts; the prompts
have been folded to match.

Lenses: **architect-alphonso** (GH Actions trigger/selection semantics), **reviewer-renata**
(false-green/fail-closed), **paula-patterns** (arch-guard honesty + collateral).

## BLOCKER — B-WP02: fail-closed must key on base RESOLVABILITY, not changed-set emptiness (#3147)

`docs-freshness.yml` PR trigger fires on many **non-`.md`** paths (`src/specify_cli/**`,
`pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `CONTRIBUTING.md`, `scripts/docs/**`; `:37-47`). A legit
PR touching only `src/specify_cli/foo.py` triggers docs-freshness but changes **zero `docs/**/*.md`**.

Both scripts already carry a `min_files=1` non-vacuity floor that raises on zero examined
(`relative_link_fixer.py:530-544`, `related_validator.py:118-124`, shared `scripts/docs/_guards.py:62-67`).

**Trap:** implementing tracer M5's "empty changed-set → ERROR" literally (reuse the `min_files` floor)
reds **every** non-docs-md PR that still triggers docs-freshness. The implementer's natural "fix"
(empty → exit 0) reopens the false-green M5 exists to prevent — a shallow clone / unfetched base also
yields an empty `git diff`.

**Required (WP02 T008/T009/T010/T012):**
1. Fail-closed triggers **only** on base/diff **resolvability**: capture the git subprocess
   returncode; a non-zero return (shallow clone with no `fetch-depth:0`, base sha unfetched,
   `merge-base` failure) or an unresolvable/absent base ref → **exit non-zero (ERROR)**.
2. A **successfully-computed** diff yielding zero in-scope docs files → clean **exit 0 (PASS)**. Do NOT
   route this through the `min_files` floor. Keep `min_files=1` only for the whole-tree/`push` mode
   (where zero docs genuinely means a broken scan).
3. Scope by **file**, not by hunk/line: select the changed `docs/**/*.md` files and run the existing
   **whole-file** check on each (`relative_link_fixer` reads each file whole and resolves links against
   the current on-disk tree). A line/hunk filter would miss a break on an unmodified line of a modified
   file. The link-from-unchanged-file-to-deleted-target case is inherently invisible to diff-scope and
   is delegated to the `push:main` backstop (`docs-freshness.yml:15-19`) — do NOT try to cover it by
   weakening the empty-set semantics.
4. T012 MUST add a **third** case: base-unresolvable → non-zero exit (distinct from in-scope-violation
   → red and out-of-scope-pre-existing → green). Without it the load-bearing M5 branch is untested.

## RISK — R-WP01-a: T007/M4 guards trigger-coverage, NOT marking-coverage → residual false-green (#3008)

Exit-code mechanics are SOUND (verified): `pytest <dirs> -m corpus` with zero matches → **exit 5** →
step FAILS (RED, a fail-safe). And a CLI `-m "corpus and not windows_ci"` fully **overrides** any
addopts `-m` (does not AND-combine). So a strictly-empty marked set is caught loudly.

But T007-as-worded ("every path a `@corpus` test reads is matched by the corpus globs") maps
**marked-readers → globs**. It does NOT assert the marked set **covers all actual corpus readers**. A
module that reads shipped corpus but is never given `pytest.mark.corpus` (missed in T005, or a future
unmarked test) is neither run by `fast-tests-corpus` nor checked by T007 → its regressions ship
invisibly = #3008 reopened for that module. `--strict-markers` is NOT set (pytest.ini addopts is
`--tb=short` only), so a misapplied marker won't error either.

**Required (WP01 T007):** add a marker-completeness invariant binding readers→marked: assert every
module importing a corpus-loading entrypoint (`load_built_in_graph`, `packs/built-in` fixtures, the
enumerated readers in `research/corpus-suite-inventory.md`) **carries** `pytest.mark.corpus`
(`{corpus-readers} ⊆ {corpus-marked}`), OR minimally assert the `-m corpus` collection count equals
the enumerated inventory count (a **floor**, not just `>0`). Explicitly forbid masking exit 5 in the
job body (no `|| true`, no `--suppress-no-test-exit-code`).

## RISK — R-WP01-b: Gate 0 (`on.paths` trigger allowlist) has ZERO automated guard (#3008)

`test_ci_quality_path_filters.py` `_path_filters()` (`:30-35`) reads **only** the dorny `filters`
block — never `on.pull_request.paths`/`on.push.paths`. So an implementer who adds the dorny `corpus:`
filter + group + job + gate wiring but **forgets the `on.paths` globs (T001)** gets every arch test
green and a workflow that **never triggers on a corpus-only PR** — #3008 inert. Gate 0 is the decisive
gate and it is currently unguarded.

**Required (WP01 T006/T007):** the completeness guard MUST assert every corpus glob is present in
**BOTH** `on.pull_request.paths` AND `on.push.paths`. **YAML 1.1 gotcha:** `yaml.safe_load` parses the
top-level `on:` key as boolean `True`, not `"on"` — access `data[True]["pull_request"]["paths"]` (or
use a bool-preserving loader). A naive `data["on"]…` guard crashes or asserts nothing.

## RISK — R-WP01-c: 4 co-evolution guards the WP omits; a PARTIAL 5-edit reds an unnamed guard

The corpus wiring (on.paths + `changes.outputs.corpus` + dorny `corpus:` filter + `fast-tests-corpus`
if-gate + `JOB_GROUPS` row + `quality-gate.needs` edge + `-m corpus`) is a single **atomic** set. Any
subset reds a guard the plan doesn't name:
1. `tests/architectural/test_workflow_coherence.py` (`test_job_groups_table_equals_parsed_if_gating_live`,
   `:266`) — FR-011 pins `JOB_GROUPS == parsed job-if: gating` (exact `==`). Adding the if-gate WITHOUT
   the JOB_GROUPS row (or vice-versa) reds HERE (not `test_suite_jobs_gate_blocking`, which N2 names).
2. `tests/architectural/test_src_filter_coverage.py` — `:180` every named group must gate ≥1
   test-running job (dorny `corpus:` filter without the `fast-tests-corpus` if-gate referencing
   `corpus` reds here); `:155` `unmatched` enumerates EXACTLY the src-backed groups — **this** guard
   (not the census) reds if `corpus` is wrongly added to the unmatched loop.
3. `tests/architectural/test_marker_job_completeness.py` (`:221/:269`) — every `pytest.ini`-registered
   marker must be ROUTED-BY-MARKER / ROUTED-BY-PATH / reasoned-invisible. A registered `corpus` marker
   is healthy ONLY because `fast-tests-corpus` runs `-m "corpus and not windows_ci"`. **This guard is
   the teeth behind M1** — running whole dirs without `-m corpus` reds it (`marker 'corpus' has NO CI home`).
4. `tests/architectural/test_ci_collection_completeness.py` — belongs in the run set (implied by SC-004
   but the WP named only `test_ci_quality_path_filters`).

**Required:** add all four to the WP's mandatory local run set; state the atomicity explicitly.

## BLOCKER — B-WP01: T005 `pytestmark = [pytest.mark.corpus]` CLOBBERS existing markers on 6/7 readers

Nearly every named reader ALREADY has a load-bearing `pytestmark`:
- `test_wp_owned_files_no_kitty_specs.py:12` → `fast`
- `test_no_tracked_test_feature_missions.py:10` → `[architectural, git_repo]`
- `test_events_tracker_public_imports.py:26` → `[architectural]`
- `test_verdict_seam_census.py:165` → `architectural`
- `contract/test_example_round_trip.py:73` → `[contract, fast]`
- `charter/synthesizer/test_manifest.py:44` → `[unit]`
- `integration/test_mission_review_contract_gate.py:38` → `[integration, git_repo]`

A literal `pytestmark = [pytest.mark.corpus]` OVERWRITES these, dropping `architectural`/`contract`/
`unit`/`integration`/`fast`/`git_repo` → cascade of reds: shard bucketing
(`conftest._apply_shard_markers`), `test_marker_job_completeness` (contract is HARD-asserted
routed-by-marker), and `test_ci_collection_completeness` orphans (job-collection changes).

**Required (WP01 T005):** **APPEND**, never replace — `pytestmark = [pytest.mark.architectural,
pytest.mark.corpus]`, `[pytest.mark.fast, pytest.mark.corpus]`, etc. Add a fresh `pytestmark` only
where a module has none. Rewrite "one line per module" as "extend the existing `pytestmark` list".

## FACTUAL FIX — T003 rests on a phantom default `-m` addopts

Both alphonso and renata: there is **no** default `-m` in the active pytest config. `pytest.ini`
addopts is `--tb=short` only; the `-m "not slow and … and not architectural …"` list lives in
`[tool.mutmut] pytest_add_cli_args` (`pyproject.toml:406,422-431`) and is passed **only when mutmut
forks pytest** (note at `:453-455`) — plain pytest/CI is unaffected. So `-m "corpus and not
windows_ci"` is the **sole** marker filter, no override contest. Correct the T003 "-m override caveat"
so a reviewer checking `pyproject.toml:422` isn't misled. Still run `--collect-only -m corpus` to
confirm the marked set is non-empty (defense-in-depth; zero → exit 5 → RED anyway).

## SOUND (confirmed, no action) — for the record

- The `unmatched`/`run_all` catch-all is genuinely **src-only** (`any_src` matches `src/**` only,
  `:475-476`; `unmatched` = `any_src && !matched-over-src-backed`, `:530`). A corpus-only PR →
  `any_src=false` → `unmatched=false` → runs ONLY `fast-tests-corpus` (+ always-on jobs), NOT the full
  suite. Corpus resolves `true` independently via its own dorny filter, exactly like `docs` (`:181`).
- `fast-tests-corpus` `if: always() && (corpus=='true' || event==push)` is a correct clone of
  `fast-tests-docs` (`:1811`); NOT in `DRAFT_GATED_JOBS` → normally-blocking on drafts too.
- quality-gate: a corpus **failure** → FAIL always (`quality_gate_decision.py:248`); a legitimate skip
  on a non-corpus PR → neutral (`:265`); an **improper** skip on a corpus PR → FAIL (`:252-260`). Full
  false-green closure needs BOTH the `quality-gate.needs` edge (makes failure blocking) AND the
  `JOB_GROUPS["fast-tests-corpus"]=["corpus"]` row (makes improper-skip blocking).
- M2 census: stays green untouched **provided every corpus dorny glob stays non-src** — an `src/**`
  glob in the corpus filter would grow `mapped_src_dirs` and red `test_census_mapped_dirs_matches_live_derivation`.
  Complete the M2 note: "do NOT touch the census AND keep every corpus glob non-src".
- New `test_ci_corpus_trigger_completeness.py` auto-shards via `_arch_shard_map.py` `default_fallback=True`
  (no manual `_ARCH_SHARD_N_FILES` edit). `test_marker_baseline.txt` unaffected (only slow/stress/quarantine).
- WP02 blocking/non-blocking kept straight (docs-freshness NOT required; corpus IS blocking). Read
  "blocking" in WP02 as **job-step-failing**, never "gates merge" (required check = `["drift-detector"]`).
- WP02 push routing sound: `push:main` (`:48-49`) is unfiltered, no `base.sha` → whole-tree mode with
  `min_files=1` intact. Retain as-is; scope the relaxed emptiness semantics to the PR/diff path only.

## Verdict
Mechanism is sound and correctly clones the `docs` precedent. Two BLOCKERs (WP02 fail-closed
resolvability; WP01 pytestmark clobber) + three RISKs (WP01 marker-completeness false-green, Gate-0
unguarded, 4 unnamed co-evolution guards) folded into the WP prompts before implement. M4 reworded to
the honest curated form (glob-vs-glob roots + reader⊆marked pin); the literal "paths a test reads" is
not statically computable.
