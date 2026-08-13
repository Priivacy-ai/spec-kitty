---
affected_files:
- path: tests/architectural/_home_pin_scan.py
- path: tests/architectural/test_home_pin_scan_limbs.py
cycle_number: 2
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T16:53:05+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP01
---

# WP01 review — cycle 2 (focused confirmation)

**Reviewer**: reviewer-renata · **Verdict**: **APPROVE**
**Under review**: `75d790885` (on `5068b8cbd`) on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-a`
**Scope**: confirmation of cycle-1's one required change and two LOW recommendations. Cycle-1's
twelve-mutation battery was **not** repeated; it stands against `5068b8cbd` and the cycle-2 diff is
docstring-only plus one added test.

Blast radius verified: `git diff 5068b8cbd..75d790885` touches `_home_pin_scan.py` (+59/-22, **docstrings
only**), `test_home_pin_scan_limbs.py` (+33, one new test), and mission status files. No behaviour change —
`OWNER_PARAM_NAMES` is byte-identical at `_home_pin_scan.py:339`,
`frozenset({"tmp_path", "canonical_home", "runtime_home"})`, both entries kept as required.

---

## 1. [HIGH] `OWNER_PARAM_NAMES` is now honestly labelled — CLOSED

`_home_pin_scan.py:310-338`. All five required elements present:

- **the limb is correct to exist** — opens with FR-010's blindness argument;
- **it matches nothing today** — stated explicitly, and framed as FR-007's own rule applied to the sixteenth
  limb ("the one the rule was **not** applied to until review constructed it");
- **measured population-0 for both entries**, each with its reason;
- **`canonical_home` marked provisional and unbound** — "nothing binds it to the fixture WP03 will actually
  add", with the observation that the shipped tests supply the name on both sides of the equality;
- **WP03/T012 named as the closing obligation** — "assert the contract's declared fixture name is a member
  of this set. Until that lands, treat this entry as unanchored."

Every factual claim in the new text re-derived independently:

| Claim | Constructed result |
|---|---|
| Exactly one def declares `runtime_home` | **1** — `audit/test_no_legacy_path_literals.py:80 _capture_nudge` |
| No def declares `canonical_home` | **0** defs, tree-wide |
| Refused on both limbs | union `{argv, module_name, tmp_path}` — silhouette fails for want of `monkeypatch`; value `<tmp_path>` at `:94`, `None` at `:112`, never `<tmp_path>/home` |
| Removing `runtime_home` leaves `discover()` unmoved | 40 → 40, **symmetric difference 0** |

The anchor citation is now correct: the def at `:80`, the writes at `:94`/`:112`. My cycle-1 text repeated
`spec.md`'s `:82`, which is the parameter declaration — corrected here, and the spec's three inconsistent
citations were corrected separately in `7d3539910`. Do not re-derive the anchor from cycle-1's text.

## 2. [MEDIUM] The new limb test — CLOSED, non-vacuity re-verified by my own mutation

`test_home_pin_scan_limbs.py:714-745`. Shape is as required: `assert sites` non-vacuity guard first, then per
site the two refusing limbs as **separate** assertions (silhouette at `:738`, value resolution at `:741`),
`key_member(...) is None`, and absence from `discover(TESTS_ROOT)`. `_MEMBER_TREE`'s `# M4 FR-010 owner param`
is named in the docstring as the limb's positive control, so the population-0 claim ships with the proof that
the matcher bites where the shape exists.

**Mutation re-run (not taken on report).** Narrowing `SILHOUETTE` to `{"tmp_path"}` in a detached scratch
worktree at `75d790885`:

```
tests/architectural/test_home_pin_scan_limbs.py:738: AssertionError
>   assert not union >= scan.SILHOUETTE
E   AssertionError: assert not frozenset({'argv', 'module_name', 'tmp_path'}) >= frozenset({'tmp_path'})
```

It flips red, on limb 1, for the stated reason. The failure output also independently re-confirms that the
alias normalisation **does** fire — `runtime_home` appears in the union as `tmp_path` — so the test is
measuring the limb it claims to measure rather than a name that never resolves. Reverted; scratch worktree
removed.

