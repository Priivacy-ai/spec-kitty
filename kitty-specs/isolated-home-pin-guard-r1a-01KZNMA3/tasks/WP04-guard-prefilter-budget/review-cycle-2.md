---
affected_files:
- path: tests/architectural/_home_pin_synthetic.py
- path: tests/architectural/test_home_pin_synthetic_trees.py
- path: tests/architectural/test_spec_kitty_home_pin_guard.py
- path: tests/architectural/test_spec_kitty_home_pin_prefilter.py
- path: tests/architectural/test_spec_kitty_home_pin_budget.py
- path: tests/architectural/_home_pin_verdict.py
- path: tests/architectural/test_home_pin_verdict_seam.py
cycle_number: 2
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T00:31:08+02:00'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP04
---

# WP04 review — cycle 2

**Reviewer**: reviewer-renata · **Verdict**: **REJECT** (narrow — two required changes, one line each, both constructed below)
**Under review**: `84a840b30` + `ad61b3329` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-d`
**Files**: `_home_pin_verdict.py` (new), `test_home_pin_verdict_seam.py` (new), and re-points in
`test_spec_kitty_home_pin_guard.py`, `test_spec_kitty_home_pin_prefilter.py`,
`test_spec_kitty_home_pin_budget.py`.

Directives applied: DIR-001, DIR-024, DIR-030, DIR-032, DIR-041. Tactics: code-review-incremental,
reverse-speccing, test-scaffolding-as-design-smell, delete-the-assertion-not-the-test.

**The reject is not about the extraction, which is right, nor about the two MEDs from cycle 1, which
are properly closed.** It is about two one-line holes in the enforcement this pass exists to install,
both of which I walked through rather than inferred. WP05 has not started; the person who meets
these holes is WP05's implementer, and there is no cheaper moment than now.

---

## 1. The adjudication asked for: `test_every_exemption_states_a_reason`

**Not acceptable as shipped. `EXEMPT` growth must become a review event. I agree with the
coordinator's read, and the argument is stronger than stated.**

### I walked the door rather than describing it

Taking the module's own positive control 1 — the copy it exists to catch — and adding one `EXEMPT`
row with twelve words of content-free filler (`"This module is fine and does not need the shared
verdict seam"`):

```
before:  offenders = ['architectural/test_hand_rolled.py']
after:   offenders = []
limb 'still needed'   would flag the new row: False
limb 'states a reason' would flag the new row: False
limb 'names real files' would flag the new row: False
```

All three `EXEMPT` limbs accept it. The module the guard was written to catch is fully forgiven, and
nothing in the package can tell that filler from a reason. The implementer's own sentence — *"the
softest target in the package, and I made it softer by making it feel rigorous"* — is exact.

### The tension the implementer declined to resolve does not exist, and the repository says so

The implementer declined the fix because a frozen-set assertion is *"one refactor away from the
golden-count ratchet I've been avoiding all mission."* That is inverted, and the ratchet's own module
docstring says which way round it goes (`test_golden_count_ban.py:4-9`):

> the `len(<collection>) == <int>` "golden-count" friction: an assertion that pins a bare
> cardinality **where a set/frozenset-equality would express the real contract** (adding, removing,
> or renaming a member should force a *content* edit, not silently pass at an unchanged count).
> `tests/status/test_models.py::test_lane_member_names_exact` (WP07) is the exemplar this sweep
> follows: **`len(Lane) == 10` became an exact frozenset of member names.**

The frozen set is not one refactor away from the ratchet; it is the state the ratchet **converts
to**. And the regression the implementer fears — someone later collapsing `set(EXEMPT) == {…}` into
`len(EXEMPT) == 3` — is the exact AST shape (`len(<expr>) == <int>`, either operand order) that
`test_golden_count_ban` matches, in a directory sitting at **25/25 with zero headroom**. The fix was
declined out of fear of a hazard already mechanised against, by the very guard feared.

The word count is on the wrong side of that line and escapes the mechanised ban only on its operator
— `len(why.split()) < 10` is `Lt`, not `Eq`. It is the golden-count anti-pattern one character away
from being caught automatically.

### This mission has already decided this exact question, twice

