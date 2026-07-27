# Contract: SPDD/REASONS Activation Detection

## Function

```python
def is_spdd_reasons_active(repo_root: Path) -> bool: ...
```

## Inputs
- `repo_root`: project root containing `.kittify/charter/`.

## Output
- `True` iff the project's active charter selection contains AT LEAST ONE of:
  - paradigm `structured-prompt-driven-development`
  - tactic `reasons-canvas-fill`
  - tactic `reasons-canvas-review`
  - directive `DIRECTIVE_038`
- `False` otherwise (including when no charter exists).

## Failure modes
- Missing `.kittify/charter/`: returns `False` (not an error).
- Malformed governance.yaml: raises the same exception as existing charter loaders (do not swallow).
- No paradigms section in governance.yaml: returns `False` (not an error).

## Performance
- Reads at most two YAML files (`governance.yaml`, `directives.yaml`). Must complete in <50ms typical.

## Caching
- May be cached per-process for the lifetime of a single CLI invocation. Must NOT persist across invocations.

## Tests (acceptance for WP2)

| Case | Charter selection | Expected |
|---|---|---|
| 1 | empty/no charter | False |
| 2 | only directives outside the pack | False |
| 3 | paradigm `structured-prompt-driven-development` selected | True |
| 4 | tactic `reasons-canvas-fill` selected only | True |
| 5 | tactic `reasons-canvas-review` selected only | True |
| 6 | directive `DIRECTIVE_038` selected only | True |
| 7 | malformed governance.yaml | raises (not silently False) |