## 3. The two LOW docstrings — CLOSED

- **`DuplicateMemberKeyError`** (`:706-721`) now separates the two populations: non-injective over the **191
  walked sites** (190 distinct, one live class of two), **0 collision classes at member level** over 40
  members / 40 distinct keys, with "the earlier wording here overstated it" stated plainly. The added
  observation that the two sites are "one string literal away from being two members with one key, in a file
  named `test_runtime_root_spec_kitty_home.py`" is a better argument for the guard than the one it replaces.
- **`_corpus`** (`:1030-1040`) records the `lru_cache`-keyed-on-path caveat, names the shape that would hit it
  ("the natural way to write a 'mutate and re-scan' test"), states that no live path reaches it, and points
  consumers at a distinct root per materialisation.

## 4. Counts — all confirmed

| Check | Result |
|---|---|
| `-n0` | **70 passed** (128s) |
| `-n auto --dist loadfile` | **70 passed** (180s) — NFR-003 holds |
| `ruff check` | clean |
| `mypy --strict` | clean, 2 files |
| members / files / distinct keys / bare 2-tuples | **40 / 36 / 40 / 19** |
| `kind` keyed vs innermost | **30/10/0** vs **30/9/1** |
| `home_partition` | **A=27 / B1=11 / B2=2 / other=0** |
| C-011 anchor (built independently from `members.json` + `composite_key_from_file`) | 40 keys, **symmetric difference 0** |
| golden-count `tests/architectural` | **25/25**, this file contributing **0** (its `len(matches) == 1` at `:52` classifies `keep`) |

Building the anchor required stripping the `tests/` prefix from `members.json`'s repo-root-relative `path` to
meet `Member.relpath`'s walk-root-relative form — an independent re-confirmation of cycle-1's LOW handoff note
for WP05/T023.

---

## Verdict

**APPROVE.** The required change is docstring-only, changes no behaviour, and converts the module's most
consequential unmechanised constant from an implied anchor into a measured, labelled, population-0 limb with a
named closing obligation. The one new assertion demonstrably fails when the mechanism it guards is removed.

## Carried forward (unchanged from cycle 1, none blocking)

- **Contract amendments** (`contracts/home-pin-scan-seam.md`, not WP01's to edit): `key_member` →
  `Attribution | None` with `Attribution` on the public surface; C-012(5)'s mechanism restated at member level
  (the literal `assert_descriptor_unique_within_qualname` reading raises on **11 of 40** real members).
- **WP03/T012**: assert the contract's declared fixture name ∈ `_home_pin_scan.OWNER_PARAM_NAMES`. This is now
  named in the module the WP03 implementer must import, but it is still not in WP03's DoD or `not_done_if`.
- **WP05/T023**: `members.json`'s `path` is repo-root-relative, `Member.relpath` is walk-root-relative
  (`data-model.md:15`); SC-001's anchor build must reconcile the `tests/` prefix.
- **WP06/T030**: carry the three adjudicated findings and the residuals into `record.md` — WP01 could not,
  `record.md` being WP06's owned file.
- **Operator TG-item**: `tests/architectural` at `-n auto --dist loadfile` is wall-clock fragile on this
  machine. Merge-base = 1 failed / 1850 passed (`test_wp_prompt_build_latency::…implement…`, 6.08s vs a 6.0s
  budget); lane = 3 failed / 1917 passed (that red, plus `…review…` at 7.21s, plus
  `test_ci_quality_path_filters::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection`, which passes
  alone at 221s and whose `_collect_nodes` subprocess-timeout mode is documented in its own module as a
  concurrency artefact). Not a semantic regression, but the lane's added shard load raises the pressure that
  produces it. Per C-013 no `gh issue create` was run — the DIR-013 issue is the operator's to open.
- **Zero golden-count headroom**: `tests/architectural` sits at 25/25. WP02–WP05 must convert on sight.
