# Residual ledger — mission `meta-fail-closed-3162-01KZ7FSQ`

**Purpose.** One place for everything found during this mission that is not already
fixed in it. **Nothing here gets filed as an issue during development.** The order of
operations is:

1. **Fold it into this mission now** if it is in scope. Default to this.
2. If it cannot be folded, record it here with the reason.
3. **After the mission is driven to a PR**, walk this ledger: fold each remaining
   item into an existing mission where possible.
4. Only what survives step 3 becomes a new issue.

This exists because the mission was accumulating deferred findings faster than it was
closing them. Operator direction, 2026-08-06: *"we are here to deliver features and fix
bugs not keep creating residuals."*

---

## FOLDED INTO THIS MISSION

| # | Finding | Where it landed |
|---|---|---|
| F1 | **Absent-arm class.** `check-prerequisites` → `core.paths.read_target_branch_from_meta`, and `finalize-tasks` → `bulk_edit.gate.ensure_occurrence_classification_ready` plus a direct `resolution.read_dir`, read the primary meta at sites guarded by **no** arm at all, so their end-to-end payload stays degraded however the upstream arm is written. Distinct from a *stranded* arm. Found in WP02 cycle 2. | **WP04** — it owns the degrade sites and routes into these same chains. |
| F2 | **`CHANGELOG.md` untouched across the branch** although the exception escaping the routed sites changed from `ValueError` to `MissionMetaReadError` (a `RuntimeError`). Charter Code Review Checklist requires breaking changes recorded. No WP in the mission mentions CHANGELOG. | **WP08** — it is the terminal verification and sees the finished change set. |
| F3 | **`scripts/sweep_degrade_arms_on_routed_chain_3162.py` is exercised by nothing in CI.** A calibrated instrument that no gate runs will rot. | **WP08**. |
| F4 | **`SC-002` is site-scoped and structurally cannot see caller-chain strandings.** Its subject is the routed site; a stranded arm is by construction at a *caller*. A green `SC-002` carries no information about this class, which is why WP02's blocker survived it. | `spec.md` — scope statement added so the criterion is not read as covering it. |
| F5 | WP02's authorized out-of-map edits (four `cli/commands/agent/*.py`, `scripts/sweep_…py`) lacked the explicit declaration `surface_resolver.py` got. | `evidence/WP02-evidence.md`. |
| F6 | `mission_finalize.py` import grouping — `MissionMetaReadError` inserted between two sibling-package imports. Cosmetic; `ruff` passes. | Folded directly. |
| F7 | **`contextlib.suppress` blind spot** in the sweep — `with contextlib.suppress(ValueError, OSError):` is semantically the same arm and was invisible to it. 48 such sites in `src/`. | WP03 built and calibrated a probe for it; 0 on-chain, CLEAN post-routing. |
| F8 | Sweep doc defects: exit status `0` on a reproducing *control* run contradicted the documented "1 when hazards are found"; bare `--seed` names resolve to the wrong function. | `402c90c3c`. |
| F9 | Verifier folded freeze-point snapshots into its verdict, so it exited 1 on any progressed tree — including on correct work. | `bd2d14dfb`, `402c90c3c`. |
| F10 | **Two of this mission's own new test files are selected by ZERO CI gates and will never run** — WP02's `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py` and WP05's `tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`. **WP05 is APPROVED on a test CI never executes.** Measured by WP06 with the repo's own analyzer (`tests/architectural/test_gate_coverage.py` / `_gate_coverage.py`), red at its parent commit too. WP06 correctly did **not** regenerate `_gate_coverage_baseline.json`, which would have turned it green by recording the gap. | **WP08** — it owns terminal CI verification and is the only WP positioned to confirm a gate actually runs these. This is in scope: a mission whose own tests CI never executes has not verified itself. |

### Correction to F10's diagnosis — two wrong analyses, recorded so neither is repeated

Both the review MINOR that prompted my marker change and my own follow-up analysis were wrong:

1. **The reviewer's rationale was wrong.** It said an unmarked real-git test "lands in the wrong
   shard" because the fast shard selects `-m "fast and not windows_ci and not (git_repo or
   integration)"`. An unmarked test is not selected by that expression *at all* — it lands in **no**
   shard. I acted on that rationale in `be64bc0c5` without checking it. The markers I added do
   accurately describe the tests (they really do shell out to `git`), but the commit's stated reason
   for adding them is not correct, and adding them did not by itself put the file in a gate.
2. **My attempt to re-derive the path→gate mapping by grepping the workflow was under-powered.** I
   matched only lines beginning with the exact path `tests/specify_cli/cli/commands`, concluded its
   sole gate was `-m "slow and not windows_ci"` (line 3005), and would have "fixed" it by adding
   `slow`. A control disproved that: of **140** files in that directory only **1** carries `slow`,
   while many carry `git_repo` and plainly do run — so a broader `tests/specify_cli` selection I
   never matched must cover it. I read silence from a probe I had not calibrated, which is the same
   error the sweep's `--self-check` exists to prevent.

**Therefore WP08 must use `_gate_coverage.py` — the repo's authoritative analyzer — and not a
workflow grep.** Do not add markers speculatively; make the analyzer green by genuinely placing each
file in a gate that runs it, and never by regenerating the baseline.

### F10 — measured state as of `7cf529302` + the marker fix, so WP08 need not re-take it

WP06's review closed the earlier `[UNVERIFIED]`: the architectural cone failures are
**sibling-introduced, not pre-existing** — `98198e980` (`upstream/main` tip, *not* the merge base) gives **57 selected / 57 passed**, branch head
gave **6 failed / 51 passed** over the same 57-node selection. Every one named a new test file from
WP02 or WP05.

