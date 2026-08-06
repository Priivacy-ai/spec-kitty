# WP08 — review cycle 1 (reviewer-renata)

**VERDICT: REJECT (1 blocker).** One line of one artifact. Every substantive claim in WP08 was
independently verified, and several verified *stronger* than claimed. Baseline ref for everything
below is `96494e5ec` (`git merge-base HEAD main` = `git merge-base HEAD upstream/main`).

---

## BLOCKER

**[BLOCKER] `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/contracts/integration-verification.md:473`
— reintroduces the BARE literal token `#3113`, minting an unresolvable issue-matrix row and blocking
the mission's own approval gate.**

The token sits inside the fenced xfail quote in §6:

```
      — #3113, FR-015 non-adoption decision, pinned red deliberately
```

The mission had already identified this exact trap and defended against it, in writing, twice:

- `spec.md:576-577` — *"`` `#3113` `` (\"the rejected predicate\") is plan-only provenance, absent from
  this spec and from `research.md`; **keep it backticked so it does not mint an unresolvable
  issue-matrix row**."*
- `analysis-report.md:293` — *"Already backticked once this mission to stop it minting an unresolvable
  issue-matrix row."*

Provenance measured: `git grep -n '3113' 68643e23a~1 -- kitty-specs/meta-fail-closed-3162-01KZ7FSQ/`
returns only those two defended, backticked occurrences. The bare token is **WP08-introduced**.

Consequence, reproduced:

```
$ spec-kitty agent tasks move-task WP08 --to approved --mission meta-fail-closed-3162-01KZ7FSQ
Error: ERROR: issue-matrix.md has unresolved entries. Fill in verdicts before approving.
Missing rows: #3113
```

`issue-matrix.json` carries 10 rows — `#1848 #1931 #1933 #2034 #2804 #3138 #3155 #3162 #3231 #3232` —
and none is `#3113`. This is the only thing standing between the mission and its PR.

**Fix — either is sufficient:**

- (a) backtick the token in the fenced quote at `:473`; or
- (b) add an `#3113` row to `issue-matrix.json` with an out-of-scope / already-fixed verdict. It is a
  pre-existing `FR-015` non-adoption xfail in `tests/architectural/test_egress_consent_boundary.py`,
  a file this mission never touched.

**Why I did not force past it.** WP08's own governing standard is that a gate is *satisfied*, never
regenerated or forced green — the standard it applied correctly to `_gate_coverage_baseline.json`,
`_baselines.yaml` and `_golden_count_baseline.json`. Forcing this one would leave a permanently
unresolved accountability row in the mission record at the moment it goes to PR. I hold WP08 to its
own standard. (By contrast, forcing `for_review` past the *unchecked-subtask* guard was correct and I
endorse it — marking T047/T048/T050/T051/T052 done would have been a false record.)

---

## MINOR

