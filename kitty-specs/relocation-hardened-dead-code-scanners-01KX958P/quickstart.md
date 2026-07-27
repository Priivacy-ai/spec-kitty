# Quickstart: Relocation-Hardened Dead-Code Scanners

How to run and validate the mission's gates.

## Run the dead-code gate

```bash
export SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 PWHEADLESS=1
uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py -q
```

## Run the key's unit tests (IC-KEY)

```bash
uv run pytest tests/unit/test_symbol_key.py -q
```

## The (a–k) bite battery — through the PRODUCTION path (C-007)

Each assertion drives `_compute_offenders` / the stale ratchet, NOT the standalone key fn:

- **(a)** genuinely-dead symbol → caught
- **(b)** relocated-but-wired content-tier symbol → green (document the module_path-tier dead-relocated carve-out)
- **(c)** same-name fan-out dead sibling → caught (T004)
- **(d)** wired allow-listed symbol → reds stale ratchet (body-independent)
- **(e)** dead helper in a migration file → caught despite FR-010
- **(f)** undecidable/`None`-key symbol → fail-closed
- **(g)** dangling entry (both tiers) → reds; body edit → exactly one signal
- **(h)** `known_modules` + 4 T004 detector tests → byte-unchanged + green
- **(i)** NEW byte-identical same-name pair (the `GateDecision`-collapse vector) → gate escalates/fail-closes → unsanctioned sibling still caught
- **(j)** AnnAssign annotation-whitespace + single-alias `ImportFrom` relocation → 0 false-red (3.11↔3.12)
- **(k)** all 394 entries resolve to a `SymbolKey` (0 un-keyable)

## Motion battery (NFR-001)

For a content-tier sanctioned dead symbol, prove 0 false-red under: module move,
sibling reorder, blank/comment insertion, **AnnAssign annotation whitespace** (`X:int`
vs `X : int`), **single-alias `ImportFrom`**, and the 3.11↔3.12 dimension.

## Full arch suite (NFR-004) — baseline 887, 0 failed

```bash
uv run pytest tests/architectural/ -p no:cacheprovider -q
```

## Warnings census (FR-016 / NFR-006 / SC-005)

```bash
uv run pytest tests/architectural/ -p no:cacheprovider -W default -r w 2>&1 | sed -n '/warnings summary/,/passed/p'
```
Target: **0 first-party warnings** (residuals only as justified third-party filters or
tracked follow-ups).

## Meta-guard stays green

```bash
uv run pytest tests/architectural/test_ratchet_positional_anchor_ban.py -q
```
The new key is all-strings (no int-line anchor) — assert it, don't assume it.
