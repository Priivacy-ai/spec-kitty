# Quickstart: Frozen-baseline toll reduction

How a developer exercises the mission's deliverables once implemented. All commands from the repository root, using the repo `.venv` (never `uv run` — it rebuilds the venv).

## Refresh a dead-symbol hash after a body edit (FR-001/FR-002)

You edited a still-dead allowlisted symbol's body; `test_no_dead_symbols` REDs with an **offender** finding.

```bash
# Refresh hashes for still-dead allowlisted symbols (fail-closed; never admits a new dead symbol)
PWHEADLESS=1 .venv/bin/python -m tests.architectural._refresh_dead_symbol_hashes   # exact entrypoint per WP01
# Verify:
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_dead_symbols.py -q
```

If the helper **refuses** (a `bare_name` it cannot disambiguate), it prints the ambiguous name — add/fix the `# <module>::<Name>` provenance comment or escalate the entry to collision-tier; it will never silently guess.

## Run the two cheap gates locally before pushing (FR-006)

```bash
# Both sub-second gates are now fast-marked; the ~72s dead-symbols gate is NOT selected
PWHEADLESS=1 .venv/bin/python -m pytest -m fast tests/architectural/test_ratchet_baselines.py tests/architectural/test_ratchet_positional_anchor_ban.py -q
```

## Add a skip-marker without a CI hard-fail (FR-003)

Add a `# round-trip: skip: <reason>` line **on the exempted block** (the reason is mandatory and lands in your PR diff for review). CI no longer hard-fails on the count; the reviewer sees the reason line.

## Add a migration module without a baseline bump (FR-004)

Drop a new `m_*.py`; name it in the `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` frozenset (the one meaningful acknowledgment). The `category_1` **count** now derives itself — no `_baselines.yaml` edit.

## Verify the whole mission stayed within its fence

```bash
# Load-bearing gates unchanged + no regressions (NFR-003)
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py tests/architectural/test_ratchet_positional_anchor_ban.py -q
.venv/bin/ruff check tests/architectural/
.venv/bin/mypy --strict tests/architectural/_refresh_dead_symbol_hashes.py
```
