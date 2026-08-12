# Quickstart — DRG Reachability Metric & Orphan Wiring

Everything runs from the repository root checkout. Use the project `.venv` interpreter for graph
introspection (it has the deps): `.venv/bin/python`.

## 1. Inspect the current reachability residual

```python
from doctrine.drg.loader import load_built_in_graph
from doctrine.drg.reachability import action_channel_reachable, profile_channel_reachable
g = load_built_in_graph()
actions  = [n.urn for n in g.nodes if n.urn.startswith("action:")]
profiles = [n.urn for n in g.nodes if n.urn.startswith("agent_profile:")]
ar2 = set(action_channel_reachable(g, actions, 2))
pr  = set(profile_channel_reachable(g, profiles))
BY_DESIGN = {"mission_step_contract","asset","anti_pattern","template","mission_type","glossary_pack","action","agent_profile"}
kind = lambda u: u.split(":",1)[0]
unreachable = {n.urn for n in g.nodes if n.urn not in ar2 and n.urn not in pr and kind(n.urn) not in BY_DESIGN}
print(len(unreachable))   # 38 before wiring, 34 after
```

## 2. Author an edge (correctly — via the model, not dataclasses.replace)

Add tuples to `_CURATED_ARTIFACT_EDGES` in `src/doctrine/drg/migration/extractor.py`, each with an inline
rationale comment. To verify an edge's effect before committing:

```python
from doctrine.drg.models import DRGEdge, Relation
g2 = g.model_copy(update={"edges": list(g.edges) + [
    DRGEdge(source="procedure:refactoring", target="directive:DISCIPLINED_REFACTORING", relation=Relation.SUGGESTS),
]})
# re-run the reachability computation on g2
```

## 3. Regenerate the shipped graph fragments (deterministic)

```bash
# ⚠️ Use .venv/bin/spec-kitty — bare `spec-kitty` is a pyenv shim resolving a DIFFERENT checkout
# (SHADOW_CLONES/spec-kitty_THREE). Only .venv/bin/spec-kitty resolves THIS repo's packs/built-in.
.venv/bin/spec-kitty doctrine regenerate-graph            # writes packs/built-in/*.graph.yaml
.venv/bin/spec-kitty doctrine regenerate-graph --check    # verify byte-identical / no drift (path must be under fork/spec-kitty)
git diff --stat packs/built-in/                           # review the regenerated fragments
```

## 4. Run the guards

```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/doctrine/drg/test_reachability.py \
  tests/doctrine/drg/migration/test_extractor_projection.py \
  tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py -q
```

Then the full DRG area + lint/type:

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/doctrine/drg/ -q
ruff check src/doctrine/drg/ tests/doctrine/drg/
mypy src/doctrine/drg/migration/extractor.py
```

## 5. Ledger discipline (do not skip)

Every moved pin needs a row in `docs/plans/doctrine/delivery-reachability-wiring-table.md` naming the
responsible edge, and a numbered-ledger entry in `test_extractor_projection.py`. A pin change with no
ledger row is a hard review reject even if the assertion is green (D18 gate / NFR-004).

## 6. Terminology guard (pre-push, doctrine/prose touched)

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q
```