**Two of the six are now FIXED** (module-level `pytestmark` added to
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`): re-run of
`test_pytest_marker_convention.py` + `test_pytest_marker_correctness.py` → **4 selected, 4 passed,
exit 0, `^ERROR tests/` = 0**.

*Why the first attempt did not fix it:* both gates parse a **top-level `pytestmark` assignment**
(`_module_has_pytestmark`) and **never see class- or function-level marks**. My `be64bc0c5` marked
only the class, so the file still had no module-level `pytestmark` at all — wrong mechanism on top of
the wrong rationale already recorded above. Rule 1 of the correctness gate is file-scoped: a file that
calls `git` via `subprocess` must carry `git_repo` at module level, which necessarily marks all 14
tests, not just the 3 that shell out. My earlier attempt to keep 11 tests in the fast shard was
optimising against a hard architectural gate.

**Three remain RED and belong to WP08**, both naming WP02's next-root files
(`tests/next/test_wp02_row04_planner_fail_closed.py`, `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py`):
- `test_ci_collection_completeness::test_every_test_node_is_collected_on_a_push_to_main`
- `test_next_shard_marker_completeness::test_every_next_root_test_has_exactly_one_shard_marker`
- `test_next_shard_marker_completeness::test_shard_union_equals_full_next_root_universe`

Both files already carry a module-level `pytestmark`, so this is **shard assignment**, not markers:
`tests/conftest.py:242` adds `{marker_prefix}_{shard}` from a group config, and new files are not in
that split. Plus `test_gate_coverage::test_no_new_orphan_surfaces`, red at WP06's parent
`402c90c3c` (**1 failed / 36 passed**, identical two files).

**Do not chase `test_same_tier_uniqueness`'s 3 errors — that measurement is VOID.** All three were
`FileNotFoundError` on `tests/mission_runtime/test_zz_where_probe.py`, a throwaway probe WP04 created
and deleted while my full-universe collection was enumerating files. A race with a live sibling, not a
branch defect. **Do not run full-universe collection gates while an implementer is live in this shared
tree** — same hazard family as the `reset --hard`.

### F13 — scope corrected: it does NOT invalidate the other WPs' cross-tree measurements

WP04 found that `PYTHONPATH=<other tree>/src` is silently overridden by `pytest.ini:9 pythonpath = src`,
and inferred that other WPs' cross-tree pytest claims are therefore unverified. **The finding is real;
the inference is too broad.** Measured three forms with a known-answer control (a
`_F13_FOREIGN_TREE_MARKER` added to the foreign tree's `specify_cli/__init__.py` only):

| Form | Invocation | Imported from | Sound? |
|---|---|---|---|
| **A** | test file resident in the **main** tree, `PYTHONPATH=<foreign>/src` | **main** tree — marker absent | **NO — silently wrong** |
| **B** | `cd <foreign tree>` then run | foreign tree — marker present | yes |
| **C** | run from main tree, pass the **foreign worktree's** test path | foreign tree — marker present | yes |

Form C works because pytest relocates `rootdir` to the foreign worktree (which carries its own
`pytest.ini`, included by `git archive`), so `pythonpath = src` resolves to *that* tree's `src`.
`rootdir:` and `configfile:` in the header confirm it.

**Every reviewer this session used form B or C** (detached worktrees with worktree-resident test
paths), so their cross-tree numbers stand and must **not** be re-taken. Only form A is unsound, which
is the form WP04 hit — and it caught it correctly, via a deliberately-narrowed control that reported
`8 passed` when it should have been red.

**Rule for WP08 and any future cross-tree run:** never leave the test file in one tree while pointing
`PYTHONPATH` at another. Either `cd` into the target tree or pass the target tree's own test paths.

**And `rootdir` is not a sufficient control — strengthened 2026-08-06.** This venv carries an editable
`_editable_impl_spec_kitty_cli.pth` that hard-pins `/home/jeroennouws/dev/sk-missions/3162/src`
*unconditionally*. So on any cross-tree run **both** trees' `src` are on `sys.path`, and the only reason
the foreign one wins is that pytest's `pythonpath = src` **prepends** ahead of the `.pth`. A relocated
`rootdir` therefore proves where the config came from, **not which code was imported** — the two can
diverge if that ordering ever changes.

**The control must be the imported module's own `__file__`.** Print
`specify_cli.__file__` (a tiny `-p` plugin or a first-line assertion in the probe) alongside `rootdir`,
and assert it resolves under the tree you meant to measure. The three-form result above was established
with a marker planted only in the foreign tree's `__init__.py`, which is the same idea; the `.pth`
discovery explains *why* that stronger control is necessary rather than merely tidy.

### Two more orchestrator-brief errors, caught by WP08 and verified

1. **"two floors moved" — wrong; only one did.** Measured at `96494e5ec` and at HEAD:
   `INLINE_META_READ_FLOOR = 7` at **both**; `ROUTED_LOAD_META_FLOOR` 126 → **127**. `INLINE` was
   *re-derived* by WP06 and held at 7. My WP08 brief said "the two floors moving"; had WP08 written the
   CHANGELOG to that brief, it would have published a breaking-change note claiming a floor moved that
   did not.
2. **"four stranded arms" — understated by six.** The real count is **ten widened handlers in three
   groups**: 2 file-local (WP02 cycle 1), 4 stranded on the routed caller chain (WP02 cycle 2), and 4 at
   the degrade sites (WP04). A `git diff 96494e5ec..HEAD -- src/` grep for added `except` lines naming
   `MissionMetaReadError` returns **13 diff lines**, consistent with ten handlers once multi-line tuples
   are accounted for. WP08 enumerated by group rather than inheriting my number.

Both were caught because WP08 re-derived the facts instead of transcribing the brief. Recorded here
because the pattern — an orchestrator number propagating unchecked into a durable artifact — is the
same one that produced the `98198e980` mislabel below and the two F10 misdiagnoses above.

### Correction — the ref I called "merge base" all session is not the merge base

Measured: `git merge-base HEAD main` = `git merge-base HEAD upstream/main` = **`96494e5ec`**.
`git merge-base --is-ancestor 98198e980 HEAD` → **NO**; `96494e5ec` **is** an ancestor. So
`98198e980` is `upstream/main`'s **tip**, carrying commits this branch never had, and is *not* the
fork point.

**This was systematic in the orchestrator's briefs**, which repeatedly told implementers and reviewers
to "classify any red against the merge base `98198e980`". That points attribution at the wrong ref: a
test red on our branch but green at `98198e980` could be red because we *lack* an upstream fix landed
after `96494e5ec`, which is not the same thing as "pre-existing on our base".

**Conclusions already drawn are unaffected**, checked rather than assumed: the six cone failures name
this mission's own new test files, so they are ours under either ref; and WP04's F1 byte-identity was
verified at `96494e5ec`, `98198e980` **and** HEAD, so the stronger claim holds. Corrected in
`evidence/WP04-evidence.md`, `tests/mission_runtime/test_wp04_f1_absent_arm_is_intended.py` and this
file. **WP08 must use `96494e5ec` as the baseline ref**, and say which ref any pre-existing claim was
measured against.

---

## CANNOT BE FOLDED INTO THIS MISSION — assess after PR

These are **spec-kitty product/tooling defects**. This mission's subject is `meta.json`
read routing; none of these is in that subject, so folding them here would be scope
creep of exactly the kind that stalls delivery. Each was hit repeatedly and is
reproduced, not speculative.

| # | Finding | Evidence | Fold candidate |
|---|---|---|---|
> **Note on F13's row below/above:** any wording that says *any* cross-tree `pytest` claim should be
> treated as unverified is **superseded** by the "scope corrected" subsection earlier in this file.
> Only form A (test file resident in the main tree) is unsound; forms B and C are sound and every
> reviewer used one of them. Do not re-take their measurements.

| R1 | **The `for_review`/`approved` guard treats all of `kitty-specs/<mission>/` as the moving WP's surface**, so a *sibling* lane's uncommitted file blocks an unrelated WP's transition. | 3 occurrences: WP02 waited; WP05 forced; WP07's approval forced past the WP05 reviewer's untracked `review-cycle-1.md`. | A lane/ownership mission. |
| R2 | **The same guard refuses with `"No implementation commits on lane branch"` for WPs whose own prompt directs repository-root execution.** Satisfying it would mean rewriting a branch three sibling lanes are committing to. | 4 occurrences across WP02, WP03, WP05, WP07 — every one forced. | Same mission as R1. Sanction the root-worktree workflow rather than force past it every cycle. |
| R3 | **`pre_review_gate` records `outcome: no_coverage`, `test_targets: []`** and runs zero tests, so the tooling's own DIR-030 gate is discharged manually every time. | WP05 transition event `01KZAF5V4BT852XE7KTAKNNQH5`. | Same mission as R1. |
| R4 | **Parallel lanes share one working tree with no isolation.** A `git reset --hard` by one lane is a mission-wide data-loss event. | 2026-08-06: WP03 destroyed 468 uncommitted insertions of WP06's, including the `ROUTED_LOAD_META_FLOOR` 126→127 move. Unrecoverable — never staged, no dangling object holds it. | Same mission as R1. This is the most expensive of the four. |

---

## Appended by WP04 (2026-08-06)

### F1 — RESOLVED as a tested decision, not a fix (see `evidence/WP04-evidence.md` §13)

Outcome: the **absent arm at both F1 sites is INTENDED** and is now pinned by
`tests/mission_runtime/test_wp04_f1_absent_arm_is_intended.py` (4 tests, proved load-bearing — the
rejected absorbing arm makes them fail `DID NOT RAISE`). Re-derived independently by instrumented
traceback: exactly one escaping raise per command.

Decisive evidence that this is not a mission-caused regression:
`core.paths.read_target_branch_from_meta`'s body is byte-identical `load_meta_fail_closed(feature_dir)`
at baseline / merge-base `96494e5ec` **and** at `upstream/main` tip `98198e980` — this mission never routed it (fail-closed
since `#2139`), and its own docstring *mandates* the absent arm. `bulk_edit.gate.ensure_occurrence_classification_ready`
read `load_meta(feature_dir)` with **no arm** at baseline, raising a bare `ValueError` that was
equally unabsorbed and landed in the *same* top-level `except Exception`; WP02's routing changed only
the exception **type**. So `C-001` is not violated: there was never an arm here to change.

Absorbing would be strictly worse — `check-prerequisites` would report a wrong `target_branch`
(`get_current_branch() or "main"`) on a corrupt file, and the bulk-edit occurrence gate would report
**passed** for a mission whose `change_mode` could not be read (a fail-open on a guardrail).

**Wording correction to F1 as originally recorded:** "their end-to-end payload stays degraded" is
imprecise. Both commands exit `1` with structured JSON naming the corrupt file and saying
`— fail-closed`. What the payload lacks is `error_code` / `mission_flag` / `available_missions` —
*mission-detection* keys, meaningful for "could not tell which mission you meant", not for "found
your mission, its meta.json is corrupt". F1's underlying observation was accurate; its
characterisation conflated two different failures.

### Cannot be folded — found by WP04, belongs to a later pass

| # | Finding | Why it cannot be folded into WP04 | Evidence |
|---|---|---|---|
| F11 | **A third caller of the F1 absent-arm chain, on a different command.** `safe_commit_cmd.py:306`'s `except (FileNotFoundError, ValueError)` in `_resolve_mission_aware_target` guards `resolve_placement_only`, which **does** leak `MissionMetaReadError` on malformed meta — so the arm no longer absorbs and `_resolve_mission_aware_target` propagates instead of returning `None`. Origin: `resolution.py:1490 resolve_placement_only` → `paths.py:781 get_feature_target_branch` → `paths.py:720 read_target_branch_from_meta` → `load_meta_fail_closed`. | **Provably pre-existing and not caused by this mission**, so it is out of WP04's `NFR-003` remit: the identical 12-case probe leaks identically at baseline `96494e5ec`, at commit 0 `45b278823` (pre-routing) and at HEAD. `safe_commit_cmd.py` is outside WP04's `owned_files` and is not one of the four census sites. Fixing it is a scope decision about `read_target_branch_from_meta`'s pervasive absent arm (now **3** known call chains), which is the same operator question F1 raises — not a WP04 edit. | Calibrated sweep (`CONTROL: PASS — known answer reproduced exactly`) reports it as the single hazard on seeds `_resolve_coordination_branch` and `_resolve_mission_id`. Probe: malformed leaks at all 4 artifact kinds tested; absent and valid return `CommitTarget`. `evidence/WP04-evidence.md` §12. |
| F12 | **Three pre-existing `mypy --strict` `no-any-return` findings in files WP04 touched**, all one root cause — `follow_imports = "skip"` for `specify_cli.*` (`pyproject.toml:299`) erasing return types across the package boundary: `core/paths.py:278`, `core/paths.py:692` (was `:676`), `feature_meta.py:52` (was `:42`). | Confirmed present at baseline `96494e5ec` (same errors, line-shifted only by WP04's docstring growth), so not introduced here. `core/paths.py` **must stay docstring-only** for concurrent WP05, so no bind can be added there; fixing one file of a repo-wide typing-config artefact is the whack-a-field pattern `DIR-024` forbids. Neither fixed nor suppressed. | **These three are NOT in the briefing's known-pre-existing list** (`merge_driver.py:645`, 10 under `cli/commands/agent/`, 2 in `decisions/service.py`) — recorded as an addition to that set so the next WP does not re-attribute them. |
| F13 | **The WP prompts' `PYTHONPATH=<workspace>/src` instruction is unsound for `pytest` and fails silently.** `pytest.ini:9` sets `pythonpath = src`, which pytest resolves relative to its **own rootdir** and inserts *ahead* of the `PYTHONPATH` env var — so a pytest run "against another tree" silently imports the **main** tree's `src`. This is the very hazard the instruction was written to prevent, and it affects every WP prompt in the mission. | Not a code defect — a defect in the mission's planning artifacts and in `PYTHONPATH`-based evidence already recorded by earlier WPs. Correcting those prompts is out of WP04's surface; **any cross-tree `pytest` claim in another WP's evidence that relied on `PYTHONPATH` alone should be treated as unverified** until re-run from inside the target tree. | Measured `sys.path` inside a pytest run invoked with `PYTHONPATH=<control>/src`: rootdir's `src` appears at position 4, the `PYTHONPATH` entry last; `mission_runtime` resolved from the main tree. Caught because a deliberately-narrowed control worktree reported `8 passed` — a control that cannot fail. Correct method (used throughout WP04): `cd <worktree> && pytest`. `PYTHONPATH` *is* honoured for standalone `python`. `evidence/WP04-evidence.md` §11. |

### `SC-009` register row for `NFR-001` (filed here, not as a tracker issue)

Operator direction for this mission forbids `gh issue create`, which **consciously overrides charter
`DIR-013`**. WP04's prompt (T026 step 6) asks for `gh issue view <n>` verification; that is **not
applicable** and no issue number exists — recorded rather than faked.

The four degrade sites remain **knowingly indistinguishable** under `D4=(a)`: `""`, `None`,
`legacy-<slug>` and `None` are each values a **valid** `meta.json` also yields. Demonstrated by the
`SC-002` probe — `_mid8_from_primary_meta` returns `''` for malformed *and* absent input, and a valid
file lacking `mid8`/`mission_id` returns `''` too. Candidate remedy: **`Q4`** (should a degrade site
log when it degrades?). **`Q4` is an operator question and is NOT decided here** (`plan.md:783-785`).
Nothing in WP04 logs, and nothing in WP04 forecloses either answer.

---

| R5 | **Two cut-over authorities disagree about a natively-born mission, and one of them gates CI.** `migration.runtime_state_cutover.cutover_repo()` (what `spec-kitty doctor cutover` reports) calls this mission **cut over**, reason *"no legacy runtime to migrate"*, with **0 of 340** not cut over. `status.cutover_eligibility.is_cut_over()` — the spine of the dogfood corpus guard — called the same mission **not** cut over, reason *"status_phase not flipped despite event-log runtime evidence"*. | Measured 2026-08-06 on this mission. Root cause: `status_phase` in `meta.json` is stamped only by the **legacy-seeding** path. A mission born after the WP04/WP05 frontmatter-runtime retirement is event-sourced natively (ours: 47 events) and so has nothing to seed and never receives the stamp. The guard's own docstring anticipated natively-born missions and re-keyed **eligibility** to catch them via `status.events.jsonl` — but the **flip assertion** still demands a legacy-seed birth-stamp, so every such mission reds it while in flight. | A read-authority mission. This is the same defect class this mission exists to fix — a single fact with two disagreeing readers — one layer up. **Operator decision 2026-08-06:** stamp `status_phase: "1"` on this mission (it records something true: the mission *is* event-sourced, phase ≥ 1) and reconcile the two authorities separately, rather than change an architectural guard covering all 340 missions at PR time. |

### An attempted fix that was WRONG, recorded so it is not retried

Before the stamp, I tried re-keying the guard's exclusion on `mission_number is None`, reasoning that it is
the identity model's canonical pre-merge marker. **A control killed it:** that predicate classifies
**96 of 340** missions as in-flight, not one — many merged missions carry no number — so the "fix" would
have silently dropped 96 missions from a guard meant to cover them, and the non-vacuity floor of **100**
would *not* have caught it (340 − 96 = 244 > 100). Reverted to a byte-identical diff. It was a
gate-weakening dressed as a principled property. The control that caught it was simply printing the size
and contents of the set the predicate selected — worth doing before trusting any exclusion.

Two other things that misled the diagnosis on the way, both corrected by measurement:
- `status_phase` lives in **`meta.json`**, not `status.json`. Checking `status.json` returns
  "0 of 339 missions have it", which looks like proof the field is irrelevant and is not.
- `spec-kitty migrate backfill-runtime-state --dry-run` reports this mission **"Skipped (already
  migrated)"** — a no-op, because it classifies on `seeded_count > 0` rather than flip state (the defect
  already filed as `#3212`). The sanctioned remedy string in `cutover_guard.py` therefore does nothing
  for a natively-born mission.