* **`E`.** Structurally identical: an enumerated exemption set, one `why` per entry. The mission
  bound it with a **type** (`tuple[Exempt, Exempt]`, a third entry is a `mypy --strict` error) plus a
  **pinned hash with no tombstone path** — and `_home_pin_scan.py:145-148` says the quiet part:
  *"`why` is prose and entitles nothing the type does not already grant."* WP04 spent T018 proving
  that mechanism, then gave its own exemption set a word count.
* **Transition (4).** `extra_member_under_a_novel_name` exists because *"the novel name is what
  separates 'the count changed' from 'this row is new'."* A frozen key set is that distinction
  applied to `EXEMPT`; a word count is the count.

### What I require, and what I do not

Required: **`EXEMPT`'s key set is pinned by content**, so a fourth entry cannot land without a
deliberate edit naming the module being forgiven. The obvious form is a frozen constant plus
`set(EXEMPT) == FROZEN_EXEMPTIONS`; the form is the implementer's choice, the property is not.

**Do not delete `test_every_exemption_states_a_reason`** — its docstring is right that a nameless
exemption entitles everything. Keep the test, drop the threshold: assert the reason is **non-empty**,
which is this mission's own idiom for this field (`test_e_is_typed_as_a_fixed_pair_at_the_alias`
asserts `all(entry.why for entry in exempt)`). Delete the assertion, not the test.

I could not verify the coordinator's `MERGE_BASE_DEFINITION_NAMES` citation — it does not appear
under `tests/` in this lane, so it is presumably WP03-lane-local. Nothing above depends on it.

---

## 2. Second required change — the guard cannot see the wrong-shaped copy

`verdict_comparisons` (`test_home_pin_verdict_seam.py:222-232`) fires only on `ast.Eq`. I
materialised three probes and ran the module's **own** matchers over them:

| Probe | Result |
|---|---|
| `discovered <= census \| exempt`, no artefact read | **signals = {}, offenders = none** |
| census path assembled as `ROOT / "census" / "spec_kitty_home_pin_R1a.yaml"`, operands named `rows` | **signals = {}, offenders = none** |
| `discovered == census \| exempt` (control) | caught — `verdict-comparison` |

The first is the serious one. A **subset-only ratchet** is the failure `spec.md` §0.4 spends a page
refusing, and the failure this very WP ships `test_the_comparison_is_set_equality_and_not_containment`
to catch. Its operands name **three** of the four vocabulary words and it still escapes, purely
because the operator is `<=`. The guard against a second copy is blind to the one second copy whose
shape is already known to be wrong — a one-character evasion.

**Required**: the comparison signal must not turn on the operator. The vocabulary test already
carries the discrimination; restricting to `Eq` adds a hole and nothing else. Broadening to the
comparison operators (`Eq`, `NotEq`, `Lt`, `LtE`, `Gt`, `GtE`) closes it, and the containment probe
above is the control to ship with it.

---

## 3. Judging the honest-limits enumeration — **not complete**

The three stated limits are accurate and well drawn. A fourth is missing, and it is the probe-2 row
above: **an artefact read the matcher cannot recognise because the path is assembled rather than
written as a contiguous literal.** It is not covered by limit 1, which requires *no artefact read*;
here there is one. This mission already has the vocabulary for the shape — T020's *"cannot see a
constant **assembled at runtime** rather than written as a literal"* — so it should be named in the
same terms rather than discovered later.

Two smaller escapes are fairly subsumed under limit 1 and I do not require them enumerated: a digest
via `hmac`/`zlib.crc32` (outside `_HASH_NAMES`), and operands named entirely outside the vocabulary.

---

## 4. What I verified green

* **The mutation table holds for a third pass, across the new boundary.** I re-ran two, patching
  **inside** the seam rather than around it, which is the only version of this spot-check that means
  anything:
  * hash limbs disabled inside `_home_pin_verdict.evaluate` → **T5, T7** + the same three
    T018(ii)/(iii) collateral tests. Byte-identical to cycle 1.
  * FR-010 normalisation removed inside `_home_pin_scan` (two boundaries away) → **T6 only**.
    Byte-identical to cycle 1.
  Moving the code did not move the teeth.
