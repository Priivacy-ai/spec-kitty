# Contract: Census Owner-Adoption Invariants (#3121 / C-011)

This mission is a test-isolation refactor — it exposes no new runtime interface. The binding
"contracts" it must honor are the existing census invariants and the canonical-owner behaviour.

## Invariants the fix must preserve (read-only — enforced by `tests/architectural/`)

1. **Census equality** (`test_spec_kitty_home_pin_census.py`, t023): `census == anchor` and
   `discover(tests) − E == anchor`. The fix restores this by making `discover()` return to the
   frozen 40-member class — NOT by editing `census`, `anchor`, or `members.json`.
2. **Set-equality, never containment** (t022–t026): no test is weakened; equalities stay `==`.
3. **Exempt-set arity** (`_home_pin_exempt.py`): `E` remains `tuple[Exempt, Exempt]`; no third
   entry (`mypy --strict` clean).
4. **Ratchet still bites** (NFR-001): injecting any new `SPEC_KITTY_HOME`→`<tmp_path>/home`
   pin makes the census red. Verified by the T003 red-injection proof.

## Owner-adoption contract (consumed, not modified)

- `canonical_home` (`tests/conftest.py`) is the single exempt `SPEC_KITTY_HOME` owner. A test
  that requests it by parameter and writes no `setenv` of its own gets a fresh per-test
  `<tmp_path>/home` (mkdir'd) and adds **no** census row.
- A consumer that requests the owner **and keeps its own pin** still counts as a member — so
  the fix MUST delete the test's `setenv`, not merely add the fixture.

## Scope boundary

- Addresses only the acute `arch_shard_3` red owed to the new #3497 pin. Does **not** close
  #3121 (operator halt-and-rescope); the broader R1b convergence is deferred.
- No production/behaviour change (`sync/layout_generation.py` untouched — C-005).
