# The five follow-ups — how they should be sequenced after this mission

This mission filed five issues. The operator asked whether they can be delivered as one mission. The
answer, from a dedicated planning pass that measured rather than estimated, is **no — three
missions**, and the reason is not size.

## The recommendation

| | Mission | Issues | Startable |
|---|---|---|---|
| **M1** | the board says what it did | **#3125**, **#3127** | `#3125` **now**; `#3127` after this mission integrates |
| **M2** | sync-cone process-global truth | **#3130** → **#3136** | blocked on this mission landing |
| **M3** | `_isolated_home` equivalence classes | **#3121** | **not yet a mission** — spike first |

Order **M1 → M2 → M3**. M1's two work packages are parallel with each other. M2 is irreducibly
serial. **M2 and M3 must not run concurrently on one machine even as separate missions** — M3 sweeps
`tests/cli` *and* `tests/sync`, which is the pairing this mission's standing rules forbid, and lane
computation is per-mission and cannot see that constraint.

## Why not one mission

**`#3121` changes the isolation baseline under `tests/sync/` while `#3130` is trying to prove eleven
measurements taken against that baseline.** Nine of the 22 `_isolated_home` fixtures live in
`tests/sync/`; `#3121` records that three of them pin no home at all and that
`SPEC_KITTY_ENABLE_SAAS_SYNC` is documented as load-bearing in *opposite* directions at two sites.
`#3130`'s entire evidentiary claim is that its leaks are stable, pre-existing and independently
verified. The two issues share a directory. They do **not** share an acceptance criterion, and that
distinction is the seam.

## Three mechanics worth carrying forward

### Lane computation has a second rule, and it bites harder than the first

`compute.py` unions work packages on `owned_files` glob overlap **and** on shared inferred surface
tags — the second rule is skipped only when both manifests are *provably disjoint*. Measured against
the actual candidate ownership sets, per-file ownership in the sync cone is clean
(`test_target_authority.py` vs `…_wiring.py` → `False`). But **one directory glob swallows the
mission**: `scripts/mutants/**` overlaps every file beneath it, so any work package declaring it
collapses every proof-carrying package into a single lane.

**Own mutation plugins by exact filename, never by directory glob.**

### `#3130` is one lane, and that is correct rather than unfortunate

This mission's pin registry lives in `tests/sync/conftest.py` and fails a pinned node that leaves
nothing dirty. So fixing any one of the twelve leaks forces an edit to that same file in the same
change, or the suite goes red — mechanically, not by convention. Every `#3130` fix package therefore
owns `tests/sync/conftest.py`, and rule 1 collapses them into one lane.

Fragmenting the registry to buy parallelism would be a mistake: the standing rules forbid the
concurrent `tests/sync` / `tests/cli` sweeps that parallelism would be for. **Fan out the coding,
serialise the sweeps** — the lane count was never the cost driver.

### The cost driver is sweeps, and it sorts the issues for you

| Issue | Sweep cost | Cones touched |
|---|---|---|
| #3125 | none — `git check-ignore` + `git status` | — |
| #3127 | none — CI run, workflow YAML | — |
| #3130 | one `tests/sync` serial + one `--dist loadfile` | 1 |
| #3136 | same cone + a contention harness | 1 |
| #3121 | a discriminating red per hoisted file | **6** |

Two issues cost no pytest and own no test files. One costs more than the other four combined. The
seam falls out of measurement, not taste.

## `#3121` should not be a mission yet

Its scope is unknown until its own first deliverable lands. "Publish the equivalence classes, then
justify M by class count" is a spike whose output determines the next package's scope — a mission
that replans mid-flight. If the largest provably-identical class is 3, this is small; if it is 14, it
is large. **Nobody knows which today, and that is exactly the condition under which not to open a
mission.** Three independent lenses already cut it from this mission as a cross-cutting refactor;
re-merging it into a bundle would re-litigate a settled decision with no new evidence.

## Two things found that are in none of the five issues

### `#3127` is four suppressed jobs, not one

`fast-tests-status` is a tier-2 fan-out root. Nine gates in `.github/workflows/ci-quality.yml` key
off it and `fast-tests-sync`, and the `== 'success'` ones fail on a *skip*. Run `30681941495` shows
`fast-tests-sync` failed and **four** jobs skipped behind it.

**Fixing `#3136` will not clear the cascade** — `fast-tests-sync` is red for two independent causes.
The route to restoring visibility is to fix the gate, not the sync tests. `#3127` is the only item in
this bundle that is both important and urgent: every merge to `main` is currently validated by a
board four jobs short.

### An unfiled regression holds the cascade open

`tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli`
fails in all three parametrisations on current `main`
(`assert str(path) in flat, "the operator is not told which file to repair"`). Issue **#3030 is
closed** (2026-07-28), so this is a regression, not an ATDD marker — and a search of open and closed
issues returns nothing. Under DIR-013 it must be filed rather than absorbed as baseline. The same
run also reds `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` against a **closed**
`#2804`.

## Two corrections to artefacts this mission itself produced

1. **`#3136`'s "must key on these two node-ids" instruction is already stale.** It names
   `test_exponential_backoff_intervals` and `test_429_retries_then_raises`. Run `30681941495` failed
   `test_exponential_backoff_intervals` and **`TestRetryBehaviors::test_429_defaults_to_5s_when_missing`**
   — a third node, not on the list. This corroborates `#3136`'s own mechanism claim (the victim is
   whichever sleep-mocking test is open when the intruder sleeps) while invalidating its own
   instruction. **Key on the class — any `time.sleep` call-count assertion reachable in
   `tests/sync/tracker/` — never on an enumeration.** A wrong node-id survived three review rounds on
   this mission; a stale one will survive the next unless the spec forbids the shape.