* **Both cycle-1 MEDs closed.** The NFR-003 digest is `sha256` and byte-identical across two separate
  processes — `e2604836e22c59476a83adcddab655fc970f6802a15b2835ea6c7fe35129efdd` — and now publishes
  kinds `{fixture: 30, test-body: 10, helper: 0}` and partitions `{A: 27, B1: 11, B2: 2}` besides.
  SC-002b prints unconditionally **with the scope in the line**: *"over src/ u tests/ — src: 0/3/3;
  tests: 0/226/95"*, which is my cycle-1 reconciliation, and the `capsys` drain is gone.
* **`_home_pin_gate.py`'s absence from `EXEMPT` is right, and I measured it rather than trusting it**:
  it imports the scanner and its signal set is `{}`. Pre-emptively exempting a module that does not
  trip would be the broad-pattern habit the list exists to avoid. Correct as shipped.
* **The scanner-import gate is load-bearing, and by more than claimed.** Raw signals over
  `src/ ∪ tests/`: **103** modules. Gated: **4**, offenders **{}**. The docstring's "40+" is a true
  and conservative lower bound.
* **Counts, all confirmed**: 64 architectural passed, 4 timing passed, 52 repo gates passed
  (`test_gate_coverage` + `test_golden_count_ban` + `test_home_pin_seam_no_second_copy`), `ruff
  check` clean and `mypy --strict` "no issues found in 7 source files", zero `# noqa`, zero
  `# type: ignore`, zero `len(x) == N`, no `time.time()` call (docstring mentions only; the guard is
  AST-based and every collection above passed).
* **The seam itself.** No pytest dependency; `_home_pin_scan` + `yaml` + stdlib only. My cycle-1
  correction was carried and — better — the false `pytestmark` claim is **retracted in place** at
  `_home_pin_verdict.py:12-15` rather than deleted, so nobody re-derives it. The tombstone
  normative/inferred split at `:35-53` is now accurate: FR-004(b) and `spec.md:420` do state the
  property; only the arithmetic is the module's, and it says so. My cycle-1 LOW is closed better than
  I asked.
* The regex false positive shipped as `test_prose_about_the_artefacts_is_not_an_artefact_read` is
  the right instinct — a defect found and converted into a permanent control.

---

## 5. Findings

**[HIGH — required] `test_home_pin_verdict_seam.py:479-482` — `EXEMPT` growth is not a review event.**
One dict row plus ten words forgives the exact module positive control 1 exists to catch; all three
`EXEMPT` limbs accept content-free filler (constructed, §1). Pin `EXEMPT`'s key set by content;
keep the reason test, drop its threshold to non-empty.

**[HIGH — required] `test_home_pin_verdict_seam.py:222-232` — the comparison signal is `ast.Eq`-only,
so a containment ratchet is invisible.** `discovered <= census | exempt` names three of the four
operand words and escapes on the operator alone (constructed, §2). Broaden beyond `Eq`; ship the
containment probe as the control.

**[LOW] `test_home_pin_verdict_seam.py:19-21` — the gated population is stated as "three"; measured it
is four** (`_home_pin_verdict.py`, `test_home_pin_scan_limbs.py`, `test_home_pin_verdict_seam.py`,
`test_spec_kitty_home_pin_guard.py`). Three is the `EXEMPT` count, not the population. The
qualitative claim is unaffected — all four are genuine R1a artefacts — but this is a published figure
that does not follow from its rule, which this mission keeps catching itself doing. The number is
prose only; `test_the_verdict_work_population_is_non_empty` correctly asserts non-emptiness rather
than a count (C-002).

**[LOW] `test_home_pin_verdict_seam.py:41-51` — the honest-limits list omits the assembled-path
artefact read** (§3). Name it in T020's existing terms.

---

## 6. What I did not re-run

The other six cycle-1 mutations (the coordinator asked for two spot-checks and I ran two, both
chosen to cross a module boundary); `except SyntaxError: continue`, still not inducible without
editing `_scan_records`; the guard under contention.

---

**Verdict: REJECT.** Two one-line changes in files WP04 already owns, both constructed above so
there is nothing left to investigate, plus two LOW corrections to published prose. Everything else in
this pass is right, and the extraction closed cycle 1's architectural finding properly. Shut the two
doors before WP05 is claimed.
