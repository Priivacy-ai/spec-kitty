# Contract: the mutation plugin

The interface four work packages on this mission depended on, stated once. A "mutation" here is a
deliberate, temporary defect introduced to prove that a test would *notice* it — the red that makes a
green meaningful.

This contract exists because the obvious way to write one **does not work**, and fails silently. Four
work packages would have shipped inert mutants that reported success.

> Issue references in this file use the `spec-kitty#NNNN` form deliberately.
> `issue_reference_discovery.py` scans `contracts/*.md`, and `_GH_ISSUE_PATTERN` matches a bare
> `#NNNN` preceded by start-of-line, whitespace, `(` or `[` — a bare reference here would mint a
> mandatory issue-matrix row this mission cannot resolve.

## The contract

A mutation MUST be:

1. **A pytest plugin**, in `scripts/mutants/`, one file per mutation.
2. **Loaded with `-p <module>`**, *and* importable via `PYTHONPATH=scripts/mutants`. **Both.**
   Neither alone is sufficient.
3. **Applied at hook level** — `pytest_configure`, `pytest_fixture_setup`, or another hook — and
   **never** by declaring a fixture that shadows an existing one.
4. **Loud on non-arrival**: it MUST fail if the symbol it patched was never called. A mutation that
   silently does nothing is indistinguishable from a mutation that proved something.
