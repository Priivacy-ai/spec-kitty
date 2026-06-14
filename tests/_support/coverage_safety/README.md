# Coverage-safety harness (WP02)

Reusable, pure/deterministic safeguards that let every later test reduction or
parallelization flip in the `test-suite-acceleration` mission be *proven*
coverage-neutral. WP03 (item-explosion dedup) and WP05 (CI shard
parallelization) consume these helpers.

| Helper | Module | Contract |
|--------|--------|----------|
| Collection equivalence | `collection_equivalence.py` | C-EQUIV, FR-004, E3 |
| Stability ratchet | `ratchet.py` | C-RATCHET, FR-012, NFR-005, E4 |
| Mutation / anti-vacuity | `equivalence.py` | C-001 |

The architectural guard `tests/architectural/test_real_home_isolation_guard.py`
(SC-006) lives outside this package but follows the same conventions.

## 1. Prove a shard collects the same nodeids serially and in parallel (C-EQUIV)

```python
from tests._support.coverage_safety import assert_equivalent

shard = ["tests/agent", "-m", "not slow"]
assert_equivalent(
    serial_args=shard,
    parallel_args=[*shard, "-n", "auto", "--dist", "loadfile"],
)
```

On mismatch this raises `CollectionEquivalenceError` naming the symmetric
difference (which nodeids the parallel run is missing or has extra). An
**intended** count change must be asserted explicitly with a reviewed delta
(NFR-007) — the helper never hides one.

## 2. Accept a parallelization flip only after N green runs (C-RATCHET)

From CI or locally:

```bash
python -m tests._support.coverage_safety.ratchet -n 3 -- tests/agent -m "not slow"
```

Exit code `0` ⇒ all N runs green ⇒ the flip is accepted; `1` ⇒ rejected (the
summary names any new/flaky failures). In Python:

```python
from tests._support.coverage_safety import run_ratchet

result = run_ratchet(["tests/agent", "-m", "not slow"], n=3)
assert result.accepted, result.summary()
```

## 3. Prove a collapsed/parametrized test still catches a planted regression (C-001)

This is the recipe for **anti-vacuity** after a test collapse (e.g. the WP03 FSM
collapse). Extract the assertion body into a `check` callable, then plant one
known-bad mutation and confirm the check now fails and names it:

```python
from tests._support.coverage_safety import (
    Mutation,
    assert_mutation_caught,
)

# 1. The assertion body, extracted so it can run against arbitrary data.
def check(transitions: dict[str, str]) -> None:
    assert transitions["planned"] == "claimed"

good = {"planned": "claimed", "claimed": "in_progress"}

# 2. A single planted regression: the collapsed test MUST catch this.
def break_first_edge(t: dict[str, str]) -> dict[str, str]:
    t["planned"] = "WRONG"
    return t

assert_mutation_caught(
    check,
    good,
    Mutation(name="planned->claimed edge dropped", apply=break_first_edge),
)
```

If the mutated run still passes, `assert_mutation_caught` raises
`MutationNotCaughtError` naming the mutation — proof the collapsed test is
vacuous for that regression class and must be strengthened. The good data is
deep-copied before mutation, so the original is never disturbed.

### Recommended workflow when collapsing a test

1. Collapse / parametrize the test.
2. For **each** distinct behaviour the original asserted, write a `Mutation`
   that breaks exactly that behaviour.
3. Wrap the new assertion body in a `check(...)` callable.
4. Add one `assert_mutation_caught(check, good, mutation)` per mutation.

A collapse is only safe once every original behaviour has a mutation that the
new test demonstrably catches.
