# Contract: `charter/_io.py` encoding chokepoint

**WP**: WP06 | **FRs**: FR-016 – FR-021 | **Source bug**: #644 | **Diagnostic codes**: `CHARTER_ENCODING_*`

## Public API

```python
def load_charter_file(path: Path, *, unsafe: bool = False) -> CharterContent: ...
def load_charter_bytes(data: bytes, *, origin: str, unsafe: bool = False) -> CharterContent: ...
```

`CharterContent` shape: see `data-model.md` §3.

## Detection order

1. **BOM sniff** — if leading BOM bytes match a known encoding (UTF-8-SIG, UTF-16-LE, UTF-16-BE), use that encoding.
2. **Strict UTF-8 decode** — if `data.decode("utf-8")` succeeds, encoding is `"utf-8"` with `confidence = 1.0`.
3. **`charset-normalizer.from_bytes(data).best()`** — if a candidate clears `confidence >= 0.85` (computed from `1.0 - match.chaos`), use it.
4. **Fail** — emit `CHARTER_ENCODING_AMBIGUOUS` with the file path and detected candidates.

## `unsafe` bypass behavior

When `unsafe=True` and detection falls to step 4:

- Use the **highest-confidence** candidate from `charset-normalizer` regardless of threshold (or fall back to `cp1252` if absolutely no candidate exists).
- Set `CharterContent.normalization_applied = True`.
- Write the provenance record with `bypass_used = True`.
- The function returns successfully — the operator is taking responsibility.

When `unsafe=False` (default) and detection falls to step 4:

- Raise `CharterEncodingError` carrying the `CharterEncodingDiagnostic.AMBIGUOUS` code; caller is responsible for stdout/JSON emission.

## Diagnostic body shape

```
ERROR: CHARTER_ENCODING_AMBIGUOUS
  File: kitty-specs/<mission>/charter/charter.yaml
  Detected candidates:
    - cp1252 (confidence 0.62)
    - utf-8 with replacement (confidence 0.48)
  Mixed-content signal: bytes 0xE9 0x80 0xAE at offset 1247 form valid cp1252
  'é€®' but invalid UTF-8.

  Remediation options:
    1. Open the file in a UTF-8-aware editor and re-save.
    2. iconv -f cp1252 -t utf-8 <file> > <file>.utf8 && mv <file>.utf8 <file>.
    3. Re-run with --unsafe (logs bypass_used=true to provenance).
```

## Provenance write

Every successful detection (including pure-UTF-8 with no normalization) writes a record to the provenance file per `contracts/encoding-provenance-schema.md`. Failure path (raise) does **not** write provenance — only successful resolutions are audit-worthy.

## Retrofit sites (NFR-004 budget enforcement)

Exactly three modules in `src/charter/` retrofit their existing `read_text(encoding="utf-8")` calls to `load_charter_file(path)`:

1. `compiler.py:594` — `yaml.load(path.read_text(encoding="utf-8"))` → `yaml.load(load_charter_file(path).text)`
2. `sync.py:151` — `charter_path.read_text("utf-8")` → `load_charter_file(charter_path).text`
3. `interview.py:283, 398` — analogous wrap

Other charter modules (`context.py`, `hasher.py`, `language_scope.py`, `compact.py`, `neutrality/lint.py`) are intentionally NOT modified — they re-read already-normalized files and trust the chokepoint's contract.

## Acceptance fixtures

- cp1252-encoded charter file → ingest succeeds with `source_encoding = "cp1252"`, `normalization_applied = True`, provenance recorded.
- Pure-UTF-8 charter → ingest succeeds with `source_encoding = "utf-8"`, `confidence = 1.0`, `normalization_applied = False`.
- Mixed-content file → raises `AMBIGUOUS`; provenance NOT written.
- Same mixed-content file with `unsafe=True` → succeeds with bypass; provenance has `bypass_used = True`.

## Invariants

- Module count touched by WP06: 4 (`_io.py` new + 3 retrofit sites). NFR-004 budget respected.
- The 5 deferred re-read sites remain unchanged in this WP. WP08 covers legacy-file migration.
