---
affected_files:
- path: tests/architectural/census/spec_kitty_home_pin_R1a.yaml
- path: tests/architectural/spec_kitty_home_pin_baseline.yaml
- path: tests/architectural/test_spec_kitty_home_pin_census.py
- path: tests/_arch_shard_map.py
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T02:46:26+02:00'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP05
---

# WP05 review — cycle 1

**Reviewer**: reviewer-renata · **Verdict**: **REJECT** (narrow — two required changes, two recommended)
**Under review**: `f8ecfc707` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-e` (fully integrated tree; WP01–WP04 merged)
**Files**: `tests/architectural/census/spec_kitty_home_pin_R1a.yaml`, `tests/architectural/spec_kitty_home_pin_baseline.yaml`, `tests/architectural/test_spec_kitty_home_pin_census.py` — exactly three, `git diff --stat f8ecfc707~1 f8ecfc707` confirms.
**Directives applied**: DIR-001, DIR-024, DIR-030, DIR-032, DIR-041. **Tactics**: code-review-incremental, reverse-speccing, test-readability-clarity-check, delete-the-assertion-not-the-test, prove-the-instrument-can-see (construct, don't read).

This is a strong package. Every finding below was reached **by construction**, not by reading.

---

## The reframing, verified by construction — it is correct, and it is understated

Regenerating the census **without** `--exempt-module` (42 rows, `E ⊆ census`) and replaying all 25
tests against those artefacts in-process:

```
total 25  RED 10  GREEN 15
*** test_t024_the_real_tree_is_set_equal_to_the_census_union_e: GREEN
```

`unexpected=[] stale=[] census_hash_ok=True exempt_hash_ok=False` — the famous assertion's two limbs
(`(unexpected, stale) == (∅, ∅)` and `discovered == census | E`) are **both true** on the defective
artefact, because `census ∪ E` is a no-op union when `E ⊆ census`. What actually caught the defect,
exactly as reported: `test_t022_neither_exempt_entry_is_a_census_row` and
`test_t023_the_census_equals_the_c011_anchor` (plus `t022`'s byte-identity and `t024`'s
`exempt_hash_ok`). The implementer's self-report is accurate in every particular.

---

## Findings

### [MAJOR] `tests/architectural/test_spec_kitty_home_pin_census.py:686` — `Counter(partitions.values()) == PUBLISHED_PARTITION` is the counted assertion this WP forbids. Replace it.

**Adjudication requested; adjudicated: it must be replaced.**

Three separate places in WP05's binding text say the same thing. DoD #2: *"every comparison is
against a key **SET**."* C-002: *"no counted definition of done anywhere in this WP."* Risk table:
*"Every assertion is a **SET** comparison, never a count."* `Counter(...) == {"A": 27, "B1": 11,
"B2": 2}` is a comparison against three counts summing to 40. It evades
`test_golden_count_ban` only because that matcher is an `ast.Compare` over a literal `len(...)`
call (`test_golden_count_ban.py:170-183`) — the ban's *shape*, not its *purpose*, is what it slips.

Not a matter of taste; three constructed facts:

1. **It is blind to the drift it exists to catch.** Swapping two members' labels (`A↔B1`) leaves
   `Counter` identical while the labels demonstrably changed — verified. A distribution is
   invariant under the exact classifier drift a per-member check sees.
2. **It has no unique detection power.** `test_t022_both_artefacts_are_reproduced_byte_identically_by_the_documented_command`
   already pins every row's `home_partition` against a fresh generator run, per row, with a byte
   diff that names the row. Any classifier drift reds T022 first and better.
3. **It reds on R1b's first adjudication, and the cheapest green is a numeric hand-edit.** Every
   tombstoned row shifts one of the three numbers. WP01's partition assertion was moved here
   *because it moves with `E`* — this form moves with the **census**, which is worse. This is the
   last place the figure is asserted anywhere, and it ships in the shape the Mission spent five
   subtasks removing.

And a terminology inconsistency (DIR-032): FR-003 states `home_partition` *"appears in no key, no
hash and no equality"* — this is an equality over it, sitting thirty lines above a test named
`test_t026_home_partition_holds_no_key_no_hash_and_no_equality`.

**On the proposed replacement.** *"A per-partition key-set equality derived from the anchor"* is
**not constructible as stated**: `members.json` carries no partition labels (fields are
`path`/`qual`/`line`/`sites`/`fixture` — verified over all 40 entries). M4 is the only external
label source and covers 28 of 40.

**Recommended form** — `delete-the-assertion-not-the-test`: keep the test, keep the `other == set()`
limb, and replace the `Counter` line with a per-key recomputation against `discover()`:

```
assert {k for k in census_partitions() if census_label[k] != discovered_label[k]} == set()
```

A set equality; covers all 40 (M4 covers 28); names the row that moved; **survives every R1b
removal unchanged**. If FR-003's published figure must also be pinned, pin it as a frozen
**key set per partition**, never as a cardinality.

### [MAJOR] `test_spec_kitty_home_pin_census.py:381-391` + `:485-492` — the stale-row diagnosis is never emitted at a real red, and a docstring argues away the alternative site on that false premise.

T025(1): *"For **any stale row** the guard re-runs the EFFECT LIMB ALONE ... and emits one of two
distinct messages."* As shipped, it does not. `grep -rn "diagnose_stale_row\|effect_limb_sites\|SITE_PRESENT_MESSAGE\|SITE_ABSENT_MESSAGE" tests/`
returns **no consumer outside this module's own two T025 tests**. The real-tree assertion messages
with `str(result)`. Constructed, a genuine stale row on the real tree says:

```
unexpected=[] stale=[('zzz/test_gone.py', 'gone_fixture', 'mp . setenv ( , str ( tmp_path / ) )')] census_hash_ok=False exempt_hash_ok=True
```

Neither diagnosis message appears. The tombstone path T025 exists to close is **open at the moment
of the red**.

Compounding it: the docstring at `:699-707` justifies omitting T026(1)'s header repair instruction
because *"the instruction ships in `SITE_PRESENT_MESSAGE` instead, which is strictly the better
site ... the diagnostic fires **at the moment of the red**."* That premise is false as shipped, so
the repair instruction reaches a maintainer facing a real `:1165` red through **neither** route.
(The locality argument for not editing WP01's `FRAGILITY_NOTE_BASE` is accepted under DIR-024 — the
fix belongs here.)

**Repair (~2 lines):** carry `sorted(diagnose_stale_row(TESTS_ROOT, k) for k in result.stale)` in
`test_t024_the_real_tree_is_set_equal_to_the_census_union_e`'s assertion message, and correct the
`:699-707` docstring to describe what the code does.

### [MEDIUM] `test_spec_kitty_home_pin_census.py:8-10` — the module docstring's headline overstates T024, in the package plan §10 warned would be skimmed.

*"The single assertion that actually proves the class is frozen is
`test_t024_the_real_tree_is_set_equal_to_the_census_union_e`"* — read unconditionally, and it is
green on the 42-row artefact. The caveat **is** in the package (the census `fragility_note`; the
`t022` docstring at `:275-284`, which says *"green while checking nothing ... the state this
package was blocked on"*) — but 200+ lines below the claim, in the two places a skimming reader
reaches last. Plan §10's whole point is that attention follows the headline.

**Repair:** make the headline carry the conditional and name its co-dependencies — T022's
`neither_exempt_entry_is_a_census_row` and T023's `census == anchor` are what make T024
load-bearing rather than tautological.

### [MEDIUM] `test_spec_kitty_home_pin_census.py:500-531` — the stale diagnosis has no negative control. Self-report confirmed by mutation; the dispatch's suggested corpus file does not supply one.

Substituting `effect_limb_sites` with `lambda root, rel: {1} if (root/rel).exists() else set()`:

```
REAL                     arm1=PASS   arm2=PASS
MUTANT(exists-only)      arm1=PASS   arm2=PASS
```

The two arms discriminate **file-exists vs file-deleted**, not **site-present vs site-absent**. The
effect-limb content of the diagnosis is unproven.

**Correcting the dispatch's premise:** `_NON_MEMBER_HELPER` is **not** a byte-hit file —
`pkg/helpers.py` contains no `SPEC_KITTY_HOME` (`byte-hit=False`, `effect_limb_sites=[]`), so the
synthetic corpus does **not** already hold the discriminating case. A real control needs either a
file with a `SPEC_KITTY_HOME` write resolving somewhere other than `tmp_path/"home"`, or arm 2
deleting only the **def** while leaving the file.

### [MEDIUM — NOT WP05's; operator TG-item] Terminology gate red in the integrated tree, attributed to WP04.

`tests/architectural/test_no_legacy_terminology.py::test_forbidden_term_does_not_appear[ceremony]`
FAILS on `tests/architectural/test_home_pin_verdict_seam.py:769`. `git log -S"ceremony"` attributes
it to **`ee4728edf` (WP04)**, not to `f8ecfc707`; WP05's three files are clean. None of the
`_home_pin_*` files exist on the mission branch, so **lane-e is the first surface where it is
observable** — it is not in the operator's baseline-red list, and CI's `integration-tests-core-misc`
job will fail on it. One-word reword in WP04's docstring. **No `gh issue create`** (C-013 / dispatch)
— routed to the operator here.

### [LOW — no change requested] The anchor's `composite_key_from_file` re-read vs `discover`'s SyntaxError propagation.

Self-report accurate on the mechanism: `anchoring.py:190-194` returns `"<module>"` on `SyntaxError`;
`_home_pin_verdict.evaluate`'s docstring confirms `discover` propagates it. But the divergence is
**not silent** — `discover` raises loudly, and a syntactically broken `.py` under `tests/` breaks
pytest collection before either runs. Worth one line in `record.md`; not worth a change.

---

## Verified good (constructed, not read)

- **Digests re-derived by running the shipped command** into a clean out-dir:
  `census_key_set_sha256 = e2604836e22c59476a83adcddab655fc970f6802a15b2835ea6c7fe35129efdd`,
  `exempt_set_sha256 = b205baff23d0b77f15c61a5427734476b34d8e946326fc396fcf90ce17e14f9c`, and **both
  artefacts byte-identical** to the checked-in files.
- **T026 join key** is `(rel_path, keyed-def qual)` from `members.json`, **injective 40 distinct over
  40**, asserted **before** the comparison it enables. It is **not** `MemberKey[0:2]`: at `:1165`
  `MemberKey[1] = test_bind_counter_wrapper_changes_no_outcome_committed_red._run_once` vs
  `qual = test_bind_counter_wrapper_changes_no_outcome_committed_red`.
- **T026's positive control is two-sided** (`:672-673`): census-side flip and M4-side flip, each
  returning exactly the flipped key. Both fire.
- **T025's positive control materialises two members** in two files via an unused silhouette
  parameter and requires both back.
- **`delete-the-assertion-not-the-test` instance — polarity now correct.** Constructed: dropping a
  census row whose definition survives yields `unexpected={victim}`, `stale=∅`. `unexpected` is the
  contract; both arms and the setup were preserved.
- **T023's three assertions** present and distinct, `tests/` prefix applied at comparison time.
  **`members.json` was never edited** — touched only by `265585f53` (planning artifacts).
- **Seam discipline**: `_home_pin_verdict` imported, no `hashlib` in the module; the census module is
  **not** on `test_home_pin_verdict_seam.EXEMPT` (3 entries, content-pinned);
  `discover(Path("tests"))` still returns **42** (module uses `scan.NEEDLE`, never the literal).
- **Gates**: 25 passed `-n0` (72 s) and `-n auto --dist loadfile` (121 s) — NFR-003 parity.
  `ruff check` clean. `mypy --strict` clean. No `len(x) == N`. Literal `40` in prose only.
  `tests/_arch_shard_map.py` untouched. `test_golden_count_ban`, `test_gate_coverage`,
  `test_home_pin_verdict_seam` all green.

## What I could not check

- **The "124 repo-gate tests green" figure.** My selection (`test_golden_count_ban`,
  `test_gate_coverage`, `test_no_legacy_terminology`, `test_home_pin_verdict_seam`) ran **84**, with
  the one failure above. I did not reconstruct the implementer's exact 124-test selection, so I
  cannot say whether the terminology guard was in it.
- **Whether any member deserves to be a member**, and **whether M4's labels are right** — both
  explicitly out of scope (R1b's; M4 is an anchor, not an oracle).
- **Whether `#3121` is the right scope** for 40 adjudications — SC-003 can only check well-formedness.
