---
affected_files:
- path: tests/architectural/_home_pin_synthetic.py
- path: tests/architectural/test_home_pin_synthetic_trees.py
- path: tests/architectural/test_spec_kitty_home_pin_guard.py
- path: tests/architectural/test_spec_kitty_home_pin_prefilter.py
- path: tests/architectural/test_spec_kitty_home_pin_budget.py
- path: tests/architectural/_home_pin_verdict.py
- path: tests/architectural/test_home_pin_verdict_seam.py
cycle_number: 4
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T03:12:37+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP04
---

# WP04 review — cycle 4

**Reviewer**: reviewer-renata · **Verdict**: **APPROVE**
**Under review**: `71ab6b8ea` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-d`
**Diff**: `tests/architectural/test_home_pin_verdict_seam.py`, 6 insertions / 5 deletions, **all of
them comment or docstring lines**. No mechanism touched. Cycles 1–3 stand entirely.

Directives applied: DIR-030, DIR-032 (this is a Terminology Canon defect), DIR-041, DIR-024.

## 1. The reworded sentences carry the argument

They do, and `:202` is now slightly better than what it replaced.

The paragraph's job is to explain why `FROZEN_EXEMPT_KEYS` alone was insufficient: it sits ten lines
from `EXEMPT`, so satisfying it is a two-adjacent-line edit in one file — **ritual added, cost
unchanged** — which is why the external pin exists. The load-bearing claim is *"the cost of forgiving
yourself did not rise"*, and both rewrites state it directly:

* `:202` — *"**The cost of forgiving yourself did not actually rise**, which is the shape of the word
  count it replaced."* This names the mechanism where the old text named a metaphor. A reader who has
  never met the retired concept now gets the point on first reading.
* `:769` — *"…raising no more real cost than the word count it replaced."* Same substance, and the
  contrast lands immediately after: *"This pin lives in a **generated file**, so a self-forgiving
  edit costs two files."*

The comparison to the word count survives in both, which is the part that matters — it is what ties
this back to the cycle-2 finding and tells a future reader that the in-module pin was a repeat of a
defect, not a first attempt at it. Nothing is lost.

## 2. The mutation table is unchanged — sixth consecutive run

Hash limbs disabled **inside** `_home_pin_verdict.evaluate`, the same cross-boundary mutation as
cycles 2 and 3:

```
T5  test_transition_5_a_removed_row_with_the_definition_still_present_reds
T7  test_transition_7_a_41st_accompanied_by_a_new_census_row_still_reds
    test_hash_placement_a_row_removal_without_a_tombstone_reds
    test_e_co_edit_any_delta_to_the_exempt_set_reds_unconditionally
    test_e_co_edit_has_no_tombstone_escape
5 failed, 20 passed
```

Byte-identical to every previous run. A docstring edit that moved the teeth would be the finding;
it did not.

## 3. Counts

* **103 passed / 4 deselected** under `-m "not timing"` across the five WP04 modules plus the
  terminology guard, the golden-count ratchet and WP02's seam guard.
* `test_no_legacy_terminology.py` alone: **10 passed** (reproduced independently in lane-d).
* `grep -ril "ceremony"` across all **eight** owned files, including the generated
  `_home_pin_verdict_exempt_pin.yaml`: **nothing**.
* `ruff check` clean; `mypy --strict` **"no issues found in 7 source files"**.

## 4. The latent second occurrence — constructed, and the claim is exact

I checked the pre-fix blob rather than taking the account on trust. The forbidden-term limb builds
`git grep --line-number --fixed-strings <term>` with **no `-i`** (`test_no_legacy_terminology.py:100-111`;
the case-insensitive helper at `:242` serves a different phrase check). Against `ee4728edf`:

```
case-sensitive   → 769 only          ← the one that failed CI
case-insensitive → 202 and 769       ← :202 was capitalised, and latent
```

So the second occurrence was real, invisible to the guard, and would have tripped the moment anyone
lowercased the sentence. Sweeping case-insensitively rather than repairing only the reported line was
the right call, and the `.yaml` inclusion is correct — the guard scans `tests/**/*.yaml`, so a
module-only sweep would have missed the generated artefact.

## 5. The root-cause note belongs in the record

The implementer's framing is the transferable part and I endorse it: *"That is the miss, not the word
choice."* It ran full `tests/architectural/` selections **by module, never the directory**, and
skipped the one-line, 0.1-second check `CLAUDE.md` prescribes for prose changes. The word was not
banned for being wrong — the repository reserves it for a retired concept — so a coinage collided
with a canon it had not checked. Same class as its four self-reported design defects, in vocabulary
rather than mechanism.

**The reviewer half is mine and I record it too.** I ran module-scoped selections in all three
previous cycles, for speed, and correctly — and that is exactly why none of them could see this. A
reviewer who only ever selects the modules under review cannot see a directory-scoped or
repository-scoped guard. For a prose-carrying change, the cheap directory-level run is worth its two
minutes; I will take it on the next mission whose diff is mostly documentation.

## 6. Standing

The cycle-3 follow-ups are unaffected and remain open and non-blocking: **[MED]** the exemption is
module-scoped while every stated reason is construct-scoped (name the signals, not the constructs);
**[LOW]** the pin's ceiling is absent from the module's own "what this guard cannot see" list.

---

**Verdict: APPROVE.** Two sentences, argument intact, teeth unmoved, and the sweep found more than it
was asked to. WP05's lane may need a rebase once this lands.
