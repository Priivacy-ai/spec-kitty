# WP07 Review — Cycle 1 (REJECT)

Reviewer: paula-patterns (architecture-scout / minimal-surface) via reviewer-renata.
Crux risk: over-promotion of internal/plumbing symbols onto the `status` facade.

Verdict: **REJECT — 1 blocking over-promotion.**

All gate checks are green (facade import 95 symbols / 0 dupes, ruff clean, mypy clean,
2739 status+parity tests pass). 16 of the 17 promoted symbols have genuine consumers.
The single blocking issue below must be fixed before approval.

---

## Issue 1 (BLOCKING): `filter_dossier_snapshots` is over-promoted — no production consumer

`filter_dossier_snapshots` (status/preflight.py:62) was added to `status/__init__.py`
`__all__`, but it has **zero production consumers**. Its only consumer anywhere is one
test: `tests/integration/test_dossier_snapshot_no_self_block.py`.

```
grep -rln "\bfilter_dossier_snapshots\b" src/specify_cli --include=*.py | grep -v /status/   # → (empty)
```

The function is a trivial one-line convenience wrapper:
```python
def filter_dossier_snapshots(paths: list[str]) -> list[str]:
    return [p for p in paths if not is_dossier_snapshot(p)]
```

Its sibling `is_dossier_snapshot` IS genuinely consumed in production
(`cli/commands/agent/tasks.py:611,1249` via `_is_dossier_snapshot`), so that promotion
is correct. But the plural wrapper exposes facade surface whose only demand is a test it
ships with. The C-007 / FR-013 bar is "expose exactly the symbols external **consumers**
legitimately need," and the WP's own Risks section says: "Over-promotion → confirm each
promoted symbol has a genuine external consumer; otherwise PRIVATE." A test asserting the
wrapper's own behavior does not establish external production demand.

**How to fix (pick one):**
- Demote: remove `filter_dossier_snapshots` from both the `.preflight` import block and
  `__all__` in `status/__init__.py`. Leave it module-public in `preflight.py` (or
  `_`-prefix it) so the one integration test can still import it from
  `specify_cli.status.preflight` directly — no facade exposure. Update the
  occurrence_map `status.preflight` reason to note `is_dossier_snapshot` PROMOTE +
  `filter_dossier_snapshots` not-promoted (test-only).
- OR, if you intend it as part of the public contract, add a real production caller and
  cite it in the occurrence_map reason.

## Non-blocking notes (no action required)
- `BootstrapResult` and `FeatureStatusLockTimeoutError` show no direct production import,
  but each is the **return type** / **raised-exception contract** of a promoted, genuinely
  production-consumed function (`bootstrap_canonical_state`, `feature_status_lock`).
  External `except`/type-annotation consumers need them on the facade — legitimate.
- ROUTE family (`doctor`, store/reducer/lane_reader/emit/lifecycle mission-level) and
  PRIVATE (`history_parser`, `fire_dossier_sync`) correctly NOT in `__all__`.
- `COORD_OWNED_STATUS_FILES` appears once in `__all__` — not re-promoted/duplicated.
- 0 live `decision: REVIEW` entries remain in occurrence_map (only a comment header).
