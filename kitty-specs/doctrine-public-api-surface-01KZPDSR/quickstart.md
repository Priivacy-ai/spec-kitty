# Quickstart — Doctrine Public API Surface

How to run the mission's gates and reproduce the census. All commands from the repo root on
`feat/doctrine-public-api-surface`. Use the `.venv` python for tests (never a bare `uv run`,
which re-syncs and can destroy a hand-built `.venv`).

## Re-run the reach-through census (IC-01, at implement start)

```bash
# Direct + lazy doctrine.* imports from runtime, outside the exempt subpackage:
grep -rEn "^[[:space:]]*(from doctrine|import doctrine)" src/specify_cli/ \
  | grep -v "src/specify_cli/doctrine/"
# First-party re-export laundering conduit (consumers of specify_cli.doctrine.* doctrine objects):
grep -rEn "from specify_cli.doctrine" src/specify_cli/ | grep -v "src/specify_cli/doctrine/"
# Raw sole-door construction sites (use RawDoctrineService — a bare DoctrineService( grep
# is polluted by the sanctioned ActivationAwareDoctrineService wrapper + docstrings):
grep -rEn "RawDoctrineService\(" src/specify_cli/
```

Fold the AST-accurate classification into `data-model.md`'s disposition table before touching
facades.

## Run the architectural gates (fast — targeted, not the full suite)

```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/architectural/test_runtime_charter_doctrine_boundary.py \
  tests/architectural/test_charter_facades_reexport_doctrine.py \
  tests/architectural/test_charter_sole_door_doctrine_service.py \
  tests/architectural/test_doctrine_public_surface.py \
  tests/architectural/test_doctrine_wheel_closure.py \
  tests/architectural/test_no_dead_symbols.py \
  -q
```

Run the terminology guard when touching doctrine/prose (CI-only gate otherwise):

```bash
.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Behavior-preservation guard for FR-009 / FR-010

The committed `packs/built-in/**/*.graph.yaml` (14 files) **are** the golden — no separate
fixture is needed. The CLI already ships a byte-identity gate (`--check` regenerates to a
tempdir and compares against the committed source):

```bash
# Reinstall first to avoid the stale-install false-red (regenerate-graph shells out):
pip install -e . >/dev/null
# Byte-identity gate — exits non-zero on any drift after the refactor:
spec-kitty doctrine regenerate-graph --check
# (equivalently: regenerate then `git diff --exit-code -- packs/built-in`)
```

Wire this `--check` invocation into CI as the FR-009/FR-010 round-trip test so byte-identity
is machine-enforced, not a manual ritual.

## Quality gates before pushing

```bash
ruff check src/doctrine src/charter src/specify_cli     # C901 complexity ≤ 15
.venv/bin/mypy --strict src/doctrine/api.py src/charter # public surface + facades
```

## Definition-of-done checklist (maps to contracts)

- [ ] `doctrine/api.py` exists, `__all__` pinned by wheel-closure; no-dead-symbol interaction resolved (C1)
- [ ] All new/widened facade re-exports are symbol-level identity + in `__all__` (C2)
- [ ] Lazy-import ratchet green; baseline shrunk to zero for migrated files (C3)
- [ ] Laundering conduit closed; management surface enumerated inbound-only (C4)
- [ ] Raw DoctrineService sites routed through the builder (C5)
- [ ] Truly-INTERNAL negative test green (C6)
- [ ] regenerate-graph byte-identical; helpers tested; cc ≤ 15 (C7)
- [ ] Regression-delta gate holds; no Sonar-UI triage; CHANGELOG entry added (C8, DIR-009)