**[MINOR] `tests/specify_cli/context/test_wp03_row08_resolver_fail_closed.py:19-20` — false statement
in committed source: "No such class exists in `test_resolver.py`".**
`class TestResolveContext:` **does** exist, at `tests/specify_cli/context/test_resolver.py:125`. The
substantive correction is right — the *method* `test_missing_meta_json_raises` (`:251`) is enclosed by
`TestResolveContextErrors` (`:215`), not by `TestResolveContext`. Only the justification sentence is
wrong. Note the artifact says this was "verified by listing every `class` and `def` between `:215` and
`:255`" — a window that structurally could not see `:125`. That is the uncalibrated-probe error the
ledger records twice for F10.
**Recommendation:** say "no such *method* exists in `TestResolveContext`" (or "the method is not in
`TestResolveContext`").

**[MINOR] `contracts/integration-verification.md:518` — same false claim in the terminal evidence
artifact.** Same fix.

**[MINOR] `contracts/integration-verification.md` §0 — does not name the DoD contradiction it
creates.** The DoD says the artifact and the script are *"the only two files this WP wrote; no source,
no test"*. WP08 wrote/modified `docs/changelog/CHANGELOG.md`, `tests/_next_shard_map.py`, four test
files, one new test file, one baseline file, `residual-ledger.md`, and another WP's evidence file. The
operator rescope *necessarily* supersedes that clause (F3 cannot be closed without a new test file),
and §0 is otherwise scrupulous — but a reader checking the DoD line by line finds an unexplained
contradiction. **Recommendation:** add one line to §0 stating that the rescope supersedes the DoD's
write-surface clause, and list the surface actually written.

**[MINOR] `owned_files` left unwritten.** §5.6's argument for not authoring
`scripts/verify_meta_fail_closed_integration_3162.py` is sound and I verified it: I ran
`scripts/verify_meta_routing_manifest_3162.py` myself and it emits every required output (input file
count, routed, inline, both floors read off the gate, the derived band, the `pending-batch-a` delta
with the `:185` legend exclusion shown as the control, the tree and `PYTHONPATH`), `exit=0`,
`VERDICT: PASS`. Authoring a second counter would have violated the `NFR-002` clause T049 step 9 itself
cites. The residue is that WP08's declared ownership surface is empty. The clean resolution is to point
`owned_files` at the existing script — which WP08 could not do without editing `tasks/*.md`, forbidden
by its own DoD. Orchestrator decision; F16 family.

**[MINOR] `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP03-evidence.md` amended after WP03's
approval.** The three citation corrections are each correct (`safe_commit_cmd.py:306` verified as the
single `except (FileNotFoundError, ValueError)` match; `resolver.py:86` verified as the
`raise MissingIdentityError(msg)` line) and each carries an inline "applied by WP08" attribution
stamp, which is the right way to do it. Flagging the cross-WP write boundary only.

**[MINOR] `tests/mission_runtime/test_wp04_routed_call_counts.py` — escape-hatch marker duplicated per
site.** The marker text appears 4× in that file and 2× in
`test_wp04_sc007_guard_and_handler_contract.py`: once as a block comment above the assert and once
inline on it. `is_escaped` reads only `source_lines[node.lineno - 1]`, so only the inline copy is
load-bearing; the block-comment copies are audit noise that will over-count any
`grep -c 'golden-count: cardinality-is-contract'`. Cosmetic; the gate's own site count is correct (3).

**[MINOR] `docs/changelog/CHANGELOG.md` — `coordination/surface_resolver.py` described as "file-local
… at the routed sites themselves".** It is a direct *caller* of the routed `read_primary_meta`, not one
of the 13 routed sites. The grouping's substance (adjacent-to-the-call vs several-hops-away) is right;
the wording overstates it slightly.

---

## What I verified GREEN — reproduced, not accepted

### The refreeze — LEGITIMATE

```
pre-WP08 (68643e23a~1) node-ids : 442
HEAD node-ids                   : 448
DROPPED (in pre, not post)      : 0
ADDED   (in post, not pre)      : 6
ADDED not from row05's file     : 0
git diff --numstat              : 7   0
```

All six added node-ids are `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py::test_census_row05_*`.
The 7th insertion is the provenance comment. The file's **pre-existing** header (unchanged at
`68643e23a~1`) mandates exactly this path: *"Regenerate ONLY with an explicit provenance comment
(data-model E3) when a WP legitimately changes this job's selection"* — and WP08 added one. Coverage
gained, no gap accepted.

The other three baselines, sha256 at pre-WP08 / HEAD / worktree:

```
tests/architectural/_gate_coverage_baseline.json   1120708212…  BYTE-IDENTICAL (all three)
tests/architectural/_baselines.yaml                ec56126b4b…  BYTE-IDENTICAL (all three)
tests/architectural/_golden_count_baseline.json    6713d2b18e…  BYTE-IDENTICAL (all three)
```

`_golden_count_baseline.json` is additionally unchanged across the *whole* mission
(`git diff 96494e5ec HEAD` empty). No ceiling moved anywhere.

### The golden-count escapes — each judged individually, all three legitimate

| Site | Remedy | My verdict |
|---|---|---|
| `len(targets) == 1` ×2 (AST-helper preconditions) | escape | **ACCEPT.** Elements are `ast.FunctionDef` nodes whose `.name` **is** `symbol` by the filter that built the list; AST nodes hash by identity, so a member-set literal is not even expressible, and any name-set equality is vacuous. The count is the strongest available contract. Genuine heuristic misclassification. |
| `len(fail_closed) == 1` | escape | **ACCEPT, emphatically.** `fail_closed` is a list of identical strings (`n == _FAIL_CLOSED_CALLEE`), so `set(fail_closed) == {…}` holds for one call **and for five** — strictly weaker. Converting here would have *destroyed* the mission's routed-budget assertion, load-bearing in both directions. Escaping was the DIR-041-correct move; converting would have been the violation. |
| `len(hazards) == 1` | convert | **ACCEPT.** Now a set-equality over hazard identity `(file, function, sorted(caught), guarded_callee)` — catches a hazard reported at the wrong frame, which is the failure mode that matters for an instrument whose job is naming the frontier frame. |
| `len(_C002_HANDLERS) == 6` | convert | **ACCEPT.** Frozenset equality over the six `(module, symbol)` pairs — catches a handler *swap* at constant count. Setup and the `offenders` assertion preserved (assertion replaced, not test deleted). Non-tautological: the enclosing test walks `src/` and inspects each handler by `(module, symbol)`, so a stale entry reds against the real tree. |

