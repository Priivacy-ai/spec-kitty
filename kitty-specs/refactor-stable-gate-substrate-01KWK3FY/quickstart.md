# Quickstart — refactor-stable-gate-substrate-01KWK3FY

Run from the repo root (lane worktrees share the primary venv:
`export PATH="$PWD/.venv/bin:$PATH"` and use `PYTHONPATH="$PWD/src"`).

## The converted gates (IC-01/02/03)

```bash
PWHEADLESS=1 pytest tests/architectural/test_resolution_authority_gates.py \
  tests/architectural/test_untrusted_path_containment.py -q -p no:cacheprovider
# the audits' own mains (reviewer form):
python -m tests.architectural.untrusted_path_audit.audit 2>/dev/null || true  # check invocation form in the file header
```

## Theater verification (per converted gate — reviewers re-run these)

```bash
PWHEADLESS=1 pytest tests/architectural/ -q -k "drift or theater or vacuity or ghost" -p no:cacheprovider
```

## Doctrine freshness (IC-04)

```bash
PWHEADLESS=1 pytest tests/doctrine/drg/migration/test_extractor.py tests/doctrine/drg/migration/test_path_ref_resolver.py -q
# regenerate (the ONLY sanctioned way):
python -c "from pathlib import Path; import sys; sys.path.insert(0,'src'); from doctrine.drg.migration.extractor import generate_graph; generate_graph(Path('src/doctrine'), Path('src/doctrine/graph.yaml'))"
```

## CT9 determinism (IC-05 — the real shard form, twice)

```bash
SPEC_KITTY_RUN_QUARANTINE=1 PWHEADLESS=1 pytest -m quarantine -q  # pre-check the set
PWHEADLESS=1 pytest <the 5 files> -n auto --dist loadfile -q -p no:cacheprovider  # run 1
PWHEADLESS=1 pytest <the 5 files> -n auto --dist loadfile -q -p no:cacheprovider  # run 2
```

## Full closing sweep (gate-owner mission)

```bash
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q  # pre-push, always
ruff check <touched>; python -m mypy --strict <touched src+tests together>
```

## Watch-list

- Coord-topology mission: artifacts the gates read live on the coordination branch.
- graph.yaml is byte-sensitive — never hand-edit.
- Any parity/theater surprise: revert the step; never adjust floors/fixtures.
- If #2308 (degod-follow-ups) gains commits: rebase tidy/gate-substrate before merge (C-002).
