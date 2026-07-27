# Quickstart — DRG completeness (#2843)

Run from the repo root (`doctrine/drg-completeness-2843`), always via `uv run`.

## Item B — activation gate

```bash
# Red-first characterization (must be RED on merge-base, GREEN after the fix; with a GREEN canonical-id control)
uv run pytest tests/charter/ -k "activation and (stem or canonical)" -q

# Full consumer regression net + charter suite
uv run pytest tests/charter/ tests/doctrine/ -q

# Gates
uv run ruff check src/charter/drg.py src/charter/consistency_check.py
uv run python -m mypy --strict src/charter
```

Manual live-bug sanity (D1): with this repo's populated `.kittify/config.yaml`, a charter-mediated
resolve (`reference_resolver` / `_check_drg_cross_kind_refs`) drops the 26 activated directive nodes
before the fix and retains them after.

## Item A — relation parity

```bash
# Completeness gate (converted from == {3} to == set(Relation))
uv run pytest tests/doctrine/drg/test_models.py -q

# Content-equality parity on the single surface (doctrine-relationships.md), _SCOPED_RELATIONS 3->15
uv run pytest tests/doctrine/test_relation_doc_parity.py -q

# Terminology guard (before pushing doctrine/prose)
uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Whole-mission green bar

```bash
uv run pytest tests/charter/ tests/doctrine/ tests/architectural/test_no_legacy_terminology.py -q
uv run ruff check . && uv run python -m mypy --strict src/charter src/doctrine
```