Live counts from the gate's own `scan_repo()` / `convert_counts_by_dir()`:
`tests/architectural live=25 ceiling=25`; `tests/mission_runtime live=0 ceiling=ABSENT→0`; violating
dirs `[]`. Exactly 3 escaped sites, all `convert`-classified, in the two WP04 files.

Attribution independently confirmed **mission-introduced, not pre-existing**: at `96494e5ec`,
`tests/mission_runtime` held 20 files and exactly one `len(…) == <int>` site
(`test_consolidated_resolution.py:540`) which **already carried the escape annotation** — so the
non-escaped convert count was 0, which is precisely why the directory is absent from the frozen
ceilings.

### The shard fix and its trap — verified

Root cause exactly as stated: `tests/_shard_registry.py:66` `default_fallback: bool = False`;
`tests/_arch_shard_map.py:381` `default_fallback=True`; `tests/_next_shard_map.py` omits it. An
under-root file absent from `file_assignment` gets no `next_shard_N` marker.

My own count of `_NEXT_FILE_ASSIGNMENT` (union of all three roots): post-WP08 `{1: 24, 2: 24, 3: 25}`;
removing the two added files gives `24 22 25`. **24/22/25 → 24/24/25 confirmed.**

The trap is real. `unit-contract-residual` (`ci-quality.yml:2918`) is
`-m "(unit or contract) and not (fast or … or next_shard_1 or next_shard_2 or next_shard_3)"` — it
excludes `next_shard_*` **and** `fast`. Sharding alone would have moved the file from one gate to zero.

`fast` is honest — my measurement: slowest duration **0.03 s** (a setup), 14 further durations
`< 0.005 s`, `5 passed`. Gate membership by exact-CI-selector collection:

```
fast-tests-next    (tests/next/ tests/specify_cli/next/ tests/runtime/  -m "fast and not windows_ci")
    row04 nodes selected: 5     row05 nodes selected: 0
integration-tests-next shard 2  (-m 'next_shard_2 and not windows_ci and (git_repo or integration)')
    row05 nodes selected: 6
```

### F10's closure via the analyzer — reproduced, and stronger than claimed

`tests/architectural/_gate_coverage.py` via `load_gates()` / `collect_universe()` /
`main_push_active_jobs()` / `analyze()`:

```
universe NODES              : 36268
gates parsed                : 68
jobs active on push to main : 57
TOTAL orphan nodes ALL-JOBS model  : 0
TOTAL orphan nodes MAIN-PUSH model : 0
```

Zero orphan nodes **universe-wide** in both models — a superset of the 17-file claim. `git diff
--diff-filter=A 96494e5ec HEAD -- tests/` returns 19 added `.py` files, of which 2 are `_fixtures/`
non-test modules ⇒ exactly **17 test files**. Universe control: the F3 gate file contributes exactly 8
nodes and `36268 − 8 = 36260`. **Exactly +8.** Node counts 5 (row04) and 6 (row05) match.

All six F10 gate tests plus GC-2b's fidelity companion are collected (not deselected) and green in my
own cone run.

### The architectural cone — corroborated

```
rootdir: /home/jeroennouws/dev/sk-missions/3162   configfile: pytest.ini
serial   pytest tests/architectural --collect-only -q  -> 1703 tests collected, exit=0
parallel PWHEADLESS=1 -n 6 --dist loadfile -p no:cacheprovider
         -> 6 workers [1703 items]
         -> 3 failed, 1696 passed, 2 skipped, 2 xfailed in 1049.77s
grep -c '^ERROR tests/' = 0
```

**Collection equivalence holds: serial 1703 == parallel 1703.** The 2 skips and 2 xfails are byte-for-byte
the ones WP08 reports and are pre-existing and unrelated (`test_compat_shims.py:96,:104` empty parameter
sets; `test_egress_consent_boundary` `#3113` / `FR-015` non-adoption, deliberately pinned).

