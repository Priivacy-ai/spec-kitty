# Charter Encoding Error & Warning Codes

> **Source of truth**: `src/charter/_diagnostics.py` (StrEnum class `CharterEncodingDiagnostic`).
> This file is a hand-maintained mirror. Until #645's code-to-docs flow exists,
> the StrEnum members and this file's section count must match per NFR-008.

## CHARTER_ENCODING_AMBIGUOUS

**When it fires**: the charter file's byte sequence cannot be decoded as strict
UTF-8 and no single encoding candidate from `charset-normalizer` achieved a
confidence score of ≥ 0.85; the chokepoint cannot safely normalize the content.

**JSON stability**: this code string is stable across minor releases; consumers
may match it as an opaque identifier.

**Remediation**:
1. Open the file in a UTF-8-aware editor (e.g. VS Code, Vim `:set fileencoding=utf-8`) and re-save it.
2. Convert with `iconv`: `iconv -f <detected-encoding> -t utf-8 <file> > <file>.utf8 && mv <file>.utf8 <file>`.
3. Re-run with `--unsafe` to accept the highest-confidence candidate; `bypass_used=true` is recorded in `.encoding-provenance.jsonl`.

**Body example**:

```text
ERROR: CHARTER_ENCODING_AMBIGUOUS
  File: kitty-specs/my-mission/charter/charter.yaml
  Detected candidates:
    - cp1252 (confidence 0.62)
    - utf-8 with replacement (confidence 0.48)
  Mixed-content signal: the byte sequence cannot be decoded as strict UTF-8
  and no single encoding achieved >= 85% confidence.

  Remediation options:
    1. Open the file in a UTF-8-aware editor and re-save.
    2. iconv -f <detected-encoding> -t utf-8 <file> > <file>.utf8 && mv <file>.utf8 <file>.
    3. Re-run with --unsafe (logs bypass_used=true to provenance).
```

## CHARTER_ENCODING_NOT_NORMALIZED

**When it fires**: the charter file is successfully decoded but contains
byte-order marks or characters that indicate the content was not originally
saved as plain UTF-8 (e.g. a UTF-8-BOM file); normalization was applied
automatically and the operator may want to re-save the source file as plain
UTF-8.

**JSON stability**: this code string is stable across minor releases; consumers
may match it as an opaque identifier.

**Remediation**:
1. Re-save the file as UTF-8 without BOM in your editor.
2. Convert with `iconv`: `iconv -f utf-8-sig -t utf-8 <file> > <file>.utf8 && mv <file>.utf8 <file>`.
3. No action required if the content loaded correctly; this is an informational
   warning — the chokepoint normalized the content successfully.

**Body example**:

```text
WARNING: CHARTER_ENCODING_NOT_NORMALIZED
  File: kitty-specs/my-mission/charter/charter.yaml
  Detected encoding: utf-8-sig (confidence 1.00)
  Action: BOM stripped; content normalized to plain UTF-8.
  Recommendation: re-save the file as UTF-8 without BOM to avoid this message.
```
