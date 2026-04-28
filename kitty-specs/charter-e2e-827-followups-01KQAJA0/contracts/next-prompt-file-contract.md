# Contract — `next --json` prompt-file field (post-#844)

Maps to FR-004, FR-005, FR-006, FR-007, FR-008 and INV-844-{1,2,3} in `data-model.md`.

## Wire format (the parts this mission touches)

```json
{
  "kind": "step | blocked | complete | ...",
  "prompt_file": "<absolute path to prompt body file> | null",
  "prompt_path": "<alias of prompt_file> | null",
  "reason": "<short string, present when kind != step>",
  "...": "..."
}
```

- `prompt_file` is the canonical name. `prompt_path` continues to be accepted as an alias for backward compatibility. The value, when populated, is the same on either field; producers SHOULD set `prompt_file`.

## Invariants enforced by this mission

| ID | Rule |
|---|---|
| **C1** | When `kind == "step"`, `prompt_file` (or `prompt_path` if that is the populated field) is a **non-empty string**. Null and empty-string are illegal. |
| **C2** | When `kind == "step"`, the value emitted under C1 **resolves to an existing file** at envelope-construction time. `Path(value).is_file()` is true. |
| **C3** | When the runtime cannot produce a step (no actionable composed action, blocked dependency, etc.), the envelope's `kind` is **not** `"step"`. The runtime returns `kind=blocked` (or another non-step kind) with a `reason`. `kind=step` with a missing prompt is a runtime invariant violation. |

## Producer obligations (`spec-kitty next` runtime)

- Construct decisions through `RuntimeDecision` (or peer construction site). Validate C1/C2 before serialization.
- A `kind=step` envelope that fails C1 or C2 in production code is a programmer error: the runtime falls back to `kind=blocked` with `reason="prompt_file_not_resolvable"` (or equivalent) instead of emitting an illegal envelope.

## Consumer obligations (`tests/e2e/test_charter_epic_golden_path.py`)

The E2E test asserts, for every issued decision where `kind == "step"`:

```python
prompt = payload.get("prompt_file") or payload.get("prompt_path")
assert prompt is not None, "kind=step must carry a prompt_file (C1)"
assert prompt != "", "kind=step prompt_file must be non-empty (C1)"
assert Path(prompt).is_file(), f"kind=step prompt_file must resolve on disk (C2): {prompt}"
```

For non-step kinds, the test does not assert on the prompt fields.

## Doctrine surface (host-facing)

- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` is updated to state explicitly: "A `kind=step` envelope with a null or non-resolvable `prompt_file` is illegal. If you see one, treat it as a runtime bug, not a `kind=blocked` substitute."
- The inline comment at `src/specify_cli/next/decision.py:79` ("advance mode populates this") is replaced with a comment that names the C1/C2/C3 contract.

## What this contract does NOT change

- The set of legal `kind` values (no new kind introduced).
- The wire-format keys themselves (no rename, no removal).
- Behavior for non-step kinds (`blocked`, `complete`, etc.).
- Any other field on the envelope.
