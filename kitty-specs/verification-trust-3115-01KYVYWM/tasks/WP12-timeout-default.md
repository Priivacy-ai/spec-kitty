---
work_package_id: WP12
title: 'A default per-test timeout with a stated method, derivation and enumerated blast radius'
dependencies:
- WP11
requirement_refs:
- FR-016
- FR-017
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T036
- T037
- T038
- T039
history: []
authoritative_surface: pytest.ini
execution_mode: code_change
owned_files:
- pytest.ini
- .github/workflows/ci-quality.yml
- scripts/mutants/hang_a_fast_test_3115.py
create_intent:
- scripts/mutants/hang_a_fast_test_3115.py
tags: []
tracker_refs: []
---

# WP12 — The timeout default

**A hang is not a measurement; it is the absence of one, wearing the appearance of a slow job.**

## Blocked by WP11 — hard, non-negotiable

**The counter pin must precede the timeout default. This is the plan's single hardest sequencing
constraint.** With a global timeout in place, WP11's mutant reds on the **timeout** and the missing pin
becomes **unobservable** — the backstop masks the defect it is supposed to backstop. Prove the counter
first, on a tree with no global timeout; then add the timeout over a tree where the counter already
holds.

## This is the mission's only repo-wide package, and the last code-changing WP merged

`pytest.ini` sets `testpaths = tests`, so an `addopts` default caps **every** invocation of this ini.
Landing it early makes every subsequent lane's baseline incomparable to the ones taken before it.
**Every lane cut before WP12 re-merges the mission branch before its next measurement and states the
commit it measured at** (NFR-009).

## Why the WP owns both `pytest.ini` and `ci-quality.yml`

So the derivation choice can be made **from the measurement rather than from availability**. It owns
both either way and **states which it chose**.

## Definition of done — measurable evidence

### T036 — the derivation, chosen and stated

Choose **(a)** `addopts` in `pytest.ini` **or (b)** the flag scoped to the fast job command lines in
`.github/workflows/ci-quality.yml` — **and state which**.

- **(a) is permissible only if `--durations` is actually collected over every selection that inherits
  the ini**, including the `slow`/`stress`/`e2e` opt-ins that FR-017's regression clause structurally
  **cannot** observe. If the WP cannot afford that, **it takes (b), and its blast radius is the
  enumerated job list.**
- **`--cov` must be accounted for.** Both fast shard commands carry it (`ci-quality.yml:1132`, `:1543`);
  it installs a **per-thread trace function, changes thread scheduling and inflates `--durations`** —
  the coverage state **must be stated with the value**, and if the value was derived with coverage on,
  **say so and justify it against the coverage-on numbers**.
- **State all five**: the **chosen value**, the **chosen method**, the **chosen derivation (a)/(b)**,
  the **coverage state**, and the **measured maximum unmarked-test duration** — with a **floor of 4×**
  that maximum.

### T037 — the method is stated explicitly, and red first

**The method is stated explicitly, not left to pytest-timeout's platform default.** This is what
discriminates the usable configuration from the useless one: pytest-timeout's **thread** method killed a
`#3030` session mid-run and produced **no summary and therefore no verdict**, while the **signal**
method reds the test with a traceback.

- **Red first**: a deliberately non-terminating `fast` test **hangs** the selection on `bb2020fea9`. The
  hanging test is injected by `scripts/mutants/hang_a_fast_test_3115.py` under the corrected mutant
  contract — **loaded with `-p hang_a_fast_test_3115` (the flag quoted in the evidence)** under
  `PYTHONPATH=scripts/mutants`, collecting/injecting at **hook level**, **asserting its own binding**,
  and **failing loudly if the injected test was never collected**. *"The selection ended fine" from a
  run that never collected the hanging test is not a measurement.* It is a **plugin, not a committed
  test file**, so nothing else can collect it.
- **Green after**: the same selection **ends and prints a summary line naming that test**. **A run that
  ends with empty output does not satisfy this** — it is the same "empty output is not a failure" trap
  one layer down.
- **Carried forward, verified**: `pytest-timeout`'s **`signal` method works under `xdist` on Linux** —
  probed at `--timeout=3 --timeout-method=signal -n 2` → `Failed: Timeout (>3.0s) from pytest-timeout`,
  a named red with a real summary and a correct elapsed time. **Caveat that binds the evidence**: the
  same run also emitted an `execnet gateway_base._thread_receiver` traceback, so **the evidence must
  quote the summary line, never "the output was clean".**
- **`ci-windows.yml` has no `SIGALRM`**: **state what method it gets and what its failure mode is.** Do
  **not** assume parity.

### T038 — blast radius, stated because `testpaths = tests`

- **46** tests are marked `slow` (ini definition: ">30 seconds") against **~15** `@pytest.mark.timeout`
  sites (including `timeout(600)` on `test_dogfood_corpus_backfilled` and `timeout(120)` on the charter
  e2e golden path and `tests/stress/test_concurrent_emits.py`).
- **The opt-in selections that run them are ones FR-017's regression clause structurally cannot
  observe.**
- **Existing explicit marks override the ini default.**
- **No new pytest marker.** `timeout` is **already registered** in `pytest.ini`. WP12 is the **sole
  owner** of that file, and **no other WP may add a marker there**.
- **Why a global default and not per-test marks**: marks cover only what someone remembered to mark, and
  the failure class here is *the loop nobody anticipated* — *"registering a marker that nothing applies
  is the same shape as an allowlist with no enforcement"*.
- **A newly-added global timeout that reds a legitimately slow unmarked test is a finding about the
  value, not about the test**: raise the value or mark the test, and **record which**.

### T039 — the regression clause, enumerated not aggregate

The **first full CI run after the change**:

- lists **every job that inherited the new default**, with its **conclusion** and its **collected
  count**; and
- separately lists **every selection that did not run at all**, with the reason — path-filtered, skipped,
  or opt-in-only. `fast-tests-sync` is gated on `needs.changes.outputs.sync` (`ci-quality.yml:1101`) and
  was **skipped entirely** on run `30622853036`.
- **Zero tests newly red attributable to the timeout**; any that are, are **listed with their durations**
  and either marked or the value raised.

> ***"Nothing newly red" over a set that did not run is not a result.***

**Any CI claim names the job, its conclusion (`success`/`skipped`/`failure`) and its collected count. A
workflow conclusion is not evidence** — a workflow is green when its path-filtered jobs are *skipped*,
and `fast-tests-cli` carries `|| test $? -eq 5` (`ci-quality.yml:1545`), so an empty collection is a
**green job**.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail of the file read; **an empty output file is no
measurement**; a **killed run is neither a pass nor a fail** — re-run it narrowed, and check elapsed time
against the `timeout` value before attributing it. **NFR-007**: quote the failure text, not the tally.

## Files other agents hold

`tests/delivery/test_dispatch_window_consent_3030.py` and
`scripts/mutants/nonterminating_dispatch_3115.py` are **WP11's** — this WP must not touch the counter
pin, and in particular must not "help" WP11's mutant by adding a timeout. `.github/workflows/ci-windows.yml`
is **nobody's write scope** — this WP **states** what method it gets; it does not edit it.
`tests/**` is other WPs' — **WP12 changes configuration, not tests**; if the new default reds a test,
the response is to list it with its duration and either mark it (in **its owning WP's** file, by
coordination) or raise the value. `src/**` is nobody's.