My 3 failures are **contention artifacts**, not mission reds — my run overlapped the concurrent
13-directory sweep and took 1049 s against WP08's 710 s:

- `test_ci_quality_path_filters.py::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection` —
  `subprocess.TimeoutExpired` on an internal `--collect-only` at a 240 s budget;
- `test_wp_prompt_build_latency.py` ×2 — 8.51 s / 8.82 s against a 6.0 s wall-clock budget.

Re-run in isolation, `-n0`: **`3 passed in 268.74s`, exit=0.** All three live in files
`git diff --name-only 96494e5ec HEAD` shows the mission never touched.

The five files outside the cone (§6.1), including the two WP04 files WP08 edited:
**`28 passed in 64.74s`, exit=0, `^ERROR tests/` = 0.**

### F3's skip path — a GENUINE environment guard, and the gate bites

The skip is empirically justified, not hypothetical:

```
CONTROL_BASE_REV = "f1681bf1"
git cat-file -e f1681bf1^{commit}                 -> present in this checkout
git merge-base --is-ancestor f1681bf1 main        -> NOT an ancestor of main
git merge-base --is-ancestor f1681bf1 HEAD        -> IS an ancestor of HEAD
```

So after a squash merge the rev is genuinely unreachable from `main`, and `actions/checkout` at
`fetch-depth: 1` cannot materialize it. Pinning the gate there would be the false-red landmine
`DIR-041` forbids.

It is not a green-washing device: the skip covers **1 of 8** tests, and it is gated by a real
`git cat-file -e` probe with the reason named in the `pytest.skip()` message. The remaining 7 need no
git history and carry the whole calibration — synthetic positive control (hazard *identity* set, not a
count), negative control, a mutual-discrimination check, the live-tree CLEAN regression guard with its
own anti-vacuity assertion, the `CONTROL_EXPECT` non-emptiness pin, and the F11 exclusion pin.
Locally all 8 run: my `17 passed` (8 + 9 golden-count), **0 skipped**.

Asserting `status != 2` rather than `status == 0` is correct, not a weakening: `--self-check` sweeps the
working tree after replaying the control, so `status == 0` would make a live-tree finding read as "the
known answer did not reproduce" — a failure for the wrong reason, already reported with the hazard
printed by test 3.

Anti-vacuity figure reproduced exactly: 4 seeds → **65 raising frames**, 0 hazards, CLEAN.

