# Quickstart: validating Doctrine-Controlled Transition Gates (half A)

**Traces**: SC-001..004, NFR-001..005, US1..4
**Env**: `PYTHONPATH=$(pwd)/src` (editable install points at the sibling repo).
**Scope**: only the `→ for_review` pre-review gate (C-006).

This walkthrough proves the five acceptance-defining behaviours. Each step is a design-time
validation recipe a WP turns into an executable, red-first test (C-005).

---

## (a) Spec-Kitty parity through the hook — SC-002, NFR-001, US2

**Goal.** The refactored gate produces identical results to the incumbent, **through
`_mt_run_transition_gates`**, across all six outcomes + both hard-stops.

1. **Capture the oracle from base** commit `e4ef6e850` against the **incumbent**
   `_mt_run_pre_review_gate` — a committed fixture of expected
   `(outcome, scope, transition_applied metadata, block/exit, console)` tuples, authored
   **red-first** and NEVER regenerated from the new code (anti-circular).
2. On the Spec-Kitty tree, drive the same changed-file inputs through the refactored
   handler-plus-hook path (`_mt_run_transition_gates`) for a scenario set covering all six outcomes:
   `NO_COVERAGE`, `NO_NEW_FAILURES`, `NEW_FAILURES`, `UNVERIFIED_BASELINE`, `TIMED_OUT`,
   `CANCELLED`.
3. Assert identical tuples vs the base-captured oracle, including the two hard-stops: `NEW_FAILURES`
   under opt-in blocking + no `--force` → `Exit(1)` same message; `TIMED_OUT`/`CANCELLED` →
   `Exit(1)` with `transition_applied=False`.

**Pass:** golden comparison is byte-identical to the base-captured oracle across 100% of the
scenario set.

---

## (b) Consumer portable gate — failing declared command → `NEW_FAILURES` — SC-001, NFR-004, US1

**Goal.** A non-pytest, non-`src/specify_cli/` consumer is genuinely gated by its own command.

1. Build a simulated consumer checkout with **no** `tests/architectural/_gate_coverage.py` and a
   non-pytest layout; set `review.test_command` to a command whose suite has a **newly-failing**
   test not present at baseline.
2. Move a WP to `for_review`.
3. Assert: the declared command ran; its output was **parsed** into per-failure identities
   (`DeclaredCommandScopeSource.parse_results`); the gate diffed head vs a baseline captured via
   the **same declared command**; the gate yielded a **blocking-capable `NEW_FAILURES`** (not
   `NO_COVERAGE`); and `_gate_coverage` was **never imported**.
4. **Pre-existing-failure fixture (baseline-relative proof).** Repeat with a suite that is
   **already red at baseline** (no new failure at head) → assert the transition is **NOT blocked**
   (pre-existing ≠ new). Then flip one test newly-red → assert it **blocks**. This proves
   `NEW_FAILURES` is baseline-relative, not ANY_FAILURES.

**Pass:** newly-red → `NEW_FAILURES` block; already-red-at-baseline → not blocked; import spy on
`tests.architectural._gate_coverage` records zero imports.

---

## (c) Doctrine toggle changes gate firing with no code edit — SC-003, US3

**Goal.** Activation is the sole selector.

1. Author a gate binding in `review.step-contract.yaml` (`gates`) for `in_progress->for_review` → handler
   `spec-kitty-pre-review`. **Activate** the handler in the repo's doctrine. Move a WP to
   `for_review` → assert the handler runs and contributes its verdict (resolved via the
   activation ⋈ binding join).
2. **Deactivate** the handler in doctrine — **no Python edit**. Move a WP to `for_review` →
   assert the handler does **not** run, and the non-resolution is **detectable** (negative-control
   arm, NFR-003), not silent.
3. Author a second binding with `handler_kind: asset`; load→serialize → assert it round-trips
   **byte-stable** and is **inert** (never executed) in half A.

**Pass:** identical code, opposite firing between (1) and (2); the `asset` binding is unconsumed
and byte-stable.

---

## (d) Fault-inject a handler → visible unverified warning, no crash — SC-004, NFR-002, US4

**Goal.** Per-handler fail-open with deterministic aggregation.

1. Register two handlers on the edge: one raises during execution; the other returns a normal
   verdict.
2. Move a WP to `for_review`.
3. Assert: the transition **completes** (0 crashes); the faulting handler surfaces **exactly one**
   visible "unverified" warning; the other handler's verdict is unaffected.
4. Repeat with the healthy handler returning `NEW_FAILURES` (blocking enabled, no `--force`):
   assert the **block still fires** (the faulting handler does not suppress it) and the fault
   degrades to a warning (US4 AS3).

**Pass:** no crash, one warn per faulting handler, no cross-suppression.

---

## (e) Erroneous activation still never imports `_gate_coverage` — SC-001, FR-009, US1 AS4

**Goal.** Closure does not depend on activation being configured correctly.

1. In the consumer checkout of (b), **force-activate** the Spec-Kitty pre-review handler in the
   consumer's config.
2. Move a WP to `for_review`.
3. Assert: `tests.architectural._gate_coverage` is **still never imported** — the handler's own
   `GateAuthoritiesUnavailable` degrades to a `NO_COVERAGE` warn; the internal-module import never
   succeeds.

**Pass:** import spy records zero successful imports of the internal module even under erroneous
activation.

---

## Cross-cutting checks (every WP; C-005, NFR-006)

- **Non-vacuous resolution** — positive + negative-control arms; a test that would pass against an
  empty graph is rejected (NFR-003).
- **Mission-type axis (distinguishable warn)** — a `research`/`documentation` WP (no
  `(mission, review)` contract) hitting `for_review` yields a `NO_COVERAGE` warn whose reason names
  the missing-contract cause and is **distinct** from the "handler not activated" advisory — assert
  the two reason strings differ (FR-008, FR-012).
- **Save round-trip** — load then re-save an unrelated contract; assert byte-identical output with
  **no** spurious `gates: []` injected (NFR-004).
- **Bounded cost** — assert one graph load + one binding load per transition (NFR-005).
- **Aggregation matrix** — `aggregate_verdicts` / `resolve_active_gate_bindings` unit-tested with
  synthetic handlers over the full outcome × precedence matrix (half A ships one real binding).
- **Quality** — `ruff check .` and `mypy --strict` clean; complexity ≤ 15/function; ≥ 90% new-code
  line coverage.

```bash
# representative local runs
PYTHONPATH=$(pwd)/src pytest tests/ -k "transition_gate or scope_source or gate_binding"
PYTHONPATH=$(pwd)/src pytest tests/architectural/test_no_legacy_terminology.py   # gate terms (FR-015)
ruff check . && mypy --strict src/specify_cli/review/
```
