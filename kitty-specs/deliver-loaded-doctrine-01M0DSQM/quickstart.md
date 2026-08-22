# Quickstart — Verifying Doctrine Delivery (M4)

Red-first per fix (C-003): prove each test red on the merge-base (`upstream/main`) before the fix, green after. Run targeted suites only (full suite ~1h — CI is release authority).

```bash
export PATH="$PWD/.venv/bin:$PATH"   # shadow-venv: prepend .venv/bin
```

## WP-A — delivery/render family
```bash
# Glossary reaches the bundle + names-only render + fetch pointer
pytest tests/charter/test_action_bundle_delivery.py -q
pytest tests/doctrine/drg/test_kind_mapping_totality.py tests/doctrine/drg/test_unknown_kind_fails_loudly.py -q
# Step description renders (procedure + tactic; bundle + profile paths)
pytest tests/charter/ -q -k "step or procedure or tactic or render"
# Every None delivery-table row has a stated reason (new assertion)
pytest tests/charter/test_action_bundle_delivery.py -q -k "reason or none"
```
Expected: glossary term surfaces appear under action doctrine with a `--include glossary-pack:<id>` pointer; a step's `description` renders alongside its `title`; no `slot=None` row lacks a stated reason.

## WP-B — builder overlay seam (#3176)
```bash
# Project-overlay profiles visible through the activation-aware service
pytest tests/specify_cli/tool_surface/profiles/test_projection.py \
       tests/specify_cli/tool_surface/profiles/test_projection_collision_precedence.py \
       tests/specify_cli/tool_surface/profiles/test_projection_org_visibility.py -q
# Byte-identical builder when overlay unset
pytest tests/charter/ -q -k "builder or doctrine_service or activation_aware"
```
Expected: a `.kittify/agent_profiles/<id>.agent.yaml` profile is visible; carve-out deleted; unset-overlay builder unchanged.

## WP-C — procedures[] JSON contract (#3389)
```bash
pytest tests/charter/test_context_parity.py -q
# New: procedures[] typed array present under bumped schema version
spec-kitty charter context --action implement --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('schema', d['context_schema_version']); print('has procedures[]', 'procedures' in d); print('asset typed?', 'assets' in d)"
```
Expected: `context_schema_version == 1.1.0`; `procedures` present as a typed array; no `assets` typed array (asset reference-only).

## Cross-cutting gates (before push)
```bash
ruff check src/charter src/doctrine src/specify_cli/tool_surface/profiles
mypy --strict src/charter src/doctrine   # zero new suppressions
pytest tests/architectural/test_no_legacy_terminology.py -q   # renderer prose + docs touched
```
