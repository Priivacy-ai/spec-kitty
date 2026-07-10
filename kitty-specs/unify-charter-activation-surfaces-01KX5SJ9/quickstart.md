# Quickstart: verifying config-as-single-authority

## The behaviour to verify

```bash
# 1. Activate an artefact and confirm it RESOLVES with no answers.yaml edit (the #2524 regression)
spec-kitty charter activate directive <some-directive-stem>
uv run pytest tests/doctrine/test_charter_references_resolve.py::test_no_new_charter_reference_danglers -q   # green, no hand-edit

# 2. Answers is inert for activation (SC-004)
#    edit answers.selected_* only, regenerate -> compiled set UNCHANGED

# 3. Parity guard bites (FR-005 / NFR-002)
#    plant a config<->references divergence -> consistency_check FAILS closed

# 4. Migration preserves the active set (FR-006)
uv run pytest -k "migration and activation" -q   # 0 dropped on a skewed fixture

# 5. Gates
uv run pytest tests/doctrine/ tests/charter/ -q
uv run pytest tests/architectural/test_layer_rules.py -q          # charter !import specify_cli
uv run pytest tests/doctrine/drg/migration/test_extractor.py -k fresh -q   # graph.yaml freshness
ruff check . && mypy src/charter/
```

## Definition of done (mission)

- FR-001–FR-006 satisfied; FR-007 done OR explicitly split to a tracked follow-up (per research Open Question A).
- SC-001 (no dangling), SC-002 (fail-closed guard), SC-003 (0 dropped migration), SC-004 (answers inert) verified.
- Layer rule + graph freshness + terminology + ruff/mypy green.
