# Quickstart — verify locally

All from the repo root with `uv run`.

## Regenerate + inspect the edges

```bash
uv run spec-kitty doctrine regenerate-graph          # rewrites src/doctrine/graph.yaml
uv run python - <<'PY'
from pathlib import Path
from ruamel.yaml import YAML
d = YAML(typ="safe").load(Path("src/doctrine/graph.yaml"))
mt = [e for e in d["edges"] if e["source"].startswith("mission_type:") and e["relation"] == "requires"]
print("mission_type→action requires edges:", len(mt))   # expect 21
urns = {n["urn"] for n in d["nodes"]}; inc = {x for e in d["edges"] for x in (e["source"], e["target"])}
print("orphans:", len(urns - inc))                        # expect 10
PY
```

## Gates

```bash
uv run pytest tests/doctrine/drg/test_mission_type_nodes.py \
  tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py \
  tests/doctrine/drg/migration/test_extractor.py -q          # orphan gate green, re-pin green, freshness green
uv run spec-kitty doctrine regenerate-graph --check --json   # byte-identity fresh
uv run ruff check src/doctrine/drg tests/doctrine/drg
uv run mypy --strict src/doctrine/drg/migration/extractor.py src/doctrine/drg/models.py
```
