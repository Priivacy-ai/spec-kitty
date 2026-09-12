---
affected_files:
- path: tests/architectural/_home_pin_synthetic.py
- path: tests/architectural/test_home_pin_synthetic_trees.py
- path: tests/architectural/test_spec_kitty_home_pin_guard.py
- path: tests/architectural/test_spec_kitty_home_pin_prefilter.py
- path: tests/architectural/test_spec_kitty_home_pin_budget.py
- path: tests/architectural/_home_pin_verdict.py
- path: tests/architectural/test_home_pin_verdict_seam.py
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T22:43:54+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP04
---

# WP04 review — cycle 1

**Reviewer**: reviewer-renata · **Verdict**: **APPROVE** (three findings, none of them a false green in the mechanism)
**Under review**: `964aedc28` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-d`
**Files** (`git show --name-only` confirms exactly these five, nothing else):
`tests/architectural/_home_pin_synthetic.py`, `test_home_pin_synthetic_trees.py`,
`test_spec_kitty_home_pin_guard.py`, `test_spec_kitty_home_pin_prefilter.py`,
`test_spec_kitty_home_pin_budget.py`.

Directives applied: DIR-001 (architectural integrity), DIR-024 (locality of change), DIR-030 (test and
typecheck quality gate), DIR-032 (conceptual alignment), DIR-041 (tests as scaffold, not friction); project
DIR-005–DIR-009 via the charter's review checklist, DIR-013 noted as governed by C-013 here.
Tactics: code-review-incremental, reverse-speccing, language-driven-design, test-readability-clarity-check,
test-scaffolding-as-design-smell, delete-the-assertion-not-the-test.

Method: I did not read the red-first claim and believe it. I re-ran it. Eight mechanisms were disabled at
**runtime** through a reviewer-owned pytest plugin on `PYTHONPATH` (no file in the repository was edited;
`git status` is clean at the end), and I recorded which named assertion goes red.

---

## 1. The headline claim — reproduced, 8 of 9 rows

Baseline, this runner (`/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest`, `-n0`,
`-p no:cacheprovider`): **50 passed** across the three `architectural` modules, **4 passed** for the
`timing` module. 54/54 green.

| Mutation (runtime, no edit) | Reported newly RED | Observed newly RED |
|---|---|---|
| absorbs in already-known files | T3, not T4 | **T3 only** — T4 green |
| absorbs in brand-new files | T4, not T3 | **T4 red, T3 green** (my mutation was coarser than the implementer's and also caught T1/T5/T6/T8; the load-bearing half — T4 reds, T3 does not — holds) |
| keys compared bare (19-key collapse) | T8 | **T8 only** |
| hash limb removed | T5, T7 | **T5, T7** (+ the three T018(ii)/(iii) hash cases, expected collateral) |
| FR-010 owner normalisation removed | T6 | **T6 only** |
| equality weakened to containment | SC-004 set-equality | **`test_the_comparison_is_set_equality_and_not_containment` + `test_sc004_the_guard_reds_on_a_stale_census_row`** |
| `kind` read at innermost def | C-004 witness | **`test_c004_synthetic_outermost_versus_innermost_witness`** |
| `E` union dropped | T1–T7 + SC-004 | **T1–T7 + SC-004** (+ the three "must PASS" hash cases) |
| `except SyntaxError: continue` | SC-013 | not re-run (cannot be induced without editing `_scan_records`); SC-013 is covered behaviourally **and** by AST over three modules **and** by a positive control that plants a real handler — all three green |

**T3 and T4 are not redundant.** Absorb-known reds T3 and leaves T4 green; absorb-new reds T4 and leaves T3
green. The pair discriminates in both directions.

**T8 is the only test that keeps the 19-key collapse caught.** Under a comparison-level bare-key regime,
exactly one test in the module goes red, and it goes red on the discriminating assertion
(`verdict.unexpected == {members[0].key}`), not on `not verdict.ok` — `not verdict.ok` survives on the hash
limb, so a reviewer who accepted only that assertion would have been fooled.

**The instrument check is real and it is first.** `test_spec_kitty_home_pin_guard.py:421-428` asserts the
bare `composite_key` is byte-identical across the pair, and that the 3-tuples still differ **on the relpath
component**, *before* line 430 renders the census and line 434 performs the removal. Ordering verified by
reading; content verified by the mutation.

**T7 is a hash red, not an equality red.** The test asserts `verdict.unexpected == frozenset()` and
`verdict.stale == frozenset()` explicitly and then `not verdict.census_hash_ok` — and the hash-removal
mutation reds it. Adding a census row does satisfy `discovered == census ∪ E` by construction; only the
pinned key-set hash refuses it.

**Transition 6's witness** is declared `(monkeypatch, canonical_home)` with **no `tmp_path`**
(`:346-349`); `canonical_home` (`:442-456`) **yields** a root from `tmp_path_factory`, i.e. the live
`runtime_home` shape, never the `None`-returning canonical owner. The test additionally asserts the
synthetic 41st declares no `tmp_path` of its own (`:372`). **Transition 8's colliding pair is in different
files** — `one/test_collide.py` / `two/test_collide.py` — asserted, not merely arranged.

**Eight transitions.** `test_transition_1` … `test_transition_8`, one tree and one assertion each. Counted.

---

## 2. The rest of the checklist

* **T015 — nothing checked in.** The commit adds exactly the five owned files. `git status` is clean.
  `test_no_member_of_the_real_tree_lives_under_a_fixture_root` is green **and** its positive control
  (`test_the_fixture_root_matcher_can_actually_see_a_planted_member`) is green, so the population-0 claim is
  not its own proof. `_home_pin_synthetic.py` holds no assertions, asserted by AST through the seam's parser.
* **T017** — the synthetic outermost-vs-innermost witness ships and reds under the kind-at-innermost
  mutation, so C-004 no longer rests on `:1165` alone.
* **T019 — the differential is an observation, not a reconstruction.** `recording_parses` rebinds
  `scan.parse_module`, which `_scan_records` resolves as a module global at call time, so the recorded set is
  what `discover` really parsed. Measured here: **108 parsed pre-filtered vs 2747 unfiltered**, matching the
  implementer's report. The unfiltered set is compared to an `rglob` **written inline in the test**. Cost
  **1.378 s / 9.159 s, total 10.537 s** — and the 90 s figure appears only in a printed line; the sole
  assertion on the clock is `> 0.0`. It is an envelope, not an assertion.
* **T021** — `pytestmark = pytest.mark.timing` and nothing else; `timing-nfr-serial` selects `tests/ -m
  timing` and the `arch-adversarial` pole carries `and not timing`, so the routing is correct.
  `time.perf_counter()` throughout — the only `time.time()` occurrences are inside docstrings and the
  collection guard is AST-based, which the full collection in every run above proves. Expected set from an
  inline `rglob`. Warm runs **[1.277, 1.277, 1.282] s** against 6 s; 2747 files enumerated.
* **Golden count** — `test_golden_count_ban.py` 9 passed; the frozen baseline is untouched (not in the
  commit); no `len(x) == N` in the diff.
* **Orphan surfaces** — `test_gate_coverage.py` 37 passed, so all four collected modules are positively
  selected by a CI job. `tests/_arch_shard_map.py` not edited.
* **NFR-004 / charter checklist** — `ruff check` clean on the five files; `mypy --strict` (MYPYPATH=src)
  **Success: no issues found in 5 source files**; zero `# noqa`, zero `# type: ignore`, zero pragmas. The
  `ExemptPair` alias is a real fix for a real defect (`ExemptSet` admits `tuple[()]`), not a suppression.
