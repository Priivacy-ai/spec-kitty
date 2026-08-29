# Quickstart / Verification

Run from the repository root checkout of `spec-kitty_TWO`. Targeted surfaces only (charter §Testing).

## US2 — fetch-stanza prose (#3082)
```bash
uv run pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py tests/charter/ -k "fetch or stanza or when or profile" -q
```
Expect: every rendered stanza grammatical AND per-stanza matching `_WHEN_DOING_RE`/`_FETCH_CMD_RE`.

## US1 — empty-charter dispatch (#3064)
```bash
uv run pytest tests/specify_cli/invocation/ -q            # new fallback + dispatch tests + untouched parity
uv run pytest tests/specify_cli/test_doctrine_service_factory.py tests/charter/test_activation_authority.py -q   # gate untouched → green
spec-kitty doctrine asset path common-default-charter     # resolves the shipped default charter (exit 0)
```
Manual: in a temp repo with no charter activations, `spec-kitty dispatch "review the auth module"` →
routes to `generic-agent`, prints the activation warning once, `--json` shows `empty_charter_fallback: true`.
With `--profile architect-alphonso` on the same repo → specialist still resolves (no fallback).

## US3 — context.py decomposition (#2532)
```bash
uv run pytest tests/charter/test_context*.py tests/charter/test_reference_block.py tests/charter/test_activation_consumers.py -q  # parity + seam unit tests
uv run pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py -q                              # regression guards
wc -l src/charter/activation/context.py                                                                                                       # ≤ 500 (stretch 400)
```
Expect: byte-parity on the non-trivial corpus; each seam module exists + imported from its home; cycle dissolved.

## Aggregate (pre-handoff)
```bash
uv run ruff check src/charter/ src/specify_cli/invocation/ src/doctrine/assets/
uv run mypy src/charter/ src/specify_cli/invocation/
```
