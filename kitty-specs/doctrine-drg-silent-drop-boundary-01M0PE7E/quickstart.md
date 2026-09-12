# Quickstart — verify each fix

Use the shadow venv (repo memory): `export PATH="$PWD/.venv/bin:$PATH"`.
Run targeted tests only — never the full suite in-session.

## IC-1 — DRG node-kind SSOT (#3608)

```bash
# drift-guard (new): recognized set == NodeKind values
.venv/bin/python -m pytest tests/architectural/ -k "drg_node_kind or node_kinds_drift" -q
# manual sanity: a previously-dropped kind now resolves
.venv/bin/python - <<'PY'
from charter.synthesizer.topic_resolver import _DRG_NODE_KINDS
from doctrine.drg.models import NodeKind
missing = {k.value for k in NodeKind} - _DRG_NODE_KINDS
print("missing:", missing)  # expect: set()
PY
```

## IC-2 — profile-reference consolidation (#3629 p1)

```bash
# extractor projects from *-references; context-sources rejected at load
.venv/bin/python -m pytest tests/doctrine/drg/migration/ -k "reference or context_sources or projection" -q
# migration moves authored refs; no context-sources left in shipped profiles
grep -rl "context-sources" packs/built-in/agent_profiles/ && echo "FAIL: still present" || echo "OK: none remain"
```

## IC-3 — governance-profile fail-loud (#3629 p2, verify)

```bash
.venv/bin/python -m pytest tests/doctrine/drg/migration/test_extractor.py -k "governance_scope or resolve" -q
# add/confirm an org-tier variant of the nonexistent-selection test
```

## IC-4 — org_roots seam folds fragments (#3530)

```bash
# the executor/action-bundle seam must fold packs/internal's drg/fragment.yaml
.venv/bin/python -m pytest tests/specify_cli/mission_step_contracts/test_executor.py -q
.venv/bin/python -m pytest tests/ -k "action_doctrine_bundle or drg_helpers or org_roots" -q
```

## IC-5 — chain delivery on built-in + spec-kitty-internal (#3530 close)

```bash
.venv/bin/python -m pytest tests/integration/ -k "chain or three_layer or org_pack" -q
# new: assert every kind packs/internal declares reaches the consumer via the seam,
# and a misconfigured variant fails loud
```

## Pre-push gates

```bash
.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q   # terminology canon
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/   # touched modules; zero new issues, zero new suppressions
```