* **C-006 / DIR-024** — nothing under `src/`, no existing test module changed, no `conftest.py`. Locality is
  exact.
* **Terminology canon** — no `feature`/`--feature` in the added lines.

---

## 3. Findings

**[MED] `test_spec_kitty_home_pin_budget.py:120-137` — `test_nfr003_the_verdict_is_identical_under_both_parallel_modes` asserts in-process determinism, and the digest it publishes for the cross-mode comparison is not comparable across processes.**
`hash(frozenset(...))` over strings is per-process randomised. Two identical serial runs printed
`-8111599440180932904` and `-4018342587456936278` for the same 40-member class. Under `-n auto` xdist
swallows the print entirely. So the one artefact offered to discharge T021(4) cannot discharge it. The
docstring is honest about the limitation; the **test name is not**, and under DIR-041 the name is the
contract a future reader reads.
*I constructed the missing evidence myself*: the module is **4 passed under `-n0`** and **4 passed under
`-n auto --dist loadfile`**, so NFR-003 holds empirically for this module — but nothing in the repository
records that.
**Recommendation**: publish a stable digest (the seam already ships `render_baseline`/`_sha256_of` for
exactly this shape) and either rename the test to what it asserts or carry the two-mode figures into WP06's
`record.md`. Do not absorb this silently.