**Load-bearing, proved by my own injection** (detached scratch worktree at HEAD, since removed; main
tree's `src/` never touched and `git status --short src/` empty afterwards):

```
rootdir: …/scratchpad/wt-inject   configfile: pytest.ini      collected 8 items
1 failed, 7 passed
FAILED …::test_live_src_has_no_stranded_arm_on_the_missions_routed_chains
E  AssertionError: 1 degrade arm(s) are stranded …
E    mission_finalize.py:298 in …mission_finalize._resolve_mission_slug
E      catches ['ActionContextError', 'ValueError']
E      guarding …mission_feature_resolution._find_feature_directory
```

Exactly one test reds, and it names the arm precisely. The other 7 stay green — the gate discriminates.

### The CHANGELOG — accurate, and both corrections to the brief confirmed

Placement: `docs/changelog/CHANGELOG.md` line 1223+, under `### 💥 Breaking Changes` (`:1129`) inside
`## [Unreleased] - 3.2.6` (`:16`). Root `CHANGELOG.md` is a symlink to it. DIR-009 satisfied.

**13 routed sites — exact.** `git diff 96494e5ec HEAD` deletes exactly **12** `pending-batch-a` rows
from `_ACCOUNTED_SITES`, one (`missions/_read_path_resolver.read_primary_meta`) at count **2** ⇒ 13 call
sites. The CHANGELOG's enumeration matches the 12 deleted rows one-for-one. The only surviving
`pending-batch-a` grep hit is the legend at `:185` — the control.

**10 widened handlers in three groups — verified against the src diff.** 2 file-local
(`coordination/surface_resolver.py`, `missions/_read_path_resolver.py`, both
`(ValueError, OSError)` → `(MissionMetaReadError, ValueError, OSError)`); 4 stranded
(`mission_setup_plan.py`, `mission_record_analysis.py`, `mission_finalize.py`,
`mission_check_prerequisites.py`, all → `(MissionMetaReadError, ValueError, ActionContextError)`);
4 degrade-site (`mission_runtime/resolution.py` ×3, `upgrade/feature_meta.py`). The three further
handlers that gained the type (`decisions/service.py`, `_resolve_planning_branch.py`,
`git/ref_advance.py`) are at routed sites and were *rewritten* as part of routing, not widened — the
grouping is coherent. The brief's "four stranded arms" understated it by six, as WP08 says.

MRO verified: `MissionMetaReadError → RuntimeError → Exception → BaseException`;
`issubclass(…, ValueError)` **False**; `issubclass(…, OSError)` **False**. Citations exact:
`class MissionMetaReadError` at `core/paths.py:506`, `def load_meta_fail_closed` at `:638`. The
`_mid8_from_primary_meta` "keeps `ValueError` deliberately" rationale is verified verbatim against the
code — `assert_safe_path_segment`'s traversal `ValueError` is raised inside the same `try`.

**Only ONE floor moved.**

```
ROUTED_LOAD_META_FLOOR         96494e5ec: 126   HEAD: 127   moved
ROUTED_LOAD_META_FLOOR_MARGIN  96494e5ec:   4   HEAD:   4   —
INLINE_META_READ_FLOOR         96494e5ec:   7   HEAD:   7   held
FLOOR_MARGIN                   96494e5ec:   2   HEAD:   2   —
```

The brief's "two floors" was wrong; WP08's correction is right.

**Citation correction confirmed.** `def test_routed_load_meta_floor()` at `:1305`; the three asserts at
`:1313` (`>=`), `:1318` (`>`, strict, anti-vacuous), `:1322` (`- FLOOR <= MARGIN`). The prompt's
`:1084/:1092/:1097/:1101` are unrelated lines (`assert is_meta_path_expr(...)`, docstring prose, a
string literal). Stale as WP08 says.

### The declined claims — honest, and the `src/` premise holds

`git diff --name-status 68643e23a~1 baddccb0e` touches 11 files: `docs/changelog/CHANGELOG.md`, four
`kitty-specs/` files, `tests/_next_shard_map.py`, the E3 baseline, the new F3 gate, and four test files.
**Zero files under `src/`**, and `git status --short src/` is empty. So the `mypy --strict`
byte-identity argument rests on a premise I verified, and WP08 labels the conclusion `[UNVERIFIED]` as a
fresh run rather than claiming it. `ruff check src tests` → **All checks passed!**, exit=0. No `# noqa`,
`# type: ignore` or per-file ignore added anywhere in the diff. No `--feature` in any added line.

I found **no place where WP08 claims more than it measured.** §0 is exemplary: it leads with what was
*not* done, names T047/T048/T050/T051/T052 individually with reasons, marks T047's handshake
`[UNVERIFIED] as a sampled measurement`, and states plainly that 13 of 14 cone directories were not run.

### The three disclosures

1. **Forcing `move-task` past the unchecked-subtask guard without marking them done — CORRECT.**
   `status.json` shows `force_count: 1`, `subtasks: {"T049": "done"}` only, and a note enumerating
   exactly what is missing per subtask. Marking the other five done would have been a false record. The
   truth survives in the durable status record and cross-references §0.
2. **The scratchpad wipe — surviving evidence is ADEQUATE.** Everything re-derivable was re-taken and
   I reproduced it independently (the analyzer run, §5's counts, the cone, §8's suppress figures, the
   65-frame anti-vacuity figure, the injection). The only irreplaceable item is the §2.1 red-first text,
   quoted from `68643e23a`'s commit message — a contemporaneous, immutable, signed record. That is a
   sound provenance chain, and §10 discloses the loss rather than papering over it. The discarded
   killed cone run was correctly recorded as neither pass nor fail and re-run from scratch.
3. **Declining to add frontmatter to `analysis-report.md` — CORRECT.** Verified: 774 lines, first line
   `# Post-plan adversarial squad — findings and remediation directive`, not `---`. Adding YAML
   frontmatter to a hand-authored planning artifact purely to pass a guard would be editing evidence to
   satisfy tooling. Recorded as ledger F16 with the guard's two error codes quoted. Right call.

---

## To clear this review

Fix the blocker (one line, either remedy) and ideally the two `TestResolveContext` MINORs, which are
false statements in committed source and in the mission's terminal evidence artifact. Nothing else
needs to move. Re-review is a re-run of the approval gate.
