---
affected_files:
- path: tests/architectural/census/spec_kitty_home_pin_R1a.yaml
- path: tests/architectural/spec_kitty_home_pin_baseline.yaml
- path: tests/architectural/test_spec_kitty_home_pin_census.py
- path: tests/_arch_shard_map.py
cycle_number: 2
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T03:30:36+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP05
---

# WP05 review — cycle 2

**Reviewer**: reviewer-renata · **Verdict**: **APPROVE**
**Under review**: `fb49a53c2` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-e`
**Diff since cycle 1**: `tests/architectural/test_spec_kitty_home_pin_census.py` only (+175/−45). The census
and baseline YAML are **byte-identical** across `f8ecfc707 → HEAD` (empty diff) — the artefact under
freeze did not move to satisfy a review.
**Directives applied**: DIR-001, DIR-024, DIR-030, DIR-032, DIR-041. **Tactics**: code-review-incremental,
reverse-speccing, test-readability-clarity-check, delete-the-assertion-not-the-test, prove-the-instrument-can-see.

All four cycle-1 items landed. Cycle-1 constructions not repeated.

---

## The adjudication: the "diagnosis refiner" ships. It is also **understated**.

**Ruling: acceptable, and the charge does not survive — the replacement has unique detection power
T022 cannot have.**

Constructed. Mangle `render_census` so the rendered `home_partition` diverges from the classifier's
`Member.home_partition`, and let the **same** mangled renderer produce both the frozen artefact and
T022's fresh re-run:

```
T022 byte-identity GREEN on the mangled artefact: True
NEW per-key check disagreements: 27 -> RED: True
```

The two assertions sit on **opposite sides of a boundary**. T022 compares generator output against
generator output; a renderer defect present *at freeze* is invisible to it forever. The per-key check
compares the **artefact's rendered column** against `discover()`'s in-memory `Member.home_partition`
— it is the only assertion in the package that reads the classifier's partition output directly
rather than through the artefact. The implementer's self-report errs **pessimistic**, which is the
right direction for a self-report and the opposite of cycle 1's defect.

**And it would have shipped at zero.** The condition I set in cycle 1 was: *a set equality; covers
all 40; names the row that moved; survives every R1b removal unchanged.* Four for four. I did not
require independent detection, and I would not: for the 12 members M4 does not label there is no
external anchor, and manufacturing one would be the invent-an-oracle failure C-011 exists to
prevent. **Declining to invent it is the correct call**, and naming the 28/40 reach honestly is what
makes the declining reviewable. This is the same standard by which the exemption word count was
required (it bought something nothing else bought) and `MERGE_BASE_DEFINITION_NAMES` refused (it did
not, at a real cost). Here the cost is ~8 lines, zero R1b maintenance, and the removal of a C-002
violation. The trade is positive with or without the detection.

*(One LOW, no change requested: the docstring's "zero unique detection power" under-sells both forms
— the old `Counter` also crossed the renderer boundary; it simply could not see distribution-preserving
drift. Under-claiming in the safe direction; not worth a cycle.)*

---

## The four, confirmed by construction

**1. `Counter` gone; per-key recomputation in its place.** Your swap figures reproduced exactly:

```
clean     OLD passes: True  | NEW disagreements: 0
swapped   OLD passes: True  | NEW disagreements: 2
          -> cli/commands/test_sync_commands.py :: _isolated_home
          -> delivery/test_body_queue_purge_differential_3030.py :: _isolated_home
```

`Counter` now survives only inside an f-string failure message; `other == set()` kept as a set
equality; `PUBLISHED_PARTITION` deleted. No `len(x) == N` assertion; no literal `40` in any assertion
(prose, and `"0" * 40` as a SHA placeholder).

**2. The diagnosis reaches a real red.** The exact cycle-1 construction that returned *"carries a
diagnosis: False"* now returns:

```
unexpected=[] stale=[('zzz/test_gone.py', 'gone_fixture', 'mp . setenv ( , str ( tmp_path / ) )')] census_hash_ok=False exempt_hash_ok=True
  stale row (…): site absent — deleted