2. **No counted acceptance criteria anywhere in this bundle.** `#3121` argues it for itself and it
   generalises: counts do not move when a body changes. Each of these has a discriminating red
   available instead — `#3125` → `git status` without `-f`; `#3127` → a run whose suppression is
   visible without reading YAML; `#3130` → pin removal, which is already strict in both directions;
   `#3121` → a per-file plugin-neutralised red.

## The precondition, stated as one command

M2 is not specifiable, let alone startable, until this mission integrates. The leak guard, the pin
registry, `docs/development/process-global-inventory-3115.md` and `scripts/verify_shard_3115.sh` are
all off `main` today, and both `#3130`'s done-when and `#3136`'s starting inventory reference them.

```
git show main:tests/sync/conftest.py | grep -c _PINNED_LEAKS
```

`0` means only M1's `#3125` package is startable.

**Corollary worth writing down:** the moment this mission lands, `tests/sync/` becomes a tripwire for
*every* mission, not just M2. The registry fails a pinned node that leaves nothing dirty, so any
incidental fix to one of the twelve — by anyone, in any mission — hard-fails until the pin is
removed. That is the intended design, but a successor meeting it cold will read it as a bug.

## The thing most likely to go wrong in M2

An agent "fixes" a leak by making the test stop exercising the thing it started — never start the
background service, and the dirty state disappears. That passes pin removal, satisfies the guard in
both directions, and **silently deletes coverage.** It is this mission's own rule — *any assertion of
absence must establish why the thing would otherwise have happened* — applied to a leak fix, and the
guard cannot catch it, because absence is exactly what it measures.

**Make it a named requirement: every leak fix carries a positive control proving the test still
starts the thread, sets the variable, or builds the singleton it now cleans up.**

Second most likely: `#3136` eats the mission. Its predecessor spent a bounded six-agent-hour budget
and deferred. Scope it as *"measure whether the leak fixes eliminated the pollution"* rather than
*"fix #3136"*, with the same bounded-exit clause. If the leaked threads were the intruders, it is
already fixed and the measurement is the whole deliverable.

---

# Addendum at mission close — three issues filed later, and one correction to this file

## The later follow-ups

Three more issues were filed after this note was written. They belong to the same successor set:

- **`#3138`** — `test_issue_2804_merge_resets_gate_artifacts` is red against a **closed** `#2804`. A
  regression with nothing tracking it.
- **`#3139`** — 14 red node-ids, every one on the `accept` surface and no other. One drift observed
  fourteen times, not fourteen defects. A twelve-agent parity test that is red for all twelve has
  stopped detecting the asymmetry it exists for.
- **`#3140`** — malformed `meta.json` raises a raw `ValueError` at three call sites that assert
  fail-closed behaviour by name. A fifth instance of the same shape had been carried on missions'
  "known pre-existing, don't chase" lists long enough to have been informally routed around.
- **`#3143`** — the Windows job and every local `pytest` run get **no per-test timeout**. Derivation
  (b) put the flags in `ci-quality.yml` only; `pytest.ini` is byte-identical to base.
- **`#3142`** — FR-017's regression enumeration needs a post-merge CI run, and `#3127`'s four-job
  blackout will leave it incomplete unless `#3127` lands first.

## Why `#3142` and `#3143` are named here and not in `spec.md`

A pre-merge reviewer flagged that `#3142` appeared only in `acceptance-matrix.json`, which
`issue_reference_discovery.py:42-50` does not scan — so the handle is invisible to discovery. The
observation is correct. **The fix it implies is not available.**

That scanner reads `spec.md`, `plan.md`, `research.md`, `analysis-report.md`, `tasks/*.md` and
`contracts/*.md`. Naming a live issue in any of them **mints a mandatory issue-matrix row this
mission cannot resolve** — the row would need a terminal verdict, and a follow-up filed at close by
definition has none. That is the exact reasoning that kept `#3121` out of every scanned artifact, and
it is recorded in `issue-matrix.json`'s own scope text.

So the placement is deliberate: **`notes/` is the most discoverable location available that does not
mint an unresolvable row.** This addendum exists so the handles are at least in a file a successor
opens, rather than only in a JSON field.

If that trade is wrong, the fix is a scanner that distinguishes *this mission resolves it* from *this
mission filed it* — which is a spec-kitty change, not a mission one.

## Correction to this file

The section above headed **"An unfiled regression holds the cascade open"** is **superseded**. It
states that `tests/sync/test_consent_write_refusal_3030.py::test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli`
is unfiled and must be filed under DIR-013, on the reasoning that the test is named `_3030` and
`#3030` is closed.

That is wrong. **`#3115` names all six of those files** as a known shard-isolation victim class, and
`#3115` is open. A keyword search for `consent_write_refusal` finds nothing because the tracking issue
contains neither the filename nor the test name — which is how the wrong conclusion was reached.

Nothing is unfiled there. `#3115` is recorded `deferred-with-followup`, so it stays open and keeps
carrying them. The corrected classification is in
[`ci-baseline-at-landing.md`](ci-baseline-at-landing.md); this note is annotated so a successor
reading the two in directory order does not act on the superseded claim.
