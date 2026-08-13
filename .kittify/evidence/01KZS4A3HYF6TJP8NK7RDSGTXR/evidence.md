# Core #3328 WP04 independent Prime review

- Verdict: **APPROVE**
- Governed reviewer Op: `01KZS4A3HYF6TJP8NK7RDSGTXR` (`reviewer-renata`)
- Reviewed implementation commit: `c2edd891d8a9de67e3fa673a9568912fa119b79d`
- Lane final tree: `b153992f3c7d232ff5e4524849a17ab28b9f8c02`
- Harness: Prime Agent `0.7.1`, OpenRouter, requested model `~moonshotai/kimi-latest`, thinking `high`, no session
- Provider response model: `moonshotai/kimi-k3` (catalog alias metadata is non-authoritative)
- Raw JSONL: `/tmp/core-3328-wp04-prime-review.jsonl`
- Raw bytes: `23367336`
- Raw SHA-256: `38c16cfd79c4a36d63890e385375293399a70b034980dd4ccb6058934c385536`

## Independent evidence

- Real-git subprocess probes exercised `agent mission create ... --owned-checkout ... --json` and `next --mission ... --owned-checkout ... --json` for nested, foreign, and broken-pointer checkout arguments. Both surfaces exited `1`, emitted `success:false`, and returned byte-identical stable codes: `OWNERSHIP_NESTED`, `OWNERSHIP_FOREIGN`, `OWNERSHIP_BROKEN_POINTER`.
- WP04 architectural fence: `6 passed in 56.27s`. No production `allow_worktree_context=True` bypass; import-origin probe confirmed lane source; probe self-removed and tree remained clean.
- Ownership core: `21 passed in 49.11s`.
- Targeted agent create/next: `33 passed, 44 deselected in 56.41s`.
- Full agent suite: `1477 passed, 20 skipped, 7 warnings in 142.10s`; with the separately exercised WP04 six tests this matches the orchestrator's `1483 passed` gate.
- Current full architectural xdist run reported `4 failed, 2001 passed, 5 skipped, 2 xfailed, 36 errors in 559.55s`. Exact serial/base adjudication showed no WP04 regression:
  - stale surface inventory: current and immutable pre-WP04 base `01787a7db` both `2 failed, 15 passed`;
  - CI collection/gate group: current and immutable pre-WP04 base both `2 failed, 100 passed, 15 errors`.

## Mission-level blockers carried to WP05

These do not alter the WP04 APPROVE verdict, but block mission acceptance/merge:

1. A real mission created only under a linked checkout's `kitty-specs` cannot be found by `next --owned-checkout <linked>` from either primary or linked cwd (`MISSION_NOT_FOUND`). WP05 must repair same-owned-root mission content resolution with no ambient/primary fallback and prove it with a real installed-CLI RED-to-green test.
2. `tests/architectural/surface_resolution_audit/inventory.md` and `tests/architectural/test_single_mission_surface_resolver.py` contain stale descriptors for the WP02 `effective_root` seam. WP05 must update them under governed ownership.

Final Prime output: `VERDICT: APPROVE`.