**[MED] `test_spec_kitty_home_pin_prefilter.py:223-248` — the figures SC-002b exists to publish are not published, and the stated reason for their divergence from the spec is the wrong reason.**
(a) The print is consumed by `capsys.readouterr()`. Running the module with `-s`, the other three reported
lines appear and this one does not. On the primary failure path (`assert bound == set()`) the print never
executes, so the denominator is absent from the failure message T020(3) requires it in.
(b) The docstring attributes the divergence from the spec's 229/98 to staleness. It is **entirely a scope
difference**, which I measured: `tests/` = 0 bound / 226 occurrences / 95 files; `src/` = 0 / 3 / 3.
226 + 3 = **229**; 95 + 3 = **98**, exactly the spec's figure. `spec.md:372` and `:518` state SC-002b over
`src/ ∪ tests/`. The scoping distinction is therefore **not stated** — a wrong reason is stated in its place.
(c) The empty-set limb here is a weaker duplicate of WP01's
`test_every_inert_sub_form_has_population_zero_over_the_real_tree[SC-002b]`, which runs over **both** roots
(`test_home_pin_scan_limbs.py:748-749`), and WP01's `test_sc002b_publishes_its_denominator` prints
**229 in 98 files** to real test output — I saw it. The canonical discharge is WP01's; this module's job is
the binding, and the binding is correct.
**Recommendation**: name the scope in the docstring, move the print above the assertions (or drop the
`capsys` self-assertion, which asserts only that the test printed), and cite WP01 as the canonical figure.

**[LOW] `test_spec_kitty_home_pin_guard.py:128-130` — the tombstone equation is an inference and is recorded nowhere binding.**
`hash(census ∪ tombstones) == pinned` is well grounded — `plan.md:221` says "shrink-only key-set hash plus
an explicit tombstone list" and the §5 table says "reds → tombstone" — but the equation itself is stated in
no spec, plan or contract. Self-flagged by the implementer, correctly. If R1b implements tombstones
differently, T018(ii)'s four cases green against a semantics nothing else shares.
**Recommendation**: WP06 records the equation, or the seam contract carries it, before R1b is planned.

**[LOW] `test_spec_kitty_home_pin_guard.py:359` — a decorative `monkeypatch.setenv("R1A_WITNESS_HOME_ROOT", …)`.**
Nothing reads that variable; it exists to give `monkeypatch` a use. Harmless, but it sits inside the one
witness whose entire point is shape fidelity, where a reader may take it for load-bearing. `ruff`'s `ARG` is
relaxed for `tests/**`, so the parameter needs no use at all.

---

## 4. Adjudications

