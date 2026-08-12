---
affected_files:
- path: tests/architectural/_home_pin_scan.py
- path: tests/architectural/test_home_pin_scan_limbs.py
cycle_number: 3
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T22:18:08+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP01
---

# WP01 review — cycle 3 (focused confirmation)

**Verdict**: **APPROVE**
**Under review**: `8bca98e74` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-a` — two tests and
three docstrings, nothing else (`git diff 75d790885..8bca98e74 --stat`: 2 files, +73/-27).
**Scope**: confirmation only. Cycle-1's twelve-mutation battery and cycle-2's confirmation stand and were not
repeated. Reopened under an operator ruling after WP03 landed, not because of a defect in what I approved.

---

## 1. The C-004 test asserts the discrimination, not the counts — CONFIRMED

`test_home_pin_scan_limbs.py:441-462`. Four arms as specified. All four are invariant under `E` growing: a
member `E` adds is a top-level fixture, which increments `fixture` identically in both readings, so arms 1–2
absorb it and arms 3–4 never read `fixture`.

**Judgment requested: is arm 4 sufficient, or does dropping the magnitude lose something it cannot see?**
**Arm 4 is sufficient, and the implementer's departure from the `== 1` instruction was right.** This is now
measured, not argued:

- Arm 4 is *precisely* the arm that catches innermost attribution — it reds as `assert 9 > 9` at `:455`.
  Against that mutation, `transfer == 1` and `transfer >= 1` are equivalent: the transfer drops to 0 either way.
- The rule `== 1` might be thought to catch — one that *over*-attributes outward — is MUT-B below, and on the
  real tree MUT-B moves **neither** distribution. `== 1` would have passed it too. So the magnitude buys
  **zero** additional detection while reintroducing exactly the census-sized brittleness that reopened this WP.

One optional strengthening, explicitly **not** required: the old assertion also pinned `keyed["helper"] == 0`,
which unlike the magnitude is not census-sized (every `E` member is a fixture or a test, so it survives `E`
growing) and is a genuine structural property of the keyed reading — the outermost *satisfying* def cannot be a
bare helper, because pytest injects `tmp_path`/`monkeypatch` only into fixtures and tests. I measured it: it
adds no detection against either mutation below. Noted so it is a considered omission rather than an
unnoticed one.

## 2. The two-mutation claim — VERIFIED, and the framing needs one correction

Both re-run by me at `8bca98e74`:

| Mutation | real-tree test | synthetic sibling |
|---|---|---|
| **A** — attribute at the innermost def | **RED**, arm 4 at `:455` (`assert 9 > 9`); arms 1–3 green | **RED** at `:417` |
| **B** — attribute at `chain[0]` regardless of which def satisfies | **PASSES all four arms** | **RED** at `:417` (`fixture: 4` vs `3`, the M3 chain-union witness) |

**The load-bearing half holds**: MUT-B is caught **only** by the synthetic test. A wrong attribution rule that
happens to agree with the correct one on the real population is invisible to the real-tree arms, so the repair
has **not** traded a tight assertion for a loose one — the tight assertion still exists, in the synthetic
sibling, where it belongs.

**Correction to the framing**: "neither does alone" is not what I measured. MUT-A is caught by **both**, so
across these two mutations the synthetic test alone catches everything and the real-tree test catches nothing
the synthetic misses. The real-tree test is still necessary, but for a different and better reason than
mutation coverage: it is the only one asserting C-004 over a population **this author does not control**.
`_MEMBER_TREE` is written by the same hand as the predicate — the exact circularity C-011 diagnoses for the
census — and a reviewer's mutation battery cannot tell those two roles apart, while a future contributor
changing the real tree can. Keep both; state the reason accurately.

## 3. The partition split — CONFIRMED CORRECT, with one coverage nuance

The removal is signposted at the removal site and reasoned in `_home_partition`'s docstring, and
`PARTITION-OTHER` correctly stayed (classifier claim, unmoved by `E`) with both its population-0 assertion and
its positive control intact — the test count going 70 → 69 confirms exactly one test left.

WP05 does carry it, in a **stronger** form than what was removed: WP05/T023 step 3 *recomputes* the
`home_partition` cross-check at test time against M4's `TABLES.md`, on a named join key
(`(rel_path, keyed-def qualname)`, measured injective over the 40) giving 28 matches and zero unmatched, with
the disagreeing set asserted empty, the intersection size published, and a positive control feeding a
deliberately mislabelled row. Its Validation section explicitly refuses the weaker form this WP just deleted:
*"Copying `A=27 / B1=11 / B2=2` … into a comment satisfies any prose-shaped criterion."*

Nuance, recorded not objected to: WP05's check covers the 28-row intersection per member, so the **aggregate**
distribution `A=27/B1=11/B2=2` is now asserted nowhere. That is correct — it is a census figure that moves with
`E`, which is why it could not stay here — and the per-member recomputation against an external anchor is the
better claim. Flagged only so nobody later reads its absence as an oversight.

## 4. `OWNER_PARAM_NAMES` docstring and the rename — CONFIRMED ACCURATE

I verified both WP03 citations by reading the lane-c branch, without touching that worktree:
`tests/conftest.py:302` declares `def canonical_home(monkeypatch, tmp_path) -> None`, and
`tests/architectural/test_home_owner_behaviour.py` declares
`test_the_declared_owner_name_is_a_member_of_owner_param_names` at `:339` and
`test_the_owner_alias_limb_actually_fires_on_the_owner_name` at `:363`. **Cycle-1's HIGH finding is genuinely
discharged**: the operand is now outside this author's control, and WP03 independently chose the same name.

The rename is accurate. `test_fr010_runtime_home_alias_is_measured_inert_and_refused_on_both_limbs` probes only
`_capture_nudge`/`runtime_home` and never the owner, so the new name matches what the body asserts, and the
old name did claim more than the body proved once WP03 merges. **The refusal argument survives the boundary**:
`_capture_nudge`'s chain union is `{argv, module_name, tmp_path}` and its value resolves to `<tmp_path>`
(`None` at `:112`) — neither fact depends on the owner existing, so it is refused on both limbs in this lane
and in the merged tree alike.

One precision note, non-blocking: the docstring's "WP03 **has landed** the canonical owner" is true of lane-c
and **not yet of the mission branch** — `canonical_home` is absent from `tests/conftest.py` there, and in
lane-a's own tree `discover()` still returns 40. The sentence describes the state the module ships into, which
is the right thing to describe, but a reader in lane-a who greps `tests/conftest.py` will not find it and may
briefly doubt correct work.

## 5. Counts — all confirmed

| Check | Result |
|---|---|
| `-n0` | **69 passed** (143s) |
| `-n auto --dist loadfile` | **69 passed** (236s) — NFR-003 holds |
| `ruff check` | clean |
| `mypy --strict` | clean, 2 files |
| golden-count `tests/architectural` | **25/25**, this file contributing **0** (`:52` classifies `keep`) |
| `_golden_count_baseline.json` | untouched by this commit — nothing re-frozen |

---

## Recorded, not fixed

- **The framework regression gate was SILENT here, not green.** `move-task` reported
  `no_coverage — excluded scope — unverified`: both WP01 files land only in a catch-all group, so the gate ran
  nothing against this change. The mutation evidence in cycles 1–3 stands in for it. A later reader should not
  read that gate result as a pass.
- **My own instrument failed a "prove it can see" check, and I want it on the record.** My first cycle-3
  mutation runs reported "2 passed" for *both* mutations. The cause was not the code: the mutation helper in
  my shared scratchpad had been overwritten by an unrelated harness that exits 0 without editing the file. Had
  I trusted that output I would have reported a genuinely non-vacuous test as vacuous. The helper was rebuilt
  with a write-back self-check (re-read the file, confirm the new text is present, else refuse), and every
  mutation result in §2 comes from the rebuilt instrument after confirming it flips
  `kind_distribution(at="keyed")` from `30/10/0` to `30/9/1`. Positive control before conclusion, including for
  the reviewer's own tools.
- **Carried forward unchanged from cycles 1–2** (none blocking): contract amendments to
  `contracts/home-pin-scan-seam.md` (`key_member -> Attribution | None`; C-012(5) restated at member level —
  the literal reading raises on 11 of 40 real members); WP05/T023's `tests/` prefix reconciliation between
  `members.json` (repo-root-relative) and `Member.relpath` (walk-root-relative); WP06/T030 to carry the three
  adjudicated findings into `record.md`; the operator TG-item on `-n auto` wall-clock fragility in
  `tests/architectural`; and zero golden-count headroom for WP02–WP05.
