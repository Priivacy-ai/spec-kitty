# Quickstart — Verify Single-Authority Resolution Parity

How to prove the mission's four success criteria end to end. Run from the repository root with the shadow venv on PATH.

```bash
export PATH="$PWD/.venv/bin:$PATH"
export SPEC_KITTY_SYNC_DISABLE=1   # skip the claim-time full-suite gate during local checks
```

## SC-001 — Nested org/project doctrine discovered & activatable (0 silent drops)
```bash
# The red-first tests that fail before the fix, pass after:
pytest tests/doctrine -k "nested and (tactic or agent_profile) and recurs" -q
pytest tests/charter -k "nested and styleguide and activate" -q
```
Expected after fix: a `*.tactic.yaml` / `*.agent.yaml` authored one directory deep in an org pack or project overlay is discovered by the loader **and** resolved by charter activation — matching built-in. Tactic undercount 71% → 0%.

## SC-002 — Loader/resolver parity, falsifiable gate
```bash
pytest tests/doctrine/drg/test_kind_mapping_totality.py -q
```
- Green when loader and resolver agree for 100% of kinds.
- The falsifiability test reintroduces a `recursive=False` divergence and asserts the gate **reddens and names the kind**, then restores and asserts green.

## SC-003 — `--include glossary_pack` / `anti_pattern` resolves (no unknown-selector error)
```bash
pytest tests/charter -k "include and (glossary_pack or anti_pattern)" -q
```
Expected: `charter context --include glossary_pack:<id>` renders; `--include anti_pattern:<id>` resolves to a normal "no such artifact" not-found — **neither** raises "Unsupported --include selector kind".

## SC-004 — No regression; flat-layout output unchanged; NO golden ripple (C-004)
```bash
# Flat-layout activation output byte-identical:
pytest tests/charter -k "flat and activation and (byte or unchanged or golden)" -q
# Vocabulary round-trip + 10-kind (incl anti_pattern):
pytest tests/doctrine -k "artifact_kinds and (round_trip or charter_activatable)" -q
# GOLDEN-COUNT STOP GATE — must show ZERO change vs base:
pytest tests -k "golden and (cascade or drg or count)" -q
```
**If any golden count moves, STOP** — scope has exceeded M1; the ripple belongs to M2 (#3572) / M5 (#2829). Do not "fix" the golden file.

## Full targeted gate before hand-off
```bash
ruff check src/doctrine src/charter tests/doctrine tests/charter
mypy --strict src/doctrine/discovery_recursion.py src/charter/kind_vocabulary.py   # + touched modules
pytest tests/architectural/test_no_legacy_terminology.py -q                        # terminology canon
pytest tests/architectural/test_runtime_charter_doctrine_boundary.py -q            # layer boundary (C-006)
```

> Note: do **not** run the entire suite locally (≈1 h, breaks the session) — CI is the release authority. Use the targeted selectors above.
