# Contract — Intake source provenance

**Owning WP**: WP02
**Backing FR**: FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, NFR-003,
NFR-004

## Provenance line escape rules (FR-007)

Provenance lines MUST be written through
`specify_cli.intake.provenance.escape_for_comment()`. The helper:

1. Strips ASCII control characters (0x00–0x1F, 0x7F) except `\t`.
2. Replaces comment-terminator-like sequences:
   - `-->` → `--&gt;`
   - `*/` → `*&#47;`
   - leading `#` (line start) → `\\#` (when written into a Markdown context)
3. Clips the resulting string to 256 bytes (UTF-8 safe truncation).
4. Returns the cleaned string.

The helper has unit tests for each rule.

## Path scanning (FR-008, FR-012)

Path resolution rules:

1. Compute `intake_root_resolved = Path(intake_root).resolve(strict=True)`.
2. For every candidate path under the root, compute
   `candidate.resolve(strict=True)`.
3. Assert `candidate_resolved.is_relative_to(intake_root_resolved)`.
4. If assertion fails, raise `INTAKE_PATH_ESCAPE` with both paths in the
   message.

The same `intake_root_resolved` is used for the brief write target (FR-012).

## Size cap (FR-009, NFR-003)

- Default cap: `intake.max_brief_bytes = 5_242_880` (5 MB).
- Configurable in `.kittify/config.yaml`.
- Enforcement order:
  1. `os.stat(path).st_size`. If `> cap`, raise `INTAKE_TOO_LARGE`.
  2. If `os.stat()` is unavailable (e.g. STDIN-piped), use
     `read1(cap + 1)`; if `len(buf) > cap`, raise `INTAKE_TOO_LARGE`.
- Memory ceiling: `cap + small overhead`. NFR-003 asserts < 1.5 × cap in
  resident memory during a 50 MB rejection trial.

## Atomic write (FR-010, NFR-004)

Brief and provenance writes use:

```python
with open(target_tmp, "wb") as f:
    f.write(payload)
    f.flush()
    os.fsync(f.fileno())
os.replace(target_tmp, target)
```

Pre-conditions:

- `target_tmp` is in the same directory as `target` (same filesystem).
- If `target` exists on a different filesystem, the helper logs a structured
  warning and falls back to a non-atomic write only when explicitly forced
  by `intake.allow_cross_fs=True`. Default behavior is to fail loudly.

NFR-004 test: 100 simulated kill-9 mid-write trials → 0 partial files.

## Missing vs corrupt distinction (FR-011)

`intake.read_brief()` raises:

- `INTAKE_FILE_MISSING` (with `path` in detail) when `os.stat()` raises
  `FileNotFoundError`.
- `INTAKE_FILE_UNREADABLE` (with `path` and underlying `OSError` chain)
  for any other read failure.

Callers MUST NOT collapse these into a single error type. The CLI surface
distinguishes them in user-facing messages.
