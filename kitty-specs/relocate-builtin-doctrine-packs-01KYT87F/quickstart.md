# Quickstart: verify the built-in relocation

Prereqs: repo checkout on `feat/relocate-builtin-doctrine-packs`.

## 1. Capture the pre-move baseline (do this BEFORE moving anything)

```bash
PYTHONPATH=src python - <<'PY'
from doctrine.drg.loader import load_built_in_graph
g = load_built_in_graph()
urns = sorted(n.urn for n in g.nodes)
edges = sorted((e.source, e.relation, e.target) for e in g.edges)
import json, pathlib
pathlib.Path("kitty-specs/relocate-builtin-doctrine-packs-01KYT87F/graph-identity.baseline.json").write_text(
    json.dumps({"nodes": urns, "edges": [list(t) for t in edges]}))
print(len(urns), len(edges))   # expect 324 892
PY
```

## 2. After relocation — identity must hold

```bash
PYTHONPATH=src python - <<'PY'
from doctrine.drg.loader import load_built_in_graph
import json, pathlib
base = json.loads(pathlib.Path("kitty-specs/relocate-builtin-doctrine-packs-01KYT87F/graph-identity.baseline.json").read_text())
g = load_built_in_graph()
assert sorted(n.urn for n in g.nodes) == base["nodes"], "node-URN set drift"
assert sorted([e.source, e.relation, e.target] for e in g.edges) == base["edges"], "edge-triple drift"
print("graph identity preserved")
PY
spec-kitty doctor doctrine --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('profiles', d['profile_health'])"
```

## 3. Guard: nothing resolves from src/doctrine

```bash
PYTHONPATH=src python -c "from doctrine.pack_paths import resolve_pack_root; p=resolve_pack_root('built-in'); assert p.is_relative_to('packs/built-in') or 'packs/built-in' in str(p), p; print('resolves from', p)"
git grep -nE 'files\("doctrine\.(agent_profiles|directives|procedures|tactics|paradigms|styleguides|toolguides|assets|glossary_packs)"\)' src/ && echo "FAIL: per-kind anchors remain" || echo "OK: no per-kind content anchors"
```

## 4. Packaging parity (two-layout)

```bash
# wheel + sdist carry packs/built-in; clean-venv install resolves it
python -m build 2>&1 | tail -2
# inspect: unzip -Z1 dist/*.whl | grep -c '^packs/built-in/' ; tar tzf dist/*.tar.gz | grep -c 'packs/built-in/'
```
