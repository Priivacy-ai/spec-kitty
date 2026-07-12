# Contract — Content-Descriptor Resolver (IC-DESCRIPTOR)

The shared helper every WS1 gate imports. Location: `tests/architectural/_ratchet_keys.py`
(or a sibling test-support module). Reuses `contracts/anchoring`.

## Types
```
ContentDescriptor = tuple[rel_path: str, qualname: str, token_substring: str,
                          occurrence: int | None, rationale: str]
CompositeKey      = tuple[str, str]   # (qualname, token_line) — from anchoring.composite_key
```

## resolve_descriptor(source: str, descriptor: ContentDescriptor) -> CompositeKey
- Tokenize `source` via `anchoring.code_tokens_by_line` (normalized space-joined
  tokens; f-string interiors/strings/comments dropped).
- Collect findings whose `anchoring.enclosing_qualname(source, lineno) == descriptor.qualname`
  AND whose normalized token line **contains** `descriptor.token_substring`.
- If `occurrence` is set, select that ordinal (0-based) among matches in file order.
- **MUST** yield **exactly one** finding. **RAISE / FAIL (RED)** if the match
  count is 0 or (with no `occurrence`) >1. Never silently pick the first.
- Return `anchoring.composite_key(source, finding.lineno)`.

## descriptor_still_live(source, descriptor, seeded_key: CompositeKey) -> bool
- Returns True iff `resolve_descriptor(source, descriptor) == seeded_key`
  (exactly-one resolution AND key equality). Any deviation (0 matches, >1, or a
  different key) → False → the twin-guard reds → the entry must be deleted.
- **Forbidden**: "≥1 finding matches" semantics (D-1 bite hole).

## Authoring rule
`token_substring` is written in the **normalized token space**
(`coord_branch or _current_branch`, `parent . parent`, `get_current_branch (`),
NOT raw source (`feature_dir.parent.parent`). A raw-source substring matches
nothing → vacuous green → caught by the FR-013 non-vacuity self-test.
