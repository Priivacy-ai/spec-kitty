# Contract — Ratchet Baseline Format

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-110, FR-111, FR-112, FR-141 | Companions: [contract-round-trip-frontmatter.md](contract-round-trip-frontmatter.md)
> Data model: [../data-model.md §7](../data-model.md#7-ratchetbaseline-fr-110-fr-141)

The ratchet baseline file (`tests/architectural/_baselines.yaml`) is the canonical statement of allowlist-size intent for every mutable architectural ratchet in the test suite. The companion meta-test (`test_ratchet_baselines.py`) FAILS on growth above baseline and WARNS (informationally) on shrinkage so the baseline gets edited downward in the same PR.

---

## Input Contract

### File location

`tests/architectural/_baselines.yaml`. Checked in. Per C-004 (binding) the file participates in the project charter's burn-down policy (FR-303(a)).

### Schema

#### Real-values example (the gate's positive case)

This block is what an actual `_baselines.yaml` looks like at HEAD after WP01 + WP03 land. The contract round-trip gate parses this block and asserts it validates cleanly against `BaselinesFile`.

```yaml
# pydantic_model: tests.architectural.test_ratchet_baselines.BaselinesFile
# expect: valid
test_no_dead_modules:
  category_1_auto_discovered: 70
  category_2_schema_generators: 4
  category_3_external_entry_points: 4
  category_4_compat_shims: 8
  category_5_slot_holders: 3
  category_6_internal_runtime: 3
  category_7_grandfathered: 7      # MUST SHRINK -- C-006 target 0 by 4.0

test_migration_chain_integrity:
  known_line_jumps: 4
  known_patch_skips: 9             # NEW with Gap-A8

test_runtime_charter_doctrine_boundary:
  baseline_allowlist: 0

test_auth_transport_singleton:
  allowed_direct_httpx_files: 2    # NO CHANGE this mission (C-005)

test_compat_shims:
  pure_shim_files: 3               # MUST SHRINK -- C-006 target 0 by 4.0

test_example_round_trip:
  legacy_contract_allowlist: 151   # WP03 discovery sweep; shrinks as legacy contracts gain frontmatter

test_all_declarations_required:
  charter_without_all: 0           # all migrated at WP02
  kernel_without_all: 0            # all migrated at WP02
```

#### Schema-shape example with placeholders (the gate's negative case)

This block illustrates the schema shape for documentation purposes with placeholder values where the live count is operator-dependent. The contract round-trip gate parses this block and asserts it correctly FAILS validation (placeholders are strings, not the `int` the schema demands). This pattern doubles as a regression-test for the validator: if the validator silently coerced strings to ints (a bug class), this block would parse cleanly and the gate would flag it.

```yaml
# pydantic_model: tests.architectural.test_ratchet_baselines.BaselinesFile
# expect: invalid
# expect_message: Input should be a valid integer
test_no_dead_modules:
  category_1_auto_discovered: <count-at-HEAD>
  category_2_schema_generators: <count-at-HEAD>
  category_3_external_entry_points: <count-at-HEAD>
  category_4_compat_shims: <count-at-HEAD>
  category_5_slot_holders: <count-at-HEAD>
  category_6_internal_runtime: <count-at-HEAD>
  category_7_grandfathered: <count-at-HEAD>

test_migration_chain_integrity:
  known_line_jumps: <count-at-HEAD>
  known_patch_skips: <count-at-HEAD>

test_runtime_charter_doctrine_boundary:
  baseline_allowlist: <count-at-HEAD>

test_auth_transport_singleton:
  allowed_direct_httpx_files: <count-at-HEAD>

test_compat_shims:
  pure_shim_files: <count-at-HEAD>

test_example_round_trip:
  legacy_contract_allowlist: <discovered-at-WP03>

test_all_declarations_required:
  charter_without_all: 0
  kernel_without_all: 0
```

(Initial values for this mission: WP01 implementer reads HEAD-of-mission-branch sizes and pins them. The Cat-7 value `7` reflects the FR-113 same-PR shrinkage from 10.)

### Per-test, per-category interpretation

- A test with a single mutable allowlist (e.g. `test_runtime_charter_doctrine_boundary`) maps to a single integer baseline.
- A test with multiple categorised allowlists (e.g. `test_no_dead_modules` after FR-112 refactor) maps to a sub-dict of per-category integers.

### Per-PR baseline edit policy

Per C-004 binding:

- Growing a baseline requires a one-line YAML diff in the same PR.
- The PR description MUST include a `rationale:` line naming why growth is justified.
- A PR that grows Cat-7 specifically MUST link a follow-up tracker ticket per FR-303's burn-down policy.
- Shrinkage requires no ceremony.

---

## Output Contract

### Meta-test API — `tests/architectural/test_ratchet_baselines.py`

The meta-test imports each gated module dynamically and inspects the size of its frozenset / dict. Pseudocode:

```python
import yaml
import importlib

BASELINES = yaml.safe_load((Path(__file__).parent / "_baselines.yaml").read_text())

def test_no_dead_modules_per_category():
    from tests.architectural.test_no_dead_modules import (
        _CATEGORY_1, _CATEGORY_2, ..., _CATEGORY_7,
    )
    for name, current in {
        "category_1_auto_discovered": len(_CATEGORY_1),
        ...
        "category_7_grandfathered": len(_CATEGORY_7),
    }.items():
        baseline = BASELINES["test_no_dead_modules"][name]
        if current > baseline:
            pytest.fail(
                f"Allowlist `{name}` grew from baseline {baseline} to {current}. "
                f"Either remove the new entry OR edit _baselines.yaml from {baseline} "
                f"to {current} with a justification comment in the PR."
            )
        elif current < baseline:
            warnings.warn(
                f"Allowlist `{name}` shrunk from baseline {baseline} to {current}. "
                f"Edit _baselines.yaml in this PR to lock in the shrinkage."
            )
```

### Failure shape

When the meta-test FAILS (growth above baseline), the message names:

1. The test file / category (e.g. `test_no_dead_modules.category_7_grandfathered`).
2. The baseline value.
3. The current value.
4. The remediation hint (remove the entry OR edit the baseline with justification).

When the meta-test WARNS (shrinkage below baseline), the message names:

1. The category.
2. The new lower bound (current value).
3. The instruction to edit `_baselines.yaml` in this PR.

### Per-test invariants

| Test | Invariant |
|---|---|
| `test_no_dead_modules` | Per-category baselines; Cat-7 MUST shrink each major release per C-006 (≥ 2 entries per major; target 0 by 4.0) |
| `test_migration_chain_integrity.known_line_jumps` | Cap on intentional line jumps; grows only with HiC-approved exception |
| `test_runtime_charter_doctrine_boundary.baseline_allowlist` | Cap at 2 documented exceptions per Mission B C-004; this mission keeps it at 0 |
| `test_auth_transport_singleton.allowed_direct_httpx_files` | NO CHANGE this mission per C-005 |
| `test_compat_shims.pure_shim_files` | Per C-006, target 0 by 4.0 |
| `test_example_round_trip.legacy_contract_allowlist` | Per FR-141; shrinks over time as legacy contracts gain frontmatter |
| `test_all_declarations_required.{charter,kernel}_without_all` | After WP02 lands, MUST stay at 0 |

---

## Failure modes

| Trigger | Reporter | Operator message |
|---|---|---|
| New entry added to `_ALLOWLIST` without baseline edit | `test_ratchet_baselines.py::test_no_dead_modules_per_category` FAIL | "Allowlist `category_<n>_<name>` grew from baseline `<b>` to `<c>`. Either remove the new entry OR edit `_baselines.yaml` from `<b>` to `<c>` with a justification comment in the PR." |
| Entry removed from `_ALLOWLIST` without baseline edit | `test_ratchet_baselines.py` WARN | "Allowlist `category_<n>_<name>` shrunk from baseline `<b>` to `<c>`. Edit `_baselines.yaml` in this PR to lock in the shrinkage." |
| `_baselines.yaml` missing | `test_ratchet_baselines.py` collection error | "`tests/architectural/_baselines.yaml` is missing. This file is a binding ratchet artefact per C-004; restore it from the previous commit OR run the WP01 bootstrap script." |
| `_baselines.yaml` malformed (e.g. wrong key for `test_no_dead_modules`) | `pydantic.ValidationError` via the `BaselinesFile` model | Per pydantic; names the offending key |

---

## Backward compatibility guarantee

- `_baselines.yaml` is **additive**: introducing it does not modify any existing allowlist nor any pre-existing test's pass/fail behaviour.
- The meta-test `test_ratchet_baselines.py` is a separate test file; existing CI does not regress because the gated tests themselves are unchanged in semantics (only categorised in FR-112's refactor).
- For tests not yet listed in `_baselines.yaml` (e.g. a future gate added in a follow-up mission), the meta-test treats them as "no baseline pinned" and skips them with a `pytest.skip` reason — they participate in the burn-down model only when an explicit baseline entry is added.

---

## Charter pinning (per FR-303(a) / C-004 binding)

After Mission C ships, the project charter (`.kittify/charter/charter.md`) carries:

> **Burn-down policy.** Per-category allowlist sizes recorded in `tests/architectural/_baselines.yaml` may shrink between releases but never grow except via documented exception (rationale comment + tracker reference). Cat-7 (grandfathered orphans) MUST shrink by ≥2 entries per major release; target = 0 by 4.0. Pure-shim files in `compat/_adapters/` MUST go to 0 by 4.0.

---

## ATDD anchors

- `tests/architectural/test_ratchet_baselines.py` (the meta-test itself; FR-111)
- `tests/architectural/test_no_dead_modules.py` (refactored per FR-112; the gate the meta-test guards)
- `tests/contract/test_example_round_trip.py` (legacy-contract-allowlist shrinkage participates per FR-141)
