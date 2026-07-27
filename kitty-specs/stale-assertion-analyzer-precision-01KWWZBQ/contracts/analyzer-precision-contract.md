# Contract — stale-assertion analyzer precision (#2031 + #2343)

`src/specify_cli/post_merge/stale_assertions.py`:
- `_head_still_exports_name(head_tree, name) -> bool` — True iff the ORIGIN file's already-parsed head AST re-exports/imports `name` (`from mod import X` incl. `as _X` / `other as X`, `X ∈ __all__`, `__init__`/module re-export). Origin-file-scoped, no full-repo scan (NFR-002).
- `_extract_changed_symbols` suppresses a removed identifier iff `_head_still_exports_name(head_tree, name)` — NOT "bare name appears in another changed file" (would collide on common names + blind deletions).
- `_is_generic_literal(value) -> bool` — True iff value ∈ `_GENERIC_LITERAL_TOKENS` (pinned frozenset) OR all-punctuation/whitespace/empty. **No length disjunct** (a short literal like `"E001"` can be assert-critical). Suppresses matching removed literals.
- Both **suppress (drop before scanning)**, never downgrade to `info` → `merge/executor.py` + `cli/commands/agent/tests.py` unchanged; FP-ceiling (`findings_per_100_loc`) never counts suppressed findings. NFR-001 preserved (no "definitely_stale").
