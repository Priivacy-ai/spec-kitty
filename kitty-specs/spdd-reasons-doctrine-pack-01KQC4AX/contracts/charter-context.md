# Contract: Charter Context Injection

## Surface

`spec-kitty charter context --action <action> --json` (existing CLI command). Powered by `src/charter/context.py:build_charter_context()`.

## Behavior change

- When `is_spdd_reasons_active(repo_root)` is `False`: the JSON `text` and `context` fields MUST equal the pre-feature output exactly (byte-or-semantic identical). This is verified by an "inactive baseline" snapshot fixture in `tests/charter/test_charter_context_spdd_reasons.py`.
- When active: the "Action Doctrine" section gains an additional subsection titled "SPDD/REASONS Guidance (action: `<action>`)" appended after the existing tactic lines. Subsection content depends on action per the table in `prompt-fragment.md`.

## Implementation seam

In `src/charter/context.py`, after `_append_action_doctrine_lines()` (line 537), add a single optional call:

```python
if is_spdd_reasons_active(self.repo_root):
    _append_spdd_reasons_guidance(lines, mission, action)
```

Place the helper in a new module (`src/doctrine/spdd_reasons/charter_context.py`) so context.py only imports a single function.

## Inactive guarantee

A regression test loads a fixture project without the pack and asserts that `build_charter_context()` returns identical bytes to the snapshot captured before this mission was implemented.

## Performance

The added work is bounded by reading and formatting at most ≤4 artifact records per call. Total budget for the SPDD branch ≤50ms additional, keeping the call within the 2s target (NFR-002).

## JSON shape (unchanged)

The top-level JSON keys (`result`, `mode`, `text`, `context`, `references_count`, `action`) are unchanged. Only the inner content of `text` and `context` grows when active.