```

`test_t025_the_stale_diagnosis_reaches_the_guard_report` runs the **real** `evaluate` over a
materialised tree and requires the message — the wiring is held, not just the function. The `:699`
docstring is corrected in place and records that its own prior claim was *false as shipped*, which is
the right way to retire a wrong justification.

**3. The caveat is at the claim.** The headline now states T024, then immediately qualifies it with
the 10-red/15-green replay, the `exempt_hash_ok=False` verdict line, and names
`test_t022_neither_exempt_entry_is_a_census_row` and `test_t023_the_census_equals_the_c011_anchor`
as the actual catchers.

**4. The negative control has the only detection power in its neighbourhood.** Mutation table:

```
REAL                   site_present=PASS  site_absent=PASS  neg_control=PASS  wiring=PASS
MUTANT(exists-only)    site_present=PASS  site_absent=PASS  neg_control=FAIL  wiring=PASS
```

`neg_control` is the **only** test the exists-only matcher fails. The division of labour is right:
the control holds the limb's content, the wiring test holds its reachability. My cycle-1 premise
correction about `_NON_MEMBER_HELPER` is recorded in the docstring.

## The two smaller self-reports — both correct

- **`guard_report` diagnoses `stale`, not `unexpected`.** Constructed: a dropped row whose definition
  survives yields `unexpected=1, stale=0` and **0** diagnosis lines. Correct — the two messages are
  about a row whose member is gone, and a surviving definition is `unexpected` by contract.
- **The anchor's `composite_key_from_file` re-read** is unchanged from cycle 1: real, unreachable
  while SC-013 holds, not silent (`discover` raises loudly; a broken `.py` breaks collection first).
  LOW, `record.md` material.

---

## The two findings it surfaced — neither WP05's

### `frozen_at_sha` from `$(git rev-parse HEAD)` — **WP06's record, as an R1b hand-off residual**

My ruling on placement. Four reasons: (i) it is a **procedural** hazard about how the command is
invoked, not a property of the artefact — the shipped `REGENERATION_COMMAND` already reads
`--frozen-at-sha <sha>`, a placeholder, and recommends nothing wrong; (ii) putting it in the census
header means editing `_home_pin_scan.FRAGILITY_NOTE_BASE`, which this package does not own — I
accepted exactly that boundary for T026(1)'s repair instruction in this same package, and reversing
it for a lesser item would be incoherent (DIR-024); (iii) WP06 exists to carry residuals and the R1b
hand-off, and **R1b is where regeneration becomes routine**, which is the only place the hazard
bites; (iv) the consequence is already mechanised — a wrong `frozen_at_sha` reds T022's byte-identity,
which is how it was caught. Record the incident **with** the residual: a guard that caught a real
error in real time, during its own review, is a non-vacuity datum worth more than the warning.

### SC-002b denominator — **confirmed exactly, and correctly routed to WP04**

```
tests/ literal SPEC_KITTY_HOME occurrences: 229 in 97 files  (documented 226/95)
  conftest.py: linenos [338]
  architectural/test_home_owner_never_wins.py: linenos [88, 122]
```

Attribution exact: 226+3=229, 95+2=97, both files WP03's owner and probes, documented figure in
WP04's `test_spec_kitty_home_pin_prefilter.py:237`. Not WP05's file. Worth carrying into WP04's
cycle: the `_home_pin_*` guard modules are **not** byte-hit (they use `scan.NEEDLE`), which is what
keeps the guard from measuring itself — the same property that keeps the census at 42.

---

## Gate figures — reproduced, with one correction that closes cycle 1's gap

- **124 passed in 753.66 s** over the six named files. Reproduced exactly.
- **`test_spec_kitty_home_pin_census.py`: 27 passed** `-n0` (80 s) and `-n auto --dist loadfile`
  (174 s) — NFR-003 parity holds.
- `ruff check` clean; `mypy --strict` clean.

**The correction, and it matters.** That six-file selection **does not include
`test_no_legacy_terminology.py`.** That is precisely why "124 repo-gate tests green" and a red
terminology gate coexisted in cycle 1. The figure is a *selection* result and must never be read as
"the repo gates are green".

**`ceremony`, confirmed:** `_grep_for` uses `git grep --fixed-strings` with **no `-i`** — case-sensitive.
`:769` is the live hit; `:202` `Ceremony` is genuinely **latent** and would trip the moment anyone
lowercases the sentence. Both WP04's; WP05's module has **0** hits. *(Correcting myself: the
`.lower()` calls at `:370`/`:402` belong to the lane-consolidation guard, a different test — they do
not soften this one.)*

---

## Verdict

**APPROVE.** Two MAJOR findings closed with mechanism rather than prose, both held by a test that
would red if the wiring were removed; one MEDIUM closed at the point of the claim; one MEDIUM closed
with the only control in the module that has detection power against its own mutant. The package
retires two of its own wrong docstring claims in place rather than quietly deleting them, which is
the behaviour that makes the next review cheaper.
