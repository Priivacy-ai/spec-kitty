# Contract: `next` Output Preservation (NFR-004) — spans WP-A + WP-B

Both durable-fix levers MUST be behavior-preserving. The oracle is a real black-box subprocess diff.

## Guarantee

For identical mission inputs, `spec-kitty next --agent <a> --mission <m> --json` produces **byte-identical stdout JSON** whether:
- imports are trimmed (WP-A) or not,
- the charter freshness verdict is served from cache (warm) or freshly computed (cold, WP-B),

**excluding** the intrinsically per-call `timestamp` field (generated at emit, never part of the projection or the freshness verdict).

## Test shape

- Run the CLI twice via `subprocess.run([sys.executable, "-m", "specify_cli", "next", …, "--json"])` (cold then warm), capture stdout, JSON-load, delete/normalize only `timestamp`, assert equality.
- **Do NOT reuse** the masked `canonical()` helper from `tests/runtime/test_bridge_parity.py` — its masking of ULID/timestamp/path noise would silently accept a real regression that lands in a masked field. NFR-004 wants literal byte-identity (minus the one documented `timestamp`).
- Cover both the no-charter fixture (WP-A path) and a charter-bearing fixture (WP-B path).

## Rationale

Deferred (lazy) imports must resolve identically when first used; a cached freshness verdict must deserialize to the same object the parse would have produced. This contract is the safety net that lets both optimizations ship without changing observable behavior.