---

## BASE HYGIENE — the branch cannot open a PR on its current base

Measured 2026-08-06, `git fetch upstream`:

| | |
|---|---|
| merge base | `96494e5ec` |
| `upstream/main` tip | `d0ed802cc` |
| commits we are **behind** | **95** |
| commits we are ahead | 166 |
| files we changed that upstream also changed | **5** |

The five overlapping files are `docs/changelog/CHANGELOG.md`, `src/mission_runtime/resolution.py`
(WP04's degrade sites), `src/specify_cli/cli/commands/merge_driver.py` (WP05 site E),
`tests/architectural/test_inline_meta_read_gate.py` (WP06's floors) and
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.

### `upstream/main` is RED on this mission's own gate — pre-existing, not ours

Reproduced in a pristine `upstream/main` worktree (imported module `__file__` printed as the control,
confirming the upstream tree was measured, not the `.pth`-pinned main tree):

```
ROUTED live (upstream/main) : 133      INLINE live : 7
ROUTED_LOAD_META_FLOOR      : 128      MARGIN : 4   -> band [129, 132]

E   AssertionError: ROUTED_LOAD_META_FLOOR (128) is more than
E   ROUTED_LOAD_META_FLOOR_MARGIN (4) below the live routed count (133); tighten the floor.
E   assert (133 - 128) <= 4
FAILED tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor   exit=1
```

Someone landed routing upstream without tightening the floor. **This is a pre-existing main breakage
by the charter's classification** — but unlike an unrelated red, **this mission owns that gate**: the
routed floor is its subject. So re-pinning it post-rebase is a *contract crossing* to re-pin in this PR
with a dated rationale, not a foreign red to leave alone. Doing so also clears upstream's red.

### Consequences for the numbers — every routed figure in this dossier is pre-rebase

Upstream and this mission routed **largely disjoint** site sets: upstream's `resolution.py` carries **0**
`load_meta_fail_closed(` calls where ours carries **3**, yet upstream's total (133) exceeds ours (130).
So the post-rebase live count is neither 130 nor 133, and **must be re-measured**, after which:

- `ROUTED_LOAD_META_FLOOR` must be re-derived so `live > floor` **and** `live - floor <= 4`. Ours (127)
  and upstream's (128) will both be wrong.
- WP06's 126 → 127 derivation, WP04/WP05/WP07's 0-net and `129 -> 130` attributions, and the
  `[128, 131]` band quoted throughout the dossier are all **pre-rebase** figures. They were correct when
  taken; they describe a tree 95 commits stale.
- `SC-008` / `SC-010` / `SC-002` re-captures must be retaken post-rebase.

**Nothing here indicates a defect in the mission's work** — the numbers were measured correctly against
the base that existed. It is a staleness cost, and the rebase is the remedy.

### Already filed before this direction took effect

Not to be added to; listed so the post-PR pass has the full picture.

- **Foldable candidates**: `#3212`, `#3221`, `#3227`
- **Need an owner's decision**: `#3213`, `#3214`, `#3222`, `#3226`
- **Filed by WP07 as deliberate non-fixes, correctly** (the product defect had to be
  recorded rather than suppressed, per the operator's rider on `#3138`): `#3231`, `#3232`
- **Filed by WP06** before the no-more-filing direction reached it — it was dispatched earlier, so
  this is a briefing gap on my side, not a WP06 error: `#3239` (SC-009 row 3), `#3240` (SC-009 row 7
  — **an open question put to the operator, not answered**, so it legitimately needs a human),
  `#3241` (the zero-gate coverage finding, now folded as **F10** above plus the `_rel()` cross-tree
  measurement trap). At the post-PR pass, `#3241` should be closable as folded.

**No further issues are to be filed by any WP in this mission.** Findings go into this ledger or into
the WP that owns the surface.

---

## Appended by WP08 (2026-08-06) — the four owned items, closed

**Baseline ref for every claim below is `96494e5ec`** (`git merge-base HEAD main` =
`git merge-base HEAD upstream/main`). `98198e980` is `upstream/main`'s **tip**, not the fork
point, and is not used for attribution anywhere in this section.

Every measurement in this section was taken in the **repository-root tree**
`/home/jeroennouws/dev/sk-missions/3162`, with `rootdir` printed as the control on every
`pytest` run (`rootdir: /home/jeroennouws/dev/sk-missions/3162`, `configfile: pytest.ini`).
**No cross-tree run was needed**, so F13's form-A hazard could not arise; the one scratch-tree
measurement (the `contextlib.suppress` positive control) used standalone `python` against a
`git archive` tree, which is the form F13 records as sound for `PYTHONPATH`.

### F10 — CLOSED. Six mission-introduced arch gate reds, not four

The ledger recorded **four** remaining. Running the **whole** `tests/architectural` directory
(1703 collected) instead of WP06's 57-node selection found **two more**. All six are now green
and **no ratchet baseline was regenerated to reach that**.

Red first, quoted verbatim (`4 failed, 1 passed in 358.84s`, `^ERROR tests/` = 0):

| # | Gate | Failure text (quoted) | Cause |
|---|---|---|---|
| 1 | `test_ci_collection_completeness::test_every_test_node_is_collected_on_a_push_to_main` | *"6 of 36260 collected test NODES (1 files) run in NO job on a push to `'main'`"* — `tests/runtime/test_wp02_row05_bridge_io_fail_closed.py` | shard assignment |
| 2 | `test_next_shard_marker_completeness::test_every_next_root_test_has_exactly_one_shard_marker` | *"11 test(s) under group 'next' carry NO shard marker (assignment gap)"* | shard assignment |
| 3 | `test_next_shard_marker_completeness::test_shard_union_equals_full_next_root_universe` | same 11 nodes | shard assignment |
| 4 | `test_gate_coverage::test_no_new_orphan_surfaces` | *"1 test file(s) are selected by ZERO CI gates and are not in the recorded baseline"* | shard assignment |
| 5 | `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline` | *"tests/mission_runtime: 4 un-annotated convert-classified golden-count site(s) exceeds the frozen baseline ceiling of 0"* (+ 1 of mine) | **new finding** |
| 6 | `test_gate_coverage::test_gc2b_bites_on_producer_side_selection_shrink` | *"producer-side fault injection did not shrink the REAL selection"* | consequence of fixing 1–4 |

**Reds 1–4 were ONE root cause, not four.** `tests/_next_shard_map.py` registers the `next`
group with `default_fallback=False` (`tests/_shard_registry.py`), so an under-root file absent
from `file_assignment` gets **no** `next_shard_N` marker at all. The `arch` row opts into the
hash-bucket fallback and would have auto-covered it; `next`'s does not. The ledger's diagnosis
("this is shard assignment, not markers — `tests/conftest.py:242`") was **correct**.

The fix registered both of WP02's files in shard 2 (lightest by file count, 24/22/25 → 24/24/25 —
this module's documented pick rule) **and** moved
`tests/next/test_wp02_row04_planner_fail_closed.py` from `unit` to `[unit, fast]`. That second
half is load-bearing and is the trap in this fix: that file's only gate was
`unit-contract-residual`, whose selector **excludes every `next_shard_*` test by construction**
(`-m "(unit or contract) and not (… or next_shard_1 or next_shard_2 or next_shard_3)"`), so
registering it in the shard split *alone* would have moved it from one gate to **zero** —
turning a GC-1 fix into a new orphan. Measured 0.06 s slowest item, no subprocess, no git,
no network, so `fast` is honest (`docs/context/testing-taxonomy.md` §Fast: `fast` is the
performance characterisation, orthogonal to the `unit` category).

**Closure evidence, from the repo's authoritative analyzer** (`tests/architectural/_gate_coverage.py`,
never a workflow grep — the error the ledger records twice). Universe 36268 nodes, 68 gates
parsed, 57 jobs active on a push to `main`:

```
SUMMARY: 17/17 files have ZERO zero-gate nodes in BOTH models;
         total zero-gate nodes across both models = 0
```

Every one of the 17 test files this mission added (16 from WP02–WP07 plus WP08's own new gate)
is selected by **exactly one** gate, in both the all-jobs and the main-push-active model. The
three that moved:

```
tests/next/test_wp02_row04_planner_fail_closed.py
  markers: ['fast', 'next_shard_2', 'unit']
  ci-quality.yml:fast-tests-next:'fast and not windows_ci'  -> 5/5 nodes
tests/runtime/test_wp02_row05_bridge_io_fail_closed.py
  markers: ['git_repo', 'integration', 'next_shard_2']
  ci-quality.yml:integration-tests-next:'next_shard_2 and not windows_ci and (git_repo or integration)'  -> 6/6
tests/architectural/test_sweep_degrade_arms_instrument.py   (WP08's own)
  markers: ['arch_shard_1', 'architectural', 'git_repo']
  ci-quality.yml:arch-adversarial:'arch_shard_1 and not windows_ci and (git_repo or integration or architectural) and not timing'  -> 8/8
```

`test_meta_bypass_diagnosability.py` was already off the orphan list by the time WP08 ran — the
module-level `pytestmark` fix closed it, confirmed by red #4 naming only **one** file.

**Red 5 is a new finding and belongs in this ledger's history.** `tests/mission_runtime` is
**absent** from `_golden_count_baseline.json`'s ceilings, so its ceiling is an implicit **0**;
WP04's `test_wp04_routed_call_counts.py` and `test_wp04_sc007_guard_and_handler_contract.py`
carry four `convert`-classified `len(…) == <int>` sites, so the gate went red the moment WP04
landed. It is mission-introduced, not pre-existing at `96494e5ec` — the directory could not have
been absent from the ceilings had it carried convert sites when they were frozen. WP06's
57-node selection did not include this gate, which is why it went unrecorded until now.
**Lesson for the next mission: measure the whole cone, not a selection, before calling a branch
green.** Fixed by 2 conversions (`len(hazards) == 1` → a hazard-identity set equality;
`len(_C002_HANDLERS) == 6` → a frozenset equality over the six `(module, symbol)` pairs) and
3 per-site escapes with rationales where a member-set equality would be strictly *weaker* than
the count. `_golden_count_baseline.json` untouched; re-scanned `tests/architectural` 26 → 25
(ceiling 25), `tests/mission_runtime` 4 → 0 (ceiling 0), violating dirs `[]`.

**Red 6 is the price of fixing 1–4, and the refreeze is measured, not assumed.**
`test_gc2b_bites_on_producer_side_selection_shrink` asserts a **strict subset** of the committed
E3 node-id manifest, so adding 6 tests to `integration-tests-next`'s real selection reds it.
`tests/architectural/baselines/integration-tests-next-nodeids.txt` was refrozen — **442 → 448
node-ids, 0 DROPPED, +6 ADDED, all six from row05's file**; `git diff --stat` = 7 insertions,
**0 deletions**. That is coverage *gained*: a refreeze accepting a gap shows `DROPPED > 0`. The
file's own committed header mandates this exact path (*"Regenerate ONLY with an explicit
provenance comment (data-model E3) when a WP legitimately changes this job's selection"*), and
`_gate_coverage.py:1113-1124` records the same design intent. `_gate_coverage_baseline.json`,
`_baselines.yaml` and `_golden_count_baseline.json` were **not** touched anywhere in WP08. Had
the diff dropped anything, the gate would have been left red and recorded here instead.

### F2 — CLOSED, with a correction to the brief

`docs/changelog/CHANGELOG.md` (repo root is a symlink) now carries an entry under
`## [Unreleased] - 3.2.6` / `### 💥 Breaking Changes`: the 13 routed read call sites enumerated
by `module:symbol`, the `ValueError` → `MissionMetaReadError` type change with
`core/paths.py:638` / `:506`, the **ten** widened handlers in three groups, and the floors.

**Correction.** The brief says *"the two floors moving (`ROUTED_LOAD_META_FLOOR` 126→127)"*.
Measured `git show 96494e5ec:tests/architectural/test_inline_meta_read_gate.py` against HEAD:
`ROUTED_LOAD_META_FLOOR` 126 → 127 (**moved**), `ROUTED_LOAD_META_FLOOR_MARGIN` 4 → 4,
`INLINE_META_READ_FLOOR` 7 → 7 (**re-derived, held**), `FLOOR_MARGIN` 2 → 2. Both floors were
re-derived; **one** moved. The entry says so.

Also corrected: the WP08 prompt cites `test_routed_load_meta_floor` at `:1084` with its three
asserts at `:1092` / `:1097` / `:1101`. Post-WP06 those are `def` at **`:1305`** and the asserts
at **`:1313`** (`>= FLOOR`), **`:1318`** (`> FLOOR`, the strict one), **`:1322`**
(`- FLOOR <= MARGIN`). The prompt's line numbers are stale by ~220 lines; the assertions
themselves are unchanged in substance and **127 is still RED**.

### F3 — CLOSED

`tests/architectural/test_sweep_degrade_arms_instrument.py` (8 tests) puts
`scripts/sweep_degrade_arms_on_routed_chain_3162.py` under the always-on arch pole. Design note
worth keeping: **the gate does not rest on `--self-check`.** That flag shells out to
`git archive f1681bf1 src`, and `actions/checkout` defaults to `fetch-depth: 1` with the arch
pole not overriding it, so on a CI runner the control rev is usually absent — and after a squash
merge it may never exist on `main` again. Pinning the gate there would have been a landmine of
exactly the class `DIR-041` forbids. So `--self-check` runs when the rev is present (it is
locally: 8 passed, **0 skipped**) and skips with the reason named when it is not, while the
calibration that always runs in CI is a **synthetic positive control** (one stranded arm on a
3-module chain must be reported as exactly that hazard) plus its **negative control** (widened
arm ⇒ CLEAN) plus a live-tree CLEAN assertion over the mission's four routed seeds with its own
anti-vacuity guard (65 raising frames from 4 seeds — a graph resolving no edges cannot report
CLEAN vacuously). Proved load-bearing by injection, not asserted: narrowing
`mission_finalize.py:298` took the live test red and named the arm exactly.

### F13 — rule honoured

No cross-tree `pytest` run was performed. `rootdir` printed on every run. The one scratch-tree
measurement used standalone `python` (form F13 records as sound for `PYTHONPATH`) against a
`git archive HEAD src` tree, and `git status --short src/` was verified empty afterwards.

---

## Appended by WP08 — cannot be folded

| # | Finding | Why it cannot be folded | Evidence |
|---|---|---|---|
| F14 | **`gc._baseline_header` hardcodes ONE mission's provenance sentence for every E3 target.** So `--freeze-baselines` — the command those files' own headers tell you to run — overwrites every target's provenance with the text of the *previous* refreeze (`runtime-state-corpus-cutover-01KXZ0AX` WP06, `#2816`), silently erasing the recorded reason for each file's last refreeze. The file contract says "Regenerate ONLY with an explicit provenance comment"; the tool that regenerates cannot honour it. | Fixing it means changing the writer's contract and re-authoring provenance for all 22 targets — a `tests/architectural` tooling mission, not a `meta.json`-read-routing one. WP08 worked around it by hand-writing the one file it had to touch (existing header preserved verbatim, new provenance added as a second `#` line, which `load_baseline_nodeids` skips). | `tests/architectural/_gate_coverage.py:1946-1959` (`_baseline_header`), `:1972-1978` (`write_baseline_nodeids`), `:2001-2014` (`freeze_baselines` loops all `BASELINE_TARGETS`). |
| F15 | **WP06's "the architectural cone is green" measurement was a 57-node selection, not the cone.** The cone is **1703** collected. Two mission-introduced reds (F10's #5 and, latent, #6) sat outside that selection and survived six approved WPs. | Not a code defect — a measurement-method defect in this mission's own process, already spent. Recording it so the next mission's terminal WP runs the whole directory. | WP08's whole-cone run: 1703 collected, `2 failed, 1697 passed, 2 skipped, 2 xfailed in 708.98s` before the fixes; WP06's recorded figure was `57 selected / 57 passed`. |
| F16 | **The `implement` action gate could not be satisfied for WP08.** `spec-kitty agent action implement WP08 --agent claude --mission …` refuses with `analysis_report_required: /spec-kitty.analyze must be run before implementation` → `invalid_analysis_report_frontmatter: File has no frontmatter`. The mission's `analysis-report.md` is a 774-line hand-authored squad record with no YAML frontmatter, and adding frontmatter to a planning artifact purely to satisfy a guard would be editing evidence to pass a gate. | The guard's contract (frontmatter-bearing report from `/spec-kitty.analyze`) versus the mission's actual artifact (hand-authored adversarial-squad record) is a spec-kitty product question, not a `meta.json` routing one. WP08 proceeded without the action record and says so rather than faking the frontmatter. Same family as **R1–R3**. | `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/analysis-report.md:1` is `# Post-plan adversarial squad — findings and remediation directive`, not `---`. |

---

## Appended by the terminal branch-measurement pass (2026-08-06) — cannot be folded

**Baseline ref for every claim below is `96494e5ec`** (`git merge-base HEAD main`), re-verified:
`git merge-base --is-ancestor 96494e5ec HEAD` → yes; `98198e980` → **no**.

| # | Finding | Why it cannot be folded | Evidence |
|---|---|---|---|
| F17 | **`tests/sync`'s real-port daemon suites collide across xdist workers, producing phantom reds for any mission that runs the directory in parallel.** Two daemons were bound to **port 9413 at the same time** from two different workers, and a daemon **leaked onto port 9400 and survived into the next pytest pass**, squatting the range while `test_orphan_sweep.py` ran. Three composing causes: **(a) the declared port bands overlap** — `tests/sync/test_issue_1071_singleton_reconfirmation.py:24` claims `[9401, 9425)` while `tests/sync/_daemon_harness.py:18` claims `[9400, 9425)` for its own consumers, i.e. near-total overlap, not the documented partition; **(b) the serial-only exclusion list is incomplete** — `docs/development/testing-parallel.md:86-93` and `:147` name **only** `tests/sync/test_orphan_sweep.py`, yet **four** files bind real ports through the harness (`test_daemon_cleanup_boundary.py`, `test_issue_1071_singleton_reconfirmation.py`, `tracker/test_saas_client.py`, `test_daemon_orphan_classification.py`), and `_daemon_harness.py:22` itself mandates *"Never overlap ranges across suites; each must run serially with `-n0`"*; **(c) `find_free_port_in_range` (`tests/sync/_daemon_harness.py:44-56`) is a TOCTOU** — it binds a probe socket, closes it on `with`-exit, returns the port, and the daemon binds *later*, so two workers probing concurrently receive the **same** port. **`--dist loadfile` is NOT the defect and must not be "fixed"**: it correctly keeps one file on one worker, but the contended resource is OS-global and shared *across* files, which file-affinity cannot address. | This is `tests/sync` test-infrastructure, not `meta.json` read routing. The mission changed **no** `src/specify_cli/sync/` file (`git diff --stat 96494e5ec..HEAD -- src/` lists 19 files, none under `sync/`), so nothing here is mission-introduced and fixing it would be scope creep. It nevertheless costs every future mission real time: the 6 apparent `tests/sync` reds in this pass (2 failed + 4 `^ERROR tests/`) were all topology artifacts, and a reviewer who did not re-run serially would have attributed them to the branch. | `tests/sync` at `-n 6 --dist loadfile`: `2 failed, 2369 passed, 18 skipped, 4 errors`, exit 1. Reap output names cross-worker daemons explicitly: `pid=276364 port=9413 … gw2/.spec-kitty  skip_reason=cross_root` alongside `pid=276365 port=9413 … popen-gw3/test_no_leak_after_reap_pgrep0/home/.spec-kitty`. Leaked squatter observed live between passes with `ss -ltnp`: `LISTEN 127.0.0.1:9400 users:(("python",pid=275347,fd=4))`, cmdline `run_sync_daemon(9400, …) --spec-kitty-daemon-root=/tmp/spec-kitty-test-homes/…/gw3/.spec-kitty`. The 4 `^ERROR tests/` are FR-007 leak-guard teardown errors (`#3130` family) on process-global threads/singletons; one of them (`test_lifecycle_readiness.py::test_init_emits_project_init_event_offline`) reports its own pin's markers *not* reproducing (`missing markers (genuinely absent): ['[E27]', 'target=None', 'spec-kitty-sync-async-loop']`) precisely because the producer test that normally precedes it landed on a different worker — i.e. the pin is itself worker-order-dependent. |
| F18 | **Three `tests/specify_cli` wall-clock assertions red under parallel load and green serially, with no marker protecting them.** `test_completion_latency_within_budget[spec-kitty ]`, `[spec-kitty agent ]`, `[spec-kitty agent mission ]` measured 546–580 ms against a 500 ms budget under `-n 6`, and **all three pass** in a serial quiet-system re-run. The file carries `pytestmark = [pytest.mark.integration]` (`:25`) and **not** the `timing` marker that `pytest.ini` defines for exactly this ("wall-clock timing regression gate; run only in dedicated CI jobs or explicit local invocations"). `min`-of-5 sampling (`:247`) cannot rescue it, because under `-n 6` *every* sample is contended. | Marker/topology policy for the completion latency gate is a testing-taxonomy question owned by the CI-topology missions, not by `meta.json` read routing. Recorded rather than fixed so a future pass does not re-attribute these three to a branch. Not mission-introduced: the file is untouched by this mission. | Under `-n 6 --dist loadfile`: 3 failed, e.g. *"completion for 'spec-kitty ' took 565 ms (budget 500 ms); durations=['570ms','572ms','580ms','573ms','565ms']"*. Serial `-n0` on a quiet system, same file, same ref: `1 failed, 21 passed` — the sole failure being the unrelated, **pre-existing** `test_manifest_matches_live_cli` (red at `96494e5ec` too under identical serial topology, base-tree relocation confirmed by control: `specify_cli=/home/jeroennouws/dev/sk-missions/base-96494e5ec/src/specify_cli/__init__.py`). |

| F19 | **A THIRD cross-tree trap, distinct from F13's form A: `locate_project_root()` escapes a detached worktree, so any test that resolves its corpus through it reads the MAIN tree even under the "sound" form B (`cd <worktree> && pytest`).** Measured from inside the base worktree: `locate_project_root()` returns **`/home/jeroennouws/dev/sk-missions/3162`**, not the worktree, because a linked worktree's `.git` is a *file* (`gitdir: …/3162/.git/worktrees/base-96494e5ec`) that resolves back to the main repo. Consequence: `tests/specify_cli/migration/test_dogfood_corpus_backfilled.py` scanned **HEAD's** `kitty-specs/` during a base-worktree run and reported HEAD's failure verbatim — which would have been misread as "red at base ⇒ pre-existing" when the truth is the opposite. **F13's rule ("cd into the target tree or pass its own test paths, print `rootdir`") is necessary but NOT sufficient**: `rootdir` and even `specify_cli.__file__` relocate correctly while the *data corpus* does not. Any future attribution of a test that calls `locate_project_root()` (or any marker/`.git` walk-up) must additionally pin the corpus path explicitly. | Not a code defect in this mission's subject — it is a property of worktree topology plus the production root resolver, and correcting the resolver's worktree semantics is a `core.paths` ownership decision (the same pervasive-resolver question F1/F11 raise). Recorded so the next mission does not repeat the misattribution. | Direct probe from `cd /home/jeroennouws/dev/sk-missions/base-96494e5ec`: `locate_project_root() -> /home/jeroennouws/dev/sk-missions/3162`; `our mission present = True` although `ls base-96494e5ec/kitty-specs/meta-fail-closed-3162-01KZ7FSQ` is `No such file or directory` and `git ls-tree -r 96494e5ec --name-only kitty-specs/ \| grep -c meta-fail-closed-3162` = **0** (vs **48** at HEAD). Correct measurement, obtained by pinning the corpus explicitly and using base's own code: base corpus → `eligible 321, unflipped []`, **PASS**; HEAD corpus → `eligible 322, unflipped ['meta-fail-closed-3162-01KZ7FSQ']`, **FAIL**. Exactly one mission added, ours, sole cause. |
| F20 | **The venv's editable install pins the HEAD tree, and `.venv/bin` is absent from `PATH`.** `_editable_impl_spec_kitty_cli.pth` contains a single plain path entry `/home/jeroennouws/dev/sk-missions/3162/src`, so site-packages injects HEAD's `src` into **every** interpreter using this venv, including base-worktree runs. `pytest.ini`'s `pythonpath = src` happens to win because it is *prepended*, but nothing enforces that ordering — a plain `python` (no pytest) in the base worktree imports HEAD's code silently. Separately, a bare `spec-kitty` resolves to `/home/jeroennouws/.local/bin/spec-kitty`, a **different** install with shebang `#!/usr/bin/python3` (3.14, not the venv's 3.11), so any test shelling out to the bare command would exercise the wrong tree entirely. | Environment/tooling topology, not this mission's subject. No failure measured in this pass depends on the console script, so nothing here changes the branch verdict — recorded because it is a live silent-wrong-answer hazard for every future cross-tree measurement, and because it means "the editable install is stale" can be ruled out as an explanation for a red **by construction** (a plain path entry reads live files; no reinstall is ever needed). | `cat .venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` → the 3162 path only. Control plugin on every base run confirmed `specify_cli=/home/jeroennouws/dev/sk-missions/base-96494e5ec/src/specify_cli/__init__.py`, i.e. pytest's prepend beat the `.pth`. `case ":$PATH:" in *".venv/bin"*` → **NO**; `which -a spec-kitty` → `/home/jeroennouws/.local/bin/spec-kitty` only. |

### Deviation from charter `DIR-013`, disclosed

`DIR-013` ("Pre-existing Failure Reporting Rule") requires opening a GitHub issue before treating
pre-existing failures as accepted baseline. Operator direction for this pass forbids filing issues
and directs findings into this ledger instead. Recorded here as a **conscious override**, consistent
with the same override already recorded for WP04's `SC-009` row — not as an oversight.

---

## Appended by WP08's second pass (2026-08-06) — after the review rewind

**Baseline ref for every claim below is `96494e5ec`** (`git merge-base HEAD main`).
`98198e980` is `upstream/main`'s tip, is not an ancestor of HEAD, and is not used for
attribution anywhere in this section. **Every count is `pre-rebase (base 96494e5ec)`.**

### Two corrections to WP08's OWN first-pass evidence — recorded because both would have shipped

1. **The `SC-006` code delta was reported as `0`, derived from the wrong thing.** §5.4 argued it
   from `INLINE_META_READ_FLOOR` being unchanged at 7 between `96494e5ec` and HEAD. That restates
   the floor; it does not measure the delta. Measured as a 2×2 (gate predicate × `src` tree),
   **both deltas are non-zero and they cancel**: widening **`+1`**, code **`−1`**. The site is
   named rather than counted — `src/specify_cli/git/ref_advance.py::_meta_change_is_vcs_lock_only`,
   which at base read `meta_path.read_text()` (`:244`) and parsed it one hop away via
   `_parse_meta_object` (`:247`), and at HEAD is `load_meta_fail_closed(meta_path.parent)`
   (`:247`). So **one edit is simultaneously the mission's single net routed `+1` (`129 → 130`) and
   the inline census's `−1`**, verified by count: `grep -c 'load_meta_fail_closed('` on
   `ref_advance.py` is **0** at base and **1** at HEAD. This is exactly the pair `SC-006` exists to
   separate, and reporting one number would have hidden both causes while looking correct.
2. **§7's `mypy` claim was `[UNVERIFIED]` and its premise had gone stale.** *"WP08 changed no file
   under `src/`"* was true when written and is not now — `24a5e62a5` touches
   `mission_check_prerequisites.py`. Re-measured on both sides under CI's own invocation
   (`src/specify_cli src/charter src/doctrine`): base **and** HEAD both `Success: no issues found in
   1130 source files`, exit 0. Delta **`0 → 1 → 0`**, against a clean floor.

Both were caught the same way the earlier brief errors were — by re-deriving instead of
transcribing. The pattern is now recorded three times in this file; it is the mission's most
reliable defect-finder and its most expensive omission.

### The briefing's "known pre-existing `mypy` findings" list is INVOCATION-DEPENDENT

Recorded because it will otherwise be re-attributed every pass. Under CI's **package-scope**
invocation, base measures **zero** — the list does not reproduce at all. Under a **single-file**
invocation it does:

```
$ mypy --strict src/specify_cli/cli/commands/merge_driver.py     # HEAD
merge_driver.py:645: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
$ mypy --strict src/specify_cli/cli/commands/merge_driver.py     # BASE 96494e5ec
merge_driver.py:630: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
```

Same source line both refs — `return AcceptanceMatrix.from_dict(merged_document).to_dict()` —
line-shifted only, so **pre-existing is proved, not asserted**. Cause: package scope lets `mypy`
resolve `to_dict()`'s real return type through the package, while single-file scope with
`follow_imports = "skip"` (`pyproject.toml:299`) erases it to `Any`. Same for `F12`'s family.
**Confirmed do-not-fix under either invocation** — but "the branch has N pre-existing mypy findings"
is not a well-formed statement without naming the invocation, and previous briefs quoted the list as
if it were invocation-independent.

### `F21` — a SECOND instance of the `_rel()` cross-tree trap, in a second gate surface

| # | Finding | Why it cannot be folded | Evidence |
|---|---|---|---|
| F21 | **`test_inline_meta_read_gate`'s own exclusion silently stops working on any relocated tree, over-counting the inline census.** `_rel` (`:424`) resolves paths with `path.relative_to(_REPO_ROOT)`, where `_REPO_ROOT` is derived from the **gate file's own `__file__`** (`:59-61`) — *not* from the `src_root` argument the scanner was handed. `EXCLUDED_REL_PATHS` (`:75`, `{mission_metadata.py, task_utils/support.py}`) is matched against that value, so scanning a foreign `src_root` readmits the canonical reader's own internals and the census reads **+1** high. This defeats any cross-tree inline measurement — including the baseline comparison a reviewer would run to attribute a floor red. It is the same trap already folded via `#3241` (recorded there for `_gate_coverage`), surfacing independently in the inline gate. | The fix is to key the exclusion on a path relative to the **passed** `src_root` rather than to the gate file's location — a `tests/architectural` tooling change touching a ratchet-bearing gate, not a `meta.json`-read-routing change. WP08 **worked around it and did not fix it**: `scripts/verify_meta_fail_closed_integration_3162.py` restates the exclusion by path **suffix**, which survives relocation, and prints a known-answer control. | Measured: the gate's own scanner returns **7** on `/home/jeroennouws/dev/sk-missions/3162/src` and **8** on a `git archive HEAD src` copy of the identical content. The extra site is `src/specify_cli/mission_metadata.py::_parse_meta_text`. Control that the corrected probe is right: `corrected(HEAD predicate, HEAD tree) = 7 = ` the real gate's real-tree figure — printed by the script as `CONTROL known answer: ... -> PASS`. |

### `C-007`'s handshake has no mechanism — recorded as a gap in the guardrail, not in the measurement

WP08 took 4 timestamped samples spaced 35 s and inspected the named sibling tree. All were empty, and
the cone is disjoint from `tests/sync` / `tests/cli` anyway. But the check is **only process
inspection**: there is **no advisory lock file, no mission-event field and no CLI command** that
reserves or reports the `tests/sync` / `tests/cli` window. Consequences worth recording:

* "no sweep running" can never be more than a sample — a sibling starting one microsecond after the
  last sample is undetectable **by construction**, which is *why* the prompt demands spaced samples;
* a **queued-but-not-started** sweep is invisible, so a sibling about to run `tests/sync` looks
  identical to one that never will;
* `pgrep -af <pattern>` **matches the invoking shell's own command line** when the pattern appears in
  it. Observed: `pgrep -af 'pytest'` returned the `bash -c` wrapper running the `pgrep`. Anyone
  re-running this handshake must exclude that self-match before reading a hit as a real sweep.

Cannot be folded: giving `C-007` a real mechanism is a test-topology/CLI feature, in the same family
as `F17`'s serial-only exclusion list. Belongs with `R1`–`R4`'s lane/ownership mission or a
CI-topology one.

### T051's recorded blocker was a misreading, not a blocker

WP08 first recorded T051 as blocked because it *"needs `gh issue view` rows; filing is forbidden"*.
**Reading is not filing.** The operator direction bars `gh issue create`; `gh issue view` is a read and
is permitted. The register is now complete with 7 of 8 rows verified by quoted live `gh issue view`
output. Recorded because the same conflation would block any future register the direction touches:
the prohibition is on **creating** tracker state, never on reading it.

### Still open, and explicitly NOT answered by WP08

* **`Q4`** (should the degrade sites log when they degrade?) — OPEN, owner is the WP that owns the
  degrade sites' routing. It is `SC-009` row 5's candidate **remedy**, not its answer.
* **`Q11`** (does `merge_driver.py:167 _load_json_object` belong to the bypass class for full
  routing?) — OPEN, operator's, and it is a **question, not a deliverable**.
* **`SC-009` row 7 / `#3240`** — the charter Burn-down Policy §(a) choice between registering
  `inline_meta` in `_baselines.yaml` and recording the deviation is a **governance call**. The absence
  is verified (`grep -c inline_meta tests/architectural/_baselines.yaml` → **0**); the operator's
  answer is outstanding. **No ratchet baseline was regenerated** to make it moot.
* **`#3241`** should be **closable as folded** at the post-PR pass — but note `F21` above is a second
  instance of the `_rel()` half of it, in a different gate, and that half is **not** fixed.

### T052 was NOT performed

History was not compacted, nothing was rebased, nothing was pushed, and no PR was opened. The operator
is landing the PR personally. WP08's `T052` is deliberately left **unmarked**.

### `F22` — the enforced `diff-coverage` gate is structurally blind to every draft-gated integration shard

| # | Finding | Why it cannot be folded | Evidence |
|---|---|---|---|
| F22 | **`diff-coverage` (critical-path, ENFORCED) scores a line as uncovered whenever its only test lives in a shard whose job is skipped on a draft PR.** `integration-tests-core-misc` (and its siblings) carry `&& (github.event_name != 'pull_request' \|\| (github.event.pull_request.draft == false && …))`, so on a draft PR the job is skipped and its `coverage-integration-core-misc-*.xml` is never uploaded. `diff-coverage` still `needs:` it, but `needs` on a skipped job is satisfied, and the download step is `continue-on-error: true` — so the gate proceeds against a **silently smaller** coverage set and fails ENFORCED on lines that are, in fact, tested. The failure is indistinguishable from a genuinely untested line, which is the dangerous part: the honest reading of a red here is "write a test", and a contributor who does so at the integration tier will get the identical red again. This is not specific to this mission — it applies to every critical-path line whose coverage comes only from a draft-gated shard. | The fix is a CI-workflow change (e.g. have `diff-coverage` refuse to run — or run advisory — when any `needs:` job it depends on was skipped, rather than silently scoring against a partial set; or exempt draft PRs from the ENFORCED arm). That is a `ci-quality.yml` topology change touching gate semantics for all PRs, not a `meta.json`-read-routing change. It is the same family as `F17`/`C-007`'s CI-topology bucket. **The in-scope half WAS folded** — see the entry below it. | Measured on PR #3247, run `31137786167` (head `8079df492`): job list shows `integration-tests-core-misc (${{ matrix.shard }})` → **skipped**; the gate step printed `Found 23 coverage report(s)` and **none** is `coverage-integration-core-misc-*`; gate output `src/mission_runtime/resolution.py (77.8%): Missing lines 545,1156`. Both lines are in fact covered by `tests/mission_runtime/test_wp04_degrade_site_fallbacks.py` + `test_wp04_sc007_guard_and_handler_contract.py` — measured locally: running just those two files under `--cov=mission_runtime` yields a missing-line list containing `438-483, 547-552` and `1018-1089, 1192-1213`, i.e. **545 and 1156 are hit**. |

**In-scope half, FOLDED (not deferred):** the two arms are now ALSO pinned at the `fast` tier by
`tests/mission_runtime/test_wp04_degrade_arms_fast_tier.py`, which lands in
`fast-tests-core-misc (core-misc)` — a shard that runs on draft PRs and does contribute a
`--cov=mission_runtime` report the gate consumes. Both new tests were proven load-bearing against
mutants of the arms they cover (narrow the `:545` tuple to `MissionMetaReadError` → 5 failed;
delete the `:1156` arm → 1 failed), with `src/mission_runtime/resolution.py` restored
byte-identically afterwards (`sha256 96c6bc32…8e8b61b`, empty `git diff`).
