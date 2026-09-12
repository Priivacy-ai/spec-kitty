# Quickstart: verify SymbolKey source_module (#3552)

Test-infrastructure change; no runtime surface. All verification is `pytest` + lint/type.

## Run the touched gates

```bash
# Non-goal guards (G1–G6)
PWHEADLESS=1 uv run pytest tests/unit/test_symbol_key.py -q

# The dead-symbol gate + refresh helper (no regression; acceptance anchor)
PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py \
  tests/architectural/test_refresh_dead_symbol_hashes.py -q

# Ratchet baselines must be unchanged (no key added/moved)
PWHEADLESS=1 uv run pytest tests/architectural/test_ratchet_baselines.py -q
```

## Lint / type

```bash
uv run ruff check tests/architectural/_symbol_key.py tests/architectural/test_no_dead_symbols.py \
  tests/architectural/_refresh_dead_symbol_hashes.py tests/unit/test_symbol_key.py
uv run mypy --strict tests/architectural/_symbol_key.py tests/architectural/_refresh_dead_symbol_hashes.py
```

## Backfill verification (IC-02)

```bash
# Every content-tier entry carries source_module (SC-001: expect 338)
grep -c "source_module=" tests/architectural/test_no_dead_symbols.py
# No machine comment-parse surface remains (SC-004: expect 0)
grep -nE "_recover_provenance|_PROVENANCE_COMMENT_RE|_comments_by_row|test_every_content_tier_entry_has_parseable_provenance_comment" \
  tests/architectural/ -r || echo "all parse surfaces retired"
```

## Success signals

- G1–G6 present and green (incl. keystone G6).
- `test_no_dead_symbols` + refresh-helper suites green; allowlist cardinality 363.
- `test_ratchet_baselines` baselines unchanged.
- ruff 0, mypy 0; no `pyproject.toml` version diff.
- #3560 Finding-1 collision resolves without `NEEDS_MODULE_PATH`.
