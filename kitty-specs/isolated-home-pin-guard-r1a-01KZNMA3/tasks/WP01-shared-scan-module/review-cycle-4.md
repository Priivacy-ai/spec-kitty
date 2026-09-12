---
affected_files:
- path: tests/architectural/_home_pin_scan.py
- path: tests/architectural/test_home_pin_scan_limbs.py
cycle_number: 4
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-12T01:45:22+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP01
---

# WP01 review — cycle 4 (focused confirmation)

**Verdict**: **APPROVE**
**Under review**: `1759e836e` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-a` — two files,
+350/-19. **Scope**: confirmation only; cycles 1–3 stand and were not repeated. Reopened because WP05 blocked
on a silent green in `main()`, not because of a defect in the surfaces those cycles examined.

---

## The transferable finding — why it survived four approvals

`--exempt-module` fed only `render_baseline`'s `exempt=` hash and never the census, so census output was
byte-identical with and without the flag while `evaluate(...).ok` returned `True`. With `E ⊆ census`,
`census ∪ E` is a no-op union and `discovered == census ∪ E` degenerates to `discovered == census` — the
mission's central accounting reporting success while checking nothing.

**It survived because WP01's only `main()` test ran with the flag ABSENT.** A flag whose entire purpose is to
change an output was never exercised in the state where it changes it. That is precisely the
population-0-without-a-positive-control shape this package closes fifteen times over in `INERT_LIMBS` — applied
rigorously to a registry of classifier sub-forms, and not once to the entry point's own flags.

The generalisation, stated so it outlives this WP: **every optional argument that changes an artefact needs a
control that runs with it PRESENT and asserts the artefact MOVED.** My cycles 1–3 pointed a twelve-mutation
battery at the classifier, the registry and the attribution rule — where the mission's own risk register
pointed — and nobody, myself included, pointed one at `main()`. The risk register is not the same thing as the
surface area.

---

## 1. `E` subtracted from both renderers — CONFIRMED

`main()` now builds `census_members = {m for m in discover(args.root) if m.key not in exempt_keys}` and passes
it to **both** renderers. Four arms, all set relations, parametrised over a synthetic 3-member tree and the
real `tests/` tree, with `E`'s keys derived by calling `discover()` rather than embedded as literals — so the
control is valid at 3, 40 and 42 members alike. That derivation is the right call: a literal `E` would have to
be rewritten the day WP03 lands, which is the same brittleness that reopened this WP at cycle 3.

**Mutation (restoring the original defect — `census_members = discover(args.root)`)**: both parametrisations
**RED**, at `:1073`, the Not-Done-If arm (`with_exempt & exempt_keys == set()`). The defect is caught.

Note on method: you asked me to re-run the "flag moves the census" arm specifically. Under the natural
mutation the earlier arm fires first, so I verified that arm's **property** by construction instead — see §5,
where two subprocess runs of the shipped command give 40 rows without the flag and 38 with it, removing
exactly the two `E` keys and nothing else.

## 2. `REGENERATION_COMMAND` parsed, not string-matched — CONFIRMED, and it is stronger than what was asked

Extracting `build_parser()` from `main()` is the right factoring: the shipped header string is run through
**the same parser the entry point uses**, so the check cannot drift from the thing it describes, and it ships a
positive control (`--regenerate placeholder` rejected) proving the mechanism discriminates rather than
accepting anything. A string match would have passed a header naming a flag that does not exist; this cannot.

One bound worth stating, not a defect: the arm feeds every flag `"placeholder"`, so it checks flag **names**,
not types or requiredness — `--root placeholder` parses because `type=Path` accepts any string. That is exactly
what the docstring claims ("names every flag it needs"), so the claim and the mechanism match.

## 3. T026(1) — the fragility note's empty branch — CONFIRMED, with one safe-direction residual

Confirmed in emitted output. The empty branch reads *"KNOWN-FRAGILE ROWS: not supplied to this generator call,
so this census makes no claim about them"* and **never** says "none" — so the dangerous reading (a census
asserting no fragile rows exist when the register merely was not passed) is genuinely foreclosed. Deriving the
note changes a **value** and never a key: the header's asserted key set is unchanged, verified.

Residual, in the safe direction: `fragility=()` (not supplied) and `fragility=[]` (supplied but genuinely
empty) emit **byte-identical** text saying "not supplied". A genuinely empty register would therefore be
described as unsupplied — which under-claims rather than over-claims, and is separately guarded by
`test_fragility_register_over_the_real_tree_is_a_non_empty_subset_of_the_class` asserting the register is
non-empty ("an empty register means the matcher stopped seeing, not that fragility ended"). Recorded, not
required.

## 4. ADJUDICATION — `fragility_register` is ACCEPTABLE AS SHIPPED

The implementer self-reported this as *"a claim about `ruff` that nothing checks against `ruff`"* and noted the
comparison was constructible but not constructed. **I constructed it.**

`ruff check --isolated --select ARG --output-format=json tests/` — 3262 ARG diagnostics, 202 naming a
silhouette parameter (`tmp_path` / `monkeypatch` / `canonical_home` / `runtime_home`). Restricted to defs
sitting inside a **member's** enclosing chain:

| | Result |
|---|---|
| ruff-flagged unused silhouette params inside a member chain | **1** — `sync/tracker/test_tracker_egress_refusal_3108.py:1165 monkeypatch` |
| `fragility_register(Path("tests"))` | **1** — the same row |
| **ruff flags but the register MISSES** (the dangerous direction) | **∅** |
| register flags but ruff does not (over-inclusion, safe) | **∅** |

Three grounds for acceptance, in order of strength:

1. **The dangerous direction is measured at zero.** The divergence classes named in the concern —`**kwargs`
   forwarding, `locals()`, string-annotation references, names used only inside a nested comprehension scope —
   are absent from every member's chain today. That is a measurement, not an argument.
2. **The register carries no enforcement load.** It feeds a header *value*; nothing gates on its completeness.
   The actual defence against the failure it describes — someone deletes the unused `monkeypatch` and the
   member leaves the class — is the census equality `discovered == census ∪ E`, which reds on the member's
   disappearance whether or not the register ever named it. A missed row costs documentation completeness, not
   a silent green. This is the decisive ground.
3. **The header hedges honestly**: "KNOWN-FRAGILE ROWS, named by the generator", not "all fragile rows".

Consistency with my earlier calls: I refused `MERGE_BASE_DEFINITION_NAMES` (speculative hardening, no measured
gap) and required the exemption word count (it gated something). This one gates nothing **and** the gap is
measured at zero, so it lands with the refusal — and unlike that one, it now has a number attached.

**Residual to record, not to fix**: my reconciliation is a measurement, not a mechanism, and it will not repeat
itself. Route to WP06/T030 as a named residual carrying the symmetric-difference-0 datum, so the next reader
inherits the number rather than the worry.

### Secondary — the `sys.modules` guard is a mechanism, not just a convention

**Constructed**: forcing both parametrisations onto one module name (`_synthetic_exempt_COLLIDING`) **REDS** at
`:1070` — `assert exempt_keys <= discovered, "the control is vacuous unless E is drawn from real members"`. So
the case that could pass for the wrong reason (cross-root `sys.modules` reuse, where a cached `E` from the real
tree is applied to the 3-member tree) is caught by an arm already in the test. A same-root collision would
yield the same `E` and no wrong answer. The concern is closed.

## 5. Digests — framing confirmed, and nothing is pinned

Re-derived by running the repaired command as a **subprocess** with `PYTHONPATH` (not a scratch script), on the
lane-a tree, with a 2-entry `E` whose keys are derived by calling `discover()`:

| Run | Rows | `census_key_set_sha256` |
|---|---|---|
| flag absent | **40** | `e2604836e22c59476a83adcddab655fc970f6802a15b2835ea6c7fe35129efdd` |
| `--exempt-module` present | **38** | `6ef640cb0780f1fce031c74e00ada289032f3c28f88d57c71ea9cef8e13ae7e5` |

The flag removes **exactly** the two `E` keys and nothing else, and `exempt_set_sha256` with the flag absent is
`sha256("")`. `e2604836…` is the value WP05 hand-derived, now falling out of the shipped command — the
prediction holds.

**Nothing was pinned prematurely, verified**: no long hex literal appears in either file (the only one is
`FROZEN_SHA`, a git sha passed as `--frozen-at-sha`, not a content digest), and no R1a census or baseline
artefact is committed (`tests/architectural/census/` holds only the three pre-existing `verdict_seam_IC0*`
files). The framing is right: this is a **40**-member tree without WP03's owner, so the mission digests must
come from a tree containing it.

## 6. Counts — all confirmed

| Check | Result |
|---|---|
| `-n0` | **75 passed** (112s) |
| `-n auto --dist loadfile` | **75 passed** (174s) — NFR-003 holds |
| `ruff check` | clean |
| `mypy --strict` | clean, 2 files |
| golden-count `tests/architectural` | **25/25**, this file contributing **0** (`:54` classifies `keep`) |
| `_golden_count_baseline.json` | untouched by this commit — nothing re-frozen |

---

## Carried forward (none blocking)

- **WP06/T030**: the ruff-vs-register reconciliation above (symdiff 0, both directions) as a named residual;
  plus the three adjudicated findings from cycles 1–3.
- **Contract amendments** to `contracts/home-pin-scan-seam.md`: `key_member -> Attribution | None` with
  `Attribution` on the public surface; C-012(5) restated at member level (the literal reading raises on 11 of
  40 real members). Cycle 4 adds two more public names — `Fragility`, `fragility_register`, `build_parser` —
  which the contract's "Public surface" section does not list either.
- **WP05/T023**: `members.json` is repo-root-relative, `Member.relpath` is walk-root-relative
  (`data-model.md:15`); the anchor build must reconcile the `tests/` prefix. WP05 can now unblock — the
  subtraction is exact and the digest it hand-derived reproduces from the shipped command.
- **Operator TG-item**: `-n auto` wall-clock fragility in `tests/architectural` (cycle 1, §non-blocking).
- **Zero golden-count headroom** for WP02–WP05: `tests/architectural` sits at 25/25.
- **The framework regression gate remains silent for these files** (`no_coverage — excluded scope —
  unverified`, recorded at cycle 3). The mutation evidence across cycles 1–4 stands in for it. A later reader
  should not read that gate result as a pass.
