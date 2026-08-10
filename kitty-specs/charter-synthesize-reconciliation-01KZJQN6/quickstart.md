# Quickstart — Verifying Charter Synthesize Reconciliation

## Reproduce the defect (baseline red)

The committed red-first test reproduces the loss at the library seam:

```bash
PYTHONPATH=src PWHEADLESS=1 python -m pytest \
  tests/charter/synthesizer/test_synthesize_node_preservation.py -q -p no:cacheprovider
```

Expected on `main`/pre-fix: FAILS — a backed legacy tactic node + its `applies` edge injected
into the on-disk graph are silently dropped by a routine re-synthesis.

## Verify the fix (post-implementation)

1. **Preserve default** — the committed test passes (node + edge survive a plain `synthesize`).
2. **Dry-run surfaces deletions**:
   ```bash
   spec-kitty charter synthesize --dry-run   # lists content that --prune would remove; writes nothing
   ```
3. **Prune is explicit**:
   ```bash
   spec-kitty charter synthesize --prune     # removes divergent content, lists every deletion
   ```
4. **No-op stability**:
   ```bash
   spec-kitty charter synthesize && git diff --stat   # identical inputs → 0 changed bytes (graph + manifest)
   ```
5. **Boundary is not trapped** — after an authoring-only `charter.yaml` edit:
   ```bash
   spec-kitty charter status --json | jq '.freshness.synthesized_drg.state'   # stale
   spec-kitty agent action implement --mission <slug> --agent claude          # proceeds; no content lost
   spec-kitty charter status --json | jq '.freshness.synthesized_drg.state'   # fresh; second run not re-blocked
   git diff --stat .kittify/doctrine/graph.yaml                               # no dropped nodes/edges
   ```
6. **Consumer-pack edges + lint** (#3052):
   ```bash
   spec-kitty charter synthesize && spec-kitty charter lint   # generated directives not flagged as orphaned
   ```

## Gate before PR

```bash
PYTHONPATH=src PWHEADLESS=1 pytest tests/charter/ -n auto --dist loadfile -p no:cacheprovider
ruff check . && mypy src/charter src/specify_cli/charter_runtime
pytest tests/architectural/test_no_legacy_terminology.py -q
```
