# Quickstart: verify Kind-Complete Cascade + Orphan Wiring (M5)

All commands run from the repository root checkout with `PYTHONPATH=src`.

## Reproduce the #2829 baseline (should be 0 before the fix)

```python
from doctrine.drg.loader import load_built_in_graph
from charter.cascade import cascade_activation_targets, CascadeScope

g = load_built_in_graph()
for mt in [n.urn for n in g.nodes if n.urn.startswith("mission_type:")]:
    res = cascade_activation_targets(g, mt, CascadeScope.all())
    print(mt, sum(len(v) for v in res.activated.values()))
# Before: every mission_type prints 0.
# After:  every mission_type prints a non-zero count of activatable governance
#         kinds, and no `template`/`asset` appears in res.activated.
```

## Verify the kind-complete filter

```python
# A source whose closure reaches templates/assets must not propose them.
res = cascade_activation_targets(g, "mission_type:documentation", CascadeScope.all())
assert "template" not in res.activated and "asset" not in res.activated
assert sum(len(v) for v in res.activated.values()) > 0
```

## Verify the orphan wiring (pure graph)

```bash
# Regenerate the committed graph fragments and confirm freshness (byte-identity).
spec-kitty doctrine regenerate-graph --check
```

```python
from doctrine.drg.migration.extractor import generate_graph  # pure, no overlay
# (build via the test helper generate_reference_graph / pure path)
# After the fix, these 4 have an inbound edge in the PURE graph:
#   styleguide:given-when-then-authoring, toolguide:gherkin, toolguide:sonar,
#   styleguide:quadruple-a-test-format
# and styleguide:deployable-skill-authoring is recorded direct-activation-only.
```

## Targeted test surface

```bash
PYTHONPATH=src python -m pytest \
  tests/charter/test_cascade.py \
  tests/charter/test_kind_cascade_exhaustive.py \
  tests/doctrine/drg/migration/test_extractor_projection.py \
  tests/doctrine/drg/test_reachability.py \
  -q
ruff check src/charter/cascade.py src/doctrine/drg/migration/
mypy --strict src/charter/cascade.py
```

## Success signals

- All 4 built-in mission-type cascades non-zero (was 0).
- No `template`/`asset` in any cascade activation / no-cascade-warning output.
- `_ACTIVATED_BUT_ORPHANED` shrinks by 5; 4 via frontmatter edges, 1 direct-only.
- `regenerate-graph --check` clean; shipped edge set unchanged.
- `ruff` + `mypy --strict` clean, zero suppressions.