5. **Never a source edit.** The tree under measurement stays at its commit.
6. **Verified under the distribution the suite actually uses**, not only serially. If the non-arrival
   check depends on state accumulated in xdist workers, that state MUST be forwarded to the
   controller explicitly. See [clause 6](#6--under-xdist-a-counter-needs-an-explicit-channel-a-report-does-not)
   — three of this mission's five plugins satisfied clauses 1–5 and were still useless under `-n`.

## Why each clause is there

### 2 — `PYTHONPATH` alone never loads a plugin

Measured against a known-answer baseline. `PYTHONPATH` makes a module *importable*; it does not make
pytest *load* it. A mutant on the path and not on the command line is imported by nothing, patches
nothing, and the suite passes — which reads exactly like "the mutation was caught and the test is
robust", the opposite of the truth.

The `.gitignore` interaction is worse and is filed as `spec-kitty#3125`: an unanchored `mutants/`
rule silently swallows `scripts/mutants/`, so `git add <path>` on a mutant does nothing without `-f`.
Combined with this mission's explicit-path staging rule, a plugin can be written, used, believed, and
never committed.

### 3 — a plugin fixture loses to a conftest fixture

Also measured, also with a known-answer baseline. Fixture resolution prefers the conftest definition
over the plugin's, so a mutation written as a shadowing fixture is **silently discarded** whenever the
target has a conftest fixture of the same name — which, for anything worth mutating, it does.

The failure mode is the one this whole mission is about: the run completes, reports green, and the
green is evidence of nothing.

### 4 — `pytest_fixture_setup` is `firstresult=True`

Returning `None` from that hook means *"I did not handle this"*, and pytest moves on to the next
implementation. A mutation that patches and returns `None` therefore un-patches itself. **A non-`None`
sentinel is required.**

This is not a style preference. It is the difference between a hook that fires and a hook that is
politely ignored.

## Five recorded ways a mutation lies

Each of these produces a passing suite that means nothing. All five were hit or narrowly avoided on
real work.

1. **The architecture moved.** The mutant patches a symbol the code no longer routes through. Nothing
   breaks because nothing calls it.
2. **The changed signature raises `TypeError`s.** The suite goes red — but for the wrong reason. A red
   is not automatically the red you wanted; read the failure text, not the tally.
3. **The mutant hard-codes what the tests vary.** Pinning a value the tests parametrise means the
   mutation is invisible to exactly the cases designed to catch it.
4. **The branch is unreachable locally and live on CI.** Platform-conditional paths — `pidfd` vs
   `waitpid`, terminal vs dumb-terminal — make a locally-dead mutation a CI-live one, and the reverse.
5. **`from X import f` rebinds by value.** Patching `X.f` leaves every module that did
   `from X import f` holding the original. **Patch every name, and report the per-site split** —
   "patched 3 of 7 call sites" is a finding; "patched" is not.

## The obligation that follows

**Any assertion of absence must establish why the thing would otherwise have happened.**

For a mutation, that means: before trusting a null result, run the probe against a case whose answer
you already know. A mutant that catches a planted defect has earned the right to report a clean run.
One that has never been shown to catch anything has not, and its silence is not evidence.

Concretely, every mutation-backed claim on this mission carries:

- a **positive control** that must pass (the unmutated run stays green), and
- a **discriminating red** (the mutated run fails, *for the stated reason*, naming the count or the
  symbol rather than returning a boolean).

## Scope of this contract

Binding on `scripts/mutants/*` for this mission and offered forward. It is written as a contract
rather than a note because the two clauses that matter most — plugin loading and fixture precedence —
are **counter-intuitive and fail silently**, which is the combination that makes a convention worth
promoting to an interface.

The successor issues that inherit it are `spec-kitty#3125` (the `.gitignore` swallow, which must be
fixed before any of this is reproducible) and `spec-kitty#3130` / `spec-kitty#3136` (whose proofs
depend on it).

## 6 — Under xdist, a counter needs an explicit channel; a report does not

Added at pre-merge, after this was measured to have broken **three of the five** plugins written
against the first five clauses. They all satisfied clauses 1–5 and were still useless in the
configuration CI actually runs.

The defect: the suppression counter incremented in xdist **workers**, while the non-arrival check ran
in the **controller**. The controller's counter therefore read zero on every distributed run.

Measured with a controlled diagnostic — a three-test selection whose first test asserts it received
the *mutated* result, so a pass proves the patch was live in the worker:

| case | serial | `-n 2` |
|---|---|---|
| symbol **reached** | `3 passed`, exit 0, quiet | `3 passed`, **exit 1, "suppressed ZERO calls"** |
| symbol **not reached** | exit 1, `NO VERDICT` | exit 1, `NO VERDICT` |

**The bottom two cells are indistinguishable.** Under xdist the guard had no discriminating power in
either direction — not noisy, *uninformative*. Clause 4 was satisfied in letter and void in effect.

### Why one plugin was already correct, and what that teaches

`hang_a_fast_test` used `terminalreporter.stats` and worked. The reason generalises:

> **It proves arrival of a test *report*, and xdist aggregates reports for free. A suppression
> *counter* rides on no report, so it needs a channel of its own.**

That channel is `config.workeroutput` (populated in workers) drained via `pytest_testnodedown` (on
the controller). A worker's `session.exitstatus` mutation is **discarded outright** by xdist, so
forcing the exit from inside a worker was never available.

### The clause

A mutation MUST verify its non-arrival check **under the distribution the suite actually uses**, not
only serially. If the check depends on state accumulated in workers, that state MUST be forwarded to
the controller explicitly.

### The direction of this failure, and why it was survivable

This bug forced **false `NO VERDICT`s** — loud, exit 1 — and never false greens. Runs bitten by it
proved nothing; they did not assert something untrue. That is the difference between a mission that
loses some evidence and one that ships a false claim, and it is worth designing for: **when a proof
instrument fails, make it fail loud and empty rather than quiet and confident.**

It also gives a cheap post-hoc test. A bitten run reports **zero** suppressed calls at every site, so
any recorded measurement carrying non-zero per-site counts was not affected — the numbers clear
themselves without any claim about how the run was invoked.

### The gap this exposed in the record

None of this mission's five plugin-backed criteria stated whether its run was serial or under `-n`,
which NFR-001 requires. The distribution had to be *inferred* from the counters rather than read off
the record. **State the distribution beside every plugin-backed measurement** — otherwise a defect
like this one is unscopeable after the fact, and you are reasoning where you should be reading.
