# Quickstart: Operating-Procedures Validate, Triage, Data-Drive

**Mission**: operating-procedures-validate-triage-01M0DR8F

Prereqs: `.venv/bin/python`; run from repo root. Use `PYTHONPATH=src` if invoking modules directly.

## Prove the defect (before the fix)

```bash
# Census: 6 real / 8 wrong-kind / 36 fictional (50 total)
.venv/bin/python - <<'PY'
from pathlib import Path
from ruamel.yaml import YAML
y=YAML(typ="safe"); root=Path("packs/built-in")
procs={y.load(f).get("id") for f in (root/"procedures").glob("*.procedure.yaml")}
u=0
for f in sorted((root/"agent_profiles").glob("*.agent.yaml")):
    d=y.load(f); ops=(d.get("collaboration") or {}).get("operating-procedures") or []
    for op in ops:
        if op not in procs: u+=1
print("unresolved op-proc entries (built-in):", u)   # 44 before, 0 after
PY
```

## WP01 — Validate & Triage

```bash
# Red-first: the empty-set gate fails (44 unresolved)
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_operating_procedures_resolve.py -q
# ... triage the 44 (delete fictional, migrate wrong-kind tactics to tactic-references) ...
# Green: gate passes (0 unresolved)
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_operating_procedures_resolve.py -q

# Diagnostic surface
spec-kitty doctor doctrine --json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('org_drg',{}).get('operating_procedures_unresolved'))"
```

## WP02 — Data-drive & wire

```bash
# Red-first: extractor emission test (resolvable→edge, unresolvable→none)
PWHEADLESS=1 .venv/bin/python -m pytest tests/doctrine/drg/migration/test_extractor.py -q

# Regenerate the committed graph after teaching the extractor + retiring pins + RECONCILE edge
spec-kitty doctrine regenerate-graph
# Freshness gate must be green
spec-kitty doctrine regenerate-graph --check

# Confirm the delta: 8 agent_profile->procedure edges, 3 RECONCILE inbound
.venv/bin/python - <<'PY'
from pathlib import Path
from doctrine.drg.migration.extractor import extract_artifact_edges
_,edges=extract_artifact_edges(Path("packs/built-in"))
ap=[e for e in edges if e.source.startswith("agent_profile:") and e.target.startswith("procedure:")]
rec=[e for e in edges if e.target=="directive:RECONCILE_CHANGE_SCOPE_TENSIONS"]
print("agent_profile->procedure edges:", len(ap))   # 8
print("RECONCILE inbound:", len(rec))                # 3
PY
```

## Full validation surface

```bash
# Targeted suites (scoped change)
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/doctrine/drg/migration/ tests/doctrine/agent_profiles/ tests/doctrine/test_profile_model.py \
  tests/architectural/test_operating_procedures_resolve.py \
  tests/architectural/test_doctrine_regenerate_graph_roundtrip.py -q

# Terminology + lint + types
pytest tests/architectural/test_no_legacy_terminology.py -q
ruff check src/doctrine src/specify_cli/cli/commands
.venv/bin/python -m mypy --strict src/doctrine/agent_profiles/operating_procedures.py
```

## Success signals

- Census script prints `0` unresolved.
- Empty-set gate green; injecting a fictional entry reddens it.
- `regenerate-graph --check` exit 0; `agent_profile→procedure` = 8, RECONCILE inbound = 3.
- `assert_valid` passes (zero dangling); ruff + mypy --strict clean.