**Deviation 1 — `assignment_bound_env_key_constant`. ACCEPTED; binding to `"SC-002b"` is right.**
The id exists in no code anywhere in the repository: `grep -rn` finds it only in the WP01 and WP04 prompts
and in WP04's own explaining comment. `_home_pin_scan.INERT_LIMBS` registers the premise as `"SC-002b"` and
`inert_hits` dispatches on that spelling. Binding to the brief's name would red on day one and would be
repairable only by editing WP01's owned module — barred by C-006 and by `owned_files`. **The quadruple still
closes**: I ran `test_inert_registry_completeness_is_a_quadruple` green — 14 FR-007 table rows ∪ {SC-002b}
== `INLINE_EXPECTED` == `scan.INERT_LIMBS` == `CONTROL_IDS`. Raising it in a comment rather than silently
repairing it is the right handling.

**Deviation 2 — `record.md` left to WP06. ACCEPTED, with a correction.**
`record.md` is not in WP04's `owned_files`, six WPs reference it, and WP03 was running in a sibling lane;
writing it would have been a cross-WP edit under concurrency. The claim that "the figures published in test
output are sufficient until WP06" holds for three of the four figure sets — I saw all three with `-s`
(108/2747 parsed; 1.378 s / 9.159 s; warm runs [1.277, 1.277, 1.282] s and 2747 enumerated). It does **not**
hold for SC-002b's pair (eaten by `capsys`) or for the NFR-003 digest (per-process garbage). Deferral
accepted; WP06 must carry both, and the two publication defects above should be fixed so the figures are
real when WP06 collects them.

---

## 5. The self-reported defect — judgement, and it bears on WP05

**The promotion is needed, and this is the moment. It is NOT WP04's to do.**

The seam ships `discover`, `render_census`, `render_baseline`. It ships **no verdict**. `evaluate`,
`census_keys`, `hash_of_key_set` and the tombstone rule live in `test_spec_kitty_home_pin_guard.py`. WP02's
anti-drift guard polices the **scanner** among modules that import `_home_pin_scan` and says in its own
docstring that it cannot see "a second copy of the predicate written without importing `_home_pin_scan` at
all". WP05 must assert `discovered == census ∪ E` plus both hash limbs over the real tree and has no
importable seam for any of it. That is the drift `_sole_door_scan.py:13-27` records as a live incident,
one WP ahead of itself.

**One correction to the implementer's framing.** The stated obstacle is not real:
`from tests.architectural.test_spec_kitty_home_pin_guard import evaluate` does **not** apply that module's
`pytestmark` to the importer and does **not** import its fixtures; `tests/architectural/__init__.py` exists
and every module in this package already imports through it. The real objection is architectural (DIR-001):
a shared primitive parked in a leaf test module is a boundary violation, and a peer WP importing another
WP's `test_*.py` inverts the dependency. That objection stands on its own and is sufficient.

WP04 could not have fixed it: `_home_pin_verdict.py` is not in its `owned_files`, and C-006 forbids it
touching anything else. **Routed to the orchestrator, before WP05 is claimed** — pick one:

* (a) add `tests/architectural/_home_pin_verdict.py` to WP05's `create_intent`/`owned_files` and make its
  first subtask the extraction, with a follow-up cycle re-pointing WP04's module at it; or
* (b) dispatch a small Op that extracts the verdict and re-points WP04's module, before WP05 starts.

Either way the WP02 seam guard picks the new module up **without being edited** — its consumer set is
discovered by AST, not hard-coded. Do not let WP05 start without one of the two: the cheapest path for WP05
today is a second copy, and a second copy of the verdict is worse than a second copy of the scanner, because
the scanner has teeth and the verdict does not.

---

## 6. What I could not check

* The `except SyntaxError: continue` mutation — not inducible without editing `_scan_records`. SC-013 is
  covered three ways instead and all three are green.
* `discover()` at 42 in WP03's lane — not visible here and not WP04's concern, as briefed.
* The guard under contention. `timing-nfr-serial` measures it uncontended; the serial figure is a floor.
  The module says so itself.
* Whether any given census row deserves to exist. R1a adjudicates nothing, by design.

**Verdict: APPROVE.** The mechanism is real, red-first, and I could not make it green for the wrong reason
in eight independent mutations. The three findings are publication and naming defects around it, and the
one architectural item is out of this WP's reach and is routed above.
